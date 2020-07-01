import pygame
import os
import numpy as np
import pygame.freetype

class game_display:

    def __init__(self, engine, disp_scale=1.0, mute=True):
        self.mute = mute

        self.color_dark = (30, 30, 30)
        self.color_green = (0, 200, 0)
        self.color_player_1 = (0, 255, 255)
        self.color_player_2 = (255, 64, 255)
        self.color_parcel = (255, 255, 0)

        self.text_font_size = int(max(22*disp_scale, 14))
        self.num_font_size = int(max(11*disp_scale, 7))
        self.block_size = int(48*disp_scale)
        self.header_size = int(3.5*self.text_font_size)

        pygame.mixer.pre_init(44100, -16, 2, 65536)
        pygame.init()
        pygame.mixer.init()
        pygame.font.init()

        sound_folder = "res/sounds/sci_fi_tone/"
        self.sounds = [x for x in os.listdir(sound_folder) if x[-4:]==".wav"]
        self.sounds = [pygame.mixer.Sound(sound_folder+s) for s in self.sounds]

        clock = pygame.time.Clock()
        clock.tick(60)

        self.screen = pygame.display.set_mode((engine._map.shape[1]*self.block_size+1,
                                               engine._map.shape[0]*self.block_size+self.header_size+1))
        self.text_font = pygame.freetype.SysFont('Comic Sans MS', self.text_font_size)
        self.num_font = pygame.freetype.SysFont('Comic Sans MS', self.num_font_size)

    def update(self, engine, moves_str=[], isPlaySounds=False):
        """
        return: True  -> The display is on.
                False -> The display is off, the program should shut down.
        """
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False

        if not self.mute and isPlaySounds:
            self.sounds[np.random.randint(len(self.sounds))].play()

        # 清屏
        self.screen.fill(self.color_dark)

        self._show_players(engine)
        self._show_parcels(engine)

        self._show_texts(engine, moves_str)
        self._show_blocks(engine)
        self._show_walls(engine)
        self._show_spawns(engine)
        self._show_shelves(engine)

        pygame.display.update()
        return True

    def _show_texts(self, engine, moves_str):
        textsurface, rect = self.text_font.render('YOUR MOVES: '+" ".join(moves_str), self.color_green)
        self.screen.blit(textsurface,(2,10))
        textsurface, rect = self.text_font.render('SCORE: '+str(engine.score), self.color_green)
        self.screen.blit(textsurface,(2,10+self.text_font_size+10))
        textsurface, rect = self.text_font.render('STEP: '+str(engine.steps), self.color_green)
        self.screen.blit(textsurface,(2+engine._map.shape[1]*self.block_size/2, 10+self.text_font_size+10))

    def _show_blocks(self, engine):
        pygame.draw.lines(self.screen, self.color_green, False, [(0,0),
                          (engine._map.shape[1]*self.block_size,0)], 1)
        pygame.draw.lines(self.screen, self.color_green, False, [(0,0),
                          (0,engine._map.shape[0]*self.block_size+self.header_size)], 1)
        pygame.draw.lines(self.screen, self.color_green, False, [(engine._map.shape[1]*self.block_size,0),
                          (engine._map.shape[1]*self.block_size,engine._map.shape[0]*self.block_size+self.header_size)], 1)

        for i in range(engine._map.shape[0]+1):
            y = i*self.block_size+self.header_size
            pygame.draw.lines(self.screen, self.color_green, False, [(0,y),
                              (engine._map.shape[1]*self.block_size,y)], 1)
        for i in range(engine._map.shape[1]+1):
            x = i*self.block_size
            pygame.draw.lines(self.screen, self.color_green, False, [(x,self.header_size),
                              (x,engine._map.shape[0]*self.block_size+self.header_size)], 1)

    def _show_walls(self, engine):
        for i in range(engine._map.shape[0]):
            for j in range(engine._map.shape[1]):
                if engine._map[i,j,0]==-1:
                    x = j * self.block_size + int(self.block_size/2)
                    y = i * self.block_size + int(self.block_size/2) + self.header_size
                    size = self.block_size
                    s = pygame.Surface((size,size))
                    s.fill(self.color_dark)
                    s.set_colorkey(self.color_dark)
                    pygame.draw.rect(s, self.color_green, (0, 0, size, size), 0)
                    self.screen.blit(s, (x-int(size/2), y-int(size/2)))

    def _show_spawns(self, engine):
        for i in range(engine._map.shape[0]):
            for j in range(engine._map.shape[1]):
                if engine._map[i,j,0]==-2:
                    x = j * self.block_size + int(self.block_size/2)
                    y = i * self.block_size + int(self.block_size/2) + self.header_size
                    size = int(self.block_size*0.8)
                    s = pygame.Surface((size,size))
                    s.fill(self.color_dark)
                    s.set_colorkey(self.color_dark)
                    pygame.draw.rect(s, self.color_green, (0, 0, size, size), 1)
                    self.screen.blit(s, (x-int(size/2), y-int(size/2)))

    def _show_shelves(self, engine):
        for i in range(engine._map.shape[0]):
            for j in range(engine._map.shape[1]):
                if engine._map[i,j,0]>0:
                    x = j * self.block_size + int(self.block_size/2)
                    y = i * self.block_size + int(self.block_size/2) + self.header_size
                    size = int(self.block_size*0.8)
                    s = pygame.Surface((size,size))
                    s.fill(self.color_dark)
                    s.set_colorkey(self.color_dark)
                    pygame.draw.rect(s, self.color_green, (0, 0, size, size), 1)
                    self.screen.blit(s, (x-int(size/2), y-int(size/2)))

                    textsurface, rect = self.num_font.render(str(int(engine._map[i,j,0])), self.color_green)
                    self.screen.blit(textsurface,(x-int(size/2)+2, y-int(size/2)+2))

    def _show_players(self, engine):
        for i in range(engine._map.shape[0]):
            for j in range(engine._map.shape[1]):
                if engine._map[i,j,2]>0:
                    x = j * self.block_size + int(self.block_size/2)
                    y = i * self.block_size + int(self.block_size/2) + self.header_size
                    size = int(self.block_size*0.8)
                    s = pygame.Surface((size,size))
                    s.fill(self.color_dark)
                    s.set_colorkey(self.color_dark)
                    if engine.players[int(engine._map[i,j,2])-1][2]>0:
                        pygame.draw.rect(s, self.color_player_2, (0, 0, size, size), 0)
                    else:
                        pygame.draw.rect(s, self.color_player_1, (0, 0, size, size), 0)
                    self.screen.blit(s, (x-int(size/2), y-int(size/2)))

                    num_str = str(int(engine._map[i,j,2]))
                    textsurface, rect = self.num_font.render(num_str, self.color_dark)
                    font_size = self.num_font.get_metrics(num_str)
                    font_width = int(np.sum([font_size[i][1]-font_size[i][0]-1 for i in range(len(font_size))]))
                    font_height = font_size[0][3]-font_size[0][2]
                    self.screen.blit(textsurface, (x+int(size/2) - font_width - 2,
                                                   y+int(size/2) - font_height - 2))

    def _show_parcels(self, engine):
        for i in range(engine._map.shape[0]):
            for j in range(engine._map.shape[1]):
                if engine._map[i,j,1]>0:
                    x = j * self.block_size + int(self.block_size/2)
                    y = i * self.block_size + int(self.block_size/2) + self.header_size
                    size = int(self.block_size * 0.5)
                    s = pygame.Surface((size,size))
                    s.fill(self.color_dark)
                    s.set_colorkey(self.color_dark)
                    pygame.draw.rect(s, self.color_parcel, (0, 0, size, size), 1)
                    self.screen.blit(s, (x-int(size/2), y-int(size/2)))

                    # 剩余时间
                    if engine.step_left is not None:
                        parcel_id = int(engine._map[i,j,1])
                        num_str = str(engine.step_left[parcel_id-1])
                        textsurface, rect = self.num_font.render(num_str, self.color_parcel)
                        font_size = self.num_font.get_metrics(num_str)
                        font_height = font_size[0][3]-font_size[0][2]
                        self.screen.blit(textsurface, (x-int(size/2)+2, y-int(size/2)+2))

                    num_str = str(int(engine._map[i,j,1]))
                    textsurface, rect = self.num_font.render(num_str, self.color_parcel)
                    font_size = self.num_font.get_metrics(num_str)
                    font_height = font_size[0][3]-font_size[0][2]
                    self.screen.blit(textsurface, (x-int(size/2)+2, y+2))
