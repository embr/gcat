#!/usr/bin/python

from oauth2client.client import  OAuth2WebServerFlow, OAuth2Credentials
from oauth2client.file import Storage
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from apiclient import errors
import httplib2

import argparse
import sys, os.path
import re
import time
import logging


from operator import itemgetter
import collections
from collections import defaultdict, OrderedDict
import webbrowser
import yaml, csv, json, pprint
import StringIO
import shelve
import pandas as pd
import datetime

LOGLEVELS = {'DEBUG': logging.DEBUG,
             'INFO': logging.INFO,
             'WARNING': logging.WARNING,
             'ERROR': logging.ERROR,
             'CRITICAL': logging.CRITICAL}  

logger = logging.getLogger(__name__)

def default_options():
    defaults = {}
    defaults['store'] = os.path.expanduser('~/.gcat/store')
    defaults['config'] = os.path.expanduser('~/.gcat/config')
    defaults['cache'] = os.path.expanduser('~/.gcat/cache')
    defaults['usecache'] = False
    defaults['redirect_uri'] = 'urn:ietf:wg:oauth:2.0:oob'
    return defaults
     
def load_config(opts):
    if 'config' in opts:
        try:
            with open(opts['config'], 'r') as f:
                config = yaml.load(f)
                return dict(config)
        except IOError:
            logger.error('Could not find config file at %s', yaml_name)
            sys.exit()
    else:
        return {}


def get_file(title=None, fmt='dict', **kwargs):
    """
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
        

    """
    opts = default_options()
    opts['title'] = title
    opts.update((k,v) for k, v in load_config(opts).items() if v is not None)
    opts.update((k,v) for k, v in kwargs.items() if v is not None)
    logger.info('opts:\n%s', pprint.pformat(opts))
    if opts['title'] is None:
        raise ValueError('`title` not found in options.  exiting')

    content = get_content(opts)
    wb = pd.ExcelFile(StringIO.StringIO(content))

    if fmt == 'pandas_excel':
        return wb
    
    try:
        print 'sheets: %s' % wb.sheet_names
        parsed_wb = OrderedDict([(sheet_name, wb.parse(sheet_name)) for sheet_name in wb.sheet_names])
    except:
        logger.exception('error parsing worksheet using pandas.ExcelFile.parse(sheet_name). '
                         'Consider using pandas_excel and parsing the file yourself to have more control')
    if fmt == 'list':
        fmt_wb = OrderedDict([(name, list(df.itertuples(index=False))) for name, df in parsed_wb.items()])
    elif fmt == 'dict':
        fmt_wb = OrderedDict([(name, [r[1].to_dict() for r in df.iterrows()]) for name, df in parsed_wb.items()])
    elif fmt == 'pandas':
        fmt_wb = parsed_wb
    else:
        raise ValueError('unkown format: %s' % fmt)
    if len(fmt_wb) == 1:
        return fmt_wb.values()[0]
    if 'sheet' in opts:
        try:
            return fmt_wb[opts['sheet']]
        except:
            print 'sheet name: `%s` not found in workbook.  sheet_names: %s' % (opts['sheet'], fmt_wb.keys())
            logger.exception('sheet name: %s not found in workbook.  sheet_names: %s', opts['sheet'], fmt_wb.keys())
            raise
    else:
        return fmt_wb


def write_xlsx(dfs, fname, sheet_names=None):
    if isinstance(dfs, pd.DataFrame):
        dfs = [dfs]
    if isinstance(dfs, collections.Sequence):
        if sheet_names is not None:
            assert len(sheet_names) == len(dfs), 'sheet_names must have the same length as the `dfs` Sequence'
        else:
            sheet_names = ['Sheet %d' % i for i in range(len(dfs))]
        dfs = dict(zip(sheet_names, dfs))
    assert isinstance(dfs,collections.Mapping), 'dfs must either be a DataFrame, a Sequence of DataFrames or Mapping from strs to DataFrames'

    writer = pd.ExcelWriter(fname)
    for sheet_name, df in dfs.items():
        try:
            df = pd.DataFrame(df)
        except:
            logger.exception('could not convert data object: %s into pandas.DataFrame', df)
        df.to_excel(writer, sheet_name)
    writer.save()


def put_file(title=None, data=None, sheet_names=None, fname=None, **kwargs):
    """
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
      **kwargs     : options for configuring the OAuth stuff and which will be merged with
                     any options passed in from the command line or read in from the config file.
    """
    opts = default_options()
    opts['title'] = title
    opts['fname'] = fname
    opts['data'] = data
    opts['sheet_names'] = sheet_names
    opts.update((k,v) for k, v in load_config(opts).items() if v is not None)
    opts.update((k,v) for k, v in kwargs.items() if v is not None)
    if opts['title'] is None:
        raise ValueError('`title` not found in options. exiting')
    if opts['fname'] is None:
        if opts['data'] is not None:
            fname = os.path.join(os.environ['TMPDIR'], str(int(time.time())))
            write_xlsx(data, fname, sheet_names)
        else:
            raise ValueError('neither `title` nor `data` found in options. exiting')

    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    media_body = MediaFileUpload(fname, mimetype=mimetype, resumable=True)
    body = {
            'title': title,
            'description': '',
            'mimeType': mimetype}
    service = get_service(opts)
    try:
       file = service.files().insert(
                body=body,
                media_body=media_body,
                convert=True).execute()
                                
    except errors.HttpError, error:
        logger.exception('An error occured while attempting to insert file: %s', title)


