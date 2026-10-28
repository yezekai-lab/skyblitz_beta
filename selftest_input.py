"""输入层（InputManager + Ship 连续移动 + 暂停）的无头测试。"""

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
from input_manager import InputManager

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


def ev(kind, **kw):
    return pygame.event.Event(kind, **kw)


print("=" * 64)
print("① 摇杆死区换算（纯函数，可以脱离手柄测）")
print("=" * 64)
adz = InputManager.apply_dead_zone
check("中心 0.0 -> 0.0", adz(0.0) == 0.0)
check("死区内的抖动 +0.2 -> 0.0", adz(0.2) == 0.0)
check("死区内的抖动 -0.2 -> 0.0", adz(-0.2) == 0.0)
check("刚好 0.25（边界）-> 0.0", adz(0.25) == 0.0)
check("刚出死区 0.26 -> 很小的一步", 0 < adz(0.26) < 0.05, f"(得 {adz(0.26):.4f})")
check("推到一半 0.5 -> 约 0.33", abs(adz(0.5) - 0.3333) < 0.001, f"(得 {adz(0.5):.4f})")
check("推到底 +1.0 -> +1.0", adz(1.0) == 1.0)
check("推到底 -1.0 -> -1.0", adz(-1.0) == -1.0)
check("方向没被搞反", adz(-0.9) < 0 < adz(0.9))

print()
print("=" * 64)
print("② 键盘 → 意图")
print("=" * 64)
g = m.AlienInvasion()
has_pad = g.input.has_joystick
print(
    f"  [{'OK' if has_pad else '--'}]   手柄当前{'已连接' if has_pad else '未连接（蓝牙休眠了，按一下 Xbox 键唤醒）'}"
)
if has_pad:
    ok += 1

check("没按任何键 -> 0.0", g.input.read_direction() == 0.0)

g.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_RIGHT))
check("按右键 -> +1.0", g.input.read_direction() == 1.0)
g.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_LEFT))
check("左右同按 -> 0.0（互相抵消）", g.input.read_direction() == 0.0)
g.input.handle_event(ev(pygame.KEYUP, key=pygame.K_RIGHT))
check("松开右、仍按左 -> -1.0", g.input.read_direction() == -1.0)
g.input.handle_event(ev(pygame.KEYUP, key=pygame.K_LEFT))
check("全松开 -> 0.0", g.input.read_direction() == 0.0)

print()
print("=" * 64)
print("③ 边沿触发：按一次只算一次")
print("=" * 64)
g.input.begin_frame()
g.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_SPACE))
check("按下空格 -> fire_pressed True", g.input.fire_pressed is True)
g.input.begin_frame()
check("下一帧自动清零", g.input.fire_pressed is False)

g.input.begin_frame()
g.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_p))
check("按下 P -> pause_pressed True", g.input.pause_pressed is True)
g.input.begin_frame()
check("下一帧自动清零", g.input.pause_pressed is False)

g.input.begin_frame()
g.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_RETURN))
check("按下回车 -> confirm_pressed True", g.input.confirm_pressed is True)
check("回车不该开火", g.input.fire_pressed is False)
g.input.begin_frame()
check("confirm 也会被自动清零", g.input.confirm_pressed is False)

g.input.begin_frame()
g.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_SPACE))
check(
    "空格 -> confirm 和 fire 同时为 True",
    g.input.confirm_pressed and g.input.fire_pressed,
)

print()
print("=" * 64)
print("④ 手柄按钮也要能触发同样的意图（用假事件模拟按键）")
print("=" * 64)
g.input.begin_frame()
g.input.handle_event(ev(pygame.JOYBUTTONDOWN, button=0))  # A 键
check("手柄 A 键 -> confirm_pressed True", g.input.confirm_pressed is True)
check("手柄 A 键 -> fire_pressed True", g.input.fire_pressed is True)
g.input.begin_frame()
g.input.handle_event(ev(pygame.JOYBUTTONDOWN, button=7))  # Start 键
check("手柄 Start 键 -> pause_pressed True", g.input.pause_pressed is True)
g.input.begin_frame()
g.input.handle_event(ev(pygame.JOYBUTTONDOWN, button=13))  # 随便一个无关键
check(
    "无关按钮 -> 什么都不触发", not g.input.fire_pressed and not g.input.pause_pressed
)

print()
print("=" * 64)
print("⑤ 真实手柄的当前读数")
print("=" * 64)
if g.input.has_joystick:
    pygame.event.pump()
    raw = g.input.joystick.get_axis(0)
    stick = g.input._joystick_direction()
    print(f"  左摇杆原始值 = {raw:+.4f}")
    check("静止时摇杆不产生移动意图", stick == 0.0, f"(意图 {stick:+.4f})")
else:
    print("  [--]   跳过：现在没连手柄")
    print("         唤醒手柄后重跑本脚本，这一段会真的去读摇杆数值")

