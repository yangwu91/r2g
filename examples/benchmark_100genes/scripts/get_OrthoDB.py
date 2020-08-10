#!/usr/bin/env python

import requests
import json
import sys
import time


def fetch_vb_faa(species, trx_id):
    # For test:
    # trx_id = "ASTE009131-RA"
    # species = "Anopheles_stephensi"
    url = "https://www.vectorbase.org/{}/Export/Output/Transcript".format(species)
    gene_id = trx_id.split('-')[0]
    params = {
        "db": "core",
        "flank3_display": "0",
        "flank5_display": "0",
        "output": "fasta",
        "strand": "feature",
        "param": "peptide",
        "genomic": "unmasked",
        "_format": "Text",
        "g": gene_id,
        "t": trx_id
    }
    VB_request = requests.get(url, params=params)
    if VB_request.status_code == 200:
        trx_faa = "".join(VB_request.text.split("\r\n>")[0].strip('\r\n').split('\r\n')[1:])
    else:
        raise IOError("Error occurred while getting {} sequences from VectorBase.".format(trx_id))
    return trx_faa


def get_orthodb_intprot_id(faa, level):
    orthodb_levels = {
        "Anopheles": "7164",
        "Culicidae": "7157",
        "Nematocera": "7148",
        "Diptera": "7147",
        "Holometabola": "33392",
        "Insecta": "50557",
        "Hexapada": "6960",
        "Arthropada": "6656",
        "Metazoa": "33208"
    }
    url = "https://www.orthodb.org/tab"
    params = {
        "level": orthodb_levels.get(level),
        "species": "7165",  # Anopheles gambiae
        "seq": faa[:999]  # OrthoDB requires sequence length < 1000 bp
    }
    retry = 0
    while True:
        orthodb_request = requests.get(url, params=params)
        if orthodb_request.status_code == 200 or retry > 5:
            break
        time.sleep(1.1)
        retry += 1
    if orthodb_request.status_code != 200:
        results = "Error {}".format(str(orthodb_request.status_code))
    else:
        try:
            results = str(json.loads(orthodb_request.text).get("message"))
        except json.decoder.JSONDecodeError:
            orthodb_tsv = [line.split('\t') for line in orthodb_request.text.strip('\n').split('\n')]
            results = [l[5] for l in orthodb_tsv[1:]]
    return results


def get_orthodb_ogdetails(intprot_id):
    url = "https://www.orthodb.org/ogdetails"
    params = {
        "id": intprot_id
    }
    retry = 0
    while True:
        orthodb_request = requests.get(url, params=params)
        if orthodb_request.status_code == 200 or retry > 5:
            break
        time.sleep(10)
        retry += 1
    if orthodb_request.status_code != 200:
        results = "Error {}".format(str(orthodb_request.status_code))
    else:
        try:
            ensembls = json.loads(orthodb_request.text).get("data", {}).get("ensembl", [])
        except AttributeError:
            ensembls = []
        results = [e.get("id", "null") for e in ensembls]
    return results


def merge_results(orthodb_results):
    merged = ";".join([",".join(i) for i in orthodb_results])
    return merged


if __name__ == "__main__":
    species = "Anopheles_stephensi_indian"
    level = "Insecta"
    summary_table = open(sys.argv[1], 'r').read().strip().split('\n')[1:]
    outf = open("{}.OrthoDB.tsv".format(sys.argv[1]), 'w')
    outf.write("# OrthoDB level: {}\n".format(level))
    outf.write("No.\tAn_stephensi_Indian_Gene\tAn_gambiae_OrthoDB\n")
    for line in summary_table:
        line = line.split('\t')
        print(line[0])
        trx_faa = fetch_vb_faa(species, line[1])
        if len(trx_faa) > 0:
            inprots = get_orthodb_intprot_id(trx_faa, level)
            if type(inprots) == list and len(inprots) > 0:
                orthodb_results = merge_results([get_orthodb_ogdetails(i) for i in inprots])
            else:
                orthodb_results = "Orthologs not found. Msg from OrthoDB: {}".format(inprots)
        else:
            orthodb_results = "Peptide sequences not found."
        outf.write("{}\t{}\t{}\n".format(line[0], line[1], orthodb_results))
    outf.close()
