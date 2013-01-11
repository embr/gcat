gcat
====

A simple library and utility for interacting with Google Drive spreadsheets from python or the command-line

* [Introduction](https://github.com/embr/gcat#introduction)
* [Installation](https://github.com/embr/gcat#installation)
  * [Google Drive SDK] https://github.com/embr/gcat/blob/master/README.md#google-drive-sdk
* [Library Usage](https://github.com/embr/gcat#library-usage)
  * [`gcat.get_file()`](https://github.com/embr/gcat#gcatget_file-python-function)
  * [`gcat.put_file()`](https://github.com/embr/gcat#gcatput_file-python-function)
* [`gcat` Command Line Utility](https://github.com/embr/gcat#gcat-command-line-utility)

##Introduction
Basically, the Google Drive API documentation is a mess and a lot of work for simple cases where you just want to grab a file. `gcat` is a python wrapper for the Google Drive API which aims to simplify the process.  After an initial setup of OAuth you can grab the contents of a file with a single Python function call or a command line utility.  This makes it easy to integrate manually curated data with a more programatic analysis pipeline.

By default it stores installation specific configuration in `~/.gcat/config` and 
stores user specific credentials as a json object in `~/.gcat/store`.

Probably the most common use case for `gcat` is just grabbing a
Google Drive document from Python, which is as easy as:

````python
import gcat
rows = gcat.get_file('My File Name')
````

This returns a list of dicts that might look like this for a restaurant review document populated by a Google Form:

````
[{'reviewer' : 'Evan Rosen', 'restaurant' : 'Bar Tartine', 'Food' : 22, 'Decor' : 19, 'Service' : 17, 'Cost' : '$$'}
 {'reviewer' : 'Evan Rosen', 'restaurant' : 'Delfina', 'Food' : 21, 'Decor' : 20, 'Service' : 20, 'Cost' : '$$$'}]
````

If you wanted to work with the data using the [pandas](http://pandas.pydata.org/) DataFrame object you would just pass in the `fmt` keyword as 'pandas' like this:

````python
>>> reviews = gcat.get_file('My File Name', fmt='pandas')

<class 'pandas.core.frame.DataFrame'>
Int64Index: 2000 entries, 0 to 1
Data columns:
Cost          2000  non-null values
Decor         2000  non-null values
Food          2000  non-null values
Service       2000  non-null values
restaurant    2000  non-null values
reviewer      2000  non-null values
dtypes: int64(3), object(3)
````

`gcat` also installs a command line utilty which can be useful if you want to do some command-line fu and mix google docs items with the unix tabular data suite.  For example, you might run a cronjob on your data like this:

````
0 0 1 * * gcat My Google Doc | cut -f1,4 | xargs my_utility
````

or create a set of automatic backups of files which live on Google Drive

````
0 0 1 * * gcat My Google Doc > /home/embr/data/mydoc_`date +"\%Y-\%m-\%d"`.tsv
````

## Installation
`gcat` is packaged with setuptools so it can be easily installed with pip like this:

````bash
$ pip install -e git+git@github.com:embr/gcat.git#egg=gcat-0.1.0
````
or

````bash
$ cd gcat/
$ [sudo] pip install -e .
````

A word of warning that this installs [pandas](http://pandas.pydata.org/) which depends on numpy 1.6, which often cannot be easily updated using pip.  See [this stackoverflow post](http://stackoverflow.com/questions/12436979/how-to-fix-python-numpy-pandas-installation) for a solution.

### Google Drive SDK
In order to actually use the tool to access the document however, you'll need to first
register your installation as an "installed application" with Google. To do this, follow the instuctions from Google [here](https://developers.google.com/drive/quickstart).
Once you've installed gcat on your system and gone through the registration process,
you'll need to copy the client id, client secret, into the config file created at `~/.gcat/config`
replacing `<your_client_id_here>` and `<your_client_id_here>` with your actual information.
Upon installing gcat the following stub file will be created, so you only need to fill in
your fields

````
client_id:     '<your_client_id_here>'
client_secret: '<your_client_secret_here>'
scope:        'https://www.googleapis.com/auth/drive'
redirect_uri:  'urn:ietf:wg:oauth:2.0:oob'
````

## Library Usage

### `gcat.get_file()` Python function

````
>>> help(gcat.get_file)
gcat.get_file = get_file(title, fmt='dict', **kwargs)
    Simple interface for grabbing a Google Drive file by title.  Retrieves
    file in xlsx format and parses with pandas.ExcelFile If keyword argument `sheet` is given,
    returns only specified sheet.
    args:
        title     (str)   : Title of Google Drive document
        fmt       (str)   : Determines the format of the return value.
                            list of accepted formats and the corresponding return value type:
                            * `dict`           : list of dicts (Default).
                            * `pandas`         : pandas.DataFrame
                            * `list`           : list of lists
                            * `pandas_excel`   : Pandas.ExcelFile, (not yet parsed) useful for custom parsing
                            For all formats other than `pandas_excel`, if no sheet name is given and the spreadsheet
                            contains more than one sheet, get_file returns a dict with sheet names as keys and accordingly
                            formatted sheets as values.
    kwargs:
        sheet     (str)   : name of sheet to return
        cache     (str)   : location in which to store the cached contents of files
        usecache  (bool)  : whether to use the cache (default is False), but useful for debugging
        config    (str)   : path from which to read the config file which contains credentials
        store     (str)   : location in which to store file-specific credentials

````

### `gcat.put_file()` Python function

````
>>> help(gcat.put_file)
put_file(title=None, data=None, sheet_names=None, fname=None, update=False, **kwargs)
    Simple tool for writing Google Drive Spreadsheets.
    Args:
      title (str)  : name which spreadsheet will show up with on Google Drive (required)
      data         : either an object from which a pandas.DataFrame can be constructed
                     (including a DataFrame) or a list of such objects, or a dict which maps
                     strs to such objects.  If a single object or list of object is passed in
                     sheet names will be constructed as 'Sheet %d'.  If a dict is passed in
                     then the keys will be used as sheet names.  This allows a smooth round trip
                     when used in conjunction with gcat.get_file, which returns a dict of
                     sheet_names and sheets in the event that there is more than one sheet.
      sheet_names (list(str))
                   : list of sheet_names to use when passing in a list of data objects
      fname (str)  : name of file on local filesystem if uploading an external xlsx file
      update (bool): whether to update a file with title `title`.  If put_file is
                     called with a title of a preexisting file, it will simply create a duplicate
                     document with the same title (but a different internal Google Drive id)
      **kwargs     : options for configuring the OAuth stuff and which will be merged with
                     any options passed in from the command line or read in from the config file.
    
    Example:
    
        >>> import pandas as pd
        >>> import gcat
        >>> df1 = pd.DataFrame({'x' : [1,2], 'y' : [2,3]})
        >>> df2 = pd.DataFrame({'a' : [7,8], 'b' : [8,9]})
        >>> wb = {'sheet1' : df1, 'sheet2' : df2}              # put sheets together as dict
        >>> gcat.put_file(title='gcat_put_test', data=wb)      # put original
        >>> df2 = gcat.get_file('gcat_put_test', fmt='pandas') # download
        >>> df2['sheet1'].ix[1,1] = 17                         # update
        >>> gcat.put_file(title='gcat_put_test', data=df2)     # putting updated copy

````


## `gcat` command-line utility

````
$ gcat -h
usage: gcat [-h] [--store STORE] [--config CONFIG] [--client_id CLIENT_ID]
            [--client_secret CLIENT_SECRET] [--scope SCOPE]
            [--redirect_uri REDIRECT_URI]
            [--sheet sheet_word [sheet_word ...]] [--cache CACHE] [--usecache]
            title_word [title_word ...]

print a google spreadsheet to stdout

positional arguments:
  title_word            the name of the google drive file in question. If the
                        name has spaces, gcat will do the right thing and join
                        a sequence of command line arguments with space

optional arguments:
  -h, --help            show this help message and exit
  --store STORE         location where gcat will store file specific
                        credentials
  --config CONFIG       a yaml file specifying the client_id, client_secret,
                        scope, and redirect_uri
  --client_id CLIENT_ID
                        google api client id. this can be found at the google
                        api console. Note thatyou first need to register your
                        client as an "installed application" at the console as
                        well (code.google.com/apis/console)
  --client_secret CLIENT_SECRET
                        google api client secret. this can be found at the
                        google api console. Note thatyou first need to
                        register your client as an "installed application" at
                        the console as well (code.google.com/apis/console)
  --scope SCOPE         list of scopes for which your client is authorized
  --redirect_uri REDIRECT_URI
                        google api redirect URI. this can be found at the
                        google api console under the "Redirect URI"section. By
                        default a client if assigned two valid redirect URIs:
                        urn:ietf:wg:oauth:2.0:oob and http://localhostl. use
                        the urn:ietf:wg:oauth:2.0:oob unless you are doing
                        something fancy.see https://developers.google.com/acco
                        unts/docs/OAuth2InstalledApp for more info
  --sheet sheet_word [sheet_word ...]
                        sheet name within the spreadsheet. If no sheet is
                        given, will return first sheetIf the name has spaces,
                        gcat will do the right thing and join a sequence of
                        command line arguments with spaces into a single
                        document title.
  --cache CACHE         location in which gcat will store documents when the
                        --usecache flag is given
  --usecache            instructs gcat to use the cache located in a file
                        specified by the --cache option
````
