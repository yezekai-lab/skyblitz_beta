import math
import random

import pygame
from pygame.sprite import Sprite

import art

# 外星人的三种型号：分越高越稀有（weight 是相对权重，不是百分比）
#   灰色 50 分 ×60 / 绿色 100 分 ×30 / 紫色 200 分 ×10
ALIEN_TYPES = (
    {"color": (150, 150, 150), "points": 50, "weight": 60},
    {"color": (60, 200, 110), "points": 100, "weight": 30},
    {"color": (170, 90, 230), "points": 200, "weight": 10},
)
_WEIGHTS = [t["weight"] for t in ALIEN_TYPES]

# 颜色 -> 已染好色的图片。同类外星人共用同一张 Surface
_image_cache = {}


def pick_type():
    """随机挑一种型号（按权重）。分值高的更少见。"""
    return random.choices(ALIEN_TYPES, weights=_WEIGHTS, k=1)[0]


def image_for(color):
    """取（必要时才画，然后缓存）某个颜色的外星人图片。

    低多边形素材是代码画的，所以不用“染色”那套。
    但还是加一层缓存：一队十几个外星人共用同一张 Surface，
    不必每造一个都重画一遍多边形。

    这个函数对同一个 color 永远返回同一个结果，所以缓存是安全的。
    """
    if color not in _image_cache:
        _image_cache[color] = art.make_alien(color)
    return _image_cache[color]


class Alien(Sprite):
    def __init__(self, ai_game):
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings

        alien_type = pick_type()
        self.points = alien_type["points"]
        self.image = image_for(alien_type["color"])
        self.rect = self.image.get_rect()

        self.rect.x = self.rect.width
        self.rect.y = self.rect.height

        self.x = float(self.rect.x)

        # 纵向位置的真身是 base_y（自己那一行的基准线），rect.y 是由它算出来的。
        # 整队下移时改的是 base_y，不是 rect.y —— 这样"浮动"才不会把它冲掉。
        self.base_y = self.rect.y

        # 每个外星人自己的"呼吸"相位。因为起点随机，它们不会一起动。
        self.bob_phase = random.uniform(0, math.tau)

    def place(self, x, y):
        """把外星人摆到 (x, y)。

        位置和"基准线"必须一起设 —— 分开设就会出现"改了位置没改基准线"
        这种不一致（本项目已经因为"两个状态分开赋值"栽过好几次了）。
        """
        self.rect.x = x
        self.x = float(x)
        self.base_y = y
        self.rect.y = y

    def check_edges(self):
        screen_rect = self.screen.get_rect()
        if self.rect.right >= screen_rect.right or self.rect.left <= 0:
            return True
        return False

    def update(self):
        # 横向：整队一起走
        self.x += self.settings.alien_speed * self.settings.fleet_direction
        self.rect.x = self.x

        # 纵向：在基准线附近轻轻上下浮动。
        # 每个外星人的相位不同 → 屏幕上看起来是"一个个怪在动"，
        # 而不是"一整块一起平移"。
        self.bob_phase += self.settings.alien_bob_speed
        self.rect.y = self.base_y + int(
            math.sin(self.bob_phase) * self.settings.alien_bob_amplitude
        )
