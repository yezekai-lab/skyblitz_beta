import pygame
from pygame.sprite import Sprite

import art


class Ship(Sprite):
    """玩家飞船。

    外观会跟着升级变化 —— 这是"看得出来自己拿了什么"最直接的地方：
        额外炮口  <- MULTI SHOT（2 发 -> 两侧各一门；3 发 -> 再加中央一门）
        金边变亮  <- PHASE PIERCE
        外面一圈盾 <- PLASMA SHIELD（层数越多越亮）
    """

    def __init__(self, ai_game):
        super().__init__()
        self.game = ai_game
        self.settings = ai_game.settings
        self.screen = ai_game.screen
        self.screen_rect = self.screen.get_rect()

        self.image = art.make_ship(80, 80)
        self.rect = self.image.get_rect()
        self.shield_image = None
        self._look_key = None

        self.center_ship()

    def blitme(self):
        self._sync_look()
        if self.shield_image is not None:
            self.screen.blit(self.shield_image, self.rect)
        self.screen.blit(self.image, self.rect)

    def _sync_look(self):
        """升级变了才重画外观，没变就直接用缓存。"""
        key = (
            self.settings.bullets_per_shot,
            self.settings.bullets_pierce,
            self.game.stats.shield,
        )
        if key == self._look_key:
            return
        self._look_key = key

        pods, piercing, shields = key
        self.image = art.make_ship(
            self.rect.width, self.rect.height, pods=pods, piercing=piercing
        )
        if shields > 0:
            self.shield_image = art.make_shield_ring(
                self.rect.width, self.rect.height, shields
            )
        else:
            self.shield_image = None

    def update(self, direction):
        """按 direction 移动：-1.0 全速左 ~ +1.0 全速右，0 表示不动。

        原来是 moving_right / moving_left 两个布尔量，现在合成一个连续的值 ——
        因为手柄摇杆推多深是有中间档的。
        """
        if not direction:
            return
        self.x += self.settings.ship_speed * direction
        self.rect.x = self.x
        self._keep_in_screen()

    def _keep_in_screen(self):
        """撞到左右边界就贴住。

        ⚠️ 只有**真的贴住边界**时才把浮点累加器同步回来。没贴住就绝不碰
        self.x —— 否则每帧都会把 self.x 舍入成整数，精度一丢，慢速移动
        （比如 0.5 像素/帧）就会彻底失效。两个状态该同步的时候才同步。
        """
        if self.rect.left < self.screen_rect.left:
            self.rect.left = self.screen_rect.left
        elif self.rect.right > self.screen_rect.right:
            self.rect.right = self.screen_rect.right
        else:
            return
        self.x = float(self.rect.x)

    def center_ship(self):
        self.rect.midbottom = self.screen_rect.midbottom
        self.x = float(self.rect.x)
