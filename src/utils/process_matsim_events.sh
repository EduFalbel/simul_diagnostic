#!/bin/bash

echo "time,type,link_id,vehicle" > $2 && zcat $1 | parallel -q --pipe awk 'BEGIN {FS= "\""; RS="\n"} /"entered link"/ {printf "%f,%s,%d,%d\n", $2, $4, $6, $8}' >> $2

# parallel -a $1 awk -f "$(dirname $(realpath ${BASH_SOURCE[0]}))/matsim_events.awk" >> $2