import os
import pygame
import pygame.locals as pygame_locals
import time as t
import random


def add_line(screen, text, x, y):
    # used to print the status of the variables
    text = font.render(text, True, (255, 255, 255))
    text_rect = text.get_rect()
    text_rect.topleft = (x, y)
    screen.blit(text, text_rect)


lava_lev = str(input("lava mode [N/y]: "))
# lava_lev = lava_lev.lower

SURFACE_SZ = 680  # Desired physical surface size, in pixels.
map_length = 8800
endy = 200
if map_length < SURFACE_SZ:
    SURFX = map_length
else:
    SURFX = SURFACE_SZ

# from joy import Joystick

# joysticks = []
# try:
#     joysticks.append(Joystick(0))
# except:
#     print('unable to load controler')
WHITE = (255, 255, 255)

# Tick time
TICKS = 60
TICK_TIME = 1 / TICKS

pygame.init()
font = pygame.font.Font("freesansbold.ttf", 32)

# Global physics
AIR_RESISTANCE = 5
JUMP_ACC = 650
GRAVITY = 100000 / TICKS


# player characteristics
PLAYER_HEIGHT, PLAYER_WIDTH = 40, 20
PLAYER_COLOR = (0, 255, 255)  # (Red, Green, Blue) 0 - 255
MOVE_ACC = 400


class Platforms(list):
    """Collection of platforms"""

    def __init__(self, scroll=-100):
        self.scroll = scroll

    def update(self):
        """Update all platforms"""
        for item in self:
            item.scroll = self.scroll
            item.update()


class Wall(pygame.sprite.Sprite):
    """ Wall the player can run into. """

    def __init__(
        self,
        x,
        y,
        width,
        height,
        scroll,
        bouncy=False,
        color=(255, 255, 255),
        kills=False,
    ):
        """ Constructor for the wall that the player can run into. """
        # Call the parent's constructor
        super().__init__()

        self.scroll = scroll

        # Make a blue wall, of the size specified in the parameters
        self.image = pygame.Surface([width, height])
        self.image.fill(color)

        # Make our top-left corner the passed-in location.
        self._x = x
        self.rect = self.image.get_rect()
        self.rect.y = SURFACE_SZ - y
        self.rect.x = self._x - self.scroll
        self.bouncy = bouncy

    def update(self):
        """Update the position of the platform"""
        self.rect.x = self._x - self.scroll


