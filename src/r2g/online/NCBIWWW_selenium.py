import re
import time
import os
from copy import deepcopy

import requests
from selenium import webdriver

import r2g
from r2g import errors
from r2g import utils


headers = {
    "User-Agent": "R2gClient/{} (X11; Linux x86_64)".format(r2g.__version__)
}


def _search_keyword(pattern, text, default_value=None):
    """ (PRIVATE)
    Get the value of the keyword (e.g. job title, RID, etc.) from the webpage.
    """
    value = re.search(pattern=pattern, string=text)
    if value is not None:
        try:
            value = value.group(1).strip()
        except IndexError:
            value = default_value
    else:
        value = default_value
    return value


def _format_sra(sra, text):
    """ (PRIVATE)
    End users can input either SRX or SRR, which will be submitted to NCBI to check the validity,
    and this function is for deciding what the kind of SRA the input is.
    """
    # NSuggest_CreateData("srr181288", new
    # Array(
    #     "SRX882917 ( taxid:13443; run:SRR1810085 SRR1810146 SRR1810833 SRR1812884)@srx882917 13443
    #         srr1810085 srr1810146 srr1810833 srr1812884",
    #     "SRX885412 ( taxid:1639; run:SRR1812880)@srx885412 1639     srr1812880",
    #     "SRX885413 ( taxid:28901; run:SRR1812881)@srx885413 28901     srr1812881",
    #     "SRX885414 ( taxid:28901; run:SRR1812882)@srx885414 28901     srr1812882",
    #     "SRX885415 ( taxid:28901; run:SRR1812883)@srx885415 28901     srr1812883",
    #     "SRX885416 (Leymus arenarius taxid:220462; run:SRR1812885)@srx885416 220462  leymus arenarius   srr1812885",
    #     "SRX885417 ( taxid:115547; run:SRR1812888)@srx885417 115547     srr1812888",
    #     "SRX885418 ( taxid:7160; run:SRR1812886)@srx885418 7160     srr1812886",
    #     "SRX885419 ( taxid:7160; run:SRR1812887)@srx885419 7160     srr1812887",
    #     "SRX885420 ( taxid:7160; run:SRR1812889)@srx885420 7160     srr1812889"),
    # 1);
    srx = _search_keyword(r'"({}) \( ?'.format(sra.upper()), text)
    srr = _search_keyword(r'run:[0-9A-Z ]*({})[0-9A-Z ]*\)'.format(sra.upper()), text)
    if srx is not None and srr is None:
        srr = _search_keyword(r'"{} \([\d\w\ \:]+; run:([0-9A-Z ]+)\)'.format(srx.upper()), text)
        if srr is None:
            raise errors.QueryError("Invalid SRX accession number: \033[31m{}\033[0m. Aborted.".format(sra))
    elif srr is not None and srx is None:
        srx = _search_keyword(r'"(\w+\d+) \([\d\w\ \:]+; run:[0-9A-Z ]*({})[0-9A-Z ]*\)'.format(srr.upper()), text)
        if srx is None:
            raise errors.QueryError("Invalid SRR accession number: \033[31m{}\033[0m. Aborted.".format(sra))
        else:
            # An SRX may relates to multiple SRAs:
            srr = _search_keyword(r'"{} \([\d\w\ \:]+; run:([0-9A-Z ]+)\)'.format(srx.upper()), text)
    else:
        raise errors.QueryError(
            "Invalid SRA accession number: \033[31m{}\033[0m. Aborted.".format(sra)
        )
    taxid = _search_keyword(r'"{} \(.+taxid:(\d+); run:{}'.format(srx, srr), text)
    srr = srr.strip().split()
    return taxid, srx, srr


def _taxid_to_species(taxid):
    """ (PRIVATE)
    transfer the taxid to the speicies name
    """
    taxid_dict = utils.file2json(os.path.join(r2g.__path__[0], "taxid_to_species.json"))
    species = taxid_dict.get(
        taxid,
        "Unknown species (taxid {})".format(taxid)
    )
    return species


