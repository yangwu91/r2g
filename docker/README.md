
# R2g Docker

![docker](https://img.shields.io/docker/cloud/build/yangwu91/r2g?logo=docker&style=plastic) ![License](https://img.shields.io/github/license/yangwu91/r2g?logo=open-source-initiative&style=plastic)

<div align=center><img src="https://raw.githubusercontent.com/yangwu91/r2g/master/images/banner.png" alt="banner"/></div>

## Introduction

**Reads to genes**, or **r2g**, is a computationally lightweight and homology-based pipeline that allows rapid identification of genes or gene families from raw sequence databases in the absence of an assembly, by taking advantage of  over 10,000 terabases of sequencing data for all kinds of species deposited in  [Sequence Read Archive](https://www.ncbi.nlm.nih.gov/sra) hosted by [National Center for Biotechnology Information](https://www.ncbi.nlm.nih.gov/), which can be effectively run on **most common computers without high-end specs**.

You can find source code of the r2g project [here](https://github.com/yangwu91/r2g).

This docker integrates required third-party applications and the r2g itself, which is ready to go.

## Running the images
### Print detailed usages
```bash
docker run -it -v /dev/shm:/dev/shm -v /dir/to/your/folder:/workspace -u $UID yangwu91/r2g:latest --help
```
To avoid the applications crashing inside a docker container, the option `-v /dev/shm:/dev/shm` is recommended to be used, or tune the value `--shm-size=8g` in your specific cases.

In the command, the option `-v /dir/to/your/folder:/workspace` will mount your folder `/dir/to/your/folder` onto the Docker.

### Debug mode

Enter an interactive shell to debug:

```bash
docker run -it yangwu91/r2g:latest debug
```

### An example command

```
docker run -it -v /dev/shm:/dev/shm -v /dir/to/your/folder:/workspace yangwu91/r2g:latest -o OUTPUT -s SRXNNNNNN -q QUERY.fasta --cut 80,50 -p blastn
```
After that, you can find the results in the folder `/dir/to/your/folder/OUTPUT/`.