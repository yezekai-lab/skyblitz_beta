"""清理后的回归测试：验证原有功能一个都没坏。"""

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
from alien import ALIEN_TYPES, Alien, image_for, pick_type
from bullet import Bullet
from game_state import State
from settings import Settings
from upgrades import UpgradePool

ok = 0
fail = 0

# 当前一队外星人的数量上限：7 列 × 3 行 = 21
# （由 settings.fleet_spacing = 2.5 决定，改间距就要改这里）
# ⚠️ 因为防阵型太死板，每个格子有 fleet_skip_chance 的几率空着，
#    所以实际数量是一个区间 —— 断言只能写成范围。
FLEET_COLS, FLEET_ROWS = 7, 3
FLEET_MAX = FLEET_COLS * FLEET_ROWS
FLEET_MIN = 8


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK]   {name} {extra}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {extra}")


print("=" * 62)
print("① 构造与初始状态")
print("=" * 62)
g = m.AlienInvasion()
check("游戏对象构造成功", True)
check("开局状态为 READY", g.state is State.READY)
check(
    f"舰队数量在 {FLEET_MIN}~{FLEET_MAX} 之间（阵型有随机空洞）",
    FLEET_MIN <= len(g.aliens) <= FLEET_MAX,
    f"(实际 {len(g.aliens)})",
)
check("子弹 0 个", len(g.bullets) == 0)
check("飞船居中", g.ship.rect.midbottom == g.screen.get_rect().midbottom)

print()
print("=" * 62)
print("② 点 Play 开局")
print("=" * 62)
g._check_play_button(g.play_button.rect.center)
check("状态变 PLAYING", g.state is State.PLAYING)
check("鼠标被隐藏", pygame.mouse.get_visible() is False)

print()
print("=" * 62)
print("③ 飞船移动（键盘 → 意图 → 位移 / 边界）")
print("=" * 62)
x0 = g.ship.x
speed = g.settings.ship_speed
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
g._check_events()
check("按右键 → 移动意图 +1.0", g.input.read_direction() == 1.0)
g.ship.update(g.input.read_direction())
check(
    f"飞船往右走了一个 ship_speed（{speed}）",
    g.ship.x == x0 + speed,
    f"({x0} → {g.ship.x})",
)
check(
    "rect 是从累加器取整来的（误差 ≤ 0.5）",
    abs(g.ship.rect.x - (x0 + speed)) <= 0.5,
    f"(rect.x = {g.ship.rect.x})",
)

pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
g._check_events()
check("松开右键 → 意图 0.0", g.input.read_direction() == 0.0)
x1 = g.ship.x
g.ship.update(g.input.read_direction())
check("松开后停下", g.ship.x == x1)

for _ in range(1000):
    g.ship.update(1.0)
check("贴右边界不再越界", g.ship.rect.right == g.screen.get_rect().right)
g.ship.center_ship()
check("center_ship 同时复位 rect 与累加器", g.ship.x == float(g.ship.rect.x) == 560.0)

print()
print("=" * 62)
print("④ 发射子弹（用改名后的 _fire_bullet）")
print("=" * 62)
check("方法名已改为 _fire_bullet", hasattr(g, "_fire_bullet"))
check("旧名字 fire_bullet 已不存在", not hasattr(g, "fire_bullet"))
g._fire_bullet()
check("发射 1 发", len(g.bullets) == 1)
for _ in range(30):
    g._fire_bullet()
check("连按 30 次不超过上限 20", len(g.bullets) == 20, f"(实际 {len(g.bullets)})")

print()
print("=" * 62)
print("⑤ 子弹绘制的改动（Group.draw 替代逐颗 draw_bullet）")
print("=" * 62)
check("Bullet 已无 draw_bullet 方法", not hasattr(Bullet, "draw_bullet"))
b = list(g.bullets)[0]
check("Bullet 仍有 image", hasattr(b, "image"))
check("Bullet 仍有 rect", hasattr(b, "rect"))
g.bullets.draw(g.screen)
check("self.bullets.draw(self.screen) 可正常执行", True)

print()
print("=" * 62)
print("⑥ 完整跑一帧到 _update_screen")
print("=" * 62)
g._update_screen()
check("_update_screen() 全程无异常", True)

print()
print("=" * 62)
print("⑦ 子弹飞出屏幕后被删除")
print("=" * 62)
for _ in range(500):
    g._update_bullets()
