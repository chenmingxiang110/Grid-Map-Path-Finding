import numpy as np
from queue import PriorityQueue

def tup_equal(tup1, tup2):
    return tup1[0]==tup2[0] and tup1[1]==tup2[1]

def tup_dist(tup1, tup2):
    # return ((tup1[0]-tup2[0])**2+(tup1[1]-tup2[1])**2)**0.5
    return int(np.abs(tup1[0]-tup2[0])+np.abs(tup1[1]-tup2[1]))

def parse_moves(route):
    moves = []
    for i in range(1, len(route)):
        moves.append((route[i][0]-route[i-1][0], route[i][1]-route[i-1][1]))
    return moves

def _Astar_Strict(grid, start, end, reservation=None, _heuristic=None):
    """
    grid : m*n np bool matrix
    start: (x,y), tuple
    end  : (x,y), tuple
    """
    def heuristic(node):
        return tup_dist(node, end)

    visited = set([])
    prevs = {}
    q = PriorityQueue() # (priority, dist_to_origin, current_node)
    q.put((0, 0, start))
    flag = False

    while q.qsize()>0:
        _, dist, node = q.get()
        if node in visited: continue
        if tup_equal(node, end):
            flag = True
            break
        visited.add(node)
        for new_node in [(int(node[0]-1), int(node[1])),
                         (int(node[0]+1), int(node[1])),
                         (int(node[0]), int(node[1]-1)),
                         (int(node[0]), int(node[1]+1))]:
            if new_node[0]<0 or new_node[1]<0 or new_node[0]>=grid.shape[0] or new_node[1]>=grid.shape[1]: continue
            if not grid[new_node] or new_node in visited: continue
            if reservation is not None and (dist+1)<reservation.shape[2] and \
                    reservation[new_node[0], new_node[1], dist]+reservation[new_node[0], new_node[1], dist+1]>0:
                continue
            if _heuristic is None:
                p = dist+1+heuristic(new_node)
            else:
                p = dist+1+_heuristic[new_node[0],new_node[1],end[0],end[1]]
            q.put((p, dist+1, new_node))
            prevs[new_node] = node

    if flag:
        route = []
        while not tup_equal(node, start):
            route.append(node)
            node = prevs[node]
        route.append(node)
        route.reverse()
        moves = parse_moves(route)
        return route, moves
    else:
        return [], []

def Astar(grid, start, end, reservation=None, _heuristic=None, isStrictCheck=True, canWait=False, useVisited=True):
    """
    grid : m*n np bool matrix, True for road, False for block
    start: (x,y), tuple
    end  : (x,y), tuple
    """
    if isStrictCheck and (not canWait) and useVisited:
        return _Astar_Strict(grid, start, end, reservation=reservation, _heuristic=_heuristic)

    def heuristic(node):
        return tup_dist(node, end)

    visited = set([])
    q = PriorityQueue() # (priority, dist_to_origin, current_node)
    q.put((0, 0, start, [start]))
    flag = False

    while q.qsize()>0:
        _, dist, node, route = q.get()
        if tup_equal(node, end):
            flag = True
            break
        if useVisited: visited.add(node)

        if canWait:
            new_nodes = [(int(node[0]), int(node[1])),
                         (int(node[0]-1), int(node[1])),
                         (int(node[0]+1), int(node[1])),
                         (int(node[0]), int(node[1]-1)),
                         (int(node[0]), int(node[1]+1))]
        else:
            new_nodes = [(int(node[0]-1), int(node[1])),
                         (int(node[0]+1), int(node[1])),
                         (int(node[0]), int(node[1]-1)),
                         (int(node[0]), int(node[1]+1))]

        for new_node in new_nodes:
            if new_node[0]<0 or new_node[1]<0 or new_node[0]>=grid.shape[0] or new_node[1]>=grid.shape[1]:
                continue
            if not grid[new_node]:
                continue
            if new_node in visited and (not tup_equal(node, new_node)):
                continue
            if isStrictCheck:
                if reservation is not None and (dist+1)<reservation.shape[2] and \
                        reservation[new_node[0], new_node[1], dist]+reservation[new_node[0], new_node[1], dist+1]>0:
                    continue
            else:
                if reservation is not None and (dist+1)<reservation.shape[2] and \
                        reservation[new_node[0], new_node[1], dist+1]>0:
                    continue
            if _heuristic is None:
                p = dist+1+heuristic(new_node)
            else:
                p = dist+1+_heuristic[new_node[0],new_node[1],end[0],end[1]]
            q.put((p, dist+1, new_node, route+[new_node]))

    if flag:
        moves = parse_moves(route)
        return route, moves
    else:
        return [], []
