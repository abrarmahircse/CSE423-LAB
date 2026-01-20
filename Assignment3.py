from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
from OpenGL.GLU import *
import math, random

window_width, window_height = 1000, 800
aspect_ratio = window_width / window_height
fov_y = 68.0 # field of view 
near_clip = 1.0 # minimum boundary camera clipped
far_clip = 3000.0

grid_tiles = 13 # 13x13 dimension of playard 
tile_size = 100.0 #100 units wide
grid_world_size = grid_tiles * tile_size# valid play area 
grid_half_size = grid_world_size / 2.0 #world is centered at (0,0). so instaed of 0-1300, we buiult -650 → +650
wall_height = 140.0 # vertical boundary

player_accel = 4.2 #smooth movement, adding velocity 
player_friction = 0.88# smooth, not sliding always
player_turn_step = 12.0 #A/D rotates
player_hit_radius = 62.0 #player’s collision “bubble” size (a radius in world units). # invisible bubble around player to determine hit 

enemy_total = 5
enemy_speed = 0.25
enemy_min_separation = 150.0
enemy_hit_radius_base = 50.0
enemy_scale_min = 0.90 # The smallest the enemy is allowed
enemy_scale_max = 1.35
enemy_scale_step = 0.012  # the scale per frame while pulsing.

bullet_speed = 32.0
bullet_cube_size = 9.0
bullet_max_distance = 4200.0
bullet_muzzle_offset = 92.0 #Bullet starts in front of the gun,
bullet_hit_radius_base = 52.0 #bullet_hit  ≤ enemy_hit_r, you say the bullet hit the enemy.

orbit_step = 3.5 #LEFT/RIGHT arrows rotate camera 3.5 degrees each press.
height_step = 18.0#UP/DOWN arrows raise/lower camera
height_min = 160.0 # camera min height
height_max = 980.0

cheat_spin_speed_deg = 6.0 #gun rotates 6 degrees per frame automatically, hardcoded 
cheat_aim_tol_deg = 4.0 # uptp  deg consideration 

quadric = None
#Player live state
player_pos_x, player_pos_y = 0.0, 0.0 #center (0,0)
player_heading_deg = 0.0
player_lives = 5
player_score = 0
bullets_missed = 0
is_game_over = False
game_over_cause = ""

player_vel_x, player_vel_y = 0.0, 0.0 #movement feels smooth:, velo adding 

enemies = []
enemy_pulse_scale = 1.0
enemy_pulse_growing = True # pulse growws/ shrink every frame 

active_bullets = []#bullet dicts currently flying.

#Camera live state
is_first_person = False # so 3rd person
fp_camera_yaw_deg = 0.0
camera_orbit_deg = 270.0 # angle between center 
camera_height = 900.0 #  big height, top down 
camera_radius = 900.0 # big radius, further away 

is_cheat_mode = False #c
is_auto_cam_follow = False #v
cheat_can_fire = True 


def clamp_value(v, lo, hi): # here v is enemy x , y and cam height pos
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def grid_world_min():
    return -grid_half_size # -650 


def grid_world_max():
    return grid_half_size # +650


def is_inside_grid(x, y, pad=0.0): #pad=shrink the allowed area so objects don’t spawn too close to walls.
    mn = grid_world_min() + pad # min
    mx = grid_world_max() - pad # max 
    return (mn <= x <= mx) and (mn <= y <= mx)


def smallest_angle_diff_deg(a, b):
    d = abs((a - b) % 360.0)
    return d if d <= 180.0 else 360.0 - d # clock , anticlock 


def forward_unit_vector(heading_deg): #takes the player’s heading angle and converts it into a direction vector (dx, dy) (a unit vector).
    r = math.radians(heading_deg)#rad convertion
    return math.sin(-r), math.cos(r) #dx,dy


def angle_to_target_deg(px, py, tx, ty):#takes two points (player and target) and computes the heading angle you’d need to face the target, using the same angle convention as your player.
    dx = tx - px
    dy = ty - py
    #the player face to look from (px,py) toward (tx,ty)
    return math.degrees(math.atan2(-dx, dy)) % 360.0 #“0 degrees” is pointing along +Y (not +X like normal math).
    #math.atan2(y, x) returns an angle in radians


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
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