check("1000 帧后子弹清空", len(g.bullets) == 0, f"(实际 {len(g.bullets)})")

print()
print("=" * 62)
print("⑧ 击落外星人 → 加分 + 舰队重建")
print("=" * 62)
g.stats.score = 0
g.bullets.empty()
target = list(g.aliens)[0]
target.rect.x = g.ship.rect.centerx
target.rect.y = g.ship.rect.top - 40
target.x = float(target.rect.x)
expected_points = target.points
g._fire_bullet()
for i in range(60):
    g._update_bullets()
    if target not in g.aliens:
        break
check("子弹击中外星人", target not in g.aliens, f"(第 {i} 帧)")
check(
    f"分数 +{expected_points}（该外星人自己的分值）",
    g.stats.score == expected_points,
    f"(实际 {g.stats.score})",
)

g.stats.score = 0
g.aliens.empty()
g._update_bullets()
check(
    f"外星人清空后自动重建（{FLEET_MIN}~{FLEET_MAX} 个）",
    FLEET_MIN <= len(g.aliens) <= FLEET_MAX,
    f"(实际 {len(g.aliens)})",
)
check("等级 +1（记下打完了第几批）", g.stats.level == 2, f"(实际 {g.stats.level})")
# 【难度固定】打完一批**不该**让外星人更快 —— 这是试玩后改的：
# 以前每批 ×1.1，玩家后期手忙脚乱。
check(
    "难度不变：外星人速度仍是 1.0",
    g.settings.alien_speed == 1.0,
    f"(实际 {g.settings.alien_speed})",
)
check(
    "分值不涨：灰外星人还是 50 分",
    ALIEN_TYPES[0]["points"] == 50,
    f"(实际 {ALIEN_TYPES[0]['points']})",
)
check("重建后子弹被清空", len(g.bullets) == 0)

print()
print("=" * 62)
print("⑨ 舰队撞边转向")
print("=" * 62)
g.settings.fleet_direction = 1
for a in g.aliens:
    a.rect.right = g.screen.get_rect().right
    a.x = float(a.rect.x)
y0 = list(g.aliens)[0].base_y
g._update_aliens()
check("撞右边界后方向翻转", g.settings.fleet_direction == -1)
check(
    "同时下移 10（下移改的是 base_y —— 纵向位置的真身）",
    list(g.aliens)[0].base_y == y0 + 10,
    f"({y0} -> {list(g.aliens)[0].base_y})",
)

print()
print("=" * 62)
print("⑩ 撞船扣命 → 命数归零 → 回到 Play 界面")
print("=" * 62)
g.stats.ship_left = 3
g._ship_hit()
check("命数 3 → 2", g.stats.ship_left == 2)
check("剩余飞船图标 2 个", len(g.sb.ships) == 2)
check(
    f"撞后舰队重建（{FLEET_MIN}~{FLEET_MAX} 个）",
    FLEET_MIN <= len(g.aliens) <= FLEET_MAX,
    f"(实际 {len(g.aliens)})",
)
g._ship_hit()
g._ship_hit()
check("命数归零", g.stats.ship_left == 0)
check("状态变 GAME_OVER", g.state is State.GAME_OVER)
check("鼠标重新可见", pygame.mouse.get_visible() is True)

print()
print("=" * 62)
print("⑪ check_edges 显式返回 False")
print("=" * 62)
g._check_play_button(g.play_button.rect.center)
a = list(g.aliens)[0]
a.rect.centerx = g.screen.get_rect().centerx
check("屏幕中间 -> False（不是 None）", a.check_edges() is False)
a.rect.right = g.screen.get_rect().right
check("贴右边 -> True", a.check_edges() is True)

print()
print("=" * 62)
print("⑫ 最高分持久化（回归）")
print("=" * 62)
if os.path.exists("high_score.txt"):
    os.remove("high_score.txt")
g2 = m.AlienInvasion()
check("第一次运行 high_score = 0", g2.stats.high_score == 0)
g2._check_play_button(g2.play_button.rect.center)
g2.stats.score = 1234
g2.sb.check_high_score()
g2.stats.save_high_score()
with open("high_score.txt") as f:
    content = f.read()
check("写入文件 = '1234'", content == "1234", f"(实际 {content!r})")
g3 = m.AlienInvasion()
check("重启后读到 1234", g3.stats.high_score == 1234)
check("重开后本局分数归 0", g3.stats.score == 0)
os.remove("high_score.txt")

