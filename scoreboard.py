import pygame.font
from pygame.sprite import Group

from ship import Ship
from upgrades import RARITY_COLOR, Rarity


class Scoreboard:
    def __init__(self, ai_game):
        self.ai_game = ai_game
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()
        self.settings = ai_game.settings
        self.stats = ai_game.stats

        self.text_color = (30, 30, 30)
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 28)
        self.upgrade_images = []
        self.evolution_image = None
        self.prep_score()
        self.prep_high_score()
        self.prep_level()
        self.prep_next_upgrade()
        self.prep_ships()
        self.prep_shield()
        self.prep_overlays()

    def prep_score(self):
        rounded_score = round(self.stats.score, -1)
        score_str = "{:,}".format(rounded_score)
        self.score_image = self.font.render(
            score_str, True, self.text_color, self.settings.bg_color
        )

        self.score_rect = self.score_image.get_rect()
        self.score_rect.right = self.screen_rect.right - 20
        self.score_rect.top = 20

    def prep_score_and_next(self):
        """分数变了：分数图和"距下次升级"一起刷新。

        为什么不在 `prep_score()` 里顺手调 `prep_next_upgrade()`：
        "还差多少分"要排在【等级】下面，而构造对象时 `prep_level()` 还没跑
        （等级又要排在分数下面，两者本来就是有先后的）。
        与其在里面偷偷判断"排版好了没"，不如让调用方明确说清要刷新什么。
        """
        self.prep_score()
        self.prep_next_upgrade()

    def prep_next_upgrade(self):
        """右上角显示"离下一次升级还差多少分"。

        为什么值得加：升级门槛改成"越到后面越贵"之后，玩家在屏幕上
        完全看不到进度，只能干等 —— 不知道自己还要打多久，节奏感是断的。

        ⚠️ 这里**不存**"还差多少"这个值，每次现算：
        它就是 `门槛 - 当前分`，存下来就等于多一份会和分数不同步的副本。
        """
        game = self.ai_game
        pool = getattr(game, "upgrades", None)

        if pool is None or not pool.has_upgrades_left():
            # 全拿满了：没有"下一次"可言
            text = "NEXT  MAXED"
        else:
            remaining = max(0, game.next_upgrade_at() - self.stats.score)
            text = f"NEXT  {remaining:,}"

        self.next_upgrade_image = self.small_font.render(text, True, (70, 80, 110))
        self.next_upgrade_rect = self.next_upgrade_image.get_rect()
        self.next_upgrade_rect.right = self.score_rect.right
        self.next_upgrade_rect.top = self.level_rect.bottom + 8

    def prep_next_upgrade(self):
        """右上角显示"离下一次升级还差多少分"。

        为什么值得加：升级门槛改成"越到后面越贵"之后，玩家在屏幕上
        完全看不到进度，只能干等 —— 不知道自己还要打多久，节奏感是断的。

        ⚠️ 这里**不存**"还差多少"这个值，每次现算：
        它就是 `门槛 - 当前分`，存下来就等于多一份会和分数不同步的副本。
        """
        game = self.ai_game
        pool = getattr(game, "upgrades", None)

        if pool is None or not pool.has_upgrades_left():
            # 全拿满了 / 还没初始化好：没有"下一次"可言
            text = "NEXT  MAXED"
        else:
            remaining = max(0, game.next_upgrade_at() - self.stats.score)
            text = f"NEXT  {remaining:,}"

        self.next_upgrade_image = self.small_font.render(text, True, (70, 80, 110))
        self.next_upgrade_rect = self.next_upgrade_image.get_rect()
        self.next_upgrade_rect.right = self.score_rect.right
        self.next_upgrade_rect.top = self.level_rect.bottom + 8

    def show_score(self):
        self.screen.blit(self.score_image, self.score_rect)
        self.screen.blit(self.high_score_image, self.high_score_rect)
        self.screen.blit(self.level_image, self.level_rect)
        self.screen.blit(self.next_upgrade_image, self.next_upgrade_rect)
        if self.shield_image is not None:
            self.screen.blit(self.shield_image, self.shield_rect)
        self.ships.draw(self.screen)
        for image, rect in self.upgrade_images:
            self.screen.blit(image, rect)

    def prep_upgrades(self):
        """左下角列出已获得的升级（名字 + 等级）。

        为什么需要这个：飞船外观只能表现部分升级（炮口 / 金边 / 护盾），
        TIME WARP、AUTO FIRE 这类没地方画。所以还需要一份文字清单 ——
        这是“能分辨出自己拿了什么”最不会误判的方式。
        """
        self.upgrade_images = []
        pool = getattr(self.ai_game, "upgrades", None)
        if pool is None:
            return

        texts = []
        for upgrade in pool.definitions:
            level = pool.level_of(upgrade.key)
            if level:
                texts.append(f"{upgrade.title} Lv{level}")

        y = self.screen_rect.bottom - 12
        for text in reversed(texts):
            image = self.small_font.render(text, True, (70, 80, 110))
            rect = image.get_rect()
            rect.left = 12
            rect.bottom = y
            self.upgrade_images.append((image, rect))
            y = rect.top - 4

    def prep_evolution(self, title):
        """进化成功的提示条。只在进化那一刻渲染一次，别每帧做。

        文字单独画在一块深色底板上（而不是直接 blit）——
        背景色是浅灰 (230,230,230)，青白色的字打上去几乎看不见。
        """
        color = RARITY_COLOR[Rarity.ASCENDED]
        text = self.font.render(f"EVOLUTION  {title}", True, color)

        pad_x, pad_y = 22, 12
        panel = pygame.Surface(
            (text.get_width() + pad_x * 2, text.get_height() + pad_y * 2),
            pygame.SRCALPHA,
        )
        pygame.draw.rect(panel, (20, 24, 36, 225), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, color, panel.get_rect(), 2, border_radius=10)
        panel.blit(text, (pad_x, pad_y))

        self.evolution_image = panel
        self.evolution_rect = panel.get_rect(centerx=self.screen_rect.centerx, top=110)

    def show_evolution(self):
        """把提示条画出来。`evolution_image` 为 None 表示现在没有提示。"""
        if self.evolution_image is not None:
            self.screen.blit(self.evolution_image, self.evolution_rect)

    def prep_shield(self):
        """护盾层数。只在数值变了的时候调，不用每帧渲染。

        盾数为 0 时把 image 置为 None —— 这样显示代码只要判断"不是 None"，
        不用再去查一次 stats。
        """
        if self.stats.shield <= 0:
            self.shield_image = None
            return
        self.shield_image = self.font.render(
            f"SHIELD {self.stats.shield}", True, (70, 130, 220), self.settings.bg_color
        )
        self.shield_rect = self.shield_image.get_rect()
        self.shield_rect.right = self.score_rect.right
        self.shield_rect.top = self.level_rect.bottom + 10

    def prep_high_score(self):
        high_score = round(self.stats.high_score, -1)
        high_score_str = "{:,}".format(high_score)
        self.high_score_image = self.font.render(
            high_score_str, True, self.text_color, self.settings.bg_color
        )

        self.high_score_rect = self.high_score_image.get_rect()
        self.high_score_rect.centerx = self.screen_rect.centerx
        self.high_score_rect.top = self.score_rect.top

    def check_high_score(self):
        if self.stats.score > self.stats.high_score:
            self.stats.high_score = self.stats.score
            self.prep_high_score()

    def prep_level(self):
        level_str = str(self.stats.level)
        self.level_image = self.font.render(
            level_str, True, self.text_color, self.settings.bg_color
        )

        self.level_rect = self.level_image.get_rect()
        self.level_rect.right = self.score_rect.right
        self.level_rect.top = self.score_rect.bottom + 10

    def prep_ships(self):
        self.ships = Group()
        for ship_number in range(self.stats.ship_left):
            ship = Ship(self.ai_game)
            ship.rect.x = 10 + ship_number * ship.rect.width
            ship.rect.y = 10
            self.ships.add(ship)

    def prep_overlays(self):
        """预渲染暂停 / 结束 / 退出确认的提示。

        `font.render()` 每次都要重新画一遍字形，挺贵的；提示文字又是固定的，
        所以建对象时渲染一次就够，别每帧做。
        """
        self.paused_image, self.paused_rect = self._render_center_text("PAUSED")
        self.game_over_image, self.game_over_rect = self._render_center_text(
            "GAME OVER"
        )
        # "GAME OVER" 往上挪一点，免得和中间的 Play 按钮叠在一起
        self.game_over_rect.centery -= 80

        self.quit_image, self.quit_rect = self._render_center_text("QUIT?   Y / N")
        self.quit_hint_image = self.small_font.render(
            "press Y to quit,  N or ESC to keep playing", True, (235, 235, 235)
        )
        self.quit_hint_rect = self.quit_hint_image.get_rect(
            centerx=self.screen_rect.centerx, top=self.quit_rect.bottom + 16
        )

    def _render_center_text(self, text):
        image = self.font.render(text, True, (255, 255, 255))
        return image, image.get_rect(center=self.screen_rect.center)

    def show_paused(self):
        self.screen.blit(self.paused_image, self.paused_rect)

    def show_game_over(self):
        self.screen.blit(self.game_over_image, self.game_over_rect)

    def show_quit_confirm(self):
        self.screen.blit(self.quit_image, self.quit_rect)
        self.screen.blit(self.quit_hint_image, self.quit_hint_rect)
