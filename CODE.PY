
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
import math
import time
import random


WINDOW = {"w": 1000, "h": 800}
ASPECT_RATIO = WINDOW["w"] / WINDOW["h"]

FOV_Y = 68.0
NEAR_CLIP = 1.0
FAR_CLIP = 3000.0

GRID_TILES = 13
TILE_SIZE = 100.0
GRID_WORLD_SIZE = GRID_TILES * TILE_SIZE
GRID_HALF_SIZE = GRID_WORLD_SIZE / 2.0

PLAYER_ACCEL = 900.0
PLAYER_MAX_SPEED = 520.0
FRICTION_PER_FRAME = 0.88
TURN_SPEED_DEG = 220.0

PLAYER_HIT_PAD = 26.0
PLAYER_HIT_RADIUS = 62.0

MAX_LIVES = 20

INVINCIBLE_SEC = 0.75

SPRINT_MULT = 1.35

DASH_SPEED = 1700.0
DASH_DURATION = 0.12
DASH_COOLDOWN = 1.10

BULLET_SPEED = 900.0
BULLET_CUBE_SIZE = 9.0
BULLET_MUZZLE_OFFSET = 120.0
BULLET_Z = 95.0

NORMAL_BULLET_DAMAGE = 3
SHOTGUN_PELLET_DAMAGE = 2

COOLDOWN_SEC = 0.18
RELOAD_SEC = 0.95

MAX_AMMO = 18

SHOTGUN_PELLETS = 5
SHOTGUN_SPREAD_DEG = 12.0

ENEMY_BULLET_SPEED = 520.0
ENEMY_BULLET_SIZE = 10.0
ENEMY_BULLET_Z = 75.0
ENEMY_BULLET_DAMAGE = 2

ENEMY_MIN_SEP = 160.0
ENEMY_Z = 40.0

ENEMY_SCALE_MIN = 0.90
ENEMY_SCALE_MAX = 1.35
ENEMY_SCALE_STEP = 0.012

ENEMY_TYPES = {
    "chaser":  {"speed": 10.0, "radius": 50.0, "hp_base": 2, "color": (1.0, 1.0, 1.0)},
    "fast":    {"speed": 35.0, "radius": 38.0, "hp_base": 1, "color": (1.0, 0.6, 0.0)},
    "tank":    {"speed": 5.0,  "radius": 64.0, "hp_base": 3, "color": (0.6, 0.1, 1.0)},
    "shooter": {"speed": 8.0,  "radius": 46.0, "hp_base": 2, "color": (0.2, 0.85, 1.0)},
}

SHOOTER_DESIRED_RANGE = 520.0
SHOOTER_FIRE_INTERVAL = 1.05
SHOOTER_SPREAD_DEG = 7.0
SHOOTER_ORBIT_MULT = 1.0

LAVA_COUNT = 8
MUD_COUNT = 8

MUD_SLOW_MULT = 0.55
LAVA_TICK_SEC = 0.55

PICKUP_RADIUS = 65.0
PICKUP_TTL = 12.0
DROP_CHANCE = 0.35
DROP_AMMO_PROB = 0.65
AMMO_GAIN = 8
HEALTH_GAIN = 3

MAX_LEVEL = 5

LEVEL_CONFIG = {
    1: {"kills": 5,  "clouds": False, "lava": False, "boss": False},
    2: {"kills": 8,  "clouds": True,  "lava": False, "boss": False},
    3: {"kills": 10, "clouds": True,  "lava": True,  "boss": False},
    4: {"kills": 1,  "clouds": False, "lava": False, "boss": True},
    5: {"kills": 2,  "clouds": True,  "lava": True,  "boss": True},
}

LEVEL_MESSAGE_DURATION = 2.0

KEY_HOLD_TIMEOUT =0.1
ACTION_DEBOUNCE_SEC = 0.35


player_state = {
    "x": 0.0, "y": 0.0,
    "vx": 0.0, "vy": 0.0,
    "heading_deg": 0.0,

    "hit_pad": PLAYER_HIT_PAD,
    "hit_radius": PLAYER_HIT_RADIUS,

    "lives": MAX_LIVES,
    "score": 0,

    "invincible_timer": 0.0,

    "sprint_on": False,

    "is_dashing": False,
    "dash_timer": 0.0,
    "dash_cd": 0.0,
    "dash_dir_x": 0.0,
    "dash_dir_y": 1.0,
}

weapon_state = {
    "mode": 1,

    "ammo": MAX_AMMO,
    "max_ammo": MAX_AMMO,

    "cooldown": 0.0,

    "is_reloading": False,
    "reload_timer": 0.0,
}

camera_state = {
    "orbit_deg": 270.0,
    "height": 900.0,
    "radius": 900.0,

    "orbit_step": 3.5,
    "height_step": 18.0,
    "height_min": 160.0,
    "height_max": 980.0,
}

game_state = {
    "is_over": False,
    "over_cause": "",

    "level": 1,
    "max_level": MAX_LEVEL,

    "kills_this_level": 0,
    "kills_required": 5,

    "enemy_total": 0,
    "is_boss_level": False,

    "show_level_message": False,
    "level_message_text": "",
    "level_message_timer": 0.0,

    "lava_timer": 0.0,
    "sun_shoot_timer": 0.0,
    "sun_shoot_interval": 3.0,  # Shoot every 3 seconds
}

input_tracker = {
    "keys_last_time": {},
    "special_last_time": {},
    "action_last_time": {},
}

tile_hazard_map = {}
lava_tile_cells = []
pickup_items = []
rain_clouds = []
boss_units = []
enemy_units = []
player_projectiles = []
enemy_projectiles = []
sun_projectiles = []
enemy_pulse_anim = {"scale": ENEMY_SCALE_MIN, "growing": True}

static_env = {"tree_positions": [], "house_positions": []}

render_quadric = None
last_tick_time = time.time()


def grid_world_min():
    return -GRID_HALF_SIZE

def grid_world_max():
    return GRID_HALF_SIZE