print()
print("=" * 62)
print("⑬ 用键盘 / 手柄开始游戏（不靠鼠标）")
print("=" * 62)
g4 = m.AlienInvasion()
check("开局状态 READY", g4.state is State.READY)

# 键盘回车
g4.input.begin_frame()
g4.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
check("回车 -> confirm_pressed True", g4.input.confirm_pressed is True)
g4._start_game()
check("回车开始后状态 PLAYING", g4.state is State.PLAYING)
check(
    f"开始后舰队重建（{FLEET_MIN}~{FLEET_MAX} 个）",
    FLEET_MIN <= len(g4.aliens) <= FLEET_MAX,
    f"(实际 {len(g4.aliens)})",
)
check("开始后飞船居中", g4.ship.rect.midbottom == g4.screen.get_rect().midbottom)
check("开始后鼠标隐藏", pygame.mouse.get_visible() is False)

# 手柄 A 键（模拟"在 Play 界面按 A"）
g5 = m.AlienInvasion()
g5.state = State.READY
pygame.mouse.set_visible(True)
g5.input.begin_frame()
g5.input.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
check("手柄 A 键 -> confirm_pressed True", g5.input.confirm_pressed is True)
check(
    "手柄 A 键 -> fire_pressed 也 True（一个键两种含义）", g5.input.fire_pressed is True
)
g5._start_game()
check("手柄 A 键开始后状态 PLAYING", g5.state is State.PLAYING)

# 模拟主循环那一圈：按 A 开始游戏的同一帧不该顺带射出一发子弹
g6 = m.AlienInvasion()
g6.state = State.READY
g6.input.begin_frame()
g6.input.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
g6._check_events()
state_changed = g6._handle_state_input()
if not state_changed and g6.state.world_moves:
    if g6.input.fire_pressed:
        g6._fire_bullet()
check(
    "开始游戏那一帧不会顺带射出子弹", len(g6.bullets) == 0, f"(实际 {len(g6.bullets)})"
)
check("_handle_state_input 正确报告了状态切换", state_changed is True)

# 还有：按 A 开始的那一帧不能同时把游戏暂停掉
check("开始那一帧也没被误暂停", g6.state is State.PLAYING)

# 下一帧恢复正常：world_moves 生效
g6.input.begin_frame()
if not g6._handle_state_input() and g6.state.world_moves:
    if g6.input.fire_pressed:
        g6._fire_bullet()
check("状态没变的帧不报告切换", g6.state is State.PLAYING)

# 玩到 game over 之后还能用 A 重开
g6._ship_hit()
g6._ship_hit()
g6._ship_hit()
check("命数归零 -> 状态变 GAME_OVER", g6.state is State.GAME_OVER)
check("GAME_OVER 时鼠标重新可见", pygame.mouse.get_visible() is True)
g6.input.begin_frame()
g6.input.handle_event(pygame.event.Event(pygame.JOYBUTTONDOWN, button=0))
if g6.state.accepts_confirm and g6.input.confirm_pressed:
    g6._start_game()
check("game over 后按 A 可以重开", g6.state is State.PLAYING)
check("重开后命数复位为 3", g6.stats.ship_left == 3)

print()
print("=" * 62)
print("⑭ 外星人分色 / 分值不同")
print("=" * 62)

check("共有 3 种外星人", len(ALIEN_TYPES) == 3)
check(
    "分值分别是 50 / 100 / 200",
    sorted(t["points"] for t in ALIEN_TYPES) == [50, 100, 200],
)

# 每次造出来的外星人，分值必须落在合法集合里
values = {t["points"] for t in ALIEN_TYPES}
sample = [Alien(g).points for _ in range(200)]
check("所有外星人的分值都在合法集合里", set(sample) <= values)
check("三种分值都会出现", set(sample) == values, f"(实际出现 {sorted(set(sample))})")

# 分值高的应该更稀有 —— 用固定随机种子保证可复现
random.seed(20261016)
picked = [pick_type()["points"] for _ in range(3000)]
count = {p: picked.count(p) for p in values}
check(
    "200 分的比 100 分的少见",
    count[200] < count[100],
    f"(50分 {count[50]} 次 / 100分 {count[100]} 次 / 200分 {count[200]} 次)",
)
check("100 分的比 50 分的少见", count[100] < count[50])
check(
    "50 分那档占比接近 60%",
    abs(count[50] / 3000 - 0.6) < 0.05,
    f"(实际 {count[50] / 3000:.2f})",
)
random.seed()  # 恢复真随机

