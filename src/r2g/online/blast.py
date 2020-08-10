from __future__ import division

import os
import time
from copy import deepcopy
import xml.etree.ElementTree as ET

from r2g import utils
from r2g.online import NCBIWWW_selenium
from r2g import errors


def _cut_seq(name, seq, args):
    chunks = []
    try:
        frag = int(args["cut"].split(',')[0])
        ovlp = int(args["cut"].split(',')[-1])
        assert frag > ovlp
    except AssertionError:
        raise errors.InputError(
            'The fragment must be longer than the overlap.'
        )
    except ValueError as err:
        raise errors.InputError(
            'The format or type of the argument "--cut" is wrong. '
            '{}'.format(err)
        )
    else:
        seq = ''.join(seq.strip().split('\n'))
        seed = frag - ovlp
        num_frag = (len(seq) - ovlp) // seed
        for i in range(num_frag):
            chunk_name = ">{}_{}".format(name, i)
            if i == num_frag - 1:
                chunk_seq = seq[(i * seed):]
            else:
                chunk_seq = seq[(i * seed):(i * seed + frag)]
            if len(chunk_seq) > 0:
                chunk = "{}\n{}".format(chunk_name, chunk_seq)
                chunks.append(chunk)
    # chunks = [">name1\nseq1", ">name2\nseq2", ...]
    return chunks