def clamp_float(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

def is_inside_world_bounds(x, y, pad=0.0):
    mn = grid_world_min() + pad
    mx = grid_world_max() - pad
    return (mn <= x <= mx) and (mn <= y <= mx)

def world_pos_to_cell(x, y):
    mn = grid_world_min()
    j = int((x - mn) / TILE_SIZE) # col index 
    i = int((y - mn) / TILE_SIZE) # row index
    i = int(clamp_float(i, 0, GRID_TILES - 1)) # clamps i
    j = int(clamp_float(j, 0, GRID_TILES - 1)) # clamps j 
    return i, j

def get_time_now():
    return time.time()

def normalize_key(k): # Converts bytearray → bytes , A becomes a, movements
    if isinstance(k, (bytes, bytearray)):
        return bytes(k).lower()
    return k

def is_key_held(k): 
    k = normalize_key(k)
    t = input_tracker["keys_last_time"].get(k, -9999.0)
    return (get_time_now() - t) <= KEY_HOLD_TIMEOUT

def is_special_held(k): # camera controls 
    t = input_tracker["special_last_time"].get(k, -9999.0)
    return (get_time_now() - t) <= KEY_HOLD_TIMEOUT

def _debounced_action(k):
    k = normalize_key(k)
    t = input_tracker["action_last_time"].get(k, -9999.0)
    n = get_time_now()
    if (n - t) <= ACTION_DEBOUNCE_SEC:
        return False
    input_tracker["action_last_time"][k] = n
    return True

def heading_to_unit_vector(heading_deg): #convert player heading angle into a direction vector.
    r = math.radians(heading_deg)
    return math.sin(-r), math.cos(r)

def vector_length_2d(x, y):
    return math.sqrt(x * x + y * y)

def normalize_2d(x, y):
    L = vector_length_2d(x, y)
    if L < 1e-6:
        return 0.0, 0.0
    return x / L, y / L #Unit vector with same direction.

def rotate_vector_2d(x, y, deg):
    r = math.radians(deg)
    cs, sn = math.cos(r), math.sin(r)
    return (x * cs - y * sn), (x * sn + y * cs)

def build_static_env():
    L, R = grid_world_min(), grid_world_max()
    B, T = grid_world_min(), grid_world_max()

    tree_spacing = 200 # tree making 
    trees = []

    for x in range(int(L), int(R), tree_spacing):
        trees.append((x, B + 50, 0)) # bottom edge 
        trees.append((x, T - 50, 0)) # top edge

    for y in range(int(B), int(T), tree_spacing):
        trees.append((L + 50, y, 0)) # left edge
        trees.append((R - 50, y, 0)) # right edge 

    static_env["tree_positions"] = trees
    static_env["house_positions"] = [
        (L + 120, B + 120),
        (R - 120, B + 120),
        (R - 120, T - 120),
        (L + 120, T - 120),
    ]


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW["w"], 0, WINDOW["h"])

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glRasterPos2f(x, y)
    for ch in str(text):
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def initialize_lava_positions():
    global lava_tile_cells
    lava_tile_cells = []

    ci, cj = world_pos_to_cell(0.0, 0.0)

    safe_tiles = []
    i = 1
    while i < GRID_TILES - 1:
        j = 1
        while j < GRID_TILES - 1:
            if (i, j) != (ci, cj): # skips playerntsarting and bored outside tiles 
                safe_tiles.append((i, j))
            j += 1
        i += 1

    if not safe_tiles:
        return

    k = LAVA_COUNT if LAVA_COUNT < len(safe_tiles) else len(safe_tiles) # pick 6 lava from 8 tiles check
    lava_tile_cells = random.sample(safe_tiles, k)

def spawn_clouds():
    global rain_clouds
    rain_clouds = []

    n = 0
    while n < 2:
        i = random.randint(3, GRID_TILES - 4)
        j = random.randint(3, GRID_TILES - 4)
        rain_clouds.append({
            "x": grid_world_min() + j * TILE_SIZE + 50,
            "y": grid_world_min() + i * TILE_SIZE + 50,
            "z": 600,
            "cell": (i, j),
            "timer": 0.0,
        })
        n += 1

def update_clouds(dt):
    idx = 0
    while idx < len(rain_clouds):
        c = rain_clouds[idx]
        c["timer"] += dt
        if c["timer"] >= 1.0:
            tile_hazard_map[c["cell"]] = "mud"
            c["timer"] = 0.0 #reset timer so it repeats forever
        idx += 1

def draw_clouds():
    idx = 0
    while idx < len(rain_clouds):
        c = rain_clouds[idx]
        glColor3f(0.8, 0.8, 0.85)
        glPushMatrix()
        glTranslatef(c["x"] - 20, c["y"], c["z"])
        gluSphere(render_quadric, 30, 12, 12)
        glTranslatef(40, 0, 0)
        gluSphere(render_quadric, 35, 12, 12)
        glPopMatrix()
        idx += 1

def spawn_bosses():
    global boss_units
    boss_units = []

    count = 2 if game_state["level"] == 5 else 1
    for i in range(count):
        boss_units.append({
            "x": 0,
            "y": 300 - i * 200,
            "hp": 50,
            "max_hp": 50,
            "speed": 40,
        })

def update_bosses(dt):
    for b in boss_units:
        dx = player_state["x"] - b["x"]
        dy = player_state["y"] - b["y"]
        d = math.hypot(dx, dy)
        if d > 1: # 1 unit far eo will approach 
            b["x"] += (dx / d) * b["speed"] * dt
            b["y"] += (dy / d) * b["speed"] * dt

def draw_bosses():
    for b in boss_units:
        glColor3f(0.6, 0.0, 0.8)
        glPushMatrix()
        glTranslatef(b["x"], b["y"], ENEMY_Z + 60)
        glutSolidCube(120)
        glPopMatrix()

def initialize_level(lvl):
    global enemy_units

    cfg = LEVEL_CONFIG[lvl]
    print(f"Starting Level {lvl}")

    game_state["kills_required"] = cfg["kills"]
    game_state["kills_this_level"] = 0

    game_state["enemy_total"] = 3 + (lvl * 2)
    game_state["is_boss_level"] = cfg["boss"]

    rain_clouds.clear()
    boss_units.clear()
    tile_hazard_map.clear()

    if cfg["lava"]:
        for cell in lava_tile_cells:
            tile_hazard_map[cell] = "lava"

    if cfg["clouds"]:
        spawn_clouds()

    if cfg["boss"]:
        spawn_bosses()

    if not cfg["boss"]:
        initialize_enemies()

def show_level_completion_message(lvl):
    if lvl == 5:
        game_state["level_message_text"] = "CONGRATULATIONS! YOU WIN!"
    else:
        game_state["level_message_text"] = f"LEVEL {lvl-1} COMPLETED!"

    game_state["show_level_message"] = True
    game_state["level_message_timer"] = LEVEL_MESSAGE_DURATION

def update_level_message(dt):
    if game_state["show_level_message"]:
        game_state["level_message_timer"] -= dt
        if game_state["level_message_timer"] <= 0.0:
            game_state["show_level_message"] = False
            game_state["level_message_timer"] = 0.0

def check_level_progression():
    if game_state["kills_this_level"] >= game_state["kills_required"]:
        if game_state["level"] < game_state["max_level"]:
            game_state["level"] += 1
            show_level_completion_message(game_state["level"])
            initialize_level(game_state["level"])
        else:
            show_level_completion_message(game_state["level"])
            print("YOU WIN! You beat all 5 levels!")

def current_hazard_under_player():
    i, j = world_pos_to_cell(player_state["x"], player_state["y"])
    return tile_hazard_map.get((i, j), None)


def spawn_pickup(px, py, ptype):
    pickup_items.append({"x": px, "y": py, "type": ptype, "ttl": PICKUP_TTL})

def maybe_drop_pickup(x, y):
    if random.random() > DROP_CHANCE:
        return
    ptype = "ammo" if random.random() < DROP_AMMO_PROB else "health"
    spawn_pickup(x, y, ptype)

