#!/usr/bin/env python

from __future__ import division
import subprocess
from r2g.Bio import NCBIWWW
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import sys


def find_r2g_results(dir):
    results = subprocess.check_output([
        "find", dir,
        "-maxdepth", "1",
        "-name", "*.homologs.*.fasta"
    ]).decode("utf-8").strip('\n').split('\n')
    return results


def blast(fasta, species):
    sequence = open(fasta, 'r').read()
    results_xml = NCBIWWW.qblast(
        program="blastn",
        database="nr",
        sequence=sequence,
        organisms=species,
        expect="1e-10",
        megablast=True,
        format_type='XML'
    ).read()
    return results_xml


def parse_xml(results_xml):
    results_tree = ET.fromstring(results_xml)
    highest_score = 0
    parsed_results = ['NoHit', 'NA', 'NA', 'NA', 'NA', 'NA', 'NA']
    for hit in results_tree.iter('Hit'):
        for hsp in hit.iter('Hsp'):
            score = float(hsp.find("Hsp_bit-score").text.strip())
            if score > highest_score:
                highest_score = score
                hit_id = hit.find('Hit_id').text.strip()
                hit_def = hit.find('Hit_def').text.strip()
                db_len = int(hit.find('Hit_len').text.strip())
                align_len = int(hsp.find('Hsp_align-len').text.strip())
                idt_len = int(hsp.find('Hsp_identity').text.strip())
                gap_len = int(hsp.find('Hsp_gaps').text.strip())
                eval = hsp.find('Hsp_evalue').text.strip()
                parsed_results = [
                    hit_id,
                    hit_def,
                    "{}/{} ({}%)".format(align_len, db_len, str(round(align_len/db_len*100, 2))),    # Coverage
                    "{}/{} ({}%)".format(idt_len, align_len, str(round(idt_len/align_len*100, 2))),  # Identity
                    "{}/{} ({}%)".format(gap_len, align_len, str(round(gap_len/align_len*100, 2))),  # Gap
                    eval,
                    str(highest_score)
                ]
    return parsed_results


if __name__ == "__main__":
    db_species = "Anopheles gambiae PEST (taxid:180454)"
    wd = sys.argv[1]
    summary_tsv = open("{}/summary_table.tsv".format(wd), 'r').read().strip().split('\n')
    blast_result = open("{}/summary_BLAST_results.tsv".format(wd), 'w')
    annotation = "# WD: {}\n# BLAST against: {}\n".format(wd, db_species)
    header = "No.\tGene\tGeneLen\tr2g_results\tHit_ID\tHit_descriptions\tCoverage\tIdentity\tGap\te-value\tBit_score\n"
    blast_result.write(annotation + header)
    for line in summary_tsv[1:]:
        line = line.strip().split('\t')
        print(line[0])
        if line[5] == "SUCCESS":
            query_fasta = find_r2g_results(line[6])[0]
            blast_xml = blast(query_fasta, db_species)
            parsed_result = parse_xml(blast_xml)
            outline = '\t'.join(line[:3] + [query_fasta, ] + parsed_result) + '\n'
        elif line[5] == "FAILED":
            outline = '\t'.join(line[:3]) + 'FAILED\tNA\tNA\tNA\tNA\tNA\tNA\tNA\n'
        blast_result.write(outline)
    blast_result.close()