def make_enemy_spawn(min_dist_from_player=220.0): # enemy recreate, min dis is a param value fixed
    for _ in range(300):# try 300 times for random spot
        rx = random.uniform(grid_world_min() + 85, grid_world_max() - 85)# left , right, keep safe margin 85
        ry = random.uniform(grid_world_min() + 85, grid_world_max() - 85)#
        if math.hypot(rx - player_pos_x, ry - player_pos_y) < min_dist_from_player:#random point is closer than player, reject it
            continue # when it enters here jump back to the for_ loop
        ok = True # enemey far so ok 
        for e in enemies:
            if math.hypot(rx - e["x"], ry - e["y"]) < enemy_min_separation: # same spot re spawn 
                ok = False # dont respawn min speration low 
                break
        if ok:
            return {"x": rx, "y": ry} # Immediately return the new spawn position as a dictionary.
    return {"x": grid_world_min() + 110, "y": grid_world_min() + 110} # after 300, this return safe fallback after 300 tries


def initialize_enemies(): # enemy create 
    global enemies
    enemies = []
    for _ in range(enemy_total): # 5ta 
        enemies.append(make_enemy_spawn())


def trigger_game_over(cause): # ending game 
    global is_game_over, game_over_cause
    if is_game_over: # if game already over do nothing 
        return
    is_game_over = True
    game_over_cause = cause
    print(f"Game is Over. Your Score is {player_score}.")
    print('Press "R" to RESTART the Game.')


def reset_state():# back to base 
    global player_pos_x, player_pos_y, player_heading_deg, player_vel_x, player_vel_y
    global player_lives, player_score, bullets_missed, active_bullets
    global is_game_over, game_over_cause
    global enemy_pulse_scale, enemy_pulse_growing
    global is_first_person, fp_camera_yaw_deg, camera_orbit_deg, camera_height, camera_radius
    global is_cheat_mode, is_auto_cam_follow, cheat_can_fire

    player_pos_x, player_pos_y = 0.0, 0.0# respawn at center
    player_heading_deg = 0.0
    player_vel_x, player_vel_y = 0.0, 0.0#Stops any leftover movement., may not slide 

    player_lives = 5
    player_score = 0
    bullets_missed = 0
    active_bullets = []

    is_game_over = False
    game_over_cause = ""# empty string, clears reason basically 

    enemy_pulse_scale = enemy_scale_min # chotosize 
    enemy_pulse_growing = True  # growing up down
    initialize_enemies()

    is_first_person = False
    fp_camera_yaw_deg = 0.0

    camera_orbit_deg = 270.0
    camera_height = 900.0
    camera_radius = 900.0

    is_cheat_mode = False
    is_auto_cam_follow = False
    cheat_can_fire = True # cheat mode is allowed to shoot now 

    print("Game Restarted.")
    print(f"Remaining Player Life: {player_lives}")
    print(f"Bullet missed: {bullets_missed}")


