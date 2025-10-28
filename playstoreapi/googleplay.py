#!/usr/bin/python

import json
import os
import ssl
import time
from base64 import b64decode, urlsafe_b64encode

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import load_der_public_key
from urllib3.poolmanager import PoolManager

from . import config, googleplay_pb2, utils

CONFIG_PATHS = ["~/.config/playstoreapi", "./.playstoreapi"]

CONTENT_TYPE_PROTO = "application/x-protobuf"
CONTENT_TYPE_URLENC = "application/x-www-form-urlencoded; charset=UTF-8"

URL_DISPENSER = "https://auroraoss.com/api/auth"

URL_BASE = "https://android.clients.google.com/"
URL_FDFE = URL_BASE + "fdfe/"
URL_CHECKIN = URL_BASE + "checkin"
URL_AUTH = URL_BASE + "auth"

URL_BROWSE = URL_FDFE + "browse"
URL_BULK = URL_FDFE + "bulkDetails"
URL_BULK_PREFETCH = URL_FDFE + "bulkPrefetch"
URL_CATEGORIES = URL_FDFE + "categoriesList"
URL_CATEGORIES_2 = URL_FDFE + "allCategoriesList"
URL_DELIVERY = URL_FDFE + "delivery"
URL_DETAILS = URL_FDFE + "details"
URL_DETAILS_STREAM = URL_FDFE + "getDetailsStream"  # similiar apps
URL_DETAILS_ACQUIRE_STREAM = URL_FDFE + "getPostAcquireDetailsStream"
URL_DETAILS_DEVELOPER = URL_FDFE + "browseDeveloperPage"
URL_HOME = URL_FDFE + "homeV2"
URL_LIBRARY = URL_FDFE + "library"
URL_LIST = URL_FDFE + "list"
URL_LOG = URL_FDFE + "log"
URL_MODIFY_LIBRARY = URL_FDFE + "modifyLibrary"
URL_MY_APPS = URL_FDFE + "myApps"
URL_PURCHASE = URL_FDFE + "purchase"
URL_PURCHASE_HISTORY = URL_FDFE + "purchaseHistory"
URL_REVIEW_ADD_EDIT = URL_FDFE + "addReview"
URL_REVIEW_USER = URL_FDFE + "userReview"
URL_REVIEWS = URL_FDFE + "rev"
URL_SEARCH = URL_FDFE + "search"
URL_SEARCH_SUGGEST = URL_FDFE + "searchSuggest"
URL_SELF_UPDATE = URL_FDFE + "selfUpdate"
URL_SYNC = URL_FDFE + "apps/contentSync"
URL_TOC = URL_FDFE + "toc"
URL_TOP_CHART = URL_FDFE + "listTopChartItems"
URL_TOS_ACCEPT = URL_FDFE + "acceptTos"
URL_UPLOAD_DEVICE_CONFIG = URL_FDFE + "uploadDeviceConfig"
URL_USER_PROFILE = URL_FDFE + "api/userProfile"


# https://android.clients.google.com/fdfe/listTopChartItems?c=3&scat=APPLICATION&stcid=apps_topselling_free
# top free


class SSLContext(ssl.SSLContext):
    def set_alpn_protocols(self, protocols):
        """
        ALPN headers cause Google to return 403 Bad Authentication.
        """
        pass


class AuthHTTPAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        """
        Secure settings from ssl.create_default_context(), but without
        ssl.OP_NO_TICKET which causes Google to return 403 Bad
        Authentication.
        """
        context = SSLContext()
        context.verify_mode = ssl.CERT_REQUIRED
        context.options &= ~ssl.OP_NO_TICKET
        self.poolmanager = PoolManager(*args, ssl_context=context, **kwargs)


