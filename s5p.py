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

import pycurl
from io import BytesIO
import certifi
from urllib.parse import urlencode, quote as urllib_quote
from functools import partial
from pprint import pprint, pformat
import simplejson
import time
from enum import Enum
from typing import Union, Tuple, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
from argparse import ArgumentParser, RawTextHelpFormatter
from netCDF4 import Dataset as netcdf_dataset
import geojsoncontour
import cartopy.crs as ccrs
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import json
import traceback
import sys
from s5p_cities import cities
import random

GEOJSON_AREA_MATCH_CONDITION = 'Contains'  # another alternative is 'Intersects
TURKEY_LATLON_BOUNDS = [35.9025, 42.02683, 25.90902, 44.5742]
USE_NONGUI_BACKEND = True

if USE_NONGUI_BACKEND:
    matplotlib.use('Agg')


def construct_headers(headers_dict: dict) -> list:
    ret_list = list()
    for key, val in headers_dict.items():
        ret_list.append(f'{key}: {val}')
    return ret_list


def cookies_as_dict(cookies: list) -> dict:
    return {'Cookie: ': '; '.join(cookies)}


def login_required(func: Callable) -> Callable:
    def check_login_status_and_call(*args, **kwargs):
        _self = args[0]
        if not isinstance(_self, S5PSession):
            print(
                f'Decorator not compatible with this function; use it on a S5PSession\'s member functions')
        if _self.login_http_status != '200 OK':
            print(f'Login status not OK; try logging in first/again')
            return None
        else:
            print(f'Login status OK')
            return func(*args, **kwargs)
    return check_login_status_and_call


def format_product_summary(product: dict):
    s = ''
    s += f'{product["summary"][0]}\n'
    s += f'{product["summary"][-1]}\n'
    s += f'UUID: {product["uuid"]}\n'
    s += f'https://s5phub.copernicus.eu/dhus/odata/v1/Products(\'{product["uuid"]}\')/$value\n'
    s += f'Identifier: {product["identifier"]}\n'
    s += f'offline: {product["offline"]}\n'
    s += f'ProcessingMode: {product["indexes"][1]["children"][7]["value"]}\n'
    s += f'productType: {product["productType"]}'
    return s


def print_product_summary(product: dict):
    print(format_product_summary(product))


def clip_netcdf_data(plotme_nc, lats_nc, lons_nc, bounds: Tuple[float, float, float, float] = None, city: str = None, *args, **kwargs) -> Path:

    # netcdf to numpy
    plotme_np = plotme_nc[:]
    lats_np = lats_nc[:]
    lons_np = lons_nc[:]

    # reduce dimensions to only what's needed
    plotme_np = plotme_np[0, :, :]
    lats_np = lats_np[0, :, :]
    lons_np = lons_np[0, :, :]

    # create bounds masks
    bounds = bounds if bounds else cities[city] if city else (-360, 360, -360, 360)  # basically implying use no bounds
    print(f'BOUNDS = {bounds}')
    lat1, lat2, lon1, lon2 = bounds
    lat1_mask = lats_np >= lat1
    lat2_mask = lats_np <= lat2
    lon1_mask = lons_np >= lon1
    lon2_mask = lons_np <= lon2
    bounds_mask = lat1_mask & lat2_mask & lon1_mask & lon2_mask
    # apply bounds mask and existings masks
    plotme_np.mask = ~bounds_mask | plotme_np.mask
    # mask values with FillValue to ensure no illegal value stays unmasked
    plotme_np.mask = plotme_np.mask | (plotme_np == plotme_nc._FillValue)
    lats_np.mask = plotme_np.mask
    lons_np.mask = plotme_np.mask

    # reduce shape to only what's needed
    plotme_np = plotme_np[:, ~np.all(plotme_np.mask, axis=0)]
    plotme_np = plotme_np[~np.all(plotme_np.mask, axis=1), :]

    lats_np = lats_np[:, ~np.all(lats_np.mask, axis=0)]
    lats_np = lats_np[~np.all(lats_np.mask, axis=1), :]

    lons_np = lons_np[:, ~np.all(lons_np.mask, axis=0)]
    lons_np = lons_np[~np.all(lons_np.mask, axis=1), :]

    return plotme_np, lats_np, lons_np


def extract_product_essentials(rootgrp) -> Tuple[str, str, str, str]:
    product_type_raw = rootgrp['METADATA']['ESA_METADATA']['earth_explorer_header']['fixed_header'].File_Type
    product_type = ProductType(product_type_raw)
    var_name = product_type.var_name()

    validity_start = rootgrp['METADATA']['ESA_METADATA']['earth_explorer_header']['fixed_header']['validity_period'].Validity_Start
    validity_stop = rootgrp['METADATA']['ESA_METADATA']['earth_explorer_header']['fixed_header']['validity_period'].Validity_Stop
    description = rootgrp['METADATA']['ESA_METADATA']['earth_explorer_header']['fixed_header'].File_Description

    cut_from = description.find('observed')-1
    description = description[:cut_from if cut_from>0 else len(description)]
    plotme_nc = rootgrp['PRODUCT'][var_name]
    long_name = plotme_nc.long_name
    # some products have File_Description and othershave long_name. Below block helps choose from them
    if not description:
        description = long_name

    units = plotme_nc.units

    # grab data grid
    plotme_nc = rootgrp['PRODUCT'][var_name]
    lats_nc = rootgrp['PRODUCT']['latitude']
    lons_nc = rootgrp['PRODUCT']['longitude']

    return plotme_nc, lats_nc, lons_nc, description, units, validity_start, validity_stop


