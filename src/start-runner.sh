#!/bin/bash

cd "$(dirname "$0")"
sudo nohup python3.8 runner.py > ./output.log 2>&1 </dev/null &
