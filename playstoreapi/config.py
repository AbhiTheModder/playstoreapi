from configparser import ConfigParser
from os import path
from re import match
from time import time

from . import googleplay_pb2

DFE_TARGETS = "CAESN/qigQYC2AMBFfUbyA7SM5Ij/CvfBoIDgxHqGP8R3xzIBvoQtBKFDZ4HAY4FrwSVMasHBO0O2Q8akgYRAQECAQO7AQEpKZ0CnwECAwRrAQYBr9PPAoK7sQMBAQMCBAkIDAgBAwEDBAICBAUZEgMEBAMLAQEBBQEBAcYBARYED+cBfS8CHQEKkAEMMxcBIQoUDwYHIjd3DQ4MFk0JWGYZEREYAQOLAYEBFDMIEYMBAgICAgICOxkCD18LGQKEAcgDBIQBAgGLARkYCy8oBTJlBCUocxQn0QUBDkkGxgNZQq0BZSbeAmIDgAEBOgGtAaMCDAOQAZ4BBIEBKUtQUYYBQscDDxPSARA1oAEHAWmnAsMB2wFyywGLAxol+wImlwOOA80CtwN26A0WjwJVbQEJPAH+BRDeAfkHK/ABASEBCSAaHQemAzkaRiu2Ad8BdXeiAwEBGBUBBN4LEIABK4gB2AFLfwECAdoENq0CkQGMBsIBiQEtiwGgA1zyAUQ4uwS8AwhsvgPyAcEDF27vApsBHaICGhl3GSKxAR8MC6cBAgItmQYG9QIeywLvAeYBDArLAh8HASI4ELICDVmVBgsY/gHWARtcAsMBpALiAdsBA7QBpAJmIArpByn0AyAKBwHTARIHAX8D+AMBcRIBBbEDmwUBMacCHAciNp0BAQF0OgQLJDuSAh54kwFSP0eeAQQ4M5EBQgMEmwFXywFo0gFyWwMcapQBBugBPUW2AVgBKmy3AR6PAbMBGQxrUJECvQR+8gFoWDsYgQNwRSczBRXQAgtRswEW0ALMAREYAUEBIG6yATYCRE8OxgER8gMBvQEDRkwLc8MBTwHZAUOnAXiiBakDIbYBNNcCIUmuArIBSakBrgFHKs0EgwV/G3AD0wE6LgECtQJ4xQFwFbUCjQPkBS6vAQqEAUZF3QIM9wEhCoYCQhXsBCyZArQDugIziALWAdIBlQHwBdUErQE6qQaSA4EEIvYBHir9AQVLmgMCApsCKAwHuwgrENsBAjNYswEVmgIt7QJnN4wDEnta+wGfAcUBxgEtEFXQAQWdAUAeBcwBAQM7rAEJATJ0LENrdh73A6UBhAE+qwEeASxLZUMhDREuH0CGARbd7K0GlQo"
DFE_PHENOTYPE = "H4sIAAAAAAAAAB3OO3KjMAAA0KRNuWXukBkBQkAJ2MhgAZb5u2GCwQZbCH_EJ77QHmgvtDtbv-Z9_H63zXXU0NVPB1odlyGy7751Q3CitlPDvFd8lxhz3tpNmz7P92CFw73zdHU2Ie0Ad2kmR8lxhiErTFLt3RPGfJQHSDy7Clw10bg8kqf2owLokN4SecJTLoSwBnzQSd652_MOf2d1vKBNVedzg4ciPoLz2mQ8efGAgYeLou-l-PXn_7Sna1MfhHuySxt-4esulEDp8Sbq54CPPKjpANW-lkU2IZ0F92LBI-ukCKSptqeq1eXU96LD9nZfhKHdtjSWwJqUm_2r6pMHOxk01saVanmNopjX3YxQafC4iC6T55aRbC8nTI98AF_kItIQAJb5EQxnKTO7TZDWnr01HVPxelb9A2OWX6poidMWl16K54kcu_jhXw-JSBQkVcD_fPsLSZu6joIBAAA"
GOOGLE_PUBKEY = "AAAAgMom/1a/v0lblO2Ubrt60J2gcuXSljGFQXgcyZWveWLEwo6prwgi3iJIZdodyhKZQrNWp5nKJ3srRXcUW+F1BD3baEVGcmEgqaLZUNBjm057pKRI16kB0YppeGx5qIQ5QjKzsR8ETQbKLNWgRY0QRNVz34kMJR3P/LgHax/6rmf5AAAAAwEAAQ=="
ACCOUNT = "HOSTED_OR_GOOGLE"

