import pygame

def get_moves_manual(ge, gd):
    moves = []
    moves_str = []
    run = True

    while run:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return False, []
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT:
                    moves.append([0,-1,0])
                    moves_str.append("<")
                if e.key == pygame.K_RIGHT:
                    moves.append([0,1,0])
                    moves_str.append(">")
                if e.key == pygame.K_UP:
                    moves.append([-1,0,0])
                    moves_str.append("^")
                if e.key == pygame.K_DOWN:
                    moves.append([1,0,0])
                    moves_str.append("v")
                if e.key == pygame.K_SPACE:
                    moves.append([0,0,1])
                    moves_str.append("x")
                if e.key == pygame.K_w:
                    moves.append([0,0,0])
                    moves_str.append("w")
                if e.key == pygame.K_BACKSPACE:
                    moves = moves[:max(0, len(moves)-1)]
                    moves_str = moves_str[:len(moves)]
                if e.key == pygame.K_RETURN:
                    return True, moves

        gd.update(ge, moves_str=moves_str)
