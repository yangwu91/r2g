from __future__ import print_function
from __future__ import division

import argparse
import json
import os
import sys
import platform
import subprocess
import time
import shutil
import re
from copy import deepcopy
from multiprocessing import cpu_count

import r2g
from r2g import errors


def log(info, verbose=False, attr='info', shift=""):
    if attr == 'debug' and verbose is False:
        pass
    else:
        # time in grey color
        print("{}\033[1;37m[{}]\033[0m {}".format(
            shift,
            time.strftime("%m-%d-%Y %H:%M:%S", time.localtime()),
            info)
        )


def stamp():
    return time.strftime("%m%d%y%H%M%S", time.localtime())


def bytes2str(b):
    """In Python 3, subprocess.check_output will return a bytes class."""
    return str(b.decode("utf-8"))


def delete_everything(items):
    if type(items) not in (list, tuple):
        items = [items, ]
    for item in items:
        try:
            shutil.rmtree(item)
        # except shutil.NotADirectoryError:
        except Exception:
            os.remove(item)


def file2json(f):
    with open(f, 'r') as inf:
        return json.loads(inf.read())


def processing(current, total, info, mode="fraction"):
    if str(current) != str(total):
        end_chr = ""
    else:
        end_chr = "\n"
    if mode == "percent":
        process = "{}%".format(round(current / total * 100, 1))
    else:
        process = "{}/{}".format(current, total)
    print("\r[{}] {}: {}".format(
        time.strftime("%m-%d-%Y %H:%M:%S", time.localtime()),
        info,
        process
    ), end=end_chr),
    sys.stdout.flush()


