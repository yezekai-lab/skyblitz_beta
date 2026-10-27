import pygame.font

# 配色：和升级卡上的 ASCENDED 同一个青白色系，让整个游戏看起来是一套
ACCENT = (110, 231, 219)


class Button:
    """开始界面中间那个 PLAY 按钮。

    设计上做了三件事：
        1. 深色圆角面板 + 亮色描边 —— 在浅灰背景上立得起来，不像一块"色块"
        2. 鼠标移上去：面板变亮、描边变白变粗、外面多一圈光晕
        3. 两套状态**预渲染成两张图**，每帧只 blit，不重画图形

    第 3 点很重要：`pygame.draw` 每帧重画几十个元素，在 60 帧下就是几千次调用。
    按钮的样子只随"悬停与否"变化，所以最多只需要两张图。
    """

    WIDTH = 264
    HEIGHT = 76
    RADIUS = 14
    GLOW = 12  # 外发光需要额外留出的边距（图比按钮本身大一圈）

    def __init__(self, ai_game, msg):
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()
        self.font = pygame.font.Font(None, 56)

        # ⚠️ rect 决定"点哪里算点到按钮"，点击判定和测试都靠它 —— 位置尺寸保持不变
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self.rect.center = self.screen_rect.center

        self.hover = False
        self.image_normal = self._render(msg, hover=False)
        self.image_hover = self._render(msg, hover=True)
        self.image_rect = self.image_normal.get_rect(center=self.rect.center)

    def _render(self, msg, hover):
        """把按钮画成一张图。图的尺寸比 rect 大一圈，多出来的是发光和投影的位置。"""
        box = pygame.Surface(
            (self.WIDTH + self.GLOW * 2, self.HEIGHT + self.GLOW * 2),
            pygame.SRCALPHA,
        )
        panel = pygame.Rect(self.GLOW, self.GLOW, self.WIDTH, self.HEIGHT)

        # ① 投影：背景是浅灰的，没有它按钮就像一张贴纸，浮不起来
        #    ⚠️ alpha 必须"贴着按钮最深、越往外越淡"。
        #    反过来写（外圈最深）看起来就不是阴影，而是一圈灰色边框。
        shadow = panel.move(0, 7)
        for i in range(8, 0, -1):  # 8 = 最外圈，1 = 贴着按钮
            pygame.draw.rect(
                box,
                (16, 22, 34, 6 + (8 - i) * 4),
                shadow.inflate(i * 2, i * 2),
                border_radius=self.RADIUS + i,
            )

        # ② 外发光：只有悬停时才画，越往外越淡
        #    在 SRCALPHA 上 pygame.draw 是直接写入、不做混合，
        #    所以从大到小画，最内层自然会盖住外层 —— 这就是"渐变"的来源
        if hover:
            for i in range(self.GLOW, 0, -1):
                alpha = int(150 * (1 - i / self.GLOW)) + 20
                pygame.draw.rect(
                    box,
                    (*ACCENT, alpha),
                    panel.inflate(i * 2, i * 2),
                    border_radius=self.RADIUS + i,
                )

        # ③ 面板本体
        fill = (58, 72, 102) if hover else (30, 36, 52)
        pygame.draw.rect(box, fill, panel, border_radius=self.RADIUS)

        # ④ 内侧细线：给平面一点层次，没有它就只是个纯色块
        pygame.draw.rect(
            box,
            (82, 98, 130),
            panel.inflate(-10, -10),
            1,
            border_radius=max(2, self.RADIUS - 5),
        )

        # ⑤ 描边：悬停时更亮更粗
        pygame.draw.rect(
            box,
            (255, 255, 255) if hover else ACCENT,
            panel,
            3 if hover else 2,
            border_radius=self.RADIUS,
        )

        # ⑥ 文字
        color = (255, 255, 255) if hover else ACCENT
        label = self.font.render(msg.upper(), True, color)
        box.blit(label, label.get_rect(center=panel.center))

        return box

    def update_hover(self, mouse_pos):
        """鼠标动了：更新"是不是悬停"。返回状态有没有变化。"""
        hover = self.rect.collidepoint(mouse_pos)
        changed = hover != self.hover
        self.hover = hover
        return changed

    def draw_button(self):
        image = self.image_hover if self.hover else self.image_normal
        self.screen.blit(image, self.image_rect)