print()
print("-- 低多边形素材：三档颜色要能分辨 --")


def center_of(color):
    return tuple(image_for(color).get_at((30, 30)))[:3]


seen = [center_of(t["color"]) for t in ALIEN_TYPES]
check("三档外星人画出来的颜色互不相同", len(set(seen)) == 3, f"({seen})")

# 中心那一点落在"暗半边"上，所以亮度会比设定色低一点，
# 但「哪个通道最强」必须和设定色一致 —— 这就是"颜色没被搞错"的判据
for t, got in zip(ALIEN_TYPES, seen):
    want_dominant = t["color"].index(max(t["color"]))
    got_dominant = got.index(max(got))
    channel = "RGB"[want_dominant]
    check(
        f"{t['points']:>3} 分那档的主通道是 {channel}（实际像素 {got}）",
        want_dominant == got_dominant,
        f"(设定色 {t['color']})",
    )

print()
print("-- 缓存 --")
check(
    "同色的图片是同一个对象（只加载 / 染色一次）",
    image_for(ALIEN_TYPES[0]["color"]) is image_for(ALIEN_TYPES[0]["color"]),
)
check(
    "不同色的图片不是同一个对象",
    image_for(ALIEN_TYPES[0]["color"]) is not image_for(ALIEN_TYPES[1]["color"]),
)

print()
print("-- 计分：一枪打中两个不同分值的外星人 --")
g.stats.score = 0
g.bullets.empty()
g.aliens.empty()
pair = []
for pts in (50, 200):
    a = Alien(g)
    a.points = pts
    a.rect.x = g.ship.rect.centerx
    a.rect.y = g.ship.rect.top - 40
    a.x = float(a.rect.x)
    g.aliens.add(a)
    pair.append(a)
g._fire_bullet()
g._update_bullets()
check("两个都被打中", all(a not in g.aliens for a in pair))
check(
    "分数 = 50 + 200 = 250（各算各的）",
    g.stats.score == 250,
    f"(实际 {g.stats.score}；写成 alien_points×数量 就会得到别的数)",
)

print()
print("-- 计分：一枪两个不同分值的已经验过了，这里验『升级门槛越来越贵』--")

# 【试玩反馈】难度固定之后，唯一还在变强的就是升级 —— 所以它必须越来越贵。
# 规则：第 n 次升级需要的累计分 = base × n × (n+1) ÷ 2
#   n=1 → 400   n=2 → 1200   n=3 → 2400   n=4 → 4000
# 断言用"关系"而不是写死 400/1200/2400：
#   ① 每次之间的差额严格递增（这就是"越来越贵"）
#   ② 第 1 次等于 base（保证开局别太难）
g.base = g.settings.upgrade_score_base


def needed_for(n):
    """照抄 _check_upgrade_threshold 里的算法，用来算"第 n 次要多少分"。"""
    return g.base * n * (n + 1) // 2


gaps = [needed_for(n + 1) - needed_for(n) for n in range(1, 6)]
check(
    "升级间隔严格递增（第 n 次比第 n-1 次多要 base 分）",
    all(gaps[i] < gaps[i + 1] for i in range(len(gaps) - 1)),
    f"(间隔: {gaps})",
)
check(
    "第 1 次升级只要 base 分（开局不至于卡住）",
    needed_for(1) == g.base,
    f"(实际 {needed_for(1)})",
)
check(
    "第 4 次门槛已接近第 1 次的 10 倍",
    needed_for(4) >= g.base * 9,
    f"(第 4 次 {needed_for(4)}，第 1 次 {needed_for(1)})",
)

# 反过来验一次真实代码：把分数摆到"第 5 次刚好不够"，不该弹窗
g._upgrade_count = 4
g.stats.score = needed_for(5) - 1
g.state = m.State.PLAYING
g.upgrade_screen = None
g._check_upgrade_threshold()
check(
    "差 1 分时不该弹升级界面",
    g.upgrade_screen is None and g.state is m.State.PLAYING,
    f"(state={g.state.name})",
)
g.stats.score = needed_for(5)
g._check_upgrade_threshold()
check(
    "刚好够分时弹出升级界面",
    g.state is m.State.UPGRADING,
    f"(state={g.state.name})",
)
g.state = m.State.PLAYING
g.upgrade_screen = None
g._upgrade_count = 0
g.stats.score = 0

