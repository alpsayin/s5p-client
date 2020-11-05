# s5p-client
### Another Sentinel-5 Precursor data query and downloader tool

This tool is written to automate data download, conversion and aggregation for a daily NO2 levels visualisation project.

User guide is coming...

### Acknowledgements

I wrote this tool while working at Novit.AI for https://emissions.novit.ai project. I'm releasing the source under my management with Novit's permission. I would also like to acknowledge and thank the ESA (European Spatial Agency) for the access to the Sentinel 5P Hub.

### Advantages & Disadvantages of this tool
1. Input areas are lat,lon bboxes in the format of minlat, maxlat, minlon, maxlon. While this makes it a breeze to quickly query some areas, if you need to work with more complex geojson defined areas see below.
2. The products are downloaded directly from the copernicus s5phub. This is both an advantage because I've noticed AWS host is sometimes broken and it was missing products, but also a disadvantage because it may not be as fast as the AWS host. In fact, be nice to Copernicus, limit your download bandwidth yourself.
3. If you search for NRT products older than 30 days you'll get nothing. If you search for OFFLINE products newer than 30 days, you'll get nothing. And who knows if there are even any RPRO products. It's just the way s5p data is organised. The tool is not smart enough to tell you if products couldnt be found for a specific reason. It's up to you to send reasonable queries.

### Alternative tool which uses the proper sentinelsat library but a bit more complex
For all purposes that require a bit more official touch; you should probably use below tool
https://github.com/bilelomrani1/s5p-tools

### Installation 

```bash
pip install -r requirements.txt
# Cartopy needs to be installed after numpy is installed because it's build wheel needs it
pip install Cartopy==0.18.0  
python3 s5p.py --help
```

### Usage

s5p.py client comes with 2 main modes query and download. Query mode also allows downloading of search results with certain flags. Download mode is just used to download products with their uuids and not very useful on its own. The 2 most important command you'll most likely need are given in Quick Start.

```usage: s5p.py [-h] {query,search,lookup,download,get,pull,test,alp,populate,fill} ...

S5P Query and Download Tool
Mega Quick start:
    python s5p.py query

Quick start:
    Query only:
        python s5p.py query -b lat1 lat2 lon1 lon2 -pt CO -pm Offline
    Query and download latest product:
        python s5p.py query -b {lat1} {lat2} {lon1} {lon2} -pt CO -pm Offline -rl 1 -d -tf /tmp/s5p/

    Download product with uuid:
        python s5p.py download {uuid} -tf /tmp/s5p/

optional arguments:
  -h, --help            show this help message and exit

subcommands:
  Modes: "query" or "download"

  {query,search,lookup,download,get,pull,test,alp,populate,fill}
                        Use "query", "search" or "lookup" to make a search. Use "download", "pull" or "get" to initiate a download.

```

## Query Mode
Chances are this is the mode you'll use most to both query and automatically download products and convert those products into more friendly jsons.

Cities are defined in a *s5p_cities.py*. If there's an area you'll likely query a lot, I suggest you fork the repo and add in your own cities.

```
usage: s5p.py query [-h] [-v] [-u USERNAME] [-p PASSWORD] (-b BOUNDS BOUNDS BOUNDS BOUNDS | -c CITY) [-df DATE_FROM] [-dt DATE_TO] [-pt PRODUCT_TYPE] [-pm PROCESSING_MODE] [-ro OFFSET]
                    [-rl LIMIT] [-d] [-f] [-rp REFRESH_PERIOD] [-ap ABORT_PERIOD] [-tf OUTPUT_FOLDER] [-o OUTPUT_FILENAME] [-g] [-j] [-r RETRIES]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         This will enable outputting all sorts of information including pycurl outputs
  -u USERNAME, --username USERNAME
                        S5P username; default is s5pguest
  -p PASSWORD, --password PASSWORD
                        S5P password; default is s5pguest
  -b BOUNDS BOUNDS BOUNDS BOUNDS, --bounds BOUNDS BOUNDS BOUNDS BOUNDS
                        Bounds as space-separated 4 numbers in lat1, lat2, lon1, lon2 format
  -c CITY, --city CITY  Major city name as string
  -df DATE_FROM, --date-from DATE_FROM
                        This filter includes the date you enter
  -dt DATE_TO, --date-to DATE_TO
                        This filter includes the date you enter
  -pt PRODUCT_TYPE, --product-type PRODUCT_TYPE
                        AER_AI, AER_LH, NO2, CO, CH4, SO2, HCHO, O3, O3_TCL, CLOUD
  -pm PROCESSING_MODE, --processing-mode PROCESSING_MODE
                        NRT, OFFLINE, RPRO
  -ro OFFSET, --offset OFFSET
                        Default:0; Offset for fetching results. This is about pagination but using a limit will speed up
  -rl LIMIT, --limit LIMIT
                        Default:25;Limit for fetching results. This is mostly about pagination but using a limit will speed up
  -d, --download        Download the latest result from query. Implies -rl=1 -ro=0
  -f, --force-overwrite
                        Download even if the target file exists
  -rp REFRESH_PERIOD, --refresh-period REFRESH_PERIOD
                        Progress update refresh period. Default is 0.5s. Set this high when using in notebook.
  -ap ABORT_PERIOD, --abort-period ABORT_PERIOD
                        Abort timeout time for interrupting a download if no data has been received. Default is 30 seconds.
  -tf OUTPUT_FOLDER, -of OUTPUT_FOLDER, --target-folder OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER
                        Output file directory for downloads
  -o OUTPUT_FILENAME, --output OUTPUT_FILENAME
                        Forces output file name for downloads. Note this isnt a Path but a str
  -g, --geojson, --generate-geojson
                        Convert the downloaded netcdf file to a geojson.
  -j, --json, --generate-json
                        Convert the downloaded netcdf file to a json.
  -r RETRIES, --retries RETRIES
                        Max retries for downloading a product
```

## Download Mode
Download mode only accepts a product uuid and not very useful on its own. It's useful if you want to separate your querying and downloading processes.
```
usage: s5p.py download [-h] [-v] [-tf OUTPUT_FOLDER] [-o OUTPUT_FILENAME] uuid

positional arguments:
  uuid                  Logs in and downloads the specified uuid

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         This will enable outputting all sorts of information including pycurl outputs
  -tf OUTPUT_FOLDER, -of OUTPUT_FOLDER, --target-folder OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER
                        Output file directory for downloads
  -o OUTPUT_FILENAME, --output OUTPUT_FILENAME
                        Forces output file name for downloads. Note this isnt a Path but a str
```

## Test Mode
There is also a test mode not detailed in user manuals. This is for developers to get **into** it. The `python s5p.py test` will call a `test(*args, **kwargs)` function inside the `s5p.py`. This was my main method of testing some routines.

### License
License is an MIT License if it's not obvious.