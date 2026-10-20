"""三选一升级界面：把几张卡片摆到屏幕上，并处理「选哪张」。

=====================================================================
这个模块**只管画面和"鼠标/方向键落在哪张卡上"**，
不管"选了之后怎么生效" —— 那是 `upgrades.UpgradePool.take()` 的事。

分工：
    upgrades.py        有哪些升级、抽哪几个、选了怎么生效
    upgrade_screen.py  长什么样、高亮哪张、点在哪个矩形里
    alien_invasion.py  什么时候弹出来、选完切回什么状态
=====================================================================
"""

import pygame
from pygame import Rect

from upgrades import RARITY_COLOR


def _wrap_text(text, font, max_width):
    """把一段话按宽度折行。

    英文按空格切词。这是最朴素的做法，够用了 ——
    卡片上的说明都很短，不需要处理连字符断词那种复杂情况。
    """
    lines = []
    current = ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class UpgradeScreen:
    """一屏"三选一"。

    Args:
        choices:     要展示的升级（`UpgradePool.available(3)` 的返回值）
        screen_rect: 屏幕矩形，用来居中排版
    """

    CARD_W = 320
    CARD_H = 340
    GAP = 40

    def __init__(self, choices, screen_rect):
        self.choices = list(choices)
        # 手柄/键盘用方向键移动的"当前高亮"
        self.index = 0

        self.title_font = pygame.font.Font(None, 46)
        self.detail_font = pygame.font.Font(None, 26)
        self.tag_font = pygame.font.Font(None, 24)

        self.rects = self._layout(screen_rect)

        # 压暗背景的幕布，只建一次
        self.backdrop = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
        self.backdrop.fill((8, 10, 20, 175))

    # ------------------------------------------------------------------
    # 排版
    # ------------------------------------------------------------------
    def _layout(self, screen_rect):
        count = len(self.choices)
        if count == 0:
            return []
        total = count * self.CARD_W + (count - 1) * self.GAP
        left = screen_rect.centerx - total // 2
        top = screen_rect.centery - self.CARD_H // 2 + 20
        return [
            Rect(left + i * (self.CARD_W + self.GAP), top, self.CARD_W, self.CARD_H)
            for i in range(count)
        ]

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def move(self, delta):
        """把高亮往左/往右挪一格（到头会绕回去）。"""
        if self.choices:
            self.index = (self.index + delta) % len(self.choices)

    def highlight_at(self, pos, margin=0):
        """鼠标悬停时把高亮跟过去。返回是否发生了变化。"""
        index = self.index_at(pos, margin)
        if index is not None and index != self.index:
            self.index = index
            return True
        return False

    def index_at(self, pos, margin=0):
        """某个坐标落在第几张卡上；没落在任何卡上返回 None。

        `margin` 给鼠标留一点容错（点偏一点点也算）。
        """
        for i, rect in enumerate(self.rects):
            if rect.inflate(margin, margin).collidepoint(pos):
                return i
        return None

    def highlighted_choice(self):
        """当前高亮的那张卡（没有可选的就返回 None）。"""
        if not self.choices:
            return None
        return self.choices[self.index]

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw(self, screen, screen_rect):
        screen.blit(self.backdrop, (0, 0))

        heading = self.title_font.render("CHOOSE AN UPGRADE", True, (236, 240, 255))
        screen.blit(heading, heading.get_rect(centerx=screen_rect.centerx, top=90))

        for i, (choice, rect) in enumerate(zip(self.choices, self.rects)):
            self._draw_card(
                screen, choice, rect, highlighted=(i == self.index), number=i + 1
            )

        hint = self.tag_font.render(
            "1 / 2 / 3   or   click   or   D-pad + A", True, (150, 160, 190)
        )
        screen.blit(
            hint,
            hint.get_rect(centerx=screen_rect.centerx, bottom=screen_rect.bottom - 70),
        )

    def _draw_card(self, screen, upgrade, rect, highlighted, number):
        color = RARITY_COLOR.get(upgrade.rarity, (200, 200, 200))

        # ① 底板
        pygame.draw.rect(screen, (26, 30, 46), rect, border_radius=12)
        # ② 顶部稀有度色条
        band = Rect(rect.left, rect.top, rect.width, 10)
        pygame.draw.rect(
            screen, color, band, border_top_left_radius=12, border_top_right_radius=12
        )
        # ③ 边框：高亮时更粗更亮
        if highlighted:
            pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=12)
            pygame.draw.rect(screen, color, rect.inflate(-10, -10), 3, border_radius=10)
        else:
            pygame.draw.rect(screen, color, rect, 2, border_radius=12)

        # ④ 稀有度标签
        tag = self.tag_font.render(upgrade.rarity.name, True, color)
        screen.blit(tag, (rect.left + 20, rect.top + 24))

        # ⑤ 标题（长了就缩字号）
        title = self.title_font.render(upgrade.title, True, (245, 248, 255))
        if title.get_width() > rect.width - 40:
            title = pygame.transform.smoothscale(
                title,
                (
                    rect.width - 40,
                    title.get_height() * (rect.width - 40) // title.get_width(),
                ),
            )
        screen.blit(title, (rect.left + 20, rect.top + 58))

        # ⑥ 说明（自动折行）
        y = rect.top + 112
        for line in _wrap_text(upgrade.detail, self.detail_font, rect.width - 40):
            image = self.detail_font.render(line, True, (188, 196, 220))
            screen.blit(image, (rect.left + 20, y))
            y += 26

        # ⑦ 按键提示
        key_hint = self.tag_font.render(f"PRESS {number}", True, color)
        screen.blit(key_hint, (rect.left + 20, rect.bottom - 40))
