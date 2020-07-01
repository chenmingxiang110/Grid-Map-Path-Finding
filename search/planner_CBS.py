import numpy as np
import copy
import time
from queue import PriorityQueue

from lib.game_engine import game_engine
from search.planner_utils import tup_equal, tup_dist, parse_moves, Astar

def build_moving_plan(map, startings, endings, deadlines=None):

    def validate(solution):
        conflicts = set([])
        max_length = cost(solution)
        for i_step in range(max_length):
            moves = []
            for i_sol in range(len(solution)):
                if len(solution[i_sol])<=i_step:
                    moves.append(solution[i_sol][-1])
                else:
                    moves.append(solution[i_sol][i_step])
            if i_step>0:
                moves_prev = []
                for i_sol in range(len(solution)):
                    if len(solution[i_sol])<=(i_step-1):
                        moves_prev.append(solution[i_sol][-1])
                    else:
                        moves_prev.append(solution[i_sol][i_step-1])

            flag = False
            for i_sol in range(len(solution)):
                if i_sol<(len(solution)-1):
                    the_rest = moves[:i_sol]+moves[(i_sol+1):]
                else:
                    the_rest = moves[:i_sol]

                if moves[i_sol] in the_rest:
                    flag = True
                    conflicts.add((i_sol, moves[i_sol], i_step))

            # 判断路线中是否有二元环
            # if i_step>0:
            #     for i_sol in range(len(solution)):
            #         if i_sol<(len(solution)-1):
            #             the_rest = moves_prev[:i_sol]+[(-1,-1)]+moves_prev[(i_sol+1):]
            #         else:
            #             the_rest = moves_prev[:i_sol]+[(-1,-1)]
            #         if moves[i_sol] in the_rest:
            #             candidate = the_rest.index(moves[i_sol])
            #             if tup_equal(moves[candidate], moves_prev[i_sol]):
            #                 flag = True
            #                 conflicts.add((i_sol, moves[i_sol], i_step))

            # 判断路线中是否有环
            if i_step>0:
                for i_sol in range(len(solution)):
                    if i_sol<(len(solution)-1):
                        the_rest = moves_prev[:i_sol]+[(-1,-1)]+moves_prev[(i_sol+1):]
                    else:
                        the_rest = moves_prev[:i_sol]+[(-1,-1)]
                    if moves[i_sol] in the_rest:
                        ring = [i_sol]
                        new_i_sol = the_rest.index(moves[i_sol])
                        ring_flag = True
                        while new_i_sol not in ring:
                            ring.append(new_i_sol)
                            i_sol = new_i_sol
                            if i_sol<(len(solution)-1):
                                the_rest = moves_prev[:i_sol]+[(-1,-1)]+moves_prev[(i_sol+1):]
                            else:
                                the_rest = moves_prev[:i_sol]+[(-1,-1)]
                            if moves[i_sol] in the_rest:
                                new_i_sol = the_rest.index(moves[i_sol])
                            else:
                                ring_flag = False
                                break
                        if ring_flag:
                            flag = True
                            conflicts.add((i_sol, moves[i_sol], i_step))

            if flag: break

        return list(conflicts)

    def cost(solution):
        return np.max([len(x) for x in solution])

    def build_reservation(constraint):
        reservation = np.zeros([map.shape[0], map.shape[1], np.max([x[2] for x in constraint])+1], dtype=int)
        for c in constraint:
            reservation[c[1][0], c[1][1], c[2]] = 1
        return reservation

    def low_level(start, end, reservation, deadline=None):
        route = Astar(map, start, end, reservation=reservation)[0]
        if len(route)==0:
            return None, []
        if deadline is not None and len(route)>deadline:
            return None, []
        if len(route)>=reservation.shape[2]:
            return route, []
        else:
            for i in range(len(route), reservation.shape[2]):
                node = route[-1]
                new_nodes = [(int(node[0]), int(node[1])),
                             (int(node[0]-1), int(node[1])),
                             (int(node[0]+1), int(node[1])),
                             (int(node[0]), int(node[1]-1)),
                             (int(node[0]), int(node[1]+1))]
                flag = False
                for new_node in new_nodes:
                    if new_node[0]<0 or new_node[1]<0 or new_node[0]>=reservation.shape[0] or new_node[1]>=reservation.shape[1]: continue
                    if reservation[node[0], node[1], i]==0:
                        route.append(new_node)
                        flag = True
                        break
                if not flag:
                    # return None, [node[0], node[1], i-1]
                    return None, []
            return route, []

    assert len(startings)==len(endings)
    q = PriorityQueue() # (cost, solution)
    constraints = [[] for _ in range(len(startings))]
    solution = [Astar(map, startings[i], endings[i])[0] for i in range(len(startings))]
    q.put((cost(solution), solution, constraints))

    while q.qsize()>0:
        _, solution, constraints = q.get()
        conflicts = validate(solution)
        if len(conflicts)==0:
            return solution
        for c in conflicts:
            new_constraint_i = copy.deepcopy(constraints[c[0]]+[c])
            res = build_reservation(new_constraint_i)
            new_constraints = copy.deepcopy(constraints)
            new_constraints[c[0]] = new_constraint_i

            new_solution = copy.deepcopy(solution)
            if deadlines is None:
                new_route, new_conflict = low_level(startings[c[0]], endings[c[0]], res)
            else:
                new_route, new_conflict = low_level(startings[c[0]], endings[c[0]], res, deadlines[c[0]])
            while len(new_conflict)>0:
                res[new_conflict[0], new_conflict[1], new_conflict[2]] = 1
                if deadlines is None:
                    new_route, new_conflict = low_level(startings[c[0]], endings[c[0]], res)
                else:
                    new_route, new_conflict = low_level(startings[c[0]], endings[c[0]], res, deadlines[c[0]])
            if new_route is None:
                continue
            new_solution[c[0]] = new_route
            q.put((cost(new_solution), new_solution, new_constraints))

    return None

class CBS:

    def __init__(self, ge):
        map = ge._map[:,:,0]>=0
        startings = sorted([(int(x[0]), int(x[1])) for x in np.argwhere(ge._map[:,:,1]>0)], key=lambda x: ge._map[x[0],x[1],1])
        endings = sorted([(int(x[0]), int(x[1])) for x in np.argwhere(ge._map[:,:,0]>0)], key=lambda x: ge._map[x[0],x[1],0])
        if ge.step_left is not None:
            self.deadlines = ge.step_left-1
        else:
            self.deadlines = None

        tmp_sol = build_moving_plan(map, startings, endings, self.deadlines)
        if tmp_sol is None:
            self.solution = [[(0,0,0)] for _ in range(len(ge.players))]
        else:
            moves_list = [parse_moves(x) for x in tmp_sol]
            max_len = np.max([len(x) for x in tmp_sol])
            self.solution = []
            for moves in moves_list:
                moves_t = [(x[0], x[1], 0) for x in moves]
                while len(moves_t)<(max_len-1):
                    moves_t.append((0,0,0))
                moves_t.reverse()
                moves_t.append((0,0,1))
                self.solution.append(moves_t)

    def pop_moves(self, ge=None):
        # 此处输入 game engine 只是为了和其他 policy 保持一致 本质上没有任何作用
        if len(self.solution[0])>0:
            moves = [m.pop() for m in self.solution]
            return True, moves
        else:
            return False, []