print()
print("=" * 62)
print("⑮ 外星人阵型：有行列感但不整齐")
print("=" * 62)


def build_fleet(jitter):
    """按指定抖动值建一队，返回外星人列表。

    注意把 skip_chance 关掉 —— 这一段测的是【布局】，不是数量。
    开着随机跳格的话，每个格子都可能空着，好多断言会时灵时不灵。
    """
    gg = m.AlienInvasion()
    gg.settings.fleet_jitter = jitter
    gg.settings.fleet_skip_chance = 0.0
    gg.aliens.empty()
    gg._create_fleet()
    return list(gg.aliens)


random.seed(20261016)
jittered = build_fleet(0.7)

check(
    f"数量是 {FLEET_MAX} 个（跳格关卡了）",
    len(jittered) == FLEET_MAX,
    f"(实际 {len(jittered)})",
)

# 最关键的一条不变量：抖动绝不能抖出重叠来
overlaps = []
for i in range(len(jittered)):
    for j in range(i + 1, len(jittered)):
        if jittered[i].rect.colliderect(jittered[j].rect):
            overlaps.append((i, j))
check(
    "任意两个外星人都不重叠（几何保证，不靠运气）",
    not overlaps,
    f"(有 {len(overlaps)} 对重叠)",
)

screen_rect = jittered[0].screen.get_rect()
out_of_screen = [a for a in jittered if not screen_rect.contains(a.rect)]
check("全部都在屏幕范围内", not out_of_screen, f"(越界 {len(out_of_screen)} 个)")

# 不整齐：原本整齐的方格只有 FLEET_COLS 个不同的 x、FLEET_ROWS 个不同的 y
distinct_x = len({a.rect.x for a in jittered})
distinct_y = len({a.rect.y for a in jittered})
check(
    f"x 坐标远多于 {FLEET_COLS} 列（说明不是整齐的网格）",
    distinct_x >= FLEET_COLS * 2,
    f"({distinct_x} 个不同的 x / 共 {FLEET_MAX} 个)",
)
check(
    f"y 坐标远多于 {FLEET_ROWS} 行（说明不是整齐的网格）",
    distinct_y >= FLEET_ROWS * 2,
    f"({distinct_y} 个不同的 y / 共 {FLEET_MAX} 个)",
)

# 但也不能抖散架：整队仍应落在原来的那片区域里
st = jittered[0].settings
w0 = jittered[0].rect.width
room = int(w0 * st.fleet_spacing) - w0
max_offset = room / 2 * st.fleet_jitter + 1  # +1 是四舍五入的余量
min_x = min(a.rect.x for a in jittered)
max_right = max(a.rect.right for a in jittered)
check(
    "整队水平范围仍落在原来的列区域内（没有系统性偏移）",
    min_x >= w0 - max_offset and max_right <= st.screen_width - w0 + max_offset,
    f"(最左 x={min_x}, 最右 right={max_right}, 允许偏移 ±{max_offset:.0f})",
)
check(
    "整队仍然留在屏幕上半部分，和飞船之间留着空隙",
    max(a.rect.bottom for a in jittered) < g.ship.rect.top - 100,
    f"(最下面 bottom={max(a.rect.bottom for a in jittered)}, 飞船 top={g.ship.rect.top})",
)

print()
print("-- 反证：把抖动调成 0，应该变回整齐的方格 --")
random.seed(1)
grid = build_fleet(0.0)
check(
    f"jitter=0 时只有 {FLEET_COLS} 个不同的 x（整齐的 {FLEET_COLS} 列）",
    len({a.rect.x for a in grid}) == FLEET_COLS,
)
check(
    f"jitter=0 时只有 {FLEET_ROWS} 个不同的 y（整齐的 {FLEET_ROWS} 行）",
    len({a.rect.y for a in grid}) == FLEET_ROWS,
)
check(f"jitter=0 时数量不变（{FLEET_MAX} 个）", len(grid) == FLEET_MAX)
check(
    "说明 fleet_jitter 这个参数真的在起作用",
    len({a.rect.x for a in grid}) == FLEET_COLS and distinct_x >= FLEET_COLS * 2,
)

print()
print("-- 每个外星人自己在上下浮动（不是整队僵硬平移）--")
bobbers = build_fleet(0.7)
phases = [a.bob_phase for a in bobbers]
check(
    "每个外星人的浮动相位都不一样（所以不会一起动）",
    len(set(round(p, 3) for p in phases)) == len(bobbers),
)

