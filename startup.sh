#!/usr/bin/env bash
#source /home/miniconda3/bin/activate
#conda activate tgcli

path="$(cd "$(dirname $0)" && pwd)"
script="${path}/start.py"
nohup python3 ${script} > /dev/null 2>&1 &