def check_sra_validity(input_SRAs, proxy=None):
    """
    End users can input either SRX or SRR, which will be submitted to NCBI to check the validity,
    and this function is for deciding what the kind of SRA the input is.
    The proxy should be args[proxy].
    """
    if type(input_SRAs) == str:
        input_SRAs = [input_SRAs, ]
    output_SRAs = {}
    for s in input_SRAs:
        check_sra_params = {"dict": "srx_dict_sg", "q": s}
        try:
            check_sra_response = requests.get(
                "https://blast.ncbi.nlm.nih.gov/portal/utils/autocomp.fcgi",
                params=check_sra_params,
                headers=headers,
                timeout=60,
                proxies=proxy
            )
        except Exception as err:
            raise errors.QueryError(
                "Couldn't check the validity of SRA accession numbers "
                "probably because of network issues. {}.".format(err)
            )
        else:
            if not check_sra_response.ok:
                raise errors.QueryError(
                    "Couldn't check the validity of SRA accession numbers "
                    "probably because of network issues. Status code: {}".format(check_sra_response.status_code)
                )
            else:
                # returned srr is a list
                taxid, srx, srr = _format_sra(s, check_sra_response.content.decode('utf-8'))
                species = _taxid_to_species(taxid)
                srxes = deepcopy(output_SRAs.get(species, {}))
                srxes[srx] = deepcopy(srxes.get(srx, []) + srr)
                output_SRAs[species] = deepcopy(srxes)
                # output_SRAs = {species1: {srx1: [srr...], srx2: [srr...]}, species2: ...}
        time.sleep(5)
    return output_SRAs


def _parse_qblast_wait_page(wait_html):
    """ (PRIVATE)
    Extract a tuple of job title, entrez query, RID, and RTOE from the 'please wait' page.

    The NCBI FAQ pages use TOE for 'Time of Execution', so RTOE is probably
    'Request Time of Execution' and RID would be 'Request Identifier'.
    """
    rid = _search_keyword(r'<input name="RID".+?value="([\d\w]+?)">', wait_html)  # The most important to proceed
    status_code = _search_keyword(r'<input name="SEARCH_DB_STATUS".+?value="(\d+?)"', wait_html, "NA")
    status1 = _search_keyword(r'<td>Status</td><td>(\w+?)</td>', wait_html)
    status2 = _search_keyword(r'Status=(\w+)', wait_html)
    job_title = _search_keyword(r'<input name="JOB_TITLE".+?value="(.+?)"', wait_html)
    entrez_query = _search_keyword(r'<input name="ENTREZ_QUERY".+?value="(.+?)"', wait_html)
    rtoe = _search_keyword(r'<input name="RID".+?value="(\d+?)">', wait_html)
    max_num_seq = _search_keyword(r'<input name="MAX_NUM_SEQ".+?value="(\d+?)"', wait_html, 500)

    if rid is None:
        # Can we reliably extract the error message from the HTML page?
        # e.g.  "Message ID#24 Error: Failed to read the Blast query:
        #       Nucleotide FASTA provided for protein sequence"
        # or    "Message ID#32 Error: Query contains no data: Query
        #       contains no sequence data"
        #
        # This used to occur inside a <div class="error msInf"> entry.
        #
        # Taken from an error webpage (July 23, 2020, format: HTML):
        # <!-- Do errors this way -->
        # <!--<ul class="msg error"><li class="error"><p class="error"></p></li></ul>-->
        # <ul id="upgMsg" class="msg error"><li id="lpgMsg" class="error">\
        # <p class="error">Non-interactive SRA BLAST searches not supported.</p>\
        # </li></ul>

        err_msg = _search_keyword(r'(<p class="error">.+?</p>)', wait_html)
        if err_msg is None:
            err_msg = _search_keyword(r"Message ID#\d+ Error: (.+?)$", wait_html)
            if err_msg is None:
                # We didn't recognise the error layout :(
                raise errors.QueryError("No RID found in the 'please wait' page, "
                                        "there was probably an error in your request "
                                        "but we could not extract a helpful error message.")
        else:
            err_msg = "".join(re.findall(r'>(.+?)<', err_msg))
        raise errors.QueryError("Error message from NCBI: {}".format(err_msg))
    else:
        # Polling Status can be very tricky:
        status_code_dict = {"31": "searching", "21": "waiting", "43": "ready", "63": "failed"}  # these are all I met
        if status1 is not None:
            status = status1.lower()
        elif status2 is not None:
            status = status2.lower()
        else:
            status = status_code_dict.get(status_code, "unknown")
    return rid, status, job_title, entrez_query, rtoe, max_num_seq