# 跑几帧让浮动走到不同位置
for _ in range(20):
    for a in bobbers:
        a.update()
offsets = [a.rect.y - a.base_y for a in bobbers]
check(
    "浮动偏移有正有负（是上下波动，不是单向漂移）",
    min(offsets) < 0 < max(offsets),
    f"(偏移范围 {min(offsets)} ~ {max(offsets)})",
)
check(
    "同一时刻各外星人的浮动量不同（没有齐步走）",
    len(set(offsets)) > 1,
    f"(实际有 {len(set(offsets))} 种不同的偏移量)",
)
amplitude = bobbers[0].settings.alien_bob_amplitude
check(
    f"浮动幅度不超过设定值 ±{amplitude}",
    all(abs(o) <= amplitude for o in offsets),
    f"(实际最大 {max(abs(o) for o in offsets)})",
)

# 反证：把幅度调成 0，纵向就应该完全重合在基准线上
silent = build_fleet(0.7)
for a in silent:
    a.settings.alien_bob_amplitude = 0
for _ in range(5):
    for a in silent:
        a.update()
check(
    "幅度=0 时 rect.y 应该刚好等于 base_y（浮动真的可以关掉）",
    all(a.rect.y == a.base_y for a in silent),
)

# 浮动不能改变基准线本身（否则整队会自己往下漂）
moving = build_fleet(0.7)
before = [a.base_y for a in moving]
for _ in range(50):
    for a in moving:
        a.update()
check(
    "浮动不会改动 base_y（整队不会自己往下漂）",
    [a.base_y for a in moving] == before,
)
random.seed()

print()
print("-- 随机可复现 --")
random.seed(777)
first = sorted(a.rect.x for a in build_fleet(0.7))
random.seed(777)
second = sorted(a.rect.x for a in build_fleet(0.7))
check("同一个种子 -> 同一套位置（测试才可能稳定）", first == second)
random.seed()

print()
print("=" * 62)
print("⑯ 帧率限制（游戏速度不能取决于电脑有多快）")
print("=" * 62)
check("游戏对象带一个帧率时钟", hasattr(g, "clock"))
check(f"帧率设置是 {g.settings.fps}", g.settings.fps == 60)

# 真的验证 tick 能限速：跑 8 帧，应当明显耗时（不是瞬间跑完）
import time

probe = pygame.time.Clock()
start = time.perf_counter()
for _ in range(8):
    probe.tick(60)
elapsed = time.perf_counter() - start
check(
    "clock.tick(60) 真的会把循环压到每秒 60 帧（8 帧 ≈ 0.13 秒）",
    0.08 < elapsed < 0.5,
    f"(实际 {elapsed:.3f} 秒)",
)

# 反证：不限帧时同样 8 帧应该几乎不花时间
start = time.perf_counter()
for _ in range(8):
    probe.tick()
elapsed_free = time.perf_counter() - start
check(
    "不限帧时同样 8 帧几乎不花时间（说明上面那条测的是真东西）",
    elapsed_free < elapsed / 3,
    f"(不限帧 {elapsed_free:.4f} 秒 vs 限帧 {elapsed:.3f} 秒)",
)

print()
print("=" * 62)
print("⑰ 机制类升级真的改变了【行为】，不只是改了数字")
print("=" * 62)

# ---- MULTI SHOT：一次发多发 ----
print()
print("-- MULTI SHOT --")
g7 = m.AlienInvasion()
g7._start_game()
g7.bullets.empty()
g7.settings.bullets_per_shot = 1
g7._fire_bullet()
check("没升级时发 1 发", len(g7.bullets) == 1)

g7.bullets.empty()
g7.settings.bullets_per_shot = 3
g7._fire_bullet()
check("升级后一次发 3 发", len(g7.bullets) == 3, f"(实际 {len(g7.bullets)})")
xs = sorted(b.rect.centerx for b in g7.bullets)
check("3 发是【左右排开】的，不是叠在一起", len(set(xs)) == 3, f"(x = {xs})")
check(
    "以飞船中心为轴对称",
    abs((xs[0] + xs[2]) / 2 - g7.ship.rect.centerx) <= 1,
    f"(子弹中轴 {(xs[0] + xs[2]) / 2}, 飞船中心 {g7.ship.rect.centerx})",
)