# parse phone config from the file 'device.properties'.
# if you want to add another phone, just create another section in
# the file. Some configurations for common phones can be found here:
# https://github.com/yeriomin/play-store-api/tree/master/src/main/resources
filepath = path.join(path.dirname(path.realpath(__file__)), "device.properties")

config = ConfigParser()
config.read(filepath)

config_case_preserved = ConfigParser()
config_case_preserved.optionxform = str
config_case_preserved.read(filepath)


class InvalidLocaleError(Exception):
    pass


class InvalidTimezoneError(Exception):
    pass


def getDevicesCodenames():
    """Returns a list containing devices codenames"""
    return config.sections()


def getDevicesReadableNames():
    """Returns codename and readable name for each device"""
    return [
        {"codename": s, "readableName": config.get(s).get("userreadablename")}
        for s in getDevicesCodenames()
    ]


class DeviceBuilder(object):
    def __init__(self, device):
        self.device = {}
        for key, value in config.items(device):
            self.device[key] = value

        self.device_case_preserved = {"CONFIG_NAME": f"{device}.properties"}
        for key, value in config_case_preserved.items(device):
            self.device_case_preserved[key] = value

    def setLocale(self, locale):
        # test if provided locale is valid
        if locale is None or type(locale) is not str:
            raise InvalidLocaleError()

        # check if locale matches the structure of a common
        # value like "en_US"
        if match(r"[a-z]{2}\_[A-Z]{2}", locale) is None:
            raise InvalidLocaleError()
        self.locale = locale

    def setTimezone(self, timezone):
        if timezone is None or type(timezone) is not str:
            timezone = self.device.get("timezone")
            if timezone is None:
                raise InvalidTimezoneError()
        self.timezone = timezone

    def getBaseHeaders(self):
        return {
            "Accept-Language": self.locale.replace("_", "-"),
            # "Accept-Encoding": "gzip",
            "X-DFE-Encoded-Targets": DFE_TARGETS,
            "X-DFE-Phenotype": DFE_PHENOTYPE,
            "User-Agent": self.getUserAgent(),
            # "X-Ad-Id": "",
            # "Connection": "keep-alive",
            # "X-Limit-Ad-Tracking-Enabled": "false",
            "X-DFE-Client-Id": "am-android-google",
            "X-DFE-MCCMNC": self.device.get("celloperator"),
            "X-DFE-Network-Type": "4",
            "X-DFE-Content-Filters": "",
            "X-DFE-UserLanguages": self.device.get("locales"),
            # "Host": "android.clients.google.com",
            "X-DFE-Request-Params": "timeoutMs=4000",
        }

    def getDeviceUploadHeaders(self):
        headers = self.getBaseHeaders()
        headers["X-DFE-Enabled-Experiments"] = (
            "cl:billing.select_add_instrument_by_default"
        )
        headers["X-DFE-Unsupported-Experiments"] = (
            "nocache:billing.use_charging_poller,"
            "market_emails,buyer_currency,prod_baseline,checkin.set_asset_paid_app_field,"
            "shekel_test,content_ratings,buyer_currency_in_app,nocache:encrypted_apk,recent_changes"
        )
        headers["X-DFE-SmallestScreenWidthDp"] = "320"
        headers["X-DFE-Filter-Level"] = "3"
        return headers

    def getUserAgent(self):
        version_string = self.device.get("vending.versionstring")
        if version_string is None:
            version_string = "8.4.19.V-all [0] [FP] 175058788"
        return (
            "Android-Finsky/{versionString} ("
            "api=3"
            ",versionCode={versionCode}"
            ",sdk={sdk}"
            ",device={device}"
            ",hardware={hardware}"
            ",product={product}"
            ",platformVersionRelease={platform_v}"
            ",model={model}"
            ",buildId={build_id}"
            ",isWideScreen=0"
            ",supportedAbis={supported_abis}"
            ")"
        ).format(
            versionString=version_string,
            versionCode=self.device.get("vending.version"),
            sdk=self.device.get("build.version.sdk_int"),
            device=self.device.get("build.device"),
            hardware=self.device.get("build.hardware"),
            product=self.device.get("build.product"),
            platform_v=self.device.get("build.version.release"),
            model=self.device.get("build.model"),
            build_id=self.device.get("build.id"),
            supported_abis=self.device.get("platforms").replace(",", ";"),
        )

    def getAuthHeaders(self, gsfid):
        headers = {
            "User-Agent": ("GoogleAuth/1.4 ({device} {id})").format(
                device=self.device.get("build.device"), id=self.device.get("build.id")
            )
        }
        if gsfid is not None:
            headers["device"] = "{0:x}".format(gsfid)
        return headers

    def getLoginParams(self, email, encrypted_passwd):
        return {
            "Email": email,
            "EncryptedPasswd": encrypted_passwd,
            "add_account": "1",
            "accountType": ACCOUNT,
            "google_play_services_version": self.device.get("gsf.version"),
            "has_permission": "1",
            "source": "android",
            "device_country": self.locale[0:2],
            "lang": self.locale,
            "client_sig": "38918a453d07199354f8b19af05ec6562ced5788",
            "callerSig": "38918a453d07199354f8b19af05ec6562ced5788",
        }

    def getAndroidCheckinRequest(self):
        request = googleplay_pb2.AndroidCheckinRequest()
        request.id = 0
        request.checkin.CopyFrom(self.getAndroidCheckin())
        request.locale = self.locale
        request.timeZone = self.timezone
        request.version = 3
        request.deviceConfiguration.CopyFrom(self.getDeviceConfig())
        request.fragment = 0
        return request

    def getDeviceConfig(self):
        libList = self.device["sharedlibraries"].split(",")
        featureList = self.device["features"].split(",")
        localeList = self.device["locales"].split(",")
        glList = self.device["gl.extensions"].split(",")
        platforms = self.device["platforms"].split(",")

        hasFiveWayNavigation = self.device["hasfivewaynavigation"] == "true"
        hasHardKeyboard = self.device["hashardkeyboard"] == "true"
        deviceConfig = googleplay_pb2.DeviceConfigurationProto()
        deviceConfig.touchScreen = int(self.device["touchscreen"])
        deviceConfig.keyboard = int(self.device["keyboard"])
        deviceConfig.navigation = int(self.device["navigation"])
        deviceConfig.screenLayout = int(self.device["screenlayout"])
        deviceConfig.hasHardKeyboard = hasHardKeyboard
        deviceConfig.hasFiveWayNavigation = hasFiveWayNavigation
        deviceConfig.screenDensity = int(self.device["screen.density"])
        deviceConfig.screenWidth = int(self.device["screen.width"])
        deviceConfig.screenHeight = int(self.device["screen.height"])
        deviceConfig.glEsVersion = int(self.device["gl.version"])
        for x in platforms:
            deviceConfig.nativePlatform.append(x)
        for x in libList:
            deviceConfig.systemSharedLibrary.append(x)
        for x in featureList:
            deviceConfig.systemAvailableFeature.append(x)
        for x in localeList:
            deviceConfig.systemSupportedLocale.append(x)
        for x in glList:
            deviceConfig.glExtension.append(x)
        return deviceConfig

    def getAndroidBuild(self):
        androidBuild = googleplay_pb2.AndroidBuildProto()
        androidBuild.id = self.device["build.fingerprint"]
        androidBuild.product = self.device["build.hardware"]
        androidBuild.carrier = self.device["build.brand"]
        androidBuild.radio = self.device["build.radio"]
        androidBuild.bootloader = self.device["build.bootloader"]
        androidBuild.device = self.device["build.device"]
        androidBuild.sdkVersion = int(self.device["build.version.sdk_int"])
        androidBuild.model = self.device["build.model"]
        androidBuild.manufacturer = self.device["build.manufacturer"]
        androidBuild.buildProduct = self.device["build.product"]
        androidBuild.client = self.device["client"]
        androidBuild.otaInstalled = False
        androidBuild.timestamp = int(time() / 1000)
        androidBuild.googleServices = int(self.device["gsf.version"])
        return androidBuild

    def getAndroidCheckin(self):
        androidCheckin = googleplay_pb2.AndroidCheckinProto()
        androidCheckin.build.CopyFrom(self.getAndroidBuild())
        androidCheckin.lastCheckinMsec = 0
        androidCheckin.cellOperator = self.device["celloperator"]
        androidCheckin.simOperator = self.device["simoperator"]
        androidCheckin.roaming = self.device["roaming"]
        androidCheckin.userNumber = 0
        return androidCheckin