class DownloadProgressTracker(object):
    """DownloadProgressTracker"""
    def __init__(self, fid, refresh_period=0.5, abort_period=np.inf):
        super(DownloadProgressTracker, self).__init__()
        self.start_time = None
        self.prev_time = None
        self.prev_download_d = 0
        self.refresh_period = refresh_period
        self.fid = fid
        self.abort_counter = 0
        self.abort_period = abort_period

    def progress(self, download_t, download_d, upload_t, upload_d):
        if not self.start_time:
            self.start_time = time.time()
            self.prev_time = time.time()
        now = time.time()
        if now - self.prev_time < self.refresh_period:
            return
        if download_t == 0:
            # print(f'Why is download_t == {download_t}?')
            return
        avg_speed_kbs = download_d/(now-self.start_time)/1024  # KBs per sec
        cur_speed_kbs = float(download_d-self.prev_download_d)/(now-self.prev_time)/1024.0  # KBs per sec
        print(f'\rDownloaded %{100*download_d/download_t:.2f} - {download_d/1024/1024:.2f}/{download_t/1024/1024:.2f} MB - Avg {avg_speed_kbs:0.2f} kb/s - Cur {cur_speed_kbs:0.2f} kb/s            ', end='')
        if download_d == download_t:
            print('')
        if self.prev_download_d == download_d:
            self.abort_counter += 1
        else:
            self.abort_counter = 0
        if self.abort_counter*self.refresh_period > self.abort_period:
            DownloadProgressTracker.aborted_once = True
            raise Exception(f'Download aborted due to no progress in {self.abort_period} seconds')
        self.prev_time = now
        self.prev_download_d = download_d


class ProductType(Enum):
    '''AER_AI, AER_LH, NO2,  CO, CH4, SO2, HCHO, O3, O3_TCL, CLOUD'''
    AER_AI = 'L2__AER_AI'
    AER_LH = 'L2__AER_LH'
    NO2 = 'L2__NO2___'
    CO = 'L2__CO____'
    CH4 = 'L2__CH4___'
    SO2 = 'L2__SO2___'
    HCHO = 'L2__HCHO__'
    O3 = 'L2__O3____'
    O3_TCL = 'L2__O3_TCL'
    CLOUD = 'L2__CLOUD_'

    def var_name(self):
        var_name_dict = {'AER_AI': 'aerosol_index_340_380',
                         'AER_LH': 'aerosol_mid_height',
                         'NO2': 'nitrogendioxide_tropospheric_column',
                         'CO': 'carbonmonoxide_total_column',
                         'CH4': 'methane_mixing_ratio_bias_corrected',
                         'SO2': 'sulfurdioxide_total_vertical_column',
                         'HCHO': 'formaldehyde_tropospheric_vertical_column',
                         'O3': 'ozone_total_vertical_column',
                         'O3_TCL': '',  # product not yet ready
                         'CLOUD': 'cloud_optical_thickness',
                         }
        return var_name_dict[self.name]


class ProcessingMode(Enum):
    '''NRT, OFFLINE, RPRO'''
    NRT = 'Near real time'
    OFFLINE = 'Offline'
    RPRO = 'Reprocessing'


