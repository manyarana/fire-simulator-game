import pygame
import random
import sys
import os
import math
import time

# ==============================================================================
# SECTION 1: HARDWARE DRIVER
# ==============================================================================
HARDWARE_CONNECTED = False
ads = None
GPIO = None

try:
    import board
    import busio
    import RPi.GPIO as GPIO
    from adafruit_ads1x15.analog_in import AnalogIn
    from adafruit_ads1x15.ads1115 import ADS1115

    # Initialize I2C and ADS1115
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS1115(i2c)
    GPIO.setmode(GPIO.BCM)
    HARDWARE_CONNECTED = True
    print("[HW] Hardware Driver Loaded Successfully.")
except Exception as e:
    print(f"[HW] Hardware warning: {e}")
    print("[HW] Running in KEYBOARD ONLY mode.")

class JoystickHandler:
    def _init_(self, ch_x_num, ch_y_num, pin_sw):
        self.ch_x_num = ch_x_num
        self.ch_y_num = ch_y_num
        self.pin = pin_sw
        
        # State variables
        self.norm_x = 0.0
        self.norm_y = 0.0
        self.is_pressed = False
        self.just_pressed = False # For menu clicking (one-shot)
        self.prev_pressed = False
        
        self.center = 15000
        self.deadzone = 2000

        self.ax_obj = None
        self.ay_obj = None
        
        if HARDWARE_CONNECTED:
            try:
                self.ax_obj = AnalogIn(ads, ch_x_num)
                self.ay_obj = AnalogIn(ads, ch_y_num)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception as e:
                print(f"Error setting up joystick channels {ch_x_num}/{ch_y_num}: {e}")

    def update(self):
        if not HARDWARE_CONNECTED or not self.ax_obj:
            return

        # 1. READ BUTTON (Active Low)
        try:
            current_btn_state = (GPIO.input(self.pin) == 0)
            self.is_pressed = current_btn_state
            
            # Logic for "Just Pressed" (useful for menus to prevent spamming)
            if current_btn_state and not self.prev_pressed:
                self.just_pressed = True
            else:
                self.just_pressed = False
            self.prev_pressed = current_btn_state
            
        except: pass

        # 2. READ ANALOG
        try:
            raw_x = self.ax_obj.value
            raw_y = self.ay_obj.value

            # X Calculation
            diff_x = raw_x - self.center
            if abs(diff_x) < self.deadzone: self.norm_x = 0.0
            else: self.norm_x = diff_x / 15000.0

            # Y Calculation
            diff_y = raw_y - self.center
            if abs(diff_y) < self.deadzone: self.norm_y = 0.0
            else: self.norm_y = diff_y / 15000.0

            # Clamp
            self.norm_x = max(-1.0, min(1.0, self.norm_x))
            self.norm_y = max(-1.0, min(1.0, self.norm_y))
        except: pass

# ==============================================================================
# SECTION 2: GAME CODE
# ==============================================================================

# --- Pygame Setup ---
pygame.init()

# --- Game Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480 # Updated to 480px as requested
UI_HEIGHT = 40

# Grid system
TILE_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = (SCREEN_HEIGHT - UI_HEIGHT) // TILE_SIZE 

PLAYER_SIZE = 25
GAME_DURATION_SEC = 60
LEVEL_1_FIRE_COUNT = 6

# --- MECHANICS CONSTANTS ---
FIRE_SPREAD_CHANCE = 0.25
MAX_FIRE_PERCENTAGE = 0.5
OBSTACLE_SPAWN_RATE_MS = 5000 
PENALTY_DURATION_MS = 3000

# ZOMBIE SETTINGS
ZOMBIE_COUNT_NORMAL = 3 # Updated to 3
ZOMBIE_COUNT_PARKINSONS = 2 # Updated for Parkinsons Level 4
ZOMBIE_SPEED = 1.5         
PARKINSON_ZOMBIE_SPEED = 0.7 # Slower speed for Parkinson's mode
FLAME_ZOMBIE_SPEED = 1.7   

# --- Tile Types ---
TILE_GRASS = 0
TILE_TREE = 1
BURNT_GROUND = 2
TILE_DIRT = 3
TILE_BUSH = 4
TILE_FLOWERS = 5
TILE_OBSTACLE = 6

# --- Colors ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)             
FLAME_ZOMBIE_COLOR = (255, 69, 0) 
BROWN = (139, 69, 19)
DARK_GREEN = (0, 100, 0)
OBSTACLE_COLOR = (128, 128, 128) 
ZOMBIE_GREEN = (50, 205, 50)     
HEART_RED = (220, 20, 60)        
PURPLE = (128, 0, 128)
UI_BG_COLOR = (30, 30, 30) 
GOLD_SPEED = (255, 215, 0)

# Tree Colors
TREE_TRUNK_LIGHT = (160, 82, 45)
TREE_TRUNK_DARK = (101, 51, 0)
TREE_LEAVES_LIGHT = (124, 252, 0)
TREE_LEAVES_MEDIUM = (34, 139, 34)
TREE_LEAVES_DARK = (0, 100, 0)
COLOR_BURNT_GROUND = (50, 50, 50)
WATER_BLUE = (173, 216, 230)
DIRT_COLOR = (139, 69, 19)
BUSH_COLOR_LIGHT = (0, 155, 0)
BUSH_COLOR_DARK = (0, 120, 0)
FLOWER_COLOR_1 = (255, 0, 255)
FLOWER_COLOR_2 = (255, 255, 0)
FLOWER_COLOR_3 = (255, 255, 255)

# --- Player Colors ---
PLAYER_SKIN_WHITE = (255, 255, 255)
PLAYER_SKIN_BLACK = (50, 50, 50)
PLAYER_SKIN_BROWN = (160, 82, 45)
PLAYER_HELMET_BLUE = (0, 0, 255)
PLAYER_HELMET_RED = (255, 0, 0)
PLAYER_HELMET_GREEN = (0, 128, 0)

# --- Game States ---
STATE_START_MENU = 0
STATE_PLAYER_SELECT = 1
STATE_MODE_SELECT = 2
STATE_LEVEL_SELECT = 3
STATE_GAME_STARTING = 4 
STATE_GAME_RUNNING = 5
STATE_GAME_PAUSED = 6   
STATE_GAME_OVER = 7
STATE_GAME_WON = 8
STATE_PAUSED_MENU = 9
STATE_GAME_PENALTY = 10 

# --- Custom Pygame Events ---
FIRE_SPREAD_EVENT = pygame.USEREVENT + 1
OBSTACLE_SPAWN_EVENT = pygame.USEREVENT + 2

# --- Setup the Screen ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Forest Fire")
clock = pygame.time.Clock()

# --- Font Loading ---
FONT_FILENAME = "PressStart2P-Regular.ttf"

def load_font(custom_font_path, size):
    try:
        return pygame.font.Font(custom_font_path, size)
    except (pygame.error, FileNotFoundError):
        if size >= 40: default_size = 74
        elif size >= 25: default_size = 50
        elif size >= 15: default_size = 36
        else: default_size = 24
        return pygame.font.Font(None, default_size)

# Fonts
font_large = load_font(FONT_FILENAME, 40)
font_huge = load_font(FONT_FILENAME, 75)
font_medium = load_font(FONT_FILENAME, 28)
font_small = load_font(FONT_FILENAME, 18) 
font_menu_title = load_font(FONT_FILENAME, 24)
font_menu_item = load_font(FONT_FILENAME, 18)
font_menu_tiny = load_font(FONT_FILENAME, 12)