# Geckodriver keep throwing "Failed to decode response from marionette", which seems to be a known bug.
# def _setup_firefox_webdriver(browser="http://127.0.0.1:4444/wd/hub", proxy=None):
#     """ (PRIVATE)
#     Set up the webdriver.
#     The input brower should be either "/path/to/geckodriver" or "http://127.0.0.1:4444/wd/hub".
#     The input proxy is supposed to be args[firefox_proxy].
#     """
#     # set up the user-agent:
#     prof = webdriver.FirefoxProfile()
#     prof.set_preference("general.useragent.override", headers["User-Agent"])
#     opts = webdriver.firefox.options.Options()
#     opts.headless = True
#     Optimize the browser to load fast:
#     opts.set_preference("network.http.pipelining", True)
#     opts.set_preference("network.http.proxy.pipelining", True)
#     opts.set_preference("network.http.pipelining.maxrequests", 8)
#     opts.set_preference("content.notify.interval", 500000)
#     opts.set_preference("content.notify.ontimer", True)
#     opts.set_preference("content.switch.threshold", 250000)
#     opts.set_preference("browser.cache.memory.capacity", 65536)  # Increase the cache capacity.
#     opts.set_preference("browser.startup.homepage", "about:blank")
#     opts.set_preference("reader.parse-on-load.enabled", False)  # Disable reader, we won't need that.
#     opts.set_preference("browser.pocket.enabled", False)  # Duck pocket too!
#     opts.set_preference("loop.enabled", False)
#     opts.set_preference("browser.chrome.toolbar_style", 1)  # Text on Toolbar instead of icons
#     opts.set_preference("browser.display.show_image_placeholders", False)  # Don't show thumbnails on not loaded image
#     opts.set_preference("browser.display.use_document_colors", False)  # Don't show document colors.
#     opts.set_preference("browser.display.use_document_fonts", 0)  # Don't load document fonts.
#     opts.set_preference("browser.display.use_system_colors", True)  # Use system colors.
#     opts.set_preference("browser.formfill.enable", False)  # Autofill on forms disabled.
#     opts.set_preference("browser.helperApps.deleteTempFileOnExit", True)  # Delete temporary files.
#     opts.set_preference("browser.shell.checkDefaultBrowser", False)
#     opts.set_preference("browser.startup.homepage", "about:blank")
#     opts.set_preference("browser.startup.page", 0)  # blank
#     opts.set_preference("browser.tabs.forceHide", True)  # Disable tabs, We won't need that.
#     opts.set_preference("browser.urlbar.autoFill", False)  # Disable autofill on URL bar.
#     opts.set_preference("browser.urlbar.autocomplete.enabled", False)  # Disable autocomplete on URL bar.
#     opts.set_preference("browser.urlbar.showPopup", False)  # Disable list of URLs when typing on URL bar.
#     opts.set_preference("browser.urlbar.showSearch", False)  # Disable search bar.
#     opts.set_preference("extensions.checkCompatibility", False)  # Addon update disabled
#     opts.set_preference("extensions.checkUpdateSecurity", False)
#     opts.set_preference("extensions.update.autoUpdateEnabled", False)
#     opts.set_preference("extensions.update.enabled", False)
#     opts.set_preference("general.startup.browser", False)
#     opts.set_preference("plugin.default_plugin_disabled", False)
#     opts.set_preference("permissions.default.image", 2)  # Image load disabled
#     caps = webdriver.common.desired_capabilities.DesiredCapabilities.FIREFOX.copy()
#     # set up the proxy:
#     if proxy is not None:
#         scheme, address = proxy
#         if scheme[:5] == "socks":
#             caps["proxy"] = {
#                 "socksProxy": address,
#                 'proxyType': "manual",
#                 "socksVersion": int(scheme[5])
#             }
#         elif scheme == "http":
#             caps["proxy"] = {
#                 'httpProxy': address,
#                 'sslProxy': address,
#                 'proxyType': "manual"
#             }
#     if browser[:7] == "http://":
#         firefox = webdriver.Remote(
#             command_executor=browser,
#             desired_capabilities=caps,
#             options=opts,
#         )
#     else:
#         firefox = webdriver.Firefox(
#             executable_path=browser,
#             capabilities=caps,
#             options=opts,
#             firefox_profile=prof,
#         )
#     return firefox