g7.bullets.empty()
g7.settings.bullets_per_shot = 3
g7.settings.bullets_allowed = 2  # 装不下 3 发
g7._fire_bullet()
check(
    "装不下时宁可不发，也不会超上限", len(g7.bullets) == 0, f"(实际 {len(g7.bullets)})"
)

# ---- PIERCE：子弹穿透 ----
print()
print("-- PIERCE --")
for pierce_flag, expect_survive in ((False, False), (True, True)):
    gg = m.AlienInvasion()
    gg._start_game()
    gg.settings.bullets_per_shot = 1
    gg.settings.bullets_pierce = pierce_flag
    gg.bullets.empty()
    gg.aliens.empty()

    target = Alien(gg)
    target.points = 50
    target.rect.x = gg.ship.rect.centerx
    target.rect.y = gg.ship.rect.top - 40
    target.x = float(target.rect.x)
    gg.aliens.add(target)

    # ⚠️ 必须再放一个"陪跑"的外星人：
    #    如果场上只有 target，打光它会触发"清空子弹 + 重建舰队"，
    #    那时不管有没有穿透，子弹都会被清掉 —— 测的就不是穿透了。
    dummy = Alien(gg)
    dummy.points = 50
    dummy.place(20, 60)
    gg.aliens.add(dummy)

    gg._fire_bullet()
    bullet = list(gg.bullets)[0]
    for _ in range(60):
        gg._update_bullets()
        if target not in gg.aliens:
            break

    check(
        f"bullets_pierce={pierce_flag} 时，打中外星人后子弹{'还在' if expect_survive else '消失'}",
        (bullet in gg.bullets) is expect_survive,
        f"(子弹还在吗: {bullet in gg.bullets})",
    )

# ---- AUTO FIRE：按住连发 ----
print()
print("-- AUTO FIRE --")
gg = m.AlienInvasion()
gg._start_game()
gg.settings.bullets_per_shot = 1
gg.bullets.empty()

check("fire_held 开局是 False", gg.input.fire_held is False)
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
gg._check_events()
check("按下空格 -> fire_held True", gg.input.fire_held is True)
pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE))
gg._check_events()
check("松开空格 -> fire_held False", gg.input.fire_held is False)


def run_one_frame(game):
    """跑一帧主循环（不含限帧）。"""
    game.input.begin_frame()
    game._check_events()
    if not game._handle_state_input() and game.state.world_moves:
        game.ship.update(game.input.read_direction())
        if game.input.fire_pressed or (
            game.settings.auto_fire and game.input.fire_held
        ):
            game._fire_bullet()
        game._update_aliens()
        game._update_bullets()


# 没升级：按住不放也只发 1 发（因为是边沿触发）
gg = m.AlienInvasion()
gg._start_game()
gg.settings.bullets_per_shot = 1
gg.settings.auto_fire = False
gg.bullets.empty()
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
for _ in range(5):
    run_one_frame(gg)
check(
    "没升级时按住 5 帧只发 1 发（边沿触发）",
    len(gg.bullets) == 1,
    f"(实际 {len(gg.bullets)})",
)

# 升级后：按住会持续发
gg = m.AlienInvasion()
gg._start_game()
gg.settings.bullets_per_shot = 1
gg.settings.auto_fire = True
gg.bullets.empty()
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
for _ in range(5):
    run_one_frame(gg)
check(
    "升级后按住 5 帧发了 5 发（状态触发）",
    len(gg.bullets) == 5,
    f"(实际 {len(gg.bullets)})",
)

print()
print("=" * 62)
print("⑱ 神族元素：等离子护盾 / 灵能风暴 / 时间扭曲")
print("=" * 62)

# ---- 等离子护盾：有盾先碎盾，不扣命 ----
print()
print("-- PLASMA SHIELD --")
gs = m.AlienInvasion()
gs._start_game()
gs.stats.shield = 1
lives_before = gs.stats.ship_left
gs._ship_hit()
check("有盾时撞一下：盾 1 -> 0", gs.stats.shield == 0, f"(实际 {gs.stats.shield})")
check(
    "有盾时撞一下：【命数不变】",
    gs.stats.ship_left == lives_before,
    f"({lives_before} -> {gs.stats.ship_left})",
)
gs._ship_hit()
check(
    "盾碎了之后再撞：命数 -1",
    gs.stats.ship_left == lives_before - 1,
    f"({lives_before} -> {gs.stats.ship_left})",
)

