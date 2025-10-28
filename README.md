![](https://forthebadge.com/images/badges/built-with-love.svg)
![](https://forthebadge.com/images/badges/fuck-it-ship-it.svg)

# Google Play Store Python API

This project is fork of [playstoreapi](https://gitlab.com/marzzzello/playstoreapi).
It contains an unofficial API for google play interactions.

The code was updated with the following changes:

- add config files for token & gsfid instead of env vars (env vars still supported though)
- Updated with latest googleplay proto format
- better download support for split files
- fixes for latest urllib3 library
- update fdfe base url

P.S.: There's still a lot of things I want to fix & update in it, but for now it's good enough and working and I don't have enough time to spend on it very much.

## Setup

Install playstoreapi using pip:

```sh
$ pip install playstoreapi
```

Or clone the repo and run:

```sh
$ python setup.py build
```

# Usage

Check scripts in `test` and `examples` directory for more examples on how to use this API.

```python
from playstoreapi.googleplay import GooglePlayAPI

mail = 'mymail@google.com'
passwd = 'mypasswd'

api = GooglePlayAPI('en_GB', 'Europe/London')
api.login(email=mail, password=passwd)
print(f'authSubToken: {api.authSubToken} gsfId: {api.gsfId}')

result = api.search('firefox')
for doc in result:
    if 'id' in doc:
        print('doc: {}'.format(doc['id']))
    for cluster in doc['subItem']:
        print('\tcluster: {}'.format(cluster['id']))
        for app in cluster['subItem']:
            print('\t\tapp: {}'.format(app['id']))
```

For first time logins, you should only provide email and password.
The module will take care of initalizing the api, upload device information
to the google account you supplied, and retrieving
a Google Service Framework ID (which, from now on, will be the android ID of your fake device).

For the next logins you **should** save the gsfId and the authSubToken, and provide them as parameters
to the login function or set them as environement variables. If you login again with email and password,
this is the equivalent of re-initalizing your android device with a google account, invalidating previous gsfId and authSubToken.

## Environment variables

```sh
# for envLogin()
export PLAYSTORE_TOKEN='ya29.fooooo'
export PLAYSTORE_GSFID='1234567891234567890'
export PLAYSTORE_DISPENSER_URL='http://goolag.store:1337/api/auth'

# requests
export HTTP_PROXY='http://localhost:8080'
export HTTPS_PROXY='http://localhost:8080'
export CURL_CA_BUNDLE='/usr/local/myproxy_info/cacert.pem'
```