class Player(pygame.sprite.Sprite):
    def __init__(
        self,
        name="Alex",
        xpos=0,
        ypos=None,
        width=PLAYER_WIDTH,
        height=PLAYER_HEIGHT,
        platforms=[],
        scroll=0,
        scrollvel=0,
    ):
        super().__init__()

        # init image
        self._width = width
        self._height = height

        self.scroll = scroll
        self.scrollvel = scrollvel

        self._lowest_y = SURFACE_SZ - self._height

        self.image = pygame.Surface([self._width, self._height])
        this_dir = os.path.dirname(__file__)
        image_file = os.path.join(this_dir, "player.png")
        image = pygame.image.load(image_file).convert()
        self.image = pygame.transform.scale(image, (self._width, self._height))

        # self.image.convert_alpha()

        # self.image.fill((0, 200, 200))
        self.rect = self.image.get_rect()

        if ypos is None:
            ypos = self._lowest_y
        self.ypos = ypos

        self.name = name
        self.mass = 1

        self._xvel = 0
        self._yvel = 0

        self._check_bounds()

        self._xacc = 0
        self._yacc = 0

        self._platforms = platforms
        self._grounded = True
        self.alive = True
        self.gravity = GRAVITY

    @property
    def xpos(self):
        return self.rect.x

    @xpos.setter
    def xpos(self, x):
        self.rect.x = x

    @property
    def ypos(self):
        return self.rect.y

    @ypos.setter
    def ypos(self, y):
        self.rect.y = y

    @property
    def platforms(self):
        return self._platforms

    def update(self):
        """Update acceleration, velocity, position"""

        self.xpos += self._xvel * TICK_TIME + 0.5 * self._xacc * TICK_TIME ** 2
        self.scroll += self.scrollvel * TICK_TIME + 0.5 * 0 * TICK_TIME ** 2
        self.ypos += self._yvel * TICK_TIME + 0.5 * self._yacc * TICK_TIME ** 2

        # only change velocity if no colision
        # self._xvel -= self._xacc*TICK_TIME
        # self.scrollvel -= self._xacc*TICK_TIME

        self._yvel += self._yacc * TICK_TIME

        self.scrollvel = self._xvel

        self._grounded = self._check_colision()
        self._check_bounds()
        self._floor_velocity()

        # reset forces on character
        self._yacc = self.gravity
        self._xacc = 0

        # account for "air resistance"
        self._xvel -= self._xvel * AIR_RESISTANCE * TICK_TIME
        self.scrollvel -= self.scrollvel * TICK_TIME
        # self._yvel -= self._yvel * AIR_RESISTANCE * TICK_TIME

    def _check_colision(self):
        block_hit_list = pygame.sprite.spritecollide(self, self.platforms, False)

        bottom = False
        for block in block_hit_list:

            tl = block.rect.collidepoint(self.rect.topleft)
            tm = block.rect.collidepoint(self.rect.midtop)
            tr = block.rect.collidepoint(self.rect.topright)

            bl = block.rect.collidepoint(self.rect.bottomleft)
            bm = block.rect.collidepoint(self.rect.midbottom)
            br = block.rect.collidepoint(self.rect.bottomright)
            if any((bl, bm, br)):
                bottom = True
            if any((tl, tm, tr)):
                if block.kill == True:
                    self.alive = False

            rm = block.rect.collidepoint(self.rect.midright)
            lm = block.rect.collidepoint(self.rect.midleft)

            # any mid intersection means that side is always in colision
            if rm:
                self.rect.right = block.rect.left
                self._xvel = 0
                self.scrollvel = 0
            elif lm:
                self.rect.left = block.rect.right
                self._xvel = 0
                self.scrollvel = 0
            elif tm:
                self.rect.top = block.rect.bottom
                self._yvel = 0
            elif bm:
                self.rect.bottom = block.rect.top
                self.set_yvel_bounce(block)

            # must be a corner, check which one
            elif br:
                if self._yvel > 0 and self._xvel > 0:
                    # double colision, determine which is greater
                    vert_dist = abs(self.rect.bottom - block.rect.top)
                    horz_dist = abs(self.rect.right - block.rect.left)
                    if vert_dist < horz_dist:
                        self.rect.bottom = block.rect.top
                        self.set_yvel_bounce(block)
                    else:
                        self.rect.right = block.rect.left
                        self._xvel *= -1
                        self.scrollvel *= -1
                elif self._yvel > 0:
                    self.rect.bottom = block.rect.top
                    self._yvel = 0
                elif self._xvel > 0:
                    self.rect.right = block.rect.left
                    self._xvel *= -1
                    self.scrollvel *= -1

            elif bl:
                if self._yvel > 0 and self._xvel < 0:
                    # double colision, determine which is greater
                    vert_dist = abs(self.rect.bottom - block.rect.top)
                    horz_dist = abs(self.rect.left - block.rect.right)
                    if vert_dist < horz_dist:
                        self.rect.bottom = block.rect.top
                    else:
                        self.rect.left = block.rect.right
                elif self._yvel > 0:
                    self.rect.bottom = block.rect.top
                    self.set_yvel_bounce(block)
                elif self._xvel < 0:
                    self.rect.left = block.rect.right
                    self._xvel *= -1
                    self.scrollvel *= -1

            elif tr:
                if self._yvel < 0 and self._xvel > 0:
                    # double colision, determine which is greater
                    vert_dist = abs(self.rect.top - block.rect.bottom)
                    horz_dist = abs(self.rect.right - block.rect.left)
                    if vert_dist < horz_dist:
                        self.rect.top = block.rect.bottom
                        self._yvel = 0
                    else:
                        self.rect.right = block.rect.left
                        self._xvel *= -1
                        self.scrollvel *= -1
                elif self._yvel > 0:
                    self.rect.top = block.rect.bottom
                    self._yvel = 0
                elif self._xvel < 0:
                    self.rect.right = block.rect.left
                    self._xvel *= -1
                    self.scrollvel *= -1

            elif tl:
                if self._yvel < 0 and self._xvel < 0:
                    # double colision, determine which is greater
                    vert_dist = abs(self.rect.top - block.rect.bottom)
                    horz_dist = abs(self.rect.left - block.rect.right)
                    if vert_dist < horz_dist:
                        self.rect.top = block.rect.bottom
                        self._yvel = 0
                    else:
                        self.rect.left = block.rect.right
                        self._xvel *= -1
                        self.scrollvel *= -1
                elif self._yvel < 0:
                    self.rect.top = block.rect.bottom
                    self._yvel = 0
                elif self._xvel < 0:
                    self.rect.left = block.rect.right
                    self._xvel *= -1
                    self.scrollvel *= -1

        # any bottom collision
        return bottom

    def set_yvel_bounce(self, block):
        if block.bouncy:
            self._yvel = -block.bouncy
            # self.gravity = -GRAVITY
        else:
            self._yvel = 0

    def _check_bounds(self):
        # do not allow to fall through map
        if self.xpos < 0:
            self.xpos = 0
            self._xvel = 0
        if self.scroll < 0:
            self.scroll = 0
            self.scrollvel = 0

        if self.ypos > self._lowest_y:
            self.alive = False
        # elif self.ypos < -200:
        #     self.alive = False
        # self.ypos = self._lowest_y
        # self._yvel = 0

    def _floor_velocity(self):
        if abs(self._xvel) < 10:
            self._xvel = 0
        if abs(self.scrollvel) < 10:
            self.scrollvel = 0
        if abs(self._yvel) < 10:
            self._yvel = 0

    def jump(self):
        """Implement jump, but only if on the 'ground' (i.e. xpos == 0) """
        if self._grounded:
            self._yvel = -JUMP_ACC

    def left(self):
        """Left movement acceleration"""
        # if self._grounded:
        self._xvel = -MOVE_ACC
        self.scrollvel = -MOVE_ACC

    def right(self):
        """Right movement acceleration"""
        # if self._grounded:
        self._xvel = MOVE_ACC
        self.scrollvel = MOVE_ACC

    def __repr__(self):
        txt = [f"Player {self.name}"]
        txt.append(f"Position     ({self.xpos}, {self.ypos})")
        txt.append(f"Velocity     ({self._xvel}, {self._yvel})")
        txt.append(f"Acceleration ({self._xacc}, {self._yacc})")
        return "\n".join(txt)


