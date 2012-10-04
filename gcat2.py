from oauth2client.client import  OAuth2WebServerFlow
from apiclient.discovery import build
import httplib2
import webbrowser

#key = '0Au8PHt8_RuNedENfdVJtS19INHE4VjZTLTVrVFhRblE'

flow = OAuth2WebServerFlow(client_id='676635101978-9dbcpv7hobs4ufof2fejrrj11ird4uh4.apps.googleusercontent.com',
                           client_secret='L8UwOQ3zEWX_aAuengPUYK68',
                           scope='https://www.googleapis.com/auth/drive',
                           redirect_uri='urn:ietf:wg:oauth:2.0:oob')

auth_url = flow.step1_get_authorize_url()
webbrowser.open(auth_url)
code = raw_input('go to:\n\n\t%s\n\nand enter in the code displayed:' % auth_url)
credentials = flow.step2_exchange(code)

http = httplib2.Http()
http = credentials.authorize(http)

service = build('drive', 'v2', http=http)
res = service.files().list().execute()
print res
