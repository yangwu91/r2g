import subprocess

from r2g import utils
from r2g import errors


def fastq_dump(sra, spotN, spotX, app_json):
    """Works with fastq-dump 2.8.2 and 2.9.2"""
    cmd = [
        app_json['fastq-dump'],
        # "--defline-seq", "@$sn[_$rn]/$ri",
        "--defline-seq", "@$sn/$ri",
        "--split-files",
        "-W",         # Clip adapter sequences
        # "-O", tmpdir,
        "-Z",         # stdout
        "-N", str(spotN),  # Minimum spot id (included)
        "-X", str(spotX),  # Minimum spot id (included)
        sra
    ]
    try:
        with subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as p:
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                raise errors.FetchError(utils.bytes2str(stderr))
            else:
                sequence = _parse_fastq(utils.bytes2str(stdout))
                log = '{} {}-{}:\n{}----'.format(sra, spotN, spotX, stderr)
                return sequence, log
    except OSError as err:
        raise errors.InputError(err)


def _parse_fastq(sequence):
    sequence = sequence.strip().split('\n')
    split_sequence = {}
    for i in range(int(len(sequence)/4)):
        read = sequence[4*i: 4*(i+1)]
        try:
            assert read[0][0] == '@'
            assert read[2][0] == '+'
            assert len(read[1]) == len(read[3])
            pair = read[0][-2:]
            assert pair in ['/1', '/2']
        except (AssertionError, IndexError):
            raise errors.FetchError("Downloaded sequences are not in FASTQ format: \n{}".format('\n'.join(read)))
        else:
            split_sequence[pair[-1]] = split_sequence.get(pair[-1], '') + '\n'.join(read) + '\n'
    # num_keys = len(split_sequence.keys())
    # if num_keys == 1:
    #     split_sequence['paired'] = False
    # else:
    #     split_sequence['paired'] = False
    return split_sequence
