#!/usr/bin/env python

import requests
import sys
import time
from copy import deepcopy
from bs4 import BeautifulSoup
import re


def get_mapping_list():
    url = "https://www.vectorbase.org/sites/default/files/ftp/downloads/" \
          "Anopheles_stephensi_MAPPINGS_AsteS1.2_AsteI2.2.txt"
    mapping_lst = requests.get(url).text.strip().split('\n')[1:]
    mapping = {}
    for line in mapping_lst:
        line = line.split('\t')
        SDS500 = line[3].split(',')
        India = line[6].split(',')
        for I in India:
            mapped_SDS = deepcopy(mapping.get(I, []))
            mapped_SDS += SDS500
            mapping[I] = deepcopy(mapped_SDS)
    return mapping


def get_VB_ortholog(species, trx_id):
    gene_id = trx_id.split('-')[0]
    url = "https://www.vectorbase.org/{}/Component/Gene/Compara_Ortholog/orthologues".format(species)
    headers = {
        "Host": "www.vectorbase.org",
        "Connection": "keep-alive",
        "Accept": "text/html, */*; q = 0.01",
        "DNT": "1",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/77.0.3865.75 Safari/537.36",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://www.vectorbase.org/{}/Gene/Compara_Ortholog?db=core;g={};t={}".format(
            species, gene_id, trx_id
        ),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
    }
    params = {
        "db": "core",
        "g": gene_id,
        "t": trx_id,
        "time": "%.3f" % time.time()
    }
    VB_request = requests.get(url, params=params, headers=headers)
    if VB_request.status_code == 200:
        d = {}
        try:
            table = BeautifulSoup(VB_request.content, "lxml").select('table')[1]
        except IndexError:
            d = {}
        else:
            ths = table.select('th')
            tds = table.select('td')
            for i in range(int(len(tds)/len(ths))):
                row = tds[i*len(ths):(i+1)*len(ths)]
                key = row[0].text.replace("\xa0", " ")
                values = d.get(key, [])
                values += row
                d[key] = values
        return d
    else:
        raise IOError("Error occurred while getting orthologs of {} from VectorBase.".format(trx_id))


def parse_VB_ortholog(VB_dict, species):
    result_soup = VB_dict.get(species, None)
    if result_soup:
        details = result_soup[2].select('p')[:2]
        details = [p.text.replace("\xa0\xa0", " ") for p in details]
    else:
        details = []
    return details


def find_An_gambaie_pest_gene_id(text):
    an_gambiae_pest_pattern = re.compile(r"AGAP\d+")
    gene_id = re.search(an_gambiae_pest_pattern, text)
    if gene_id:
        return gene_id.group()
    else:
        return text


if __name__ == "__main__":
    summary_table = open(sys.argv[1], 'r').read().strip().split('\n')[1:]
    outf = open("{}.Vectorbase.tsv".format(sys.argv[1]), 'w')
    outf.write("No.\tAn_stephensi_Indian_Gene\tAn_gambiae_VB\tDescription\n")
    mapping = get_mapping_list()
    for line in summary_table:
        line = line.split('\t')
        print(line[0])
        SDS = mapping.get(line[1], None)
        outline = [[], []]
        if SDS:
            for g in SDS:
                orthologs_soup = get_VB_ortholog("Anopheles_stephensi", g)
                if len(orthologs_soup) > 0:
                    results = parse_VB_ortholog(orthologs_soup, "Anopheles gambiae")
                    if len(results) > 1:
                        outline[0].append(find_An_gambaie_pest_gene_id(results[0]))
                        outline[1].append(results[1])
        if len(outline[0]) == 0 and len(outline[1]) == 0:
            outline = [["NA"], ["NA"]]
        outline = [','.join(x) for x in outline]
        outf.write("\t".join(line[:2] + outline) + '\n')
        time.sleep(1)