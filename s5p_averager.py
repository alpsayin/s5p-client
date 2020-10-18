#!/usr/bin/env python3

import numpy as np
import simplejson
from pathlib import Path
from pprint import pprint, pformat
import argparse
import shutil
import scipy
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import warnings
import traceback

from s5p import ProductType
from s5p_cities import cities as skybase_cities

DATE_FORMAT = "%Y-%m-%d"
USE_NONGUI_BACKEND = True
SILENT = True


def silencable_print(*args, **kwargs):
    if not SILENT:
        print(*args, **kwargs)


def extrapolate_nans(x, y, v):
    '''  
    Extrapolate the NaNs or masked values in a grid INPLACE using nearest
    value.

    .. warning:: Replaces the NaN or masked values of the original array!

    Parameters:

    * x, y : 1D arrays
        Arrays with the x and y coordinates of the data points.
    * v : 1D array
        Array with the scalar value assigned to the data points.

    Returns:

    * v : 1D array
        The array with NaNs or masked values extrapolated.
    '''

    if np.ma.is_masked(v):
        nans = v.mask
    else:
        nans = np.isnan(v)
    notnans = np.logical_not(nans)
    v[nans] = scipy.interpolate.griddata((x[notnans], y[notnans]), v[notnans], (x[nans], y[nans]), method='nearest').ravel()
    return v


def interpolation2d(x, y, z, latlon_bounds, grid_size):

    x = np.array(x)
    y = np.array(y)
    z = np.array(z)
    # data coordinates and values
    silencable_print(f'lon,lat & value.shape:{x.shape}')
    min_lat, max_lat, min_lon, max_lon = latlon_bounds
    silencable_print(f'minlon:{min_lon},maxlon:{max_lon},minlat:{min_lat},maxlat:{max_lat}')

    ## target grid to interpolate to
    # xi = np.arange(min_lon,max_lon, 0.003)
    # yi = np.arange(min_lat,max_lat,0.003)
    # xi,yi = np.meshgrid(xi,yi)
    # silencable_print(f'target_latlon.shape:{xi.shape}')

    # target grid to interpolate to
    xi, yi = np.mgrid[min_lon:max_lon:1j*grid_size[0], min_lat:max_lat:1j*grid_size[1]]
    silencable_print(f'target_latlon.shape:{xi.shape}')

    # # set mask
    # mask = (xi > lon1_mask) & (xi < lon2_mask) & (yi > lat1_mask) & (yi < lat2_mask)

    # interpolate
    zi = griddata((x, y), z, (xi, yi), method='cubic')
    silencable_print(f'result.shape:{zi.shape}')

    # # mask out the field
    # zi[mask] = np.nan
    # Do not uncomment below unless you've commented the line above
    if np.all(np.isnan(zi)):
        return xi, yi, zi

    try:
        zi = extrapolate_nans(xi, yi, zi)
    except Exception as ex:
        print(f'xi={xi}')
        print(f'yi={yi}')
        print(f'zi={zi}')
        traceback.print_exc()
        raise ex
    # returns targeted lon, lat, interpolation result zi, original lon, lat, and product value numpy arrays
    return xi, yi, zi


def lists_to_latlonval_list(xlist, ylist, zlist):
    return [[x, y, z] for x, y, z in zip(xlist, ylist, zlist)]


def griddata_to_latlonval_list(xi, yi, zi):
    nonNan_lon_list = xi.compressed().tolist()
    nonNan_lat_list = yi.compressed().tolist()
    nonNan_value_list = zi.compressed().tolist()
    return lists_to_latlonval_list(nonNan_lat_list, nonNan_lon_list, nonNan_value_list)


def plot_griddata(gridded_data, scatter_data, title, output_filename):
    xi, yi, zi = gridded_data
    x, y, z = scatter_data
    plt.contourf(xi, yi, zi)
    plt.scatter(x, y, c=z)
    plt.title(title)
    plt.xlabel('xi', fontsize=12)
    plt.ylabel('yi', fontsize=12)
    plt.colorbar()
    plt.savefig(output_filename, dpi=100)
    plt.close()


