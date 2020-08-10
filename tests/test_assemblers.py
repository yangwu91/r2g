import unittest
import tempfile
import os
import shutil
from r2g import utils
from r2g.local import assemblers


class TestAssemblers(unittest.TestCase):
    def setUp(self):
        self.assertion = False
        self.fastq_dir = os.path.split(os.path.abspath(__file__))[0]
        self.output_dir = tempfile.mkdtemp(prefix="r2g-test_tmp_")
        self.args = {
                'query': "ATGC",
                'verbose': True,
                'outdir': self.output_dir,
                'CPU': 2,
                'max_memory': '4G',
                'min_contig_length': 150,
                # 'KMER_SIZE': 25,
                'full_cleanup': False,
                'trim': False,
                'stage': 'butterfly',
            }
        self.fastq_list = {
                "1": ['{}/data/sample1_1.fastq.gz'.format(self.fastq_dir),
                      '{}/data/sample2_1.fastq.gz'.format(self.fastq_dir)],
                "2": ['{}/data/sample1_2.fastq.gz'.format(self.fastq_dir),
                      '{}/data/sample2_2.fastq.gz'.format(self.fastq_dir)]
        }

    def test_trinity_paired(self):
        paired = True
        app_json = utils.preflight(self.args)
        trinity = assemblers.Trinity(self.args, app_json, self.fastq_list, paired)
        trinity_dir = trinity.run()
        result = "{}/Trinity.fasta".format(trinity_dir)
        if os.path.isfile(result):
            trinity.copyto("{}/final_assembly.fasta".format(self.output_dir))
            if os.stat("{}/final_assembly.fasta".format(self.output_dir)).st_size > 1000:
                self.assertion = True
        self.assertTrue(self.assertion)

    def test_trinity_singled_trimmed(self):
        paired = False
        # self.args["verbose"] = True
        # self.args['full_cleanup'] = True
        self.args['trim'] = True
        app_json = utils.preflight(self.args)
        trinity = assemblers.Trinity(self.args, app_json, self.fastq_list, paired)
        trinity_dir = trinity.run()
        # result = "{}/{}.Trinity.fasta".format(self.output_dir, os.path.split(trinity_dir)[1])
        result = "{}/{}/Trinity.fasta".format(self.output_dir, os.path.split(trinity_dir)[1])
        if os.path.isfile(result) and os.stat(result).st_size > 1000:
            self.assertion = True
        self.assertTrue(self.assertion)

    def test_trinity_customtrimmed(self):
        paired = False
        # self.args["verbose"] = True
        # self.args['full_cleanup'] = True
        self.args['trim'] = "SLIDINGWINDOW:4:5 LEADING:5 TRAILING:5 MINLEN:25"
        del self.fastq_list['2']
        app_json = utils.preflight(self.args)
        trinity = assemblers.Trinity(self.args, app_json, self.fastq_list, paired)
        trinity_dir = trinity.run()
        result = "{}/{}/Trinity.fasta".format(self.output_dir, os.path.split(trinity_dir)[1])
        print(result)
        print(os.stat(result).st_size)
        if os.path.isfile(result) and os.stat(result).st_size > 1000:
            self.assertion = True
        self.assertTrue(self.assertion)

    def test_trinity_stage(self):
        paired = True
        for stage in ['jellyfish', 'inchworm', 'chrysalis']:
            stamp = utils.stamp()
            self.args['stage'] = stage
            app_json = utils.preflight(self.args)
            trinity = assemblers.Trinity(self.args, app_json, self.fastq_list, paired)
            trinity_dir = trinity.run()
            if stage == "jellyfish":
                result = "{}/jellyfish.kmers.fa".format(trinity_dir)
            elif stage == "inchworm":
                result = "{}/inchworm.K25.L25.DS.fa".format(trinity_dir)
            elif stage == "chrysalis":
                result = "{}/Trinity.fasta".format(trinity_dir)
            if os.path.isfile(result) and os.stat(result).st_size > 1000:
                trinity.copyto("{}/final_results-{}".format(self.output_dir, stamp))
                self.assertion = True
            else:
                self.assertion = False
                break
        self.assertTrue(self.assertion)

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