def _format_seq(args):
    batch = 20
    seq, seq_list = [], []
    if os.path.isfile(args['query']):
        with open(args['query'], 'r') as inf:
            fasta = inf.read().rstrip('\n').lstrip('>').split('\n>')
            names = []
            # name = fasta[0].split('\n', 1)[0][1:].split()[0]
            for fa in fasta:
                fa = fa.split('\n', 1)
                seqname = fa[0].split()[0]
                seq_list += _cut_seq(seqname, fa[-1], args)
                names.append(seqname)
            name = '_'.join(names)
    else:
        if args['query'][0] == ">":
            fasta = args['query'].strip().split('\n', 1)
            name = fasta[0].split()[0][1:]
            seq = ''.join(fasta[1].strip().split())
        else:
            name = "Undefined"
            seq = args['query']
        seq_list = _cut_seq(name, seq, args)
    seq = [
        '\n'.join(seq_list[(n * batch):((n + 1) * batch + 1)])
        for n in range(len(seq_list) // 20 + 1)
    ]
    # seq = [">name1\nseq1\n>name2\nseq2...>name20\nseq20", ...]
    while '' in seq:
        seq.remove('')
    return name, seq


def _clear_up_list(download_list):
    stacked_list = {}
    for sra in download_list:
        stacked_spots = []
        # remove redundant spots first:
        spots = sorted({}.fromkeys(download_list[sra]).keys())
        # stack spots:
        start_spot, pre_spot = spots[0], (spots[0]-1)
        for spot in spots:
            if spot - pre_spot == 1:
                pass
            else:
                stacked_spots.append((start_spot, pre_spot))
                start_spot = spot
            pre_spot = spot
        stacked_spots.append((start_spot, pre_spot))
        stacked_list[sra] = deepcopy(stacked_spots)
    return stacked_list


# def _parse_tabular(raw_results):
#     """Deprecated. Use XML instead of Tabular."""
#     download_list = {}
#    for line in raw_results.strip().split('\n'):
#         line_lst = line.strip().split('\t')
#         if len(line_lst) == 12:
#             hit = line_lst[1].split('.')
#             try:
#                 sra = hit[0][4:]
#                 spot = int(hit[1])
#             except IndexError:
#                 pass
#             except ValueError:
#                 pass
#             else:
#                 spots = deepcopy(download_list.get(sra, []))
#                 spots.append(spot)
#                 download_list[sra] = deepcopy(spots)
#     download_list = _clear_up_list(download_list)
#     return download_list


def _parse_xml(raw_results, args):
    download_list = {}
    r = -1
    err = ""
    while r < int(args['retry']):
        try:
            results_tree = ET.fromstring(raw_results)
        except ET.ParseError as e:
            err = str(e)
            r += 1
            print(raw_results)
            utils.log("\033[1;33mWARNING:\033[0m couldn't get results from NCBI due to temporary errors. Retrying...",
                      args['verbose'], 'debug')
        else:
            Iterations = results_tree.find(
                'BlastOutput_iterations'
            ).findall('Iteration')
            for I in Iterations:
                hits = I.find('Iteration_hits')
                for hit in hits:
                    hit = hit.find('Hit_accession').text.strip().split('.')
                    try:
                        sra = hit[0]
                        spot = int(hit[1])
                    except (ValueError, IndexError):
                        pass
                    else:
                        spots = deepcopy(download_list.get(sra, []))
                        spots.append(spot)
                        download_list[sra] = deepcopy(spots)
            err = ""
            break
    if len(err) > 0:
        utils.log("\033[1;33mWARNING:\033[0m couldn't get results for from NCBI due to temporary errors. "
                  "The fragment was skipped.")
        if args['verbose']:
            with open(
                    os.path.join(
                        args['outdir'], "{}.xml".format(args['sra'])
                    ), 'w'
            ) as outf:
                outf.write(raw_results)
    return download_list


def query(args, webdriver):
    download_list = {}
    name, seq_chunks = _format_seq(args)
    utils.log(seq_chunks, args['verbose'], 'debug')
    SRAs = {}.fromkeys(args['sra'].strip().split(',')).keys()
    formatted_SRAs = NCBIWWW_selenium.check_sra_validity(SRAs, proxy=args["proxy"])
    # formatted_SRAs = {species1: {srx1: [srr...], srx2: [srr...]}, species2: ...}
    interval = 10
    for i in formatted_SRAs.items():
        for j in i[-1].items():
            srx = j[0]
            srr = ','.join(j[-1])
            current = 0
            for chunk in seq_chunks:
                current += 1
                utils.processing(
                    current,
                    len(seq_chunks),
                    "\033[1;32m{}\033[0m - {} \033[1;37m({})\033[0m".format(i[0], srx, srr),
                    "percent"
                )
                r = -1
                err = ''
                while r < int(args['retry']):
                    # Do not contact the server more often than once every 10 seconds:
                    if interval < 10:
                        time.sleep(11 - interval)
                    start_time = time.time()
                    if len(err) > 0:
                        # utils.log("Retrying...", shift="\n")
                        utils.log("Retrying...")
                    try:
                        result = NCBIWWW_selenium.qblast(
                            program=args["program"],
                            srx=srx,
                            query=chunk,
                            max_num_seq=(args["max_num_seq"] // (len(seq_chunks) * 20) + 1),
                            expect=args["evalue"],
                            # format_type='Tabular'
                            # Don't know why the number of returned hits can't be determined when the format is Tabular.
                            # So the XML format is required:
                            format_type='XML',
                            browser=webdriver,
                            proxies=(args["chrome_proxy"], args["proxy"]),
                            verbose=args["verbose"]
                        )
                        if args['verbose']:
                            with open(os.path.join(args['outdir'], "{}.xml".format(srx)), 'w') as outf:
                                outf.write(result)
                    except Exception as e:
                        err = str(e)
                        r += 1
                        utils.log("Error msg while querying: {}.".format(err), shift="\n")
                    else:
                        err = ''
                        break
                if len(err) > 0:
                    raise errors.QueryError("Couldn't get results from NCBI. Errors above must be investigated.")
                else:
                    result = _parse_xml(result, args)
                    for sra in result.keys():
                        spots = deepcopy(download_list.get(sra, []))
                        spots += result[sra]
                        download_list[sra] = deepcopy(spots)
                    interval = time.time() - start_time
    download_list = _clear_up_list(download_list)
    return name, download_list
