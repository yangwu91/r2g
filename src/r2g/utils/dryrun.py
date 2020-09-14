import argparse
import sys
import os
import subprocess
import tempfile

import r2g
from r2g import utils


class DryRunAction(argparse.Action):
    def __init__(self, option_strings, r2g_script, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        self.r2g_script = r2g_script
        super(DryRunAction, self).__init__(
            option_strings=option_strings, dest=dest, default=default, nargs=0, help=help
        )

    def __call__(self, parser, namespace, values, option_string=None):
        args = utils.file2json(os.path.join(r2g.__path__[0], "quick_test.json"))
        output_dir = tempfile.mkdtemp(prefix="r2g-dryrun_tmp_")
        cmd = [
            self.r2g_script,
            "-q", args['query'],
            "-s", args['sra'],
            "-o", output_dir,
            "-c", args['cut'],
            "-p", args['program'],
            "--verbose",
        ]
        try:
            webdriver_cmd = ["--browser", os.environ["PRIVATE_WEBDRIVER"]]
        except KeyError:
            webdriver_cmd = []
        cmd += webdriver_cmd
        err = ""
        try:
            p = subprocess.run(cmd, shell=False, timeout=600)
        except subprocess.TimeoutExpired as err:
            err += "\nThe quick test is supposed to finished in 10 minutes. Aborted."
            exit_code = 2
        except Exception as err:
            exit_code = 3
        else:
            exit_code = p.returncode
        if exit_code != 0:
            print(err)
            utils.log(
                "The quick test failed. Please check the error message above. "
                "Make sure the r2g was installed and configured correctly"
            )
        else:
            utils.log("The quick test done. Please feed me something real 😋")
        utils.delete_everything(output_dir)
        sys.exit(exit_code)
