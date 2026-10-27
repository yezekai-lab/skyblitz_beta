import os
import sys


def _data_dir():
    """存档放哪儿。

    - 直接跑 .py：**本文件所在目录**（不跟启动时的当前工作目录跑）
    - 打包成 exe：**exe 所在目录**

    为什么 exe 不能沿用 `__file__`：PyInstaller 单文件模式会把程序解压到一个
    临时目录再运行，`__file__` 指向那个临时目录 —— 程序一关就整个删掉，
    最高分等于每局归零。`sys.frozen` 是 PyInstaller 打的标记，
    `sys.executable` 才是"用户双击的那个 exe"的位置。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# 存档锚定在"程序住在哪"，不跟着启动时的当前工作目录跑
HIGH_SCORE_PATH = os.path.join(_data_dir(), "high_score.txt")


class GameStats:
    """只存**数据**：分数、命数、等级、最高分。

    注意这里**没有**游戏状态(State) —— 状态不是"统计",它是"现在处于哪个阶段"。
    两者住在同一个类里的时候，改一个很容易顺手影响另一个。
    """

    def __init__(self, ai_game):
        self.settings = ai_game.settings
        self.reset_stats()

        try:
            with open(HIGH_SCORE_PATH, "r") as file:
                self.high_score = int(file.read())
        except FileNotFoundError:
            with open(HIGH_SCORE_PATH, "w") as file:
                file.write("0")
            self.high_score = 0
        except ValueError:
            with open(HIGH_SCORE_PATH, "w") as file:
                file.write("0")
            self.high_score = 0

    def reset_stats(self):
        self.ship_left = self.settings.ship_limit
        self.score = 0
        self.level = 1
        # 等离子护盾的层数（升级给的），新一局清空
        self.shield = 0

    def save_high_score(self):
        with open(HIGH_SCORE_PATH, "w") as file:
            file.write(str(self.high_score))
