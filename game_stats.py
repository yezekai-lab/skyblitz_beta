import os

# 存档锚定在"本文件所在目录"，不跟着启动时的当前工作目录跑
HIGH_SCORE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "high_score.txt"
)


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