def parse_arguments(raw_args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--version",
                        help="Print the version.",
                        action="version",
                        version="{} ({}) Version {}".format(r2g.__title__, r2g.__full_name__, r2g.__version__))
    parser.add_argument("-v", "--verbose",
                        help="Print detailed log.",
                        action="store_true",
                        default=False)
    parser.add_argument("-r", "--retry",
                        help="Number of times to retry."
                             "Enabling it without any numbers will force it to keep retrying. Default: 5.",
                        metavar="INT",
                        nargs="?",
                        default="5"
                        )
    parser.add_argument('--cleanup',
                        action="store_true",
                        help="Clean up all intermediate files "
                             "and only retain the final assembled contig file in FASTA format."
                        )
    parser.add_argument("-o", "--outdir",
                        help="Specify an output directory. Default: {}".format(os.getcwd()),
                        metavar="DIR",
                        default=os.getcwd()
                        )
    parser.add_argument("-W", "--browser",
                        help="Temporarily overwrite the local path or the remote address of the chrome webdriver. "
                             "E.g., /path/to/chromedriver or http://127.0.0.1:4444/wd/hub",
                        default=None,
                        metavar="DIR"
                        )
    parser.add_argument("-P", "--proxy",
                        help="Set up proxies. Http and socks are allowed, "
                             "but authentication is not supported yet (still testing).",
                        metavar='SCHEME://IP:PORT',
                        default=None
                        )
    # 1. Online mode:
    # 1.1 NCBI options:
    ncbi = parser.add_argument_group("NCBI options")
    ncbi.add_argument("-s", "--sra",
                      help='Choose SRA accessions (comma-separated without blank space). '
                           'E.g., "SRX885418" (an SRA experiment) or "SRR1812886,SRR1812887" (SRA runs)',
                      required=True,
                      metavar="SRA"
                      )
    ncbi.add_argument("-q", "--query",
                      help="Submit either a FASTA file or nucleotide sequences.",
                      required=True,
                      metavar="SEQUENCE"
                      )
    ncbi.add_argument("-p", "--program",
                      help="Specify a BLAST program: tblastn, tblastx, or "
                           "blastn (including megablast, blastn, and discomegablast). Default: blastn.",
                      choices=["megablast", "blastn", "discomegablast", "tblastn", "tblastx"],
                      default="blastn",
                      metavar="BLAST"
                      )
    ncbi.add_argument("-m", "--max_num_seq",
                      help="Maximum number of aligned sequences to retrieve "
                           "(the actual number of alignments may be greater than this). Default: 1000.",
                      type=int,
                      default="1000",
                      metavar="INT"
                      )
    ncbi.add_argument("-e", "--evalue",
                      default=1e-3,
                      help="Expected number of chance matches in a random model. Default: 1e-3.",
                      metavar="FLOAT"
                      )
    ncbi.add_argument("-c", "--cut",
                      help="Cut sequences and query them respectively to prevent weaker matches from being ignored. "
                           "Default: 70,20 (nucleotides), or 24,7 (amino acids)",
                      default=None,
                      metavar="FRAGMENT,OVERLAP"
                      )
    # 1.2 Trinity options:
    trinity = parser.add_argument_group("Trinity options")
    trinity.add_argument("-t", "--CPU",
                         help="Number of CPU threads to use. Default: {}.".format(cpu_count()),
                         default=cpu_count(),
                         type=int,
                         metavar="INT"
                         )
    trinity.add_argument("--max_memory",
                         help='Suggest max Gb of memory to use by Trinity. Default: 4G.',
                         type=str.upper,
                         metavar="RAM",
                         default="4G"
                         )
    trinity.add_argument("--min_contig_length",
                         help="Minimum assembled contig length to report. Default: 150.",
                         default=150,
                         type=int,
                         metavar="INT"
                         )
    # Doesn't work in Trinity >2.6.6 or <1.10.0:
    # trinity.add_argument("-k", "--KMER_SIZE",
    #                      help="K-mer size for Trinity, maximum: 32, default: 25.",
    #                      default=25,
    #                      type=int,
    #                      metavar="INT"
    #                      )
    trinity.add_argument("--trim",
                         help="Run Trimmomatic to qualify and trim reads. "
                              "Using this option without any parameters will trigger preset settings in Trinity for "
                              "Trimmomatic. See Trinity for more help. Default: disabled.",
                         nargs="?",
                         default=False,
                         metavar="TRIM_PARAM"
                         )
    trinity.add_argument("--stage",
                         help="Stop Trinity after the stage you chose. Default: butterfly (the final stage).",
                         choices=["no_trinity", "jellyfish", "inchworm", "chrysalis", "butterfly"],
                         default="butterfly",
                         type=str.lower
                         )
    # TODO:
    # 2. Local mode:
    #    local = subparser.add_parser("local")
    #    local.add_argument("-q", "--query",
    #                       help="Submit either a FASTA file or nucleotide sequences.",
    #                       required=True,
    #                       metavar="SEQUENCE")
    #    local.add_argument("-o", "--outdir",
    #                       help="Specify an output directory.",
    #                       metavar="DIR",
    #                       default=os.getcwd())
    #
    #    # 2.1 Aligner:
    #    aligner = local.add_argument_group("Aligner options")
    #    aligner.add_argument("--aligner",
    #                         help="Choose a program to align sequences, default: blastx",
    #                         default="blastx",
    #                         type=str.lower)
    # End of TODO

    args_dict = vars(parser.parse_args(raw_args))  # dict
    try:
        args_dict['retry'] = int(args_dict['retry'])
    except TypeError:
        args_dict['retry'] = float('inf')
    # Detect if it is in a docker:
    try:
        _ = re.search(r'docker', bytes2str(subprocess.check_output(["cat", "/proc/self/cgroup"]))).group()
    except Exception:
        args_dict['docker'] = False
        # The options "--proxy" and "--browser" are valid only if not in a docker:
        # format proxies:
        if args_dict['proxy'] is not None:
            args_dict['proxy'] = args_dict['proxy'].strip('"').strip("'")
            try:
                scheme = re.search(r'([\w\d]+)://\d{1,3}\.', args_dict['proxy']).group(1)
            except AttributeError:
                scheme = 'http'
            else:
                if scheme not in ['http', 'socks5', 'socks4']:
                    raise errors.InputError('Only http, socks5 and socks4 are supported proxy protocols. '
                                            'Your input proxy is {}'.format(scheme))
            try:
                address = re.search(r'(\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}:\d+)', args_dict['proxy']).group(1)
            except AttributeError:
                raise errors.InputError('Your input proxy address "{}" is not correct. '
                                        'The format should be scheme://ip:port.'.format(args_dict['proxy']))
            # this is specific format for the firefox webdriver:
            args_dict['chrome_proxy'] = deepcopy(args_dict['proxy'])
            # this is specific format for the firefox webdriver:
            args_dict['firefox_proxy'] = (scheme, address)
            # this is the general format:
            args_dict['proxy'] = {
                "http": args_dict['proxy'],
                "https": args_dict['proxy']
            }
        else:
            args_dict['chrome_proxy'] = None
            args_dict['firefox_proxy'] = None
    else:
        args_dict['proxy'] = None
        args_dict['chrome_proxy'] = None
        args_dict['firefox_proxy'] = None
        args_dict['docker'] = True

    # set up default values for --cut:
    if args_dict['cut'] is None:
        # The query is nuleotides:
        if args_dict['program'] in ["megablast", "blastn", "discomegablast"]:
            args_dict['cut'] = "70,20"
        elif args_dict['program'] in ["tblastn", "tblastx"]:
            args_dict['cut'] = "24,7"
    else:
        cut = args_dict["cut"].split(',')
        try:
            frag, ovlp = int(cut[0]), int(cut[-1])
        except (ValueError, IndexError):
            raise errors.InputError("The option --cut must be followed by two integers separated by a comma.")
        if args_dict['program'] in ["tblastn", "tblastx"] and frag > 50:
            # raise a warning when input sequences are amino acids but fragment is too high:
            log('\033[1;33mWARNING:\033[0m input query sequences are supposed to be amino acids '
                'but the parameter "fragment" from the option "--cut"/"-c" was set too high.'
                'R2g will proceed anyway but some weak BLAST hits may be ignored due to the settings')
    return args_dict


