#!/usr/bin/env python3
"""
 Copyright (c) 2020 Alp Sayin <alpsayin@alpsayin.com>, Novit.ai <info@novit.ai>
 
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
 
"""


cities = {
          'istanbul': [40.84706035607121, 41.615442324681084, 27.95196533203125, 30.009155273437496],
          'milan': [44.46123053905879, 46.72480037466718, 8.1793212890625, 11.865234374999998],
          'wuhan': [29.933120, 31.454347, 113.538980, 115.181099],
          'london': [51.1250115157, 51.8933934843, -1.1526639707, 0.9045259707],
          'barcelona': [40.9992880157, 41.7676699843, 1.1223435293, 3.1795334707],
          'paris': [48.4849910157, 49.2533729843, 1.3415960293, 3.3987859707],
          'new york': [40.328609015695065, 41.09699098430494, -75.03459497070313, -72.97740502929688],
          'los angeles': [33.66800901569506, 34.436390984304936, -119.27229497070313, -117.21510502929688],
          'moscow': [55.371609015695064, 56.13999098430494, 36.588705029296875, 38.645894970703125],
          'tokyo': [35.29620901569506, 36.064590984304935, 138.74040502929688, 140.79759497070313],
          'kiev': [50.071748015695064, 50.84012998430494, 29.530153029296876, 31.587342970703126],
          'minsk': [53.132218031390124, 54.66898196860987, 25.501810058593755, 29.616189941406247],
          'stockholm': [58.56091803139013, 60.097681968609876, 16.011410058593754, 20.125789941406246],
          'seoul': [36.798118031390125, 38.33488196860987, 124.92081005859374, 129.03518994140623],
          'hong kong': [21.764951031390126, 23.301714968609872, 111.67614305859375, 115.79052294140625],
          'ankara': [39.165018031390126, 40.70178196860987, 30.80251005859375, 34.91688994140624],
          }


def generate_city_bounds_from_centre(center, template=cities['istanbul']):
    halflat, halflon = template[1]-template[0], template[3]-template[2]
    return center[0]-halflat, center[0]+halflat, center[1]-halflon, center[1]+halflon


def dump_to_json_or_stdout(output_file=None, *args, **kwargs):
    import json
    import sys

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w') as fid:
            json.dump(cities, fid)
    else:
        json.dump(cities, sys.stdout)
        sys.stdout.write('\n')


def main():
    from argparse import ArgumentParser
    from pathlib import Path
    parser = ArgumentParser(description='Exports cities as json')
    parser.add_argument('-o', '--output', dest='output_file', type=Path, help='Output file for json export. Dumps to stdout if omitted')
    args = parser.parse_args()
    print(args)
    vargs = vars(args)
    filtered_vargs = vargs.copy()
    for key, val in vargs.items():
        if val is None:
            del filtered_vargs[key]

    dump_to_json_or_stdout(**filtered_vargs)


if __name__ == '__main__':
    main()
