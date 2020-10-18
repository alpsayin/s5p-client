#!/bin/bash
echo "start $1"
date
source pyenv/bin/activate
if [ -z "$1" ]
then
    # echo "\$1 is empty"
    curday=$(date +%Y-%m-%d)
else
    # echo "\$1 is NOT empty"
    curday=$1
fi
mkdir -p "$HOME/s5p-data/data"
mkdir -p "/tmp/s5p-data/data"
pyenv/bin/python3 s5p.py populate -df $curday -dt $curday -d -j -tf /tmp/s5p-data/data/ -r 20 -ap 5
touch -a "$HOME/s5p-data/excluded.txt"
rsync -va --exclude='*.nc' --exclude-from "$HOME/s5p-data/excluded.txt" --info="progress2" /tmp/s5p-data/data $HOME/s5p-data/
pyenv/bin/python3 s5p_summary_generator.py -tf $HOME/s5p-data/data/
date
echo "finish $1"
