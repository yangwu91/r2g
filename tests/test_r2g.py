#!/usr/bin/env python

import os
import unittest

from r2g import utils
from r2g.online import blast

aae_rps7 = """>AAEL009496-RA_RPS7
CCCCCATCGGACAGCTGTCAGTAAACGCAAACTCGCTCGAACTTCCGCCCAACTGTCTGT
GGTCGGCTGTTCTGTCAAAATTTGCTCCTTTCTCGCTCTTTTTCCGGGCATCTTTGATGT
GCGAGTGAACACATTTCACTGTGAACGTAAAATAAATTCGCTATGGTTTTCGGATCAAAG
GTGATCAAGGCCGGTGGCGCCGAGCCTGATGCTTTCGAGGGACAAATCGGCCAGGCTATC
CTGGAGTTGGAGATGAACTCGGACCTGAAGCCACAGCTGCGTGATCTGTACATCACCCGC
GCTCGTGAGATCGAGTTCAACAGCAAGAAGGCTATCGTGATCTACGTCCCGGTGCCCAAG
CAGAAGGCCTTCCAGAAGGTCCAAACCCGGCTGGTCCGTGAGCTGGAGAAGAAGTTCTCC
GGCAAGCACGTCGTGTTCATCGGCGAGCGTCGCATCCTGCCCAAGCCCCAGCGCGGCCGC
CGTGACCCCAACAAGCAGAAGCGTCCACGATCCCGCACTCTGACCGCCGTCTACGATGCC
ATCCTGGAGGATCTGGTCTTCCCGGCTGAAGTCGTCGGCAAGCGTATGCGCGTCAAGCTG
GACGGATCGCAGCTGATCAAGGTGCACCTGGACAAGAACCAGCAGACCACCATTGAACAC
AAGGTCGACACCTTCACGTCAGTGTACAAGAAGCTGACCGGACGTGACGTTACGTTCGAA
TTCCCGGAGCCCTACCTATAAACTATTACAACCAATAGTTGCTAGAAATTAATCTAATAA
GTGAGCGCGCGCGGAAGGTTGGTAAAACTGAAGAAAAAAAACTATGTACGGAACTAGGGT
GTGCATAAATCATCTTTGTGCTGCATCGTTCGCCCCCTTTAAATAAAGACCCTCACCAAA
CGGAGGGACAAGAACAGTTTACAGGTGTATTGGAAAACAATTTCTAA"""

args_dict = {
    'CPU': 4,
    'browser': None,
    'chrome_proxy': None,
    'cleanup': False,
    'cut': '50,20',
    'docker': False,
    'evalue': 0.001,
    'firefox_proxy': None,
    'max_memory': '4G',
    'max_num_seq': 1000,
    'min_contig_length': 150,
    'outdir': 'RPS7',
    'program': 'blastn',
    'proxy': None,
    'query': None,
    'retry': 5,
    'sra': 'SRX5138669',
    'stage': 'butterfly',
    'trim': False,
    'verbose': False
}


class TestR2g(unittest.TestCase):

    def test_utils_parse_argument(self):
        online_raw_args = "-o RPS7 -s SRX5138669 -q aae_RPS7.fa --cut 50,20 -r 5 --CPU 4".split()
        globals()['args_dict']['query'] = "aae_RPS7.fa"
        self.assertEqual(utils.parse_arguments(online_raw_args), globals()['args_dict'])

    def test_blast_query(self):
        globals()['args_dict']['query'] = globals()['aae_rps7']
        result = blast.query(globals()['args_dict'], os.environ["PRIVATE_WEBDRIVER"])
        print(result)
        self.assertTrue((result[0] == "AAEL009496-RA_RPS7") and ((148515, 148515) in result[1]["SRR8326954"]))


if __name__ == "__main__":
    unittest.main(verbosity=2, warnings='ignore')
