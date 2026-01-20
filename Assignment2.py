from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time

WIDTH, HEIGHT = 480, 700

catcher = [12, 102, 22, 92] # x1, x2, width, height
move_step = 7
is_playing = True # a flag of game active 
game_over = False
cheat_mode = False
score = 0
prev_time = time.time() # positioning diamonds+random nos


def new_diamond(): # Diamond init
    x = random.randint(15, 460) # from 15 tp 460 
    color = (
        random.uniform(0.6, 1.0), # lighter tone, intensity
        random.uniform(0.6, 1.0), # from 0.6 to 1 any val
        random.uniform(0.6, 1.0)
    )
    return [x, x + 9, x - 9, 652, 639, 626, color] # x-center, right ,left ,y-top ,mid ,bottom
diamond = new_diamond()


def setup_projection():
    glViewport(0, 0, WIDTH, HEIGHT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, 0, 1)
    glMatrixMode(GL_MODELVIEW)


def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()
    draw()
    glutSwapBuffers()


def to_original(x, y, zone):  # zone conversiuon , for mid line algo
    if zone == 0: return x, y
    if zone == 1: return y, x
    if zone == 2: return -y, x
    if zone == 3: return -x, y
    if zone == 4: return -x, -y
    if zone == 5: return -y, -x
    if zone == 6: return y, -x
    return x, -y # last zone 7 

