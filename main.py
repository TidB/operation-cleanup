from collections import OrderedDict
import sys
import time
import traceback

import requests

import review
from wikiparser import Wikitext

# TODO: HTTPS as soon as reactivated!
API_LOCATION = "http://wiki.teamfortress.com/w/api.php"
#LANGUAGES = ["ar", "cs", "da", "de", "es", "fi", "fr", "hu", "it", "ja", "ko", "nl", "no", "pl", "pt", "pt-br", "ro", "ru", "sv", "tr", "zh-hans", "zh-hant"]
LANGUAGES = ["de"]


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def format_pages(all_pages):
    formatted_pages = OrderedDict()
    for page in sorted(all_pages, key=lambda k: k["title"]):
        title = page["title"]
        try:
            content = Wikitext(page["revisions"][0]["*"]).fromstring()
        except Exception:
            print("Error parsing '{0}':\n{1}".format(
                title,
                traceback.format_exc()
            ), file=sys.stderr)
            continue
        categories = [category["title"] for category in page["categories"]]
        displaytitle = page["displaytitle"]
        formatted_pages[title] = {
            "content": content,
            "categories": categories,
            "displaytitle": displaytitle
        }

    return formatted_pages


def retrieve_pagelist(session, language):
    all_pages = session.get(API_LOCATION, params={
        "action": "query",
        "format": "json",
        "redirects": "",
        "prop": "revisions",
        "rvprop": "content",
        "rvsection": "1",
        "titles": "Team Fortress Wiki:Reports/All articles/{}".format(language)
    }).json()

    pages_query = list(all_pages["query"]["pages"].values())[0]
    pages_query = pages_query["revisions"][0]["*"]
    language_pagelist = [page[4:-2] for page in pages_query.splitlines()[1:]]
    return language_pagelist


def retrieve_pages(session, pagetitles):
    all_pages = []
    for chunk in chunker(pagetitles, 50):
        print("chunk:", chunk)
        response = session.post(API_LOCATION, data={
            "action": "query",
            "format": "json",
            "redirects": "",
            "prop": "categories|info|revisions",
            "cllimit": "max",
            "inprop": "displaytitle",
            "rvprop": "content",
            "titles": "|".join(chunk)
        }).json()
        if "warnings" in response:
            print("\tWarning\n", response["warnings"], file=sys.stderr)
        all_pages.extend(
            list(response["query"]["pages"].values())
        )
        time.sleep(0.5)
    return format_pages(all_pages)


def _main(session):
    for language in LANGUAGES:
        pagetitles = retrieve_pagelist(session, language)
        #pagetitles = ["ARG/de", "Ammo/de"]
        pages = retrieve_pages(session, pagetitles)

        review.simple_review(pages, language)

if __name__ == "__main__":
    session = requests.Session()
    session.headers["User-Agent"] = "Operation Cleanup (TidB)"
    _main(session)