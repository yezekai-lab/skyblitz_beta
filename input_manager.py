import pygame

# 摇杆死区：静止时摇杆不会精确停在 0，小幅度漂移必须当 0 处理
DEAD_ZONE = 0.25

# ---------------------------------------------------------------------------
# 本机手柄的按键布局：Xbox One S Controller（蓝牙）
#
# ⚠️ 这张表不是猜的，是问 SDL 要来的官方映射表：
#     a=b0  start=b7  leftx=a0  lefty=a1  dpup=h0.1  dpleft=h0.8  ...
#     （SDL 内置一个手柄数据库，Xbox / PS / Switch 手柄插上就认得出）
#
# 换手柄之后，跑一次 `python probe_controller.py` 重新读，它会直接打印出
# 可以粘贴回来的常量。
# ---------------------------------------------------------------------------
PAD_MOVE_AXIS = 0  # 左摇杆 X（-1 左 ~ +1 右）
PAD_MOVE_HAT = 0  # 方向键帽（左右为 -1 / 0 / +1）
PAD_FIRE_BUTTON = 0  # A 键
PAD_PAUSE_BUTTON = 7  # Start 键
PAD_BACK_BUTTON = 1  # B 键（"返回 / 取消"）
PAD_YES_BUTTON = 3  # Y 键（确认退出时用）