def detect_zone(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1 # difference 

    if abs(dx) >= abs(dy): # detecting zone 
        if dx >= 0 and dy >= 0: return x1, y1, x2, y2, 0
        if dx < 0 and dy >= 0: return -x1, y1, -x2, y2, 3
        if dx < 0 and dy < 0: return -x1, -y1, -x2, -y2, 4
        return x1, -y1, x2, -y2, 7
    else:
        if dx >= 0 and dy >= 0: return y1, x1, y2, x2, 1
        if dx < 0 and dy >= 0: return y1, -x1, y2, -x2, 2
        if dx < 0 and dy < 0: return -y1, -x1, -y2, -x2, 5
        return -y1, x1, -y2, x2, 6


def draw_point(x, y, color):  
    glColor3f(*color)
    glPointSize(2)
    glBegin(GL_POINTS)
    glVertex2f(x, y)
    glEnd()

def midpoint(x1, y1, x2, y2, color):
    x1, y1, x2, y2, zone = detect_zone(x1, y1, x2, y2)

    if x1 > x2:# line always moves from left to right
        x1, x2 = x2, x1
        y1, y2 = y2, y1 # y corresonds to x 

    dx, dy = x2 - x1, y2 - y1
    d = 2 * dy - dx
    incE = 2 * dy
    incNE = 2 * (dy - dx)

    x, y = x1, y1 # assigning starting points 

    while x <= x2:  #line is drawn from x1 to x2 (left to right).
        px, py = to_original(x, y, zone) # Zone 0 to the original zone
        draw_point(px, py, color)
        if d > 0: #next point is closer to the diagonal
            y += 1
            d += incNE # increase the value of d for next itrtn
        else: # horizontal movement , just east 
            d += incE
        x += 1


def draw(): # drawing objs
    global catcher, diamond
    #catcher
    c = (1, 0, 0) if game_over else (1, 1, 1)   # red if game over else white
    a, b, cx, d = catcher
    midpoint(a, 20, b, 20, c)# top edge
    midpoint(cx, 6, d, 6, c)# bottom edge
    midpoint(cx, 6, a, 20, c)# botthom left to top
    midpoint(b, 20, d, 6, c)# bottom right to top

    teal = (0, 0.6, 0.6)  #restart
    midpoint(25, 670, 55, 670, teal) #hori
    midpoint(25, 670, 42, 688, teal) # diag
    midpoint(25, 670, 42, 652, teal)#diag

    amber = (1, 0.75, 0) #pause , play 
    if is_playing:
        midpoint(238, 688, 238, 652, amber)
        midpoint(255, 688, 255, 652, amber)
    else:
        midpoint(238, 688, 238, 652, amber) #vertical line
        midpoint(238, 688, 270, 670, amber) #left diag
        midpoint(238, 652, 270, 670, amber)#right diag

    red = (1, 0, 0) # quit 
    midpoint(440, 652, 470, 688, red)
    midpoint(440, 688, 470, 652, red)

    if not game_over: # diamond
        x1, x2, x3, y1, y2, y3, col = diamond
        #4 lines are drawn of diamond 
        midpoint(x1, y1, x2, y2, col)
        midpoint(x1, y1, x3, y2, col)
        midpoint(x2, y2, x1, y3, col)
        midpoint(x3, y2, x1, y3, col)


def animate():
    global diamond, score, prev_time, game_over
    now = time.time()
    dt = now - prev_time
    prev_time = now
    speed = (140 + score * 45) * dt
    #bounding box
    catcher_box = {'x': catcher[0], 'y': 6, 'w': 98, 'h': 14} # y=6 bottom of screen 
    diamond_box = {'x': diamond[1], 'y': diamond[5], 'w': 18, 'h': 24}

    if is_playing and not game_over:
        # moving diamonds downward, vertical move so y only 
        if diamond[5] >= 20: # dia[5]= bottom, 20 threshold
            # >= if still not reach 
            diamond[3:6] = [i - speed for i in diamond[3:6]]

        elif collide(catcher_box, diamond_box):
            score += 1
            print(f"Score: {score}")
            diamond = new_diamond()
        else:
            print(f"Game Over! Score: {score}")
            game_over = True
            score = 0 # the score is reset to 0 again 

        if cheat_mode:
            center = (catcher[0] + catcher[1]) / 2 # calculates hori center
            if center < diamond[1] - 3: # catchers center is left of diamond pos
                move_catcher(6) # move left 
            elif center > diamond[1] + 3:# center is right to diamonds pos
                move_catcher(-6) # move right 
    glutPostRedisplay()

def move_catcher(step):
    global catcher
    for i in range(4):  #catcher = [x1, x2, width, height]
        catcher[i] += step # already defiened =7
    left = min(catcher[0], catcher[2]) #epresents the leftmost position of the catcher
    right = max(catcher[1], catcher[3]) #which represents the rightmost position of the catcher
    if left < 0:
        shift = -left
        for i in range(4):
            catcher[i] += shift # back on the screen from left 
    elif right > WIDTH:
        shift = WIDTH - right
        for i in range(4):
            catcher[i] += shift # back on screen from right 

def collide(a, b): ## if conditions met then true caught
    return (a['x'] < b['x'] + b['w'] and
            a['x'] + a['w'] > b['x'] and
            a['y'] < b['y'] + b['h'] and
            a['y'] + a['h'] > b['y'])

def keyboard(key, x, y):
    global cheat_mode
    if key == b'c':
        cheat_mode = not cheat_mode
        print("Cheat Mode:", cheat_mode)

def special(key, x, y):
    if not game_over and is_playing:
        if key == GLUT_KEY_RIGHT and catcher[1] < WIDTH: # right move 
            for i in range(4): catcher[i] += move_step
        elif key == GLUT_KEY_LEFT and catcher[0] > 0: # left move 
            for i in range(4): catcher[i] -= move_step

def mouse(btn, state, x, y): # btn mouse right or left click
    #state= pressed (GLUT_DOWN) or released (GLUT_UP).
    #x,y= mouse click cordinates 
    global is_playing, game_over, diamond, cheat_mode, score, prev_time
    mx, my = x, HEIGHT - y
    if btn == GLUT_LEFT_BUTTON and state == GLUT_DOWN: # left and pressed 
        if 440 <= mx <= 470 and 652 <= my <= 688:
            print("Goodbye")
            glutLeaveMainLoop()
        elif 230 <= mx <= 270:
            is_playing = not is_playing
        elif 25 <= mx <= 55:
            game_over = False 
            diamond = new_diamond()  # new diamond as game over 
            is_playing = True  # restart er porei auto start
            cheat_mode = False  # reset cheat
            score = 0  # reset score 
            prev_time = time.time() 
            print("Starting Over") 

def main():
    glutInit()
    glutInitDisplayMode(GLUT_RGB)
    glutInitWindowSize(WIDTH, HEIGHT)
    glutCreateWindow(b"Catch The Diamonds!")
    setup_projection()
    glutDisplayFunc(display)
    glutIdleFunc(animate)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special)
    glutMouseFunc(mouse)
    glutMainLoop()

if __name__ == "__main__":
    main()
