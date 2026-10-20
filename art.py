"""低多边形（low-poly）素材生成器。

=====================================================================
为什么用"代码画"而不是"下载素材"？

低多边形风格的本质就是「**平面多边形 + 每个面一个纯色**」——
它天生适合用代码画：不要贴图、不要光照计算、改风格只改几个坐标。
而且没有版权问题，也不怕老师在别的电脑上打开时素材丢失。

三个素材：
    make_ship()          飞船（神族风格：三角楔形 + 金边 + 灵能核心）
    make_bullet(pierce)  灵能弹（菱形晶体）
    make_alien(color)    外星人（六边形躯干 + 尖刺 + 三角眼）

所有坐标都用 0~1 的**归一化坐标**写，最后乘尺寸 ——
这样改大小只要改一个数字，形状不用重画。
=====================================================================
"""

import math

import pygame

# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _shade(color, factor):
    """把颜色变亮或变暗。factor > 1 变亮，< 1 变暗。

    低多边形风格靠"同一个色的几个明暗不同的面"来表现体积，
    所以这个函数会用得很多。
    """
    r, g, b = color[:3]
    return (
        min(255, int(r * factor)),
        min(255, int(g * factor)),
        min(255, int(b * factor)),
    )


def _pts(points, width, height, dx=0, dy=0, scale=1.0):
    """把归一化坐标 (0~1) 换算成像素坐标，顺便支持缩放和位移。"""
    cx = width * (1 - scale) / 2 + dx
    cy = height * (1 - scale) / 2 + dy
    return [(cx + x * width * scale, cy + y * height * scale) for x, y in points]


def _canvas(width, height):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    return surface


# ---------------------------------------------------------------------------
# 飞船：神族风格的三角楔形
#   形状参考《星际争霸 2》的侦察机 / 凤凰：尖头、后掠翼、中央能量核
# ---------------------------------------------------------------------------

# 外壳轮廓（顺时针，从机首开始）
SHIP_HULL = [
    (0.50, 0.02),  # 机首
    (0.66, 0.30),
    (0.80, 0.52),  # 右翼根
    (0.97, 0.78),  # 右翼尖
    (0.74, 0.86),
    (0.50, 0.72),  # 机尾中央
    (0.26, 0.86),
    (0.03, 0.78),  # 左翼尖
    (0.20, 0.52),  # 左翼根
    (0.34, 0.30),
]

# 左半边（用来上暗色，制造"光从右上打过来"的错觉）
SHIP_HULL_DARK = [
    (0.50, 0.02),
    (0.34, 0.30),
    (0.20, 0.52),
    (0.03, 0.78),
    (0.26, 0.86),
    (0.50, 0.72),
]

# 中央能量核（菱形）
SHIP_CORE = [(0.50, 0.24), (0.60, 0.44), (0.50, 0.62), (0.40, 0.44)]

HULL = (58, 68, 96)
HULL_LIGHT = (92, 108, 142)
GOLD = (206, 172, 92)
CORE_BRIGHT = (168, 232, 255)
CORE_MID = (96, 126, 232)
CORE_DARK = (58, 58, 158)


def make_ship(width=80, height=80, pods=1, piercing=False):
    """画一艘飞船。

    Args:
        pods:      「炮口」数量 —— 由 MULTI SHOT 升级决定（见 ship.py）。
                   1 = 没有额外炮口；2 = 两侧各一个；3 = 再加中央一个。
        piercing:  是否已经拿到 PHASE PIERCE —— 机身边缘会亮起来。
    """
    surf = _canvas(width, height)

    # ① 外壳：亮面打底
    pygame.draw.polygon(surf, HULL_LIGHT, _pts(SHIP_HULL, width, height))
    # ② 左半边压暗 → 立刻就"立体"了
    pygame.draw.polygon(surf, HULL, _pts(SHIP_HULL_DARK, width, height))
    # ③ 金边（神族的标志性装饰）
    trim = (232, 214, 150) if piercing else GOLD
    pygame.draw.polygon(surf, trim, _pts(SHIP_HULL, width, height), 2)

    # ④ 中央灵能核心：三块面，从亮到暗
    core = _pts(SHIP_CORE, width, height)
    pygame.draw.polygon(surf, CORE_MID, core)
    pygame.draw.polygon(
        surf,
        CORE_BRIGHT,
        _pts([(0.50, 0.24), (0.60, 0.44), (0.50, 0.44)], width, height),
    )
    pygame.draw.polygon(
        surf, CORE_DARK, _pts([(0.50, 0.62), (0.40, 0.44), (0.50, 0.44)], width, height)
    )

    # ⑤ 额外炮口（MULTI SHOT 的可视化）
    if pods >= 2:
        for px in (0.22, 0.78):
            pod = _pts(
                [
                    (px - 0.05, 0.40),
                    (px + 0.05, 0.40),
                    (px + 0.04, 0.58),
                    (px - 0.04, 0.58),
                ],
                width,
                height,
            )
            pygame.draw.polygon(surf, HULL_LIGHT, pod)
            pygame.draw.polygon(surf, trim, pod, 2)
    if pods >= 3:
        pod = _pts(
            [(0.46, 0.02), (0.54, 0.02), (0.53, 0.18), (0.47, 0.18)], width, height
        )
        pygame.draw.polygon(surf, CORE_BRIGHT, pod)

    return surf


