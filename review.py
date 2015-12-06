from collections import OrderedDict
import re
from string import ascii_uppercase
import sys
import traceback

from helpers import show_progress

CHUNK_SIZE = 50
DELAY = 0.5

CATEGORY_EXCEPTIONS = [
    "(Category:Item infobox usage)",
    "(Category:Item infobox using 'loadout-name')",
    "(Category:Stubs/lang)",
    "(Category:Featured articles/lang)",
    "(Category:Item infobox using 'loadout-prefix')",
    "(Category:Quotations needing translating)",
    "(Category:Maps supporting bots)",
    "(Category:Pages needing citations)",
    "(Category:Pages with broken file links)",
    "(Category:Articles needing images)",
    "(Category:Translations needing updating)",
    "(Category:Translating into .*?)",
    "(Category:Lists to be expanded)",
    "(Category:Out of date pages)",
]

EXTERNAL_LINK_EXCEPTIONS = [
    "(https?://(www)?\.?(store)?\.?steampowered\.com)",
    "(.*?\.(jpg|png))",
]

DISPLAYTITLE_NOTREQUIRED = [
    "Cosmetic items",
    "Weapons",
    "Patches",
    "Tools",
    "Action items",
]

DISPLAYTITLE_REQUIRED = [
    "Major updates",
]


def merge_dicts(all_reviews1, all_reviews2):
    reviews = all_reviews1.copy()
    for title, reviews2 in all_reviews2.items():
        if title in reviews:
            reviews[title].extend(reviews2)
        else:
            reviews[title] = reviews2

    return OrderedDict(sorted(reviews.items()))


# -------------
# Simple Review
# -------------
simple_reviews = []


def save_file(reviewed_pages, language):
    with open("results{}.txt".format(language.upper()), "wb") as file:
        file.write(bytes(
            "{{Languages}}\n{{Compact ToC|symnum=yes}}\n__NOTOC__\n== !-9 ==\n",
            "utf-8"
        ))
        current_char = "Whatever this doesn't even matter"
        for title, value in reviewed_pages.items():
            if title[0] in ascii_uppercase and title[0] != current_char:
                current_char = title[0]
                file.write(bytes(
                    "\n== {} ==\n".format(current_char),
                    "utf-8"
                ))

            file.write(bytes(
                "=== [[{}]] ===\n".format(title) +
                "".join(value) +
                "\n",
                "utf-8"
            ))


