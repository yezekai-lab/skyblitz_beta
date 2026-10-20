"""局内升级池：攒够分数就弹三选一。

=====================================================================
【这个文件的核心逻辑由你自己写】

其余部分 Copilot 已经接好了：
  - 分数攒够阈值 -> 进入 State.UPGRADING（弹三选一）
  - 三张卡片画在屏幕上
  - 键盘 1/2/3 / 鼠标点 / 手柄 选卡
  - 选完切回 State.PLAYING

你要实现的是下面标了  TODO  的两处：`available()` 和 `take()` —— 已帮你修好。

UPGRADES 那张表随时可以继续加，那是设计工作。

=====================================================================

【两类升级的差别，很重要】

    数值升级：只改一个【数字】—— 同一条代码路径跑得更快 / 更多
    机制升级：改一个【开关】—— 代码走进【另一条分支】

两者在代码里长得一模一样（都是"改一个字段"），区别在于
**谁去读它、读到之后怎么做**。

    # 数值：飞船移动的代码不变，只是数字大了
    self.x += self.settings.ship_speed * direction

    # 机制：发射的代码里多了分支 —— 这就是"另一条路"
    if self.settings.bullets_pierce:
        ...
=====================================================================
"""

import random
from enum import Enum, auto


class Rarity(Enum):
    """稀有度。它同时决定两件事：出现的概率、卡片边框的颜色。

    参考《弓箭手大作战》(Archero)：越强的技能越少见。
    """

    COMMON = auto()
    RARE = auto()
    EPIC = auto()
    LEGENDARY = auto()
    ASCENDED = auto()  # 只属于「进化」—— 不在普通池里出现


# 抽取权重：数字是"票数"，越大越容易抽到。
# COMMON 10 票 vs LEGENDARY 1 票 —— 差 10 倍。
RARITY_WEIGHT = {
    Rarity.COMMON: 10,
    Rarity.RARE: 5,
    Rarity.EPIC: 2,
    Rarity.LEGENDARY: 1,
    # 进化同时只会有 1~3 条可抽，所以给 5 票也不会"满屏进化"
    Rarity.ASCENDED: 5,
}

# 卡片颜色。这一套是《弓箭手大作战》那类游戏的通用约定：
# 灰 → 蓝 → 紫 → 橙，越往后越稀有。
RARITY_COLOR = {
    Rarity.COMMON: (168, 176, 190),
    Rarity.RARE: (86, 156, 236),
    Rarity.EPIC: (170, 108, 238),
    Rarity.LEGENDARY: (246, 174, 72),
    # 青白色：一眼就能和下面四档区分开，卡面上一看就知道"这是进化"
    Rarity.ASCENDED: (110, 231, 219),
}


class Upgrade:
    """一条升级的"定义"。它只描述"这是什么"，不管"拿了几次"。

    字段：
        key        唯一标识，用来记录"这个升级已经拿了几级"
        title      卡片上的大字（英文，界面不渲染中文）
        detail     卡片上的说明（写清楚它到底改了什么，玩家才敢选）
        max_level  最多能拿几次（拿满了就不要再出现在候选里）
        apply      生效函数，签名是 apply(game) -> None
        rarity     稀有度（影响抽取概率 + 卡片颜色）
        category   分类标签，纯展示用（OFFENSE / DEFENSE / SYSTEM）
        requires   「前置条件」：((key, 等级), ...)。空元组 = 普通升级，随时可抽；
                   非空 = 进化，**只有前置全部满级之后才会出现在候选里**
    """

    def __init__(
        self, key, title, detail, max_level, apply, rarity, category, requires=()
    ):
        self.key = key
        self.title = title
        self.detail = detail
        self.max_level = max_level
        self.apply = apply
        self.rarity = rarity
        self.category = category
        self.requires = tuple(requires)

    @property
    def is_fusion(self):
        """是不是「进化」条目。有前置条件的就是。"""
        return bool(self.requires)


# ---------------------------------------------------------------------------
# 效果函数。写成有名字的函数而不是 lambda，是为了让人一眼看懂改的是什么。
#
# ⚠️ 参数是 game 而不是 settings —— 因为有些升级要动 stats（比如加命）。
#    之前给的接口 apply(settings) 太窄了：settings 里没有命数。
# ---------------------------------------------------------------------------


# ===== 机制类 =====


def _multi_shot(game):
    """一次多打出一发。发射代码里按这个数字决定发几发、怎么排开。"""
    game.settings.bullets_per_shot += 1


def _pierce(game):
    """子弹打中外星人后不消失，能继续打后面的。"""
    game.settings.bullets_pierce = True


def _auto_fire(game):
    """按住开火键就持续射击，不用一下一下点。"""
    game.settings.auto_fire = True