def make_shield_ring(width=80, height=80, layers=1):
    """护盾环：套在飞船外面的一圈六边形。层数越多越亮。

    单独做成一张图，绘制时叠在飞船下面 —— 这样飞船的开火动作不受影响。

    ⚠️ 半径必须留在 0.5 以内：超出画布的部分会被**静默裁掉**
    （第一版就是写成 0.92+grow 超出去了，结果只剩几个碎角）。
    """
    surf = _canvas(width, height)
    radius = 0.42 + 0.025 * min(layers, 3)
    ring = []
    for i in range(6):
        angle = math.pi / 6 + i * math.pi / 3
        ring.append((0.5 + math.cos(angle) * radius, 0.5 + math.sin(angle) * radius))
    points = _pts(ring, width, height)

    alpha = min(70 + 45 * layers, 200)
    pygame.draw.polygon(surf, (90, 200, 255, alpha), points, 3)
    pygame.draw.polygon(surf, (170, 235, 255, alpha // 2), points, 1)
    return surf


# ---------------------------------------------------------------------------
# 子弹：灵能晶体
# ---------------------------------------------------------------------------

BULLET_SHARD = [(0.50, 0.00), (1.00, 0.42), (0.50, 1.00), (0.00, 0.42)]


def make_bullet(width=20, height=20, piercing=False):
    """画一发子弹。拿到 PHASE PIERCE 之后会变得更细更亮（"相位化"）。"""
    surf = _canvas(width, height)
    if piercing:
        outer, inner = (120, 220, 255), (240, 255, 255)
    else:
        outer, inner = (70, 110, 230), (150, 225, 255)

    pygame.draw.polygon(surf, outer, _pts(BULLET_SHARD, width, height))
    # 左半边压暗，做出晶体感
    pygame.draw.polygon(
        surf,
        _shade(outer, 0.65),
        _pts([(0.50, 0.00), (0.50, 1.00), (0.00, 0.42)], width, height),
    )
    pygame.draw.polygon(
        surf,
        inner,
        _pts([(0.50, 0.15), (0.72, 0.44), (0.50, 0.85), (0.28, 0.44)], width, height),
    )
    return surf


# ---------------------------------------------------------------------------
# 外星人：六边形躯干 + 尖刺 + 三角眼
# ---------------------------------------------------------------------------

ALIEN_BODY = [
    (0.50, 0.06),
    (0.78, 0.18),
    (0.94, 0.52),
    (0.70, 0.94),
    (0.30, 0.94),
    (0.06, 0.52),
    (0.22, 0.18),
]
ALIEN_BODY_DARK = [
    (0.50, 0.06),
    (0.22, 0.18),
    (0.06, 0.52),
    (0.30, 0.94),
    (0.50, 0.94),
]
ALIEN_SPIKES = [
    [(0.30, 0.20), (0.28, 0.00), (0.40, 0.14)],
    [(0.70, 0.20), (0.72, 0.00), (0.60, 0.14)],
]
EYES = [
    [(0.32, 0.42), (0.44, 0.50), (0.32, 0.60)],
    [(0.68, 0.42), (0.56, 0.50), (0.68, 0.60)],
]


def make_alien(color, width=60, height=60):
    """画一个外星人。`color` 就是它的主色（灰 / 绿 / 紫）。

    因为是程序化画的，**不需要染色** —— 直接按目标色算明暗就行了。
    """
    surf = _canvas(width, height)

    # ① 尖刺（先画，会被躯干压住根部）
    for spike in ALIEN_SPIKES:
        pygame.draw.polygon(surf, _shade(color, 0.55), _pts(spike, width, height))

    # ② 躯干：亮面打底 + 左半边压暗
    pygame.draw.polygon(surf, color, _pts(ALIEN_BODY, width, height))
    pygame.draw.polygon(surf, _shade(color, 0.62), _pts(ALIEN_BODY_DARK, width, height))
    pygame.draw.polygon(surf, _shade(color, 1.35), _pts(ALIEN_BODY, width, height), 2)

    # ③ 三角眼（低多边形的"眼"就是两个小三角）
    for eye in EYES:
        pygame.draw.polygon(surf, _shade(color, 0.25), _pts(eye, width, height))

    return surf
