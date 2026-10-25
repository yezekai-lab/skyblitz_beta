from enum import Enum, auto


class State(Enum):
    """游戏当前处于哪个阶段。

    为什么用枚举，而不是继续加布尔量（game_active / paused / choosing / over）？

    因为**布尔量的组合是乘法增长的**：2 个 = 4 种组合，4 个 = 16 种，
    而其中大部分是没意义的（比如"正在选升级"同时"已经结束"）。
    写成枚举之后，任一时刻**只能处于一个状态**，那些荒谬的组合从根上就不存在。

    更进一步：状态**自己知道该怎么表现**（见下面的三个属性）。
    这样主循环里就不用到处写 `if 状态 == X or 状态 == Y`。
    """

    READY = auto()  # 停在开始界面（刚启动）
    PLAYING = auto()  # 正常游戏中
    PAUSED = auto()  # 玩家按了暂停
    UPGRADING = auto()  # 弹出三选一，等玩家挑升级（第 ④ 项才会用到）
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