def draw_floor_and_walls():
    for i in range(grid_tiles):
        for j in range(grid_tiles):
            if (i + j) % 2 == 0: # even 
                glColor3f(1.0, 1.0, 1.0)
            else:# violet 
                glColor3f(0.7, 0.5, 0.95)
                #rowi, col j 
            x = grid_world_min() + j * tile_size  #position = starting_point + (index × step_size), x eer kaje row ek, col diff , j col so adding j 
            y = grid_world_min() + i * tile_size # i chnages, when we move up , rows 
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0.0)
            glVertex3f(x + tile_size, y, 0.0)
            glVertex3f(x + tile_size, y + tile_size, 0.0)
            glVertex3f(x, y + tile_size, 0.0)
            glEnd()

    L, R = grid_world_min(), grid_world_max()
    B, T = grid_world_min(), grid_world_max()

    glColor3f(0.3, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(L, B, 0.0)
    glVertex3f(R, B, 0.0)
    glVertex3f(R, B, wall_height)
    glVertex3f(L, B, wall_height)
    glEnd()

    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(R, B, 0.0)
    glVertex3f(R, T, 0.0)
    glVertex3f(R, T, wall_height)
    glVertex3f(R, B, wall_height)
    glEnd()

    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(R, T, 0.0)
    glVertex3f(L, T, 0.0)
    glVertex3f(L, T, wall_height)
    glVertex3f(R, T, wall_height)
    glEnd()

    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(L, T, 0.0)
    glVertex3f(L, B, 0.0)
    glVertex3f(L, B, wall_height)
    glVertex3f(L, T, wall_height)
    glEnd()


def draw_player():
    glPushMatrix()#Saves the current transformation matrix on a stack.
    glTranslatef(player_pos_x, player_pos_y, 0.0)# after game over, rotate player by 90
    if is_game_over:
        glRotatef(90.0, 1.0, 0.0, 0.0) # deg=90, by x axis 
    else:
        glRotatef(player_heading_deg, 0.0, 0.0, 1.0) # rotate around z axis , xy plane 

    glColor3f(0.2, 0.2, 0.9)
    glPushMatrix()
    glTranslatef(-12, 0, 0)
    gluCylinder(quadric, 4, 8, 55, 12, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(12, 0, 0)
    gluCylinder(quadric, 4, 8, 55, 12, 10)
    glPopMatrix()

    glPushMatrix()
    glColor3f(0.0, 0.55, 0.0)
    glTranslatef(0, 0, 85)
    glScalef(0.9, 0.55, 2.0)
    glutSolidCube(35)
    glPopMatrix()

    glColor3f(1.0, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(-26, 12, 95)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quadric, 8, 3, 45, 12, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(26, 12, 95)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quadric, 8, 3, 45, 12, 10)
    glPopMatrix()

    glColor3f(0.75, 0.75, 0.75)
    glPushMatrix()
    glTranslatef(0, 25, 95)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quadric, 10, 3, 85, 16, 12)
    glPopMatrix()

    glColor3f(0.2, 0.2, 0.2)
    glPushMatrix()
    glTranslatef(0, 25, 80)
    glScalef(0.35, 0.55, 0.9)
    glutSolidCube(30)
    glPopMatrix()

    glColor3f(0.0, 0.0, 0.0)
    glPushMatrix()
    glTranslatef(0, 0, 130)
    gluSphere(quadric, 22, 14, 14)
    glPopMatrix()

    glPopMatrix()


def draw_enemies():
    for e in enemies: # enemeies pyuthon list ( run 5 time)
        ex, ey = e["x"], e["y"]

        glPushMatrix()
        glTranslatef(ex, ey, 40)
        glScalef(enemy_pulse_scale, enemy_pulse_scale, 1.0)
        glColor3f(1.0, 0.0, 0.0)
        gluSphere(quadric, enemy_hit_radius_base, 16, 16)
        glPopMatrix()

        glPushMatrix()
        glTranslatef(ex, ey, 85)
        glScalef(enemy_pulse_scale, enemy_pulse_scale, 1.0)
        glColor3f(0.0, 0.0, 0.0)
        gluSphere(quadric, enemy_hit_radius_base * 0.6, 16, 16)
        glPopMatrix()


bullet_z = 95.0 # game floor z=0, bullet has a height 

def draw_bullets():
    glColor3f(1.0, 0.0, 0.0)
    for b in active_bullets:
        glPushMatrix() # saves current transform, for one bnullet doesnt affect oth
        glTranslatef(b["x"], b["y"], bullet_z) # move the bullet to world coordinates 
        glutSolidCube(bullet_cube_size)
        glPopMatrix()


def spawn_bullet(x, y, dx, dy):#bullets world position on the floor plane
    #x,y= bullet starting 
    #dx,dy=bullet moves each frame
    active_bullets.append({"x": x, "y": y, "dx": dx, "dy": dy, "dist": 0.0}) #
    #dist=how far the bullet has travlled 

def fire_bullet():
    if is_game_over:
        return

    dir_x, dir_y = forward_unit_vector(player_heading_deg) # direction where my gun is facing 
    x = player_pos_x + dir_x * bullet_muzzle_offset # infront of muzzle , not inside 
    y = player_pos_y + dir_y * bullet_muzzle_offset

    if not is_inside_grid(x, y, pad=12): # when muzzle is at grid, bullet spawn at player
        x, y = player_pos_x, player_pos_y

    spawn_bullet(x, y, dir_x * bullet_speed, dir_y * bullet_speed)
    print("Player Bullet Fired!")

def bullet_out_or_far(b):# bullet miss , helper used in udate bullets 
    return (not is_inside_grid(b["x"], b["y"], pad=0.0)) or (b["dist"] > bullet_max_distance)

def bullet_hits_enemy(b):# also helper used in uodate bullets
    hit_r = bullet_hit_radius_base * enemy_pulse_scale
    for i, e in enumerate(enemies):
        #bullet x - enemy x 
        if math.hypot(b["x"] - e["x"], b["y"] - e["y"]) <= hit_r: #If distance is <= hit radius → collision
            return i # if hit 
    return -1 # if not 

def update_bullets():
    global active_bullets, bullets_missed, player_score, cheat_can_fire
    if is_game_over:
        return

    kept = [] # new list bullets
    for b in active_bullets:
        b["x"] += b["dx"]
        b["y"] += b["dy"]
        b["dist"] += bullet_speed

        if bullet_out_or_far(b): # checking miss
            bullets_missed += 1
            print(f"Bullet missed: {bullets_missed}")
            cheat_can_fire = True
            if bullets_missed >= 10:  # if 10 bullets miss game over reason
                trigger_game_over("miss")
            continue #stop processing this bullet right now, go to the next bullet in the loop.
        # if it enters continue it starts from for b in ...

        hit_index = bullet_hits_enemy(b) # checking hit 
        if hit_index != -1:
            player_score += 1
            enemies[hit_index] = make_enemy_spawn()
            cheat_can_fire = True  #cheat mode is allowed to shoot now
            continue

        kept.append(b) #If neither miss nor hit

    active_bullets = kept  #only alive bullets remain


def separate_enemies(): #enemy positions so they don’t overlap.
    min_sep = enemy_min_separation
    min_sep2 = min_sep * min_sep # sqrd is faster than sq root
    eps = 1e-6

    pad = 60.0  
    mn = grid_world_min() + pad # clamp as well
    mx = grid_world_max() - pad

    for i in range(len(enemies)):#Loops through every unique pair of enemies:
        for j in range(i + 1, len(enemies)): # picks next enemy 
            a = enemies[i]
            b = enemies[j]

            dx = a["x"] - b["x"]
            dy = a["y"] - b["y"]
            d2 = dx*dx + dy*dy

            if d2 < eps:#top of each othe
                angle = random.random() * 2.0 * math.pi
                dx = math.cos(angle)
                dy = math.sin(angle)
                d2 = dx*dx + dy*dy

            if d2 < min_sep2:#If too close, push apart
                d = math.sqrt(d2)
                push = (min_sep - d) * 0.5
                nx, ny = dx / d, dy / d# normalizing it in unit directioin 
               #For every pair of enemies, it checks if they’re closer than enemy_min_separation, 
                # and if so, it pushes both apart equally, while keeping them inside the grid.
                a["x"] = clamp_value(a["x"] + nx * push, mn, mx)
                #Enemy A moves forward along the direction from B to A.
                a["y"] = clamp_value(a["y"] + ny * push, mn, mx)

                #Enemy B moves backward along that same direction (so opposite direction).
                b["x"] = clamp_value(b["x"] - nx * push, mn, mx)
                b["y"] = clamp_value(b["y"] - ny * push, mn, mx)

def move_enemies():
    global player_lives
    if is_game_over:
        return

    for i, e in enumerate(enemies):
        dx = player_pos_x - e["x"]# dx=pos, player is to the right of enemy
        dy = player_pos_y - e["y"]# dy above , samme logic 
        d = math.hypot(dx, dy)
        if d > 1e-6:
            e["x"] += (dx / d) * enemy_speed # unit vec
            e["y"] += (dy / d) * enemy_speed

        e["x"] = clamp_value(e["x"], grid_world_min() + 60, grid_world_max() - 60)#inside grid 
        e["y"] = clamp_value(e["y"], grid_world_min() + 60, grid_world_max() - 60)

        enemy_radius = enemy_hit_radius_base * enemy_pulse_scale
        if math.hypot(e["x"] - player_pos_x, e["y"] - player_pos_y) <= (player_hit_radius + enemy_radius) * 0.55:
            #idea: two circles touch when distance ≤ sum of radii.
            #0.55 A tuning hack: makes collision less harsh

            player_lives = max(0, player_lives - 1) # lives minus 1 
            print(f"Remaining Player Life: {player_lives}")
            enemies[i] = make_enemy_spawn()
            if player_lives <= 0: # game over reason 
                trigger_game_over("life")
                return

    separate_enemies()


def update_enemy_pulse():
    global enemy_pulse_scale, enemy_pulse_growing
    if is_game_over:
        return

    if enemy_pulse_growing:
        enemy_pulse_scale += enemy_scale_step
        if enemy_pulse_scale >= enemy_scale_max:# if hit max it will shrink in next frame 

            enemy_pulse_growing = False
    else:# shrinking 
        enemy_pulse_scale -= enemy_scale_step
        if enemy_pulse_scale <= enemy_scale_min:
            enemy_pulse_growing = True


def clamp_player_to_grid():
    global player_pos_x, player_pos_y, player_vel_x, player_vel_y
    pad = 26.0
    mn = grid_world_min() + pad
    mx = grid_world_max() - pad

    if player_pos_x < mn:# left boundaryr o left e 
        player_pos_x = mn
        player_vel_x = 0.0 # stores x velo, so it doesnt push into wall
    elif player_pos_x > mx: # sem logic  
        player_pos_x = mx
        player_vel_x = 0.0

    if player_pos_y < mn:
        player_pos_y = mn
        player_vel_y = 0.0
    elif player_pos_y > mx:
        player_pos_y = mx
        player_vel_y = 0.0


def cheat_logic():
    global player_heading_deg, cheat_can_fire, fp_camera_yaw_deg #where the gun is facing

    player_heading_deg = (player_heading_deg + cheat_spin_speed_deg) % 360.0
    if is_first_person and is_auto_cam_follow:
        fp_camera_yaw_deg = player_heading_deg  #the first-person camera yaw is forced to match the gun’s heading.

    if not cheat_can_fire:
        return

    best_distance = 1e18 # huge no
    best_found = False  # did we find any enemy worth shooting?”

    for e in enemies:
        target_angle = angle_to_target_deg(player_pos_x, player_pos_y, e["x"], e["y"])
        diff = smallest_angle_diff_deg(player_heading_deg, target_angle)
        d = math.hypot(e["x"] - player_pos_x, e["y"] - player_pos_y)
        if diff <= cheat_aim_tol_deg and d < best_distance:
            best_distance = d
            best_found = True

    if best_found:
        fire_bullet()
        cheat_can_fire = False


def keyboardListener(key, x, y):
    global player_heading_deg, player_vel_x, player_vel_y
    global is_cheat_mode, is_auto_cam_follow, fp_camera_yaw_deg

    if is_game_over:
        if key in (b"r", b"R"):
            reset_state()
        return

    if key == b"a":
        player_heading_deg = (player_heading_deg + player_turn_step) % 360.0
        if is_first_person and not is_cheat_mode:
            fp_camera_yaw_deg = player_heading_deg
    elif key == b"d":
        player_heading_deg = (player_heading_deg - player_turn_step) % 360.0
        if is_first_person and not is_cheat_mode:
            fp_camera_yaw_deg = player_heading_deg
    elif key in (b"w", b"s"):
        dir_x, dir_y = forward_unit_vector(player_heading_deg)
        sign = 1.0 if key == b"w" else -1.0
        player_vel_x += dir_x * player_accel * sign
        player_vel_y += dir_y * player_accel * sign
    elif key in (b"c", b"C"):
        is_cheat_mode = not is_cheat_mode
        if is_first_person:
            fp_camera_yaw_deg = player_heading_deg
    elif key in (b"v", b"V"):
        is_auto_cam_follow = not is_auto_cam_follow#V toggles whether the camera follows the gun direction automatically
        if is_first_person and is_cheat_mode and is_auto_cam_follow:#matters in first-person + cheat mode + auto follow on.
            fp_camera_yaw_deg = player_heading_deg
    elif key in (b"r", b"R"):
        reset_state()


def specialKeyListener(key, x, y):
    global camera_orbit_deg, camera_height
    if key == GLUT_KEY_LEFT:
        camera_orbit_deg -= orbit_step
    elif key == GLUT_KEY_RIGHT:
        camera_orbit_deg += orbit_step
    elif key == GLUT_KEY_UP:
        camera_height += height_step
    elif key == GLUT_KEY_DOWN:
        camera_height -= height_step

    camera_orbit_deg %= 360.0
    camera_height = clamp_value(camera_height, height_min, height_max)


def mouseListener(button, state, x, y):
    global is_first_person, fp_camera_yaw_deg
    if state != GLUT_DOWN:
        return
    if button == GLUT_LEFT_BUTTON:
        fire_bullet()
    elif button == GLUT_RIGHT_BUTTON:
        is_first_person = not is_first_person
        fp_camera_yaw_deg = player_heading_deg #camera to look exactly where the player/gun is facing.


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fov_y, aspect_ratio, near_clip, far_clip)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if is_first_person:
        yaw = fp_camera_yaw_deg if (is_cheat_mode and not is_auto_cam_follow) else player_heading_deg
        if is_cheat_mode and is_auto_cam_follow:
            yaw = player_heading_deg # autofoollow 
        dir_x, dir_y = forward_unit_vector(yaw)
        cam_x, cam_y, cam_z = player_pos_x, player_pos_y, 185.0
        look_x = cam_x + dir_x * 140.0 # 140 is how far ahead the camera looks 
        look_y = cam_y + dir_y * 140.0
        gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, cam_z, 0, 0, 1)
    else:
        r = math.radians(camera_orbit_deg)
        cam_x = math.cos(r) * camera_radius
        cam_y = math.sin(r) * camera_radius
        cam_z = camera_height
        gluLookAt(cam_x, cam_y, cam_z, 0,0, 0, 0, 0, 1) # center 000, up direc 001