clock = pygame.time.Clock()
screen = pygame.display.set_mode((0, 0))

# unn = True
# while unn:
#     screen.fill((120, 0, 170))# make entire screen black
#     add_line(screen, 'Kaszynski studios',
#                      550, 250)
#     pygame.event.poll()
#     pygame.display.update()
#     t.sleep(2)
#     clock.tick(TICKS)
#     unn = False


def run():
    """ Set up the game and run the main game loop """
    pygame.init()  # Prepare the pygame module for use
    game_font = pygame.font.SysFont(pygame.font.get_default_font(), 80)
    pygame.key.set_repeat(1, 10)

    won = False

    scroll = 0
    wallheight = 20
    platforms = Platforms()
    platforms.append(Wall(0, 100, 60, wallheight, scroll))
    platforms.append(Wall(100, 200, 20, 120, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(0, 300, 100, 20, scroll))
    platforms.append(Wall(300, 440, 100, 20, scroll))
    platforms.append(Wall(600, 240, 60, 20, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(300, 300, 100, 20, scroll))
    platforms.append(Wall(400, 500, 120, wallheight, scroll))
    platforms.append(Wall(500, 600, 60, wallheight, scroll))
    platforms.append(Wall(660, 620, 540, 300, scroll))
    platforms.append(Wall(640, 280, 600, 300, scroll))
    platforms.append(Wall(2000, 100, 60, wallheight, scroll))
    platforms.append(Wall(1700, 100, 20, 120, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(1300, 440, 100, 20, scroll))
    platforms.append(Wall(1600, 240, 60, 20, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(1300, 300, 100, 20, scroll))
    platforms.append(Wall(1400, 500, 120, wallheight, scroll))
    platforms.append(Wall(2400, 400, 60, wallheight, scroll))
    platforms.append(Wall(2200, 400, 20, 820, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(1300, 440, 100, 20, scroll))
    platforms.append(Wall(1800, 140, 600, 20, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(3600, 100, 500, 20, scroll))
    platforms.append(Wall(2450, 500, 1020, 20, scroll))
    platforms.append(Wall(2700, 300, 60, wallheight, scroll))
    platforms.append(Wall(2900, 200, 1000, 20, scroll))
    platforms.append(Wall(3550, 400, 520, 100, scroll))
    platforms.append(Wall(4250, 180, 120, 20, scroll))
    platforms.append(Wall(4500, 300, 160, wallheight, scroll))
    platforms.append(Wall(4800, 400, 160, wallheight, scroll))
    platforms.append(Wall(5000, 340, 160, wallheight, scroll))
    platforms.append(Wall(5080, 100, 60, wallheight, scroll))
    platforms.append(Wall(5100, 200, 20, 120, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(5000, 300, 100, 20, scroll))
    platforms.append(Wall(5300, 440, 100, 20, scroll))
    platforms.append(Wall(6500, 240, 60, 20, scroll, bouncy=1000, color=(0, 200, 0)))
    platforms.append(Wall(5300, 300, 100, 20, scroll))
    platforms.append(Wall(4500, 500, 120, wallheight, scroll))
    platforms.append(Wall(5500, 600, 60, wallheight, scroll))
    platforms.append(Wall(5660, 620, 540, 300, scroll))
    platforms.append(Wall(5640, 280, 600, 300, scroll))
    platforms.append(Wall(7300, 300, 100, 20, scroll))
    platforms.append(Wall(6500, 500, 120, wallheight, scroll))
    platforms.append(Wall(7500, 600, 60, wallheight, scroll))
    platforms.append(Wall(7660, 620, 540, 300, scroll))
    platforms.append(Wall(7640, 280, 600, 300, scroll))
    platforms.append(Wall(7500, 600, 60, wallheight, scroll))
    platforms.append(Wall(6660, 620, 540, 20, scroll))
    platforms.append(Wall(7640, 280, 600, 20, scroll))
    platforms.append(Wall(7500, 500, 60, wallheight, scroll))
    platforms.append(Wall(6260, 620, 54, 20, scroll))
    platforms.append(Wall(7240, 380, 600, 20, scroll))

    # make the end point
    platforms.append(Wall(map_length - 200, endy, 360, wallheight, scroll))
    platforms.append(Wall(map_length + 40, endy + 40, 3, 40, scroll))
    platforms.append(
        Wall(map_length + 43, endy + 40, 20, 20, scroll, color=(200, 10, 0))
    )

    # platforms.append(Wall(0, 100, 60, wallheight))
    # platforms.append(Wall(100, 200, 120, 20, bouncy=0, color=(255, 255, 255)))
    # platforms.append(Wall(200, 300, 120, 20, bouncy=1000, color=(0, 200, 0)))
    # platforms.append(Wall(300, 500, 120, 20))
    # platforms.append(Wall(300, 600, 20, 200))

    # Create surface of (width, height), and its window.
    screen = pygame.display.set_mode((1200, 680))
    # initialize player
    player = Player(
        "Alex",
        platforms=platforms,
        xpos=0.5 * SURFACE_SZ,
        ypos=(SURFACE_SZ - 100 - PLAYER_HEIGHT),
    )

    # list of 'sprites.'
    # The list is managed by a class called 'Group.'
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    all_sprites.add(platforms)

    clock = pygame.time.Clock()

    game_running = True
    total_ticks = 0
    time = 0
    while game_running:

        # if player.xpos > 0.5*SURFACE_SZ:
        # player.scroll = player.xpos - 0.5*SURFACE_SZ
        time += 1

        for event in pygame.event.get():
            if event.type == pygame_locals.QUIT:
                print("quitting...")
                game_running = False
            # joysticks[0]._process_event(event)
            # joysticks[1]._process_event(event)

            keys = pygame.key.get_pressed()
            if keys[pygame_locals.K_w]:  # or joysticks[0].button_a:
                player.jump()
            if keys[pygame_locals.K_a]:  # or joysticks[0]._lb:
                player.left()
            if keys[pygame_locals.K_d]:  # or joysticks[0]._rb:
                player.right()
            if keys[pygame_locals.K_q]:  # or joysticks[0]._quit:
                game_running = False

        text = font.render("points: {player.scroll}", True, "white")
        text_rect = text.get_rect()
        text_rect.topleft = (0, 0)
        screen.blit(text, text_rect)

        # We draw everything from scratch on each frame.
        # So first fill everything with the background color
        screen.fill((0, 200, 200))

        # if won == False:
        add_line(screen, f"distance: {player.scroll / 20 :.0f} meters", 0, 0)

        if player.scroll > map_length:
            # if player.xpos > SURFX:
            won = True

        if lava_lev == "y":
            player._lowest_y -= 0.1
        if lava_lev == "Y":
            player._lowest_y -= 0.1

        if platforms.scroll < 0:
            platforms.scroll = 0

        # update the position of the platforms
        if player.scroll > 0.5 * SURFACE_SZ:
            if player.xpos < map_length - 0.5 * SURFACE_SZ:
                platforms.scroll = player.scroll - 0.5 * SURFACE_SZ
                player.xpos = 0.5 * SURFACE_SZ

        platforms.update()

        if platforms.scroll < 0:
            platforms.scroll = 0

        if won == True:
            text_surface = game_font.render("You won!", True, (255, 255, 255))
            player.alive = False
        if not player.alive:
            if won != True:
                text_surface = game_font.render("You lost.", True, (255, 255, 255))
                t.sleep(0.5)
                player.xpos = 0
                player.scroll = 0
                platforms.scroll = 0
                player.alive = True
                player.ypos = SURFACE_SZ - 100 - PLAYER_HEIGHT
                player._lowest_y = SURFACE_SZ - PLAYER_HEIGHT

            text_rect = text_surface.get_rect()
            text_rect.left = 0.3 * SURFX
            text_rect.top = 0.4 * SURFACE_SZ
            screen.blit(text_surface, text_rect)
            # if won == True:
            #     if fir == True:
            #         playsound('fireworks.mp3')
            #     fir = False
        else:
            all_sprites.update()
            all_sprites.draw(screen)
        if player.alive == True:
            if won == False:
                lava = pygame.Rect(0, player._lowest_y + PLAYER_HEIGHT, 20000, 20000)
                pygame.draw.rect(screen, (200, 100, 0), lava)

        if player.alive == False:
            if won == False:
                black = pygame.Rect(0, 0, 2000, 2000)
                pygame.draw.rect(screen, (0, 0, 0), black)

        # Now the surface is ready, tell pygame to display it!
        pygame.display.update()

        # Limit to TICKS frames per second
        clock.tick(TICKS)
        total_ticks += 1

    pygame.quit()  # Once we leave the loop, close the window.


if __name__ == "__main__":
    run()