class S5PSession(object):
    """S5PSession session object holds cookies for querying and downloading products"""
    SHARED_HEADERS_DICT = {'Connection': 'keep-alive',
                           'Pragma': 'no-cache',
                           'Cache-Control': 'no-cache',
                           'DNT': '1',
                           'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
                           'X-Requested-With': 'XMLHttpRequest',
                           'Origin': 'https://s5phub.copernicus.eu',
                           'Sec-Fetch-Site': 'same-origin',
                           'Referer': 'https://s5phub.copernicus.eu/dhus/',
                           'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8',
                           # 'Accept-Encoding': 'gzip, deflate, br',
                           }
    LOGIN_HEADERS_DICT = {'Accept': 'application/json, text/plain, */*',
                          'Content-Type': 'application/x-www-form-urlencoded',
                          'Sec-Fetch-Dest': 'empty',
                          'Sec-Fetch-Mode': 'cors',
                          }
    QUERY_HEADERS_DICT = {'Accept': 'application/json, text/plain, */*',
                          'Sec-Fetch-Dest': 'empty',
                          'Sec-Fetch-Mode': 'cors',
                          }
    DOWNLOAD_HEADERS_DICT = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                             'Upgrade-Insecure-Requests': '1',
                             'Sec-Fetch-Dest': 'document',
                             'Sec-Fetch-Mode': 'navigate',
                             'Sec-Fetch-User': '?1',
                             }

    def __init__(self, username='s5pguest', password='s5pguest', *args, **kwargs):
        super(S5PSession, self).__init__()
        self.username = username if username else 's5pguest'
        self.password = password if password else 's5pguest'
        self.cookies = list()
        self.login_http_status = None
        self.query_http_status = None
        self.query_results_cache = list()
        self.download_content_length = None

    def login(self, verbose: bool = False, *args, **kwargs):
        '''
        Imitates the curl request below. This should return 3 Set-Cookie Headers we must capture and save
        curl 'https://s5phub.copernicus.eu/dhus//login' -H 'Connection: keep-alive' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'DNT: 1' -H 'Authorization: Basic czVwZ3Vlc3Q6czVwZ3Vlc3Q=' -H 'Content-Type: application/x-www-form-urlencoded' -H 'Accept: application/json, text/plain, */*' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36' -H 'Sec-Fetch-Dest: empty' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: https://s5phub.copernicus.eu' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-Mode: cors' -H 'Referer: https://s5phub.copernicus.eu/dhus/' -H 'Accept-Language: en-GB,en;q=0.9,tr-TR;q=0.8,tr;q=0.7,en-US;q=0.6' -H 'Cookie: JSESSIONID=2901D963D3643D3E43FAB3E5329ED4C8' --data 'login_username=s5pguest&login_password=s5pguest'

        '''
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(c.URL, 'https://s5phub.copernicus.eu/dhus//login')
        c.setopt(c.CAINFO, certifi.where())
        c.setopt(c.FOLLOWLOCATION, True)
        c.setopt(c.WRITEDATA, buffer)
        # login_username=s5pguest&login_password=s5pguest
        login_data = {'login_username': f'{self.username}',
                      'login_password': f'{self.password}'}
        postfields = urlencode(login_data, quote_via=urllib_quote)
        c.setopt(pycurl.POSTFIELDS, postfields)
        c.setopt(pycurl.HTTPPOST, [])
        c.setopt(pycurl.VERBOSE, verbose)
        c.setopt(pycurl.ENCODING, b"gzip, deflate, br")
        headers_list = list()
        headers_list += construct_headers(S5PSession.SHARED_HEADERS_DICT)
        headers_list += construct_headers(S5PSession.LOGIN_HEADERS_DICT)
        c.setopt(pycurl.HTTPHEADER, headers_list)

        # closure to capture Set-Cookie
        def _write_header(header, verbose):
            header = header.decode('utf-8').strip()
            if verbose:
                print(f'Captured Header: {header}')
            if header.startswith('HTTP/1.1 '):
                self.login_http_status = header[len('HTTP/1.1 '):]
            if header.startswith(f'Set-Cookie: '):
                cookie = header[len('Set-Cookie: '):]
                parts = cookie.split(';')
                cookie = parts[0]
                self.cookies.append(cookie)

        # use closure to collect cookies sent from the server
        self.cookies = list()
        c.setopt(pycurl.HEADERFUNCTION, partial(_write_header, verbose=verbose))
        c.perform()
        c.close()

        # print(self.cookies)

    @login_required
    def query(self, bounds: Tuple[float, float, float, float] = None, city: str = None, date_from: datetime = None, date_to: datetime = None, product_type: ProductType = ProductType.NO2, processing_mode: ProcessingMode = ProcessingMode.NRT, offset=0, limit=25, verbose=False, *args, **kwargs) -> dict:
        '''
        Imitates the curl request below. This should return a JSON list of products we must capture and save
        curl 'https://s5phub.copernicus.eu/dhus/api/stub/products?filter=(%20footprint:%22Intersects(POLYGON((28.631599515845753%2041.493133691236096,28.64944685853913%2040.82802689873458,29.349955059254064%2040.80438956050165,29.33656955223404%2041.46973496540136,28.631599515845753%2041.493133691236096,28.631599515845753%2041.493133691236096)))%22)%20AND%20(%20ingestionDate:[2020-03-15T00:00:00.000Z%20TO%202020-03-18T23:59:59.999Z%20]%20)%20AND%20(%20%20(platformname:Sentinel-5%20AND%20producttype:L2__NO2___%20AND%20processinglevel:L2%20AND%20processingmode:Near%20real%20time))&offset=0&limit=25&sortedby=ingestiondate&order=desc' -H 'Connection: keep-alive' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'Accept: application/json, text/plain, */*' -H 'Sec-Fetch-Dest: empty' -H 'X-Requested-With: XMLHttpRequest' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36' -H 'DNT: 1' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-Mode: cors' -H 'Referer: https://s5phub.copernicus.eu/dhus/' -H 'Cookie: dhusAuth=13907c0568f18567a221414d76456f78; dhusIntegrity=e21cc801df0db557826cdb9bfc35e1b66a804aff; JSESSIONID=5D019DAFA0C7160E6A767D2E4EBD7CB5'

        '''
        buffer = BytesIO()
        c = pycurl.Curl()
        base_url = 'https://s5phub.copernicus.eu/dhus/api/stub/products?'
        date_from = date_from if date_from else datetime(1990, 1, 3)
        date_to = date_to if date_to else datetime.utcnow()
        date_from_str = date_from.isoformat(timespec='milliseconds')
        date_to_str = date_to.isoformat(timespec='milliseconds')
        bounds = bounds if bounds else cities[city]
        lat1, lat2, lon1, lon2 = bounds
        filter_params = {'footprint': f'"{GEOJSON_AREA_MATCH_CONDITION}(POLYGON(( {lon1} {lat1}, {lon2} {lat1}, {lon2} {lat2}, {lon1} {lat2}, {lon1} {lat1})))"',
                         'beginPosition': f'[{date_from_str}Z TO {date_to_str}Z ]',
                         'endPosition': f'[{date_from_str}Z TO {date_to_str}Z ]',
                         'platformname': 'Sentinel-5',
                         'producttype': product_type,
                         'processinglevel': 'L2',
                         'processingmode': processing_mode,  # Offline
                         }
        parameters = {'filter': f'( footprint:{filter_params["footprint"]}) AND ( beginPosition:{filter_params["beginPosition"]} AND endPosition:{filter_params["endPosition"]} ) AND (  (platformname:{filter_params["platformname"]} AND producttype:{filter_params["producttype"].value} AND processinglevel:{filter_params["processinglevel"]} AND processingmode:{filter_params["processingmode"].value}))',
                      'offset': offset,  # this is for pagination of results
                      'limit': limit,  # also for pagination, there's probably a server side limit
                      'sortedby': 'beginposition',
                      'order': 'desc',
                      }
        c.setopt(c.URL, base_url + urlencode(parameters, quote_via=urllib_quote))
        c.setopt(c.CAINFO, certifi.where())
        c.setopt(c.FOLLOWLOCATION, True)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(pycurl.ENCODING, b"gzip, deflate, br")
        c.setopt(pycurl.VERBOSE, verbose)
        headers_list = list()
        headers_list += construct_headers(S5PSession.SHARED_HEADERS_DICT)
        headers_list += construct_headers(S5PSession.QUERY_HEADERS_DICT)
        headers_list += construct_headers(cookies_as_dict(self.cookies))
        c.setopt(pycurl.HTTPHEADER, headers_list)

        # closure to capture Set-Cookie
        def _write_header(header, verbose):
            header = header.decode('utf-8').strip()
            if verbose:
                print(f'Captured Header: {header}')
            if header.startswith('HTTP/1.1 '):
                self.query_http_status = header[len('HTTP/1.1 '):]

        # use closure to collect cookies sent from the server
        c.setopt(pycurl.HEADERFUNCTION, partial(
            _write_header, verbose=verbose))

        print(f'Querying ')
        c.perform()
        c.close()

        body = buffer.getvalue()
        # Body is a byte string.
        # We have to know the encoding in order to print it to a text file
        # such as standard output.
        decoded_body = body.decode('utf-8')
        products_dict = simplejson.loads(decoded_body)
        print(f'Fetched {len(products_dict["products"])} out of {products_dict["totalresults"]} products')
        self.query_results_cache += products_dict['products'].copy()
        return products_dict

    def find_product(self, **kwargs):
        if len(kwargs) != 1:
            raise Exception('find_product takes only 1 keyword argument')
        key = list(kwargs.keys())[0]
        val = kwargs[key]
        for product_dict in self.query_results_cache:
            if val == product_dict[key]:
                return product_dict.copy()
        return None

    @login_required
    def download_product(self, uuid: str, output_filename: str = None, output_folder: Path = None, refresh_period=0.5, overwrite: bool = False, verbose: bool = False, abort_period: int = 15, *args, **kwargs) -> Path:
        '''
        Imitates the curl request below. This should return a full NC file
        curl $'https://s5phub.copernicus.eu/dhus/odata/v1/Products(\'50c3c635-6430-47e9-bc18-fe3dbefa9c75\')/$value' -H 'Connection: keep-alive' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'Upgrade-Insecure-Requests: 1' -H 'DNT: 1' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36' -H 'Sec-Fetch-Dest: document' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-User: ?1' -H 'Referer: https://s5phub.copernicus.eu/dhus/' -H 'Accept-Language: en-GB,en;q=0.9,tr-TR;q=0.8,tr;q=0.7,en-US;q=0.6' -H 'Cookie: dhusAuth=13907c0568f18567a221414d76456f78; dhusIntegrity=aec1e796cefd0f60990c96f698256b66c04df772; JSESSIONID=54D81611452766E848AC5AC4E5F0133B' --compressed
        '''
        product_dict = self.find_product(uuid=uuid)
        if product_dict:
            print(f'Matched UUID {uuid} to product {format_product_summary(product_dict)}')
        else:
            print(f'Couldnt match UUID {uuid}')
        fname = f'{product_dict["identifier"]}' if product_dict else str(uuid)
        output_filename = output_filename if output_filename else fname
        output_folder = output_folder if output_folder else Path.cwd()
        if not output_folder.exists():
            output_folder.mkdir(parents=True, exist_ok=True)
        target_filepath = output_folder/f'{output_filename}.nc'
        request_url = f'https://s5phub.copernicus.eu/dhus/odata/v1/Products(\'{uuid}\')/$value'
        print(f'Generated download link {request_url}')

        def create_download_request(head=False, fid=sys.stdout, abort_period=abort_period):
            c = pycurl.Curl()
            c.setopt(c.URL, request_url)
            c.setopt(c.CAINFO, certifi.where())
            c.setopt(c.FOLLOWLOCATION, True)
            c.setopt(c.WRITEDATA, fid)
            c.setopt(pycurl.ENCODING, b"gzip, deflate, br")
            if not head:
                c.setopt(c.NOPROGRESS, False)
                dpt = DownloadProgressTracker(fid=fid, refresh_period=refresh_period, abort_period=abort_period)
                c.setopt(c.XFERINFOFUNCTION, dpt.progress)
            c.setopt(pycurl.VERBOSE, verbose)
            headers_list = list()
            headers_list += construct_headers(S5PSession.SHARED_HEADERS_DICT)
            headers_list += construct_headers(S5PSession.DOWNLOAD_HEADERS_DICT)
            headers_list += construct_headers(cookies_as_dict(self.cookies))
            c.setopt(pycurl.HTTPHEADER, headers_list)
            if head:
                c.setopt(c.NOBODY, True)

            # closure to capture Set-Cookie
            def _write_header(header, verbose):
                header = header.decode('utf-8').strip()
                if verbose:
                    print(f'Captured Header: {header}')
                if header.startswith('Content-Length: '):
                    self.download_content_length = int(header[len('Content-Length: '):])
                if header.startswith('HTTP/1.1 '):
                    self.query_http_status = header[len('HTTP/1.1 '):]
                    print(f'HTTP/1.1 STATUS {self.query_http_status}')
                if header.startswith('HTTP/1.0 '):
                    self.query_http_status = header[len('HTTP/1.0 '):]
                    print(f'HTTP/1.0 STATUS {self.query_http_status}')

            # use closure to collect cookies sent from the server
            c.setopt(pycurl.HEADERFUNCTION, partial(_write_header, verbose=verbose))
            return c

        c = create_download_request(fid=sys.stdout, head=True)
        print(f'Sending HEAD request for {str(uuid)}')
        c.perform()
        c.close()

        print(f'Captured Content-Length: {self.download_content_length}')

        time.sleep(1.0)  # because i managed to http 429 too many requests

        content_range_start = 0
        if target_filepath.exists():
            target_stats = target_filepath.stat()
            # pprint(target_stats)
            filesize = target_stats.st_size
            content_range_start = filesize
            print(f'Target file exists with size = {filesize}')
            if overwrite:
                print(f'Target file exists at {target_filepath}. Overwrite flag issued; downloading again.')
                target_filepath.unlink()
                content_range_start = 0
            elif filesize == self.download_content_length:
                print(f'Target file exists at {target_filepath}. Use overwrite flag if you want to download again')
                return target_filepath
            elif filesize < self.download_content_length:
                print(f'Will try to continue download by asking range "{content_range_start}-{self.download_content_length}"')
            elif filesize > self.download_content_length:  # means somehow we have a local file larger than the remote one. we should just erase the local file
                print(f'Somehow we have a local file larger than the remote one ({filesize} > {self.download_content_length}).')
                print(f'Gonna assume this is OK')
                return target_filepath
                # print(f'Erasing the local file')
                # target_filepath.unlink()
                # content_range_start = 0
        # Body is a byte string.
        # This is supposed to be empty

        fid = open(target_filepath, 'a+b')
        print(f'cursor is at {fid.tell()}')
        fid.seek(content_range_start)

        c = create_download_request(fid=fid, head=False)
        if content_range_start != 0:
            c.setopt(pycurl.RANGE, f'{content_range_start}-{self.download_content_length}')
        print(f'Downloading to {str(target_filepath)}')
        c.perform()
        c.close()
        bytes_written = fid.tell()
        fid.close()
        # Body is a byte string.
        # This is supposed to be a binary file, so no decoding.
        print(f'Wrote {bytes_written} bytes')

        return target_filepath

    def netcdf_to_geojson(self, product_dict: dict, input_filepath: Path, bounds: Tuple[float, float, float, float] = None, city: str = None, output_filename: str = None, output_folder: Path = None, *args, **kwargs) -> Path:

        fname = str(product_dict["identifier"])
        output_filename = output_filename if output_filename else city if city else fname
        output_folder = output_folder if output_folder else Path.cwd()
        if not output_folder.exists():
            output_folder.mkdir(parents=True, exist_ok=True)
        geojson_filepath = output_folder/f'{output_filename}_geo.json'

        rootgrp = netcdf_dataset(input_filepath, 'r')
        plotme_nc, lats_nc, lons_nc, description, units, validity_start, validity_stop = extract_product_essentials(rootgrp=rootgrp)

        # netcdf to numpy
        plotme_np, lats_np, lons_np = clip_netcdf_data(plotme_nc=plotme_nc, lats_nc=lats_nc, lons_nc=lons_nc, bounds=bounds, city=city, *args, **kwargs)

        # dummy code block for potential post processing
        plotme_final = plotme_np.copy()
        plotme_final = (plotme_final)

        nonmasked_item_shape = plotme_final.shape
        if nonmasked_item_shape[0] < 2 or nonmasked_item_shape[1] < 2:
            print(f'Nonmasked item count is {nonmasked_item_shape}')
            print('Exiting; nothing to do here...')
            with open(geojson_filepath, 'w') as fp:
                result_dict = dict(features=list())
                simplejson.dump(result_dict, fp=fp)
            return geojson_filepath

        # calculating min, max, mean, variance to potentially use for plot parameters
        minval = plotme_final.min()
        maxval = plotme_final.max()
        meanval = plotme_final.mean()
        varval = plotme_final.var()

        print('PostProcessed')
        print(f'Min-Max {minval:.6f}-{maxval:.6f}')
        print(f'Mean-Var {meanval:.6f}-{varval:.6f}')

        # picking out filled contour parameters
        vmin = minval*1.0
        vmax = maxval*1.0
        levels = 16

        # grabing acquition parameters from product metadata
        print(f'Description: {description}')

        # ### Filled Contour Plot
        fig = plt.figure(figsize=(16, 18), dpi= 80, facecolor='w', edgecolor='k')
        ax = plt.axes(projection=ccrs.PlateCarree())
        # ax.set_extent((lon1-0.5, lon2+0.5, lat1-0.5, lat2+0.5))
        plt.title(f'{description}\n{validity_start} - {validity_stop}')
        cs = plt.contourf(lons_np, lats_np, plotme_final, levels, transform=ccrs.PlateCarree(), vmin=vmin, vmax=vmax, cmap="inferno")
        ax.coastlines()
        ax.gridlines(draw_labels=True)
        # ax.stock_img()
        cbar = fig.colorbar(cs, ax=ax, shrink=0.2)
        cbar.ax.set_ylabel(units)
        # Add the contour line levels to the colorbar
        # plt.show()

        # Convert matplotlib contourf to geojson
        try:
            geojsoncontour.contourf_to_geojson(
                contourf=cs,
                min_angle_deg=3.0,
                ndigits=3,
                stroke_width=2,
                fill_opacity=0.5,
                geojson_filepath=geojson_filepath,
            )
        except TypeError as terr:
            print(terr)
            print(f'Couldnt manage to convert contour into a geojson. There probably isnt enough data points!')
            traceback.print_exc()
            return None
        except Exception as exc:
            print(f'{exc.__class__.__name__}: {exc}')
            traceback.print_exc()

        return geojson_filepath

    def netcdf_to_json(self, product_dict: dict, input_filepath: Path, bounds: Tuple[float, float, float, float] = None, city: str = None, output_filename: str = None, output_folder: Path = None, *args, **kwargs) -> Path:

        fname = str(product_dict["identifier"])
        output_filename = output_filename if output_filename else city if city else fname
        output_folder = output_folder if output_folder else Path.cwd()
        if not output_folder.exists():
            output_folder.mkdir(parents=True, exist_ok=True)
        json_filepath = output_folder/f'{output_filename}.json'

        rootgrp = netcdf_dataset(input_filepath, 'r')
        plotme_nc, lats_nc, lons_nc, description, units, validity_start, validity_stop = extract_product_essentials(rootgrp=rootgrp)

        # netcdf to numpy
        plotme_np, lats_np, lons_np = clip_netcdf_data(plotme_nc=plotme_nc, lats_nc=lats_nc, lons_nc=lons_nc, bounds=bounds, city=city, *args, **kwargs)

        # dummy code block for potential post processing
        plotme_final = plotme_np.copy()
        plotme_final = (plotme_final)

        nonmasked_item_count = plotme_final.count()
        if nonmasked_item_count < 16:
            print(f'Nonmasked item count is {nonmasked_item_count}')
            print('Exiting; nothing to do here...')
            min_data = 0
            max_data = np.finfo(float).eps
            mean_data = np.finfo(float).eps
            variance_data = 0.0
            stddev_data = 0.0
        else:
            min_data = float(plotme_np.min())
            max_data = float(plotme_np.max())
            mean_data = float(plotme_np.mean())
            variance_data = float(plotme_np.var())
            stddev_data = float(plotme_np.std())

        print(f'Description: {description}')

        # Convert compressed masked numpy to list and json
        data = np.ndarray(shape=(plotme_np.count(), 3))
        data[:, 0] = lats_np.compressed()
        data[:, 1] = lons_np.compressed()
        data[:, 2] = plotme_np.compressed()
        data_aslist = data.tolist()
        product_summary_dict = dict(date_str=f'{product_dict["summary"][0].split("Date : ")[1]}',
                                    uuid=product_dict["uuid"],
                                    url=f'https://s5phub.copernicus.eu/dhus/odata/v1/Products(\'{product_dict["uuid"]}\')/$value',
                                    identifier=product_dict["identifier"],
                                    offline=product_dict["offline"],
                                    processing_mode=product_dict["indexes"][1]["children"][7]["value"],
                                    product_type=product_dict["productType"],
                                    )

        result_dict = dict(description=description,
                           units=plotme_nc.units,
                           validity_start=validity_start,
                           validity_stop=validity_stop,
                           data=data_aslist,
                           min=min_data,
                           max=max_data,
                           mean=mean_data,
                           variance=variance_data,
                           stddev=stddev_data,
                           city=city,
                           product_summary_dict=product_summary_dict,
                           )

        with open(json_filepath, 'w') as fp:
            simplejson.dump(result_dict, fp=fp)
            return json_filepath
        return None

    @login_required
    def query_and_download_latest_product(self, bounds: Tuple[float, float, float, float] = TURKEY_LATLON_BOUNDS, date_from: datetime = None, date_to: datetime = None, product_type: ProductType = ProductType.CO, processing_mode: ProcessingMode = ProcessingMode.OFFLINE, verbose=False, output_filename: str = None, output_folder: Path = None, *args, **kwargs) -> Path:
        products = self.query(bounds=bounds, date_from=date_from, date_to=date_to, product_type=product_type, processing_mode=processing_mode, verbose=verbose, *args, **kwargs)
        if products['totalresults'] == 0:
            return None
        target_filepath = self.download_product(uuid=products['products'][0]['uuid'], output_folder=output_folder, output_filename=output_filename, *args, **kwargs)
        print(f'Downloaded file size {target_filepath.stat().st_size/1024/1024:0.2f} MB')
        return target_filepath


