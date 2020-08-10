import unittest
from r2g import utils
from r2g.online import fetch
from r2g import errors


class TestFetch(unittest.TestCase):
    def test_fastq_dump(self):
        utils.log("Testing r2g.online.fetch fastq_dump.")
        args = {
            'query': "ATGC",
            'verbose': False,
            'stage': 'butterfly'
        }
        app_json = utils.preflight(args)
        fastq = {
            '1':
                '@FCC2U5KACXX:6:1101:9243:74192/1\n'
                'CACGTCGTGCGCGTTTTCCGTGTTCCCTCTAGCAGACCTCAAGGTTTTGGATTTTTTTTTGTGTGCTCAGTGCCAAAGTTGCTGATTGTC\n'
                '+SRR1812889.232339 FCC2U5KACXX:6:1101:9243:74192 length=90\n'
                'BB@FFFFDHHHHHHIJJJJJGHHHGIJIJIHJJJIJJJIJHIIJAHIJIICHHHHHDDDD?BCDDCDDDDCDCDDACCCCDDDDDCDCCD\n',
            '2':
                '@FCC2U5KACXX:6:1101:9243:74192/2\n'
                'TCCGGGAATCCACAGCAGCTCAGCAATGCGGGATTTTCCACTGCCCGATAAAAACAAGTTCTACTACTGATGATTTTTCACTTTCAGCTA\n'
                '+SRR1812889.232339 FCC2U5KACXX:6:1101:9243:74192 length=90\n'
                'CCCFFFFFHHHHHJJJJJJJIJJIJJIJJJJJIIJJJJIGIIJJJJJHIHHHFFFFDECEEEEDEDDDDDDDEEFEDDDCDDDDDCCDDD\n'
        }
        log = "SRR1812889 232339-232339:\nb'Read 1 spots for SRR1812889\\nWritten 1 spots for SRR1812889\\n'----"
        utils.log("Testing fastq-dump.")
        fetched_fastq, fetched_log = fetch.fastq_dump('SRR1812889', 232339, 232339, app_json)
        self.assertEqual((fastq, log), (fetched_fastq, fetched_log))

    def test_fastq_dump_error(self):
        utils.log("Raising r2g.online.fetch fastq_dump error.")
        args = {
            'query': "ATGC",
            'verbose': False,
            'stage': 'butterfly'
        }
        app_json = utils.preflight(args)
        with self.assertRaises(errors.FetchError):
            _, _ = fetch.fastq_dump('SRR1812889', "X", "J", app_json)

    def test_parse_fastq_error(self):
        utils.log("Raising r2g.online.fetch _parse_fastq error.")
        check = []
        fake_fastqs = [
            "@a\nATGC\n+\nAAAA\n",
            "a\nATGC\n+\nAAAA\n",
            "@a/1\nATG\n+\nAAAA\n",
            "@a/1\nATGC\n\nAAAA\n",
            "@a/1\nATGC\n?\nAAAA\n",
            "@a/1\nATGC\n+\nAAAA\n",
        ]
        for seq in fake_fastqs:
            try:
                _ = fetch._parse_fastq(seq)
            except errors.FetchError:
                check.append(False)
            else:
                check.append(True)
        self.assertEqual(check, [False, False, False, False, False, True])


if __name__ == '__main__':
    unittest.main()