def update_pickups(dt):
    global pickup_items

    i = 0
    while i < len(pickup_items):
        p = pickup_items[i]
        p["ttl"] -= dt

        if p["ttl"] <= 0.0:
            pickup_items.pop(i)
            continue

        if math.hypot(p["x"] - player_state["x"], p["y"] - player_state["y"]) <= PICKUP_RADIUS: # if within radfius, colects it 
            if p["type"] == "ammo":
                weapon_state["ammo"] = min(weapon_state["max_ammo"], weapon_state["ammo"] + AMMO_GAIN)
            else:
                player_state["lives"] = min(MAX_LIVES, player_state["lives"] + HEALTH_GAIN)
            pickup_items.pop(i)
            continue

        i += 1

def draw_pickups():
    for p in pickup_items:
        if p["type"] == "ammo":
            glColor3f(0.0, 1.0, 0.2)
        else:
            glColor3f(0.2, 0.9, 1.0)

        glPushMatrix()
        glTranslatef(p["x"], p["y"], 35.0)
        glutSolidCube(26)
        glPopMatrix()


def draw_roof_pyramid(half_size, height):
    x0, y0, z0 = -half_size, -half_size, 0.0
    x1, y1 = half_size, -half_size
    x2, y2 = half_size, half_size
    x3, y3 = -half_size, half_size
    xt, yt, zt = 0.0, 0.0, height

    glBegin(GL_TRIANGLES)
    glVertex3f(x0, y0, z0); glVertex3f(x1, y1, z0); glVertex3f(xt, yt, zt)
    glVertex3f(x1, y1, z0); glVertex3f(x2, y2, z0); glVertex3f(xt, yt, zt)
    glVertex3f(x2, y2, z0); glVertex3f(x3, y3, z0); glVertex3f(xt, yt, zt)
    glVertex3f(x3, y3, z0); glVertex3f(x0, y0, z0); glVertex3f(xt, yt, zt)
    glEnd()

    glBegin(GL_QUADS)
    glVertex3f(x0, y0, z0)
    glVertex3f(x1, y1, z0)
    glVertex3f(x2, y2, z0)
    glVertex3f(x3, y3, z0)
    glEnd()

def draw_floor_and_walls():
    total = GRID_TILES * GRID_TILES
    t = 0
    while t < total:
        i = t // GRID_TILES
        j = t - (i * GRID_TILES)

        hz = tile_hazard_map.get((i, j), None)
        if hz == "lava":
            glColor3f(1.0, 0.25, 0.05)
        elif hz == "mud":
            glColor3f(0.35, 0.25, 0.12)
        else:
            glColor3f(0.2, 0.8, 0.2)

        x = grid_world_min() + j * TILE_SIZE
        y = grid_world_min() + i * TILE_SIZE

        glBegin(GL_QUADS)
        glVertex3f(x, y, 0.0)
        glVertex3f(x + TILE_SIZE, y, 0.0)
        glVertex3f(x + TILE_SIZE, y + TILE_SIZE, 0.0)
        glVertex3f(x, y + TILE_SIZE, 0.0)
        glEnd()

        t += 1 # next tile 

    L, R = grid_world_min(), grid_world_max()
    B, T = grid_world_min(), grid_world_max()

    tree_spacing = 200
    tree_positions = []

    x = int(L)
    while x < int(R):
        tree_positions.append((x, B + 50, 0))
        x += tree_spacing

    x = int(L)
    while x < int(R):
        tree_positions.append((x, T - 50, 0))
        x += tree_spacing

    y = int(B)
    while y < int(T):
        tree_positions.append((L + 50, y, 0))
        y += tree_spacing

    y = int(B)
    while y < int(T):
        tree_positions.append((R - 50, y, 0))
        y += tree_spacing

    k = 0
    while k < len(tree_positions):
        tx, ty, tz = tree_positions[k]

        glColor3f(0.4, 0.25, 0.1)
        glPushMatrix()
        glTranslatef(tx, ty, tz + 40)
        gluCylinder(render_quadric, 15, 15, 80, 12, 10)
        glPopMatrix()

        glColor3f(0.0, 0.6, 0.1)
        glPushMatrix()
        glTranslatef(tx, ty, tz + 80)
        gluSphere(render_quadric, 40, 12, 12)
        glTranslatef(0, 0, 30)
        gluSphere(render_quadric, 35, 12, 12)
        glTranslatef(0, 0, 30)
        gluSphere(render_quadric, 25, 12, 12)
        glPopMatrix()

        k += 1

    house_positions = [
        (L + 120, B + 120),
        (R - 120, B + 120),
        (R - 120, T - 120),
        (L + 120, T - 120),
    ]

    h = 0
    while h < len(house_positions):
        hx, hy = house_positions[h]

        glColor3f(0.8, 0.7, 0.5)
        glPushMatrix()
        glTranslatef(hx, hy, 50)
        glutSolidCube(100)
        glPopMatrix()

        glColor3f(0.7, 0.2, 0.1)
        glPushMatrix()
        glTranslatef(hx, hy, 100)
        draw_roof_pyramid(70, 60)
        glPopMatrix()

        glColor3f(0.3, 0.2, 0.1)
        glBegin(GL_QUADS)
        glVertex3f(hx - 15, hy - 51, 0)
        glVertex3f(hx + 15, hy - 51, 0)
        glVertex3f(hx + 15, hy - 51, 40)
        glVertex3f(hx - 15, hy - 51, 40)
        glEnd()

        h += 1

def draw_sun(): #top-right corner of arena.
    glColor3f(1.0, 0.9, 0.0)
    glPushMatrix()
    glTranslatef(grid_world_max() - 150, grid_world_max() - 150, 800)
    gluSphere(render_quadric, 80, 20, 20)

    glColor3f(1.0, 0.95, 0.3)
    angle = 0
    while angle < 360:
        glPushMatrix()
        glRotatef(angle, 0, 0, 1)
        glTranslatef(0, 100, 0)
        glScalef(0.3, 2.0, 0.3)
        glutSolidCube(30)
        glPopMatrix()
        angle += 45

    glPopMatrix()


def start_reload():
    if weapon_state["is_reloading"]:
        return
    if weapon_state["ammo"] >= weapon_state["max_ammo"]: #ammo already full, no reload needed.
        return
    weapon_state["is_reloading"] = True
    weapon_state["reload_timer"] = RELOAD_SEC

def update_weapon_timers(dt):
    if weapon_state["cooldown"] > 0.0:
        weapon_state["cooldown"] = max(0.0, weapon_state["cooldown"] - dt)

    if weapon_state["is_reloading"]:
        weapon_state["reload_timer"] -= dt
        if weapon_state["reload_timer"] <= 0.0:
            weapon_state["ammo"] = weapon_state["max_ammo"]
            weapon_state["is_reloading"] = False
            weapon_state["reload_timer"] = 0.0

def spawn_bullet(x, y, dx, dy, dmg):
    player_projectiles.append({"x": x, "y": y, "dx": dx, "dy": dy, "dmg": dmg})

