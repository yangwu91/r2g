#!/usr/bin/env python
"""
For benchmark use:
Randomly pick 100 genes from Species 1, and call r2g to find homologues of these 100 genes in Species 2.
"""

import sys
import random
import subprocess


def random_pick(fasta_file):
    num_picked = 100
    with open(fasta_file, 'r') as inf:
        picked = random.sample(inf.read().rstrip('\n').lstrip('>').split('\n>'), k=num_picked)
    return picked


sp1 = sys.argv[1]
sp2 = sys.argv[2]
sp1_picked = random_pick(sp1)

r2g_cmd = [
    "r2g",
    "-s", sp2,
    "-c", "90,50",
    "-r", "5",
    "-p", "tblastx",
]

i = 0
for query in sp1_picked:
    query = ">" + query
    output_dir = "./" + str(i)
    r2g_cmd = r2g_cmd + ["-q", query, "-o", output_dir]
    subprocess.check_call(r2g_cmd)
    i += 1