def _setup_chrome_webdriver(browser="http://127.0.0.1:4444/wd/hub", proxy=None):
    # TODO: change the user-agent and proxy settings in the remote webdriver. Maybe utilize a crx plugin?
    caps = webdriver.common.desired_capabilities.DesiredCapabilities.CHROME.copy()
    caps['acceptInsecureCerts'] = True
    opts = webdriver.ChromeOptions()
    if proxy is not None:
        opts.add_argument("--proxy-server={}".format(proxy))
    opts.add_argument("--headless")
    opts.add_argument("--user-agent={}".format(headers["User-Agent"]))
    # opts.add_argument("--disable-gpu")  # On Windows
    # prefs = {
    #    'profile.default_content_setting_values' : {
    #        'images' : 2
    #    }
    # }
    # opts.add_experimental_option('prefs', prefs)
    if browser[:7] == "http://":
        chrome = webdriver.Remote(
            command_executor=browser,
            desired_capabilities=caps
        )
    else:
        chrome = webdriver.Chrome(
            executable_path=browser,
            options=opts
        )
    return chrome


def _add_eq_menus(srx):
    """ (PRIVATE)
    Construct the part of EQ_MENUs in the base url. Input must be srx.
    """
    if type(srx) == str:
        srx = srx.strip().split(',')
    params = "&EQ_MENU={}".format(srx[0])
    if len(srx) > 1:
        for i in range(1, len(srx)):
            params += "&EQ_MENU{}={}".format(i, srx[i])
    params += "&NUM_ORG={}".format(len(srx))
    return params


def _add_program(program):
    """ (PRIVATE)
    Construct the part of PROGRAMs in the base url.
    """
    params = "&PROGRAM=blastn&BLAST_PROGRAMS=megaBlast"  # default in NCBI: megablast
    if program.lower() == "blastn":
        params = "&PROGRAM=blastn&BLAST_PROGRAMS=blastn"
    elif program.lower() == "megablast":
        params = "&PROGRAM=blastn&BLAST_PROGRAMS=megaBlast"
    elif program.lower() == "discomegablast":
        params = "&PROGRAM=blastn&BLAST_PROGRAMS=discoMegablast"
    elif program.lower() == "tblastn":
        params = "&PROGRAM=tblastn"
    elif program.lower() == "tblastx":
        params = "&PROGRAM=tblastx"
    return params