def s5p_averager(cities: list = list(skybase_cities.keys()), data_folder: Path = Path.home()/'/s5p-data/data/', grid_size: list = [50, 50], window_size: int = 10, num_days: int = 11, plot: bool = False, silent: bool = False):
    global SILENT
    SILENT = silent
    plotdata_folder = data_folder.parent/f'plotdata'
    for city in cities:
        city_folder = data_folder/city
        print(f'% s5p_averager: inside {city_folder}')
        city_plot_folder = plotdata_folder/city
        product_folders = [f for f in (city_folder).iterdir() if f.is_dir()]
        for product_folderpath in product_folders:
            print(f'\t%% s5p_averager: inside {product_folderpath}')
            product_type = product_folderpath.name
            if product_type != 'NO2':
                warnings.warn('TEMPORARILY SKIPPING ANYTHING BUT NO2 FOLDERS')
                continue
            city_product_plot_folder = city_plot_folder/product_type
            if plot:
                city_product_plot_folder.mkdir(exist_ok=True, parents=True)
            product_data_folders = [f for f in product_folderpath.iterdir() if f.is_dir()]
            product_data_folders = sorted(product_data_folders, key=lambda fpath: datetime.strptime(fpath.name, DATE_FORMAT), reverse=False)
            rawdata_json_files = [date_folderpath/f'{city}.json' for date_folderpath in product_data_folders if (date_folderpath/f'{city}.json').exists()]
            rawdata_json_files = sorted(rawdata_json_files, key=lambda fpath: datetime.strptime(fpath.parent.name, DATE_FORMAT), reverse=False)
            # pprint(rawdata_json_files)
            minlat, maxlat, minlon, maxlon = skybase_cities[city]
            # minlat, maxlat, minlon, maxlon = np.inf, -np.inf, np.inf, -np.inf
            # for file_index, filename in enumerate(rawdata_json_files):
            #     silencable_print(f'\n%%% Processing {filename}')
            #     file_date = filename.parent.name
            #     with open(filename, 'r') as json_file:
            #         data_dict = simplejson.load(json_file)
            #         product_data = data_dict['data']
            #         data_num = len(product_data)
            #         if data_num < 4:
            #             continue
            #         units = data_dict['units']

            #         asnparray = np.array(product_data, dtype=float)
            #         lats = asnparray[:, 0]
            #         lons = asnparray[:, 1]
            #         values = asnparray[:, 0]
            #         minlat = lats.min() if lats.min() < minlat else minlat
            #         maxlat = lats.max() if lats.max() > maxlat else maxlat
            #         minlon = lons.min() if lons.min() < minlon else minlon
            #         maxlon = lons.max() if lons.max() > maxlon else maxlon

            silencable_print(f'{minlat}, {maxlat}, {minlon}, {maxlon}')
            # input('wait here')
            averaging_window = np.ma.zeros((window_size, *grid_size))
            averaging_window.mask = np.ma.ones(shape=averaging_window.shape)
            rawdata_json_files = rawdata_json_files[-num_days:]
            for file_index, filename in enumerate(rawdata_json_files):
                print(f'\t\t%%% interpolating and then averaging: {filename.relative_to(data_folder)}')
                file_date = filename.parent.name
                with open(filename, 'r') as json_file:
                    data_dict = simplejson.load(json_file)
                    product_data = data_dict['data']
                    data_num = len(product_data)
                    if data_num < 4:
                        continue
                    units = data_dict['units']

                    asnparray = np.array(product_data, dtype=float)
                    lats = asnparray[:, 0]
                    lons = asnparray[:, 1]
                    values = asnparray[:, 2]

                    xi, yi, zi = interpolation2d(lons, lats, values, (minlat, maxlat, minlon, maxlon), grid_size)
                    combined_mask = np.isnan(xi) | np.isnan(yi) | np.isnan(zi)
                    xi = np.ma.MaskedArray(xi, mask=combined_mask)
                    yi = np.ma.MaskedArray(yi, mask=combined_mask)
                    zi = np.ma.MaskedArray(zi, mask=combined_mask)
                    stats = dict(min=float(zi.min()),
                                 max=float(zi.max()),
                                 mean=float(zi.mean()),
                                 variance=float(zi.var()),
                                 stddev=float(zi.std()),)

                    interpd_data_list = griddata_to_latlonval_list(xi, yi, zi)
                    data_dict['data'] = interpd_data_list
                    data_dict.update(stats)
                    with open(filename.parent/f'{city}_interpd.json', 'w') as json_file:
                        simplejson.dump(data_dict, json_file)

                    # running average calculations
                    silencable_print(f'averaging_window.mask.shape = {averaging_window.mask.shape}')
                    # rolled_mask = np.roll(averaging_window.mask, 1, axis=0)
                    averaging_window = np.roll(averaging_window, 1, axis=0)
                    averaging_window[0, :, :] = zi

                    averaged_zi = averaging_window.mean(axis=0)
                    silencable_print(averaged_zi.shape)
                    averaged_xi = np.ma.MaskedArray(xi, mask=averaged_zi.mask)
                    averaged_yi = np.ma.MaskedArray(yi, mask=averaged_zi.mask)
                    stats = dict(min=float(averaged_zi.min()),
                                 max=float(averaged_zi.max()),
                                 mean=float(averaged_zi.mean()),
                                 variance=float(averaged_zi.var()),
                                 stddev=float(averaged_zi.std()),)

                    avg_data_list = griddata_to_latlonval_list(averaged_xi, averaged_yi, averaged_zi)

                    data_dict['data'] = avg_data_list
                    data_dict.update(stats)
                    with open(filename.parent/f'{city}_avg{window_size}.json', 'w') as json_file:
                        simplejson.dump(data_dict, json_file)

                    if plot:
                        title = f'Interpolated {product_type} concentration in {city}({units}) '
                        output_filename = city_product_plot_folder/f'{file_date}_interpd.png'
                        plot_griddata((xi, yi, zi), (lats, lons, values), title, output_filename)

                        title = f'{window_size}-Averaged {product_type} concentration in {city}({units}) '
                        output_filename = city_product_plot_folder/f'{file_date}_avg{window_size}.png'
                        plot_griddata((averaged_xi, averaged_yi, averaged_zi), (lats, lons, values), title, output_filename)


def main():
    parser = argparse.ArgumentParser(description='Run pollution_metric.py on cities')
    parser.add_argument('-c', '--cities', default=list(skybase_cities.keys()), action='store', nargs='+')
    parser.add_argument('-tf', '-of', '--target-folder', '--output-folder', '--webroot', dest='data_folder', default=Path.home()/'/s5p-data/data/', type=Path, help='Output file directory for downloads. This should be the webroot. Defaults to "$HOME/s5p-data/data/" ')
    parser.add_argument('-p', '--plot', action='store_true', help='Plot the created grids')
    parser.add_argument('-s', '--silent', action='store_true', help='Dont output anything')
    parser.add_argument('-ws', '--window-size', type=int, default=10, help='Window size for running averager. Default: 10')
    parser.add_argument('-gs', '--grid-size', type=int, nargs=2, default=[50, 50], help='Grid size to interpolate to. Default: [50, 50]')
    parser.add_argument('-n', '--num-days', type=int, default=11, help='Number of last days to process for running averager. Default: 11')
    args = vars(parser.parse_args())
    print(args)

    if args['plot'] and USE_NONGUI_BACKEND:
        matplotlib.use('Agg')

    s5p_averager(**args)


if __name__ == '__main__':
    main()
