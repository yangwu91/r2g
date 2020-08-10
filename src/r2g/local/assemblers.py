import subprocess
import os
from shutil import copyfile, copytree

from r2g import utils
from r2g import errors


class Trinity:
    def __init__(self, args, app_json, fastq_list, paired):
        self.stamp = utils.stamp()
        self.output = os.path.join(args["outdir"], "trinity_output_{}".
                                   format(self.stamp))
        self.cmd = [
            app_json["Trinity"],
            "--seqType", "fq",
            "--max_memory", args["max_memory"],
            "--CPU", str(args['CPU']),
            "--min_contig_length", str(args["min_contig_length"]),
            # "--KMER_SIZE", str(args["KMER_SIZE"]), # Doesn't work on Trinity >2.6.6 or <2.10.0
            "--output", self.output
        ]
        if paired:
            self.cmd += ['--left', ','.join(fastq_list['1']),
                         '--right', ','.join(fastq_list['2'])]
        else:
            if len(fastq_list.keys()) == 1:
                files = ','.join(fastq_list['1'])
            elif len(fastq_list.keys()) == 2:
                files = ','.join(fastq_list['1'] + fastq_list['2'])
            self.cmd += ['--single', files]
        # The utils r2g script will take care of this:
        # if args['full_cleanup']:
        #    self.cmd.append("--full_cleanup")
        if args['trim'] is not False:
            if args['trim'] is None or args['trim'] is True:
                self.cmd.append("--trimmomatic")
            else:
                self.cmd += [
                    '--trimmomatic',
                    '--quality_trimming_params',
                    args['trim']
                ]
        if args['stage'] == 'jellyfish':
            self.cmd.append('--no_run_inchworm')
        elif args['stage'] == 'inchworm':
            self.cmd.append('--no_run_chrysalis')
        elif args['stage'] == 'chrysalis':
            self.cmd.append('--no_path_merging')
        elif args['stage'] == 'butterfly':
            pass
        self.log = "{}/run_trinity_{}.log".format(args['outdir'], self.stamp)
        self.args = args

    def run(self):
        utils.log("Trinity cmd: {}".format(' '.join(self.cmd)))
        utils.log("Trinity is running. Output dir: {}".format(self.output))
        utils.log("Trinity log file: {}".format(self.log))
        try:
            with subprocess.Popen(self.cmd,
                                  shell=False,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  # bufsize=1
                                  ) as p:
                if not self.args.get('cleanup', False):
                    with open(self.log, 'w') as outf:
                        for line in iter(p.stdout.readline, ''):
                            if len(line) == 0:
                                break
                            outf.write(utils.bytes2str(line))
                            if self.args['verbose']:
                                print(line)
                        # sys.stdout.write(line)
                p.wait()
                if p.returncode != 0:
                    raise errors.AssembleError(
                        "Trinity failed. Please check log files {} for more information.".format(self.log)
                    )
                else:
                    utils.log("Trinity done.")
                return self.output
        except Exception as err:
            raise errors.AssembleError("Errors raised when called Trinity. {}. "
                                       "Please check the Trinity log above".format(err))

    def copyto(self, final_result):
        if self.args['stage'] == 'chrysalis' or self.args['stage'] == 'butterfly':
            copyfile(os.path.join(self.output, "Trinity.fasta"), final_result)
        else:
            copytree(os.path.join(self.output), final_result)
