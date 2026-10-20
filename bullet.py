import pygame

from pygame.sprite import Sprite

import art

# 两种子弹（普通 / 相位化）各只需一张图，用字典缓存起来
_BULLET_IMAGES = {}


def _bullet_image(piercing):
    if piercing not in _BULLET_IMAGES:
        _BULLET_IMAGES[piercing] = art.make_bullet(20, 20, piercing)
    return _BULLET_IMAGES[piercing]


class Bullet(Sprite):
    def __init__(self, ai_game):
        super().__init__()
        self.settings = ai_game.settings

        self.image = _bullet_image(self.settings.bullets_pierce)
        self.rect = self.image.get_rect()

        self.speed = self.settings.bullet_speed

        self.rect.midtop = ai_game.ship.rect.midtop

        self.y = float(self.rect.y)

    def update(self):
        self.y -= self.speed
        self.rect.y = self.y
