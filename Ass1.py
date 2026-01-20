

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import random

WIN_WIDTH = 650
WIN_HEIGHT = 700

rain_drops = []
rain_wind = 0.0
wind_step = 0.01
sky_brightness = 0.0
def init_rain():
    global rain_drops
    rain_drops = [[random.randint(0, WIN_WIDTH), random.randint(0, WIN_HEIGHT)] for _ in range(123)]
def draw_house():

    glBegin(GL_TRIANGLES)
    glColor3f(0.9, 0.8, 0.3)
    glVertex2d(250, 250); glVertex2d(450, 250); glVertex2d(450, 400)
    glVertex2d(250, 250); glVertex2d(450, 400); glVertex2d(250, 400)
    glEnd()


    glBegin(GL_TRIANGLES)
    glColor3f(0.8, 0.1, 0.1)
    glVertex2d(250, 400); glVertex2d(450, 400); glVertex2d(350, 520)
    glEnd()


    glBegin(GL_TRIANGLES)
    glColor3f(0.4, 0.2, 0.0)
    glVertex2d(330, 250); glVertex2d(370, 250); glVertex2d(370, 320)
    glVertex2d(330, 250); glVertex2d(370, 320); glVertex2d(330, 320)
    glEnd()


    glColor3f(0.1, 0.5, 0.8)
    glBegin(GL_TRIANGLES)
    glVertex2d(275, 310); glVertex2d(315, 310); glVertex2d(315, 350)
    glVertex2d(275, 310); glVertex2d(315, 350); glVertex2d(275, 350)
    glEnd()


    glBegin(GL_TRIANGLES)
    glVertex2d(385, 310); glVertex2d(425, 310); glVertex2d(425, 350)
    glVertex2d(385, 310); glVertex2d(425, 350); glVertex2d(385, 350)
    glEnd()


    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_LINES)

    glVertex2d(275, 330); glVertex2d(315, 330)
    glVertex2d(295, 310); glVertex2d(295, 350)

    glVertex2d(385, 330); glVertex2d(425, 330)
    glVertex2d(405, 310); glVertex2d(405, 350)
    glEnd()

def draw_rain():
    global rain_drops, rain_wind
    glColor3f(0.6, 0.9, 1.0)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    new_positions = []
    for x, y in rain_drops:
        glVertex2f(x, y)
        glVertex2f(x + rain_wind * 3, y - 30)
        ny = y - 0.7
        nx = x + rain_wind
        if ny < 0:
            ny = WIN_HEIGHT
            nx = random.randint(0, WIN_WIDTH)
        new_positions.append([nx, ny])
    glEnd()
    rain_drops[:] = new_positions

def display():
    global sky_brightness
    glClearColor(0.0, 0.0, sky_brightness, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    draw_house()
    draw_rain()
    glutSwapBuffers()

def special_key_listener(key, x, y):
    global rain_wind, wind_step
    if key == GLUT_KEY_LEFT:
        rain_wind -= wind_step
    elif key == GLUT_KEY_RIGHT:
        rain_wind += wind_step
    glutPostRedisplay()

def normal_key_listener(key, x, y):
    global sky_brightness
    if key == b'd':
        sky_brightness = min(1.0, sky_brightness + 0.05)
        print("Transitioning to day:", round(sky_brightness, 2))
    elif key == b'n':
        sky_brightness = max(0.0, sky_brightness - 0.05)
        print("Transitioning to night:", round(sky_brightness, 2))
    glutPostRedisplay()

def main():
    glutInit()
    glutInitDisplayMode( GLUT_RGBA)
    glutInitWindowSize(WIN_WIDTH, WIN_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"TASK1 - Functional Rain Version")
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, WIN_WIDTH, 0, WIN_HEIGHT, -1, 1)
    init_rain()
    glutDisplayFunc(display)
    glutSpecialFunc(special_key_listener)
    glutKeyboardFunc(normal_key_listener)
    glutIdleFunc(display)
    glutMainLoop()
main()


from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time

WIN_WIDTH, WIN_HEIGHT = 600, 600

points = []
speed = .9
frozen = False
blinking = False
blink_interval = 0.55
blink_timer = 0.0
last_update_time = time.time()
blink_visible = True

def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, WIN_WIDTH, 0, WIN_HEIGHT, -1, 1)

def mouse_listener(button, state, x, y):
    global blinking, points, frozen
    if state != GLUT_DOWN:
        return
    y = WIN_HEIGHT - y
    if button == GLUT_RIGHT_BUTTON:
        if not frozen:
            create_point(x, y)
    elif button == GLUT_LEFT_BUTTON:
        if not frozen:
            blinking = not blinking

def create_point(x, y):
    dx = random.choice([-1, 1])
    dy = random.choice([-1, 1])
    r, g, b = random.random(), random.random(), random.random()
    points.append([x, y, dx, dy, r, g, b])

def keyboard_listener(key, x, y):
    global frozen, last_update_time
    if key == b' ':
        frozen = not frozen
        last_update_time = time.time()

def special_key_listener(key, x, y):
    global speed, frozen
    if frozen:
        return
    if key == GLUT_KEY_UP:
        speed += 0.2
    elif key == GLUT_KEY_DOWN:
        new_speed = speed - 0.2
        if new_speed >= 0.2:
            speed = new_speed

def update_points():
    global points
    updated = []
    for p in points:
        x, y, dx, dy, r, g, b = p
        x += dx * speed
        y += dy * speed
        if x <= 0 or x >= WIN_WIDTH:
            dx = -dx
            x = max(0, min(x, WIN_WIDTH))
        if y <= 0 or y >= WIN_HEIGHT:
            dy = -dy
            y = max(0, min(y, WIN_HEIGHT))

        updated.append([x, y, dx, dy, r, g, b])

    points[:] = updated

def draw_points():
    global blink_timer, last_update_time, blink_visible
    glPointSize(8)
    glBegin(GL_POINTS)
    current_time = time.time()
    delta = current_time - last_update_time
    if blinking and not frozen:
        blink_timer += delta
        if blink_timer >= blink_interval:
            blink_visible = not blink_visible
            blink_timer = 0.0
    last_update_time = current_time

    for x, y, dx, dy, r, g, b in points:
        if blinking and not blink_visible:
            glColor3f(0.0, 0.0, 0.0)
        else:
            glColor3f(r, g, b)
        glVertex2d(x, y)
    glEnd()

def animate():
    if not frozen:
        update_points()
    glutPostRedisplay()

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_LINE_LOOP)
    glVertex2d(0, 0)
    glVertex2d(WIN_WIDTH, 0)
    glVertex2d(WIN_WIDTH, WIN_HEIGHT)
    glVertex2d(0, WIN_HEIGHT)
    glEnd()
    draw_points()
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode( GLUT_RGB)
    glutInitWindowSize(WIN_WIDTH, WIN_HEIGHT)
    glutCreateWindow(b"Task 2 ")
    init()
    glutDisplayFunc(display)
    glutIdleFunc(animate)
    glutMouseFunc(mouse_listener)
    glutKeyboardFunc(keyboard_listener)
    glutSpecialFunc(special_key_listener)
    glutMainLoop()
main()
