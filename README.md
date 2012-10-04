gcat
====

A simple utility for grabbing google spreadsheets and printing them to the command-line stdout

##Introduction
`gcat` is simple command-line utility aimed at helping analysts integrate spreadsheets
living in Google Drive into their existing command-line environment by printing a file to stdout.
By default it stores installation specific configuration in `~/.gcat/config` and 
stores user specific credentials as a json object in `~/.gcat/store`.

As a simple example, perhaps you have a cron job that needs to integrate information updated in a google
spreadsheet.  You can downlaod the file, extract some columns and pipe the rows to the relevant utility with
a crontab line like:

````
0 0 1 * * gcat My Google Doc | cut -f1,4 | xargs my_utility
````

or create a set of automatically updated files which live on google drive

````
0 0 1 * * gcat My Google Doc > /home/embr/data/mydoc`date +"\%Y-\%m-\%d"`.csv
````

## Installation
`gcat` is packaged with setuptools so it can be easily installed with pip like this:

````
$ cd gcat/
$ [sudo] pip install -e .
````

### Google Drive SDK
In order to actually use the tool to access the document however, you'll need to first
register your installation as an "installed application" with google. To do this, follow the instuctions from google [here](https://developers.google.com/drive/quickstart).
Once you've installed gcat on your system and gone through the registration process,
you'll need to copy the client id, client secret, into the config file created at `~/.gcat/config`
replacing <your_client_id_here> and <your_client_id_here> with your actual information.
Upon installing gcat the following stub file will be created, so you only need to fill in
your fields

````
client_id:     '<your_client_id_here>'
client_secret: '<your_client_secret_here>'
scope:        'https://www.googleapis.com/auth/drive'
redirect_uri:  'urn:ietf:wg:oauth:2.0:oob'
````

## Usage

`gcat` allows you to customize most parameters through the command line.  For example, you can override the
client id/secret in the config file or the location which it uses to store credentials or where to look
for the config file.  To see the command-line options, just type:

````
gcat -h
````

which should print

````
usage: gcat.py [-h] [--store STORE] [--config CONFIG] [--client_id CLIENT_ID]
               [--client_secret CLIENT_SECRET] [--scope SCOPE]
               [--redirect_uri REDIRECT_URI]
               title [title ...]

print a google spreadsheet to stdout

positional arguments:
  title                 The name of the google drive file in question. If the
                        name has spaces, gcat will do the right thing and
                        treat a sequence of space delimited words as a single
                        file name

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

````