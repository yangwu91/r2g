#!/bin/bash

for I in {0..99}; do
    CMD="/usr/bin/python /home/wuyang/softwares/eggnog-mapper/emapper.py --cpu 10 -i formal_test_1/Anopheles-stephensi-Indian_transcripts_AsteI2.3.fa-randomquery_${I}.fasta --output_dir ./formal_test_1-eggnog  -o randomquery_${I} -m diamond -d none --tax_scope 50557 --go_evidence non-electronic --target_orthologs all --seed_ortholog_evalue 0.001 --seed_ortholog_score 60 --query-cover 20 --subject-cover 0 --override --translate"
    echo $CMD &&
    $CMD &&
    echo "###########"
done