def _extra_life(game):
    """多一条命上限，并把当前命数补满。

    ⚠️ 这条只给 max_level=1 且是 EPIC —— 一局最多拿一次。
    早期设计成 RARE×2 每次 +1 命，相当于一局能多 2 条命（+67% 容错），
    再叠上“跨局累积”的 bug，就完全超标了。
    """
    game.settings.ship_limit += 1
    game.stats.ship_left = game.settings.ship_limit


def _plasma_shield(game):
    """【神族】等离子护盾：撞到时先碎一层盾，不扣命。"""
    game.stats.shield += 1


def _psionic_storm(game):
    """【神族】灵能风暴：击落一个外星人时，炸掉它周围一圈。

    每拿一级伤害半径变大。半径存在 settings 里，碰撞代码去读。
    """
    game.settings.psionic_radius += 55


def _time_warp(game):
    """【神族】时间扭曲：外星人整队变慢。"""
    game.settings.alien_speed *= 0.8


# ===== 数值类 =====


def _faster_ship(game):
    game.settings.ship_speed *= 1.2


def _faster_bullets(game):
    game.settings.bullet_speed *= 1.25


def _bigger_magazine(game):
    game.settings.bullets_allowed += 10


# ---------------------------------------------------------------------------
# 升级表：4 机制 + 3 数值。
#
# 命名走【神族】风格；rarity 决定出现概率（LEGENDARY 比 COMMON 少见 10 倍）。
# 想再加？照着写一个 _xxx(game) 效果函数，再往这里加一行。
# ---------------------------------------------------------------------------
UPGRADES = (
    # ===== 传说：一次改变玩法 =====
    Upgrade(
        "psionic_storm",
        "PSIONIC STORM",
        "Slain aliens erupt, burning their neighbours",
        2,
        _psionic_storm,
        Rarity.LEGENDARY,
        "OFFENSE",
    ),
    # ===== 史诗 =====
    Upgrade(
        "multi_shot",
        "MULTI SHOT",
        "Fire one more bolt per shot",
        2,
        _multi_shot,
        Rarity.EPIC,
        "OFFENSE",
    ),
    Upgrade(
        "pierce",
        "PHASE PIERCE",
        "Bolts phase through aliens",
        1,
        _pierce,
        Rarity.EPIC,
        "OFFENSE",
    ),
    Upgrade(
        "time_warp",
        "TIME WARP",
        "The alien fleet slows by 20%",
        2,
        _time_warp,
        Rarity.RARE,
        "SYSTEM",
    ),
    # ===== 稀有 =====
    Upgrade(
        "plasma_shield",
        "PLASMA SHIELD",
        "Absorb one hit with a plasma barrier",
        2,
        _plasma_shield,
        Rarity.RARE,
        "DEFENSE",
    ),
    Upgrade(
        "auto_fire",
        "AUTO FIRE",
        "Hold fire to shoot continuously",
        1,
        _auto_fire,
        Rarity.EPIC,
        "SYSTEM",
    ),
    Upgrade(
        "extra_life",
        "EXTRA LIFE",
        "One more ship, and restore all ships",
        1,
        _extra_life,
        Rarity.EPIC,
        "DEFENSE",
    ),
    # ===== 普通 =====
    Upgrade(
        "engine",
        "ENGINE",
        "Ship moves 20% faster",
        3,
        _faster_ship,
        Rarity.COMMON,
        "SYSTEM",
    ),
    Upgrade(
        "cannon",
        "CANNON",
        "Bolts fly 25% faster",
        3,
        _faster_bullets,
        Rarity.COMMON,
        "OFFENSE",
    ),
    Upgrade(
        "magazine",
        "MAGAZINE",
        "Hold 10 more bolts",
        2,
        _bigger_magazine,
        Rarity.COMMON,
        "SYSTEM",
    ),
)


# ---------------------------------------------------------------------------
# 进化（融合）：两条相关升级【都满级】之后，池子里才会额外出现一条专属升级。
#
# 它和普通升级只有一处不同：**requires 非空**。
# 也就是说，进化不是"另一套系统"，只是给升级表多了一个"解锁条件"字段。
#
# 三个设计要点：
#   1. 效果是「两条前置各自效果的加强版」，不是凭空新机制 —— 玩家能理解
#   2. max_level = 1：一局最多进化一次，进完就从池子里消失
#   3. 稀有度 ASCENDED（青白）：卡面上一眼看得出来
# ---------------------------------------------------------------------------


def _starfall_cannon(game):
    """MULTI SHOT × CANNON 的进化：再多一发，且弹速 +50%。"""
    game.settings.bullets_per_shot += 1
    game.settings.bullet_speed *= 1.5


