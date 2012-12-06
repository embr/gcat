#!/usr/bin/python

from oauth2client.client import  OAuth2WebServerFlow, OAuth2Credentials
from oauth2client.file import Storage
from apiclient.discovery import build
from apiclient import errors
import httplib2

import argparse
import sys, os.path
import re
import logging

from operator import itemgetter
from collections import defaultdict
import webbrowser
import yaml, csv, json, xlrd, pprint
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


def get_file(title, fmt='dict', **kwargs):
    """
    Simple interface for grabbing a Google Drive file by title.  Retrieves
    file in xlsx format and parses with `xlrd` (http://pypi.python.org/pypi/xlrd).
    If keyword argument sheet_name or sheet_id is given, returns only specified sheet.
    The `fmt` keyword argument determines the format of the return value.
    Here is the list of accepted formats and the corresponding return value type:
      * `dict`           : list of dicts (Default).
      * `xlrd`           : xlrd.Book (only full workbook is exported)
      * `list`           : list of lists
      * `pandas_excel`   : Pandas.ExcelFile, usefule for custom parsing
    For all formats other than `xlrd`, if no sheet name is given, get_file returns
    a dict with sheet names as keys and accordingly formatted rows as values.
    """
    opts = default_options()
    opts['title'] = title
    opts.update((k,v) for k, v in load_config(opts).items() if v is not None)
    opts.update((k,v) for k, v in kwargs.items() if v is not None)
    logger.info('opts:\n%s', pprint.pformat(opts))

    content = get_content(opts)
    wb = pd.ExcelFile(StringIO.StringIO(content))

    if fmt == 'pandas_excel':
        return wb
    
    try:
        parsed_wb = {sheet_name : wb.parse(sheet_name) for sheet_name in wb.sheet_names}
    except:
        logger.exception('error parsing worksheet using pandas.ExcelFile.parse(sheet_name). '
                         'Consider using pandas_excel and parsing the file yourself to have more control')
    if fmt == 'list':
        fmt_wb = {name : list(df.itertuples()) for name, df in parsed_wb.items()}
    elif fmt == 'dict':
        fmt_wb = {name : [r[1].to_dict() for r in df.iterrows()] for name, df in parsed_wb.items()}
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
    parser.add_argument('--title',
                        nargs='+',
                        metavar='title_word',
                        action=Join,
                        required=True,
                        help='the name of the google drive file in question.  If the name has spaces, gcat will do the '
                        ' right thing and join a sequence of command line arguments with space')
    parser.add_argument('--sheet',
                        nargs='+',
                        metavar='sheet_word',
                        action=Join,
                        help='sheet name within the spreadsheet.  If neither --sheet nor --sheet_id arguments are given '
                        'gcat will default to sheet_id=0. If the name has spaces, gcat will do the right thing and join '
                        'a sequence of command line arguments with spaces.')
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

    content = get_file(as_dict=False, **parse_args())
    write_to_stdout(content)


if __name__ == '__main__':
    main()