# Fire Particle Surface
fire_particle_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# --- Game Variables ---
game_state = STATE_START_MENU
score = 0
high_score = 0
game_start_time = 0
pause_start_time = 0
penalty_start_time = 0 
total_paused_time = 0
time_remaining = GAME_DURATION_SEC
current_level_id = 1 

selected_player_index = 0
selected_mode_index = 0 
selected_level_index = 0 

player_rect = pygame.Rect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
player_base_speed = 5
player_speed = player_base_speed
player_skin_color = PLAYER_SKIN_WHITE
player_helmet_color = PLAYER_HELMET_BLUE
player_direction = 'down'
player_lives = 3
last_damage_time = 0 

has_water_powerup = False 
has_speed_powerup = False

game_grid = []
fire_tiles = set()
obstacle_tiles = set() 
total_tiles = GRID_WIDTH * GRID_HEIGHT

water_particles = []
fire_particles = []
zombies = [] 
flame_zombies = [] # Changed to list for multiple flame zombies

water_powerup_rect = None 
speed_powerup_rect = None # New Speed Powerup
heart_powerup_rect = None # New Heart Powerup

# Menu Navigation Timers (for Joystick Debounce)
last_menu_move_time = 0
MENU_MOVE_DELAY = 200 # milliseconds

try:
    jungle_background_image = pygame.image.load(os.path.join('jungle_background.png')).convert()
    jungle_background_image = pygame.transform.scale(jungle_background_image, (SCREEN_WIDTH, SCREEN_HEIGHT - UI_HEIGHT))
except (pygame.error, FileNotFoundError):
    jungle_background_image = None

# --- Helper Functions ---

def draw_text(text, font, color, surface, x, y, center=False):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

def create_grid():
    global game_grid, fire_tiles, obstacle_tiles
    game_grid = []
    fire_tiles = set()
    obstacle_tiles = set()
    
    for y in range(GRID_HEIGHT):
        row = [TILE_GRASS] * GRID_WIDTH
        game_grid.append(row)

    # Add Dirt
    for _ in range(int(total_tiles * 0.1)):
        x, y = random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1)
        if game_grid[y][x] == TILE_GRASS: game_grid[y][x] = TILE_DIRT
    
    # Add Bushes
    for _ in range(int(total_tiles * 0.05)):
        x, y = random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1)
        if game_grid[y][x] == TILE_GRASS: game_grid[y][x] = TILE_BUSH

    # Add Flowers
    for _ in range(int(total_tiles * 0.03)):
        x, y = random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1)
        if game_grid[y][x] == TILE_GRASS: game_grid[y][x] = TILE_FLOWERS

    # Add Trees
    for _ in range(int(total_tiles * 0.1)):
        x, y = random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1)
        game_grid[y][x] = TILE_TREE

def find_spawnable_spot():
    for _ in range(100):
        x = random.randint(0, GRID_WIDTH - 1)
        y = random.randint(0, GRID_HEIGHT - 1)
        if (game_grid[y][x] not in [TILE_TREE, BURNT_GROUND] and 
            (x,y) not in fire_tiles and 
            (x,y) not in obstacle_tiles):
            
            screen_x = x * TILE_SIZE
            screen_y = y * TILE_SIZE + UI_HEIGHT
            
            tile_rect = pygame.Rect(screen_x, screen_y, TILE_SIZE, TILE_SIZE)
            # Ensure not spawning too close to player
            if not tile_rect.colliderect(player_rect.inflate(150, 150)):
                return (x, y)
    return None

def spawn_initial_fire(count=1):
    global fire_tiles
    fire_tiles = set() 
    for _ in range(count):
        spot = find_spawnable_spot()
        if spot: fire_tiles.add(spot)
            
def spawn_new_fire_cluster(count=1):
    for _ in range(count):
        spot = find_spawnable_spot()
        if spot: fire_tiles.add(spot)

def spawn_obstacle():
    spot = find_spawnable_spot()
    if spot:
        obstacle_tiles.add(spot)

def spawn_zombie():
    spot = find_spawnable_spot()
    if spot:
        z_x = spot[0] * TILE_SIZE
        z_y = spot[1] * TILE_SIZE + UI_HEIGHT
        zombies.append([float(z_x), float(z_y), pygame.Rect(z_x, z_y, PLAYER_SIZE, PLAYER_SIZE)])

def spawn_flame_zombie():
    spot = find_spawnable_spot()
    if spot:
        z_x = spot[0] * TILE_SIZE
        z_y = spot[1] * TILE_SIZE + UI_HEIGHT
        flame_zombies.append([float(z_x), float(z_y), pygame.Rect(z_x, z_y, PLAYER_SIZE, PLAYER_SIZE)])

def spawn_water_powerup():
    global water_powerup_rect
    spot = find_spawnable_spot()
    if spot:
        water_powerup_rect = pygame.Rect(spot[0] * TILE_SIZE + 5, spot[1] * TILE_SIZE + UI_HEIGHT + 5, 10, 10)

def spawn_speed_powerup():
    global speed_powerup_rect
    spot = find_spawnable_spot()
    if spot:
        speed_powerup_rect = pygame.Rect(spot[0] * TILE_SIZE + 2, spot[1] * TILE_SIZE + UI_HEIGHT + 2, 16, 16)

def spawn_heart_powerup():
    global heart_powerup_rect
    spot = find_spawnable_spot()
    if spot:
        heart_powerup_rect = pygame.Rect(spot[0] * TILE_SIZE + 2, spot[1] * TILE_SIZE + UI_HEIGHT + 2, 16, 16)

def spread_fire():
    global game_grid, fire_tiles
    if current_level_id < 4 and current_level_id != 8: return
        
    new_fires = set() 
    for (x, y) in list(fire_tiles):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if (game_grid[ny][nx] != BURNT_GROUND and 
                    (nx, ny) not in fire_tiles and
                    (nx, ny) not in obstacle_tiles):
                    if random.random() < FIRE_SPREAD_CHANCE:
                        new_fires.add((nx, ny))
    fire_tiles.update(new_fires)