class LoginError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RequestError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SecurityCheckError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ApiError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class GooglePlayAPI(object):
    """
    Google Play Unofficial API Class

    Usual APIs methods are login(), search(), details(), bulkDetails(),
    download(), browse(), reviews() and list().
    """

    def __init__(
        self,
        locale="en_US",
        timezone="UTC",
        device_codename="px_3a",
        proxies_config=None,
        ssl_verify=True,
        delay=None,
    ):
        self.authSubToken = None
        self.gsfId = None
        self.device_config_token = None
        self.deviceCheckinConsistencyToken = None
        self.dfeCookie = None
        self.proxies_config = proxies_config
        self.headers = {
            "User-Agent": "com.aurora.store-4.7.4-70",
            "Content-Type": "application/json",
            "Host": "auroraoss.com",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip",
        }
        self.ssl_verify = ssl_verify
        self.deviceBuilder = config.DeviceBuilder(device_codename)
        self.setLocale(locale)
        self.setTimezone(timezone)
        self.delay = delay
        self.lastRequest = 0
        self.session = requests.session()
        self.session.mount("https://", AuthHTTPAdapter())

    def setLocale(self, locale):
        self.deviceBuilder.setLocale(locale)

    def setTimezone(self, timezone):
        self.deviceBuilder.setTimezone(timezone)

    def encryptPassword(self, login, passwd):
        """
        Encrypt credentials using the google publickey, with the
        RSA algorithm
        """

        # structure of the binary key:
        #
        # *-------------------------------------------------------*
        # | modulus_length | modulus | exponent_length | exponent |
        # *-------------------------------------------------------*
        #
        # modulus_length and exponent_length are uint32
        binaryKey = b64decode(config.GOOGLE_PUBKEY)
        # modulus
        i = utils.readInt(binaryKey, 0)
        modulus = utils.toBigInt(binaryKey[4:][0:i])
        # exponent
        j = utils.readInt(binaryKey, i + 4)
        exponent = utils.toBigInt(binaryKey[i + 8 :][0:j])

        # calculate SHA1 of the pub key
        digest = hashes.Hash(hashes.SHA1(), backend=default_backend())
        digest.update(binaryKey)
        h = b"\x00" + digest.finalize()[0:4]

        # generate a public key
        der_data = encode_dss_signature(modulus, exponent)
        publicKey = load_der_public_key(der_data, backend=default_backend())

        # encrypt email and password using pubkey
        to_be_encrypted = login.encode() + b"\x00" + passwd.encode()
        ciphertext = publicKey.encrypt(
            to_be_encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None,
            ),
        )

        return urlsafe_b64encode(h + ciphertext)

    def setAuthSubToken(self, authSubToken):
        self.authSubToken = authSubToken

    def getHeaders(self, upload_fields=False):
        """
        Return the default set of request headers, which
        can later be expanded, based on the request type
        """

        if upload_fields:
            headers = self.deviceBuilder.getDeviceUploadHeaders()
        else:
            headers = self.deviceBuilder.getBaseHeaders()
        if self.gsfId is not None:
            headers["X-DFE-Device-Id"] = "{0:x}".format(self.gsfId)
        if self.authSubToken is not None:
            headers["Authorization"] = (
                "Bearer %s" % self.authSubToken
            )  # GoogleLogin auth=
        if self.device_config_token is not None:
            headers["X-DFE-Device-Config-Token"] = self.device_config_token
        if self.deviceCheckinConsistencyToken is not None:
            headers["X-DFE-Device-Checkin-Consistency-Token"] = (
                self.deviceCheckinConsistencyToken
            )
        if self.dfeCookie is not None:
            headers["X-DFE-Cookie"] = self.dfeCookie
        return headers

    def checkin(self, email, ac2dmToken):
        headers = self.getHeaders()
        headers["Content-Type"] = CONTENT_TYPE_PROTO

        request = self.deviceBuilder.getAndroidCheckinRequest()

        stringRequest = request.SerializeToString()
        res = self.session.post(
            URL_CHECKIN,
            data=stringRequest,
            headers=headers,
            verify=self.ssl_verify,
            proxies=self.proxies_config,
        )
        res.raise_for_status()
        response = googleplay_pb2.AndroidCheckinResponse()
        response.raise_for_status()
        response.ParseFromString(res.content)
        self.deviceCheckinConsistencyToken = response.deviceCheckinConsistencyToken

        # checkin again to upload gfsid
        request.id = response.androidId
        request.securityToken = response.securityToken
        request.accountCookie.append("[" + email + "]")
        request.accountCookie.append(ac2dmToken)
        stringRequest = request.SerializeToString()
        res = self.session.post(
            URL_CHECKIN,
            data=stringRequest,
            headers=headers,
            verify=self.ssl_verify,
            proxies=self.proxies_config,
        )
        res.raise_for_status()

        return response.androidId

    def uploadDeviceConfig(self):
        """
        Upload the device configuration of the fake device
        selected in the __init__ methodi to the google account.
        """

        upload = googleplay_pb2.UploadDeviceConfigRequest()
        upload.deviceConfiguration.CopyFrom(self.deviceBuilder.getDeviceConfig())
        headers = self.getHeaders(upload_fields=True)
        stringRequest = upload.SerializeToString()
        response = self.session.post(
            URL_UPLOAD_DEVICE_CONFIG,
            data=stringRequest,
            headers=headers,
            verify=self.ssl_verify,
            timeout=60,
            proxies=self.proxies_config,
        )
        response.raise_for_status()
        response = googleplay_pb2.ResponseWrapper.FromString(response.content)
        try:
            if response.payload.HasField("uploadDeviceConfigResponse"):
                self.device_config_token = response.payload.uploadDeviceConfigResponse
                self.device_config_token = (
                    self.device_config_token.uploadDeviceConfigToken
                )
        except ValueError:
            pass

    def envLogin(self, quiet=False, check=True):
        """
        set env vars (optional):
        export PLAYSTORE_TOKEN='ya29.fooooo'
        export PLAYSTORE_GSFID='1234567891234567890'
        export PLAYSTORE_DISPENSER_URL='http://goolag.store:1337/api/auth'
        """
        for path in CONFIG_PATHS:
            expanded = os.path.expanduser(path)
            if os.path.isfile(expanded):
                try:
                    with open(expanded, "r") as f:
                        config_data = json.load(f)
                    authSubToken = config_data.get("authSubToken")
                    gsfId_str = config_data.get("gsfId")
                    if authSubToken and gsfId_str:
                        if not quiet:
                            print("\nLogin with token from config file\n")
                        self.login(
                            gsfId=int(gsfId_str), authSubToken=authSubToken, check=check
                        )
                        return
                except (IOError, ValueError):
                    pass
        gsfId = os.environ.get("PLAYSTORE_GSFID")
        authSubToken = os.environ.get("PLAYSTORE_TOKEN")
        tokenDispenser = os.environ.get("PLAYSTORE_DISPENSER_URL")

        if tokenDispenser is None:
            tokenDispenser = URL_DISPENSER

        if gsfId is None or authSubToken is None:
            self.login(anonymous=True, tokenDispenser=URL_DISPENSER)
            if not quiet:
                print("\nAnonymous login\n")
                print(f"PLAYSTORE_TOKEN='{self.authSubToken}'")
                print(f"PLAYSTORE_GSFID='{self.gsfId}'")
                print(f"PLAYSTORE_DISPENSER_URL='{self.gsfId}'")
            self.saveConfig()
        else:
            if not quiet:
                print(
                    "\nLogin with ac2dm token and gsfId provided by environment variables\n"
                )
            self.login(gsfId=int(gsfId), authSubToken=authSubToken, check=check)

    def saveConfig(self, currr_dir=False):
        """
        Save authSubToken and gsfId to config file
        """
        if currr_dir:
            path = CONFIG_PATHS[1]
        else:
            path = os.path.expanduser(CONFIG_PATHS[0])
        try:
            with open(path, "w") as f:
                json.dump({"authSubToken": self.authSubToken, "gsfId": self.gsfId}, f)
        except Exception:
            pass

    def login(
        self,
        email=None,
        password=None,
        gsfId=None,
        authSubToken=None,
        anonymous=False,
        tokenDispenser=URL_DISPENSER,
        check=True,
    ):
        """
        Login to your Google Account.
        For first time login you should provide:
            * email
            * password
            OR
            * anonymous=True
        For the following logins you need to provide:
            * gsfId
            * authSubToken
        """
        if anonymous is True:
            device_data = self.deviceBuilder.device_case_preserved

            response = self.session.post(
                URL_DISPENSER,
                json=device_data,
                verify=self.ssl_verify,
                proxies=self.proxies_config,
                headers=self.headers,
            )
            if response.status_code != 200:
                raise LoginError(f"Token dispenser is not OK ({response.status_code})")
            r = response.json()
            # email = r['email']
            # ac2dmToken = r['ac2dmToken']
            # deviceCheckInConsistencyToken = r['deviceCheckInConsistencyToken']
            # deviceConfigToken = r['deviceConfigToken']
            # gcmToken = r['gcmToken']
            gsfId = int(r["gsfId"], 16)
            authSubToken = r["authToken"]
            # print(f'authSubToken: {authSubToken} gsfId: {gsfId}')

        if email is not None and password is not None:
            # First time setup, where we obtain an ac2dm token and
            # upload device information

            encryptedPass = self.encryptPassword(email, password).decode("utf-8")
            # AC2DM token
            params = self.deviceBuilder.getLoginParams(email, encryptedPass)
            params["service"] = "ac2dm"
            params["add_account"] = "1"
            params["callerPkg"] = "com.google.android.gms"
            headers = self.deviceBuilder.getAuthHeaders(self.gsfId)
            headers["app"] = "com.google.android.gsm"
            response = self.session.post(
                URL_AUTH,
                data=params,
                verify=self.ssl_verify,
                proxies=self.proxies_config,
            )
            response.raise_for_status()
            data = response.text.split()
            params = {}
            for d in data:
                if "=" not in d:
                    continue
                k, v = d.split("=", 1)
                params[k.strip().lower()] = v.strip()
            if "auth" in params:
                ac2dmToken = params["auth"]
            elif "error" in params:
                if "NeedsBrowser" in params["error"]:
                    raise SecurityCheckError(
                        "Security check is needed, try to visit "
                        "https://accounts.google.com/b/0/DisplayUnlockCaptcha "
                        "to unlock, or setup an app-specific password"
                    )
                raise LoginError("server says: " + params["error"])
            else:
                raise LoginError("Auth token not found.")

            self.gsfId = self.checkin(email, ac2dmToken)
            self.getAuthSubToken(email, encryptedPass)
            self.uploadDeviceConfig()
        elif gsfId is not None and authSubToken is not None:
            if type(gsfId) != int:
                raise LoginError("gsfId is not of type int")
            # no need to initialize API
            self.gsfId = gsfId
            self.setAuthSubToken(authSubToken)
            # check if token is valid with a simple search
            if check:
                self.search("drv")
        else:
            raise LoginError("Either (email,pass) or (gsfId, authSubToken) is needed")

    def getAuthSubToken(self, email, passwd):
        requestParams = self.deviceBuilder.getLoginParams(email, passwd)
        requestParams["service"] = "androidmarket"
        requestParams["app"] = "com.android.vending"
        headers = self.deviceBuilder.getAuthHeaders(self.gsfId)
        headers["app"] = "com.android.vending"
        response = self.session.post(
            URL_AUTH,
            data=requestParams,
            verify=self.ssl_verify,
            headers=headers,
            proxies=self.proxies_config,
        )
        response.raise_for_status()
        data = response.text.split()
        params = {}
        for d in data:
            if "=" not in d:
                continue
            k, v = d.split("=", 1)
            params[k.strip().lower()] = v.strip()
        if "token" in params:
            master_token = params["token"]
            second_round_token = self.getSecondRoundToken(master_token, requestParams)
            self.setAuthSubToken(second_round_token)
        elif "error" in params:
            raise LoginError("server says: " + params["error"])
        else:
            raise LoginError("auth token not found.")

    def getSecondRoundToken(self, first_token, params):
        if self.gsfId is not None:
            params["androidId"] = "{0:x}".format(self.gsfId)
        params["Token"] = first_token
        params["check_email"] = "1"
        params["token_request_options"] = "CAA4AQ=="
        params["system_partition"] = "1"
        params["_opt_is_called_from_account_manager"] = "1"
        params.pop("Email")
        params.pop("EncryptedPasswd")
        headers = self.deviceBuilder.getAuthHeaders(self.gsfId)
        headers["app"] = "com.android.vending"
        response = self.session.post(
            URL_AUTH,
            data=params,
            headers=headers,
            verify=self.ssl_verify,
            proxies=self.proxies_config,
        )
        response.raise_for_status()
        data = response.text.split()
        params = {}
        for d in data:
            if "=" not in d:
                continue
            k, v = d.split("=", 1)
            params[k.strip().lower()] = v.strip()
        if "auth" in params:
            return params["auth"]
        elif "error" in params:
            raise LoginError("server says: " + params["error"])
        else:
            raise LoginError("Auth token not found.")

    def executeRequestApi2(
        self, path, post_data=None, content_type=CONTENT_TYPE_URLENC, params=None
    ):
        if self.authSubToken is None:
            raise LoginError("You need to login before executing any request")
        headers = self.getHeaders()
        headers["Content-Type"] = content_type

        if self.delay:
            tosleep = -(time.time() - self.lastRequest - self.delay)
            if tosleep > 0:
                # print('sleeping', tosleep)
                time.sleep(tosleep)

        if post_data is not None:
            response = self.session.post(
                path,
                data=str(post_data),
                headers=headers,
                params=params,
                verify=self.ssl_verify,
                timeout=60,
                proxies=self.proxies_config,
            )
        else:
            response = self.session.get(
                path,
                headers=headers,
                params=params,
                verify=self.ssl_verify,
                timeout=60,
                proxies=self.proxies_config,
            )
        response.raise_for_status()
        self.lastRequest = time.time()

        message = googleplay_pb2.ResponseWrapper.FromString(response.content)
        if message.commands.displayErrorMessage != "":
            raise RequestError(message.commands.displayErrorMessage)

        return message

    def searchSuggest(self, query):
        params = {"c": "3", "q": requests.utils.quote(query), "ssis": "120", "sst": "2"}
        data = self.executeRequestApi2(URL_SEARCH_SUGGEST, params=params)
        entryIterator = data.payload.searchSuggestResponse.entry
        return list(map(utils.parseProtobufObj, entryIterator))

    def search(self, query=None, nextPageUrl=None):
        """
        Search the play store for an app.

        nb_result (int): is the maximum number of result to be returned

        offset (int): is used to take result starting from an index.
        """

        if self.authSubToken is None:
            raise LoginError("You need to login before executing any request")

        if nextPageUrl is None:
            path = URL_SEARCH + "?c=3&q={}".format(requests.utils.quote(query))
        else:
            path = URL_FDFE + nextPageUrl

        # FIXME: not sure if this toc call should be here
        # self.toc()
        data = self.executeRequestApi2(path)
        if utils.hasPrefetch(data):
            response = data.preFetch.response
        else:
            response = data
        resIterator = response.payload.listResponse.item
        return list(map(utils.parseProtobufObj, resIterator))

    def details(self, packageName):
        """
        Get app details from a package name.

        packageName is the app unique ID (usually starting with 'com.').
        """
        path = URL_DETAILS + "?doc={}".format(requests.utils.quote(packageName))
        data = self.executeRequestApi2(path)
        return utils.parseProtobufObj(data.payload.detailsResponse.item)

    def streamDetails(self, packageName=None, nextPageUrl=None):
        """
        Get app stream details from a package name.

        packageName is the app unique ID (usually starting with 'com.').
        """

        if nextPageUrl is None:
            if packageName is None:
                raise ApiError("Either packageName or nextPageUrl is needed")
                return
            path = URL_DETAILS_STREAM + "?doc={}".format(
                requests.utils.quote(packageName)
            )
        else:
            path = URL_FDFE + nextPageUrl

        data = self.executeRequestApi2(path)
        return utils.parseProtobufObj(data.payload.listResponse)

    def bulkDetails(self, packageNames):
        """
        Get several apps details from a list of package names.

        This is much more efficient than calling N times details() since it
        requires only one request. If an item is not found it returns an empty object
        instead of throwing a RequestError('Item not found') like the details() function

        Args:
            packageNames (list): a list of app IDs (usually starting with 'com.').

        Returns:
            a list of dictionaries containing item data, or None
            if the app doesn't exist
        """

        params = {"au": "1"}
        req = googleplay_pb2.BulkDetailsRequest()
        req.DocId.extend(packageNames)
        data = req.SerializeToString()
        message = self.executeRequestApi2(
            URL_BULK,
            post_data=data.decode("utf-8"),
            content_type=CONTENT_TYPE_PROTO,
            params=params,
        )
        response = message.payload.bulkDetailsResponse
        return [
            None if not utils.hasItem(entry) else utils.parseProtobufObj(entry.item)
            for entry in response.entry
        ]

    def topChart(
        self, cat="APPLICATION", chart="apps_topselling_free", nextPageUrl=None
    ):
        """
        Get top apps. If `nextPageUrl` is provided get next page
        \ncat: `APPLICATION` or `GAME`
        \nchart: `apps_topselling_free`, `apps_topselling_paid`, `apps_topgrossing` (most success) and `apps_movers_shakers` (current trends)
        \nnextPageUrl: `getCluster?enpt=CiD6...`

        \naccess app ids like this: `ret['subItem'][0]['subItem'][0..6]['id']`
        \nnextPageUrl: `ret['subItem'][0]['containerMetadata']['nextPageUrl']`
        """

        if nextPageUrl is None:
            params = {"c": "3", "scat": cat, "stcid": chart}
            data = self.executeRequestApi2(URL_TOP_CHART, params=params)
        else:
            data = self.executeRequestApi2(URL_FDFE + nextPageUrl)

        itemIterator = data.payload.listResponse.item
        return utils.parseProtobufObj2(itemIterator)

    def home(self, dataUrl: None | str = None):
        if not dataUrl:
            path = URL_HOME + "?c=3&nocache_isui=true"
        else:
            path = URL_FDFE + dataUrl
        data = self.executeRequestApi2(path)
        if utils.hasPrefetch(data):
            response = data.preFetch.response
        else:
            response = data
        resIterator = response.payload.listResponse.item
        return list(map(utils.parseProtobufObj, resIterator))

    def browse(self, cat=None, subCat=None):
        """
        Browse categories. If neither cat nor subcat are specified,
        return a list of categories, otherwise it return a list of apps
        using cat (category ID) and subCat (subcategory ID) as filters.
        """
        path = URL_BROWSE + "?c=3"
        if cat is not None:
            path += "&cat={}".format(requests.utils.quote(cat))
        if subCat is not None:
            path += "&ctr={}".format(requests.utils.quote(subCat))
        data = self.executeRequestApi2(path)

        return utils.parseProtobufObj(data.payload.browseResponse)

    # TODO: fix/remove
    # def list(self, cat, ctr=None, nb_results=None, offset=None):
    #     '''
    #     List all possible subcategories for a specific category. If
    #     also a subcategory is provided, list apps from this category.

    #     Args:
    #         cat (str): category id
    #         ctr (str): subcategory id
    #         nb_results (int): if a subcategory is specified, limit number
    #             of results to this number
    #         offset (int): if a subcategory is specified, start counting from this
    #             result
    #     Returns:
    #         A list of categories. If subcategory is specified, a list of apps in this
    #         category.
    #     '''
    #     path = URL_LIST + '?c=3&cat={}'.format(requests.utils.quote(cat))
    #     if ctr is not None:
    #         path += '&ctr={}'.format(requests.utils.quote(ctr))
    #     if nb_results is not None:
    #         path += '&n={}'.format(requests.utils.quote(str(nb_results)))
    #     if offset is not None:
    #         path += '&o={}'.format(requests.utils.quote(str(offset)))
    #     data = self.executeRequestApi2(path)
    #     clusters = []
    #     if ctr is None:
    #         # list subcategories
    #         for pf in data.preFetch:
    #             for cluster in pf.response.payload.listResponse.item:
    #                 clusters.extend(cluster.subItem)
    #         return [c.id for c in clusters]
    #     else:
    #         apps = []
    #         for d in data.payload.listResponse.item:  # categories
    #             for c in d.subItem:  # sub-category
    #                 for a in c.subItem:  # app
    #                     apps.append(utils.parseProtobufObj(a))
    #         return apps

    def reviews(
        self, packageName, filterByDevice=False, sort=2, nb_results=None, offset=None
    ):
        """
        Browse reviews for an application

        Args:
            packageName (str): app unique ID.
            filterByDevice (bool): filter results for current device
            sort (int): sorting criteria (values are unknown)
            nb_results (int): max number of reviews to return
            offset (int): return reviews starting from an offset value

        Returns:
            dict object containing all the protobuf data returned from
            the api
        """
        # TODO: select the number of reviews to return
        path = URL_REVIEWS + "?doc={}&sort={}".format(
            requests.utils.quote(packageName), sort
        )
        if nb_results is not None:
            path += "&n={}".format(nb_results)
        if offset is not None:
            path += "&o={}".format(offset)
        if filterByDevice:
            path += "&dfil=1"
        data = self.executeRequestApi2(path)
        output = []
        for review in data.payload.reviewResponse.userReviewsResponse.review:
            output.append(utils.parseProtobufObj(review))
        return output

    def _deliver_data(self, url, cookies):
        headers = self.getHeaders()
        response = self.session.get(
            url,
            headers=headers,
            cookies=cookies,
            verify=self.ssl_verify,
            stream=True,
            timeout=60,
            proxies=self.proxies_config,
        )

        response.raise_for_status()
        total_size = response.headers.get("content-length")
        chunk_size = 32 * (1 << 10)
        return {
            "data": response.iter_content(chunk_size=chunk_size),
            "total_size": total_size,
            "chunk_size": chunk_size,
        }

    def delivery(
        self,
        packageName,
        versionCode=None,
        offerType=1,
        downloadToken=None,
        expansion_files=False,
    ):
        """
        Download an already purchased app.

        Args:
            packageName (str): app unique ID (usually starting with 'com.')
            versionCode (int): version to download
            offerType (int): different type of downloads (mostly unused for apks)
            downloadToken (str): download token returned by 'purchase' API
            progress_bar (bool): wether or not to print a progress bar to stdout

        Returns:
            Dictionary containing apk data and a list of expansion files. As stated
            in android documentation, there can be at most 2 expansion files, one with
            main content, and one for patching the main content. Their names should
            follow this format:

            [main|patch].<expansion-version>.<package-name>.obb

            Data to build this name string is provided in the dict object. For more
            info check https://developer.android.com/google/play/expansion-files.html
        """

        if versionCode is None:
            # pick up latest version
            appDetails = self.details(packageName).get("details").get("appDetails")
            versionCode = appDetails.get("versionCode")

        params = {"ot": str(offerType), "doc": packageName, "vc": str(versionCode)}
        headers = self.getHeaders()
        if downloadToken is not None:
            params["dtok"] = downloadToken
        response = self.session.get(
            URL_DELIVERY,
            headers=headers,
            params=params,
            verify=self.ssl_verify,
            timeout=60,
            proxies=self.proxies_config,
        )

        if response.status_code != 500:
            response.raise_for_status()
        response = googleplay_pb2.ResponseWrapper.FromString(response.content)
        if response.commands.displayErrorMessage != "":
            raise RequestError(response.commands.displayErrorMessage)
        elif response.payload.deliveryResponse.appDeliveryData.downloadUrl == "":
            raise RequestError("App not purchased")
        else:
            result = {}
            result["docId"] = packageName
            result["additionalData"] = []
            result["splits"] = []
            app_delivery_data = response.payload.deliveryResponse.appDeliveryData
            download_url = (
                app_delivery_data.compressedDownloadUrl or app_delivery_data.downloadUrl
            )
            cookie = app_delivery_data.downloadAuthCookie[0]
            cookies = {str(cookie.name): str(cookie.value)}
            result["file"] = self._deliver_data(download_url, cookies)

            for split in app_delivery_data.splitDeliveryData:
                a = {}
                a["name"] = split.name
                a["sha1"] = split.sha1
                a["sha256"] = split.sha256
                a["downloadSize"] = split.downloadSize
                a["compressedSize"] = split.compressedSize
                split_download_url = split.compressedDownloadUrl or split.downloadUrl
                a["file"] = self._deliver_data(split_download_url, cookies)
                result["splits"].append(a)

            if not expansion_files:
                return result
            for obb in app_delivery_data.additionalFile:
                a = {}
                # fileType == 0 -> main
                # fileType == 1 -> patch
                if obb.fileType == 0:
                    obbType = "main"
                else:
                    obbType = "patch"
                a["type"] = obbType
                a["versionCode"] = obb.versionCode
                a["file"] = self._deliver_data(obb.downloadUrl, None)
                result["additionalData"].append(a)
            return result

    def download(
        self, packageName, versionCode=None, offerType=1, expansion_files=False
    ):
        """
        Download an app and return its raw data (APK file). Free apps need
        to be 'purchased' first, in order to retrieve the download cookie.
        If you want to download an already purchased app, use *delivery* method.

        Args:
            packageName (str): app unique ID (usually starting with 'com.')
            versionCode (int): version to download
            offerType (int): different type of downloads (mostly unused for apks)
            downloadToken (str): download token returned by 'purchase' API
            progress_bar (bool): wether or not to print a progress bar to stdout

        Returns
            Dictionary containing apk data and optional expansion files
            (see *delivery*)
        """

        if self.authSubToken is None:
            raise LoginError("You need to login before executing any request")

        if versionCode is None:
            # pick up latest version
            appDetails = self.details(packageName).get("details").get("appDetails")
            versionCode = appDetails.get("versionCode")

        headers = self.getHeaders()
        params = {"ot": str(offerType), "doc": packageName, "vc": str(versionCode)}
        # self.log(packageName)
        response = self.session.post(
            URL_PURCHASE,
            headers=headers,
            params=params,
            verify=self.ssl_verify,
            timeout=60,
            proxies=self.proxies_config,
        )

        response.raise_for_status()
        response = googleplay_pb2.ResponseWrapper.FromString(response.content)
        if response.commands.displayErrorMessage != "":
            raise RequestError(response.commands.displayErrorMessage)
        else:
            dlToken = response.payload.buyResponse.encodedDeliveryToken
            return self.delivery(
                packageName,
                versionCode,
                offerType,
                dlToken,
                expansion_files=expansion_files,
            )

    # def log(self, docid):
    #     log_request = googleplay_pb2.LogRequest()
    #     log_request.downloadConfirmationQuery = 'confirmFreeDownload?doc=' + docid
    #     timestamp = int(time.time())
    #     log_request.timestamp = timestamp

    #     string_request = log_request.SerializeToString()
    #     response = self.session.post(
    #         URL_LOG,
    #         data=string_request,
    #         headers=self.getHeaders(),
    #         verify=self.ssl_verify,
    #         timeout=60,
    #         proxies=self.proxies_config,
    #     )
    #     response.raise_for_status()

    #     if response.content:
    #         try:
    #             parsed_response = googleplay_pb2.ResponseWrapper.FromString(response.content)
    #             if parsed_response.commands.displayErrorMessage != '':
    #                 raise RequestError(parsed_response.commands.displayErrorMessage)
    #         except Exception:
    #             pass

    def toc(self):
        response = self.session.get(
            URL_TOC,
            headers=self.getHeaders(),
            verify=self.ssl_verify,
            timeout=60,
            proxies=self.proxies_config,
        )
        response.raise_for_status()
        data = googleplay_pb2.ResponseWrapper.FromString(response.content)
        tocResponse = data.payload.tocResponse
        if utils.hasTosContent(tocResponse) and utils.hasTosToken(tocResponse):
            self.acceptTos(tocResponse.tosToken)
        if utils.hasCookie(tocResponse):
            self.dfeCookie = tocResponse.cookie
        return utils.parseProtobufObj(tocResponse)

    def acceptTos(self, tosToken):
        params = {"tost": tosToken, "toscme": "false"}
        response = self.session.get(
            URL_TOS_ACCEPT,
            headers=self.getHeaders(),
            params=params,
            verify=self.ssl_verify,
            timeout=60,
            proxies=self.proxies_config,
        )
        response.raise_for_status()
        data = googleplay_pb2.ResponseWrapper.FromString(response.content)
        return utils.parseProtobufObj(data.payload.acceptTosResponse)

    @staticmethod
    def getDevicesCodenames():
        return config.getDevicesCodenames()

    @staticmethod
    def getDevicesReadableNames():
        return config.getDevicesReadableNames()