def idle():
    global player_pos_x, player_pos_y, player_vel_x, player_vel_y #
    if not is_game_over: #Only update the game if it’s still running. If game over, you freeze motion and logic.
        player_pos_x += player_vel_x
        player_pos_y += player_vel_y
        player_vel_x *= player_friction #Apply friction: slow the player down gradually.
        player_vel_y *= player_friction

        clamp_player_to_grid()

        if is_cheat_mode:
            cheat_logic()
            
        move_enemies()
        update_enemy_pulse()
        update_bullets()
    glutPostRedisplay()


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, window_width, window_height)

    setupCamera()
    draw_floor_and_walls()

    if not is_game_over:
        draw_text(15, 770, f"Player Life Remaining: {player_lives}")
        draw_text(15, 740, f"Game Score: {player_score}")
        draw_text(15, 710, f"Bullets Missed: {bullets_missed} / 10")
    else:
        draw_text(15, 770, f"Game is Over. Your Score is {player_score}.")
        draw_text(15, 740, "Press 'R' to RESTART the Game.")

    draw_enemies()
    draw_bullets()
    draw_player()
    glutSwapBuffers()


def main():
    global quadric
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Bullet Game - 3D")
    glClearColor(0.0, 0.0, 0.0, 1.0)
    quadric = gluNewQuadric()
    reset_state()
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    glutMainLoop()
if __name__ == "__main__":
    main()
