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
import webbrowser
import yaml, csv, json, pprint
import StringIO
import shelve

LOGLEVELS = {'DEBUG': logging.DEBUG,
             'INFO': logging.INFO,
             'WARNING': logging.WARNING,
             'ERROR': logging.ERROR,
             'CRITICAL': logging.CRITICAL}  

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
            logging.error('Could not find config file at %s', yaml_name)
            sys.exit()
    else:
        return {}


def get_file(as_dict=True, **kwargs):
    logging.debug('computing from scratch')
    opts = default_options()
    opts.update((k,v) for k, v in load_config(opts).items() if v is not None)
    opts.update((k,v) for k, v in kwargs.items() if v is not None)
    logging.info('opts:\n%s', pprint.pformat(opts))

    cache = shelve.open(opts['cache'])
    # opts['timestamp' : datetime.date.today()] # TODO: add a timestamp to discard old caches
    if opts['usecache'] and opts['title'] in cache:
        content = cache[opts['title']]
    else:
        service = get_service(opts)
        files = service.files()
        try:
            res = files.list().execute()
        except errors.HttpError, error:
            logging.error('An error occurred: %s', exc_info=error)
            raise error

        names = map(itemgetter('title'), res['items'])
        try:
            idx = names.index(opts['title'])
        except ValueError:
            logging.error('file name: %s not in list', opts['title'])
            sys.exit()
        if idx == -1:
            raise ValueError('name %s not found in Google Drive' % opts['title'])
        file = res['items'][idx]
        content = download(service, file)
        cache[opts['title']] = content

    if as_dict:
        reader = csv.DictReader(StringIO.StringIO(content))
        parsed = []
        for line in reader:
            parsed.append(dict(filter(lambda (k,v): v, line.items())))
    else:
        parsed = list(csv.reader(StringIO.StringIO(content)))

    return parsed


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
        logging.info('refreshing token')
        refresh_http = httplib2.Http()
        credentials.refresh(refresh_http) 
    return credentials


def download(service, file):
    logging.debug('file.viewkeys(): %s', pprint.pformat(file.viewkeys()))
    # download_url = file.get('downloadUrl') # not present for some reason
    download_url_pdf = file.get('exportLinks')['application/pdf']
    download_url = re.sub('pdf$', 'csv', download_url_pdf)
    if download_url:
        resp, content = service._http.request(download_url)
        if resp.status == 200:
            logging.debug('Status: %s', resp)
            return content
        else:
            logging.error('An error occurred: %s' % resp)
            return None
    else:
        # The file doesn't have any content stored on Drive.
        logging.error('file does not have any content stored on Drive')
        return None    


def merge_config(opts, yaml_name):
    try:
        with open(yaml_name, 'r') as f:
            config = yaml.load(f)
            logging.debug('merging command-line opts with config from file: %s', yaml_name)
            for k, v in config.items():
                if not hasattr(opts,k) or getattr(opts, k) is None:
                    setattr(opts,k,v)
    except IOError:
        logging.error('Could not find config file at %s', yaml_name)
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
                        action=Join,
                        help='the name of the google drive file in question.  If the name has spaces, gcat will do the '
                        ' right thing and treat a sequence of space delimited words as a single file name')
    parser.add_argument('--cache',
                        help='location in which gcat will store documents when the --usecache flag is given')
    parser.add_argument('--usecache',
                        action='store_true',
                        help='instructs gcat to use the cache located in a file specified by the --cache option')
    args = parser.parse_args()
    return vars(args)
    

def write_to_stdout(content):
    for line in content:
        print '\t'.join(line)


def main():
    """
    logging set up
    """
    root_logger = logging.getLogger()
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s]\t[%(filename)s:%(funcName)s:%(lineno)d]\t%(message)s')
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)
    root_logger.setLevel(logging.DEBUG)

    content = get_file(as_dict=False, **parse_args())
    write_to_stdout(content)


if __name__ == '__main__':
    main()
