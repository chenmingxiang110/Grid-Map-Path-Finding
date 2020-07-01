import time
import numpy as np

from tqdm import trange
from lib.game_engine import game_engine
from search.planner_utils import Astar, tup_dist

class greedy_WHCA:
    """
    This class actually implements the windowed cooperative a*. The window size
    is defined in max_step.
    """
    def __init__(self, ge, max_step, isHierachical=False, isPuzzle=False, max_stay=3, assignment_policy="greedy"):
        """
        assignment_policy: "greedy" or "random"
        """
        self.assignment_policy = assignment_policy
        self.max_stay = max_stay
        self.max_step = max_step
        self.isPuzzle = isPuzzle
        self.isHierachical = isHierachical
        if self.isHierachical:
            # 当身上无货物时用manhattan已经可以比较好的估计了，无需heuristic，只有当身上有货时需要
            self.heuristic = self.build_heuristic(ge)
        self.assignment = np.zeros(len(ge.players)).astype(int)
        self.reservation = np.zeros([ge._map.shape[0], ge._map.shape[1], self.max_step+1]).astype(int)
        self.shelf_coords = self.find_shelf_coords(ge)
        self.moves_list = []
        self.n_stay = np.zeros([len(ge.players), 3]).astype(int)
        self.init_player_pos = np.copy(ge.players[:,:2])
        self.init_player_grid = np.copy(ge._map[:,:,2])
        parcel_coords = self.find_parcel_coords(ge)
        self.assign(parcel_coords, ge)
        # print(self.assignment)
        for i,player in enumerate(ge.players):
            x, y, parcel = player
            route, moves = self.navigate(i, int(x), int(y), int(parcel), parcel_coords, ge, False)
            for j in range(0, len(route)):
                self.reservation[route[j][0],route[j][1],j] = (i+1)
            self.moves_list.append(moves)

    def build_heuristic(self, ge):
        heuristic = np.zeros([ge._map.shape[0],ge._map.shape[1],ge._map.shape[0],ge._map.shape[1]], dtype=int)

        grid = np.zeros(ge._map.shape[:2], dtype=int)
        grid += (ge._map[:,:,0]==-1)
        grid += (ge._map[:,:,2]>0)
        grid += ge._map[:,:,0]==-2
        grid = (grid==0)

        # 此代码极为不堪入目!!!
        print("Initializing the A* heuristic...")
        ijs = []
        for i in range(ge._map.shape[0]):
            for j in range(ge._map.shape[1]):
                ijs.append((i,j))

        for index in trange(len(ijs)):
            i0,j0 = ijs[index]
            for i1,j1 in ijs:
                route, _ = Astar(grid, (i0,j0), (i1,j1))
                heuristic[i0,j0,i1,j1] = len(route)-1

        return heuristic

    def pop_moves(self, ge):
        # print(ge._map[:,:,2])
        parcel_coords = self.find_parcel_coords(ge)
        self.assign(parcel_coords, ge)
        # print(self.assignment)
        # self.reservation = np.zeros([ge._map.shape[0], ge._map.shape[1], self.max_step]).astype(int)
        # self.moves_list = []
        for i,player in enumerate(ge.players):
            x, y, parcel = player

            # 后一个判断条件是判断这一步是否符合预期，与预先的预期不同则重新规划
            if len(self.moves_list[i])>0 and (i+1)==self.reservation[int(x), int(y), 0]:
                continue

            isRandMove=False
            if self.n_stay[i][0]==int(x) and self.n_stay[i][1]==int(y):
                self.n_stay[i][2]+=1
                if self.n_stay[i][2]>=self.max_stay:
                    if self.n_stay[i][0]!=self.init_player_pos[i][0] or self.n_stay[i][1]!=self.init_player_pos[i][1]:
                        isRandMove=True
            else:
                self.n_stay[i][0]=int(x)
                self.n_stay[i][1]=int(y)
                self.n_stay[i][2]=0

            if isRandMove:
                route, moves_i = self.navigate(i, int(x), int(y), int(parcel), parcel_coords, ge, True)
            else:
                route, moves_i = self.navigate(i, int(x), int(y), int(parcel), parcel_coords, ge, False)
            for j in range(0, len(route)):
                self.reservation[route[j][0],route[j][1],j] = (i+1)
            self.moves_list[i] = moves_i
            # self.moves_list.append(moves_i)

        moves = [m.pop() for m in self.moves_list]

        new_res = np.zeros([self.reservation.shape[0], self.reservation.shape[1], 1]).astype(int)
        self.reservation = np.concatenate((self.reservation[:,:,1:], new_res), axis=2)

        for i in range(len(ge.players)):
            if moves[i][2]>0 and ge.players[i][2]>0:
                self.assignment[i]=0

        return True, moves

    def assign(self, parcel_coords, ge):
        if self.assignment_policy=="greedy":
            if ge.step_left is None:
                if np.sum(ge._map[:,:,1]>0)<=len(ge.players):
                    # print("Parcel First")
                    for i, par in enumerate(parcel_coords):
                        if par[0]>=0 and (i+1) not in self.assignment:
                            player_dists = [(j, tup_dist(par, ge.players[j])) for j in range(len(ge.players)) if self.assignment[j]==0]
                            player_sorted = sorted(player_dists, key = lambda x: x[1])
                            if len(player_sorted)>0:
                                self.assignment[player_sorted[0][0]]=i+1
                else:
                    # print("AGV First")
                    for player_i in range(len(self.assignment)):
                        if self.assignment[player_i]>0: continue
                        x,y,_ = ge.players[player_i]
                        parcel_seq = [(tup_dist(parcel_coords[i], (x,y)), i) for i in range(len(parcel_coords)) if parcel_coords[i][0]>=0]
                        parcel_seq = sorted(parcel_seq, key=lambda x: x[0])
                        ends = [x[1] for x in parcel_seq]
                        for end_i in ends:
                            if (end_i+1) in self.assignment: continue
                            self.assignment[player_i]=end_i+1
                            break
            else:
                parcel_seq = [(i, par, ge.step_left[i]) for i, par in enumerate(parcel_coords)]
                parcel_seq = sorted(parcel_seq, key = lambda x: x[2])
                for i, par, _ in parcel_seq:
                    if par[0]>=0 and (i+1) not in self.assignment:
                        player_dists = [(j, tup_dist(par, ge.players[j])) for j in range(len(ge.players)) if self.assignment[j]==0]
                        player_sorted = sorted(player_dists, key = lambda x: x[1])
                        if len(player_sorted)>0:
                            self.assignment[player_sorted[0][0]]=i+1
        elif self.assignment_policy=="random":
            for player_i in range(len(self.assignment)):
                if self.assignment[player_i]>0: continue
                x,y,_ = ge.players[player_i]
                ends = [i for i in range(len(parcel_coords)) if parcel_coords[i][0]>=0]
                for end_i in ends:
                    if (end_i+1) in self.assignment: continue
                    self.assignment[player_i]=end_i+1
                    break
        else:
            raise ValueError("Invalid assignment policy.")

    def navigate(self, i, x, y, parcel, parcel_coords, ge, isRand):
        ass = self.assignment[i]
        if isRand:
            new_x = int(min(max(x+np.random.randint(7)-3, 0), ge._map.shape[0]-1))
            new_y = int(min(max(y+np.random.randint(7)-3, 0), ge._map.shape[1]-1))
            end = np.array([new_x, new_y])
        else:
            if parcel == 0:
                if ass == 0:
                    if self.isPuzzle:
                        avail_coords = np.argwhere(ge._map[:,:,0]>=0)
                        tmp_i = np.random.randint(len(avail_coords))
                        end = (avail_coords[tmp_i,0], avail_coords[tmp_i,1])
                    else:
                        end = self.init_player_pos[i]
                else:
                    end = parcel_coords[ass-1]
            else:
                end = self.shelf_coords[parcel-1]

        grid = np.zeros(self.reservation.shape[:2])

        # 如果当前停在停车区的车数量超过1/2，那么有比较大的概率之后会撞上在停车区的车，因此需要在规划时避开
        n_player_home = np.sum(np.sum(np.abs(self.init_player_pos-ge.players[:,:2]), axis=1)==0)
        if n_player_home/len(self.init_player_pos)>0.5:
            grid += self.init_player_grid*(self.init_player_grid!=(i+1))

        grid += (ge._map[:,:,0]==-1)
        grid += (ge._map[:,:,2]>0)
        if parcel != 0:
            grid += ge._map[:,:,1]>0
            grid += ge._map[:,:,0]==-2
        grid = (grid==0)

        if parcel != 0 and self.isHierachical:
            route, moves = Astar(grid, (x,y), end, reservation=self.reservation, _heuristic=self.heuristic)
        else:
            route, moves = Astar(grid, (x,y), end, reservation=self.reservation)

        if isRand:
            if len(moves)>0:
                moves = [(m[0], m[1], 0) for m in moves]
            else:
                route = [(x,y),(x,y)]
                moves = [(0,0,0)] # 此步骤有可能打乱其他agv的规划
        else:
            if len(moves)>0:
                moves = [(m[0], m[1], 0) for m in moves]
                if ass!=0:
                    route.append(route[-1])
                    moves.append((0,0,1))
            else:
                if len(route)>0 and ass!=0:
                    route = [(x,y),(x,y)]
                    moves = [(0,0,1)]
                else:
                    route = [(x,y),(x,y)]
                    moves = [(0,0,0)] # 此步骤有可能打乱其他agv的规划

        moves.reverse()
        if self.max_step>0 and len(route)>(self.max_step+1):
            route = route[:self.max_step+1]
            moves = moves[-self.max_step:]
        return route, moves

    def find_parcel_coords(self, ge):
        parcel_coords = np.zeros([np.max(ge._map[:,:,0]),2])-1
        for i in range(ge._map.shape[0]):
            for j in range(ge._map.shape[1]):
                if ge._map[i,j,1]>0:
                    parcel_coords[ge._map[i,j,1]-1] = np.array([i,j])
        return parcel_coords.astype(int)

    def find_shelf_coords(self, ge):
        shelf_coords = np.zeros([np.sum(ge._map[:,:,0]>0),2])-1
        for i in range(ge._map.shape[0]):
            for j in range(ge._map.shape[1]):
                if ge._map[i,j,0]>0:
                    shelf_coords[ge._map[i,j,0]-1] = np.array([i,j])
        return shelf_coords.astype(int)
