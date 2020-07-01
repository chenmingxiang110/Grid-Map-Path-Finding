import numpy as np
import threading

class game_engine:
    """
    规则:
    1. 不带货的情况下 AGV可以在普通道路 货架区 和摆放货物的格子无障碍穿行
    2. 不带货的情况下 AGV不可穿墙
    3. 不带货的情况下 AGV不可以行驶至其他AGV所在位置
       * 若两AGV目标格子相同 则随机有一方可以成功 随机的方式既以随机的顺序计算AGV下一步位置及合法性
       * 注意这里要implement两次check 有可能一个AGV1走了，另一个AGV2要到该AGV1之前所在位置
    4. 在带货的情况下 除了2和3规定的情况 AGV还不能前往有货的格子
    5. AGV 可以在道路中间把货物放下 但不可以把货塞在错误的货架上
    """

    def __init__(self, _map, parcel_gen_gap, parcel_gen_seq=None, step_left=None, dl_bound=None, auto_unload=False):
        """
        _map is a (x,y,3) numpy array, where the layers are:
            1st: walls, spawn points, shelves
            2nd: parcels
            3rd: players(robos)
        step_left: None: no deadline
                   np.array([]) or []: random deadline given by the engine
                   np.array([...]) or [...]: a list of given deadline
        See the main python file for more information.
        """
        self._lock = threading.Lock() # 避免 atomic 未同步
        self.auto_unload = auto_unload
        self._map = _map.astype(int)
        self.should_gen = parcel_gen_gap>0 or (parcel_gen_seq is not None)
        self.parcel_gen_gap = parcel_gen_gap
        self.parcel_gen_seq = parcel_gen_seq # [[(x11,y11,shelf11)], [], [(x21,y21,shelf21),(x22,y22,shelf22)], ...]
        self.success_score = 10

        if dl_bound is None:
            self.lower_dl = 1 * (self._map.shape[0]+self._map.shape[1])
            self.upper_dl = 4 * (self._map.shape[0]+self._map.shape[1])
        else:
            self.lower_dl, self.upper_dl = dl_bound

        if step_left is None:
            self.step_left = None
        elif len(step_left)==0:
            self.step_left = -np.ones([np.max(self._map[:,:,0])], dtype=int)
            for i in range(len(self.step_left)):
                if i+1 in self._map[:,:,1]:
                    self.step_left[i] = np.random.randint(self.upper_dl-self.lower_dl+1)+self.lower_dl
        else:
            self.step_left = step_left
        self.score = 0
        self.steps = 0

        self.n_delivered = 0
        self.n_delayed = 0

        # i, j, whether the player carries a parcel. 注意 逻辑ij和显示时的xy是相反的
        self.players = np.zeros([np.sum(_map[:,:,2]>0),3])
        for i in range(_map.shape[0]):
            for j in range(_map.shape[1]):
                if self._map[i,j,2]>0:
                    self.players[self._map[i,j,2]-1][0] = i
                    self.players[self._map[i,j,2]-1][1] = j

    def step(self, moves):
        """
        moves = [move_0, move_1, ...]
        move = (x,y,grab)
        The function updates self._map, and returns the reward.
        """

        moves_indices = np.array([[i,move[0],move[1],move[2]] for i,move in enumerate(moves)])
        moves_indices = np.random.permutation(moves_indices)


        candidates = []
        for move in moves_indices:
            if int(move[0])>=len(self.players): continue
            old_pos = (self.players[int(move[0])][:2]).astype(int)
            new_pos = (old_pos+move[1:3]).astype(int)
            if np.sum(np.abs(old_pos-new_pos))>0:
                # 过界
                if new_pos[0]<0 or new_pos[1]<0 or new_pos[0]>=self._map.shape[0] or new_pos[1]>=self._map.shape[1]:
                    continue
                # 墙壁
                if self._map[new_pos[0], new_pos[1]][0]==-1:
                    continue
                # 其他AGV
                if self._map[new_pos[0], new_pos[1]][2]>0:
                    candidates.append(move)
                    continue
                # 若AGV身上有货物
                if self.players[int(move[0])][2]!=0:
                    # 非AGV上的货物
                    if self._map[new_pos[0], new_pos[1]][1]>0 and self._map[new_pos[0], new_pos[1]][2]<=0:
                        continue
                self.players[int(move[0])][:2] = new_pos
                self.update_player_map() # 更新AGV位置
                # 如果身上带着货物 更新货物位置
                if self.players[int(move[0])][2]!=0:
                    self._map[:,:,1][new_pos[0], new_pos[1]] = self.players[int(move[0])][2]
                    self._map[:,:,1][old_pos[0], old_pos[1]] = 0

            # 抓起/放下
            if self.auto_unload:
                if self.players[int(move[0])][2]>0 and self._map[new_pos[0], new_pos[1], 0]==self.players[int(move[0])][2]:
                    self.players[int(move[0])][2] = 0
                if move[-1]!=0 and self.players[int(move[0])][2]==0:
                    self.players[int(move[0])][2] = self._map[:,:,1][old_pos[0], old_pos[1]]
            else:
                if move[-1]!=0:
                    if self.players[int(move[0])][2]>0:
                        self.players[int(move[0])][2] = 0
                    else:
                        self.players[int(move[0])][2] = self._map[:,:,1][old_pos[0], old_pos[1]]

        candidate_last_length = -1
        while(len(candidates)>0 and not(len(candidates)==candidate_last_length)):
            # 更好的实现方法是 topological sort 否则无法解决环的问题
            new_candidates = []
            for move in candidates:
                old_pos = (self.players[int(move[0])][:2]).astype(int)
                new_pos = (old_pos+move[1:3]).astype(int)
                # 其他AGV
                if self._map[new_pos[0], new_pos[1]][2]>0:
                    new_candidates.append(move)
                    continue
                self.players[int(move[0])][:2] = new_pos
                self.update_player_map() # 更新AGV位置
                # 如果身上带着货物 更新货物位置
                if self.players[int(move[0])][2]!=0:
                    self._map[:,:,1][new_pos[0], new_pos[1]] = self.players[int(move[0])][2]
                    self._map[:,:,1][old_pos[0], old_pos[1]] = 0

                # 抓起/放下
                if self.auto_unload:
                    if self.players[int(move[0])][2]>0 and self._map[new_pos[0], new_pos[1], 0]==self.players[int(move[0])][2]:
                        self.players[int(move[0])][2] = 0
                    if move[-1]!=0 and self.players[int(move[0])][2]==0:
                        self.players[int(move[0])][2] = self._map[:,:,1][old_pos[0], old_pos[1]]
                else:
                    if move[-1]!=0:
                        if self.players[int(move[0])][2]>0:
                            self.players[int(move[0])][2] = 0
                        else:
                            self.players[int(move[0])][2] = self._map[:,:,1][old_pos[0], old_pos[1]]

            candidate_last_length = len(candidates)
            candidates = new_candidates

        delta_score = self.update_score() # 检查是否有包裹摆放到位 有的话更新分数

        if self.should_gen:
            if self.parcel_gen_seq is None:
                if self.parcel_gen_gap<1:
                    n = int(np.round(np.random.random() * 2 / self.parcel_gen_gap))
                    self.generate_parcels(n)
                elif self.parcel_gen_gap>=1 and np.random.random()<(1/self.parcel_gen_gap):
                    self.generate_parcels(1)
            else:
                self.generate_parcels(None)

        if self.step_left is not None:
            self.step_left-=1
            for i in range(len(self.step_left)):
                if self.step_left[i]<0: self.step_left[i]=-1

        self.steps+=1
        return delta_score

    def update_player_map(self):
        player_map = np.zeros(self._map.shape[:2])
        for i,p in enumerate(self.players):
            player_map[int(p[0]), int(p[1])] = i+1
        self._map[:,:,2] = player_map

    def update_score(self):
        correct_map = (self._map[:,:,0]==self._map[:,:,1]).astype(int) * (self._map[:,:,1]!=0).astype(int)
        for p in self.players:
            if p[2]!=0:
                correct_map[int(p[0]),int(p[1])]=0
        correct_coords = np.argwhere(correct_map==1)
        parcel_coords = np.argwhere(self._map[:,:,1]>0)
        _s = 0
        if self.step_left is not None:
            for x,y in parcel_coords:
                if self.step_left[self._map[x,y,1]-1]<0:
                    _s-=1
            for x,y in correct_coords:
                if self.step_left[self._map[x,y,1]-1]<0:
                    self.n_delayed+=1
                _s+=self.success_score
                self.n_delivered+=1
                self.step_left[self._map[x,y,1]-1] = -1
        else:
            for x,y in correct_coords:
                _s+=self.success_score
                self.n_delivered+=1

        with self._lock:
            self.score+=_s

        self._map[:,:,1] *= (correct_map==0)
        return _s

    def generate_parcels(self, num):
        if self.parcel_gen_seq is None:
            for _ in range(num):
                shelf_max = np.max(self._map[:,:,0])
                spawn_locs = (self._map[:,:,0]==-2).astype(int)
                parcel_locs = (self._map[:,:,1]>0).astype(int)
                parcel_locs *= spawn_locs
                avail_locs = spawn_locs-parcel_locs
                if np.sum(avail_locs) == 0:
                    # 包裹重生点已被占满
                    break
                if np.sum(self._map[:,:,1]>0)>=shelf_max:
                    # 已经不可能产生不重复的包裹
                    break
                avail_indices = np.nonzero(avail_locs)
                loc_id = np.random.randint(len(avail_indices[0]))
                loc = (avail_indices[0][loc_id],avail_indices[1][loc_id])

                # 同一时间 每个parcel目的地不能相同
                p = np.ones(shelf_max)
                for i in range(shelf_max):
                    if (i+1) in self._map[:,:,1]:
                        p[i]=0
                p = p/np.sum(p)
                obj = int(np.random.choice(np.arange(shelf_max)+1, p = p))
                if self.step_left is not None:
                    self.step_left[obj-1] = np.random.randint(self.upper_dl-self.lower_dl+1)+self.lower_dl
                self._map[loc[0],loc[1],1] = obj
        else:
            if self.step_left is not None:
                for x,y,shelf_index,dl in self.parcel_gen_seq[self.steps]:
                    if self._map[x,y,1]==0 and shelf_index not in self._map[:,:,1]:
                        self._map[x,y,1] = shelf_index
                        self.step_left[shelf_index-1] = dl
            else:
                for x,y,shelf_index in self.parcel_gen_seq[self.steps]:
                    if self._map[x,y,1]==0 and shelf_index not in self._map[:,:,1]:
                        self._map[x,y,1] = shelf_index

    def get_score(self):
        # score, num_delivered, num_time_out
        parcel_coords = np.argwhere(self._map[:,:,1]>0)
        n_timeout = 0
        if self.step_left is not None:
            for x,y in parcel_coords:
                if self.step_left[self._map[x,y,1]-1]<0:
                    n_timeout+=1
        return self.steps, self.score, self.n_delivered, self.n_delayed, n_timeout

    def get_state(self):
        if self.step_left is not None:
            return np.copy(self._map), np.copy(self.players), np.copy(self.step_left)
        return np.copy(self._map), np.copy(self.players), None

    def set_state(self, _map, players, step_left=None):
        self._map = _map
        self.players = players
        self.step_left = step_left
