"""三选一界面的无头测试：触发、选卡、状态流转。"""

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

ok = 0
fail = 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK]   {name} {extra}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {extra}")


def press(game, key):
    """按一帧完整的流程：清标记 -> 处理事件 -> 按状态解释意图。

    ⚠️ 三步缺一不可。只调用 _check_events() 只是把事件翻译成了意图，
    真正"按状态解释意图"的是 _handle_state_input()。
    """
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
    game.input.begin_frame()
    game._check_events()
    game._handle_state_input()


print("=" * 62)
print("① 分数触发")
print("=" * 62)
random.seed(11)
g = m.AlienInvasion()
g._start_game()
base = g.settings.upgrade_score_base

g.stats.score = base - 1
g._check_upgrade_threshold()
check(f"分数 {base - 1}（不够 {base}）-> 不弹", g.state is State.PLAYING)

g.stats.score = base
g._check_upgrade_threshold()
check(f"分数 {base} -> 弹三选一", g.state is State.UPGRADING)
check(
    "抽出了 3 张卡",
    len(g.upgrade_screen.choices) == 3,
    f"(实际 {len(g.upgrade_screen.choices)})",
)
check("三张卡的 key 不重复", len({c.key for c in g.upgrade_screen.choices}) == 3)
check("UPGRADING 时世界该冻住（world_moves=False）", g.state.world_moves is False)

print()
print("=" * 62)
print("② 选卡：数字键 / 方向键 / 确认键")
print("=" * 62)
target = g.upgrade_screen.choices[1]
press(g, pygame.K_2)
check("按 2 之后回到 PLAYING", g.state is State.PLAYING)
check(f"选中的是第 2 张（{target.key}）", g.upgrades.level_of(target.key) == 1)
check("升级计数 +1", g._upgrade_count == 1, f"(实际 {g._upgrade_count})")
check("选择界面已关闭", g.upgrade_screen is None)

# 第二次触发：门槛按 base×n×(n+1)÷2 算，n=2 → 3×base = 1200
second_needed = base * 2 * 3 // 2
g.stats.score = second_needed
g._check_upgrade_threshold()
check(
    f"第 2 次需要 {second_needed} 分 -> 已经够了",
    g.state is State.UPGRADING,
    f"(state={g.state.name})",
)

before = g.upgrade_screen.index
press(g, pygame.K_RIGHT)
check(
    "方向键右 -> 高亮右移一格",
    g.upgrade_screen.index == (before + 1) % 3,
    f"({before} -> {g.upgrade_screen.index})",
)
press(g, pygame.K_LEFT)
press(g, pygame.K_LEFT)
check(
    "方向键左会绕回去（不会越界）",
    0 <= g.upgrade_screen.index < 3,
    f"(index = {g.upgrade_screen.index})",
)

highlighted = g.upgrade_screen.highlighted_choice()
press(g, pygame.K_RETURN)
check("回车 -> 选中当前高亮的那张", g.upgrades.level_of(highlighted.key) >= 1)
check("状态回到 PLAYING", g.state is State.PLAYING)

print()
print("=" * 62)
print("③ 鼠标点卡")
print("=" * 62)


def needed_to_pop(g):
    """下一次升级要多少分（照抄 _check_upgrade_threshold 的算法）。

    测试里必须用同一个公式，不能写死 800 / 1200 —— 门槛规则一改，
    写死的数字就会变成"看起来在测、其实测的是别的东西"。
    """
    n = g._upgrade_count + 1
    return g.settings.upgrade_score_base * n * (n + 1) // 2


g.stats.score = needed_to_pop(g)
g._check_upgrade_threshold()
rect = g.upgrade_screen.rects[0]
clicked = g.upgrade_screen.choices[0]
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1))
g.input.begin_frame()
g._check_events()
check("点第 1 张卡 -> 选中的就是它", g.upgrades.level_of(clicked.key) >= 1)
check("状态回到 PLAYING", g.state is State.PLAYING)

# 点在卡片外面不应该选走
g.stats.score = needed_to_pop(g)
g._check_upgrade_threshold()
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(5, 5), button=1))
g.input.begin_frame()
g._check_events()
check("点在卡片外面 -> 还停在选择界面", g.state is State.UPGRADING)

print()
print("=" * 62)
print("④ 全拿满之后就不再弹了")
print("=" * 62)
g2 = m.AlienInvasion()
g2._start_game()
for u in g2.upgrades.definitions:
    for _ in range(u.max_level):
        g2.upgrades.take(u.key)
g2.stats.score = 999999
g2._check_upgrade_threshold()
check(
    "全部满级后，分数再高也不弹（不会卡死）",
    g2.state is State.PLAYING,
    f"(实际 {g2.state.name})",
)

print()
print("=" * 62)
print("⑤ 新一局：升级必须清空")
print("=" * 62)
g3 = m.AlienInvasion()
g3._start_game()
g3.stats.score = g3.settings.upgrade_score_base
g3._check_upgrade_threshold()
kind = g3.upgrade_screen.choices[0].key
g3.upgrade_screen.index = 0
g3._take_upgrade()
check("这一局拿了 1 个升级", g3.upgrades.levels != {})
g3._start_game()
check("开新局后升级清空", g3.upgrades.levels == {}, f"(残留 {g3.upgrades.levels})")
check("开新局后升级计数归零", g3._upgrade_count == 0)

pygame.quit()
print()
print("=" * 62)
print(f"结果：{ok} 项通过, {fail} 项失败")
print("=" * 62)
sys.exit(1 if fail else 0)
