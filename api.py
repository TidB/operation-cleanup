from collections import OrderedDict
from sys import stderr, getsizeof
from time import sleep

import mwparserfromhell

from helpers import chunker, show_progress


class API:
    def __init__(self, api_location, session=None, language=None):
        self.api_location_raw = api_location

        if language is None:
            self.api_location = api_location
        else:
            self.api_location = api_location.format(language)

        self.language = language

        if session is None:
            import requests
            self.session = requests.session()
        else:
            self.session = session

    def __setattr__(self, name, value):
        """Allow automatic updating of the API location when the language is
        changed"""
        if name == "language":
            self.api_location = self.api_location_raw.format(value)
        object.__setattr__(self, name, value)

    def retrieve_pagelist(self, language):
        show_progress(0, 1, "Retrieving pagelist...")
        all_pages = self.session.get(self.api_location, params={
            "action": "query",
            "format": "json",
            "redirects": "",
            "prop": "revisions",
            "rvprop": "content",
            "rvsection": "1",
            "titles": "Team Fortress Wiki:Reports/All articles/{}".format(
                language
            )
        }).json()

        page_query = list(all_pages["query"]["pages"].values())[0]
        page_query = page_query["revisions"][0]["*"]
        language_pagelist = [page[4:-2] for page in page_query.splitlines()[1:]]
        show_progress(1, 1, "Retrieved pagelist.", True)
        return language_pagelist

    def retrieve_pages(self, pagetitles, data, chunk_size, delay):
        chunks = chunker(pagetitles, chunk_size)
        for i, chunk in enumerate(chunks):
            show_progress(
                i * chunk_size + len(chunk), len(pagetitles),
                "Retrieving chunk '{}'-'{}'".format(chunk[0], chunk[-1])
            )
            data["titles"] = "|".join(chunk)
            response = self.session.post(self.api_location, data=data).json()
            if "warnings" in response:
                print("\tWarning\n", response["warnings"],
                      "\nChunk =", chunk,
                      file=stderr)

            yield response
            sleep(delay)

        show_progress(len(pagetitles), len(pagetitles),
                      "Retrieved chunks.", True)

    @staticmethod
    def format_pages(all_pages):
        """
        Returns an OrderedDict of the form

        {
            title: {
                "title": string,
                "content": mwparserfromhell.Wikicode object,
                "categories": [string, string, ...],
                "displaytitle": string,
            },
            ...
        }
        """
        formatted_pages = OrderedDict()
        for i, page in enumerate(sorted(all_pages, key=lambda k: k["title"])):
            title = page["title"]
            show_progress(i+1, len(all_pages), "Formatting "+title)
            content = mwparserfromhell.parse(page["revisions"][0]["*"])
            categories = [category["title"] for category in page["categories"]]
            displaytitle = page["displaytitle"]
            formatted_pages[title] = {
                "title": title,
                "content": content,
                "categories": categories,
                "displaytitle": displaytitle
            }
        show_progress(len(all_pages), len(all_pages), "Formatted all.", True)

        return formatted_pages
