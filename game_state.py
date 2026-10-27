from enum import Enum, auto


class State(Enum):
    """游戏当前处于哪个阶段。

    用枚举而不是几个布尔量（game_active / paused / choosing / over）：
    布尔量的组合是乘法增长的，2 个是 4 种、4 个是 16 种，其中大半没有意义
    （比如"正在选升级"同时"已经结束"）。枚举保证任一时刻只能处于一个状态。

    状态自己知道该怎么表现（见下面三个属性），主循环里就不用写
    `if 状态 == X or 状态 == Y`。
    """

    READY = auto()  # 停在开始界面（刚启动）
    PLAYING = auto()  # 正常游戏中
    PAUSED = auto()  # 玩家按了暂停
    UPGRADING = auto()  # 弹出三选一，等玩家挑升级
    GAME_OVER = auto()  # 命数用完
    QUIT_CONFIRM = auto()  # 按了 ESC，正问"真的要退出吗"

    @property
    def world_moves(self):
        """游戏世界（飞船 / 子弹 / 外星人）该不该动。

        只有 PLAYING 能动。暂停、选升级、结束都必须把世界冻住。
        """
        return self is State.PLAYING

    @property
    def accepts_confirm(self):
        """「确认」键在这里是不是表示"开始新一局"。

        开始界面和结束界面都接受；游戏中它是"开火"，暂停/选升级时归别人管。
        """
        return self in (State.READY, State.GAME_OVER)

    @property
    def shows_play_button(self):
        """要不要显示 Play 按钮。"""
        return self in (State.READY, State.GAME_OVER)