def fire_bullet_heading(heading_deg, dmg):
    dir_x, dir_y = heading_to_unit_vector(heading_deg)
    x = player_state["x"] + dir_x * BULLET_MUZZLE_OFFSET
    y = player_state["y"] + dir_y * BULLET_MUZZLE_OFFSET

    if not is_inside_world_bounds(x, y, pad=12):#If muzzle position would be outside bounds, spawn at player instead.
        x, y = player_state["x"], player_state["y"]

    spawn_bullet(x, y, dir_x * BULLET_SPEED, dir_y * BULLET_SPEED, dmg) #Bullet velocity = direction × speed.

def try_fire_weapon():
    if game_state["is_over"]:
        return
    if weapon_state["is_reloading"]:
        return
    if weapon_state["cooldown"] > 0.0:
        return
    if weapon_state["ammo"] <= 0:
        return

    weapon_state["ammo"] -= 1
    weapon_state["cooldown"] = COOLDOWN_SEC

    if weapon_state["mode"] == 1:
        fire_bullet_heading(player_state["heading_deg"], NORMAL_BULLET_DAMAGE)
    else:
        step = SHOTGUN_SPREAD_DEG / (SHOTGUN_PELLETS - 1) if SHOTGUN_PELLETS > 1 else 0.0
        start = -SHOTGUN_SPREAD_DEG / 2.0
        for i in range(SHOTGUN_PELLETS):
            off = start + i * step
            fire_bullet_heading((player_state["heading_deg"] + off) % 360.0, SHOTGUN_PELLET_DAMAGE)

def update_bullets(dt):
    global player_projectiles

    i = 0
    while i < len(player_projectiles):
        b = player_projectiles[i]
        b["x"] += b["dx"] * dt
        b["y"] += b["dy"] * dt

        if not is_inside_world_bounds(b["x"], b["y"], pad=0.0):
            player_projectiles.pop(i)
            continue

        i += 1

def draw_bullets():
    glColor3f(1.0, 0.0, 0.0)
    proj = player_projectiles
    for b in proj:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], BULLET_Z)
        glutSolidCube(BULLET_CUBE_SIZE)
        glPopMatrix()

def spawn_enemy_bullet(x, y, dir_x, dir_y):
    enemy_projectiles.append({
        "x": x, "y": y,
        "dx": dir_x * ENEMY_BULLET_SPEED,
        "dy": dir_y * ENEMY_BULLET_SPEED,
        "dmg": ENEMY_BULLET_DAMAGE,
    })
def spawn_sun_projectile():
    # Sun position
    sun_x = grid_world_max() - 150
    sun_y = grid_world_max() - 150
    sun_z = 800

    # Pick random target tile
    target_i = random.randint(1, GRID_TILES - 2)
    target_j = random.randint(1, GRID_TILES - 2)

    # Calculate target position
    target_x = grid_world_min() + target_j * TILE_SIZE + 50
    target_y = grid_world_min() + target_i * TILE_SIZE + 50
    target_z = 0

    # Direction vector
    dx = target_x - sun_x
    dy = target_y - sun_y
    dz = target_z - sun_z

    dist = math.sqrt(dx*dx + dy*dy + dz*dz)

    if dist > 0:
        speed = 400.0  # Adjust speed as needed
        dx = (dx / dist) * speed
        dy = (dy / dist) * speed
        dz = (dz / dist) * speed

    sun_projectiles.append({
        "x": sun_x, "y": sun_y, "z": sun_z,
        "dx": dx, "dy": dy, "dz": dz,
        "target_cell": (target_i, target_j)
    })

def update_sun_projectiles(dt):
    global sun_projectiles

    i = 0
    while i < len(sun_projectiles):
        p = sun_projectiles[i]
        p["x"] += p["dx"] * dt
        p["y"] += p["dy"] * dt
        p["z"] += p["dz"] * dt

        # Check if reached ground (z <= 5)
        if p["z"] <= 5:
            tile_hazard_map[p["target_cell"]] = "lava"
            sun_projectiles.pop(i)
            continue

        i += 1
def update_enemy_bullets(dt):
    global enemy_projectiles

    i = 0
    while i < len(enemy_projectiles):
        b = enemy_projectiles[i]
        b["x"] += b["dx"] * dt
        b["y"] += b["dy"] * dt

        if not is_inside_world_bounds(b["x"], b["y"], pad=0.0):#collision 
            enemy_projectiles.pop(i)
            continue

        if math.hypot(b["x"] - player_state["x"], b["y"] - player_state["y"]) <= player_state["hit_radius"] * 0.42:
            if player_state["invincible_timer"] <= 0.0:
                player_state["lives"] = max(0, player_state["lives"] - b["dmg"])
                player_state["invincible_timer"] = INVINCIBLE_SEC
                if player_state["lives"] <= 0:
                    game_state["is_over"] = True
                    game_state["over_cause"] = "enemy bullets"
                    return
            enemy_projectiles.pop(i)
            continue

        i += 1

def draw_enemy_bullets():
    glColor3f(1.0, 1.0, 0.1)
    for b in enemy_projectiles:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], ENEMY_BULLET_Z)
        glutSolidCube(ENEMY_BULLET_SIZE)
        glPopMatrix()

def draw_sun_projectiles():
    glColor3f(1.0, 0.0, 0.0)  # Red color
    for p in sun_projectiles:
        glPushMatrix()
        glTranslatef(p["x"], p["y"], p["z"])
        gluSphere(render_quadric, 12, 12, 12)  # Red sphere
        glPopMatrix()
def pick_enemy_type():
    r = random.random()

    if game_state["level"] <= 1:
        return "chaser" if r < 0.65 else "fast"

    if game_state["level"] <= 3:
        if r < 0.48:
            return "chaser"
        if r < 0.78:
            return "fast"
        if r < 0.92:
            return "tank"
        return "shooter"

    if r < 0.38:
        return "chaser"
    if r < 0.65:
        return "fast"
    if r < 0.82:
        return "tank"
    return "shooter"

