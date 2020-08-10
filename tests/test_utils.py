import unittest
from unittest import mock

import os
import tempfile
import json
from stat import S_IWUSR, S_IREAD, S_IRGRP, S_IROTH
from copy import deepcopy

import r2g
from r2g import utils
from r2g import errors


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.args = {
            'CPU': 4,
            'browser': None,
            'chrome_proxy': None,
            'cleanup': False,
            'cut': '80,50',
            'docker': False,
            'evalue': 0.001,
            'firefox_proxy': None,
            'max_memory': '4G',
            'max_num_seq': 1000,
            'min_contig_length': 150,
            'outdir': 'OUTPUT',
            'program': 'blastn',
            'proxy': None,
            'query': 'ATGC',
            'retry': float('inf'),
            'sra': 'SRXNNNNNN',
            'stage': 'butterfly',
            'trim': False,
            'verbose': False
        }
        self.config_files = [
            os.path.abspath(os.path.join(r2g.__path__[0], "path.json")),
            os.path.abspath(os.path.join(os.path.expanduser('~'), ".r2g.path.json"))
        ]
        self.path = deepcopy(os.environ['PATH'])
        self.app_json = utils.preflight(self.args)
        #self.app_json["chromedriver"] = os.environ.get("PRIVATE_WEBDRIVER", "http://127.0.0.1:4444/wd/hub")
        utils.log("app_json is {}".format(self.app_json))
        self.pwd = os.getcwd()

    def test_parse_args(self):
        utils.log("Testing r2g.utils.utils _parse_args")
        raw_args = "-o OUTPUT -s SRXNNNNNN -q ATGC --cut 80,50 -p blastn --CPU 4 --retry"
        raw_args = raw_args.split()
        parsed_args = utils.parse_arguments(raw_args)
        self.assertEqual(parsed_args, self.args)

    def test_check_sequences(self):
        utils.log("Testing r2g.utils.utils _check_sequences")
        query_file = tempfile.mkstemp(suffix=".fasta", prefix="r2g-test_tmp_", text=True)[-1]
        with open(query_file, 'w') as outf:
            # a fake fasta with a wrong character ("!")
            outf.write(">some_gene\nATGC!\n")
        self.args['query'] = query_file
        with self.assertRaises(errors.InputError):
            _ = utils.preflight(self.args)
        utils.delete_everything(query_file)

    def test_check_apps(self):
        utils.log("Testing r2g.utils.utils configure files.")
        changing_app_json = deepcopy(self.app_json)
        # SITUATION 1: apps are not in $PATH and config_files[0] is configured.
        os.environ['PATH'] = '/usr/bin'
        os.chmod(self.config_files[0], S_IWUSR | S_IREAD)
        with open(self.config_files[0], 'w') as outf:
            json.dump(self.app_json, outf, indent=4, separators=(',', ': '))
        parsed_app_json = utils.preflight(self.args)
        if parsed_app_json == self.app_json:
            assertion1 = True
        else:
            assertion1 = False
        # SITUATION 2: apps are not in $PATH, config_files[0] is not writable, and both two configs are not configured.
        # Trinity is not found:
        with open(self.config_files[0], 'w') as outf:
            changing_app_json["Trinity"] = "/"
            json.dump(changing_app_json, outf, indent=4, separators=(',', ': '))
        # make the config_files[0] readable only:
        os.chmod(self.config_files[0], S_IREAD | S_IRGRP | S_IROTH)
        # Trinity is not executable:
        with open(self.config_files[1], 'w') as outf:
            changing_app_json["Trinity"] = "{}/data".format(os.path.split(os.path.abspath(__file__))[0])
            json.dump(changing_app_json, outf, indent=4, separators=(',', ': '))
            os.chmod("{}/data/Trinity".format(os.path.split(os.path.abspath(__file__))[0]),
                     S_IREAD | S_IRGRP | S_IROTH)
        choose_yes = mock.Mock(return_value=True)
        trinity_dir = mock.Mock(return_value=self.app_json['Trinity'])
        fastq_dump_dir = mock.Mock(return_value=self.app_json['fastq-dump'])
        chromedriver_dir = mock.Mock(return_value=self.app_json['chromedriver'])
        utils._ask_yes_or_no = choose_yes
        utils._input_trinity_dir = trinity_dir
        utils._input_fastq_dump_dir = fastq_dump_dir
        utils._input_webdriver_dir = chromedriver_dir
        parsed_app_json = utils.preflight(self.args)
        with open(self.config_files[1], 'r') as inf:
            read_app_json = json.load(inf)
        if parsed_app_json == self.app_json and read_app_json == self.app_json:
            assertion2 = True
        else:
            assertion2 = False
        # Restore everything:
        os.environ['PATH'] = deepcopy(self.path)
        os.chmod(self.config_files[0], S_IWUSR | S_IREAD)
        utils.delete_everything(self.config_files[1])
        with open(self.config_files[0], 'w') as outf:
            outf.write("")
        utils.log("assertion 1 is {}".format(assertion1))
        utils.log("assertion 2 is {}".format(assertion2))
        self.assertTrue(assertion1 & assertion2)


if __name__ == '__main__':
    unittest.main()