def get_content(opts):
    cache = shelve.open(opts['cache'])
    if opts['usecache'] and opts['title'] in cache:
        content = cache[opts['title']]
    else:
        logger.debug('computing from scratch')
        service = get_service(opts)
        files = service.files()
        try:
            res = files.list().execute()
        except errors.HttpError, error:
            logger.error('An error occurred: %s', exc_info=error)
            raise error

        names = map(itemgetter('title'), res['items'])
        try:
            idx = names.index(opts['title'])
        except ValueError:
            logger.error('file name: %s not in list', opts['title'])
            sys.exit()
        if idx == -1:
            raise ValueError('name %s not found in Google Drive' % opts['title'])
        file = res['items'][idx]
        content = download(service, file)
        cache[opts['title']] = content
    return content


def get_service(opts):
    flow = OAuth2WebServerFlow(client_id=opts['client_id'],
                               client_secret=opts['client_secret'],
                               scope=opts['scope'],
                               redirect_uri=opts['redirect_uri'])

    credentials = get_credentials(flow, opts)

    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('drive', 'v2', http=http)
    return service


def get_credentials(flow, opts):
    storage = Storage(opts['store'])
    credentials = storage.get()
    if not credentials:
        # get the credentials the hard way
        auth_url = flow.step1_get_authorize_url()
        webbrowser.open(auth_url)
        code = raw_input('go to:\n\n\t%s\n\nand enter in the code displayed:' % auth_url)
        credentials = flow.step2_exchange(code)
        storage.put(credentials)

    #pprint.pprint(json.loads(credentials.to_json()), indent=2)
    if credentials.access_token_expired:
        logger.info('refreshing token')
        refresh_http = httplib2.Http()
        credentials.refresh(refresh_http) 
    return credentials


def download(service, file):
    logger.debug('file.viewkeys(): %s', pprint.pformat(file.viewkeys()))
    #download_url = file.get('downloadUrl') # not present for some reason
    #download_url_pdf = file.get('exportLinks')['application/pdf']
    download_url = file.get('exportLinks')['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    #download_url = re.sub('pdf$', 'csv', download_url_pdf)
    #download_url = re.sub('&exportFormat=csv$', '#gid=0&exportFormat=csv', download_url)
    #logger.debug('file.get(\'exportlinks\': %s', file.get('exportLinks'))
    if download_url:
        resp, content = service._http.request(download_url)
        if resp.status == 200:
            logger.debug('Status: %s', resp)
            return content
        else:
            logger.error('An error occurred: %s' % resp)
            return None
    else:
        # The file doesn't have any content stored on Drive.
        logger.error('file does not have any content stored on Drive')
        return None    


def merge_config(opts, yaml_name):
    try:
        with open(yaml_name, 'r') as f:
            config = yaml.load(f)
            logger.debug('merging command-line opts with config from file: %s', yaml_name)
            for k, v in config.items():
                if not hasattr(opts,k) or getattr(opts, k) is None:
                    setattr(opts,k,v)
    except IOError:
        logger.error('Could not find config file at %s', yaml_name)
        sys.exit()


class Join(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not isinstance(values, str):
            setattr(namespace, self.dest, ' '.join(values))


def parse_args(**kwopts):
    parser = argparse.ArgumentParser(description='print a google spreadsheet to stdout')
    parser.add_argument('--store',
                        help='location where gcat will store file specific credentials')
    parser.add_argument('--config',
                        help='a yaml file specifying the client_id, client_secret, scope, and redirect_uri')
    parser.add_argument('--client_id',
                        help='google api client id. this can be found at the google api console.  Note that'
                        'you first need to register your client as an "installed application" at the console'
                        ' as well (code.google.com/apis/console)')
    parser.add_argument('--client_secret',
                        help='google api client secret. this can be found at the google api console.  Note that'
                        'you first need to register your client as an "installed application" at the console'
                        ' as well (code.google.com/apis/console)')
    parser.add_argument('--scope',
                        help='list of scopes for which your client is authorized')
    parser.add_argument('--redirect_uri',
                        help='google api redirect URI. this can be found at the google api console under the \"Redirect URI\"'
                        'section.  By default a client if assigned two valid redirect URIs: urn:ietf:wg:oauth:2.0:oob '
                        'and http://localhostl.  use the urn:ietf:wg:oauth:2.0:oob unless you are doing something fancy.'
                        'see https://developers.google.com/accounts/docs/OAuth2InstalledApp for more info')
    parser.add_argument('title',
                        nargs='+',
                        metavar='title_word',
                        action=Join,
                        help='the name of the google drive file in question.  If the name has spaces, gcat will do the '
                        ' right thing and join a sequence of command line arguments with space')
    parser.add_argument('--sheet',
                        nargs='+',
                        metavar='sheet_word',
                        action=Join,
                        help='sheet name within the spreadsheet.  If no sheet is given, will return first sheet'
                        'If the name has spaces, gcat will do the right thing and join '
                        'a sequence of command line arguments with spaces into a single document title.')
    parser.add_argument('--cache',
                        help='location in which gcat will store documents when the --usecache flag is given')
    parser.add_argument('--usecache',
                        action='store_true',
                        help='instructs gcat to use the cache located in a file specified by the --cache option')
    args = parser.parse_args()
    return vars(args)
    

def write_to_stdout(content):
    for line in content:
        print '\t'.join(map(str, line))


def main():
    """
    logging set up
    """
    logger = logging.getLogger(__name__)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s]\t[%(filename)s:%(funcName)s:%(lineno)d]\t%(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)

    content = get_file(fmt='list', **parse_args())
    if isinstance(content, dict):
        content = content.values()[0]
    write_to_stdout(content)


if __name__ == '__main__':
    main()