def test(*args, **kwargs):
    s5p_session = S5PSession()
    s5p_session.login()
    # time.sleep(1)
    # products = s5p_session.query(date_from=datetime(2020, 3, 1), product_type=ProductType.CLOUD, processingmode=ProcessingMode.OFFLINE)
    # for product in products['products']:
    #     print('==============================================================================================================================')
    #     print(f'UUID: {product["uuid"]}')
    #     pprint(product['summary'])
    # time.sleep(1)
    # target_filepath = s5p_session.download_product(uuid=products['products'][0]['uuid'], output_folder=Path.home()/'Desktop'/'deleteme')
    # print(f'Downloaded file size {target_filepath.stat().st_size/1024/1024:0.2f} MB')
    s5p_session.query_and_download_latest_product(date_from=datetime(2020, 3, 1), product_type=ProductType.CLOUD, processingmode=ProcessingMode.RPRO, output_folder=Path.home()/'Desktop'/'deleteme')

def query_submain(s5p_session, filtered_vargs):
    products = s5p_session.query(**filtered_vargs)
    for product in products['products']:
        print('==============================================================================================================================')
        print_product_summary(product)

    results_start = filtered_vargs["offset"]+1
    results_end = filtered_vargs["offset"]+len(products["products"])
    print(f'Showed latest {results_start}-{results_end}/{products["totalresults"]} products')
    if products['totalresults'] > 0 and filtered_vargs['download']:
        product_dict = products['products'][0]
        total_retries = filtered_vargs['retries'] if 'retries' in filtered_vargs else 5
        remaining_retries = total_retries
        time.sleep(random.randint(2, 3))
        while remaining_retries > 0:
            try:
                target_filepath = s5p_session.download_product(uuid=product_dict['uuid'], **filtered_vargs)
                print(f'Downloaded file size {target_filepath.stat().st_size/1024/1024:0.2f} MB')
                remaining_retries = 0  # to ensure break
                break
            except Exception as exc:
                remaining_retries -= 1
                print(exc.__class__.__name__)
                print(f'Download failed: {exc}. Remaining retries = {remaining_retries}')
                traceback.print_exc()
                sleep_time = random.randint(5, 6) + 2*(total_retries - remaining_retries)
                print(f'Sleeping for {sleep_time}')
                time.sleep(sleep_time)
                if remaining_retries == 0:
                    print(f'Exceeded number of allowed retries. Exiting.')
                    sys.exit(-2)
        if filtered_vargs['generate_geojson']:
            print(f'Generating geojson from {target_filepath}')
            geojson_filepath = s5p_session.netcdf_to_geojson(product_dict=product_dict, input_filepath=target_filepath, **filtered_vargs)
            print(f'Geojson file created at {geojson_filepath.as_uri()}')
        if filtered_vargs['generate_json']:
            print(f'Generating json from {target_filepath}')
            geojson_filepath = s5p_session.netcdf_to_json(product_dict=product_dict, input_filepath=target_filepath, **filtered_vargs)
            print(f'Json file created at {geojson_filepath.as_uri()}')