def qblast(
        program,
        srx,  # only accept SRX
        query,
        query_from=None,
        query_to=None,
        max_num_seq=500,
        expect=10.0,
        repeat_filter=None,  # filter out low complexity regions
        short_query=None,
        word_size=None,
        job_title=None,
        format_type="XML",
        browser="http://127.0.0.1:4444/wd/hub",
        proxies=(None, None),  # (webdriver_proxy, general_proxy)
        verbose=False,
):
    """BLAST search using the selenium module:
         Some useful parameters:

          - program        megaBlast, blastn, discoMegablast, or tblastn (capital sensitive)
          - sra            Which sra database to search against (srr or srx).
          - sequence       The sequence to search.
          - max_num_seq    The number of hits that NCBI returned.
          - expect         An expect value cutoff.  Default 10.0.
          - repeat_filter  "L" turns on filtering low complexity regions.  Default no filtering.
          - word_size      default: 28 for blastn, 6 for tblastn
          - format_type    "HTML", "Text", "ASN.1", or "XML".  Default "XML".
    """
    # - base url:
    # https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?PAGE_TYPE=BlastSearch&BLAST_SPEC=SRA&DB_GROUP=Exp&
    # 1) PROGRAM = ['blastn', 'tblastn', 'tblastx']
    # 2) BLAST_PROGRAMS = ['megaBlast', 'blastn', 'discoMegablast']
    # e.g.
    # PROGRAM=blastn&BLAST_PROGRAMS=megaBlast&NUM_ORG=1&EQ_MENU=SRX000001
    # PROGRAM=tblastn&NUM_ORG=2&EQ_MENU=SRX000001&EQ_MENU1=SRX000002
    # Step 1 - Submit queries using the selenium module:
    url = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi?PAGE_TYPE=BlastSearch&BLAST_SPEC=SRA&DB_GROUP=Exp"
    url += _add_eq_menus(srx)
    url += _add_program(program)

    chrome = _setup_chrome_webdriver(browser=browser, proxy=proxies[0])
    time.sleep(4)

    submit_params = [
        # ("QUERY", query),
        # ("QUERY_FROM", query_from),
        # ("QUERY_TO", query_to),
        ("MAX_NUM_SEQ", max_num_seq),
        ("EXPECT", expect),
        ("FILTER", repeat_filter),
        ("SHORT_QUERY_ADJUST", short_query),
        ("WORD_SIZE", word_size),
        ("JOB_TITLE", job_title)
    ]
    for p in submit_params:
        if p[1] is not None:
            url += "&{}={}".format(p[0], p[-1])

    chrome.get(url)
    time.sleep(4)
    chrome.find_element_by_name("QUERY").send_keys(query)
    if query_from is not None and query_to is not None:
        chrome.find_element_by_name("QUERY_FROM").send_keys(query_from)
        chrome.find_element_by_name("QUERY_TO").send_keys(query_to)
    time.sleep(4)
    chrome.find_element_by_class_name('blastbutton').click()
    wait_page = chrome.page_source
    try:
        rid, status, job_title, entrez_query, rtoe, max_num_seq = _parse_qblast_wait_page(wait_page)
    except errors.QueryError:
        # In my experience, the first submit may be blocked somehow, so try to submit again:
        time.sleep(4)
        chrome.find_element_by_class_name('blastbutton').click()
        wait_page = chrome.page_source
        rid, status, job_title, entrez_query, rtoe, max_num_seq = _parse_qblast_wait_page(wait_page)
    cookies = chrome.get_cookies()
    _previous = time.time()
    chrome.quit()

    # Step 2 - Poll results from NCBI:
    # Actually, all parameters for polling results can be obtained from the wait page.
    # --
    # Poll NCBI until the results are ready.
    # https://blast.ncbi.nlm.nih.gov/Blast.cgi?CMD=Web&PAGE_TYPE=BlastDocs&DOC_TYPE=DeveloperInfo
    # 1. Do not contact the server more often than once every 10 seconds.
    # 2. Do not poll for any single RID more often than once a minute.
    # 3. Use the URL parameter email and tool, so that the NCBI
    #    can contact you if there is a problem.
    # 4. Run scripts weekends or between 9 pm and 5 am Eastern time
    #    on weekdays if more than 50 searches will be submitted.
    # --
    # Could start with a 10s delay, but expect most short queries
    # will take longer thus at least 70s with delay. Therefore,
    # start with 20s delay, thereafter once a minute.
    poll_params = [
        ("RID", rid),
        ("JOB_TITLE", job_title),
        ("ENTREZ_QUERY", entrez_query),
        ('MAX_NUM_SEQ', max_num_seq),
        ("CMD", "Get"),
    ]
    poll_params = [p for p in poll_params if p[1] is not None]

    delay = 20  # seconds
    session = requests.Session()
    for c in cookies:
        session.cookies.set(c['name'], c['value'])
    not_done_yet = True
    while not_done_yet:
        current = time.time()
        wait = _previous + delay - current
        if wait > 0:
            time.sleep(wait)
            _previous = current + wait
        else:
            _previous = current
        # delay by at least 60 seconds only if running the request against the public NCBI API
        if delay < 60:
            # Wasn't a quick return, must wait at least a minute
            delay = 60

        try:
            poll_response = session.get(
                "https://blast.ncbi.nlm.nih.gov/Blast.cgi",
                params=poll_params,
                headers=headers,
                timeout=120,
                proxies=proxies[-1],
            )
        except Exception as err:
            utils.log(
                "\033[1;33mWARNING:\033[0m Couldn't poll results from NCBI. {}. "
                "But don't panic, we will retry and are almost there.".format(err),
                verbose=verbose,
                attr="debug"
            )
        else:
            if poll_response.ok:
                poll_rid, poll_status, _, _, _, _ = _parse_qblast_wait_page(poll_response.content.decode("utf-8"))
                utils.log("RID: {}, Status: {}.".format(poll_rid, poll_status), verbose, "debug")
                if poll_rid == rid:
                    if poll_status.lower() in ["waiting", "searching"]:
                        continue
                    elif poll_status.lower() == "failed":
                        err_msg = _search_keyword(
                            r'(<p class="error">.+?</p>)',
                            poll_response.content.decode("utf-8"),
                            ">NA<"
                        )
                        err_msg = ''.join(re.findall(r'>(.+?)<', err_msg))  # remove inside links <a></a>
                        raise errors.QueryError(
                            'Retrieving results failed. Error message from NCBI: "{}".'.format(err_msg)
                        )
                    elif poll_status.lower() == "ready":
                        poll_params.append(("FORMAT_TYPE", format_type))
                        while not_done_yet:
                            try:
                                poll_response = session.get(
                                    "https://blast.ncbi.nlm.nih.gov/Blast.cgi",
                                    params=poll_params,
                                    headers=headers,
                                    timeout=120,
                                    proxies=proxies[-1]
                                )
                            except Exception as err:
                                raise errors.QueryError(
                                    "Although the query was submitted, "
                                    "but the results couldn't be retrieved. {}".format(err)
                                )
                            else:
                                if poll_response.ok:
                                    poll_format = _search_keyword(
                                        r'<!DOCTYPE ([\w]+?) PUBLIC',
                                        poll_response.content.decode("utf-8"),
                                        "NA"
                                    )
                                    if poll_format.lower() == "blastoutput":
                                        blastoutput = poll_response.content.decode("utf-8")  # XML
                                        not_done_yet = False
                                        break
                                    else:
                                        utils.log(
                                            "\033[1;33mWARNING:\033[0m Although the results are ready, "
                                            "they can't be retrieved somehow. "
                                            "Don't panic, we will retry and are almost there.",
                                            verbose=verbose,
                                            attr="debug"
                                        )
                                        continue
                                else:
                                    utils.log(
                                        "\033[1;33mWARNING:\033[0m Although the query was submitted, "
                                        "but the results couldn't be retrieved probably because of network issues. "
                                        "Status code: {}.".format(poll_response.status_code),
                                        verbose=verbose,
                                        attr="debug"
                                    )
                    else:
                        utils.log(
                            "\033[1;33mWARNING:\033[0m Something wrong while retrieving results from NCBI. "
                            "RID: {}. Status: \033[1;33m{}\033[0m. "
                            "But don't panic, we will retry and are almost there.".format(poll_rid, poll_status),
                            verbose=verbose,
                            attr="debug"
                        )
                else:
                    utils.log(
                        "\033[1;33mWARNING:\033[0m The submitted RID (\033[1;33m{}\033[0m) "
                        "is different from the polled one (\033[1;33m{}\033[0m). "
                        "But don't panic, we will try to retrieve results again.".format(rid, poll_rid),
                        verbose=verbose,
                        attr="debug"
                    )
            else:
                utils.log(
                    "\033[1;33mWARNING:\033[0m Couldn't get results from NCBI. Status code: \033[1;33m{}\033[0m. "
                    "But don't panic, we will retry and are almost there.".format(poll_response.status_code),
                    verbose=verbose,
                    attr="debug"
                )
    return blastoutput
