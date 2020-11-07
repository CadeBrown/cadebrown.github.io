#!/usr/bin/env python3
''' timeplot.py - plot time performance

Takes a list of files


@author: Cade Brown <cade@cade.site>
'''

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import argparse
parser = argparse.ArgumentParser(description='Plot time performance')
parser.add_argument('files', nargs='+', help='list of files that contain performance data (each row should be "N: T"')
parser.add_argument('--title', help='the title', default=None)
parser.add_argument('--output', '-o', help='output file', default=None)
args = parser.parse_args()

# select backend
matplotlib.use("TkCairo")

np.random.seed(25)

# map of each file
data = {}
colors = [np.random.rand(3,) for i in range(len(args.files))]

# parse files
for f in args.files:
    name = f.split('/')[-1]
    name = name.split('.')[0]
    data[name] = {}
    with open(f, 'r') as fp:
        for l in map(lambda x: x.strip().split(), filter(lambda x: x, fp)):
            N, T = map(float, l)
            if N not in data[name]:
                data[name][N] = np.array([], np.float32)
            data[name][N] = np.append(data[name][N], T)

if args.title is None:
    args.title = ' vs '.join(data.keys())
plt.title(args.title)

plt.xlabel('Size (N)')
plt.ylabel('Time (s)')

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
