# set env vars:
# export PLAYSTORE_TOKEN='ya29.fooooo'
# export PLAYSTORE_GSFID='1234567891234567890'
# export HTTP_PROXY='http://localhost:8080'
# export HTTPS_PROXY='http://localhost:8080'
# export CURL_CA_BUNDLE='/usr/local/myproxy_info/cacert.pem'
import zipfile

from playstoreapi.googleplay import GooglePlayAPI

api = GooglePlayAPI("en_GB", "Europe/London")
api.envLogin()

# SEARCH
print("\nSearch suggestion for 'fir'\n")
print(api.searchSuggest("fir"))

result = api.search("firefox")
for doc in result:
    if "id" in doc:
        print("doc: {}".format(doc["id"]))
    for cluster in doc["subItem"]:
        print("\tcluster: {}".format(cluster["id"]))
        for app in cluster["subItem"]:
            print("\t\tapp: {}".format(app["id"]))


# HOME APPS
print("\nFetching apps from play store home\n")
result = api.home()

for doc in result:
    for cluster in doc["subItem"]:
        print("cluster: {}".format(cluster.get("id")))
        try:
            for app in cluster["subItem"]:
                print("\tapp: {}".format(app.get("id")))
        except KeyError:
            pass

# DOWNLOAD
test_apps = ["org.mozilla.focus", "com.google.android.apps.tachyon"]
for docid in test_apps:
    print(f"\nAttempting to download {docid}\n")
    fl = api.download(docid)
    if "splits" in fl and fl["splits"]:
        with zipfile.ZipFile(docid + ".apks", "w") as apks_zip:
            main_file_info = fl.get("file")
            main_stream_data = api._deliver_data(
                main_file_info["url"], main_file_info["cookies"]
            )
            main_data = b"".join(main_stream_data.get("data"))
            apks_zip.writestr("base.apk", main_data)
            print("\nDownload base apk successful\n")
            for split in fl.get("splits"):
                split_file_info = split["file"]
                split_stream_data = api._deliver_data(
                    split_file_info["url"], split_file_info["cookies"]
                )
                split_data = b"".join(split_stream_data["data"])
                split_name = f"split_{split['name']}.apk"
                apks_zip.writestr(split_name, split_data)
        print("\nDownload splits successful\n")
    else:
        main_file_info = fl.get("file")
        main_stream_data = api._deliver_data(
            main_file_info["url"], main_file_info["cookies"]
        )
        with open(docid + ".apk", "wb") as apk_file:
            for chunk in main_stream_data.get("data"):
                if chunk:
                    apk_file.write(chunk)
        print("\nDownload successful\n")

# BULK DETAILS
testApps = ["org.mozilla.focus", "com.non.existing.app"]
bulk = api.bulkDetails(testApps)

print("\nTesting behaviour for non-existing apps\n")
if bulk[1] is not None:
    print("bulkDetails should return empty dict for non-existing apps")
    exit(1)

print("\nResult from bulkDetails for {}\n".format(testApps[0]))
print(bulk[0]["id"])

# DETAILS
print("\nGetting details for %s\n" % testApps[0])
details = api.details(testApps[0])
print(details["title"])

# REVIEWS
print("\nGetting reviews for %s\n" % testApps[0])
revs = api.reviews(testApps[0])
for r in revs:
    print(
        "UserId: {0} Vote: {1}".format(
            r["userProfile"]["profileId"], str(r["starRating"])
        )
    )

# BROWSE
print("\nBrowse play store categories\n")
browse = api.browse()
for c in browse.get("category"):
    print(c["name"])

sampleCat = browse["category"][
    0
]  # ['serverLogsCookie']  # ['categoryIdContainer']['categoryId']
print("\nBrowsing the {} category\n".format(sampleCat["name"]))
# print(sampleCat['dataUrl'])
browseCat = api.home(sampleCat["dataUrl"])

for doc in browseCat:
    if "id" in doc:
        print("doc: {}".format(doc["id"]))
    for child in doc["subItem"]:
        print("\tsubcat: {}".format(child.get("title")))
        for app in child["subItem"]:
            print("\t\tapp: {}".format(app["id"]))

# broken
# # LIST
# cat = 'ART_AND_DESIGN'
# print('\nList {} subcategories\n'.format(cat))
# catList = api.list(cat)
# for c in catList:
#     print(c)

# limit = 4
# print('\nList only {} apps from subcat {} for {} category\n'.format(limit, catList[0], cat))
# appList = api.list(cat, catList[0], 4, 1)
# for app in appList:
#     print(app['docid'])