def draw_jungle_and_fire():
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tile_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE + UI_HEIGHT, TILE_SIZE, TILE_SIZE)
            tile_type = game_grid[y][x]
            
            if tile_type == TILE_GRASS:
                pygame.draw.rect(screen, DARK_GREEN, tile_rect)
            elif tile_type == TILE_DIRT:
                pygame.draw.rect(screen, DIRT_COLOR, tile_rect)
            elif tile_type == TILE_BUSH:
                pygame.draw.rect(screen, DARK_GREEN, tile_rect)
                pygame.draw.circle(screen, BUSH_COLOR_DARK, (tile_rect.centerx + 3, tile_rect.centery + 3), 6)
                pygame.draw.circle(screen, BUSH_COLOR_LIGHT, (tile_rect.centerx, tile_rect.centery), 5)
            elif tile_type == TILE_FLOWERS:
                pygame.draw.rect(screen, DARK_GREEN, tile_rect)
                pygame.draw.rect(screen, FLOWER_COLOR_1, (tile_rect.x + 5, tile_rect.y + 5, 3, 3))
                pygame.draw.rect(screen, FLOWER_COLOR_2, (tile_rect.x + 12, tile_rect.y + 10, 3, 3))
                pygame.draw.rect(screen, FLOWER_COLOR_3, (tile_rect.x + 8, tile_rect.y + 15, 3, 3))
            elif tile_type == TILE_TREE:
                pygame.draw.rect(screen, TREE_TRUNK_DARK, (tile_rect.x + 4, tile_rect.y + 17, 12, 3))
                pygame.draw.rect(screen, TREE_TRUNK_LIGHT, (tile_rect.x + 5, tile_rect.y + 17, 10, 3))
                pygame.draw.rect(screen, TREE_TRUNK_DARK, (tile_rect.x + 6, tile_rect.y + 10, 8, 7))
                pygame.draw.rect(screen, TREE_TRUNK_LIGHT, (tile_rect.x + 7, tile_rect.y + 10, 6, 7))
                pygame.draw.rect(screen, TREE_TRUNK_DARK, (tile_rect.x + 9, tile_rect.y + 13, 2, 2))
                pygame.draw.rect(screen, TREE_LEAVES_DARK, (tile_rect.x + 2, tile_rect.y + 10, 16, 4))
                pygame.draw.rect(screen, TREE_LEAVES_MEDIUM, (tile_rect.x + 3, tile_rect.y + 10, 14, 3))
                pygame.draw.rect(screen, TREE_LEAVES_DARK, (tile_rect.x + 0, tile_rect.y + 6, 20, 4))
                pygame.draw.rect(screen, TREE_LEAVES_MEDIUM, (tile_rect.x + 1, tile_rect.y + 6, 18, 3))
                pygame.draw.rect(screen, TREE_LEAVES_LIGHT, (tile_rect.x + 4, tile_rect.y + 7, 12, 2))
                pygame.draw.rect(screen, TREE_LEAVES_DARK, (tile_rect.x + 4, tile_rect.y + 2, 12, 4))
                pygame.draw.rect(screen, TREE_LEAVES_MEDIUM, (tile_rect.x + 5, tile_rect.y + 2, 10, 3))
                pygame.draw.rect(screen, TREE_LEAVES_LIGHT, (tile_rect.x + 7, tile_rect.y + 3, 6, 1))
            elif tile_type == BURNT_GROUND:
                pygame.draw.rect(screen, COLOR_BURNT_GROUND, tile_rect)

    for (ox, oy) in obstacle_tiles:
        r = pygame.Rect(ox * TILE_SIZE, oy * TILE_SIZE + UI_HEIGHT, TILE_SIZE, TILE_SIZE)
        pygame.draw.ellipse(screen, OBSTACLE_COLOR, r)
        pygame.draw.ellipse(screen, (169, 169, 169), (r.x + 4, r.y + 4, 8, 8))

