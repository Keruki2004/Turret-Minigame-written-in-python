#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


@author: Keruki2004
"""


import sys
import random
import math
from PyQt5.QtWidgets import QApplication, QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont, QPixmap
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal, QPointF, QRect
import numpy as np

# --- Game Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TURRET_WIDTH = 40
TURRET_HEIGHT = 20
BULLET_RADIUS = 5
ENEMY_RADIUS = 15
ENEMY_SPEED = 2  # px per frame
BULLET_SPEED = 8  # px per frame
ENEMY_SPAWN_RATE = 1  # milliseconds between enemy spawns
MAX_ENEMIES = 100
SCORE_INCREMENT = 10
STARTING_HEALTH =20
MAX_HEALTH = 50  # Add max health
HEALTH_BAR_WIDTH = 150
HEALTH_BAR_HEIGHT = 50
HEALTH_BAR_COLOR = QColor(0, 200, 0)
HEALTH_BAR_BG_COLOR = QColor(50, 50, 50)
GAME_OVER_COLOR = QColor(255, 50, 0, 150)  # Semi-transparent red for game over screen


# --- Helper Functions ---
def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def is_collision(x1, y1, r1, x2, y2, r2):
    return distance(x1, y1, x2, y2) < (r1 + r2)


# --- Game Objects ---
class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed_x = BULLET_SPEED * math.cos(math.radians(angle))
        self.speed_y = BULLET_SPEED * math.sin(math.radians(angle))
        self.active = True  # To track if bullet is still active (not hit)

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        # Deactivate bullets that go off screen
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, painter):
        if self.active:
            painter.setBrush(QBrush(Qt.white))  # Set bullet color
            painter.drawEllipse(int(self.x - BULLET_RADIUS), int(self.y - BULLET_RADIUS),
                                2 * BULLET_RADIUS, 2 * BULLET_RADIUS)


class Enemy:
    def __init__(self):
        # Start enemies from the left or right
        side = random.choice(['left', 'right'])
        if side == 'left':
            self.x = -ENEMY_RADIUS  # start off-screen to the left
            self.y = random.randint(ENEMY_RADIUS, SCREEN_HEIGHT - ENEMY_RADIUS)
            self.speed_x = ENEMY_SPEED
        else:
            self.x = SCREEN_WIDTH + ENEMY_RADIUS  # start off-screen to the right
            self.y = random.randint(ENEMY_RADIUS, SCREEN_HEIGHT - ENEMY_RADIUS)
            self.speed_x = -ENEMY_SPEED
        self.speed_y = 0  # Initially no vertical movement
        self.active = True  # Track if the enemy is alive

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        # Deactivate if off screen (simplified, could add more complex behaviour)
        if self.x < -ENEMY_RADIUS or self.x > SCREEN_WIDTH + ENEMY_RADIUS or self.y < -ENEMY_RADIUS or self.y > SCREEN_HEIGHT + ENEMY_RADIUS:
            self.active = False

    def draw(self, painter):
        if self.active:
            painter.setBrush(QBrush(Qt.red))  # Set enemy color
            painter.drawEllipse(int(self.x - ENEMY_RADIUS), int(self.y - ENEMY_RADIUS),
                                2 * ENEMY_RADIUS, 2 * ENEMY_RADIUS)


class Turret:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 360  # In degrees
        self.target_x = x
        self.target_y = y

    def update(self, mouse_x, mouse_y):
        # Aim at mouse position
        self.target_x = mouse_x
        self.target_y = mouse_y
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        self.angle = math.degrees(math.atan2(dy, dx))  # Calculate angle

    def draw(self, painter):
        # Turret body
        painter.setBrush(QBrush(Qt.darkBlue))  # Set turret color
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(int(self.x - TURRET_WIDTH / 2), int(self.y - TURRET_HEIGHT / 2),
                         TURRET_WIDTH, TURRET_HEIGHT)
        # Turret barrel (rotated)
        painter.save()  # Save the current transformation matrix
        painter.translate(self.x, self.y)  # Translate to the turret's center
        painter.rotate(self.angle)  # Rotate around the center
        painter.setBrush(QBrush(Qt.gray))
        painter.drawRect(0, -3, 30, 6)  # Draw the barrel
        painter.restore()  # Restore the previous transformation matrix


# --- Custom Widget for the Game ---
class GameWidget(QWidget):
    scoreChanged = pyqtSignal(int)
    healthChanged = pyqtSignal(int)
    gameOverSignal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setMouseTracking(True)  # Important to track mouse movement even if no button is pressed
        self.init_game()  # Initialize game elements

    def init_game(self):
        self.turret = Turret(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)  # Turret at the bottom
        self.bullets = []
        self.enemies = []
        self.score = 0
        self.health = STARTING_HEALTH
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        self.game_over = False
        self.last_enemy_spawn = 0
        self.scoreChanged.emit(self.score)
        self.healthChanged.emit(self.health)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)  # ~60 frames per second (1000ms / 60frames)
        self.enemy_spawn_timer = QTimer(self)
        self.enemy_spawn_timer.timeout.connect(self.spawn_enemy)
        self.enemy_spawn_timer.start(ENEMY_SPAWN_RATE)

    def mouseMoveEvent(self, event):
        self.mouse_x = event.pos().x()
        self.mouse_y = event.pos().y()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.game_over:
            self.fire_bullet()

    def fire_bullet(self):
        # Calculate bullet starting position (at the barrel)
        barrel_length = 30
        angle_rad = math.radians(self.turret.angle)
        bullet_start_x = self.turret.x + barrel_length * math.cos(angle_rad)
        bullet_start_y = self.turret.y + barrel_length * math.sin(angle_rad)
        self.bullets.append(Bullet(bullet_start_x, bullet_start_y, self.turret.angle))
        # You could add a sound effect here (using a library like PyAudio)

    def spawn_enemy(self):
        if len(self.enemies) < MAX_ENEMIES and not self.game_over:
            self.enemies.append(Enemy())

    def update_game(self):
        if self.game_over:
            return
        self.turret.update(self.mouse_x, self.mouse_y)
        # Update Bullets
        for bullet in self.bullets:
            bullet.update()
        # Update Enemies and Check for Collisions
        for enemy in self.enemies:
            enemy.update()
            # Enemy hits turret - simple implementation
            if is_collision(enemy.x, enemy.y, ENEMY_RADIUS, self.turret.x, self.turret.y, TURRET_HEIGHT / 2):
                self.health -= 1
                self.healthChanged.emit(self.health)
                enemy.active = False  # Remove enemy
                if self.health <= 0:
                    self.game_over = True
                    self.gameOverSignal.emit()
                continue  # Skip the collision checks if enemy already inactive due to hitting the turret
            # Check for Bullet Collisions
            for bullet in self.bullets:
                if bullet.active and is_collision(bullet.x, bullet.y, BULLET_RADIUS, enemy.x, enemy.y, ENEMY_RADIUS):
                    bullet.active = False  # Deactivate the bullet
                    enemy.active = False  # Deactivate the enemy
                    self.score += SCORE_INCREMENT
                    self.scoreChanged.emit(self.score)
                    break  # Bullet only hits one enemy at a time
        # Remove inactive bullets and enemies
        self.bullets = [bullet for bullet in self.bullets if bullet.active]
        self.enemies = [enemy for enemy in self.enemies if enemy.active]
        self.update()  # Redraw the scene

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # Smoother rendering
        # --- Draw Game Elements ---
        # Background (example)
        painter.setBrush(QBrush(Qt.black))
        painter.drawRect(self.rect())
        # Turret
        self.turret.draw(painter)
        # Bullets
        for bullet in self.bullets:
            bullet.draw(painter)
        # Enemies
        for enemy in self.enemies:
            enemy.draw(painter)
        # Draw Health Bar
        self.draw_health_bar(painter)
        # Game Over Screen
        if self.game_over:
            self.draw_game_over_screen(painter)

    def draw_health_bar(self, painter):
        # Background
        painter.setBrush(QBrush(HEALTH_BAR_BG_COLOR))
        painter.setPen(QPen(Qt.black))  # Optional: Add a border
        painter.drawRect(10, 10, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT)
        # Health
        health_percentage = max(0, self.health / MAX_HEALTH)  # Ensure health doesn't go below zero
        health_width = int(HEALTH_BAR_WIDTH * health_percentage)
        painter.setBrush(QBrush(HEALTH_BAR_COLOR))
        painter.setPen(QPen(Qt.black))
        painter.drawRect(10, 10, health_width, HEALTH_BAR_HEIGHT)

    def draw_game_over_screen(self, painter):
        painter.setBrush(QBrush(GAME_OVER_COLOR))
        painter.drawRect(self.rect())  # Cover entire screen
        # Game Over Text
        font = QFont()
        font.setPointSize(36)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)
        text = "Game Over!"
        text_rect = painter.boundingRect(self.rect(), Qt.AlignCenter, text)  # Get rectangle size
        painter.drawText(self.rect(), Qt.AlignCenter, text)  # Center the text
        # Display Score (optional)
        score_text = f"Score: {self.score}"
        painter.setFont(QFont("Arial", 20))  # Smaller font
        score_rect = painter.boundingRect(self.rect(), Qt.AlignBottom | Qt.AlignCenter, score_text)
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignCenter, score_text)


# --- Main Window ---
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Turret Defense")
        self.init_ui()

    def init_ui(self):
        self.game_widget = GameWidget()
        # Score and Health Labels
        self.score_label = QLabel("Score: 0")
        self.health_label = QLabel(f"Health: {STARTING_HEALTH}/{MAX_HEALTH}")
        font = QFont()
        font.setPointSize(14)  # Bigger font
        self.score_label.setFont(font)
        self.health_label.setFont(font)
        # Layout
        controls_layout = QVBoxLayout()  # Add a layout for the reset button
        controls_layout.addWidget(self.score_label)
        controls_layout.addWidget(self.health_label)
        controls_layout.addStretch(1)  # Push items to the top
        # Add reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_game)
        self.reset_button.setEnabled(False)  # Disable it initially
        controls_layout.addWidget(self.reset_button)
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.game_widget)
        main_layout.addLayout(controls_layout)  # Add controls layout
        self.setLayout(main_layout)
        self.game_widget.scoreChanged.connect(self.update_score_label)
        self.game_widget.healthChanged.connect(self.update_health_label)
        self.game_widget.gameOverSignal.connect(self.on_game_over)

    def update_score_label(self, score):
        self.score_label.setText(f"Score: {score}")

    def update_health_label(self, health):
        self.health_label.setText(f"Health: {health}/{MAX_HEALTH}")

    def on_game_over(self):
        self.reset_button.setEnabled(True)

    def reset_game(self):
        # Remove and re-create the game widget
        self.game_widget.timer.stop()  # Stop the timer
        self.game_widget.enemy_spawn_timer.stop()
        self.game_widget.deleteLater()  # Clean up the widget
        self.game_widget = GameWidget()  # Re-create
        self.game_widget.scoreChanged.connect(self.update_score_label)
        self.game_widget.healthChanged.connect(self.update_health_label)
        self.game_widget.gameOverSignal.connect(self.on_game_over)
        # Replace the old widget in the layout
        # Find the current index of the game widget in the layout.
        index = self.layout().indexOf(self.layout().itemAt(0).widget())  # Assumes game widget is first
        self.layout().replaceWidget(self.layout().itemAt(0).widget(), self.game_widget)  # find existing and replace
        self.reset_button.setEnabled(False)  # Disable the reset button again
        self.update()  # re-draw


# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())  # Ensure the app exits cleanly
    
    
    
from numpy import pi, sin
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons

def signal(amp, freq):
    return amp * sin(2 * pi * freq * t)

axis_color = 'lightgoldenrodyellow'

fig = plt.figure()
ax = fig.add_subplot(111)

# Adjust the subplots region to leave some space for the sliders and buttons
fig.subplots_adjust(left=0.25, bottom=0.25)

t = np.arange(0.0, 1.0, 0.001)
amp_0 = 5
freq_0 = 3

# Draw the initial plot
# The 'line' variable is used for modifying the line later
[line] = ax.plot(t, signal(amp_0, freq_0), linewidth=2, color='red')
ax.set_xlim([0, 1])
ax.set_ylim([-10, 10])

# Add two sliders for tweaking the parameters#

# Define an axes area and draw a slider in it
amp_slider_ax  = fig.add_axes([0.25, 0.15, 0.65, 0.03], facecolor=axis_color)
amp_slider = Slider(amp_slider_ax, 'Amp', 0.1, 10.0, valinit=amp_0)

# Draw another slider
freq_slider_ax = fig.add_axes([0.25, 0.1, 0.65, 0.03], facecolor=axis_color)
freq_slider = Slider(freq_slider_ax, 'Freq', 0.1, 30.0, valinit=freq_0)

# Define an action for modifying the line when any slider's value changes
def sliders_on_changed(val):
    line.set_ydata(signal(amp_slider.val, freq_slider.val))
    fig.canvas.draw_idle()
amp_slider.on_changed(sliders_on_changed)
freq_slider.on_changed(sliders_on_changed)

# Add a button for resetting the parameters
reset_button_ax = fig.add_axes([0.8, 0.025, 0.1, 0.04])
reset_button = Button(reset_button_ax, 'Reset', color=axis_color, hovercolor='0.975')
def reset_button_on_clicked(mouse_event):
    freq_slider.reset()
    amp_slider.reset()
reset_button.on_clicked(reset_button_on_clicked)

# Add a set of radio buttons for changing color
color_radios_ax = fig.add_axes([0.025, 0.5, 0.15, 0.15], facecolor=axis_color)
color_radios = RadioButtons(color_radios_ax, ('red', 'blue', 'green'), active=0)
def color_radios_on_clicked(label):
    line.set_color(label)
    fig.canvas.draw_idle()
color_radios.on_clicked(color_radios_on_clicked)

plt.show()    
