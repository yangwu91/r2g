#!/usr/bin/env python

import subprocess
import re
import sys


def get_emapper_results(dir):
    emapper_results = subprocess.check_output([
        "find", dir,
        "-type", "f",
        "-name", "randomquery_*.emapper.seed_orthologs"
    ]).decode('utf-8').strip().split('\n')
    emapper_files = {}
    for filename in emapper_results:
        index = re.findall(r'randomquery_(\d{1,2}).emapper', filename)
        if len(index) > 0:
            index = int(index[0])
            emapper_files[index] = filename
    return emapper_files


if __name__ == "__main__":
    emapper_files = get_emapper_results(sys.argv[1])
    species = "7165"  # Anopheles gambiae
    outf = open("{}/summary_table_eggNOG.tsv".format(sys.argv[1]), 'w')
    outf.write("No.\tAn_stephensi_Indian_Gene\teggNOG_orthologs\n")
    for i in range(100):
        filename = emapper_files[i]
        with open(filename, 'r') as inf:
            orthologs = ["NA", "NA"]
            for line in inf:
                if line[0] != "#":
                    line = line.strip().split('\t')
                    line[1] = line[1].split('.')
                    if line[1][0] == species:
                        orthologs = [line[0], line[1][1]]
            outf.write("{}\t{}\t{}\n".format(str(i), orthologs[0], orthologs[1]))
    outf.close()