def download_submain(s5p_session, filtered_vargs):
    target_filepath = s5p_session.download_product(**filtered_vargs)
    print(f'Downloaded file size {target_filepath.stat().st_size/1024/1024:0.2f} MB')


def populate_submain(s5p_session, filtered_vargs):
    from s5p_cities import dump_to_json_or_stdout as dump_cities_to_json_or_stdout, cities as skybase_cities

    DATE_FORMAT = '%Y-%m-%d'
    webroot = filtered_vargs['output_folder']
    # cities = ['istanbul', 'london', 'barcelona', 'paris', 'wuhan', 'milan']
    cities = filtered_vargs['cities'] if 'cities' in filtered_vargs else sorted(skybase_cities.keys())
    pts = filtered_vargs['product_type'] if 'product_type' in filtered_vargs else [ProductType.NO2]
    date_from = filtered_vargs['date_from'] if 'date_from' in filtered_vargs else datetime(year=2019, month=1, day=1)
    date_to = filtered_vargs['date_to'] if 'date_to' in filtered_vargs else datetime.utcnow()
    sleep_time_between_queries = random.randint(1, 2)
    verbose = filtered_vargs['verbose']

    ##########################
    # subset for debugging
    # cities = ['istanbul', ]
    # pts = ['NO2']
    ##########################

    curday = date_to

    def nrt_data_should_exist(dt: datetime) -> bool:
        return dt.month == datetime.utcnow().month
        # experimental;
        # return dt > datetime.utcnow()-timedelta(hours=200)  # 165 published but using 200 to be on the safe side

    def safe_dump_cities_to_json_or_stdout():
        try:
            dump_cities_to_json_or_stdout(output_file=webroot/'cities.json')
        except Exception as exc:
            print(f'City summary generation failed with: {exc}')
            traceback.print_exc()

    def safe_query_submain(s5p_session, query_kwargs):
        try:
            query_submain(s5p_session, query_kwargs)
        except Exception as exc:
            print(f'Query and/or Download failed with: {exc}')
            traceback.print_exc()

    safe_dump_cities_to_json_or_stdout()

    shared_query_kwargs = dict(offset=0,
                               limit=1,
                               retries=filtered_vargs['retries'],
                               verbose=filtered_vargs['verbose'],
                               download=filtered_vargs['download'],
                               generate_json=filtered_vargs['generate_json'],
                               generate_geojson=filtered_vargs['generate_geojson'],
                               refresh_period=filtered_vargs['refresh_period'],
                               abort_period=filtered_vargs['abort_period'],
                               )
    # NRT DOWNLOADS
    pm = ProcessingMode.NRT
    while nrt_data_should_exist(curday) and curday > date_from:
        begin_position = curday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_position = curday.replace(hour=23, minute=59, second=59, microsecond=999999)
        print(f'{begin_position}<{end_position} check {end_position>begin_position}')
        for city in cities:
            for pt in pts:
                target_folder = webroot/city/pt.name/curday.strftime(DATE_FORMAT)
                query_kwargs = dict(city=city,
                                    product_type=pt,
                                    processing_mode=pm,
                                    date_from=begin_position,
                                    date_to=end_position,
                                    output_folder=target_folder,
                                    )
                query_kwargs.update(shared_query_kwargs)
                print(f'Querying with params {pformat(query_kwargs)}')
                safe_query_submain(s5p_session, query_kwargs)
                time.sleep(sleep_time_between_queries)
                s5p_session.login(verbose)
                pass
            pass
        pass
        curday = curday - timedelta(days=1)

    # Offline DOWNLOADS
    pm = ProcessingMode.OFFLINE
    while curday > date_from:
        begin_position = curday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_position = curday.replace(hour=23, minute=59, second=59, microsecond=999999)
        print(f'{begin_position}<{end_position} check {end_position>begin_position}')
        for city in cities:
            for pt in pts:
                target_folder = webroot/city/pt.name/curday.strftime(DATE_FORMAT)
                query_kwargs = dict(city=city,
                                    product_type=pt,
                                    processing_mode=pm,
                                    date_from=begin_position,
                                    date_to=end_position,
                                    output_folder=target_folder,
                                    )
                query_kwargs.update(shared_query_kwargs)
                print(f'Querying with params {pformat(query_kwargs)}')
                safe_query_submain(s5p_session, query_kwargs)
                time.sleep(sleep_time_between_queries)
                s5p_session.login(verbose)
                pass
            pass
        pass
        curday = curday - timedelta(days=1)

    return