def update_and_draw_fire_particles():
    global fire_particles
    fire_particle_surface.fill((0, 0, 0, 0))
    for i in range(len(fire_particles) - 1, -1, -1):
        particle = fire_particles[i]
        particle[0] += particle[2]
        particle[1] += particle[3]
        particle[4] -= 1
        particle[6] -= 0.1
        if particle[4] <= 0 or particle[6] <= 0:
            fire_particles.pop(i)
        else:
            pos = (int(particle[0]), int(particle[1]))
            pygame.draw.circle(fire_particle_surface, particle[5], pos, int(particle[6]))

    if game_state in [STATE_GAME_RUNNING, STATE_GAME_STARTING, STATE_GAME_PAUSED, STATE_GAME_PENALTY]:
        for (x, y) in fire_tiles:
            is_tree = game_grid[y][x] == TILE_TREE
            for _ in range(random.randint(1, 2)):
                px = x * TILE_SIZE + random.uniform(5, TILE_SIZE - 5)
                if is_tree: py = y * TILE_SIZE + UI_HEIGHT + random.uniform(2, TILE_SIZE - 10) 
                else: py = y * TILE_SIZE + UI_HEIGHT + random.uniform(TILE_SIZE // 2, TILE_SIZE)
                p_x_vel = random.uniform(-0.5, 0.5)
                p_y_vel = random.uniform(-1.5, -0.5)
                p_lifetime = random.randint(20, 40)
                p_color = random.choice([RED, ORANGE, YELLOW])
                p_radius = random.uniform(3, 6)
                fire_particles.append([px, py, p_x_vel, p_y_vel, p_lifetime, p_color, p_radius])
    screen.blit(fire_particle_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

def draw_zombies():
    for z_data in zombies:
        z_rect = z_data[2]
        pygame.draw.rect(screen, ZOMBIE_GREEN, z_rect)
        pygame.draw.rect(screen, RED, (z_rect.x + 5, z_rect.y + 5, 5, 5))
        pygame.draw.rect(screen, RED, (z_rect.x + 15, z_rect.y + 5, 5, 5))
        pygame.draw.rect(screen, ZOMBIE_GREEN, (z_rect.x - 5, z_rect.y + 10, 5, 8))
        pygame.draw.rect(screen, ZOMBIE_GREEN, (z_rect.x + PLAYER_SIZE, z_rect.y + 10, 5, 8))

def draw_flame_zombies():
    for fz in flame_zombies:
        z_rect = fz[2]
        pygame.draw.rect(screen, FLAME_ZOMBIE_COLOR, z_rect) 
        pygame.draw.rect(screen, YELLOW, (z_rect.x + 5, z_rect.y + 5, 5, 5))
        pygame.draw.rect(screen, YELLOW, (z_rect.x + 15, z_rect.y + 5, 5, 5))
        pygame.draw.polygon(screen, YELLOW, [(z_rect.x+5, z_rect.y), (z_rect.x+10, z_rect.y-8), (z_rect.x+15, z_rect.y)])

def draw_powerups():
    # Water Powerup (Diamond Shape)
    if water_powerup_rect:
        center_x = water_powerup_rect.centerx
        center_y = water_powerup_rect.centery
        size = 6
        points = [(center_x, center_y - size), (center_x + size, center_y), (center_x, center_y + size), (center_x - size, center_y)]
        pygame.draw.polygon(screen, CYAN, points)
        pygame.draw.polygon(screen, WHITE, points, 1)

    # Speed Powerup (Lightning Bolt / Yellow Square)
    if speed_powerup_rect:
        pygame.draw.rect(screen, GOLD_SPEED, speed_powerup_rect)
        pygame.draw.rect(screen, WHITE, speed_powerup_rect, 1)
        # Simple lightning symbol
        sx, sy = speed_powerup_rect.x, speed_powerup_rect.y
        points = [(sx+10, sy+2), (sx+6, sy+8), (sx+12, sy+8), (sx+4, sy+14)]
        pygame.draw.polygon(screen, RED, points)

    # Heart Powerup (Red Heart)
    if heart_powerup_rect:
        hx, hy = heart_powerup_rect.x, heart_powerup_rect.y
        # Two circles and a triangle for a heart
        pygame.draw.circle(screen, HEART_RED, (hx + 4, hy + 4), 4)
        pygame.draw.circle(screen, HEART_RED, (hx + 12, hy + 4), 4)
        pygame.draw.polygon(screen, HEART_RED, [(hx, hy+6), (hx+16, hy+6), (hx+8, hy+15)])
        pygame.draw.rect(screen, WHITE, heart_powerup_rect, 1) # Hitbox outline

def draw_hearts():
    start_x = SCREEN_WIDTH // 2 - 40 
    y = 20 
    # Draw up to 5 hearts if user gets powerups
    for i in range(5): 
        if i >= player_lives:
            if i >= 3: break # Don't draw empty slots for bonus hearts
            color = (50, 50, 50)
        else:
            color = HEART_RED
            
        x = start_x + (i * 30)
        # Simple Heart Shape
        pygame.draw.rect(screen, color, (x + 3, y, 6, 3)) 
        pygame.draw.rect(screen, color, (x + 12, y, 6, 3))
        pygame.draw.rect(screen, color, (x, y + 3, 21, 3)) 
        pygame.draw.rect(screen, color, (x, y + 6, 21, 3)) 
        pygame.draw.rect(screen, color, (x + 3, y + 9, 15, 3)) 
        pygame.draw.rect(screen, color, (x + 6, y + 12, 9, 3)) 
        pygame.draw.rect(screen, color, (x + 9, y + 15, 3, 3)) 

def draw_player_model(surface, x, y, size, skin, helmet, direction):
    s = size / 25.0
    BOOTS = (30, 30, 30)
    NOZZLE = (0, 100, 200)
    AIR_TANK = (210, 0, 0)
    STRIPE = (255, 230, 0)
    UNIFORM_COLOR = helmet 
    SKIN_COLOR = skin
    if direction == 'down':
        pygame.draw.rect(surface, BOOTS, (x+4*s, y+20*s, 7*s, 5*s))
        pygame.draw.rect(surface, BOOTS, (x+14*s, y+20*s, 7*s, 5*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+3*s, y+7*s, 19*s, 15*s), border_radius=int(2*s))
        pygame.draw.rect(surface, STRIPE, (x+3*s, y+14*s, 19*s, 3*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+5*s, y+2*s, 15*s, 10*s), border_radius=int(3*s))
        pygame.draw.rect(surface, SKIN_COLOR, (x+8*s, y+5*s, 9*s, 5*s))
        pygame.draw.rect(surface, NOZZLE, (x+9*s, y+22*s, 7*s, 3*s))
    elif direction == 'up':
        pygame.draw.rect(surface, AIR_TANK, (x+7*s, y+1*s, 11*s, 14*s), border_radius=int(3*s))
        pygame.draw.rect(surface, BOOTS, (x+4*s, y, 7*s, 5*s))
        pygame.draw.rect(surface, BOOTS, (x+14*s, y, 7*s, 5*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+3*s, y+5*s, 19*s, 15*s), border_radius=int(2*s))
        pygame.draw.rect(surface, STRIPE, (x+3*s, y+12*s, 19*s, 3*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+5*s, y+15*s, 15*s, 10*s), border_radius=int(3*s))
        pygame.draw.rect(surface, NOZZLE, (x+9*s, y, 7*s, 3*s))
    elif direction == 'left':
        pygame.draw.rect(surface, AIR_TANK, (x+15*s, y+5*s, 8*s, 14*s), border_radius=int(3*s))
        pygame.draw.rect(surface, BOOTS, (x+4*s, y+20*s, 7*s, 5*s))
        pygame.draw.rect(surface, BOOTS, (x+10*s, y+20*s, 7*s, 5*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+5*s, y+7*s, 15*s, 15*s), border_radius=int(2*s))
        pygame.draw.rect(surface, STRIPE, (x+5*s, y+14*s, 15*s, 3*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+8*s, y+2*s, 10*s, 10*s), border_radius=int(3*s))
        pygame.draw.rect(surface, SKIN_COLOR, (x+9*s, y+5*s, 5*s, 5*s))
        pygame.draw.rect(surface, NOZZLE, (x, y+12*s, 5*s, 7*s))
    elif direction == 'right':
        pygame.draw.rect(surface, AIR_TANK, (x+2*s, y+5*s, 8*s, 14*s), border_radius=int(3*s))
        pygame.draw.rect(surface, BOOTS, (x+8*s, y+20*s, 7*s, 5*s))
        pygame.draw.rect(surface, BOOTS, (x+14*s, y+20*s, 7*s, 5*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+5*s, y+7*s, 15*s, 15*s), border_radius=int(2*s))
        pygame.draw.rect(surface, STRIPE, (x+5*s, y+14*s, 15*s, 3*s))
        pygame.draw.rect(surface, UNIFORM_COLOR, (x+7*s, y+2*s, 10*s, 10*s), border_radius=int(3*s))
        pygame.draw.rect(surface, SKIN_COLOR, (x+11*s, y+5*s, 5*s, 5*s))
        pygame.draw.rect(surface, NOZZLE, (x+20*s, y+12*s, 5*s, 7*s))

def draw_player_preview(x, y, skin, helmet):
    draw_player_model(screen, x, y, 100, skin, helmet, 'down')

def draw_player():
    if pygame.time.get_ticks() - last_damage_time < 2000:
        if (pygame.time.get_ticks() // 100) % 2 == 0:
            return 
    draw_player_model(screen, player_rect.x, player_rect.y, PLAYER_SIZE, player_skin_color, player_helmet_color, player_direction)

# --- UPDATED WATER SPRAY LOGIC (Proper Stream) ---
def create_water_spray():
    global water_particles
    # Base Position
    if player_direction == 'up': px, py = player_rect.centerx, player_rect.top
    elif player_direction == 'down': px, py = player_rect.centerx, player_rect.bottom
    elif player_direction == 'left': px, py = player_rect.left, player_rect.centery
    else: px, py = player_rect.right, player_rect.centery
    
    # Increase density of particles (SUPER SOAKER EFFECT)
    particles_per_frame = 5 if has_water_powerup else 3 
    
    speed_base = 7 
    spread = 1.5   # Cone spread

    for _ in range(particles_per_frame):
        # Calculate velocity based on direction + random spread
        if player_direction == 'up':
            dx = random.uniform(-spread, spread)
            dy = -speed_base - random.uniform(0, 2)
        elif player_direction == 'down':
            dx = random.uniform(-spread, spread)
            dy = speed_base + random.uniform(0, 2)
        elif player_direction == 'left':
            dx = -speed_base - random.uniform(0, 2)
            dy = random.uniform(-spread, spread)
        else: # Right
            dx = speed_base + random.uniform(0, 2)
            dy = random.uniform(-spread, spread)
            
        # Lifetime: Enough to reach across screen partway
        lifetime = random.randint(30, 45) 
        water_particles.append([px, py, dx, dy, lifetime])

def update_and_draw_water():
    global water_particles
    for i in range(len(water_particles) - 1, -1, -1):
        particle = water_particles[i]
        
        # Move
        particle[0] += particle[2]
        particle[1] += particle[3]
        particle[4] -= 1
        
        # Hit Detection
        grid_x = int(particle[0] // TILE_SIZE)
        grid_y = int((particle[1] - UI_HEIGHT) // TILE_SIZE)
        
        if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
            if (grid_x, grid_y) in fire_tiles:
                extinguish_fire(grid_x, grid_y)
                
        if particle[4] <= 0:
            water_particles.pop(i)
        else:
            # Draw larger, more visible water
            radius = 4 if has_water_powerup else 3
            pygame.draw.circle(screen, WATER_BLUE, (int(particle[0]), int(particle[1])), radius)

def extinguish_fire(grid_x, grid_y):
    global score, game_state, pause_start_time
    if (grid_x, grid_y) in fire_tiles:
        game_grid[grid_y][grid_x] = BURNT_GROUND
        fire_tiles.remove((grid_x, grid_y))
        score += 1
        
        if current_level_id == 6: return # Normal Survival
        if current_level_id == 9: return # Parkinson Survival
        if current_level_id == 7: return 

        if current_level_id == 1: pass 
        elif current_level_id == 2: spawn_new_fire_cluster(1)
        elif current_level_id == 8: spawn_new_fire_cluster(1)
        elif current_level_id == 3: pass
        elif current_level_id >= 4: 
            if score == 1:
                spawn_new_fire_cluster(1)
                if current_level_id == 5:
                    game_state = STATE_GAME_PAUSED
                    pause_start_time = pygame.time.get_ticks()
            elif score == 3: spawn_new_fire_cluster(2)
            elif score == 8: spawn_new_fire_cluster(3)

def draw_game_ui():
    pygame.draw.rect(screen, UI_BG_COLOR, (0, 0, SCREEN_WIDTH, UI_HEIGHT))
    draw_text(f"Score: {score}", font_menu_item, WHITE, screen, 20, 10)
    
    display_level = 1
    if current_level_id == 1 or current_level_id == 3: display_level = 1
    elif current_level_id == 2 or current_level_id == 4: display_level = 2
    elif current_level_id == 5 or current_level_id == 8: display_level = 3
    elif current_level_id == 6 or current_level_id == 9: display_level = 4
    elif current_level_id == 7: display_level = 5
        
    draw_text(f"Level: {display_level}", font_menu_item, WHITE, screen, 200, 10)
    
    # Draw Hearts for survival modes or if user has heart powerup
    if current_level_id in [6, 7, 9] or player_lives > 3: draw_hearts()
    
    # Powerup Status
    status_x = 280
    if has_water_powerup:
        draw_text("2x WATER!", font_menu_tiny, CYAN, screen, status_x, 5)
        status_x += 100
    if has_speed_powerup:
        draw_text("SPEED!", font_menu_tiny, GOLD_SPEED, screen, status_x, 5)

    if current_level_id == 1 or current_level_id == 3: 
        fire_text = f"Fires Left: {len(fire_tiles)}"
    else: 
        fire_text = f"Total: {len(fire_tiles)}"
    draw_text(fire_text, font_menu_item, WHITE, screen, SCREEN_WIDTH - 250, 10)
    draw_text(f"Time: {time_remaining}", font_menu_item, WHITE, screen, SCREEN_WIDTH - 130, 10)

def draw_countdown(start_time_ref):
    elapsed = pygame.time.get_ticks() - start_time_ref
    if elapsed < 1000: text = "3"
    elif elapsed < 2000: text = "2"
    elif elapsed < 3000: text = "1"
    else: text = "GO!"
    draw_text(text, font_huge, BLACK, screen, SCREEN_WIDTH // 2 + 5, SCREEN_HEIGHT // 2 + 5, center=True)
    draw_text(text, font_huge, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)

def draw_penalty_countdown():
    elapsed = pygame.time.get_ticks() - penalty_start_time
    remaining = 3 - (elapsed // 1000)
    if remaining < 0: remaining = 0
    draw_text("STUCK!", font_large, RED, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, center=True)
    draw_text(str(remaining), font_huge, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, center=True)

def init_game():
    global game_state, score, game_start_time, time_remaining, player_rect, water_particles, player_direction, player_speed
    global pause_start_time, total_paused_time, fire_particles, obstacle_tiles, penalty_start_time, current_level_id
    global zombies, player_lives, last_damage_time, flame_zombies, water_powerup_rect, speed_powerup_rect, heart_powerup_rect
    global has_water_powerup, has_speed_powerup
    
    score = 0
    game_start_time = pygame.time.get_ticks()
    total_paused_time = 0
    time_remaining = GAME_DURATION_SEC
    player_rect.center = (SCREEN_WIDTH // 2, (SCREEN_HEIGHT - UI_HEIGHT) // 2 + UI_HEIGHT)
    water_particles = []
    fire_particles = []
    zombies = [] 
    flame_zombies = []
    
    water_powerup_rect = None
    speed_powerup_rect = None
    heart_powerup_rect = None
    
    has_water_powerup = False
    has_speed_powerup = False
    player_speed = player_base_speed
    
    player_lives = 3 
    last_damage_time = 0
    player_direction = 'down'
    
    if selected_player_index == 0:
        player_skin_color = PLAYER_SKIN_WHITE
        player_helmet_color = PLAYER_HELMET_BLUE
    elif selected_player_index == 1:
        player_skin_color = PLAYER_SKIN_BLACK
        player_helmet_color = PLAYER_HELMET_RED
    elif selected_player_index == 2:
        player_skin_color = PLAYER_SKIN_BROWN
        player_helmet_color = PLAYER_HELMET_GREEN
    
    create_grid()
    
    # --- PARKINSONS MODE ---
    if selected_mode_index == 0: 
        if selected_level_index == 0:
            current_level_id = 1
            spawn_initial_fire(LEVEL_1_FIRE_COUNT)
            game_state = STATE_GAME_RUNNING
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
        elif selected_level_index == 1:
            current_level_id = 2
            spawn_initial_fire(1)
            game_state = STATE_GAME_RUNNING
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
        elif selected_level_index == 2: 
            current_level_id = 8
            spawn_initial_fire(3)
            game_state = STATE_GAME_RUNNING
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 3000)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
        elif selected_level_index == 3: # NEW: Parkinson's Level 4
            current_level_id = 9 # Unique ID for Parkinson Survival
            spawn_initial_fire(3) 
            game_state = STATE_GAME_STARTING
            pause_start_time = pygame.time.get_ticks()
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 2000) 
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
            for _ in range(ZOMBIE_COUNT_PARKINSONS): spawn_zombie()
            
    # --- NORMAL MODE ---
    elif selected_mode_index == 1: 
        if selected_level_index == 0: 
            current_level_id = 3
            spawn_initial_fire(LEVEL_1_FIRE_COUNT)
            game_state = STATE_GAME_RUNNING
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
            spawn_water_powerup() # Add water powerup
            
        elif selected_level_index == 1: 
            current_level_id = 4
            spawn_initial_fire(1)
            game_state = STATE_GAME_STARTING
            pause_start_time = pygame.time.get_ticks()
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 2000)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
            spawn_water_powerup() # Add water powerup
            
        elif selected_level_index == 2: 
            current_level_id = 5
            spawn_initial_fire(1)
            game_state = STATE_GAME_STARTING
            pause_start_time = pygame.time.get_ticks()
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 2000)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, OBSTACLE_SPAWN_RATE_MS)
            
        elif selected_level_index == 3: # Normal Level 4: Survival
            current_level_id = 6
            spawn_initial_fire(3) 
            game_state = STATE_GAME_STARTING
            pause_start_time = pygame.time.get_ticks()
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 2000) 
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
            for _ in range(ZOMBIE_COUNT_NORMAL): spawn_zombie() # 3 Zombies
            spawn_water_powerup()
            spawn_speed_powerup()

        elif selected_level_index == 4: # Normal Level 5: Flame Zombie
            current_level_id = 7
            spawn_initial_fire(1)
            game_state = STATE_GAME_STARTING
            pause_start_time = pygame.time.get_ticks()
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 1500)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
            spawn_flame_zombie() 
            spawn_flame_zombie() # 2 Flame Zombies
            spawn_water_powerup()
            spawn_speed_powerup()
            spawn_heart_powerup()

def draw_menu_background():
    if jungle_background_image: 
        screen.blit(jungle_background_image, (0, UI_HEIGHT))
    else: 
        pygame.draw.rect(screen, BLACK, (0, UI_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - UI_HEIGHT))
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))