# ---- 灵能风暴：炸掉周围一圈 ----
print()
print("-- PSIONIC STORM --")


def storm_scene(radius):
    """摆一个'被击中的' + 一个'贴着的邻居' + 一个'远处的'。"""
    gg = m.AlienInvasion()
    gg._start_game()
    gg.bullets.empty()
    gg.aliens.empty()
    gg.settings.psionic_radius = radius
    gg.settings.bullets_per_shot = 1
    gg.stats.score = 0

    target = Alien(gg)
    target.points = 50
    target.place(gg.ship.rect.centerx, gg.ship.rect.top - 40)
    gg.aliens.add(target)

    neighbor = Alien(gg)
    neighbor.points = 100
    # +70：贴着但【不重叠】（外星人宽 60）。
    # 如果写成 +40 就会重叠，那一发子弹会直接打中两个 —— 就测不出风暴了。
    neighbor.place(target.rect.x + 70, target.rect.y)
    gg.aliens.add(neighbor)

    far = Alien(gg)
    far.points = 200
    far.place(60, 60)  # 屏幕左上角，离得远
    gg.aliens.add(far)

    gg._fire_bullet()
    for _ in range(60):
        gg._update_bullets()
        if target not in gg.aliens:
            break
    return gg, target, neighbor, far


gg, target, neighbor, far = storm_scene(55)
check("目标被打中了", target not in gg.aliens)
check("技能生效：贴着的那一个也被炸掉", neighbor not in gg.aliens)
check("远处的那个没事", far in gg.aliens)
check(
    "分数 = 50 + 100 = 150（爆炸也要算分）",
    gg.stats.score == 150,
    f"(实际 {gg.stats.score}；注意远处那个 200 分的不该算进去)",
)

# 反证：半径 = 0（没这个升级）时，邻居应该活着
gg2, target2, neighbor2, far2 = storm_scene(0)
check("半径=0 时，目标死了", target2 not in gg2.aliens)
check("半径=0 时，邻居【活】着（证明上一条测的是风暴）", neighbor2 in gg2.aliens)
check("半径=0 时，分数只有 50", gg2.stats.score == 50, f"(实际 {gg2.stats.score})")

# ---- 时间扭曲：整队变慢 ----
print()
print("-- TIME WARP --")
gt = m.AlienInvasion()
gt._start_game()
speed_before = gt.settings.alien_speed
pool_t = UpgradePool(gt)
pool_t.take("time_warp")
check(
    "时间扭曲让外星人速度降为 80%",
    abs(gt.settings.alien_speed - speed_before * 0.8) < 1e-9,
    f"({speed_before} -> {gt.settings.alien_speed})",
)

pygame.quit()
print()
print("=" * 62)
print("⑲ 升级不能跨局泄漏（新一局必须回到初始强度）")
print("=" * 62)

WATCH = [
    "ship_speed",
    "bullet_speed",
    "alien_speed",
    "bullets_allowed",
    "ship_limit",
    "bullets_per_shot",
    "bullets_pierce",
    "auto_fire",
    "psionic_radius",
]

gl = m.AlienInvasion()
gl._start_game()
pool_l = UpgradePool(gl)
for u in pool_l.definitions:
    for _ in range(u.max_level):
        pool_l.take(u.key)
# 弹数用 ">= 3" 而不是 "== 3"：第三颗是 STARFALL CANNON 进化给的。
# 以后再加进化，这条不会因为"多了一颗"就假红。
check(
    "把所有升级拿满后，数值确实被强化了",
    gl.settings.bullets_per_shot >= 3 and gl.settings.bullets_allowed > 20,
    f"(弹数 {gl.settings.bullets_per_shot}, 弹上限 {gl.settings.bullets_allowed})",
)

gl._start_game()
fresh = Settings()
leaked = [k for k in WATCH if getattr(gl.settings, k) != getattr(fresh, k)]
check(
    "开新局后，所有会被升级改的项都复位了（不跨局累积）",
    not leaked,
    f"(泄漏的: {leaked})",
)
check(
    "新局的命数也回到 3",
    gl.stats.ship_left == fresh.ship_limit,
    f"(实际 {gl.stats.ship_left})",
)
print()
print("=" * 62)
print(f"结果：{ok} 项通过, {fail} 项失败")
print("=" * 62)
sys.exit(1 if fail else 0)
