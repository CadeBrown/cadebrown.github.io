#!/usr/bin/env python3
''' timeplot-g3d.py - plot time performance over a 3D grid


@author: Cade Brown <cade@cade.site>
'''

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as anim
from mpl_toolkits.mplot3d import Axes3D
import mpl_toolkits.mplot3d.axes3d as p3

import argparse
parser = argparse.ArgumentParser(description='Plot time performance')
parser.add_argument('files', nargs=1, help='list of files that contain performance data (each row should be "I J N T"')
parser.add_argument('--title', help='the title', default=None)
parser.add_argument('--output', '-o', help='output file', default=None)
args = parser.parse_args()

# select backend
matplotlib.use("TkCairo")

np.random.seed(25)

# key: N, data: (i, j, t) tuples
data = {}
colors = [np.random.rand(3,) for i in range(len(args.files))]

# parse files
for f in args.files:
    name = f.split('/')[-1]
    name = name.split('.')[0]
    with open(f, 'r') as fp:
        for l in map(lambda x: x.strip().split(), filter(lambda x: x, fp)):
            I, J, N, T = map(float, l)
            if N not in data:
                data[N] = np.array([], np.float32)
            data[N] = np.append(data[N], (I, J, T))

#plt.xlabel('Rows (BLK_I)')
#plt.xlabel('Cols (BLK_I)')
#plt.ylabel('Time (s)')

fig = plt.figure()
ax = fig.gca(projection='3d')

ax.set_xlabel('Rows (BLK_I)')
ax.set_ylabel('Cols (BLK_I)')
ax.set_zlabel('Time (s)')

data = {k: data[k] for k in (128, 256, 384, 512)}


#ax.plot(Rx, Ry, Rz, label='Performance of blocked GEMM')
for N, dat in data.items():
    surf = ax.plot_trisurf(dat[0::3], dat[1::3], dat[2::3], label='N=' + str(int(N)))
    surf._facecolors2d=surf._facecolors3d
    surf._edgecolors2d=surf._edgecolors3d
ax.legend()


plt.show()

'''
if args.title is None:
    args.title = ' vs '.join(data.keys())
plt.title(args.title)


plots = []

# plot data
for i, (name, d) in enumerate(data.items()):
    x = []
    y = []
    err = []
    for N, Ts in d.items():
        x += [N]
        y += [np.average(Ts)]
        err += [np.std(y)]
    plot, = plt.plot(x, y, c=colors[i], marker='o')
    plots += [plot]
    plt.errorbar(x, y, yerr=err, c=colors[i], fmt='.k', capsize=2.5, elinewidth=1.5)

plt.legend(plots, data.keys())


# show plot
if args.output:
    plt.savefig(args.output)
else:
    plt.show()

'''