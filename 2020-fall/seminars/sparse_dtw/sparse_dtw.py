"""
Task:
Python Implementation of the SparseDTW Algorithm by Ghazi Al-Naymat,
Sanjay Chawla and Javid Taheri.

http://arxiv.org/abs/1201.2969
"""

# Import Built-Ins
import argparse
import logging

# Import Third-Party
import numpy as np
from scipy.sparse import lil_matrix

# Import Homebrew

log = logging.getLogger(__name__)


class SparseDTW:

    def __init__(self, s, q, res=.5):

        self.n, self.m = len(s), len(q)
        self.res = res
        self.s = s
        self.q = q
        self.S = self.quantize(self.s)
        self.Q = self.quantize(self.q)
        self.SM = lil_matrix((self.n, self.m), dtype=np.float64)

    def quantize(self, series):
        return [(series[i] - min(series)) / (max(series) - min(series))
                for i in range(len(series))]

    def euc_distance(self, x, y):
        return np.abs(x - y) ** 2

    def lower_neighbors(self, x, y):
        if x == 0 and y == 0:
            return []
        else:
            coord_a = (x-1, y) if x-1 >= 0 and y >= 0 else None
            coord_b = (x-1, y-1) if x-1 >= 0 and y-1 >= 0 else None
            coord_c = (x, y-1)if x >= 0 and y-1 >= 0 else None
            return [neighbor for neighbor in (coord_b, coord_c, coord_a)
                    if neighbor is not None]

    def upper_neighbors(self, x, y):
        if x == self.n-1 and y == self.m-1:
            return []
        else:
            coord_a = (x+1, y) if x+1 < self.n and y < self.m else None
            coord_b = (x+1, y+1) if x+1 < self.n and y+1 < self.m else None
            coord_c = (x, y+1) if x < self.n and y+1 < self.m else None
            return [neighbor for neighbor in (coord_b, coord_c, coord_a)
                    if neighbor is not None]

    def unblock_upper_neighbors(self, neighbors):

        for coord in neighbors:
            x, y = coord
            if self.SM[coord] == 0:
                try:
                    self.SM[coord] = self.euc_distance(self.S[x], self.Q[y])
                except IndexError:
                    log.debug("unblock_upper_neighbors(%s, %s): "
                              "Error at coord (%s) %s" % (i, j, coord, neighbors))
                    raise

    def populate_warp(self):

        lower_bound = 0
        upper_bound = self.res
        while 0 <= lower_bound <= 1 - self.res / 2:
            idxS = [i for i in range(self.n) if (lower_bound <= self.S[i] <= upper_bound)]
            idxQ = [i for i in range(self.m) if (lower_bound <= self.Q[i] <= upper_bound)]

            # update bounds
            lower_bound += + self.res / 2
            upper_bound = lower_bound + self.res

            # For indices, calculate euclidic distances and add to warp matrix SM
            for i in idxS:
                for j in idxQ:
                    euc_d = self.euc_distance(self.S[i], self.Q[j])
                    if euc_d == 0:
                        self.SM[(i, j)] = -1
                    else:
                        if self.SM[i, j] != -1:
                            self.SM[(i, j)] = self.SM[(i, j)] + euc_d
                        else:
                            self.SM[(i, j)] = euc_d

    def calculate_warp_costs(self):

        for i in range(self.n):
            for j in range(self.m):
                if self.SM[i,j]:
                    lower_n = [self.SM[x,y] for x,y in self.lower_neighbors(i, j)
                               if self.SM[x,y] != 0]

                    if lower_n:
                        min_cost = min(lower_n)
                        min_cost = 0 if min_cost == -1 else min_cost
                    else:
                        min_cost = 0

                    if self.SM[i, j] > -1: # Ignore blocked neighbors ??
                        self.SM[i, j] = self.SM[i, j] + min_cost
                    elif self.SM[i, j] == 0:
                        pass
                    elif self.SM[i, j] == -1:
                        self.SM[i, j] = min_cost if min_cost > 0 else -1
                    else:
                        raise ValueError('Unexpected Value in SM! '
                                         '%s (%s, %s)' % (self.SM[i, j], i, j))

                    # check upper neighbors
                    upper_n = self.upper_neighbors(i, j)
                    if upper_n and not any(self.SM[x,y] != 0 for x,y in upper_n):
                        self.unblock_upper_neighbors(upper_n)
                    else:
                        continue

    def calculate_warp_path(self):
        hop = self.n-1, self.m-1
        warping_path = [hop]
        print(hop)
        while hop != (0, 0):
            lower_n = [c for c in self.lower_neighbors(*hop) if self.SM[c] != 0]
            lowest = lower_n[0] if lower_n else None
            print(lowest)
            if lowest is None:
                self.SM[hop] = 0
                warping_path = warping_path[:-1]
            if len(lower_n) > 1:
                for next_n in lower_n[1:]:
                    lowest = next_n if self.SM[lowest] > self.SM[next_n] else lowest
                
            else:
                pass
            print(np.matrix(self.SM))
            hop = lowest
            warping_path.append(hop)
            


        warp_path = []
        for coord in sorted(warping_path):
            warp_path.append((coord, self.SM[coord]))

        return warp_path

    def __call__(self, *args, **kwargs):
        self.populate_warp()
        self.calculate_warp_costs()

        return self.calculate_warp_path()

    def as_arr(self):
        return self.SM.toarray()


if __name__ == '__main__':
    if True:
        parser = argparse.ArgumentParser()
        parser.add_argument('series', nargs=2,
                            help='paths to two time series to time warp; input '
                                 'as file names; columns required. seperator is'
                                 ' tab, last column must be values')
        parser.add_argument('--resistance', '-r', required=False, default=0.5,
                            help='Resistance to use for calculation; defaults '
                                 'to 0.5')
        args = parser.parse_args()

        a = None
        b = None

        with open(args.series[0], 'r') as f:
            a = []
            for line in f:
                a.append(np.float64(line.split('\t')[-1]))

        with open(args.series[1], 'r') as f:
            b = []
            for line in f:
                b.append(np.float64(line.split('\t')[-1]))

        dtw = SparseDTW(a, b, res=args.resistance)
    else:
        a = [i for i in range(100)]
        b = [i for i in range(100)]
        dtw = SparseDTW(a, b)
    for coord, value in dtw():
        print(coord, '\t', value)




