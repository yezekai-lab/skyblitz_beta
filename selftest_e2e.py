"""端到端：用手柄事件驱动完整跑一段主循环（和 run_game 里的顺序完全一致）。"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
dir_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(dir_path)
sys.path.insert(0, dir_path)

import pygame

pygame.init()
import alien_invasion as m
from game_state import State

FIRE = pygame.JOYBUTTONDOWN
PAD_A = 0
PAD_START = 7


def step(game, frames=1):
    """照抄 run_game() 里那一圈，跑 frames 帧。"""
    for _ in range(frames):
        game.input.begin_frame()
        game._check_events()

        state_changed = game._handle_state_input()

        if not state_changed and game.state.world_moves:
            game.ship.update(game.input.read_direction())
            if game.input.fire_pressed:
                game._fire_bullet()
            game._update_aliens()
            game._update_bullets()

        game._update_screen()


g = m.AlienInvasion()
print(f"开局: state={g.state.name}  舰队={len(g.aliens)}")

# 只用手柄事件开局
pygame.event.post(pygame.event.Event(FIRE, button=PAD_A))
step(g)
print(f"按手柄 A 之后: state={g.state.name}  舰队={len(g.aliens)}")
assert g.state is State.PLAYING
assert len(g.bullets) == 0, "开始游戏那一帧不该射出子弹"
print("  [OK] 手柄 A 成功开局，且没顺带开火")

# 按住右方向键跑 60 帧
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
x0 = g.ship.x
step(g, 60)
print(f"  [OK] 按住右键 60 帧: x {x0} -> {g.ship.x}")
assert g.ship.x > x0
pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
step(g, 1)

# 手柄 A 开火
pygame.event.post(pygame.event.Event(FIRE, button=PAD_A))
step(g, 1)
print(f"  [OK] 游戏中按 A 射出子弹: {len(g.bullets)} 发")
assert len(g.bullets) == 1

# 手柄 Start 暂停
pygame.event.post(pygame.event.Event(FIRE, button=PAD_START))
step(g, 1)
print(f"  [OK] 手柄 Start 暂停: state={g.state.name}")
assert g.state is State.PAUSED

# 暂停期间世界必须冻住
snapshot = (g.ship.x, len(g.bullets), tuple(a.rect.x for a in g.aliens))
step(g, 60)
now = (g.ship.x, len(g.bullets), tuple(a.rect.x for a in g.aliens))
print(f"  [OK] 暂停 60 帧后世界完全冻住: {snapshot == now}")
assert snapshot == now

# 再按 Start 恢复
pygame.event.post(pygame.event.Event(FIRE, button=PAD_START))
step(g, 1)
print(f"  [OK] 再按 Start 恢复: state={g.state.name}")
assert g.state is State.PLAYING

# 恢复后世界继续动
step(g, 30)
print(f"  [OK] 恢复后外星人继续移动: {len(g.aliens)} 个在场")

# 长跑：600 帧不崩
step(g, 600)
print(
    f"  [OK] 再跑 600 帧无异常（分数={g.stats.score} 命数={g.stats.ship_left} 等级={g.stats.level}）"
)

pygame.quit()
print()
print("端到端全部通过")
