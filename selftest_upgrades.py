"""升级池的自动化测试。

跑法（在 alien_invasion 目录下）：

    python selftest_upgrades.py
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
dir_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(dir_path)
sys.path.insert(0, dir_path)

import random

import pygame

pygame.init()
import alien_invasion as m
from game_state import State
from settings import Settings
from upgrade_screen import UpgradeScreen
from upgrades import EVOLUTIONS, UPGRADES, UpgradePool

ok = 0
fail = 0


def new_pool():
    """造一个全新的游戏 + 空的升级池（每段测试都用干净的）。"""
    game = m.AlienInvasion()
    return game, UpgradePool(game)


def check(name, cond, extra=""):
    """cond 为真就算通过。extra 用来在失败时打印实际值。"""
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK]   {name} {extra}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {extra}")


# ===========================================================================
# 一、先测不依赖随机的部分（最简单，先让这几条绿）
# ===========================================================================

print("=" * 62)
print("① 等级记录")
print("=" * 62)

game, pool = new_pool()
settings = game.settings

check("开局一个升级都没有", pool.level_of("engine") == 0)
check("没拿过的升级，level_of 返回 0 而不是报错", pool.level_of("不存在的key") == 0)
check("开局 engine 还没满级", pool.is_maxed(pool.find("engine")) is False)

# 找一个 effect 是确定值的升级来测（engine 让 ship_speed * 1.2）
speed_before = settings.ship_speed
pool.take("engine")
check("take 之后等级变成 1", pool.level_of("engine") == 1)
check(
    "take 之后效果真的生效了（ship_speed 变快）",
    settings.ship_speed > speed_before,
    f"({speed_before} -> {settings.ship_speed})",
)

print()
print("=" * 62)
print("② 满级（边界）")
print("=" * 62)

game, pool = new_pool()
settings = game.settings
# ⚠️ 按 key 找，不要写 UPGRADES[0] —— 按位置取很脆：
#    表的顺序一变，测试就测到别的升级上去了（这个坑当场就踩到了）
engine = pool.find("engine")

for _ in range(engine.max_level):
    pool.take("engine")
check(f"连拿 {engine.max_level} 次后正好满级", pool.is_maxed(engine) is True)

speed_at_max = settings.ship_speed
pool.take("engine")  # 满级之后再来一次
check(
    "满级之后再 take，速度不应该继续涨",
    settings.ship_speed == speed_at_max,
    f"(满级时 {speed_at_max}，又拿一次后 {settings.ship_speed})",
)

print()
print("=" * 62)
print("③ available() 的基本行为")
print("=" * 62)

game, pool = new_pool()
settings = game.settings

pick = pool.available(3)
check("返回的是 list", isinstance(pick, list))
check("默认要 3 条就有 3 条", len(pick) == 3, f"(实际 {len(pick)})")
check("挑出来的都是 Upgrade 对象", all(hasattr(u, "key") for u in pick))
check(
    "同一批里没有重复",
    len({u.key for u in pick}) == len(pick),
    f"({[u.key for u in pick]})",
)

print()
print("=" * 62)
print("④ available() 的边界（这些最容易漏）")
print("=" * 62)

# 边界 1：要得比剩下的多 -> 应该给全部剩下的，而不是报错
game, pool = new_pool()
total = len(UPGRADES)
pick = pool.available(total + 10)
check(
    f"要 100 条但只有 {total} 条可选 -> 返回全部 {total} 条，不报错",
    len(pick) == total,
    f"(实际 {len(pick)})",
)

# 边界 2：一条都不剩 -> 空列表
# ⚠️ 必须连进化一起拿满：把 10 条普通升级全拿满之后，
#    进化反而刚好全部解锁（前置都满级了），此时还剩 3 条可选。
game, pool = new_pool()
for u in UPGRADES:
    for _ in range(u.max_level):
        pool.take(u.key)
for u in EVOLUTIONS:
    for _ in range(u.max_level):
        pool.take(u.key)
check("全部拿满后，available 返回空列表 []", pool.available(3) == [])
check("全部拿满后，每个都 is_maxed", all(pool.is_maxed(u) for u in pool.definitions))

# 边界 3：拿满一部分 -> 满级的不能再出现
game, pool = new_pool()
for _ in range(UPGRADES[0].max_level):
    pool.take(UPGRADES[0].key)
maxed_key = UPGRADES[0].key
appeared = set()
for _ in range(200):
    appeared |= {u.key for u in pool.available(3)}
check(
    f"把 {maxed_key} 拿满后，它再也不出现在候选里",
    maxed_key not in appeared,
    f"(200 次抽样里出现过: {sorted(appeared)})",
)
check(
    "其他升级仍然会出现（不是把所有人都筛掉了）",
    len(appeared) >= 2,
    f"(出现过 {sorted(appeared)})",
)

print()
print("=" * 62)
print("⑤ 随机性：候选应该是随机的，不能每次都一样")
print("=" * 62)

game, pool = new_pool()
selections = {tuple(sorted(u.key for u in pool.available(3))) for _ in range(60)}
check(
    "多次调用能抽出不同的组合（说明真的是随机挑）",
    len(selections) > 1,
    f"(60 次里出现 {len(selections)} 种不同组合)",
)

# 固定种子 -> 结果可复现（带随机的代码要能测，就得能复现）
random.seed(123)
a = [u.key for u in UpgradePool(m.AlienInvasion()).available(3)]
random.seed(123)
b = [u.key for u in UpgradePool(m.AlienInvasion()).available(3)]
check("同一个随机种子 -> 同一套结果（可复现）", a == b, f"({a} vs {b})")
random.seed()

print()
print("=" * 62)
print("⑥ 你加的升级都有说明吗（给玩家看的）")
print("=" * 62)

check(f"至少有 6 条升级（现在 {len(UPGRADES)} 条）", len(UPGRADES) >= 6)
check(
    "每条都有 key / title / detail",
    all(u.key and u.title and u.detail for u in UPGRADES),
)
check("key 不重复", len({u.key for u in UPGRADES}) == len(UPGRADES))
check("每条都能被调用（apply 是可调用的）", all(callable(u.apply) for u in UPGRADES))
check("max_level 都是正数", all(u.max_level > 0 for u in UPGRADES))


def snapshot(game):
    """把"升级可能改动的所有东西"拍成一张快照，用来对比前后。"""
    s, st = game.settings, game.stats
    return (
        s.ship_speed,
        s.bullet_speed,
        s.alien_speed,
        s.bullets_allowed,
        s.ship_limit,
        s.bullets_per_shot,
        s.bullets_pierce,
        s.auto_fire,
        s.psionic_radius,
        st.shield,
        st.ship_left,
    )


noop = []
for u in UPGRADES:
    g_tmp, _ = new_pool()
    before = snapshot(g_tmp)
    u.apply(g_tmp)
    if snapshot(g_tmp) == before:
        noop.append(u.key)
check(
    "每条升级 apply 一次都真的改了东西（不是空函数）",
    not noop,
    f"(没反应的: {noop})",
)

print()
print("=" * 62)
print("⑦ 稀有度：越强越少见")
print("=" * 62)

from upgrades import RARITY_WEIGHT, Rarity

check("每条升级都有合法稀有度", all(isinstance(u.rarity, Rarity) for u in UPGRADES))
check(f"一共 {len(UPGRADES)} 条升级", len(UPGRADES) >= 8, f"(实际 {len(UPGRADES)})")
BASE_RARITIES = (Rarity.COMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY)
check(
    "普通池的四档稀有度都至少有一条",
    {u.rarity for u in UPGRADES} == set(BASE_RARITIES),
    f"(实际有 {sorted(r.name for r in {u.rarity for u in UPGRADES})})",
)
check(
    "ASCENDED 只属于进化，普通升级里一条都没有",
    all(u.rarity is Rarity.ASCENDED for u in EVOLUTIONS)
    and all(u.rarity is not Rarity.ASCENDED for u in UPGRADES),
)

# 加权抽样：同一个池子抽 1200 次，看各档出现次数
# （进化此时还锁着，所以只统计普通池的四档）
game, pool = new_pool()
random.seed(20261018)
counts = {r: 0 for r in BASE_RARITIES}
for _ in range(1200):
    counts[pool.available(1)[0].rarity] += 1
random.seed()

check(
    "COMMON 出现最多",
    counts[Rarity.COMMON] > counts[Rarity.RARE],
    f"(COMMON {counts[Rarity.COMMON]} / RARE {counts[Rarity.RARE]})",
)
check(
    "RARE 比 EPIC 多",
    counts[Rarity.RARE] > counts[Rarity.EPIC],
    f"(RARE {counts[Rarity.RARE]} / EPIC {counts[Rarity.EPIC]})",
)
check(
    "LEGENDARY 最罕见",
    counts[Rarity.LEGENDARY] < counts[Rarity.EPIC],
    f"(LEGENDARY {counts[Rarity.LEGENDARY]} / EPIC {counts[Rarity.EPIC]})",
)
check(
    "四档都抽得到（不是某档被权重压成 0）",
    all(v > 0 for v in counts.values()),
    f"(实际 {({r.name: v for r, v in counts.items()})})",
)

print()
print("=" * 62)
print("⑧ 进化（融合）：前置满级后才出现")
print("=" * 62)

# 8.1 数据一致性（先测数据，再测行为）
base_by_key = {u.key: u for u in UPGRADES}
missing = []
for u in EVOLUTIONS:
    for key, level in u.requires:
        base = base_by_key.get(key)
        if base is None or level != base.max_level:
            missing.append((u.key, key, level))
check("至少 2 条进化路径", len(EVOLUTIONS) >= 2, f"(现在 {len(EVOLUTIONS)} 条)")
check(
    "每条进化的前置都真实存在，且要求的等级正好是『满级』",
    not missing,
    f"(有问题的: {missing})",
)
check(
    "进化都是 ASCENDED，且 max_level = 1（一局一次）",
    all(u.rarity is Rarity.ASCENDED and u.max_level == 1 for u in EVOLUTIONS),
)
check(
    "进化 key 不和普通升级撞名",
    not ({u.key for u in EVOLUTIONS} & {u.key for u in UPGRADES}),
)

# 8.2 开局：进化一条都不该出现在候选里
game, pool = new_pool()
appeared = set()
for _ in range(300):
    appeared |= {u.key for u in pool.available(len(pool.definitions))}
check(
    "开局抽 300 次，进化一条都没出现过",
    not (appeared & {u.key for u in EVOLUTIONS}),
    f"(出现过: {sorted(appeared)})",
)
check(
    "开局时 ASCENDED 稀有度抽到 0 次（它只属于进化）",
    all(pool.available(1)[0].rarity is not Rarity.ASCENDED for _ in range(200)),
)

# 8.3 边界：只拿一半前置 -> 仍然锁着，而且 take 也拿不到
game, pool = new_pool()
for _ in range(pool.find("multi_shot").max_level - 1):
    pool.take("multi_shot")
check(
    "MULTI SHOT 差一级时，STARFALL CANNON 仍未解锁",
    pool.is_unlocked(pool.find("starfall_cannon")) is False,
)
check(
    "没解锁时直接 take，必须被拒绝（返回 False）",
    pool.take("starfall_cannon") is False,
    f"(等级被改成了 {pool.level_of('starfall_cannon')})",
)

# 8.4 两条前置都满级 -> 立刻解锁，且能在 available 里抽到
game, pool = new_pool()
for _ in range(pool.find("multi_shot").max_level):
    pool.take("multi_shot")
for _ in range(pool.find("cannon").max_level):
    pool.take("cannon")
check(
    "两条前置满级后，进化解锁",
    pool.is_unlocked(pool.find("starfall_cannon")) is True,
)
check(
    "解锁之后 available() 里一定有它",
    "starfall_cannon" in {u.key for u in pool.available(len(pool.definitions))},
)

# 8.5 拿进化：真的生效 + 一级满 + 拿完就消失
fusion_before = snapshot(game)
check("take 进化返回 True", pool.take("starfall_cannon") is True)
check("进化只升一级就满级", pool.is_maxed(pool.find("starfall_cannon")) is True)
check(
    "进化效果真的生效了（不是空函数）",
    snapshot(game) != fusion_before,
    f"({fusion_before} -> {snapshot(game)})",
)
check(
    "拿过之后不再出现在候选里",
    "starfall_cannon" not in {u.key for u in pool.available(len(pool.definitions))},
)

# 8.6 新一局：进化跟着清空、重新锁上
game._start_game()
check("开新局后进化等级归零", game.upgrades.level_of("starfall_cannon") == 0)
check(
    "开新局后进化重新锁上",
    game.upgrades.is_unlocked(game.upgrades.find("starfall_cannon")) is False,
)

print()
print("=" * 62)
print("⑨ 进化提示条（界面联动）")
print("=" * 62)


def take_choice(game, choice):
    """模拟"三选一里选了这一张"：摆好界面 -> 走 _take_upgrade()。"""
    game.upgrade_screen = UpgradeScreen([choice], game.screen_rect)
    game.state = State.UPGRADING
    game._take_upgrade()


game, _ = new_pool()
game._start_game()
for _ in range(game.upgrades.find("multi_shot").max_level):
    game.upgrades.take("multi_shot")
for _ in range(game.upgrades.find("cannon").max_level):
    game.upgrades.take("cannon")

take_choice(game, game.upgrades.find("starfall_cannon"))
check("拿进化后提示条开始倒计时", game.evolution_timer > 0, f"({game.evolution_timer})")
check("提示条图像已经渲染好", game.sb.evolution_image is not None)
check("拿完立刻回到 PLAYING", game.state is State.PLAYING)

for _ in range(game.settings.evolution_banner_frames):
    game._update_screen()
check(
    "倒计时结束后提示条自动消失",
    game.evolution_timer == 0 and game.sb.evolution_image is None,
    f"(timer={game.evolution_timer})",
)

# 对照组：普通升级不该弹提示条（否则"提示条"就没意义了）
game._start_game()
take_choice(game, game.upgrades.find("engine"))
check("普通升级不会弹进化提示", game.evolution_timer == 0)
check("普通升级也不会留下提示图像", game.sb.evolution_image is None)

pygame.quit()
print()
print("=" * 62)
print(f"结果：{ok} 项通过, {fail} 项失败")
print("=" * 62)
sys.exit(1 if fail else 0)
