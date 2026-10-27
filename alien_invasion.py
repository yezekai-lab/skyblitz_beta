import pygame
from time import sleep

import random
import sys

import art
from ship import Ship
from settings import Settings
from game_stats import GameStats
from scoreboard import Scoreboard
from button import Button
from bullet import Bullet
from alien import Alien
from game_state import State
from input_manager import InputManager
from upgrade_screen import UpgradeScreen
from upgrades import UpgradePool


class AlienInvasion:
    def __init__(self):
        pygame.init()
        self.settings = Settings()
        self.screen = pygame.display.set_mode(
            (self.settings.screen_width, self.settings.screen_height)
        )
        self.screen_rect = self.screen.get_rect()
        self.input = InputManager()
        self.stats = GameStats(self)
        self.upgrades = UpgradePool(self)

        # 阶段与升级计数要先于 Scoreboard 就位：
        # Scoreboard 一建好就会渲染一次 HUD，而 HUD 里要读 _upgrade_count
        # （算"还差多少分升级"）。顺序反了就是 AttributeError。
        self.state = State.READY
        self.upgrade_screen = None
        self._upgrade_count = 0
        # 进化提示条还剩几帧（0 = 不显示）
        self.evolution_timer = 0
        # 两个特效的倒计时（0 = 不显示）。只在世界更新时递减，
        # 所以暂停时它们也会一起冻住 —— 和"暂停就是冻住世界"的规则一致。
        self.muzzle_flash = 0  # 开火闪光
        self.hit_flash = 0  # 受伤红边
        # 按 ESC 前处于哪个状态 —— 取消退出时要退回到它
        self._state_before_quit = None

        self.sb = Scoreboard(self)
        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()
        self.play_button = Button(self, "Play")

        # 帧率时钟。没有它，游戏速度就取决于电脑有多快
        self.clock = pygame.time.Clock()

        # 暂停时压在画面上的半透明黑幕。只建一次 —— 每帧新建 Surface 太浪费
        self.pause_overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.pause_overlay.fill((0, 0, 0, 120))
        # 退出确认要问"是/否"，字必须一眼看清 —— 所以幕布更暗
        self.quit_overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self.quit_overlay.fill((0, 0, 0, 205))

        # 特效图只画一次，之后靠 set_alpha() 淡出（不是每帧重画）
        self.muzzle_flash_image = art.make_muzzle_flash()
        self.hit_vignette = art.make_hit_vignette(self.screen.get_size())

        self._create_fleet()

    def _check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_game()
            elif event.type == pygame.MOUSEMOTION:
                # 鼠标滑到哪张卡上，高亮就跟到哪张
                if self.state is State.UPGRADING and self.upgrade_screen:
                    self.upgrade_screen.highlight_at(event.pos, margin=8)
                elif self.state.shows_play_button:
                    self.play_button.update_hover(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_click(event.pos)
            else:
                # 键盘、手柄按钮、手柄插拔 …… 一律交给输入层翻译成"意图"
                self.input.handle_event(event)

    def _handle_mouse_click(self, pos):
        if self.state is State.UPGRADING and self.upgrade_screen:
            index = self.upgrade_screen.index_at(pos, margin=8)
            if index is not None:
                self.upgrade_screen.index = index
                self._take_upgrade()
        else:
            self._check_play_button(pos)

    def _check_play_button(self, mouse_pos):
        clicked = self.play_button.rect.collidepoint(mouse_pos)
        if clicked and self.state.accepts_confirm:
            self._start_game()

    def _quit_game(self):
        """真正退出：存好最高分再走。

        单独抽出来，是因为现在有三个入口都能退出：
        点窗口的 X、按 ESC 后按 Y、以后可能加菜单里的 Exit。
        三处各写一遍"先存盘再退出"，就会有一处忘了存。
        """
        self.stats.save_high_score()
        sys.exit()

    def _request_quit(self):
        """按下 ESC：不直接退，先问一句（防误按）。

        「来路」要记下来 —— 取消之后必须回到原来的状态，
        而不是一律回到 PLAYING（在 Play 界面按 ESC 再取消，不该直接开局）。
        """
        if self.state is State.QUIT_CONFIRM:
            return
        self._state_before_quit = self.state
        self.state = State.QUIT_CONFIRM
        pygame.mouse.set_visible(True)

    def _cancel_quit(self):
        """按了"不"：退回按 ESC 之前的状态。"""
        self.state = self._state_before_quit or State.READY
        self._state_before_quit = None
        if not self.state.accepts_confirm:
            pygame.mouse.set_visible(False)

    def _start_game(self):
        """开一局新的。

        鼠标点 Play、键盘回车 / 空格、手柄 A 键都走这里 —— 抽出来之后，
        "谁触发的"和"怎么开始"就分开了，以后加新的开始方式不用再抄一遍。
        """
        self.settings.initialize_dynamic_settings()

        self.stats.reset_stats()
        # 新一局：升级全部清空（否则上一局的强化会带过来）
        self.upgrades = UpgradePool(self)
        self._upgrade_count = 0
        self.upgrade_screen = None
        self.evolution_timer = 0
        self.sb.evolution_image = None
        self.state = State.PLAYING
        self.sb.prep_score_and_next()
        self.sb.prep_level()
        self.sb.prep_ships()
        self.sb.prep_shield()
        self.sb.prep_upgrades()

        self.aliens.empty()
        self.bullets.empty()

        self._create_fleet()
        self.ship.center_ship()

        pygame.mouse.set_visible(False)

    def _toggle_pause(self):
        """在「游戏中」和「暂停」之间来回切。其他状态下一律无效。"""
        if self.state is State.PLAYING:
            self.state = State.PAUSED
        elif self.state is State.PAUSED:
            self.state = State.PLAYING

    def _fire_bullet(self):
        """发射。发几发、怎么排开，由 settings.bullets_per_shot 决定。

        这是机制类升级改的地方：数值升级不会动这里，
        但 MULTI SHOT 会让 count 从 1 变成 2、3 —— 走进另一个分支。
        """
        count = self.settings.bullets_per_shot
        if len(self.bullets) + count > self.settings.bullets_allowed:
            return

        spacing = 30  # 多发子弹之间的横向间隔
        for i in range(count):
            bullet = Bullet(self)
            # 让多发子弹以飞船中心为轴左右对称地排开
            offset = (i - (count - 1) / 2) * spacing
            bullet.rect.x += round(offset)
            self.bullets.add(bullet)

        # 枪口闪一下。这是"给动作加反馈"最便宜的写法：
        # 一个倒计时 + 一张预渲染的图，不需要动画帧序列。
        self.muzzle_flash = self.settings.muzzle_flash_frames

    def _create_fleet(self):
        """摆一队外星人。

        思路：先把格子算出来，再让每个外星人在自己的格子里随机挪一点。
        格子保证"排得下、不重叠"，随机挪动保证"看起来不像整齐的方格".
        两者分开，互不干扰 —— 这就是"有行列感但不整齐"。

        格子多大由 `settings.fleet_spacing` 决定（间距倍数），调它就能改疏密。
        """
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        step_x = int(alien_width * self.settings.fleet_spacing)
        step_y = int(alien_height * self.settings.fleet_spacing)

        available_space_x = self.settings.screen_width - (2 * alien_width)
        number_aliens_x = available_space_x // step_x

        ship_height = self.ship.rect.height
        available_space_y = (
            self.settings.screen_height - (3 * alien_height) - ship_height
        )
        number_rows = available_space_y // step_y
        for row_number in range(number_rows):
            for alien_number in range(number_aliens_x):
                # 每个格子随机决定「这次不打仗」—— 阵型才会出现空洞
                if random.random() < self.settings.fleet_skip_chance:
                    continue
                self._create_alien(alien_number, row_number)

    def _jittered_position(self, slot_base, room):
        """以一个格子的「原始位置」为中心，左右随机偏一点。

        `room` 是这个格子里空着的宽度（格子宽 − 外星人宽）。

        - `fleet_jitter = 0` → 偏移恒为 0 → 回到整齐的方格布局
        - `fleet_jitter = 1` → 最多偏 ±room/2 → 刚好贴住邻居，但不会重叠

        ⚠️ 必须以 slot_base 为中心对称地偏，不能只往一个方向偏。
        只往一个方向偏的话整个舰队会系统性地往右下平移，位置整体跑偏
        （离飞船越来越近）。写第一版时就踩了这个，被"舰队没往下跑"那条断言抓到。
        """
        jitter = self.settings.fleet_jitter
        return slot_base + (random.random() - 0.5) * room * jitter

    def _create_alien(self, alien_number, row_number):
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        step_x = int(alien_width * self.settings.fleet_spacing)
        step_y = int(alien_height * self.settings.fleet_spacing)

        # 这个外星人分到的格子的左上角
        slot_x = alien_width + step_x * alien_number
        slot_y = alien_height + step_y * row_number

        alien.place(
            round(self._jittered_position(slot_x, step_x - alien_width)),
            round(self._jittered_position(slot_y, step_y - alien_height)),
        )
        self.aliens.add(alien)

    def _update_bullets(self):
        self.bullets.update()

        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        # 穿透：升级之后子弹打中外星人自己不消失，可以继续打下一个。
        # 这就是"机制升级"—— 同一次碰撞检测，因为一个开关走了另一条路。
        bullets_survive = self.settings.bullets_pierce
        collisions = pygame.sprite.groupcollide(
            self.bullets, self.aliens, not bullets_survive, True
        )

        if collisions:
            # groupcollide 返回的是 {子弹: [被它打中的外星人, ...]}
            # 现在每个外星人自带分值，所以必须逐个累加 ——
            # 再像以前那样写 `alien_points * len(aliens)` 就错了
            # （那样一枪打中两个不同价的外星人，会按同一个价算两遍）
            for hit_aliens in collisions.values():
                for alien in hit_aliens:
                    self.stats.score += alien.points
                    # 神族灵能风暴：击落它时把周围一圈也炸掉
                    if self.settings.psionic_radius:
                        self._psionic_storm(alien)
            self.sb.prep_score_and_next()
            self.sb.check_high_score()
            self._check_upgrade_threshold()
        if not self.aliens:
            # 难度固定只换一批新的，不加速、不涨分。
            # 变化的是"升级要多少分"（见 _check_upgrade_threshold），
            # 而不是"外星人越来越难打"。
            self.bullets.empty()
            self._create_fleet()

            self.stats.level += 1
            self.sb.prep_level()

    def _psionic_storm(self, center):
        """神族灵能风暴：以被击落的外星人为中心，炸掉周围一圈。

        为什么可以边遍历边 kill：`Group.sprites()` 返回的是一个列表副本，
        不是内部存储本身 —— 所以遍历的时候删元素不会出问题。
        （如果直接遍历 Group 内部那个容器，就可能错过元素。这是老坑了。）
        """
        radius = self.settings.psionic_radius
        area = center.rect.inflate(radius * 2, radius * 2)
        for victim in self.aliens.sprites():
            if area.colliderect(victim.rect):
                self.stats.score += victim.points
                victim.kill()

    def _update_effects(self):
        """特效倒计时每帧减一。

        放在世界更新里（而不是绘制里），这样暂停时特效也跟着冻住 ——
        和"暂停 = 冻住世界"保持同一条规则。时间相关的状态只在一个地方推进，
        就不会出现"暂停了红边还在闪"这种半冻结的怪状态。
        """
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1

    def _draw_muzzle_flash(self):
        """开火闪光：贴在飞船枪口上方，随剩余帧数淡出。"""
        if self.muzzle_flash <= 0:
            return
        ratio = self.muzzle_flash / self.settings.muzzle_flash_frames
        self.muzzle_flash_image.set_alpha(int(255 * ratio))
        rect = self.muzzle_flash_image.get_rect(midbottom=self.ship.rect.midtop)
        self.screen.blit(self.muzzle_flash_image, rect)

    def _draw_hit_flash(self):
        """受伤红边：越接近"刚被撞"越明显。"""
        if self.hit_flash <= 0:
            return
        ratio = self.hit_flash / self.settings.hit_flash_frames
        self.hit_vignette.set_alpha(int(255 * ratio))
        self.screen.blit(self.hit_vignette, (0, 0))

    def _update_screen(self):
        self.screen.fill(self.settings.bg_color)
        self.ship.blitme()
        self.bullets.draw(self.screen)
        self.aliens.draw(self.screen)
        self._draw_muzzle_flash()

        self.sb.show_score()
        self._draw_hit_flash()

        # 进化提示条。倒计时放在这里，是因为 _update_screen() 是唯一
        # 每帧必定被调用的地方（暂停 / 选卡 / 结束时世界不动，但屏幕照样重画）。
        if self.evolution_timer > 0:
            self.sb.show_evolution()
            self.evolution_timer -= 1
            if self.evolution_timer == 0:
                self.sb.evolution_image = None

        if self.state is State.PAUSED:
            self.screen.blit(self.pause_overlay, (0, 0))
            self.sb.show_paused()
        elif self.state is State.GAME_OVER:
            self.screen.blit(self.pause_overlay, (0, 0))
            self.sb.show_game_over()
        elif self.state is State.UPGRADING and self.upgrade_screen:
            self.upgrade_screen.draw(self.screen, self.screen_rect)
        elif self.state is State.QUIT_CONFIRM:
            self.screen.blit(self.quit_overlay, (0, 0))
            self.sb.show_quit_confirm()

        if self.state.shows_play_button:
            self.play_button.draw_button()
        pygame.display.flip()

    def _check_upgrade_threshold(self):
        """累积分够就弹三选一。

        第 n 次升级需要 score >= base × n × (n+1) ÷ 2
            n=1 → 400    n=2 → 1200    n=3 → 2400    n=4 → 4000
        意思是：第 1 次差 400 分，第 2 次再差 800 分，第 3 次再差 1200 分……
        每一次都比上一次更贵，所以升级会越来越慢 —— 这是"难度固定"
        之后唯一还在变强的东西，也是拉长一局的主要因素。

        不在阈值里存"下次多少分"，而是用计数现算 —— 少一份状态就少一类 bug。
        """
        if self.state is not State.PLAYING:
            return
        if self.stats.score >= self.next_upgrade_at():
            self._begin_upgrade()

    def next_upgrade_at(self):
        """下一次升级需要的累计分数（现算，不存任何状态）。

        HUD 的"还差多少分"和弹窗判定读的是同一个方法 —— 只要它俩一致，
        屏幕上的倒计时就不会和实际触发对不上。
        """
        return self.settings.upgrade_threshold(self._upgrade_count + 1)

    def _begin_upgrade(self):
        """抽出三张卡，切到 UPGRADING 状态。"""
        choices = self.upgrades.available(3)
        if not choices:  # 全拿满了，就不用弹了
            return
        self.upgrade_screen = UpgradeScreen(choices, self.screen_rect)
        self.state = State.UPGRADING
        pygame.mouse.set_visible(True)  # 能用鼠标点卡

    def _take_upgrade(self):
        """选定当前高亮的那张卡。"""
        choice = (
            self.upgrade_screen.highlighted_choice() if self.upgrade_screen else None
        )
        if choice is None or not self.upgrades.take(choice.key):
            return
        self._upgrade_count += 1
        self.sb.prep_upgrades()
        self.sb.prep_shield()
        self.sb.prep_next_upgrade()  # 门槛变了，"还差多少分"也要重算
        if choice.is_fusion:
            self._announce_evolution(choice.title)
        self.upgrade_screen = None
        self.state = State.PLAYING
        pygame.mouse.set_visible(False)

    def _announce_evolution(self, title):
        """进化成功：渲染一次提示条，并开始倒计时。"""
        self.sb.prep_evolution(title)
        self.evolution_timer = self.settings.evolution_banner_frames

    def _handle_state_input(self):
        """把输入按当前状态解释成动作。

        同一个按键在不同状态下含义不同，这正是状态机存在的理由：
        - A 键 / 空格：READY / GAME_OVER = 开始游戏，PLAYING = 开火
          （在 UPGRADING 状态下它还表示"确认选中的升级"）
        - P 键 / Start：PLAYING = 暂停，PAUSED = 继续
        - ESC / B：问"真的要退出吗"；在确认框里 ESC/N/B = 不退出，Y = 退出

        返回值：这一帧状态是否发生了变化。
        """
        state_before = self.state

        # ---- 退出确认：这一屏只认"是 / 否"，别的键一律不理 ----
        if self.state is State.QUIT_CONFIRM:
            if self.input.yes_pressed:
                self._quit_game()
            elif self.input.escape_pressed or self.input.no_pressed:
                self._cancel_quit()
            return self.state is not state_before

        # ESC 在任何界面都先弹确认，不直接退 —— 防误按
        if self.input.escape_pressed:
            self._request_quit()
            return True

        if self.state is State.UPGRADING and self.upgrade_screen:
            # 三选一：方向键/十字键移动高亮，确认键/数字键选卡
            if self.input.menu_left_pressed:
                self.upgrade_screen.move(-1)
            if self.input.menu_right_pressed:
                self.upgrade_screen.move(1)
            if self.input.choice_pressed:
                index = self.input.choice_pressed - 1
                if 0 <= index < len(self.upgrade_screen.choices):
                    self.upgrade_screen.index = index
                    self._take_upgrade()
            elif self.input.confirm_pressed:
                self._take_upgrade()
            return self.state is not state_before

        if self.input.pause_pressed:
            self._toggle_pause()
        if self.state.accepts_confirm and self.input.confirm_pressed:
            self._start_game()
        return self.state is not state_before

    def run_game(self):
        while True:
            # ⓪ 限帧。这一行的作用只是"让这一轮循环至少花掉 1/60 秒"，
            #    但它是整个游戏手感的前提 —— 所有"每帧移动 N 像素"的说法
            #    都只在固定帧率下才成立。不加这一行，循环会全力跑
            #    （实测本机无头模式 1046 帧/秒），外星人一秒能横穿屏幕。
            self.clock.tick(self.settings.fps)

            # ① 先清掉上一帧的「按下」标记（按一次只触发一次）
            self.input.begin_frame()
            # ② 再处理事件，事件会写入新的意图
            self._check_events()
            # ③ 按当前状态解释输入
            state_changed = self._handle_state_input()

            # ④ 状态切换的那一帧只重画，不跑游戏逻辑。
            #
            #    A 键同时是「确认」和「开火」（空格也一样）。如果按 A 开始游戏的
            #    同一帧又跑一遍世界更新，就会立刻射出一发子弹 —— 同一个输入被
            #    新旧两个状态各解释了一次。加了这个判断，一次状态切换才是原子的。
            if not state_changed and self.state.world_moves:
                self.ship.update(self.input.read_direction())
                # 单发（fire_pressed，按下那一刻） vs 按住连发（auto_fire 升级后）
                if self.input.fire_pressed or (
                    self.settings.auto_fire and self.input.fire_held
                ):
                    self._fire_bullet()
                self._update_aliens()
                self._update_bullets()
                self._update_effects()

            self._update_screen()

    def _update_aliens(self):
        self._check_fleet_edges()
        self.aliens.update()
        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()
        self._check_aliens_bottom()

    def _check_fleet_edges(self):
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        # 纵向位置的真身是 base_y —— 整队下移要改它。
        # 改 rect.y 是没用的：下一帧 alien.update() 会用 base_y 重算 rect.y，
        # 一动就被冲掉。
        for alien in self.aliens.sprites():
            alien.base_y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def _ship_hit(self):
        # 受伤反馈：屏幕四边闪红（渐隐）。护盾挡下也算"被撞了"，所以放在最前面
        self.hit_flash = self.settings.hit_flash_frames

        # 神族等离子护盾：有盾先碎盾，命数不动
        if self.stats.shield > 0:
            self.stats.shield -= 1
            self.sb.prep_shield()
        else:
            self.stats.ship_left -= 1
            self.sb.prep_ships()

        if self.stats.ship_left > 0:
            self.aliens.empty()
            self.bullets.empty()
            self._create_fleet()
            self.ship.center_ship()
            sleep(0.5)
        else:
            self.state = State.GAME_OVER
            pygame.mouse.set_visible(True)

    def _check_aliens_bottom(self):
        screen_rect = self.screen.get_rect()
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= screen_rect.bottom:
                self._ship_hit()
                break


if __name__ == "__main__":
    ai = AlienInvasion()
    ai.run_game()
