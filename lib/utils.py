import random
import numpy as np
import signal

from contextlib import contextmanager

from lib.game_engine import game_engine
from search.planner_utils import Astar, tup_dist

class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def read_map(file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if len(line.strip())>0:
                data.append([int(x) for x in line.strip().split(",")])
            else:
                data.append([])
    _abs = np.array(data[:data.index([])], dtype=int)
    _players = np.array(data[data.index([])+1:], dtype=int)
    return _abs, _players

def parse_map(_abs, _players, _parcels = None):
    _map = np.copy(-_abs)
    _pid = np.copy(_players)
    shelf_id = 1
    player_id = 1
    if _parcels is None:
        _parcels = np.zeros(_map.shape)

    for i in range(_map.shape[0]):
        for j in range(_map.shape[1]):
            if _map[i,j]==-3:
                _map[i,j] = shelf_id
                shelf_id+=1
            if _pid[i,j]==1:
                _pid[i,j] = player_id
                player_id+=1

    _map = np.transpose(np.array([_map, _parcels, _pid]), [1,2,0])
    return _map.astype(int)

def init_parcels(_abs, num):
    _parcels = np.zeros(_abs.shape)
    n_shelves = np.sum(_abs==3)
    for _ in range(num):
        spawn_locs = (_abs==2).astype(int)
        parcel_locs = (_parcels>0).astype(int)
        parcel_locs *= spawn_locs
        avail_locs = spawn_locs-parcel_locs
        if np.sum(avail_locs) == 0:
            # 包裹重生点已被占满
            break
        avail_indices = np.nonzero(avail_locs)
        loc_id = np.random.randint(len(avail_indices[0]))
        loc = (avail_indices[0][loc_id],avail_indices[1][loc_id])

        p = np.ones(n_shelves)
        for i in range(n_shelves):
            if (i+1) in _parcels:
                p[i]=0
        p = p/np.sum(p)
        obj = int(np.random.choice(np.arange(n_shelves)+1, p = p))
        _parcels[loc[0],loc[1]] = obj
    return _parcels.astype(int)

def random_puzzle_abs(shape, road_ratio, num):
    _abs = -np.ones(shape, dtype=int)
    _parcels = np.zeros(shape, dtype=int)
    _pid = np.zeros(shape, dtype=int)

    init_pos = (int(shape[0]/2), int(shape[1]/2))
    avail_pos = set([init_pos])
    possible_pos = []
    for i in range(shape[0]):
        for j in range(shape[1]):
            possible_pos.append((i,j))
    se_pos = random.sample(possible_pos, num*2)
    possible_pos = set(possible_pos)
    possible_trans = [(-1,0),(1,0),(0,-1),(0,1)]
    starting_pos = se_pos[:num]
    ending_pos = se_pos[num:]
    uncovered = [x for x in se_pos if x not in avail_pos]
    s = init_pos

    while len(uncovered)>0:
        if np.random.random()<0.1:
            e = random.choice(uncovered)
        else:
            e = sorted([(x,tup_dist(s,x)) for x in uncovered], key=lambda x: x[1])[0][0]
        r, _ = Astar(_parcels==0, s, e)
        for node in r:
            avail_pos.add(node)
        uncovered = [x for x in se_pos if x not in avail_pos]
        s = e

    while len(avail_pos)<(shape[0]*shape[1]*road_ratio):
        s = random.choice(list(avail_pos))
        t = random.choice(possible_trans)
        new_node = (s[0]+t[0], s[1]+t[1])
        if new_node in possible_pos:
            avail_pos.add(new_node)

    for node in avail_pos:
        _abs[node] = 0
    for i,node in enumerate(starting_pos):
        _parcels[node] = i+1
        _pid[node] = i+1
    for i,node in enumerate(ending_pos):
        _abs[node] = i+1

    _map = np.transpose(np.array([_abs, _parcels, _pid]), [1,2,0])
    return _map.astype(int)

def read_trans_center_map(file_path, spawn_marks):
    marks = "*0123456789abcdefghijklmnopqrstuvwxyz"
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            if len(line.strip())>0:
                data.append([marks.index(x)-1 for x in line.strip().split(",")])
            else:
                data.append([])
    _abs = np.array(data[:data.index([])], dtype=int)
    _players = np.array(data[data.index([])+1:], dtype=int)
    for i in range(_abs.shape[0]):
        for j in range(_abs.shape[1]):
            if _abs[i,j]==-1:
                _abs[i,j]=1
            elif _abs[i,j]>0:
                if _abs[i,j] in spawn_marks:
                    _abs[i,j] = 2
                else:
                    _abs[i,j] = 3
    return _abs, _players
