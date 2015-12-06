import requests

import api
import review

TF2WIKI_API_LOCATION = "https://wiki.teamfortress.com/w/api.php"
WIKIPEDIA_API_LOCATION = "https://{}.wikipedia.org/w/api.php"
CHUNK_SIZE = 50
DELAY = 0.5
LANGUAGES = ["ar", "cs", "da", "de", "es", "fi", "fr", "hu", "it", "ja", "ko",
             "nl", "no", "pl", "pt", "pt-br", "ro", "ru", "sv", "tr", "zh-hans",
             "zh-hant"]


def main(session):
    wiki_api = api.API(TF2WIKI_API_LOCATION, session=session)
    for language in LANGUAGES:
        print("Operations for language '{}'".format(language))
        wikipedia_api = api.API(WIKIPEDIA_API_LOCATION, session=session, language="en")
        pagetitles = wiki_api.retrieve_pagelist(language)
        all_pages = wiki_api.retrieve_pages(
            pagetitles, data={
                "action": "query",
                "format": "json",
                "redirects": "",
                "prop": "categories|info|revisions",
                "cllimit": "max",
                "inprop": "displaytitle",
                "rvprop": "content",
            },
            chunk_size=CHUNK_SIZE, delay=DELAY,
        )

        all_pages = [
            page
            for pages in all_pages
            for page in pages["query"]["pages"].values()
        ]

        pages = wiki_api.format_pages(all_pages)
        simple_reviewed_pages = review.simple_review(pages, language)
        stacked_review_pages = review.stacked_review(pages, language, wiki_api, wikipedia_api)
        reviews = review.merge_dicts(simple_reviewed_pages, stacked_review_pages)
        review.save_file(reviews, language)
        print("'{}' done.".format(language))

    print("All done.")

if __name__ == "__main__":
    # Note that you're currently just saving the output as files
    test_session = requests.Session()
    test_session.headers["User-Agent"] = "Operation Cleanup (TidB)"
    main(test_session)