def simple_review(pages, language):
    reviewed_pages = OrderedDict()
    for i, (title, page) in enumerate(pages.items()):
        show_progress(i+1, len(pages), "Reviewing "+title)
        reviews = []
        for review, level in simple_reviews:
            try:
                result = review(page, language)
            except Exception:
                print("Error reviewing", title, file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                continue
            if result is not None:
                reviews.append("* ")
                if level == "error":
                    reviews.append("{{c|x|Error}} ")
                elif level == "warning":
                    reviews.append("{{c|!|Warning}} ")
                reviews.append(result+"\n")
        if reviews:
            reviewed_pages[title] = reviews
    show_progress(len(pages), len(pages), "Reviewed all.", True)
    return reviewed_pages


def displaytitle(page, language):
    if page["displaytitle"].endswith("/{}".format(language)):
            return "Not displaying the correct title; {{tl|DISPLAYTITLE}} might be needed."
    elif page["content"].filter_templates(matches="DISPLAYTITLE:"):
        if [
            c for c in DISPLAYTITLE_REQUIRED
            if "Category:{}/{}".format(c, language) in page["categories"]
        ]:
            return
        for category in DISPLAYTITLE_NOTREQUIRED:
            if "Category:{}/{}".format(category, language) in page["categories"] and \
                    page["title"] != "{}/{}".format(category, language):
                return "Usage of {{tl|DISPLAYTITLE}} on inappropriate page."
simple_reviews.append([displaytitle, "error"])


def name_parameter(page, language):
    if page["content"].filter_templates(
        matches=lambda x: x.name.matches("Item infobox") and x.has("name")
    ):
        if "Category:Cosmetic items/{}".format(language) in page["categories"]:
            return "Usage of the {{code|name}} parameter in the item infobox on an item page."
simple_reviews.append([name_parameter, "error"])


def wikipedia_template(page, language):
    templates = page["content"].filter_templates(
        matches=lambda x: x.name.matches("w")
    )
    if templates:
        return "{} use(s) of {{{{tl|w}}}}; should be replaced with {{{{code|<nowiki>[[w:{}:Link|Caption]]</nowiki>}}}}.".format(
            len(templates),
            language
        )
simple_reviews.append([wikipedia_template, "error"])


def if_lang(page, language):
    templates = page["content"].filter_templates(
        matches=lambda x: x.name.matches("if lang")
    )
    if templates:
        return "{} use(s) of {{{{tl|if lang}}}}; should be replaced with {{{{code|/{}}}}}.".format(
            len(templates),
            language
        )
simple_reviews.append([if_lang, "error"])


def no_label(page, language):
    links = page["content"].filter_wikilinks(
        matches=lambda x: not x.title.lower().startswith("category:")
    )
    bad_links = [
        "{{{{code|<nowiki>{}</nowiki>}}}}".format(link)
        for link in links
        if not link.text and link.title.endswith("/{}".format(language))
    ]
    if bad_links:
        return "No label on localized link(s) {}".format(
            ", ".join(bad_links)
        )
simple_reviews.append([no_label, "error"])


def wrong_category(page, language):
    bad_categories = [
        "{{{{code|<nowiki>{}</nowiki>}}}}".format(category)
        for category in page["categories"]
        if (not re.match("|".join(CATEGORY_EXCEPTIONS), category)) and
        not category.endswith("/{}".format(language))
    ]
    if bad_categories:
        return "Wrong category/categories {}".format(
            ", ".join(bad_categories)
        )
simple_reviews.append([wrong_category, "warning"])


def localized_template(page, language):
    templates = page["content"].ifilter_templates()
    bad_templates = [
        "{{{{code|<nowiki>{}</nowiki>}}}}".format(template.name)
        for template in templates
        if template.name.endswith("/{}".format(language))
    ]
    if bad_templates:
        return "Wrong template(s); translated strings in this template(s) may be moved to the correct one(s): {}".format(
            ", ".join(bad_templates)
        )
simple_reviews.append([localized_template, "error"])


def no_loadout_name(page, _):
    infobox = page["content"].filter_templates(matches="Item infobox")
    if infobox and not infobox[0].has("loadout-name"):
        return "No usage of the {{code|loadout-name}} parameter in the item infobox"
simple_reviews.append([no_loadout_name, "warning"])


def external_links(page, language):
    # Filter "this item was [http://steamcommunity.com contributed] to..."
    externallinks = [
        link
        for link in page["content"].filter_external_links()
        if not (
            "Category:Community-contributed items/{}".format(language) in page["categories"] and
            re.match("https?://(www)?\.?steamcommunity\.com/sharedfiles/filedetails/", link.url.strip_code())
        )
    ]

    patch_layout = page["content"].filter_templates(matches="Patch layout")
    if patch_layout:
        patch_layout = patch_layout[0]
        for link in externallinks:
            if (
                    # Filter special patch links with automatic {{Lang icon}}
                    (
                        patch_layout.has("source") and
                        patch_layout.get("source").value.strip() and
                        link is patch_layout.get("source").value.filter_external_links()[0]
                    ) or
                    (
                        patch_layout.has("updatelink") and
                        link is patch_layout.get("updatelink").value.filter_external_links()[0]
                    )
            ):
                externallinks.remove(link)

    # Filter other exceptions
    for link in externallinks:
        if re.match("|".join(EXTERNAL_LINK_EXCEPTIONS), link.url.strip_code()):
            externallinks.remove(link)

    templates = page["content"].filter_templates(matches="Lang icon")
    difference = len(externallinks) - len(templates)
    if difference > 0:
        return "{} external link(s) without {{{{tlx|lang icon|en}}}}".format(
            difference
        )
simple_reviews.append([external_links, "warning"])


# --------------
# Stacked Review
# --------------
stacked_reviews = []


def stacked_review(pages, language, wiki_api, wikipedia_api):
    """Reviews based on retrieved TF2 Wiki and Wikipedia pages."""
    reviewed_pages = OrderedDict()

    prefixes = get_prefixes(wiki_api)
    pages, wikilinks = get_wikilinks(pages, language, prefixes)
    pages, wikipedia_links = get_wikipedia_links(pages)
    wikilinks_normal = normalize_wikilinks(wikilinks, wiki_api)

    wikipedia_missing, wikipedia_english, wikipedia_interwiki = \
        normalize_wikipedia(wikipedia_links, wikipedia_api)
    wikipedia_localized, wikipedia_missing_language = normalize_wikipedia_localized(
        wikipedia_interwiki,
        wikipedia_api,
        language
    )

    arguments = {
        "wikilinks_normal": wikilinks_normal,
        "wikipedia_missing": merge_dicts(wikipedia_missing, wikipedia_missing_language),
        "wikipedia_english": wikipedia_english,
        "wikipedia_localized": wikipedia_localized
    }

    for title, page in pages.items():
        reviews = []
        for review, args, level in stacked_reviews:
            try:
                result = review(page, language, arguments[args])
            except Exception:
                print("Error reviewing", title, file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                continue
            if result is not None:
                reviews.append("* ")
                if level == "error":
                    reviews.append("{{c|x|Error}} ")
                elif level == "warning":
                    reviews.append("{{c|!|Warning}} ")
                reviews.append(result+"\n")
        if reviews:
            reviewed_pages[title] = reviews
    return reviewed_pages


def get_prefixes(wiki_api):
    """Get the used prefixes for interwiki links which have to be ignored.
    Returns a list string, each one being a prefix."""
    response = wiki_api.session.get(wiki_api.api_location, params={
        "action": "query",
        "meta": "siteinfo",
        "siprop": "interwikimap",
        "format": "json",
    }).json()

    prefixes = [item["prefix"] for item in response["query"]["interwikimap"]]
    return prefixes


def get_wikilinks(pages, language, prefixes):
    """Get wikilinks and links inside 'main' and 'see also' templates."""
    all_links = set()
    for page in pages.values():
        links = set()

        # Collecting ordinary wikilinks
        for wikilink in page["content"].filter_wikilinks():
            links.add(str(wikilink.title))

        # Collecting wikilinks inside "main" and "see also" templates
        for template in page["content"].filter_templates(
            matches=lambda x: str(x.name) in ("see also", "main")
        ):
            for link in template.params:
                if not link.showkey:
                    links.add(str(link.value))

        # Removing duplicates, eliminating all non-wikilinks
        cleaned_links = {
            link for link in links
            if
            not re.match(                                                       # Must be in main namespace
                ":?(category|file|image|media|{}):".format("|".join(prefixes)),
                link, flags=re.I
            ) and
            not any(x in link for x in "{}[]<>") and                            # Containing special chars
            not link.startswith("#") and                                        # In-page links
            not "/{}".format(language) in link                                  # Localized links
        }

        all_links = all_links | cleaned_links
        pages[page["title"]]["wikilinks"] = list(links)

    return pages, list(all_links)


def get_wikipedia_links(pages):
    all_links = set()
    for page in pages.values():
        links = set()

        for wikipedia_link in page["content"].filter_wikilinks():
            title = str(wikipedia_link.title)
            if re.match("(w|wikipedia):", title, flags=re.I):
                title = re.sub("^(w|wikipedia):", "", title, flags=re.I)
                links.add(title)

        all_links = all_links | links
        pages[page["title"]]["wikipedia"] = list(links)

    return pages, list(all_links)


def normalize_wikilinks(links, wiki_api):
    """Create a dictionary with the format

    {
        "title": ["alias", "alias", ...]
    }
    """

    site = wiki_api.retrieve_pages(
        links,
        data={
            "action": "query",
            "format": "json",
            "redirects": "",
        },
        chunk_size=CHUNK_SIZE,
        delay=DELAY,
    )

    pages = {}
    for items in site:
        items = items["query"]

        # Create entries for each page we're *actually* linking to (after
        # normalizing links and resolving redirects)
        for value in items["pages"].values():
            if value["title"] not in pages and "missing" not in value:
                pages[value["title"]] = []

        # Add resolved redirects to a page's aliases
        if "redirects" in items:
            for redirect in items["redirects"]:
                for page, aliases in pages.items():
                    if redirect["to"] == page \
                            and redirect["from"] not in aliases:
                        pages[page].append(redirect["from"])

        # Add normalized forms of the link or its aliases
        if "normalized" in items:
            for normal in items["normalized"]:
                for page, aliases in pages.items():
                    if (normal["to"] == page or normal["to"] in aliases) \
                            and normal["from"] not in aliases:
                        pages[page].append(normal["from"])

    return pages


def normalize_wikipedia(links, wiki_api):
    """Create a dictionary with the format

    {
        "title": ["alias", "alias", ...]
    }
    """

    site = wiki_api.retrieve_pages(
        links,
        data={
            "action": "query",
            "format": "json",
            "redirects": "",
        },
        chunk_size=CHUNK_SIZE,
        delay=DELAY,
    )

    missing_pages = {}
    english_pages = {}
    interwiki_pages = {}

    for items in site:
        items = items["query"]

        # All pages retrieved in the first run are English or missing
        if "pages" in items:
            for value in items["pages"].values():
                if "missing" in value:
                    missing_pages[value["title"]] = []
                else:
                    english_pages[value["title"]] = []

        # All interwiki links
        if "interwiki" in items:
            for page in items["interwiki"]:
                interwiki_pages[page["title"]] = []

        # Add resolved redirects to a page's aliases
        if "redirects" in items:
            for redirect in items["redirects"]:
                for dictionary in [english_pages, interwiki_pages, missing_pages]:
                    for page, aliases in dictionary.items():
                        if redirect["to"] == page \
                                and redirect["from"] not in aliases:
                            dictionary[page].append(redirect["from"])

        # Add normalized forms of the link or its aliases
        if "normalized" in items:
            for normal in items["normalized"]:
                for dictionary in [english_pages, interwiki_pages, missing_pages]:
                    for page, aliases in dictionary.items():
                        if (normal["to"] == page or normal["to"] in aliases) \
                                and normal["from"] not in aliases:
                            dictionary[page].append(normal["from"])

    return missing_pages, english_pages, interwiki_pages


def normalize_wikipedia_localized(interwiki_links, wikipedia_api, language):
    if language == "pt-br":
        language = "pt"
    elif language in ["zh-hans", "zh-hant"]:
        language = "zh"
    wikipedia_api.language = language

    site = wikipedia_api.retrieve_pages(
        list(interwiki_links.keys()),
        data={
            "action": "query",
            "format": "json",
            "redirects": "",
        },
        chunk_size=CHUNK_SIZE,
        delay=DELAY,
    )

    missing_pages = {}
    language_pages = {}

    for items in site:
        items = items["query"]

        # All pages retrieved in the first run are English or missing
        if "pages" in items:
            for value in items["pages"].values():
                if "missing" in value:
                    missing_pages[value["title"]] = []
                else:
                    language_pages[value["title"]] = []

        # Add resolved redirects to a page's aliases
        if "redirects" in items:
            for redirect in items["redirects"]:
                for dictionary in [language_pages, missing_pages]:
                    for page, aliases in dictionary.items():
                        if redirect["to"] == page \
                                and redirect["from"] not in aliases:
                            dictionary[page].append(redirect["from"])

        # Add normalized forms of the link or its aliases
        if "normalized" in items:
            for normal in items["normalized"]:
                for dictionary in [language_pages, missing_pages]:
                    for page, aliases in dictionary.items():
                        if (normal["to"] == page or normal["to"] in aliases) \
                                and normal["from"] not in aliases:
                            dictionary[page].append(normal["from"])

    return language_pages, missing_pages


def wrong_wikilinks(page, language, wikilinks_normal):
    errors = []
    for original, aliases in wikilinks_normal.items():
        if original.endswith("/{}".format(language)):
            continue
        intersection = (set(aliases) | {original}) & set(page["wikilinks"])
        if intersection:
            errors.extend(list(intersection))

    if errors:
        return "Links '{}' are leading to the wrong language.".format(
            "', '".join(errors)
        )
stacked_reviews.append([wrong_wikilinks, "wikilinks_normal", "error"])


def wrong_wikipedia_links(page, language, wikipedia_english):
    errors = []
    for original, aliases in wikipedia_english.items():
        intersection = (set(aliases) | {original}) & set(page["wikipedia"])
        if intersection:
            errors.extend(list(intersection))

    if errors:
        return "Wikipedia links '{}' are leading to the English page.".format(
            "', '".join(errors)
        )
stacked_reviews.append([wrong_wikipedia_links, "wikipedia_english", "warning"])


def missing_wikipedia_pages(page, language, wikipedia_missing):
    errors = []
    for original, aliases in wikipedia_missing.items():
        intersection = (set(aliases) | {original}) & set(page["wikipedia"])
        if intersection:
            errors.extend(list(intersection))

    if errors:
        return "Wikipedia links '{}' don't exist.".format(
            "', '".join(errors)
        )
stacked_reviews.append([missing_wikipedia_pages, "wikipedia_missing", "error"])
