from __future__ import print_function

import unittest
import tempfile
import json
import shutil
import os

from r2g import utils
from r2g.online import blast
from r2g import errors


class TestBlast(unittest.TestCase):
    def setUp(self):
        self.query_fasta = ">some_gene 1\n" \
                           "AATCATTCCATTGATTAGACGATGGTTACACTTGGTTCACGTCGTGCGCGTTTCCCGTGT\n" \
                           "TCCCTCTAGACGTAGAAGTGTTGGACTTTTTTTTTTGGGTGTTGTGCTGCTATAAGCTGC\n" \
                           "TACTGCTGATTGAGGAAATT\n"
        self.args = {
            'query': self.query_fasta,
            'sra': 'SRX885420',
            'program': 'blastn',
            'outdir': tempfile.mkdtemp(prefix="r2g-test_tmp_"),
            'cut': '80,50',
            'max_num_seq': 1000,
            'evalue': 0.001,
            'verbose': True,
            'retry': 5,
            'proxy': None,
            'chrome_proxy': None,
            'firefox_proxy': None,
            'browser': None,
        }

    def test_query_cut_error_1(self):
        utils.log("Raising r2g.online.blast query Error 1.")
        self.args["cut"] = "7,31"
        with self.assertRaises(errors.InputError):
            _, _ = blast.query(self.args, "http://127.0.0.1:4444/wd/hub")

    def test_query_cut_error_2(self):
        utils.log("Raising r2g.online.blast query Error 2.")
        self.args["cut"] = "X,J"
        with self.assertRaises(errors.InputError):
            _, _ = blast.query(self.args, "http://127.0.0.1:4444/wd/hub")

    def test_query(self):
        utils.log("Testing r2g.online.blast query.")
        try:
            name, download_list = blast.query(self.args, os.environ["PRIVATE_WEBDRIVER"])
            assertion = (name == 'some_gene' and len(download_list.get('SRR1812889', [])) > 0)
        except Exception as err:
            assertion = False
            utils.log("Error occurred while testing: {}".format(err))
        self.assertTrue(assertion)

    def test_format_seq_1(self):
        # Test 1 (total_length = 169, num_frag = 3):
        utils.log("Testing r2g.online.blast _format_seq 1.")
        self.query_fasta = self.query_fasta.strip().split('\n', 1)[1] + 29 * "A"
        self.args['query'] = self.query_fasta
        name, seq = blast._format_seq(self.args)
        formatted_name = "Undefined"
        formatted_seq = [
            ">Undefined_0\nAATCATTCCATTGATTAGACGATGGTTACACTTGGTTCACGTCGTGCGCGTTTCCCGTGTTCCCTCTAGACGTAGAAGTG\n"
            ">Undefined_1\nCTTGGTTCACGTCGTGCGCGTTTCCCGTGTTCCCTCTAGACGTAGAAGTGTTGGACTTTTTTTTTTGGGTGTTGTGCTGC\n"
            ">Undefined_2\nTCCCTCTAGACGTAGAAGTGTTGGACTTTTTTTTTTGGGTGTTGTGCTGCTATAAGCTGCTACTGCTGATTGAGGAAATT"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        ]
        if name == formatted_name and seq == formatted_seq:
            assertion = True
        else:
            print(name)
            print(seq)
            assertion = False
        self.assertTrue(assertion)

    def test_format_seq_2(self):
        # Test 2:
        utils.log("Testing r2g.online.blast _format_seq 2.")
        query_file = tempfile.mkstemp(suffix=".fasta", prefix="r2g-test_tmp_", text=True)[-1]
        fasta = ">{}\n{}\n>{}\n{}\n".format(
            "A",
            self.query_fasta.strip().split('\n', 1)[1],
            "B",
            self.query_fasta.strip().split('\n', 1)[1]
        )
        with open(query_file, 'w') as outf:
            outf.write(fasta)
        self.args['query'] = query_file
        self.args['cut'] = "24,20"
        name, seq = blast._format_seq(self.args)
        formatted_name = "A_B"
        with open('{}/data/formatted_seq.json'.format(os.path.split(os.path.abspath(__file__))[0]), 'r') as inf:
            formatted_seq = json.loads(inf.read().strip())
        if name == formatted_name and seq == formatted_seq:
            assertion = True
        else:
            print(name)
            print(seq)
            assertion = False
        shutil.rmtree(query_file, ignore_errors=True)
        self.assertTrue(assertion)

    def test_parse_xml(self):
        utils.log("Testing r2g.online.blast _parse_xml.")
        xml_dir = "{}/data".format(os.path.split(os.path.abspath(__file__))[0])
        xml_files = [
            "{}/no_result.xml".format(xml_dir),
            "{}/other_result.xml".format(xml_dir),
            "{}/standard_result.xml".format(xml_dir),
            # "{}/error_result.xml".format(xml_dir)
        ]
        parsed_results = [
            {},
            {},
            {'SRR1812889': [25821753]}
        ]
        for i in range(len(xml_files)):
            with open(xml_files[i], 'r') as inf:
                download_list = blast._parse_xml(inf.read(), self.args)
                if download_list == parsed_results[i]:
                    assertion = True
                else:
                    assertion = False
                    utils.log("Error occured while parsing {}".format(xml_files[i]))
                    break
        self.assertTrue(assertion)

    def tearDown(self):
        shutil.rmtree(self.args['outdir'], ignore_errors=True)


if __name__ == '__main__':
    unittest.main(warnings='ignore')
