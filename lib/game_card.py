import numpy as np
import os
import pickle
from lib.utils import parse_map, init_parcels
from lib.game_engine import game_engine

class game_card:

    def __init__(self, params):
        if isinstance(params, str):
            folder_path=params
        else:
            _abs, _players, parcel_gen_gap, init_n_parcels, max_step, have_dl = params
            folder_path = None

        if folder_path is None:
            self.max_step = max_step
            self.parcel_gen_gap = parcel_gen_gap
            self.have_dl = bool(have_dl)
            self._map = parse_map(_abs, _players, _parcels=init_parcels(_abs, init_n_parcels))
            if self.have_dl:
                self.upper_dl = 4 * (self._map.shape[0]+self._map.shape[1])
                self.lower_dl = 1 * (self._map.shape[0]+self._map.shape[1])
                self.step_left = -np.ones([np.max(self._map[:,:,0])], dtype=int)
                for i in range(len(self.step_left)):
                    if i+1 in self._map[:,:,1]:
                        self.step_left[i] = np.random.randint(self.upper_dl-self.lower_dl+1)+self.lower_dl
            else:
                self.step_left = None
            if parcel_gen_gap == 0:
                self.parcel_gen_seq = None
            else:
                self.parcel_gen_seq = self._build_parcel_gen_seq()
        else:
            if folder_path[-1]=="/":
                root = folder_path
            else:
                root = folder_path+"/"
            self.max_step, self.parcel_gen_gap, self.have_dl = np.load(root+"basic_info.npy")
            self.max_step = int(self.max_step)
            self.have_dl = bool(self.have_dl)
            self._map = np.load(root+"_map.npy")
            if self.have_dl:
                self.step_left = np.load(root+"step_left.npy")
            else:
                self.step_left = None
            if self.parcel_gen_gap>0:
                with open(root+'parcel_gen_seq.pickle', 'rb') as handle:
                    self.parcel_gen_seq = pickle.load(handle)
            else:
                self.parcel_gen_seq = None

    def save(self, folder_path):
        if folder_path[-1]=="/":
            root = folder_path
        else:
            root = folder_path+"/"
        try:
            os.mkdir(root)
        except FileExistsError:
            print("Note: The game card folder already exists.")
        basic_info = np.array([self.max_step, self.parcel_gen_gap, self.have_dl])
        np.save(root+"basic_info", basic_info)
        np.save(root+"_map", self._map)
        if self.have_dl: np.save(root+"step_left", self.step_left)
        with open(root+'parcel_gen_seq.pickle', 'wb') as handle:
            pickle.dump(self.parcel_gen_seq, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, folder_path):
        if folder_path[-1]=="/":
            root = folder_path
        else:
            root = folder_path+"/"
        self.max_step, self.parcel_gen_gap, self.have_dl = np.load(root+"basic_info.npy")
        self.max_step = int(self.max_step)
        self.have_dl = bool(self.have_dl)
        self._map = np.load(root+"_map.npy")
        if self.have_dl:
            self.step_left = np.load(root+"step_left.npy")
        else:
            self.step_left = None
        if self.parcel_gen_gap>0:
            with open(root+'parcel_gen_seq.pickle', 'rb') as handle:
                self.parcel_gen_seq = pickle.load(handle)
        else:
            self.parcel_gen_seq = None

    def _build_parcel_gen_seq(self):
        result = []
        n_shelves = np.max(self._map[:,:,0])
        avail_indices = np.nonzero(self._map[:,:,0]==-2)

        for i in range(self.max_step):
            num = 0
            if self.parcel_gen_gap<1:
                num = int(np.round(np.random.random() * 2 / self.parcel_gen_gap))
            elif self.parcel_gen_gap>=1 and np.random.random()<(1/self.parcel_gen_gap):
                num = 1
            num = min(num, len(avail_indices[0]))

            gens = []
            loc_ids = np.random.choice(len(avail_indices[0]), num, replace=False)
            for j in range(num):
                loc_id = loc_ids[j]
                loc = (avail_indices[0][loc_id],avail_indices[1][loc_id])
                obj = np.random.randint(n_shelves)+1
                if self.have_dl:
                    dl = np.random.randint(self.upper_dl-self.lower_dl+1)+self.lower_dl
                    gens.append([loc[0], loc[1], obj, dl])
                else:
                    gens.append([loc[0], loc[1], obj])
            result.append(gens)

        return result

    def output_engine(self):
        if self.have_dl:
            ge = game_engine(self._map, self.parcel_gen_gap, parcel_gen_seq=self.parcel_gen_seq, step_left=self.step_left)
        else:
            ge = game_engine(self._map, self.parcel_gen_gap, parcel_gen_seq=self.parcel_gen_seq)
        return self.max_step, ge
