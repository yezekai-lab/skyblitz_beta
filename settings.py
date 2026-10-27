class Settings:
    def __init__(self):
        # 每秒跑多少帧。游戏里所有"每帧移动 N 像素"的说法，
        # 都是在这个帧率下才有意义 —— 不限帧的话，同一份代码
        # 在快机器上会快得没法玩，在慢机器上又慢得像幻灯片。
        self.fps = 60

        self.screen_width = 1200
        self.screen_height = 800
        self.bg_color = (230, 230, 230)

        self.fleet_drop_speed = 10

        # 难度固定：清完一批外星人不再加速，也不再涨分。
        # 早期版本有 speedup_scale / score_scale（每清一批速度 ×1.1、分值 ×1.5），
        # 问题是分值涨得比升级门槛快，后期升级几乎白送，同时速度翻倍导致难以操作。
        # 现在难度只由 fleet_drop_speed（整队往下压的速度）决定。

        # 升级门槛：第 n 次升级需要的累计分数 = base × n × (n+1) ÷ 2
        #   n=1 -> 400    n=2 -> 1200    n=3 -> 2400    n=4 -> 4000
        # 即第 1 次差 400 分，之后每次再多差 400 分，越往后升级越慢。
        # 早期版本是 base × n（400 / 800 / 1200），增长太慢，后期升级过密。
        self.upgrade_score_base = 400

        # 进化成功的提示条显示多少帧（60 帧 = 1 秒）→ 150 帧 ≈ 2.5 秒
        self.evolution_banner_frames = 150

        # 视觉特效持续多少帧（60 帧 = 1 秒）。
        # 枪口闪光要短，拖长会一直贴在船头上；受伤红边要长一点，让玩家看清。
        self.muzzle_flash_frames = 7
        self.hit_flash_frames = 26

        # 外星人之间的间距倍数：每个外星人占的格子边长 = 外星人尺寸 × 这个数
        # 2 = 挨得比较近（教材布局）；调大更疏、更难打中
        self.fleet_spacing = 2.5

        # 每个外星人上下浮动的幅度（像素）和快慢。
        # 幅度设成 0 就完全关掉（变回"整队僵直地一起动"）
        self.alien_bob_amplitude = 9
        self.alien_bob_speed = 0.03

        # 外星人阵型的「不整齐」程度：
        #   0 = 完全对齐的方格（教材布局）
        #   1 = 抖到刚好贴住邻居，仍然不会重叠（几何上保证）
        self.fleet_jitter = 1.0

        # 每个格子有多大几率「空着不打仗」。
        # 没有它的话，即使抖动很厉害，一眼还是能看出「一行一行」；
        # 随机留几个空洞之后，看起来才像「随机出现」的。
        self.fleet_skip_chance = 0.3

        self.initialize_dynamic_settings()

    def upgrade_threshold(self, n):
        """第 n 次升级需要多少累计分。

        公式只写在这一处 —— 判定"该不该弹窗"（`_check_upgrade_threshold`）
        和 HUD 显示"还差多少分"（`scoreboard.prep_next_upgrade`）都调它。
        两处各抄一遍同一个公式，是"改了 A 忘了改 B"的经典来源。
        """
        return self.upgrade_score_base * n * (n + 1) // 2

    def initialize_dynamic_settings(self):
        """开新局时调用：把会被升级改动的数值全部复位。

        ⚠️ 规则：凡是升级会改的设置项，初始值必须写在这里，不能只写在 __init__。
        因为 __init__ 一个进程只跑一次，而一局游戏会跑很多次 ——
        写在 __init__ 里的值只有"第一局"能拿到，之后就是上一局留下的残渣。
        （曾经 bullets_allowed 和 ship_limit 就漏在这一条上，导致升级跨局累积）
        """
        self.ship_speed = 3.0
        self.bullet_speed = 3.0
        self.alien_speed = 1.0
        self.fleet_direction = 1

        # ---- 会被升级改动的项 ----
        self.bullets_allowed = 20  # MAGAZINE 会加
        self.ship_limit = 3  # EXTRA LIFE 会加
        self.bullets_per_shot = 1  # MULTI SHOT（1 → 2、3）
        self.bullets_pierce = False  # PHASE PIERCE
        self.auto_fire = False  # AUTO FIRE
        self.psionic_radius = 0  # PSIONIC STORM（0 = 没这个升级）