def main():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter, description=f'S5P Query and Download Tool'
'''
Mega Quick start:
    python s5p.py query

Quick start:
    Query only:
        python s5p.py query -b lat1 lat2 lon1 lon2 -pt CO -pm Offline
    Query and download latest product:
        python s5p.py query -b {lat1} {lat2} {lon1} {lon2} -pt CO -pm Offline -rl 1 -d -tf /tmp/s5p/

    Download product with uuid:
        python s5p.py download {uuid} -tf /tmp/s5p/
''')
    subparsers = parser.add_subparsers(required=True, description='Modes: "query" or "download"', help='Use "query", "search" or "lookup" to make a search. Use "download", "pull" or "get" to initiate a download.', dest='mode')
    query_mode = subparsers.add_parser('query', aliases=['search', 'lookup'])
    query_mode.add_argument('-v', '--verbose', action='store_true', help='This will enable outputting all sorts of information including pycurl outputs')
    query_mode.add_argument('-u', '--username', type=str, help='S5P username; default is s5pguest')
    query_mode.add_argument('-p', '--password', type=str, help='S5P password; default is s5pguest')
    area_args = query_mode.add_mutually_exclusive_group(required=True)
    area_args.add_argument('-b', '--bounds', type=float, nargs=4, help=f'Bounds as space-separated 4 numbers in lat1, lat2, lon1, lon2 format')
    area_args.add_argument('-c', '--city', type=str, help=f'Major city name as string')
    query_mode.add_argument('-df', '--date-from', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help='This filter includes the date you enter')
    query_mode.add_argument('-dt', '--date-to', type=lambda s: datetime.strptime(s, '%Y-%m-%d')+timedelta(days=1, seconds=-1), help='This filter includes the date you enter')
    query_mode.add_argument('-pt', '--product-type', type=lambda s: ProductType[s.upper()], help=ProductType.__doc__)
    query_mode.add_argument('-pm', '--processing-mode', type=lambda s: ProcessingMode[s.upper()], help=ProcessingMode.__doc__)
    query_mode.add_argument('-ro', '--offset', type=int, default=0, help=f'Default:0; Offset for fetching results. This is about pagination but using a limit will speed up')
    query_mode.add_argument('-rl', '--limit', type=int, default=25, help=f'Default:25;Limit for fetching results. This is mostly about pagination but using a limit will speed up')
    query_mode.add_argument('-d', '--download', action='store_true', help='Download the latest result from query. Implies -rl=1 -ro=0')
    query_mode.add_argument('-f', '--force-overwrite', dest='overwrite', action='store_true', help='Download even if the target file exists')
    query_mode.add_argument('-rp', '--refresh-period', type=float, default=0.5, help='Progress update refresh period. Default is 0.5s. Set this high when using in notebook.')
    query_mode.add_argument('-ap', '--abort-period', type=float, default=30.0, help='Abort timeout time for interrupting a download if no data has been received. Default is 30 seconds.')
    query_mode.add_argument('-tf', '-of', '--target-folder', '--output-folder', dest='output_folder', type=Path, help='Output file directory for downloads')
    query_mode.add_argument('-o', '--output', type=str, dest='output_filename', help='Forces output file name for downloads. Note this isnt a Path but a str')
    query_mode.add_argument('-g', '--geojson', '--generate-geojson', dest='generate_geojson', action='store_true', help='Convert the downloaded netcdf file to a geojson.')
    query_mode.add_argument('-j', '--json', '--generate-json', dest='generate_json', action='store_true', help='Convert the downloaded netcdf file to a json.')
    query_mode.add_argument('-r', '--retries', type=int, default=5, help='Max retries for downloading a product')
    download_mode = subparsers.add_parser('download', aliases=['get', 'pull'])
    download_mode.add_argument('-v', '--verbose', action='store_true', help='This will enable outputting all sorts of information including pycurl outputs')
    download_mode.add_argument('-tf', '-of', '--target-folder', '--output-folder', dest='output_folder', type=Path, help='Output file directory for downloads')
    download_mode.add_argument('-o', '--output', type=str, dest='output_filename', help='Forces output file name for downloads. Note this isnt a Path but a str')
    download_mode.add_argument('uuid', type=str, help='Logs in and downloads the specified uuid')
    test_mode = subparsers.add_parser('test', aliases=['alp'])
    populate_mode = subparsers.add_parser('populate', aliases=['fill'])
    populate_mode.add_argument('-d', '--download', action='store_true', help='Download the latest results from queries. Otherwise its a dry run')
    populate_mode.add_argument('-g', '--geojson', '--generate-geojson', dest='generate_geojson', action='store_true', help='Convert the downloaded netcdf file to a geojson.')
    populate_mode.add_argument('-j', '--json', '--generate-json', dest='generate_json', action='store_true', help='Convert the downloaded netcdf file to a json.')
    populate_mode.add_argument('-r', '--retries', type=int, default=5, help='Max retries for downloading a product')
    populate_mode.add_argument('-tf', '-of', '--target-folder', '--output-folder', '--webroot', dest='output_folder', default=Path.home()/'/s5p-data/data/', type=Path, help='Output file directory for downloads. This should be the webroot. Defaults to "$HOME/s5p-data/data/" ')
    populate_mode.add_argument('-df', '--date-from', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help='This filter includes the date you enter')
    populate_mode.add_argument('-dt', '--date-to', type=lambda s: datetime.strptime(s, '%Y-%m-%d')+timedelta(days=1, seconds=-1), help='This filter includes the date you enter')
    populate_mode.add_argument('-v', '--verbose', action='store_true', help='This will enable outputting all sorts of information including pycurl outputs')
    populate_mode.add_argument('-pt', '--product-type', action='append', type=lambda s: ProductType[s.upper()], help=ProductType.__doc__)
    populate_mode.add_argument('-rp', '--refresh-period', type=float, default=0.5, help='Progress update refresh period. Default is 0.5s. Set this high when using in notebook.')
    populate_mode.add_argument('-ap', '--abort-period', type=float, default=30.0, help='Abort timeout time for interrupting a download if no data has been received. Default is 30 seconds.')
    populate_mode.add_argument('-c', '--cities', type=str, action='append', help=f'Major city name as string')
    args = parser.parse_args()
    print(args)
    vargs = vars(args)
    filtered_vargs = vargs.copy()
    for key, val in vargs.items():
        if val is None:
            del filtered_vargs[key]
    pprint(filtered_vargs)

    if 'download' in filtered_vargs and filtered_vargs['download']:
        filtered_vargs['offset'] = 0
        filtered_vargs['limit'] = 1

    s5p_session = S5PSession(**filtered_vargs)
    s5p_session.login(**filtered_vargs)
    if filtered_vargs['mode'] == 'query':
        query_submain(s5p_session, filtered_vargs)
    elif filtered_vargs['mode'] == 'download':
        download_submain(s5p_session, filtered_vargs)
    elif filtered_vargs['mode'] == 'populate':
        populate_submain(s5p_session, filtered_vargs)
    elif filtered_vargs['mode'] == 'test':
        test(**filtered_vargs)


if __name__ == '__main__':
    main()
