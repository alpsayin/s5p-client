#!/usr/bin/env python3

import simplejson
from pathlib import Path
from datetime import datetime
import traceback
from argparse import ArgumentParser, RawTextHelpFormatter
from pprint import pprint
from shutil import rmtree
from s5p_averager import s5p_averager
from s5p_cities import cities as skybase_cities, dump_to_json_or_stdout
import warnings


WEBROOT = Path.home()/'/s5p-data/data/'
DATE_FORMAT = '%Y-%m-%d'


def grid_size_finder(lat1, lat2, lon1, lon2):
    grid_size = [round(abs(lon2-lon1)*25), round(abs(lat2-lat1)*30)]  # approximate numbers found by trial&error. a better method would be to have 4-10 points per 7.5km2
    grid_size = [dim if dim>10 else 10 for dim in grid_size]
    return grid_size
    # return [50, 50]  # approximate numbers found by trial&error. a better method would be to have 4-10 points per 7.5km2


def generate_summaries(output_folder=WEBROOT, data_type='raw', cities=skybase_cities.keys(), delete_broken=False, num_days=11):
    if data_type == 'raw':
        filename_postfix = ''
    elif data_type == 'interpolated':
        filename_postfix = '_interpd'
    elif data_type == 'averaged':
        filename_postfix = '_avg10'
    city_folders = sorted([city_folder for city_folder in output_folder.iterdir() if city_folder.is_dir() and city_folder.name in cities])
    for city_folder in city_folders:
        # print(f'% inside {city_folder.name}')
        city_name = city_folder.name
        product_folders = [product_folder for product_folder in city_folder.iterdir() if product_folder.is_dir()]
        city_summary_dict = dict()
        for product_folder in product_folders:
            print(f'% generating summary {data_type} for {city_name}-{product_folder.name}')
            if product_folder.name != 'NO2':
                warnings.warn('TEMPORARILY SKIPPING ANYTHING BUT NO2 FOLDERS')
                continue
            product_summary_dict = dict()
            date_folders = [date_folder for date_folder in product_folder.iterdir() if date_folder.is_dir()]
            date_folders.sort(reverse=True, key=lambda foldername: datetime.strptime(foldername.name, DATE_FORMAT))
            for date_folder in date_folders:
                print(f'\r\t%% Counting {date_folder.name}', end='')
                json_filepath = date_folder/f'{city_folder.name}{filename_postfix}.json'
                try:
                    json_fid = json_filepath.open('r')
                    data = simplejson.load(json_fid)
                    product_summary_dict[date_folder.name] = dict(min=data['min'],
                                                                  max=data['max'],
                                                                  mean=data['mean'],
                                                                  size=len(data['data']),)
                except FileNotFoundError as fnferr:
                    print(f'\n\t{fnferr.__class__.__name__} : Couldnt find json file {json_filepath}. NC file may be broken.')
                    if delete_broken:
                        try:
                            rmtree(date_folder, ignore_errors=True)
                        except Exception as ex:
                            print(f'{ex.__class__}: {ex}')
                            print(f'Couldnt delete date folder in Cleanup mode {date_folder}')
                            traceback.print_exc()
                except Exception as ex:
                    print(f'{ex.__class__}: {ex}')
                    print(f'Couldnt load json file {json_filepath}')
                    # traceback.print_exc()
            print('\n')
            city_summary_dict[product_folder.name] = product_summary_dict
            city_summary_dict['city'] = city_folder.name
        try:
            summary_filepath = city_folder/f'summary{filename_postfix}.json'
            summary_fid = open(summary_filepath, 'w+')
            simplejson.dump(city_summary_dict, summary_fid, ignore_nan=True)
        except Exception as ex:
            print(f'{ex}')
            print(f'Couldnt dump summary to {summary_filepath}')
            traceback.print_exc()


def call_interpolater(output_folder, num_days, cities=skybase_cities.keys(), *args, **kwargs):
    city_folders = sorted([city_folder for city_folder in output_folder.iterdir() if city_folder.is_dir() and city_folder.name in cities])
    for city_folder in city_folders:
        # print(f'% inside {city_folder.name}')
        city_name = city_folder.name
        city_grid_size = grid_size_finder(*skybase_cities[city_name])
        print(f'{city_name.upper()} city_grid_size={city_grid_size}')
        s5p_averager(cities=[city_name], data_folder=Path(output_folder), grid_size=city_grid_size.copy(), window_size=10, num_days=num_days, plot=False, silent=True)


def main():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter, description=f'S5P Query and Download Tool'
'''
Quick start:
    Generate for skybase webroot with hardcoded webroot:
        python s5p_summary_generator.py

    Iterate and generate over manual webroot:
        python s5p_summary_generator.py -tf /tmp/test/fake_s5p_root/

    Cleanup mode: Deletes relevant NC files if no JSON is found inside a dir. This probably happens because NC file is corrupt:
        python s5p_summary_generator.py -d
''')
    parser.add_argument('-d', '--delete', '--delete-broken', dest='delete_broken', action='store_true', help='This will delete the relevant NC files if no JSON file is found within a directory.')
    parser.add_argument('-tf', '-of', '--target-folder', '--output-folder', default=WEBROOT, dest='output_folder', type=Path, help='Output file directory for downloads')
    parser.add_argument('-n', '--num-days', type=int, default=11, help='Number of last days to process for running averager. Default: 11')
    parser.add_argument('-c', '--cities', type=str, action='append', help=f'Major city name as string')
    args = parser.parse_args()
    print(args)
    vargs = vars(args)

    filtered_vargs = vargs.copy()
    for key, val in vargs.items():
        if val is None:
            del filtered_vargs[key]
    pprint(filtered_vargs)

    output_folder = filtered_vargs['output_folder']
    dump_to_json_or_stdout(output_file=output_folder/'cities.json')
    call_interpolater(**filtered_vargs)

    for data_type in ['raw', 'interpolated', 'averaged']:
        print(f' >>> GENERATING SUMMARIES FOR {data_type} DATA')
        generate_summaries(data_type=data_type, **filtered_vargs)


if __name__ == '__main__':
    main()
