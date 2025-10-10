#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  9 11:00:16 2025

@author: tux
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Keruki2004
"""

import sys
import random
import math
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QMenuBar, QMenu, QAction, QMainWindow, QStackedLayout, QGroupBox
)
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal, QRect

# --- Game Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TURRET_WIDTH = 40
TURRET_HEIGHT = 20
BULLET_RADIUS = 5
ENEMY_RADIUS = 15
ENEMY_SPEED = 2
FAST_ENEMY_SPEED = 4
BULLET_SPEED = 8
INITIAL_ENEMY_SPAWN_RATE = 900  # Modified for level system
MAX_ENEMIES = 100
SCORE_INCREMENT = 10
FAST_ENEMY_SCORE = 25
STARTING_HEALTH = 30
MAX_HEALTH = 50
HEALTH_BAR_WIDTH = 150
HEALTH_BAR_HEIGHT = 20
HEALTH_BAR_COLOR = QColor(0, 200, 0)
HEALTH_BAR_BG_COLOR = QColor(50, 50, 50)
GAME_OVER_COLOR = QColor(255, 50, 0, 150)
POWERUP_RADIUS = 14
POWERUP_SPAWN_RATE = 8000
POWERUP_DURATION = 3500
COMBO_RESET_TIME = 1.2
HIGHSCORE_FILE = "highscore.txt"

TURRET_MOVE_SPEED = 6  # px per frame

LEVEL_UP_SCORE = 150      # Points needed to next level
ENEMY_SPAWN_ACCEL = 80    # How much faster enemies spawn each level (ms)
ENEMY_MIN_SPAWN_RATE = 300 # Minimum allowed enemy spawn interval (ms)
MAX_LEVEL = 20

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def is_collision(x1, y1, r1, x2, y2, r2):
    return distance(x1, y1, x2, y2) < (r1 + r2)

def load_highscore():
    if os.path.exists(HIGHSCORE_FILE):
        with open(HIGHSCORE_FILE, "r") as f:
            try:
                return int(f.read())
            except Exception:
                return 0
    return 0

def save_highscore(score):
    with open(HIGHSCORE_FILE, "w") as f:
        f.write(str(score))

class Bullet:
    def __init__(self, x, y, angle, color=Qt.white):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed_x = BULLET_SPEED * math.cos(math.radians(angle))
        self.speed_y = BULLET_SPEED * math.sin(math.radians(angle))
        self.active = True
        self.color = color

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        if (self.x < 0 or self.x > SCREEN_WIDTH or 
            self.y < 0 or self.y > SCREEN_HEIGHT):
            self.active = False

    def draw(self, painter):
        if self.active:
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(self.x - BULLET_RADIUS), int(self.y - BULLET_RADIUS),
                                2 * BULLET_RADIUS, 2 * BULLET_RADIUS)

class Enemy:
    def __init__(self, level=1):
        speed_boost = min(level-1, 10)
        self.type = random.choices(['normal','fast'], weights=[0.7,0.3])[0]
        side = random.choice(['left', 'right'])
        if self.type == 'normal':
            base_speed = ENEMY_SPEED + 0.25 * speed_boost
        else:
            base_speed = FAST_ENEMY_SPEED + 0.25 * speed_boost
        if side == 'left':
            self.x = -ENEMY_RADIUS
            self.speed_x = base_speed
        else:
            self.x = SCREEN_WIDTH + ENEMY_RADIUS
            self.speed_x = -base_speed
        self.y = random.randint(ENEMY_RADIUS, SCREEN_HEIGHT - ENEMY_RADIUS)
        self.speed_y = 0
        self.active = True
        self.hit_flash = 0

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        if self.x < -ENEMY_RADIUS or self.x > SCREEN_WIDTH + ENEMY_RADIUS:
            self.active = False
        if self.hit_flash > 0:
            self.hit_flash -= 1

    def draw(self, painter):
        if self.active:
            color = Qt.red if self.type == 'normal' else Qt.yellow
            if self.hit_flash > 0:
                color = Qt.white
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(self.x - ENEMY_RADIUS), int(self.y - ENEMY_RADIUS),
                                2 * ENEMY_RADIUS, 2 * ENEMY_RADIUS)

class PowerUp:
    def __init__(self):
        self.type = random.choice(['health', 'rapid_fire'])
        self.x = random.randint(POWERUP_RADIUS, SCREEN_WIDTH-POWERUP_RADIUS)
        self.y = random.randint(POWERUP_RADIUS+40, SCREEN_HEIGHT-POWERUP_RADIUS-40)
        self.active = True
        self.color = QColor(0,200,255) if self.type == 'rapid_fire' else QColor(0,255,100)

    def update(self):
        pass

    def draw(self, painter):
        if self.active:
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.white)
            painter.drawEllipse(int(self.x-POWERUP_RADIUS),int(self.y-POWERUP_RADIUS),
                                2*POWERUP_RADIUS,2*POWERUP_RADIUS)
            icon = "+" if self.type=='health' else "R"
            painter.setPen(Qt.black)
            painter.setFont(QFont("Arial",12,QFont.Bold))
            painter.drawText(QRectF(self.x-POWERUP_RADIUS, self.y-POWERUP_RADIUS, 2*POWERUP_RADIUS, 2*POWERUP_RADIUS), Qt.AlignCenter, icon)

class Turret:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 360
        self.target_x = x
        self.target_y = y

    def update(self, mouse_x, mouse_y):
        self.target_x = mouse_x
        self.target_y = mouse_y
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        self.angle = math.degrees(math.atan2(dy, dx))

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def draw(self, painter):
        painter.setBrush(QBrush(Qt.darkBlue))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(int(self.x - TURRET_WIDTH / 2), int(self.y - TURRET_HEIGHT / 2),
                         TURRET_WIDTH, TURRET_HEIGHT)
        painter.save()
        painter.translate(self.x, self.y)
        painter.rotate(self.angle)
        painter.setBrush(QBrush(Qt.gray))
        painter.drawRect(0, -3, 30, 6)
        painter.restore()

# --- START SCREEN WIDGET ---
class StartScreenWidget(QWidget):
    modeSelected = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.selected_mode = None
        self.init_ui()
    
    def init_ui(self):
        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Turret Defense")
        title.setFont(QFont("Arial", 40, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)
        
        author = QLabel("Created by Keruki2004")
        author.setFont(QFont("Arial", 18, QFont.Bold))
        author.setAlignment(Qt.AlignCenter)
        vbox.addWidget(author)
        
        vbox.addSpacing(40)
        
        menu_group = QGroupBox()
        menu_layout = QVBoxLayout()
        menu_layout.setAlignment(Qt.AlignCenter)
        menu_label = QLabel("Select Game Mode:")
        menu_label.setFont(QFont("Arial", 20, QFont.Bold))
        menu_label.setAlignment(Qt.AlignCenter)
        menu_layout.addWidget(menu_label)
        
        self.classic_btn = QPushButton("Classic")
        self.classic_btn.setFont(QFont("Arial", 16))
        self.classic_btn.clicked.connect(lambda: self.select_mode("Classic"))
        menu_layout.addWidget(self.classic_btn)
        
        self.hardcore_btn = QPushButton("Hardcore")
        self.hardcore_btn.setFont(QFont("Arial", 16))
        self.hardcore_btn.clicked.connect(lambda: self.select_mode("Hardcore"))
        menu_layout.addWidget(self.hardcore_btn)
        
        self.practice_btn = QPushButton("Practice")
        self.practice_btn.setFont(QFont("Arial", 16))
        self.practice_btn.clicked.connect(lambda: self.select_mode("Practice"))
        menu_layout.addWidget(self.practice_btn)
        
        menu_group.setLayout(menu_layout)
        vbox.addWidget(menu_group)
        
        self.setLayout(vbox)
    
    def select_mode(self, mode):
        self.selected_mode = mode
        self.modeSelected.emit(mode)

class GameWidget(QWidget):
    scoreChanged = pyqtSignal(int)
    healthChanged = pyqtSignal(int)
    gameOverSignal = pyqtSignal()
    highScoreChanged = pyqtSignal(int)
    comboChanged = pyqtSignal(int)
    levelChanged = pyqtSignal(int)
    levelUpSignal = pyqtSignal(int)

    def __init__(self, game_mode="Classic"):
        super().__init__()
        self.game_mode = game_mode
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setMouseTracking(True)
        self.pause = False
        self.highscore = load_highscore()
        self.init_game()
        self.setFocusPolicy(Qt.StrongFocus)
        self.arrow_keys = {'left': False, 'right': False, 'up': False, 'down': False}
        self.rapid_fire_space_held = False

    def init_game(self):
        self.turret = Turret(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.score = 0
        self.health = STARTING_HEALTH
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        self.game_over = False
        self.last_enemy_spawn = 0
        self.rapid_fire = False
        self.rapid_fire_timer = 0
        self.combo_count = 0
        self.combo_timer = 0
        self.hud_message = ""
        self.hud_message_timer = 0
        self.level = 1
        self.level_target_score = LEVEL_UP_SCORE
        self.enemy_spawn_rate = INITIAL_ENEMY_SPAWN_RATE
        self.highScoreChanged.emit(self.highscore)
        self.scoreChanged.emit(self.score)
        self.healthChanged.emit(self.health)
        self.comboChanged.emit(self.combo_count)
        self.levelChanged.emit(self.level)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)
        self.enemy_spawn_timer = QTimer(self)
        self.enemy_spawn_timer.timeout.connect(self.spawn_enemy)
        self.enemy_spawn_timer.start(self.enemy_spawn_rate)
        self.powerup_timer = QTimer(self)
        self.powerup_timer.timeout.connect(self.spawn_powerup)
        self.powerup_timer.start(POWERUP_SPAWN_RATE)

    def mouseMoveEvent(self, event):
        self.mouse_x = event.pos().x()
        self.mouse_y = event.pos().y()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.game_over and not self.pause:
            self.fire_bullet()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_P:
            self.pause = not self.pause
            self.update()
        elif event.key() == Qt.Key_Space:
            if self.rapid_fire and not self.pause and not self.game_over:
                self.rapid_fire_space_held = True  # Start rapid fire
            elif not self.rapid_fire and not self.pause and not self.game_over:
                self.fire_bullet()
        elif event.key() == Qt.Key_Left:
            self.arrow_keys['left'] = True
        elif event.key() == Qt.Key_Right:
            self.arrow_keys['right'] = True
        elif event.key() == Qt.Key_Up:
            self.arrow_keys['up'] = True
        elif event.key() == Qt.Key_Down:
            self.arrow_keys['down'] = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.arrow_keys['left'] = False
        elif event.key() == Qt.Key_Right:
            self.arrow_keys['right'] = False
        elif event.key() == Qt.Key_Up:
            self.arrow_keys['up'] = False
        elif event.key() == Qt.Key_Down:
            self.arrow_keys['down'] = False
        elif event.key() == Qt.Key_Space:
            self.rapid_fire_space_held = False

    def try_move_turret(self):
        dx = dy = 0
        if self.arrow_keys['left']:
            dx -= TURRET_MOVE_SPEED
        if self.arrow_keys['right']:
            dx += TURRET_MOVE_SPEED
        if self.arrow_keys['up']:
            dy -= TURRET_MOVE_SPEED
        if self.arrow_keys['down']:
            dy += TURRET_MOVE_SPEED
        new_x = min(max(self.turret.x + dx, TURRET_WIDTH//2), SCREEN_WIDTH-TURRET_WIDTH//2)
        new_y = min(max(self.turret.y + dy, TURRET_HEIGHT//2), SCREEN_HEIGHT-TURRET_HEIGHT//2)
        self.turret.set_position(new_x, new_y)

    def fire_bullet(self):
        barrel_length = 30
        angle_rad = math.radians(self.turret.angle)
        bullet_start_x = self.turret.x + barrel_length * math.cos(angle_rad)
        bullet_start_y = self.turret.y + barrel_length * math.sin(angle_rad)
        color = Qt.cyan if self.rapid_fire else Qt.white
        self.bullets.append(Bullet(bullet_start_x, bullet_start_y, self.turret.angle, color))

    def spawn_enemy(self):
        if len(self.enemies) < MAX_ENEMIES and not self.game_over and not self.pause:
            self.enemies.append(Enemy(level=self.level))

    def spawn_powerup(self):
        if not self.game_over and not self.pause:
            self.powerups.append(PowerUp())

    def activate_powerup(self, powerup):
        if powerup.type == "health":
            self.health = min(MAX_HEALTH, self.health + 10)
            self.healthChanged.emit(self.health)
            self.show_hud_message("HEALTH UP!", QColor(0,255,128))
        elif powerup.type == "rapid_fire":
            self.rapid_fire = True
            self.rapid_fire_timer = POWERUP_DURATION // 16
            self.show_hud_message("RAPID FIRE!", QColor(0,200,255))
        else:
            self.show_hud_message("POWER UP!", QColor(255,255,255))

    def show_hud_message(self, text, color=Qt.white, duration=70):
        self.hud_message = text
        self.hud_message_color = color
        self.hud_message_timer = duration

    def check_level_up(self):
        if self.level < MAX_LEVEL and self.score >= self.level * LEVEL_UP_SCORE:
            self.level += 1
            self.levelChanged.emit(self.level)
            self.levelUpSignal.emit(self.level)
            self.show_hud_message(f"Level {self.level}!", QColor(0,255,255), 80)
            self.enemy_spawn_rate = max(INITIAL_ENEMY_SPAWN_RATE - ENEMY_SPAWN_ACCEL * (self.level-1), ENEMY_MIN_SPAWN_RATE)
            self.enemy_spawn_timer.stop()
            self.enemy_spawn_timer.start(self.enemy_spawn_rate)

    def update_game(self):
        if self.game_over or self.pause:
            return

        self.try_move_turret()
        self.turret.update(self.mouse_x, self.mouse_y)

        for bullet in self.bullets:
            bullet.update()
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo_count = 0
                self.comboChanged.emit(self.combo_count)
        if self.rapid_fire:
            self.rapid_fire_timer -= 1
            if self.rapid_fire_space_held and self.rapid_fire_timer % 3 == 0:
                self.fire_bullet()
            if self.rapid_fire_timer <= 0:
                self.rapid_fire = False
                self.rapid_fire_space_held = False
        if self.hud_message_timer > 0:
            self.hud_message_timer -= 1
            if self.hud_message_timer == 0:
                self.hud_message = ""

        for enemy in self.enemies:
            enemy.update()
            if is_collision(enemy.x, enemy.y, ENEMY_RADIUS, self.turret.x, self.turret.y, TURRET_HEIGHT / 2):
                self.health -= 1
                self.healthChanged.emit(self.health)
                enemy.active = False
                if self.health <= 0:
                    self.game_over = True
                    if self.score > self.highscore:
                        save_highscore(self.score)
                        self.highscore = self.score
                        self.highScoreChanged.emit(self.highscore)
                    self.gameOverSignal.emit()
                continue
            for bullet in self.bullets:
                if bullet.active and is_collision(bullet.x, bullet.y, BULLET_RADIUS, enemy.x, enemy.y, ENEMY_RADIUS):
                    bullet.active = False
                    enemy.active = False
                    enemy.hit_flash = 5
                    prev_score = self.score
                    self.score += FAST_ENEMY_SCORE if enemy.type=="fast" else SCORE_INCREMENT
                    self.scoreChanged.emit(self.score)
                    if self.combo_timer > 0:
                        self.combo_count += 1
                    else:
                        self.combo_count = 1
                    self.combo_timer = int(COMBO_RESET_TIME*60)
                    self.comboChanged.emit(self.combo_count)
                    break

        for powerup in self.powerups:
            if powerup.active and is_collision(powerup.x, powerup.y, POWERUP_RADIUS, self.turret.x, self.turret.y, TURRET_HEIGHT):
                self.activate_powerup(powerup)
                powerup.active = False

        self.bullets = [bullet for bullet in self.bullets if bullet.active]
        self.enemies = [enemy for enemy in self.enemies if enemy.active]
        self.powerups = [p for p in self.powerups if p.active]
        self.check_level_up()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(Qt.black))
        painter.drawRect(self.rect())
        self.turret.draw(painter)
        for bullet in self.bullets:
            bullet.draw(painter)
        for enemy in self.enemies:
            enemy.draw(painter)
        for powerup in self.powerups:
            powerup.draw(painter)
        self.draw_health_bar(painter)
        painter.setPen(QColor(0,255,255))
        painter.setFont(QFont("Arial",18,QFont.Bold))
        painter.drawText(10, 48, f"Level: {self.level}")
        if self.combo_count > 1:
            painter.setPen(QColor(255,255,0))
            painter.setFont(QFont("Arial",18,QFont.Bold))
            painter.drawText(200,28, f"Combo x{self.combo_count}!")
        if self.hud_message:
            painter.setPen(self.hud_message_color)
            painter.setFont(QFont("Arial", 28, QFont.Bold))
            painter.drawText(self.rect().adjusted(0,100,0,-300), Qt.AlignHCenter | Qt.AlignTop, self.hud_message)
        if self.game_over:
            self.draw_game_over_screen(painter)
        if self.pause and not self.game_over:
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial",32,QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, "PAUSED")

    def draw_health_bar(self, painter):
        painter.setBrush(QBrush(HEALTH_BAR_BG_COLOR))
        painter.setPen(QPen(Qt.black))
        painter.drawRect(10, 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT)
        health_percentage = max(0, self.health / MAX_HEALTH)
        health_width = int(HEALTH_BAR_WIDTH * health_percentage)
        painter.setBrush(QBrush(HEALTH_BAR_COLOR))
        painter.drawRect(10, 10, health_width, HEALTH_BAR_HEIGHT)

    def draw_game_over_screen(self, painter):
        painter.setBrush(QBrush(GAME_OVER_COLOR))
        painter.drawRect(self.rect())
        font = QFont()
        font.setPointSize(36)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)
        text = "Game Over!"
        painter.drawText(self.rect(), Qt.AlignCenter, text)
        score_text = f"Score: {self.score}"
        painter.setFont(QFont("Arial", 20))
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignCenter, score_text)
        hs_text = f"High Score: {self.highscore}"
        painter.drawText(self.rect().adjusted(0,-50,0,-20), Qt.AlignBottom | Qt.AlignCenter, hs_text)
        painter.setFont(QFont("Arial", 20, QFont.Bold))
        painter.drawText(self.rect().adjusted(0,-100,0,-60), Qt.AlignBottom | Qt.AlignCenter, f"Level Reached: {self.level}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Turret Defense")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.stacked_layout = QStackedLayout()
        self.central_widget.setLayout(self.stacked_layout)
        self.start_screen = StartScreenWidget()
        self.start_screen.modeSelected.connect(self.start_game)
        self.stacked_layout.addWidget(self.start_screen)
        self.game_widget = None
        self.side_controls_widget = None
        self.game_screen_widget = QWidget()
        self.game_screen_layout = QHBoxLayout()
        self.game_screen_widget.setLayout(self.game_screen_layout)
        self.stacked_layout.addWidget(self.game_screen_widget)
        self.init_menubar()

    def init_game_screen(self, selected_mode):
        if self.game_widget is not None:
            self.game_widget.timer.stop()
            self.game_widget.enemy_spawn_timer.stop()
            self.game_widget.powerup_timer.stop()
            self.game_screen_layout.removeWidget(self.game_widget)
            self.game_widget.deleteLater()
            self.game_widget = None
        if self.side_controls_widget is not None:
            self.game_screen_layout.removeWidget(self.side_controls_widget)
            self.side_controls_widget.deleteLater()
            self.side_controls_widget = None

        self.game_widget = GameWidget(game_mode=selected_mode)
        self.side_controls_widget = QWidget()
        controls_layout = QVBoxLayout()
        controls_layout.setAlignment(Qt.AlignTop)
        self.score_label = QLabel("Score: 0")
        self.health_label = QLabel(f"Health: {STARTING_HEALTH}/{MAX_HEALTH}")
        self.highscore_label = QLabel(f"High Score: {self.game_widget.highscore}")
        self.combo_label = QLabel("")
        self.level_label = QLabel("Level: 1")
        font = QFont()
        font.setPointSize(14)
        self.score_label.setFont(font)
        self.health_label.setFont(font)
        self.highscore_label.setFont(font)
        self.combo_label.setFont(font)
        self.level_label.setFont(font)
        controls_layout.addWidget(self.score_label)
        controls_layout.addWidget(self.health_label)
        controls_layout.addWidget(self.highscore_label)
        controls_layout.addWidget(self.level_label)
        controls_layout.addWidget(self.combo_label)
        controls_layout.addStretch(1)
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_game)
        self.reset_button.setEnabled(False)
        controls_layout.addWidget(self.reset_button)
        self.side_controls_widget.setLayout(controls_layout)
        self.game_screen_layout.addWidget(self.game_widget)
        self.game_screen_layout.addWidget(self.side_controls_widget)
        self.game_widget.scoreChanged.connect(self.update_score_label)
        self.game_widget.healthChanged.connect(self.update_health_label)
        self.game_widget.gameOverSignal.connect(self.on_game_over)
        self.game_widget.highScoreChanged.connect(self.update_highscore_label)
        self.game_widget.comboChanged.connect(self.update_combo_label)
        self.game_widget.levelChanged.connect(self.update_level_label)
        self.game_widget.levelUpSignal.connect(self.on_level_up)

    def start_game(self, mode):
        self.init_game_screen(mode)
        self.stacked_layout.setCurrentWidget(self.game_screen_widget)

    def reset_game(self):
        cur_mode = getattr(self.game_widget, 'game_mode', 'Classic')
        self.init_game_screen(cur_mode)
        self.stacked_layout.setCurrentWidget(self.game_screen_widget)
        self.reset_button.setEnabled(False)
        self.update()

    def show_about_dialog(self):
        QMessageBox.information(self, "About Turret Defense",
            "Turret Defense Minigame\n\nCreated by Keruki2004\n\nShoot incoming enemies, collect powerups, and survive as long as you can!\n\nPython & PyQt5.")

    def show_controls_dialog(self):
        QMessageBox.information(self, "Controls",
            "Mouse: Aim\nLeft Click: Fire\nArrow Keys: Move Turret\nSpace: Fire (hold for rapid-fire)\nP: Pause/Resume\nReset Button/Menu: Restart Game")

    def update_score_label(self, score):
        self.score_label.setText(f"Score: {score}")

    def update_health_label(self, health):
        self.health_label.setText(f"Health: {health}/{MAX_HEALTH}")

    def update_highscore_label(self, hs):
        self.highscore_label.setText(f"High Score: {hs}")

    def update_combo_label(self, combo):
        if combo > 1:
            self.combo_label.setText(f"COMBO x{combo}!")
        else:
            self.combo_label.setText("")

    def update_level_label(self, level):
        self.level_label.setText(f"Level: {level}")

    def on_level_up(self, level):
        pass

    def on_game_over(self):
        self.reset_button.setEnabled(True)
        QMessageBox.information(self, "Game Over", "Game Over! Click Reset to play again.")

    def init_menubar(self):
        menubar = self.menuBar()
        game_menu = menubar.addMenu("Game")
        help_menu = menubar.addMenu("Help")
        reset_action = QAction("Reset Game", self)
        reset_action.triggered.connect(self.reset_game)
        game_menu.addAction(reset_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        game_menu.addAction(exit_action)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        controls_action = QAction("Controls", self)
        controls_action.triggered.connect(self.show_controls_dialog)
        help_menu.addAction(controls_action)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    
