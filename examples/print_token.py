#!/usr/bin/env python

# set env vars (optional):
# export PLAYSTORE_TOKEN='ya29.fooooo'
# export PLAYSTORE_GSFID='1234567891234567890'
# export PLAYSTORE_DISPENSER_URL='http://goolag.store:1337/api/auth'
# export HTTP_PROXY='http://localhost:8080'
# export HTTPS_PROXY='http://localhost:8080'
# export CURL_CA_BUNDLE='/usr/local/myproxy_info/cacert.pem'

from playstoreapi.googleplay import GooglePlayAPI

api = GooglePlayAPI("en_GB", "Europe/London")

# prints token if not set via env var
api.envLogin()