print()
print("=" * 64)
print("⑥ 连续移动：浮点精度必须保住")
print("=" * 64)
g._check_play_button(g.play_button.rect.center)
g.ship.center_ship()
x0 = g.ship.x
speed = g.settings.ship_speed
for _ in range(3):
    g.ship.update(1.0)
expected = x0 + speed * 3
check(
    f"连走 3 帧 = 精确累积 3×{speed}",
    g.ship.x == expected,
    f"({x0} -> {g.ship.x}, 期望 {expected})",
)
check(
    "rect 只是取整（误差 ≤ 0.5），不污染累加器",
    abs(g.ship.rect.x - expected) <= 0.5,
    f"(rect.x = {g.ship.rect.x}, 累加器 = {g.ship.x})",
)

print()
print("=" * 64)
print("⑦ 摇杆推杆幅度 -> 速度成比例")
print("=" * 64)
g.ship.center_ship()
x0 = g.ship.x
g.ship.update(1.0)
full = g.ship.x - x0
g.ship.center_ship()
x0 = g.ship.x
g.ship.update(0.5)
half = g.ship.x - x0
check("半推 ≈ 全推的一半", abs(half * 2 - full) < 0.001, f"(全推 {full}, 半推 {half})")
g.ship.center_ship()
x0 = g.ship.x
g.ship.update(-1.0)
check("反向推 -> 往左走", g.ship.x < x0, f"({x0} -> {g.ship.x})")

print()
print("=" * 64)
print("⑧ 边界：贴住之后不会越界，也不会抖动")
print("=" * 64)
g.ship.center_ship()
for _ in range(1000):
    g.ship.update(1.0)
check("一直往右 -> 正好贴住右边界", g.ship.rect.right == g.screen.get_rect().right)
x_right = g.ship.x
for _ in range(10):
    g.ship.update(1.0)
check("继续按右 -> 位置不再变化", g.ship.x == x_right, f"({x_right})")
for _ in range(2000):
    g.ship.update(-1.0)
check("一直往左 -> 正好贴住左边界", g.ship.rect.left == g.screen.get_rect().left)
x_left = g.ship.x
for _ in range(10):
    g.ship.update(-1.0)
check("继续按左 -> 位置不再变化", g.ship.x == x_left, f"({x_left})")

print()
print("=" * 64)
print("⑨ 暂停：状态切换 + 画面")
print("=" * 64)
g.state = State.READY
g._toggle_pause()
check("READY 时按暂停 -> 无效", g.state is State.READY)

g.state = State.PLAYING
g._toggle_pause()
check("PLAYING 时按暂停 -> PAUSED", g.state is State.PAUSED)
g._toggle_pause()
check("再按一次 -> 回到 PLAYING", g.state is State.PLAYING)

# 其他状态下按暂停都不该有反应
g.state = State.GAME_OVER
g._toggle_pause()
check("GAME_OVER 时按暂停 -> 无效", g.state is State.GAME_OVER)
g.state = State.UPGRADING
g._toggle_pause()
check("UPGRADING 时按暂停 -> 无效（选升级时不能被暂停）", g.state is State.UPGRADING)

# 状态自己知道该怎么表现
g.state = State.PLAYING
g.state = State.PAUSED
pos = g.ship.x
g.ship.update(0.0)
check("暂停时移动意图为 0 -> 飞船不动", g.ship.x == pos)
g._update_screen()
check("绘制暂停画面（黑幕 + PAUSED）无异常", True)
g.state = State.GAME_OVER
g._update_screen()
check("绘制结束画面（黑幕 + GAME OVER + Play 按钮）无异常", True)
g.state = State.READY

print()
print("=" * 64)
print("⑩ 手柄断开不能崩")
print("=" * 64)
g.input.joystick = None
check("没有手柄时 read_direction 返回 0.0", g.input.read_direction() == 0.0)
check("没有手柄时 has_joystick 为 False", g.input.has_joystick is False)
g.input.handle_event(ev(pygame.JOYBUTTONDOWN, button=0))
check("没有手柄时收到手柄事件也不崩", g.input.fire_pressed is True)

g.input.begin_frame()
g.input.handle_event(ev(pygame.JOYDEVICEREMOVED, device_index=0))
check("拔掉手柄事件 -> 引用被清空", g.input.joystick is None)
g.input.handle_event(ev(pygame.JOYDEVICEADDED, device_index=0))
check(
    "插上手柄事件 -> 不崩，且状态和真实设备数一致",
    g.input.has_joystick == (pygame.joystick.get_count() > 0),
)
print(
    "     （手柄会自己休眠 -> 醒来时 SDL 报 JOYDEVICEADDED，" "这段逻辑就是为它准备的）"
)

