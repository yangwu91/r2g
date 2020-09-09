FROM ubuntu:focal
MAINTAINER wuyang@drwu.ga

ARG CONDA_VER=4.8.3
ARG PY_VER=3.8.5
ARG TRINITY_VER=2.8.5
ARG SRA_VER=2.10.8

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NONINTERACTIVE_SEEN=true

ENV PATH="/opt/miniconda3/bin:/opt/bin:$PATH"

#ENV LANG_WHICH=en
#ENV LANG_WHERE=US
#ENV ENCODING=UTF-8
#ENV LANGUAGE=${LANG_WHICH}_${LANG_WHERE}.${ENCODING}
#ENV LANG=${LANGUAGE}
#ENV TZ="America/New_York"

EXPOSE 4444

ADD configs.tar.gz /tmp/
ADD scripts.tar.gz /tmp/
ADD selenium-server.tar.gz /tmp/

RUN \
    #============================================
    # customize sources and install chrome, and dependencies
    #============================================
    apt update -qqy && \
    apt install -qqy wget gnupg2 zip tzdata xvfb pulseaudio language-pack-en locales supervisor sudo git gosu uuid-runtime && \
    wget -qO - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
	echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
	apt update -qqy && \
    apt install -qqy  google-chrome-stable && \
    bash /tmp/scripts/wrap_chrome_binary.sh && \

    #==================================================
    # add normal user and group with passwordless sudo
    #==================================================
    useradd r2guser --uid 1000 --create-home --shell /bin/bash && \
    usermod -a -G sudo r2guser && \
    echo 'ALL ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers && \
    echo 'r2guser:secret' | chpasswd && \

    #======================================
    # supervisor
    #======================================
    cp -f /tmp/configs/supervisord.conf /etc/ && \
    cp -f /tmp/configs/selenium.conf /etc/supervisor/conf.d/ && \
    mkdir -p /var/run/supervisor /var/log/supervisor && \

    #======================================
    # selenium server
    #======================================
    mkdir -p /opt/selenium && \
    touch /opt/selenium/config.json && \
    cp -f /tmp/selenium-server/selenium-server-4.0.0-alpha-6.jar /opt/selenium/selenium-server.jar && \

    #======================================
    # relax permissions
    #======================================
    chmod -R 777 /opt /var/run/supervisor /var/log/supervisor /etc/passwd && \

    #======================================
    # get all scripts ready
    #======================================
    mkdir -p /opt/bin && \
    cp -f /tmp/scripts/* /opt/bin/ && \
    chmod +x /opt/bin/* && \

    #======================================
    # chrome webdriver
    #======================================
    CHROME_MAJOR_VERSION=$(google-chrome-stable --version | sed -E "s/.* ([0-9]+)(\.[0-9]+){3}.*/\1/") && \
    CHROME_DRIVER_VERSION=$(wget -qO - "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}") && \
    wget -qO /tmp/chromedriver_linux64.zip https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver_linux64.zip -d /opt/bin/ && \
    chmod +x /opt/bin/chromedriver && \
    bash /tmp/scripts/generate_webdriver_config.sh > /opt/selenium/config.json && \

    #=====================
    # miniconda3
    #=====================
    wget -qO /tmp/miniconda3.sh https://repo.anaconda.com/miniconda/Miniconda3-py38_${CONDA_VER}-Linux-x86_64.sh && \
    bash /tmp/miniconda3.sh -bfp /opt/miniconda3 && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    # Trinity, sratoolkit and other dependencies:
    conda install -y python=$PY_VER trinity=$TRINITY_VER sra-tools=$SRA_VER numpy samtools=1.10 && \
    chown -R r2guser /opt/* && \

	#=====================
    # configure sra-tools>2.10
    #=====================
	mkdir /opt/ncbi && \
	chmod 777 /opt/ncbi && \
	mkdir -p /.ncbi && \
	chmod 777 /.ncbi && \
	mkdir -p /root/.ncbi && \
    bash /opt/bin/generate_sratools_config.sh > /.ncbi/user-settings.mkfg && \
    bash /opt/bin/generate_sratools_config.sh > /root/.ncbi/user-settings.mkfg && \

    #=================
    # clean
    #=================
    apt autoremove -yy && \
    apt autoclean -yy && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* && \
    conda clean -ayq && \

    #======================
    # creating base directory for svfb
    #======================
    mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix && \

    #======================
    # creating a worksapce
    #======================
    mkdir -p /workspace && \
    chown -R r2guser /workspace && \
    chmod 777 /workspace && \

    #======================
    # r2g
    #======================
    # pip install r2g && \
    cd /opt && \
    git clone https://github.com/yangwu91/r2g.git && \
    cd r2g && \
    pip install .[test] && \
    bash /opt/bin/generate_r2g_pathjson.sh > /opt/miniconda3/lib/python3.8/site-packages/r2g/path.json && \
    cd /workspace

#============================
# Some configuration options
#============================
ENV SCREEN_WIDTH 1360
ENV SCREEN_HEIGHT 1020
ENV SCREEN_DEPTH 24
ENV SCREEN_DPI 96
ENV DISPLAY :99.0
ENV START_XVFB true

#========================
# Selenium Configuration
#========================
# As integer, maps to "maxInstances"
ENV NODE_MAX_INSTANCES 1
# As integer, maps to "maxSession"
ENV NODE_MAX_SESSION 1
# As address, maps to "host"
ENV NODE_HOST 0.0.0.0
# As integer, maps to "port"
ENV NODE_PORT 5555
# In milliseconds, maps to "registerCycle"
ENV NODE_REGISTER_CYCLE 5000
# In milliseconds, maps to "nodePolling"
ENV NODE_POLLING 5000
# In milliseconds, maps to "unregisterIfStillDownAfter"
ENV NODE_UNREGISTER_IF_STILL_DOWN_AFTER 60000
# As integer, maps to "downPollingLimit"
ENV NODE_DOWN_POLLING_LIMIT 2
# As string, maps to "applicationName"
ENV NODE_APPLICATION_NAME ""
# Debug
ENV GRID_DEBUG false

# Following line fixes https://github.com/SeleniumHQ/docker-selenium/issues/87
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

WORKDIR /workspace

ENTRYPOINT ["/opt/bin/start-docker-entrypoint.sh"]