def _void_lance(game):
    """PHASE PIERCE × PSIONIC STORM 的进化：风暴范围 +70，并送一层护盾。"""
    game.settings.psionic_radius += 70
    game.stats.shield += 1


def _chrono_drive(game):
    """ENGINE × TIME WARP 的进化：飞船更快，舰队再慢 15%。"""
    game.settings.ship_speed *= 1.3
    game.settings.alien_speed *= 0.85


EVOLUTIONS = (
    Upgrade(
        "starfall_cannon",
        "STARFALL CANNON",
        "One more bolt, and bolts fly 50% faster",
        1,
        _starfall_cannon,
        Rarity.ASCENDED,
        "EVOLUTION",
        requires=(("multi_shot", 2), ("cannon", 3)),
    ),
    Upgrade(
        "void_lance",
        "VOID LANCE",
        "Storms reach 70px further, plus a plasma shield",
        1,
        _void_lance,
        Rarity.ASCENDED,
        "EVOLUTION",
        requires=(("pierce", 1), ("psionic_storm", 2)),
    ),
    Upgrade(
        "chrono_drive",
        "CHRONO DRIVE",
        "Ship 30% faster, and the fleet 15% slower",
        1,
        _chrono_drive,
        Rarity.ASCENDED,
        "EVOLUTION",
        requires=(("engine", 3), ("time_warp", 2)),
    ),
)


class UpgradePool:
    """管着"有哪些升级、已经拿了哪些、现在能选哪几个"。

    Args:
        ai_game: 游戏对象。升级生效时可能改 settings，也可能改 stats。
    """

    def __init__(self, ai_game):
        self.game = ai_game
        self.settings = ai_game.settings
        self.definitions = list(UPGRADES) + list(EVOLUTIONS)
        # key -> 已经拿了几级。开局是空的（一个都没有）
        self.levels = {}

    def level_of(self, key):
        """这个升级已经拿了几级。没拿过就是 0。"""
        return self.levels.get(key, 0)

    def is_maxed(self, upgrade):
        """这个升级是不是已经拿满了。"""
        return self.level_of(upgrade.key) >= upgrade.max_level

    def is_unlocked(self, upgrade):
        """「进化」的前置条件满足了没有。普通升级（requires 为空）永远算满足。

        注意这里判断的是「前置是否都**满级**」，不是「是否拿过」——
        半个 MULTI SHOT 不该换来进化。
        """
        return all(self.level_of(key) >= level for key, level in upgrade.requires)

    def available(self, count=3):
        """从"能拿"的升级里按稀有度加权随机挑 `count` 条。

        三个要点：
            1. 先筛掉拿满的
            2. 再筛掉**还没解锁的进化**（前置没满级）
            3. **加权抽取**：稀有度越高的票数越少（COMMON 10 票、LEGENDARY 1 票）
               → 越强的越少见，这正是 Archero 那种感觉

        为什么不用 random.sample：sample 是"等概率"的，没有权重。
        所以这里用 random.choices(weights=...) 一次抽一个，抽中的从池子里拿出来，
        再抽下一个 —— 这样既带权重，又保证不重复。
        """
        pool = [
            u for u in self.definitions if not self.is_maxed(u) and self.is_unlocked(u)
        ]
        picked = []
        while pool and len(picked) < count:
            weights = [RARITY_WEIGHT[u.rarity] for u in pool]
            chosen = random.choices(pool, weights=weights, k=1)[0]
            picked.append(chosen)
            pool.remove(chosen)
        return picked

    def find(self, key):
        """按 key 找出升级定义；找不到返回 None。"""
        for upgrade in self.definitions:
            if upgrade.key == key:
                return upgrade
        return None

    def take(self, key):
        """玩家选了一条升级：等级 +1，并让它立刻生效。

        分三步（顺序很重要）：
            1. 先把定义找出来；找不到就直接返回（不要继续往下跑）
            2. 已经满级的、**还没解锁的进化**，都直接返回
               —— 在这里拦住，比在 apply 里拦更干净
            3. 记等级 + 调 apply

        为什么要拦"没解锁的进化"：UI 只画 available() 里出来的卡，
        但 `take()` 是公开方法，测试和以后的作弊码都会直接调它。
        不拦的话，一句 take("starfall_cannon") 就能凭空拿到进化。

        返回 True 表示真的生效了，False 表示没生效（找不到 / 已满级 / 没解锁）。
        返回值的用处：UI 可以据此判断"这次点击到底有没有用"。
        """
        upgrade = self.find(key)
        if upgrade is None:
            return False
        if self.is_maxed(upgrade):
            return False
        if not self.is_unlocked(upgrade):
            return False

        self.levels[key] = self.level_of(key) + 1
        upgrade.apply(self.game)
        return True