print()
print("=" * 64)
print("⑪ 完整跑一帧（模拟主循环那一圈）")
print("=" * 64)
g2 = m.AlienInvasion()
g2._check_play_button(g2.play_button.rect.center)
frames = 0
for _ in range(60):
    g2.input.begin_frame()
    g2._check_events()
    if not g2._handle_state_input() and g2.state.world_moves:
        g2.ship.update(g2.input.read_direction())
        if g2.input.fire_pressed:
            g2._fire_bullet()
        g2._update_aliens()
        g2._update_bullets()
    g2._update_screen()
    frames += 1
check("连跑 60 帧主循环无异常", frames == 60)
check("外星人还在（没被误伤清空）", len(g2.aliens) > 0, f"(剩 {len(g2.aliens)})")

# 跑一整圈的暂停 + 恢复
g2.input.begin_frame()
g2.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_p))
g2._handle_state_input()
check("用键盘 P 暂停成功", g2.state is State.PAUSED)
aliens_before = len(g2.aliens)
for _ in range(30):
    g2.input.begin_frame()
    g2._check_events()
    if not g2._handle_state_input() and g2.state.world_moves:
        g2._update_aliens()
    g2._update_screen()
check("暂停期间外星人数量不变（世界真的冻住了）", len(g2.aliens) == aliens_before)
g2.input.begin_frame()
g2.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_p))
g2._handle_state_input()
check("再按 P 恢复", g2.state is State.PLAYING)

print()
print("=" * 64)
print("输入法兼容：字母键必须能到达游戏")
print("=" * 64)

# 真实踩到的 bug：中文输入法（微软拼音）处于中文状态时，字母键会被输入法
# 截走，窗口收不到 KEYDOWN —— 表现就是"按 P 暂停没反应"，而空格/ESC 正常。
# 修法是启动时关掉 SDL 的文本输入（本游戏不需要输入文字）。

from unittest import mock

with mock.patch.object(pygame.key, "stop_text_input") as mocked:
    InputManager()
check(
    "创建输入层时会关闭文本输入（否则字母键被输入法吃掉）",
    mocked.called,
    f"(调用 {mocked.call_count} 次)",
)

# 关掉之后，字母键要能被正确翻译成意图
g3 = m.AlienInvasion()
g3._start_game()
for key, attr in (
    (pygame.K_p, "pause_pressed"),
    (pygame.K_y, "yes_pressed"),
    (pygame.K_n, "no_pressed"),
    (pygame.K_ESCAPE, "escape_pressed"),
):
    g3.input.begin_frame()
    g3.input.handle_event(ev(pygame.KEYDOWN, key=key))
    check(
        f"按键 {pygame.key.name(key).upper()} 能翻译成 {attr}",
        getattr(g3.input, attr) is True,
    )

print()
print("=" * 64)
print("焦点丢失：正在按着的键必须松开")
print("=" * 64)

# 按住方向键时 Alt+Tab 切走，KEYUP 不会再来 —— 不清空的话
# 切回来飞船会一直朝一个方向飘，看起来像"按键卡住了"。
g4 = m.AlienInvasion()
g4._start_game()
g4.input.begin_frame()
g4.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_RIGHT))
g4.input.handle_event(ev(pygame.KEYDOWN, key=pygame.K_SPACE))
check("按住右键时方向为 +1", g4.input.read_direction() == 1.0)
check("按住空格时 fire_held 为真", g4.input.fire_held is True)

g4.input.handle_event(ev(pygame.WINDOWFOCUSLOST))
check(
    "焦点丢失后方向归零（不会一直往右飘）",
    g4.input.read_direction() == 0.0,
    f"(实际 {g4.input.read_direction()})",
)
check("焦点丢失后不再算按住开火", g4.input.fire_held is False)

# 切走窗口要自动暂停，否则回来时可能已经被打死了
g4._start_game()
check("开局在 PLAYING", g4.state is State.PLAYING)
pygame.event.post(ev(pygame.WINDOWFOCUSLOST))
g4.input.begin_frame()
g4._check_events()
g4._handle_state_input()
check(
    "窗口失焦时自动暂停",
    g4.state is State.PAUSED,
    f"(实际 {g4.state.name})",
)
check("自动暂停后世界冻住", g4.state.world_moves is False)

# 但在开始界面失焦不该有任何反应（本来就没在玩）
g5 = m.AlienInvasion()
pygame.event.post(ev(pygame.WINDOWFOCUSLOST))
g5.input.begin_frame()
g5._check_events()
g5._handle_state_input()
check(
    "READY 状态下失焦不会误进暂停",
    g5.state is State.READY,
    f"(实际 {g5.state.name})",
)

pygame.quit()
print()
print("=" * 64)
print(f"结果：{ok} 项通过, {fail} 项失败")
print("=" * 64)
sys.exit(1 if fail else 0)
