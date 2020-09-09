#!/bin/bash

cat <<_EOF
{
  "Trinity": "$(which Trinity)",
  "fastq-dump": "$(which fastq-dump)",
  "chromedriver": "$(which chromedriver)"
}
_EOF
