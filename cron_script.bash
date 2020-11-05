#!/bin/bash

#  Copyright (c) 2020 Alp Sayin <alpsayin@alpsayin.com>, Novit.ai <info@novit.ai>
 
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
 
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE

#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

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
# pyenv/bin/python3 s5p.py populate -df $curday -dt $curday -d -j -tf /tmp/s5p-data/data/ -r 20 -ap 5 # will download all predefined cities
pyenv/bin/python3 s5p.py populate -df $curday -dt $curday -d -j -tf /tmp/s5p-data/data/ -r 20 -ap 5 -c milan -c barcelona -c paris
touch -a "$HOME/s5p-data/excluded.txt"
rsync -va --exclude='*.nc' --exclude-from "$HOME/s5p-data/excluded.txt" --info="progress2" /tmp/s5p-data/data $HOME/s5p-data/
pyenv/bin/python3 s5p_summary_generator.py -tf $HOME/s5p-data/data/
date
echo "finish $1"
