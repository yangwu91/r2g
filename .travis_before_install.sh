#!/bin/bash

set -e
set -u

wget -qO /tmp/miniconda.sh "$1"
bash /tmp/miniconda.sh -bfp "$PWD"/miniconda3
export PATH=$PATH:$PWD/miniconda3/bin

conda config --add channels bioconda
conda config --add channels conda-forge

case $TRAVIS_OS_NAME in
    linux)
        sudo apt-get -yyq update
        sudo apt-get -yyq install libxml-libxml-perl uuid-runtime
        conda install -qy sra-tools="$SRA" trinity="$TRINITY" numpy samtools=1.10
    ;;
    osx)
        brew install gcc@8
        #wget -qO /tmp/trinity.tar.gz https://github.com/trinityrnaseq/trinityrnaseq/releases/download/"${TRINITY}"/trinityrnaseq-"${TRINITY}".FULL.tar.gz
	      wget -qO /tmp/trinity.tar.gz https://github.com/trinityrnaseq/trinityrnaseq/archive/Trinity-v"${TRINITY}".tar.gz
	      tar -zxvf /tmp/trinity.tar.gz && cd trinityrnaseq-Trinity-v"${TRINITY}"
	      export PATH=/usr/local/bin:$PATH
	      make CXX=g++-8 CC=gcc-8 && make plugins CXX=g++-8 CC=gcc-8
	      rm -rf ./util/support_scripts/tests && cd ..  # It is not compatible with python 3 and pytest!
	      # The version of sra-tools in macOS channel is not the latest, so don't specify it here.
	      # The default version of samtools is 1.4, which doesn't work, so set it to the latest (1.10).
	      conda install -qy python="$PYTHON" sra-tools numpy bowtie bowtie2 kmer-jellyfish salmon trimmomatic samtools=1.10
    ;;
esac
mkdir -p "${HOME}"/.ncbi
cat > "${HOME}"/.ncbi/user-settings.mkfg <<_EOF
## auto-generated configuration file - DO NOT EDIT ##

/LIBS/GUID = "$(uuidgen)"
/config/default = "false"
/repository/user/ad/public/apps/file/volumes/flatAd = "."
/repository/user/ad/public/apps/refseq/volumes/refseqAd = "."
/repository/user/ad/public/apps/sra/volumes/sraAd = "."
/repository/user/ad/public/apps/sraPileup/volumes/ad = "."
/repository/user/ad/public/apps/sraRealign/volumes/ad = "."
/repository/user/ad/public/root = "."
/repository/user/default-path = "${HOME}/ncbi"

_EOF

conda clean -ayq