def _ask_yes_or_no(hint):
    choice = input(hint).strip().upper()
    if choice in ['', "Y", "YES"]:
        choice = True
    else:
        choice = False
    return choice


# To use unittest.mock:
def _input_trinity_dir():
    return input("Input the directory of Trinity: ")


# To use unittest.mock:
def _input_fastq_dump_dir():
    return input("Input the directory of fastq-dump: ")


def _input_webdriver_dir():
    return input("Input the local directory or the remote address (ip:port) of webdriver: ")


def preflight(args):
    """Pre-flight check and configure"""

    def _check_app(path, app):
        """Check if the app exists and is executable"""
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isfile(path) and os.access(path, os.X_OK):
            path_app = path
        elif os.path.isdir(path):
            path_app = os.path.join(path, app)
            if not (os.path.isfile(path_app) and os.access(path_app, os.X_OK)):
                path_app = False
        else:
            path_app = False
        if path_app is False and app == "chromedriver":
            try:
                # Supposed to be a remote webdriver:
                ip = re.search(r'(\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3})', path).group(1)
            except AttributeError:
                # It is NOT a remote webdriver either:
                pass
            else:
                # It is a remote webdriver, so try to format it:
                try:
                    port = re.search(r'\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}:(\d+)', path).group(1)
                except AttributeError:
                    port = "4444"
                try:
                    scheme = re.search(r'(https?)://\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}', path).group(1)
                except AttributeError:
                    scheme = "http"
                path_app = "{}://{}:{}/wd/hub".format(scheme, ip, port)
        return path_app

    def _check_config(config_file):
        if os.path.isfile(config_file):
            re_config = False
            try:
                config_dict = file2json(config_file)
            except (json.JSONDecodeError, UnicodeDecodeError):
                re_config = True
            else:
                for item in config_dict.items():
                    path_app = _check_app(item[1], item[0])  # path, app
                    if path_app is False:
                        re_config = True
                        break
            if os.access(config_file, os.W_OK):
                writable = True
            else:
                writable = False
        else:
            re_config = True
            if os.access(os.path.split(config_file)[0], os.W_OK):
                writable = True
            else:
                writable = False
        return re_config, writable

    def _reformat_config_file(config_file):
        app_json = file2json(config_file)
        formatted_app_json = {}
        for item in app_json.items():
            path_app = _check_app(item[1], item[0])
            formatted_app_json[item[0]] = path_app
        try:
            with open(config_file, 'w') as outf:
                json.dump(
                    formatted_app_json,
                    outf,
                    indent=4,
                    separators=(',', ': ')
                )
        except Exception:
            pass
        return formatted_app_json

    def _check_sequences(seq):
        alphabets = [
            "ACDEFGHIKLMNPQRSTVWYBXZJUO",  # ambiguous protein
            "GATCRYWSMKHBVDNU"  # ambiguous nucleotide (DNA & RNA)
        ]
        # convert to dict:
        for i in range(len(alphabets)):
            alphabet = {}
            for chr in alphabets[i]:
                alphabet[chr] = None
            alphabets[i] = deepcopy(alphabet)
        if seq.strip()[0] == ">":
            seq = ''.join(seq.strip().split('\n')[1:]).upper()
        else:
            seq = ''.join(seq.strip().split('\n')).upper()
        is_seq = [True, True]
        for i in range(2):
            for letter in seq:
                if letter not in alphabets[i]:
                    is_seq[i] = False
                    break
        return is_seq

    # Check the query file:
    if os.path.isfile(args['query']):
        with open(args['query'], 'r') as inf:
            fasta = inf.read().rstrip('\n').lstrip('>').split('\n>')
            seq = ''
            for q in fasta:
                seq += ''.join(q.strip().split('\n')[1:])
    else:
        seq = args['query'].strip()
    if _check_sequences(seq) == [False, False]:
        raise errors.InputError(
            'Your query sequences are not proteins, nor nucleotides, nor an '
            'accessible file: "{}"'.format(args['query'])
        )

    system = platform.system().lower()
    if system[:3] == 'win':
        find = 'where'  # Windows
    else:
        find = 'which'  # including Linux and Darwin
    app_json = {}.fromkeys(['fastq-dump', 'chromedriver', "Trinity"])
    checked = []
    config_files = [
        os.path.abspath(os.path.join(r2g.__path__[0], "path.json")),
        os.path.abspath(os.path.join(os.path.expanduser('~'), ".r2g.path.json"))
    ]
    log(config_files, args['verbose'], 'debug')
    for cfg in config_files:
        checked.append(_check_config(cfg))
        log("Check config files: {} - {}".format(cfg, _check_config(cfg)), args['verbose'], 'debug')
    if checked[0][0] is False:
        app_json = _reformat_config_file(config_files[0])
        log("Applying the config file: {}".format(config_files[0]))
    elif checked[0][0] is True and checked[1][0] is False:
        app_json = _reformat_config_file(config_files[1])
        log("Applying the config file: {}".format(config_files[1]))
    else:
        need_save = False
        input_dir = {
            "Trinity": _input_trinity_dir,
            "fastq-dump": _input_fastq_dump_dir,
            "chromedriver": _input_webdriver_dir,
        }
        for app in app_json.keys():
            if app == "chromedriver":
                # Temporarily overwrite the path to the webdriver:
                if args.get("browser", None) is not None and args.get("docker", False) is False:
                    app_json['chromedriver'] = args['browser']
                    continue
                elif os.environ.get("PRIVATE_WEBDRIVER", None) is not None:
                    app_json["chromedriver"] = os.environ["PRIVATE_WEBDRIVER"]
                    continue
            configured = False
            try:
                path = os.path.split(bytes2str(subprocess.check_output([find, app])).strip())[0]
                app_json[app] = os.path.join(path, app)
            except subprocess.CalledProcessError:
                need_save = True
                choice = _ask_yes_or_no(
                    "Couldn't find {} in your $PATH. Configure it manually now? ([Y]/N) ".format(app)
                )
                if choice:
                    path = input_dir[app]()
                    # remote webdriver:
                    # if app == "chromedriver":
                    #     try:
                    #         # Supposed to be a remote webdriver:
                    #         address = re.search(r'(\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3})', path).group(1)
                    #     except AttributeError:
                    #         # It is NOT a remote webdriver:
                    #         pass
                    #     else:
                    #         # It is a remote webdriver, so try to format it:
                    #         try:
                    #             port = re.search(r'\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}:(\d+)', path).group(1)
                    #         except AttributeError:
                    #             port = "4444"
                    #         try:
                    #             scheme = re.search(r'(https?)://\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}', path).group(1)
                    #         except AttributeError:
                    #             scheme = "http"
                    #         path = "{}://{}:{}/wd/hub".format(scheme, address, port)
                    #         app_json[app] = path
                    #         configured = True
                    while not configured:
                        path_app = _check_app(path, app)
                        if path_app is False:
                            if app == "chromedriver":
                                log('"{}" is not the valid format of webdriver. '
                                    'It is supposed to be scheme://ip:port or a local path. '
                                    'Please try again.'.format(path))
                            else:
                                log('"{}": No such file or not executable, please try again.'.format(path))
                            path = input_dir[app]()
                        else:
                            app_json[app] = path_app
                            configured = True
                else:
                    log("Aborted by the user.")
                    sys.exit(1)
        if need_save:
            if checked[0] == (True, True) and checked[1][0] is True:
                config_file = config_files[0]
            elif checked[0] == (True, False) and checked[1] == (True, True):
                config_file = config_files[1]
            else:
                config_file = None
                log("Don't have permission to save the config. You may have to re-config it next time.")
            if config_file is not None:
                choice = _ask_yes_or_no(
                    "Do you want to keep the config file? ([Y]/N) ".format(config_file)
                )
                if choice:
                    with open(config_file, 'w') as outf:
                        log("The config file was saved as {}".format(config_file))
                        json.dump(
                            app_json,
                            outf,
                            indent=4,
                            separators=(',', ': ')
                        )
                else:
                    log("The config file is not saved. You may have to re-config it next time.")
    return app_json
