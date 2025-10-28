#!/usr/bin/env python

# set env vars (optional):
# export PLAYSTORE_TOKEN='ya29.fooooo'
# export PLAYSTORE_GSFID='1234567891234567890'
# export PLAYSTORE_DISPENSER_URL='http://goolag.store:1337/api/auth'
# export HTTP_PROXY='http://localhost:8080'
# export HTTPS_PROXY='http://localhost:8080'
# export CURL_CA_BUNDLE='/usr/local/myproxy_info/cacert.pem'

import argparse
import json
import threading
import time

from reprint import output

from playstoreapi.googleplay import GooglePlayAPI


def getChart(categorie, chart, ids):
    """
    Get all ids by downloading all pages
    Every page has 6 entries and the api returns ~110 pages resulting in ~660 ids
    """
    if categorie not in ids:
        ids[categorie] = {}
    if chart not in ids[categorie]:
        ids[categorie][chart] = []
    nextPageUrl = None
    while True:
        data = api.topChart(cat=categorie, chart=chart, nextPageUrl=nextPageUrl)
        s = data.get("subItem")
        if s is None:
            continue
        for subItem in data["subItem"]:
            for app in subItem["subItem"]:
                # print('\t{} ({}): {}'.format(chart, len(ids[chart]), app['id']))
                ids[categorie][chart].append(app["id"])
            try:
                nextPageUrl = subItem["containerMetadata"]["nextPageUrl"]
            except KeyError:
                return


def getAllCharts(out_file):
    """
    parallel downloading of all app charts and saving them in a json file
    """
    charts = [
        "apps_topselling_free",
        "apps_topselling_paid",
        "apps_topgrossing",
        "apps_movers_shakers",
    ]
    categories = ["APPLICATION", "GAME"]
    ids = {}
    threads = []
    for cat in categories:
        for chart in charts:
            t = threading.Thread(target=getChart, args=(cat, chart, ids))
            t.name = f"{cat}: {chart}"
            threads.append(t)
            print("starting thread", t.name)
            t.start()

    with output(output_type="dict") as output_lines:
        alive = 1
        while alive > 0:
            alive = 0
            for t in threads:
                n = t.name.split(": ")
                cat = n[0]
                chart = n[1]
                if t.is_alive():
                    alive += 1
                    output_lines[t.name] = f"{len(ids[cat][chart])} ..."
                else:
                    output_lines[t.name] = f"{len(ids[cat][chart])} (done)"
            time.sleep(0.1)

    print("Waiting for threads")
    for t in threads:
        t.join()

    print("Writing to file", out_file)
    with open(out_file, "w") as fp:
        json.dump(ids, fp, indent=2)


parser = argparse.ArgumentParser(description="Get all charts and save to json file")
parser.add_argument(
    "--output",
    help="name of the output file (default: %(default)s)",
    default="charts.json",
)
parser.add_argument("--locale", default="en_US", help="(default: %(default)s)")
parser.add_argument("--timezone", default="UTC", help="(default: %(default)s)")
parser.add_argument("--device", default="px_3a", help="(default: %(default)s)")

args = parser.parse_args()
api = GooglePlayAPI(args.locale, args.timezone, args.device)
api.envLogin()

getAllCharts(args.output)