class InputManager:
    """把键盘和手柄统一翻译成「移动方向 / 确认 / 开火 / 暂停」几种意图。

    上层代码（主循环）不再关心事件来自哪个设备，只读这几个结果：

    - ``read_direction()`` ：-1.0（全速左）~ +1.0（全速右），0 表示不动
    - ``confirm_pressed``  ：本帧是否按下了「确认」键（手柄 A / 回车 / 空格）
    - ``fire_pressed``     ：本帧是否按下了开火键（只在下按那一帧为 True）
    - ``pause_pressed``    ：本帧是否按下了暂停键（同上）

    注意 A 键同时算「确认」和「开火」 —— 在 Play 界面它表示"开始游戏"，
    在游戏里它表示"发射"。同一个按键在不同状态下含义不同，这件事由游戏
    状态决定，输入层只管把"用户按了确认键"这个事实报上去。

    键盘是「离散」的（按下 / 松开两个事件），手柄摇杆是「连续」的（每帧读一次
    当前值），两者状态来源不同，所以在这里统一合成 —— 这是它存在的唯一理由。
    """

    def __init__(self):
        self.joystick = None
        self.confirm_pressed = False
        self.fire_pressed = False
        self.pause_pressed = False
        # 退出确认用：ESC / B = 想退出（或取消），Y = "是的，退吧"，N = "不"
        self.escape_pressed = False
        self.yes_pressed = False
        self.no_pressed = False

        # 键盘是离散事件，必须自己记住「现在还按着没有」
        self._key_left = False
        self._key_right = False
        self._key_fire = False

        # 手柄同理：按钮按着没
        self._pad_fire = False

        # 关掉 SDL 的文本输入。看着和游戏无关，其实是必需的：
        # 中文/日文输入法一旦激活，字母键（P / Y / N）会被输入法截走，
        # 窗口根本收不到 KEYDOWN —— 表现就是"按 P 没有任何反应"，
        # 而空格、ESC、方向键却照常。本游戏不输入文字，直接关掉即可。
        pygame.key.stop_text_input()

        self._open_joystick()

    @property
    def fire_held(self):
        """开火键现在是不是按着（不是"刚按下"）。

        `fire_pressed` 是边沿（按一次只触发一次，适合单发）；
        `fire_held` 是状态（适合"按住连发"这种机制升级用）。
        """
        return self._key_fire or self._pad_fire

    # ------------------------------------------------------------------
    # 手柄连接：蓝牙手柄会自己休眠，拔插也是常态，所以这部分必须容错
    # ------------------------------------------------------------------
    def _open_joystick(self):
        """接上手柄（没有就静默跳过，游戏照常能用键盘玩）。"""
        self.joystick = None
        if pygame.joystick.get_count() == 0:
            return
        try:
            stick = pygame.joystick.Joystick(0)
            stick.init()
            self.joystick = stick
        except pygame.error:
            self.joystick = None

    @property
    def has_joystick(self):
        return self.joystick is not None

    # ------------------------------------------------------------------
    # 事件 → 意图
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)
        elif event.type == pygame.KEYUP:
            self._handle_keyup(event.key)
        elif event.type == pygame.JOYBUTTONDOWN:
            self._handle_joybuttondown(event.button)
        elif event.type == pygame.JOYBUTTONUP:
            if event.button == PAD_FIRE_BUTTON:
                self._pad_fire = False
        elif event.type == pygame.JOYHATMOTION:
            # 十字键：菜单用左右两格
            if event.hat == PAD_MOVE_HAT and event.value[0]:
                if event.value[0] > 0:
                    self.menu_right_pressed = True
                else:
                    self.menu_left_pressed = True
        elif event.type == pygame.JOYDEVICEADDED:
            self._open_joystick()
        elif event.type == pygame.JOYDEVICEREMOVED:
            self.joystick = None
        elif event.type == pygame.WINDOWFOCUSLOST:
            # 窗口失焦时把"按着"的状态全部清掉。
            # 否则按住右键 Alt+Tab 切走，KEYUP 永远不会来，切回来飞船会
            # 一直朝一个方向飘 —— 看起来就像"按键卡住了"。
            self._release_all_held()

    def _handle_keydown(self, key):
        if key == pygame.K_RIGHT:
            self._key_right = True
            self.menu_right_pressed = True
        elif key == pygame.K_LEFT:
            self._key_left = True
            self.menu_left_pressed = True
        elif key in (pygame.K_1, pygame.K_KP1):
            self.choice_pressed = 1
        elif key in (pygame.K_2, pygame.K_KP2):
            self.choice_pressed = 2
        elif key in (pygame.K_3, pygame.K_KP3):
            self.choice_pressed = 3
        elif key == pygame.K_SPACE:
            # 空格既是「确认」也是「开火」，同手柄 A 键
            self.confirm_pressed = True
            self.fire_pressed = True
            self._key_fire = True
        elif key == pygame.K_RETURN:
            self.confirm_pressed = True
        elif key == pygame.K_p:
            self.pause_pressed = True
        elif key == pygame.K_ESCAPE:
            self.escape_pressed = True
        elif key == pygame.K_y:
            self.yes_pressed = True
        elif key == pygame.K_n:
            self.no_pressed = True

    def _handle_keyup(self, key):
        if key == pygame.K_RIGHT:
            self._key_right = False
        elif key == pygame.K_LEFT:
            self._key_left = False
        elif key == pygame.K_SPACE:
            self._key_fire = False

    def _release_all_held(self):
        """把"当前按着"的状态全部清空（失焦、或收到未知重置时用）。

        注意只清"状态类"的标志（按着没），不清"边沿类"的（刚按下）——
        后者本来每帧就清，清它没有意义，还可能吃掉一次正常的按键。
        """
        self._key_left = False
        self._key_right = False
        self._key_fire = False
        self._pad_fire = False

    def _handle_joybuttondown(self, button):
        if button == PAD_FIRE_BUTTON:
            # A 键：Play 界面 = 开始游戏，游戏中 = 发射
            self.confirm_pressed = True
            self.fire_pressed = True
            self._pad_fire = True
        elif button == PAD_PAUSE_BUTTON:
            self.pause_pressed = True
        elif button == PAD_BACK_BUTTON:
            # B 键 = "返回 / 取消"，和键盘 ESC 一个意思
            self.escape_pressed = True
        elif button == PAD_YES_BUTTON:
            self.yes_pressed = True

    # ------------------------------------------------------------------
    # 每帧开头调用一次：清掉上一帧的「按下」标记
    # ------------------------------------------------------------------
    def begin_frame(self):
        """confirm / fire / pause 这类「按一下只触发一次」的意图必须自己清，

        否则按一次会连续触发几十帧（每帧都读到同一个 True）。
        """
        self.confirm_pressed = False
        self.fire_pressed = False
        self.pause_pressed = False
        self.escape_pressed = False
        self.yes_pressed = False
        self.no_pressed = False
        self.menu_left_pressed = False
        self.menu_right_pressed = False
        self.choice_pressed = None

    # ------------------------------------------------------------------
    def read_direction(self):
        """-1.0 ~ +1.0。

        每次调用都重新读一遍设备，不缓存 —— 缓存就等于多了一份可能失效的
        副本，而"两个地方各存一份状态"正是最容易出 bug 的写法。
        """
        keyboard = self._keyboard_direction()
        stick = self._joystick_direction()
        # 键盘优先：键盘只有「全速」和「不动」两档，一旦有人按了就用它；
        # 否则摇杆的零点漂移会和键盘打架，手感会发飘
        return keyboard if keyboard else stick

    def _keyboard_direction(self):
        return float(self._key_right) - float(self._key_left)

    def _joystick_direction(self):
        if self.joystick is None:
            return 0.0
        try:
            stick = self.apply_dead_zone(self.joystick.get_axis(PAD_MOVE_AXIS))
            if stick:
                return stick
            # 摇杆没动时退回到方向键帽（数字式，只有 -1 / 0 / +1）
            return float(self.joystick.get_hat(PAD_MOVE_HAT)[0])
        except pygame.error:
            # 蓝牙断了 / 手柄睡着了，直接放手柄，别让游戏崩
            self.joystick = None
            return 0.0

    @staticmethod
    def apply_dead_zone(value, dead_zone=DEAD_ZONE):
        """把摇杆原始值换算成移动意图。

        摇杆静止时不会精确停在 0（零点漂移），所以先设一个「死区」把小幅
        抖动归零；超出死区之后再把 [dead_zone, 1.0] 拉伸回 [0, 1] —— 否则
        刚推出死区那一刻会突然跳到全速，手感很生硬。
        """
        if abs(value) < dead_zone:
            return 0.0
        scaled = (abs(value) - dead_zone) / (1.0 - dead_zone)
        return scaled if value > 0 else -scaled