def enemy_hp_for_type(t):
    base = ENEMY_TYPES[t]["hp_base"]
    lvl = game_state["level"]

    if t == "tank":
        return base + (lvl // 2)
    if t == "chaser":
        return base + (lvl // 3)
    if t == "shooter":
        return base + (lvl // 3)
    return base + (lvl // 4)

def make_enemy_spawn(min_dist_from_player=220.0):
    for _ in range(300):
        rx = random.uniform(grid_world_min() + 85, grid_world_max() - 85)
        ry = random.uniform(grid_world_min() + 85, grid_world_max() - 85)

        if math.hypot(rx - player_state["x"], ry - player_state["y"]) < min_dist_from_player:
            continue

        ok = True
        for ee in enemy_units:
            if math.hypot(rx - ee["x"], ry - ee["y"]) < ENEMY_MIN_SEP:
                ok = False
                break

        if ok:
            t = pick_enemy_type()
            hp = enemy_hp_for_type(t)
            info = ENEMY_TYPES[t]

            e = {
                "x": rx, "y": ry,
                "type": t,
                "speed": info["speed"] * random.uniform(0.90, 1.10),
                "radius": info["radius"],
                "color": info["color"],
                "hp": hp,
                "max_hp": hp,
            }

            if t == "shooter":
                e["shoot_cd"] = random.uniform(0.15, SHOOTER_FIRE_INTERVAL)
                e["orbit_dir"] = random.choice([-1, 1])

            return e

    t = pick_enemy_type()
    hp = enemy_hp_for_type(t)
    info = ENEMY_TYPES[t]

    e = {
        "x": grid_world_min() + 110, "y": grid_world_min() + 110,
        "type": t,
        "speed": info["speed"] * random.uniform(0.90, 1.10),
        "radius": info["radius"],
        "color": info["color"],
        "hp": hp,
        "max_hp": hp,
    }
    if t == "shooter":
        e["shoot_cd"] = random.uniform(0.15, SHOOTER_FIRE_INTERVAL)
        e["orbit_dir"] = random.choice([-1, 1])

    return e

def initialize_enemies():
    enemy_units.clear()
    n = 0
    while n < game_state["enemy_total"]:
        enemy_units.append(make_enemy_spawn())
        n += 1

def shooter_try_fire(e, dt):
    e["shoot_cd"] -= dt
    if e["shoot_cd"] > 0.0:
        return

    dx = player_state["x"] - e["x"]
    dy = player_state["y"] - e["y"]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return

    dir_x, dir_y = dx / d, dy / d
    off = random.uniform(-SHOOTER_SPREAD_DEG, SHOOTER_SPREAD_DEG)
    dir_x, dir_y = rotate_vector_2d(dir_x, dir_y, off)

    spawn_enemy_bullet(e["x"], e["y"], dir_x, dir_y) # fire bullets 
    e["shoot_cd"] = SHOOTER_FIRE_INTERVAL

def move_enemies(dt):
    if game_state["is_over"]:
        return

    idx = 0
    while idx < len(enemy_units):
        e = enemy_units[idx]
        dx = player_state["x"] - e["x"]
        dy = player_state["y"] - e["y"]
        d = math.hypot(dx, dy)

        if e["type"] == "shooter":
            if d > 1e-6:
                nx, ny = dx / d, dy / d
            else:
                nx, ny = 0.0, 0.0

            if d > SHOOTER_DESIRED_RANGE:
                e["x"] += nx * e["speed"] * dt
                e["y"] += ny * e["speed"] * dt
            else:
                px, py = -ny, nx
                orbit_dir = e.get("orbit_dir", 1)
                e["x"] += px * e["speed"] * dt * orbit_dir * SHOOTER_ORBIT_MULT
                e["y"] += py * e["speed"] * dt * orbit_dir * SHOOTER_ORBIT_MULT

                if d < SHOOTER_DESIRED_RANGE * 0.72:
                    e["x"] -= nx * e["speed"] * dt * 0.8
                    e["y"] -= ny * e["speed"] * dt * 0.8

            shooter_try_fire(e, dt)

        else:
            if d > 1e-6:
                e["x"] += (dx / d) * e["speed"] * dt
                e["y"] += (dy / d) * e["speed"] * dt

        e["x"] = clamp_float(e["x"], grid_world_min() + 60, grid_world_max() - 60)
        e["y"] = clamp_float(e["y"], grid_world_min() + 60, grid_world_max() - 60)

        idx += 1

def update_enemy_pulse():
    if game_state["is_over"]:
        return

    if enemy_pulse_anim["growing"]:
        enemy_pulse_anim["scale"] += ENEMY_SCALE_STEP
        if enemy_pulse_anim["scale"] >= ENEMY_SCALE_MAX:
            enemy_pulse_anim["growing"] = False
    else:
        enemy_pulse_anim["scale"] -= ENEMY_SCALE_STEP
        if enemy_pulse_anim["scale"] <= ENEMY_SCALE_MIN:
            enemy_pulse_anim["growing"] = True

def draw_enemy_hp_bar(e):
    if e["max_hp"] <= 0:
        return

    frac = max(0.0, min(1.0, e["hp"] / e["max_hp"]))

    w = 90.0
    h = 10.0
    z = ENEMY_Z + e["radius"] * 2.4

    x0 = e["x"] - w / 2.0
    y0 = e["y"] - h / 2.0

    glColor3f(0.15, 0.15, 0.15)
    glBegin(GL_QUADS)
    glVertex3f(x0,       y0,       z)
    glVertex3f(x0 + w,   y0,       z)
    glVertex3f(x0 + w,   y0 + h,   z)
    glVertex3f(x0,       y0 + h,   z)
    glEnd()

    glColor3f(1.0 - frac, frac, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(x0,          y0,       z + 0.5)
    glVertex3f(x0 + w*frac, y0,       z + 0.5)
    glVertex3f(x0 + w*frac, y0 + h,   z + 0.5)
    glVertex3f(x0,          y0 + h,   z + 0.5)
    glEnd()

def draw_enemies():
    idx = 0
    while idx < len(enemy_units):
        e = enemy_units[idx]

        t = e["type"]
        r = e["radius"]
        cr, cg, cb = e["color"]

        glPushMatrix()
        glTranslatef(e["x"], e["y"], ENEMY_Z)
        glScalef(enemy_pulse_anim["scale"], enemy_pulse_anim["scale"], 1.0)
        glColor3f(cr, cg, cb)

        if t == "chaser":
            gluSphere(render_quadric, r, 16, 16)

        elif t == "fast":
            glTranslatef(0, 0, r * 0.2)
            gluCylinder(render_quadric, r * 0.95, r * 0.2, r * 2.2, 16, 12)

        elif t == "tank":
            glTranslatef(0, 0, r * 0.7)
            glutSolidCube(r * 2.1)

        elif t == "shooter":
            glTranslatef(0, 0, r * 0.55)

            num_segments = 12
            ring_radius = r * 0.75
            tube_radius = r * 0.25

            seg = 0
            while seg < num_segments:
                angle = (360.0 / num_segments) * seg
                x = ring_radius * math.cos(math.radians(angle))
                y = ring_radius * math.sin(math.radians(angle))

                glPushMatrix()
                glTranslatef(x, y, 0)
                gluSphere(render_quadric, tube_radius, 6, 6)
                glPopMatrix()

                seg += 1

        glPopMatrix()

        glPushMatrix()
        glTranslatef(e["x"], e["y"], ENEMY_Z + (r * 1.6))
        glScalef(enemy_pulse_anim["scale"], enemy_pulse_anim["scale"], 1.0)
        glColor3f(0.0, 0.0, 0.0)
        gluSphere(render_quadric, r * 0.35, 14, 14)
        glPopMatrix()

        draw_enemy_hp_bar(e)
        idx += 1


def bullet_hits_enemy(bx, by):
    for i, e in enumerate(enemy_units):
        hit_r = (e["radius"] * enemy_pulse_anim["scale"]) + 20.0
        if math.hypot(bx - e["x"], by - e["y"]) <= hit_r:
            return i
    return -1

def bullet_hits_boss(bx, by):
    for i, b in enumerate(boss_units):
        if math.hypot(bx - b["x"], by - b["y"]) <= 70:
            return i
    return -1

def update_bullet_enemy_hits():
    global player_projectiles

    i = 0
    while i < len(player_projectiles):
        b = player_projectiles[i]

        if boss_units:
            boss_hit = bullet_hits_boss(b["x"], b["y"])
            if boss_hit != -1:
                boss_units[boss_hit]["hp"] -= b["dmg"]

                if boss_units[boss_hit]["hp"] <= 0:
                    ex, ey = boss_units[boss_hit]["x"], boss_units[boss_hit]["y"]
                    maybe_drop_pickup(ex, ey)

                    player_state["score"] += 10
                    game_state["kills_this_level"] += 1

                    print(f"Boss defeated! Kills: {game_state['kills_this_level']}/{game_state['kills_required']}")
                    boss_units.pop(boss_hit)

                    if game_state["kills_this_level"] >= game_state["kills_required"]:
                        check_level_progression()

                player_projectiles.pop(i)
                continue

        hit_i = bullet_hits_enemy(b["x"], b["y"])
        if hit_i != -1:
            enemy_units[hit_i]["hp"] -= b["dmg"]

            if enemy_units[hit_i]["hp"] <= 0:
                ex, ey = enemy_units[hit_i]["x"], enemy_units[hit_i]["y"]
                maybe_drop_pickup(ex, ey)

                player_state["score"] += 1
                game_state["kills_this_level"] += 1

                print(f"Enemy killed! Kills: {game_state['kills_this_level']}/{game_state['kills_required']}")

                if not game_state["is_boss_level"]:
                    enemy_units[hit_i] = make_enemy_spawn()
                else:
                    enemy_units.pop(hit_i)

                if game_state["kills_this_level"] >= game_state["kills_required"]:
                    check_level_progression()

            player_projectiles.pop(i)
            continue

        i += 1

def check_enemy_player_hits():
    i = len(enemy_units) - 1
    while i >= 0:
        e = enemy_units[i]
        er = e["radius"] * enemy_pulse_anim["scale"]

        if math.hypot(e["x"] - player_state["x"], e["y"] - player_state["y"]) <= (PLAYER_HIT_RADIUS + er) * 0.55:
            if player_state["invincible_timer"] <= 0.0:
                player_state["lives"] = max(0, player_state["lives"] - 1)
                player_state["invincible_timer"] = INVINCIBLE_SEC

                if not game_state["is_boss_level"]:
                    enemy_units[i] = make_enemy_spawn()
                else:
                    enemy_units.pop(i)

                if player_state["lives"] <= 0:
                    game_state["is_over"] = True
                    game_state["over_cause"] = "enemy contact"
                    return
        i -= 1

    j = 0
    while j < len(boss_units):
        b = boss_units[j]
        if math.hypot(b["x"] - player_state["x"], b["y"] - player_state["y"]) <= 90:
            if player_state["invincible_timer"] <= 0.0:
                player_state["lives"] = max(0, player_state["lives"] - 2)
                player_state["invincible_timer"] = INVINCIBLE_SEC

                if player_state["lives"] <= 0:
                    game_state["is_over"] = True
                    game_state["over_cause"] = "boss contact"
                    return
        j += 1


def clamp_player_to_grid():
    pad = player_state["hit_pad"]
    mn = grid_world_min() + pad
    mx = grid_world_max() - pad

    if player_state["x"] < mn:
        player_state["x"] = mn
        player_state["vx"] = 0.0
    elif player_state["x"] > mx:
        player_state["x"] = mx
        player_state["vx"] = 0.0

    if player_state["y"] < mn:
        player_state["y"] = mn
        player_state["vy"] = 0.0
    elif player_state["y"] > mx:
        player_state["y"] = mx
        player_state["vy"] = 0.0

def start_dash():
    if game_state["is_over"]:
        return
    if player_state["dash_cd"] > 0.0:
        return
    if player_state["is_dashing"]:
        return

    dx, dy = heading_to_unit_vector(player_state["heading_deg"])
    player_state["dash_dir_x"], player_state["dash_dir_y"] = dx, dy
    player_state["is_dashing"] = True
    player_state["dash_timer"] = DASH_DURATION

def update_dash(dt):
    if player_state["dash_cd"] > 0.0:
        player_state["dash_cd"] = max(0.0, player_state["dash_cd"] - dt)

    if not player_state["is_dashing"]:
        return

    player_state["dash_timer"] -= dt

    player_state["vx"] = player_state["dash_dir_x"] * DASH_SPEED
    player_state["vy"] = player_state["dash_dir_y"] * DASH_SPEED

    if player_state["dash_timer"] <= 0.0:
        player_state["is_dashing"] = False
        player_state["dash_timer"] = 0.0
        player_state["dash_cd"] = DASH_COOLDOWN

def apply_hazards(dt):
    hz = current_hazard_under_player()

    if hz == "lava":
        game_state["lava_timer"] += dt
        if game_state["lava_timer"] >= LAVA_TICK_SEC:
            game_state["lava_timer"] = 0.0
            player_state["lives"] = max(0, player_state["lives"] - 1)
            if player_state["lives"] <= 0:
                game_state["is_over"] = True
                game_state["over_cause"] = "lava"
    else:
        game_state["lava_timer"] = 0.0

def update_invincible(dt):
    if player_state["invincible_timer"] > 0.0:
        player_state["invincible_timer"] = max(0.0, player_state["invincible_timer"] - dt)
#Updates player position and rotation based on movement speed
def update_player(dt):
    update_dash(dt)

    a_down = is_key_held(b"a")
    d_down = is_key_held(b"d")

    if a_down and not d_down:
        player_state["heading_deg"] = (player_state["heading_deg"] + TURN_SPEED_DEG * dt) % 360.0
    elif d_down and not a_down:
        player_state["heading_deg"] = (player_state["heading_deg"] - TURN_SPEED_DEG * dt) % 360.0

    if player_state["is_dashing"]:
        player_state["x"] += player_state["vx"] * dt
        player_state["y"] += player_state["vy"] * dt
        clamp_player_to_grid()
        return

    hz = current_hazard_under_player()
    mud_mult = MUD_SLOW_MULT if hz == "mud" else 1.0

    accel = PLAYER_ACCEL * (SPRINT_MULT if player_state["sprint_on"] else 1.0) * mud_mult
    max_speed = PLAYER_MAX_SPEED * (SPRINT_MULT if player_state["sprint_on"] else 1.0) * mud_mult

    fwd_x, fwd_y = heading_to_unit_vector(player_state["heading_deg"])
    left_x, left_y = -fwd_y, fwd_x
    right_x, right_y = fwd_y, -fwd_x

    ax, ay = 0.0, 0.0

    if is_key_held(b"w"):
        ax += fwd_x * accel
        ay += fwd_y * accel
    if is_key_held(b"s"):
        ax -= fwd_x * accel
        ay -= fwd_y * accel

    if a_down:
        ax += left_x * accel
        ay += left_y * accel
    if d_down:
        ax += right_x * accel
        ay += right_y * accel

    player_state["vx"] += ax * dt
    player_state["vy"] += ay * dt

    sp = vector_length_2d(player_state["vx"], player_state["vy"])
    if sp > max_speed:
        nx, ny = normalize_2d(player_state["vx"], player_state["vy"])
        player_state["vx"] = nx * max_speed
        player_state["vy"] = ny * max_speed

    player_state["x"] += player_state["vx"] * dt
    player_state["y"] += player_state["vy"] * dt

    damp = FRICTION_PER_FRAME ** (dt * 60.0)
    player_state["vx"] *= damp
    player_state["vy"] *= damp

    clamp_player_to_grid()


def draw_weapon_model():
    if weapon_state["mode"] == 1:
        glColor3f(0.15, 0.15, 0.15)
        glPushMatrix()
        glTranslatef(0, 18, 85)
        glScalef(0.65, 1.1, 0.55)
        glutSolidCube(40)
        glPopMatrix()

        glColor3f(0.10, 0.10, 0.10)
        glPushMatrix()
        glTranslatef(0, 5, 80)
        glScalef(0.65, 0.9, 0.45)
        glutSolidCube(45)
        glPopMatrix()

        glColor3f(0.75, 0.75, 0.75)
        glPushMatrix()
        glTranslatef(0, 35, 98)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(render_quadric, 5.5, 4.0, 130, 18, 12)
        glPopMatrix()

        glColor3f(0.6, 0.6, 0.6)
        glPushMatrix()
        glTranslatef(0, 35 + 130, 98)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(render_quadric, 6.5, 6.0, 10, 16, 10)
        glPopMatrix()

        glColor3f(0.2, 0.2, 0.2)
        glPushMatrix()
        glTranslatef(0, 18, 112)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(render_quadric, 4.0, 4.0, 40, 14, 10)
        glPopMatrix()

        glColor3f(0.12, 0.12, 0.12)
        glPushMatrix()
        glTranslatef(0, 16, 72)
        glScalef(0.22, 0.35, 0.45)
        glutSolidCube(40)
        glPopMatrix()

    else:
        glColor3f(0.12, 0.12, 0.12)
        glPushMatrix()
        glTranslatef(0, 16, 88)
        glScalef(0.85, 1.25, 0.65)
        glutSolidCube(42)
        glPopMatrix()

        glColor3f(0.35, 0.22, 0.12)
        glPushMatrix()
        glTranslatef(0, 2, 82)
        glScalef(0.9, 1.0, 0.55)
        glutSolidCube(48)
        glPopMatrix()

        glColor3f(0.70, 0.70, 0.70)
        for off in (-5.0, 5.0):
            glPushMatrix()
            glTranslatef(off, 35, 100)
            glRotatef(-90, 1, 0, 0)
            gluCylinder(render_quadric, 6.2, 5.5, 105, 18, 12)
            glPopMatrix()

        glColor3f(0.18, 0.18, 0.18)
        glPushMatrix()
        glTranslatef(0, 35 + 40, 86)
        glScalef(0.55, 0.55, 0.35)
        glutSolidCube(32)
        glPopMatrix()

        glColor3f(0.10, 0.10, 0.10)
        glPushMatrix()
        glTranslatef(0, 15, 70)
        glScalef(0.25, 0.4, 0.55)
        glutSolidCube(42)
        glPopMatrix()

def draw_player():
    glPushMatrix()
    glTranslatef(player_state["x"], player_state["y"], 0.0)

    if game_state["is_over"]:
        glRotatef(90.0, 1.0, 0.0, 0.0)
    else:
        glRotatef(player_state["heading_deg"], 0.0, 0.0, 1.0)

    inv = (player_state["invincible_timer"] > 0.0)
    if not inv:
        glColor3f(0.2, 0.2, 0.9)
    else:
        glColor3f(1.0, 1.0, 0.2)

    glPushMatrix()
    glTranslatef(-12, 0, 0)
    gluCylinder(render_quadric, 4, 8, 55, 12, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(12, 0, 0)
    gluCylinder(render_quadric, 4, 8, 55, 12, 10)
    glPopMatrix()

    if not inv:
        glColor3f(0.0, 0.55, 0.0)
    else:
        glColor3f(0.6, 0.6, 0.2)

    glPushMatrix()
    glTranslatef(0, 0, 85)
    glScalef(0.9, 0.55, 2.0)
    glutSolidCube(35)
    glPopMatrix()

    glColor3f(1.0, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(-26, 12, 95)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(render_quadric, 8, 3, 45, 12, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(26, 12, 95)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(render_quadric, 8, 3, 45, 12, 10)
    glPopMatrix()

    glPushMatrix()
    draw_weapon_model()
    glPopMatrix()

    glColor3f(0.0, 0.0, 0.0)
    glPushMatrix()
    glTranslatef(0, 0, 130)
    gluSphere(render_quadric, 22, 14, 14)
    glPopMatrix()

    glPopMatrix()


def apply_camera_transform():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y, ASPECT_RATIO, NEAR_CLIP, FAR_CLIP)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if is_special_held(GLUT_KEY_LEFT):
        camera_state["orbit_deg"] -= camera_state["orbit_step"]
    if is_special_held(GLUT_KEY_RIGHT):
        camera_state["orbit_deg"] += camera_state["orbit_step"]
    if is_special_held(GLUT_KEY_UP):
        camera_state["height"] += camera_state["height_step"]
    if is_special_held(GLUT_KEY_DOWN):
        camera_state["height"] -= camera_state["height_step"]

    camera_state["orbit_deg"] %= 360.0
    camera_state["height"] = clamp_float(camera_state["height"], camera_state["height_min"], camera_state["height_max"])

    r = math.radians(camera_state["orbit_deg"])
    cam_x = math.cos(r) * camera_state["radius"]
    cam_y = math.sin(r) * camera_state["radius"]
    cam_z = camera_state["height"]

    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 0, 1)

def on_key_press(key, x, y):
    k = normalize_key(key)
    input_tracker["keys_last_time"][k] = get_time_now()

    if k in (b"t",):
        if _debounced_action(k):
            reset_game_state()
        return
#this one will not work as we feel useless to do so
    if k in (b"e",):
        if _debounced_action(k):
            player_state["sprint_on"] = not player_state["sprint_on"]
        return

    if k in (b"r",):
        start_reload()
        return

    if k in (b"q",):
        start_dash()
        return

    if k == b"1":
        weapon_state["mode"] = 1
        return
    if k == b"2":
        weapon_state["mode"] = 2
        return

    if k in (b" ", b"f"):
        try_fire_weapon()
        return

def on_special_key(key, x, y):
    input_tracker["special_last_time"][key] = get_time_now()

def on_mouse_click(button, state, x, y):
    if state != GLUT_DOWN:
        return
    if button == GLUT_LEFT_BUTTON:
        try_fire_weapon()


def reset_game_state():
    input_tracker["keys_last_time"] = {}
    input_tracker["special_last_time"] = {}
    input_tracker["action_last_time"] = {}

    player_state["x"], player_state["y"] = 0.0, 0.0
    player_state["vx"], player_state["vy"] = 0.0, 0.0
    player_state["heading_deg"] = 0.0
    player_state["lives"] = MAX_LIVES
    player_state["score"] = 0
    player_state["invincible_timer"] = 0.0
    player_state["sprint_on"] = False

    player_state["is_dashing"] = False
    player_state["dash_timer"] = 0.0
    player_state["dash_cd"] = 0.0
    player_state["dash_dir_x"], player_state["dash_dir_y"] = 0.0, 1.0

    weapon_state["mode"] = 1
    weapon_state["ammo"] = weapon_state["max_ammo"]
    weapon_state["cooldown"] = 0.0
    weapon_state["is_reloading"] = False
    weapon_state["reload_timer"] = 0.0

    camera_state["orbit_deg"] = 270.0
    camera_state["height"] = 900.0
    camera_state["radius"] = 900.0

    game_state["is_over"] = False
    game_state["over_cause"] = ""
    game_state["level"] = 1
    game_state["kills_this_level"] = 0
    game_state["lava_timer"] = 0.0

    game_state["show_level_message"] = False
    game_state["level_message_text"] = ""
    game_state["level_message_timer"] = 0.0

    player_projectiles.clear()
    enemy_projectiles.clear()
    pickup_items.clear()
    rain_clouds.clear()
    boss_units.clear()
    enemy_units.clear()
    tile_hazard_map.clear()
    sun_projectiles.clear()
    game_state["sun_shoot_timer"] = 0.0
    enemy_pulse_anim["scale"] = ENEMY_SCALE_MIN
    enemy_pulse_anim["growing"] = True

    build_static_env()
    initialize_lava_positions()
    initialize_level(game_state["level"])
#Main game loop - updates player, bullets, enemies, spawns enemies, checks collisions
def game_tick():
    global last_tick_time

    now = time.time()
    dt = now - last_tick_time
    last_tick_time = now

    if dt > 0.05:
        dt = 0.05

    if not game_state["is_over"]:
        update_weapon_timers(dt)
        update_player(dt)

        update_invincible(dt)
        apply_hazards(dt)
        update_pickups(dt)
        update_level_message(dt)

        if rain_clouds:
            update_clouds(dt)

        if boss_units:
            update_bosses(dt)
        # Sun shooting logic (only on lava levels)
        cfg = LEVEL_CONFIG[game_state["level"]]
        if cfg["lava"]:
            game_state["sun_shoot_timer"] += dt
            if game_state["sun_shoot_timer"] >= game_state["sun_shoot_interval"]:
                spawn_sun_projectile()
                game_state["sun_shoot_timer"] = 0.0

        update_sun_projectiles(dt)
        move_enemies(dt)
        update_enemy_pulse()

        update_bullets(dt)
        update_bullet_enemy_hits()

        update_enemy_bullets(dt)
        check_enemy_player_hits()

    glutPostRedisplay()
# Main rendering function - clears screen, draws floor, player, enemies, bullets, UI
def render_frame():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW["w"], WINDOW["h"])

    apply_camera_transform()
    draw_floor_and_walls()
    draw_sun()

    if rain_clouds:
        draw_clouds()
    if boss_units:
        draw_bosses()

    draw_enemies()
    draw_pickups()
    draw_enemy_bullets()
    draw_bullets()
    draw_sun_projectiles()
    draw_player()

    draw_text(15, 770, "3D ARENA SURVIVAL SHOOTER GAME")

    if not game_state["is_over"]:
        draw_text(
            15, 742,
            "W/S move | A/D rotate+strafe | Q dash | E sprint | Arrows camera | LMB/Space/F shoot | R reload | 1/2 mode | T reset"
        )
        draw_text(15, 712, f"LEVEL: {game_state['level']}/{game_state['max_level']}   Kills: {game_state['kills_this_level']}/{game_state['kills_required']}")
        draw_text(15, 682, f"Life: {player_state['lives']}/{MAX_LIVES}   Score: {player_state['score']}")

        mode_name = "Normal" if weapon_state["mode"] == 1 else "Shotgun"
        reload_txt = "RELOADING..." if weapon_state["is_reloading"] else ""
        draw_text(15, 652, f"Ammo: {weapon_state['ammo']}/{weapon_state['max_ammo']}   Mode: {mode_name}   Cooldown: {weapon_state['cooldown']:.2f}  {reload_txt}")

        dash_txt = "READY" if (player_state["dash_cd"] <= 0.0 and not player_state["is_dashing"]) else f"{player_state['dash_cd']:.1f}s"
        sprint_txt = "ON" if player_state["sprint_on"] else "OFF"
        inv_txt = f"INV {player_state['invincible_timer']:.2f}s" if player_state["invincible_timer"] > 0 else "INV OFF"
        draw_text(15, 622, f"Sprint: {sprint_txt}   Dash: {dash_txt}   {inv_txt}")

        hz = current_hazard_under_player()
        hz_txt = "LAVA (damage)" if hz == "lava" else ("MUD (slow)" if hz == "mud" else "NONE")
        draw_text(15, 592, f"Hazard under you: {hz_txt} | Pickups: ammo=GREEN, health=CYAN | Enemy bullets=YELLOW")
        draw_text(15, 562, "Enemy: chaser=sphere (red), fast=cone (orange), tank=cube (purple), shooter=torus (cyan)")

        if game_state["is_boss_level"]:
            draw_text(15, 532, f"BOSS LEVEL! Defeat {len(boss_units)} boss(es) to proceed!")
        elif rain_clouds:
            draw_text(15, 532, "Watch out for CLOUDS - they create MUD where they rain!")

    else:
        if game_state["level"] >= game_state["max_level"] and game_state["kills_this_level"] >= game_state["kills_required"]:
            draw_text(15, 740, f"CONGRATULATIONS! You beat all {game_state['max_level']} levels! Final Score: {player_state['score']}")
        else:
            draw_text(15, 740, f"GAME OVER ({game_state['over_cause']}). Level: {game_state['level']}  Score: {player_state['score']}")
        draw_text(15, 710, "Press T to restart")

    if game_state["show_level_message"]:
        glColor3f(0.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex3f(250, 350, 0)
        glVertex3f(750, 350, 0)
        glVertex3f(750, 450, 0)
        glVertex3f(250, 450, 0)
        glEnd()

        draw_text(350, 400, game_state["level_message_text"])

    glutSwapBuffers()


def main():
    global render_quadric

    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW["w"], WINDOW["h"])
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"3D ARENA SURVIVAL SHOOTER GAME")

    glEnable(GL_DEPTH_TEST)

    render_quadric = gluNewQuadric()
    reset_game_state()

    glutDisplayFunc(render_frame)
    glutKeyboardFunc(on_key_press)
    glutSpecialFunc(on_special_key)
    glutMouseFunc(on_mouse_click)
    glutIdleFunc(game_tick)

    glutMainLoop()

if __name__ == "__main__":
    main()