# --- INIT JOYSTICKS ---
print("Initializing Joysticks...")
joy1 = JoystickHandler(0, 1, 17) # Move
joy2 = JoystickHandler(2, 3, 27) # Action/Menu

# --- Main Game Loop ---
running = True
while running:
    # Always update joysticks first
    joy1.update()
    joy2.update()
    current_time = pygame.time.get_ticks()

    # --- INPUT HELPER: Check Joystick 2 for Menu Nav ---
    # Directions for Menu (Debounced)
    menu_up = False
    menu_down = False
    menu_left = False
    menu_right = False
    menu_enter = False

    if abs(joy2.norm_x) > 0.5 or abs(joy2.norm_y) > 0.5:
        if current_time - last_menu_move_time > MENU_MOVE_DELAY:
            if joy2.norm_x < -0.5: menu_left = True
            elif joy2.norm_x > 0.5: menu_right = True
            
            if joy2.norm_y < -0.5: menu_up = True
            elif joy2.norm_y > 0.5: menu_down = True
            
            last_menu_move_time = current_time

    # Button for Menu (Just Pressed)
    if joy2.just_pressed:
        menu_enter = True

    # --- EVENTS ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_x:
                if game_state in [STATE_GAME_RUNNING, STATE_GAME_STARTING, STATE_GAME_PAUSED, STATE_GAME_PENALTY]:
                    game_state = STATE_PAUSED_MENU
                    if score > high_score: high_score = score
                    pygame.time.set_timer(FIRE_SPREAD_EVENT, 0) 
                    pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)
                else:
                    running = False 

        # KEYBOARD MAPPING (Merged with Joystick Flags)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: menu_up = True
            if event.key == pygame.K_DOWN: menu_down = True
            if event.key == pygame.K_LEFT: menu_left = True
            if event.key == pygame.K_RIGHT: menu_right = True
            if event.key == pygame.K_RETURN: menu_enter = True

    # --- STATE LOGIC ---
    if game_state == STATE_START_MENU:
        if menu_enter:
            game_state = STATE_PLAYER_SELECT
    
    elif game_state == STATE_PLAYER_SELECT:
        if menu_left:
            selected_player_index = (selected_player_index - 1) % 3
        elif menu_right:
            selected_player_index = (selected_player_index + 1) % 3
        elif menu_enter:
            game_state = STATE_MODE_SELECT
    
    elif game_state == STATE_MODE_SELECT:
        if menu_left: selected_mode_index = 0
        elif menu_right: selected_mode_index = 1
        elif menu_enter: game_state = STATE_LEVEL_SELECT
    
    elif game_state == STATE_LEVEL_SELECT:
        # PARKINSON'S MODE SELECTION
        if selected_mode_index == 0: 
            if menu_left: selected_level_index = max(0, selected_level_index - 1)
            elif menu_right: selected_level_index = min(3, selected_level_index + 1) # Now 4 levels (0-3)
            elif menu_enter: init_game()
        
        # NORMAL MODE SELECTION (Updated grid logic)
        elif selected_mode_index == 1:
            # 5 Levels: 0,1,2 on top row. 3,4 on bottom row.
            if menu_left: 
                selected_level_index = max(0, selected_level_index - 1)
            elif menu_right: 
                selected_level_index = min(4, selected_level_index + 1)
            elif menu_down: 
                if selected_level_index < 3: selected_level_index = min(4, selected_level_index + 3)
            elif menu_up:
                if selected_level_index >= 3: selected_level_index = selected_level_index - 3
            elif menu_enter: init_game()
                    
    elif game_state in [STATE_GAME_RUNNING, STATE_GAME_STARTING, STATE_GAME_PAUSED, STATE_GAME_PENALTY]:
        # GAME LOOP EVENTS
        for event in pygame.event.get(): 
             if event.type == FIRE_SPREAD_EVENT: spread_fire()
             if event.type == OBSTACLE_SPAWN_EVENT and current_level_id == 5: spawn_obstacle()
                    
    elif game_state == STATE_GAME_OVER or game_state == STATE_GAME_WON:
        if menu_enter:
            game_state = STATE_START_MENU
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)

    elif game_state == STATE_PAUSED_MENU:
        if menu_enter:
            init_game()

    # --- GAMEPLAY UPDATE ---
    if game_state == STATE_GAME_STARTING:
        if pygame.time.get_ticks() - pause_start_time > 3000:
            total_paused_time += (pygame.time.get_ticks() - pause_start_time)
            game_state = STATE_GAME_RUNNING
    
    elif game_state == STATE_GAME_PAUSED:
        if pygame.time.get_ticks() - pause_start_time > 3000:
            total_paused_time += (pygame.time.get_ticks() - pause_start_time)
            game_state = STATE_GAME_RUNNING

    elif game_state == STATE_GAME_PENALTY:
        if pygame.time.get_ticks() - penalty_start_time > 3000:
            total_paused_time += (pygame.time.get_ticks() - penalty_start_time)
            game_state = STATE_GAME_RUNNING

    elif game_state == STATE_GAME_RUNNING:
        
        keys = pygame.key.get_pressed()
        new_x = player_rect.x
        new_y = player_rect.y
        
        # KEYBOARD INPUT
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            new_x -= player_speed
            player_direction = 'left'
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            new_x += player_speed
            player_direction = 'right'
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_y -= player_speed
            player_direction = 'up'
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_y += player_speed
            player_direction = 'down'

        # JOYSTICK INPUT
        if abs(joy1.norm_x) > 0 or abs(joy1.norm_y) > 0:
            new_x = player_rect.x + (joy1.norm_x * player_speed)
            new_y = player_rect.y + (joy1.norm_y * player_speed)
            
            if abs(joy1.norm_x) > abs(joy1.norm_y):
                if joy1.norm_x < 0: player_direction = 'left'
                elif joy1.norm_x > 0: player_direction = 'right'
            else:
                if joy1.norm_y < 0: player_direction = 'up'
                elif joy1.norm_y > 0: player_direction = 'down'

        # OBSTACLE COLLISION
        test_rect = pygame.Rect(new_x, new_y, PLAYER_SIZE, PLAYER_SIZE)
        collision = False
        for (ox, oy) in obstacle_tiles:
            obs_rect = pygame.Rect(ox * TILE_SIZE, oy * TILE_SIZE + UI_HEIGHT, TILE_SIZE, TILE_SIZE)
            if test_rect.colliderect(obs_rect):
                collision = True
                if current_level_id == 5: 
                    game_state = STATE_GAME_PENALTY
                    penalty_start_time = pygame.time.get_ticks()
                    obstacle_tiles.remove((ox, oy)) 
                break
        
        if not collision:
            player_rect.x = new_x
            player_rect.y = new_y

        # Spray Trigger
        if keys[pygame.K_SPACE] or joy2.is_pressed:
            create_water_spray()

        playable_rect = pygame.Rect(0, UI_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - UI_HEIGHT)
        player_rect.clamp_ip(playable_rect)

        # ZOMBIE LOGIC (For Normal Level 4 OR Parkinson's Level 4)
        if current_level_id == 6 or current_level_id == 9:
            # Determine speed based on level
            current_z_speed = ZOMBIE_SPEED if current_level_id == 6 else PARKINSON_ZOMBIE_SPEED

            for z_data in zombies:
                z_rect = z_data[2]
                dx = player_rect.x - z_data[0]
                dy = player_rect.y - z_data[1]
                dist = math.hypot(dx, dy)
                if dist != 0:
                    z_data[0] += (dx / dist) * current_z_speed
                    z_data[1] += (dy / dist) * current_z_speed
                    z_rect.x = int(z_data[0])
                    z_rect.y = int(z_data[1])
                
                if z_rect.colliderect(player_rect):
                    current_time = pygame.time.get_ticks()
                    if current_time - last_damage_time > 2000:
                        player_lives -= 1
                        last_damage_time = current_time
                        if player_lives <= 0:
                            game_state = STATE_GAME_OVER
                            if score > high_score: high_score = score
        
        # FLAME ZOMBIE LOGIC (Handle list of zombies)
        if current_level_id == 7 and flame_zombies:
            for fz in flame_zombies:
                z_rect = fz[2]
                dx = player_rect.x - fz[0]
                dy = player_rect.y - fz[1]
                dist = math.hypot(dx, dy)
                if dist != 0:
                    fz[0] += (dx / dist) * FLAME_ZOMBIE_SPEED
                    fz[1] += (dy / dist) * FLAME_ZOMBIE_SPEED
                    z_rect.x = int(fz[0])
                    z_rect.y = int(fz[1])
                
                grid_x = int(z_rect.centerx // TILE_SIZE)
                grid_y = int((z_rect.centery - UI_HEIGHT) // TILE_SIZE)
                if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                     if (grid_x, grid_y) not in fire_tiles:
                         fire_tiles.add((grid_x, grid_y))

                if z_rect.colliderect(player_rect):
                     game_state = STATE_GAME_OVER
                     if score > high_score: high_score = score
            
        # POWERUP COLLISIONS
        # 1. Water Powerup
        if water_powerup_rect and not has_water_powerup:
            if player_rect.colliderect(water_powerup_rect):
                has_water_powerup = True
                water_powerup_rect = None
        
        # 2. Speed Powerup (Boosts speed)
        if speed_powerup_rect and not has_speed_powerup:
            if player_rect.colliderect(speed_powerup_rect):
                has_speed_powerup = True
                player_speed = player_base_speed * 1.75
                speed_powerup_rect = None

        # 3. Heart Powerup (Extra Life)
        if heart_powerup_rect:
            if player_rect.colliderect(heart_powerup_rect):
                player_lives += 1
                heart_powerup_rect = None

        # WIN/LOSS LOGIC
        if len(fire_tiles) == 0:
            if current_level_id == 7:
                 spawn_new_fire_cluster(3) 
            elif current_level_id == 8:
                 spawn_new_fire_cluster(3)
            elif current_level_id != 6 and current_level_id != 9:
                game_state = STATE_GAME_WON
                if score > high_score: high_score = score
                pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
                pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0) 
            else:
                spawn_new_fire_cluster(3)
            
        elapsed_ticks = pygame.time.get_ticks() - game_start_time
        running_ticks = elapsed_ticks - total_paused_time
        time_remaining = GAME_DURATION_SEC - (running_ticks // 1000)

        if time_remaining <= 0:
            time_remaining = 0
            if current_level_id in [6, 7, 8, 9]:
                game_state = STATE_GAME_WON
            else:
                game_state = STATE_GAME_OVER
            
            if score > high_score: high_score = score
            pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
            pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)

        if current_level_id >= 4:
            fire_percentage = len(fire_tiles) / total_tiles
            if fire_percentage >= MAX_FIRE_PERCENTAGE:
                game_state = STATE_GAME_OVER
                if score > high_score: high_score = score
                pygame.time.set_timer(FIRE_SPREAD_EVENT, 0)
                pygame.time.set_timer(OBSTACLE_SPAWN_EVENT, 0)

    # --- Drawing ---
    screen.fill(DARK_GREEN)
    
    if game_state == STATE_START_MENU:
        draw_menu_background()
        draw_text("FOREST FIRE", font_large, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, center=True)
        draw_text("Press JOYSTICK or ENTER to Start", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30, center=True)
        draw_text("Use Arrow Keys to Move", font_small, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100, center=True)
        draw_text("Press SPACE to Spray Water", font_small, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60, center=True)
    
    elif game_state == STATE_PLAYER_SELECT:
        draw_menu_background()
        draw_text("Choose Your Firefighter", font_menu_title, WHITE, screen, SCREEN_WIDTH // 2, 80, center=True)

        p_y = SCREEN_HEIGHT // 2 
        p1_x = 125
        draw_player_preview(p1_x, p_y - 50, PLAYER_SKIN_WHITE, PLAYER_HELMET_BLUE)
        draw_text("Alpha", font_menu_item, WHITE, screen, p1_x + 50, p_y + 70, center=True)

        p2_x = 350
        draw_player_preview(p2_x, p_y - 50, PLAYER_SKIN_BLACK, PLAYER_HELMET_RED)
        draw_text("Bravo", font_menu_item, WHITE, screen, p2_x + 50, p_y + 70, center=True)
        
        p3_x = 575
        draw_player_preview(p3_x, p_y - 50, PLAYER_SKIN_BROWN, PLAYER_HELMET_GREEN)
        draw_text("Charlie", font_menu_item, WHITE, screen, p3_x + 50, p_y + 70, center=True)

        if selected_player_index == 0: selector_rect = pygame.Rect(p1_x - 10, p_y - 60, 120, 180)
        elif selected_player_index == 1: selector_rect = pygame.Rect(p2_x - 10, p_y - 60, 120, 180)
        else: selector_rect = pygame.Rect(p3_x - 10, p_y - 60, 120, 180)
        
        pygame.draw.rect(screen, YELLOW, selector_rect, 5)
        draw_text("JOYSTICK to select & confirm", font_menu_tiny, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40, center=True)

    elif game_state == STATE_MODE_SELECT:
        draw_menu_background()
        draw_text("Select Mode", font_menu_title, WHITE, screen, SCREEN_WIDTH // 2, 80, center=True)
        
        mode1_x = SCREEN_WIDTH // 2 - 225
        mode_y = SCREEN_HEIGHT // 2 - 50
        mode1_rect = pygame.Rect(mode1_x, mode_y, 200, 150)
        pygame.draw.rect(screen, DARK_GREEN, mode1_rect)
        draw_text("Parkinson's", font_menu_item, WHITE, screen, mode1_rect.centerx, mode1_rect.centery, center=True)

        mode2_x = SCREEN_WIDTH // 2 + 25
        mode2_rect = pygame.Rect(mode2_x, mode_y, 200, 150)
        pygame.draw.rect(screen, RED, mode2_rect)
        draw_text("Normal", font_menu_item, WHITE, screen, mode2_rect.centerx, mode2_rect.centery, center=True)

        if selected_mode_index == 0: selector_rect = pygame.Rect(mode1_x - 10, mode_y - 10, 220, 170)
        else: selector_rect = pygame.Rect(mode2_x - 10, mode_y - 10, 220, 170)
        
        pygame.draw.rect(screen, YELLOW, selector_rect, 5)
        draw_text("JOYSTICK to select & confirm", font_menu_tiny, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60, center=True)

    elif game_state == STATE_LEVEL_SELECT:
        draw_menu_background()
        
        if selected_mode_index == 0: 
            draw_text("Select Level (Parkinson's Mode)", font_menu_title, WHITE, screen, SCREEN_WIDTH // 2, 50, center=True)
            
            # Layout: 4 columns
            col_width = 160
            spacing = 20
            start_x = (SCREEN_WIDTH - (4 * col_width + 3 * spacing)) // 2
            y_pos = SCREEN_HEIGHT // 2 - 75
            
            # Helper to draw box
            def draw_lvl_box(idx, color, title, sub):
                r = pygame.Rect(start_x + idx * (col_width + spacing), y_pos, col_width, 150)
                pygame.draw.rect(screen, color, r)
                draw_text(title, font_menu_item, WHITE, screen, r.centerx, r.centery - 20, center=True)
                draw_text(sub, font_menu_tiny, WHITE, screen, r.centerx, r.centery + 20, center=True)
                return r

            r0 = draw_lvl_box(0, BLUE, "LEVEL 1", "Basic")
            r1 = draw_lvl_box(1, DARK_GREEN, "LEVEL 2", "Endless")
            r2 = draw_lvl_box(2, PURPLE, "LEVEL 3", "Med. Spread")
            r3 = draw_lvl_box(3, (80, 80, 80), "LEVEL 4", "Slow Zombie")

            rects = [r0, r1, r2, r3]
            sel_rect = rects[selected_level_index]
            pygame.draw.rect(screen, YELLOW, sel_rect.inflate(10,10), 5)
            draw_text("JOYSTICK to select & confirm", font_menu_tiny, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60, center=True)

        elif selected_mode_index == 1:
            draw_text("Select Level (Normal Mode)", font_menu_title, WHITE, screen, SCREEN_WIDTH // 2, 40, center=True)
            
            # NEW LAYOUT FOR 800x480: 3 on Top, 2 on Bottom
            box_w = 180
            box_h = 130
            gap_x = 20
            gap_y = 20
            
            # Top Row (3 items) centered
            top_total_w = 3 * box_w + 2 * gap_x
            start_x_top = (SCREEN_WIDTH - top_total_w) // 2
            start_y_top = 80
            
            # Bottom Row (2 items) centered
            bot_total_w = 2 * box_w + 1 * gap_x
            start_x_bot = (SCREEN_WIDTH - bot_total_w) // 2
            start_y_bot = start_y_top + box_h + gap_y

            rects = []

            # Level 1
            r1 = pygame.Rect(start_x_top, start_y_top, box_w, box_h)
            pygame.draw.rect(screen, DARK_GREEN, r1)
            draw_text("LEVEL 1", font_menu_item, WHITE, screen, r1.centerx, r1.centery - 15, center=True)
            draw_text("Endless", font_menu_tiny, WHITE, screen, r1.centerx, r1.centery + 15, center=True)
            rects.append(r1)

            # Level 2
            r2 = pygame.Rect(start_x_top + box_w + gap_x, start_y_top, box_w, box_h)
            pygame.draw.rect(screen, ORANGE, r2)
            draw_text("LEVEL 2", font_menu_item, WHITE, screen, r2.centerx, r2.centery - 15, center=True)
            draw_text("Spread", font_menu_tiny, WHITE, screen, r2.centerx, r2.centery + 15, center=True)
            rects.append(r2)

            # Level 3
            r3 = pygame.Rect(start_x_top + 2 * (box_w + gap_x), start_y_top, box_w, box_h)
            pygame.draw.rect(screen, RED, r3)
            draw_text("LEVEL 3", font_menu_item, WHITE, screen, r3.centerx, r3.centery - 15, center=True)
            draw_text("Obstacles", font_menu_tiny, WHITE, screen, r3.centerx, r3.centery + 15, center=True)
            rects.append(r3)

            # Level 4
            r4 = pygame.Rect(start_x_bot, start_y_bot, box_w, box_h)
            pygame.draw.rect(screen, (50, 50, 50), r4) 
            draw_text("LEVEL 4", font_menu_item, WHITE, screen, r4.centerx, r4.centery - 15, center=True)
            draw_text("3 Zombies", font_menu_tiny, YELLOW, screen, r4.centerx, r4.centery + 15, center=True)
            rects.append(r4)

            # Level 5
            r5 = pygame.Rect(start_x_bot + box_w + gap_x, start_y_bot, box_w, box_h)
            pygame.draw.rect(screen, FLAME_ZOMBIE_COLOR, r5) 
            draw_text("LEVEL 5", font_menu_item, WHITE, screen, r5.centerx, r5.centery - 15, center=True)
            draw_text("2 Flame Z.", font_menu_tiny, BLACK, screen, r5.centerx, r5.centery + 15, center=True)
            rects.append(r5)

            sel_rect = rects[selected_level_index]
            pygame.draw.rect(screen, YELLOW, sel_rect.inflate(10, 10), 5)
            draw_text("JOYSTICK to select & confirm", font_menu_tiny, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40, center=True)

    elif game_state in [STATE_GAME_RUNNING, STATE_GAME_STARTING, STATE_GAME_PAUSED, STATE_GAME_PENALTY]:
        draw_jungle_and_fire()
        update_and_draw_fire_particles()
        draw_player()
        
        if game_state == STATE_GAME_RUNNING:
            update_and_draw_water()
            if current_level_id == 6 or current_level_id == 9:
                draw_zombies()
            if current_level_id == 7:
                draw_flame_zombies()
            draw_powerups() # Draw all powerups
        
        draw_game_ui()
        
        if current_level_id >= 4: 
            if game_state == STATE_GAME_STARTING:
                draw_text("GET READY!", font_large, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, center=True)
                draw_countdown(pause_start_time)
            elif game_state == STATE_GAME_PAUSED:
                 pass
            elif game_state == STATE_GAME_PENALTY:
                draw_penalty_countdown()

    elif game_state == STATE_PAUSED_MENU:
        screen.fill(BLACK)
        draw_text("GAME PAUSED", font_large, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4, center=True)
        draw_text(f"Current Score: {score}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
        draw_text(f"High Score: {high_score}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, center=True)
        draw_text("Press JOYSTICK or ENTER to Play Again", font_small, YELLOW, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100, center=True)

    elif game_state == STATE_GAME_OVER:
        screen.fill(RED)
        draw_text("GAME OVER", font_large, BLACK, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, center=True)
        draw_text(f"Final Score: {score}", font_medium, BLACK, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, center=True)
        draw_text(f"High Score: {high_score}", font_medium, BLACK, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, center=True)
        draw_text("Press JOYSTICK or ENTER to Restart", font_small, BLACK, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100, center=True)

    elif game_state == STATE_GAME_WON:
        screen.fill(BLUE)
        draw_text("YOU WON!", font_large, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, center=True)
        draw_text(f"Final Score: {score}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, center=True)
        draw_text(f"High Score: {high_score}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, center=True)
        draw_text(f"Time Remaining: {time_remaining}", font_medium, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120, center=True)
        draw_text("Press JOYSTICK or ENTER to Restart", font_small, WHITE, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100, center=True)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()