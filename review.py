import re
from string import ascii_uppercase
import sys
import traceback


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
]

EXTERNAL_LINK_EXCEPTIONS = [
    "(https?://(www)?\.?(store)?\.?steampowered\.com)",
    "(.*?\.(jpg|png))",
]


#-
# Simple Review
#-
simple_reviews = []


def simple_review(pages, language):
    with open("results{}.txt".format(language.upper()), "wb") as f:
        f.write(bytes(
            "{{Languages}}\n{{Compact ToC|symnum=yes}}\n__NOTOC__\n== !–9 ==\n",
            "utf-8"
        ))
        current_char = "Whatever"
        for title, page in pages.items():
            if title[0] in ascii_uppercase and title[0] != current_char:
                current_char = title[0]
                f.write(bytes(
                    "\n== {} ==\n".format(current_char),
                    "utf-8"
                ))
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
                    reviews.append(review(page, language)+"\n")
            if reviews:
                f.write(bytes(
                    "=== [[{}]] ===\n".format(title) +
                    "".join(reviews) +
                    "\n",
                    "utf-8"
                ))


def displaytitle(page, language):
    displaytitle_notrequired = ["Cosmetic items", "Weapons", "Patches", "Tools", "Action items"]
    displaytitle_required = ["Major updates"]
    if page["displaytitle"].endswith("/{}".format(language)):
            return "Not displaying the correct title; {{tl|DISPLAYTITLE}} might be needed."
    elif page["content"].filter_templates(matches="DISPLAYTITLE:"):
        if [c for c in displaytitle_required
                if "Category:{}/{}".format(c, language) in page["categories"]]:
            return
        for category in displaytitle_notrequired:
            if "Category:{}/{}".format(category, language) in page["categories"]:
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


def no_label(page, language):
    links = page["content"].filter_wikilinks(
        matches=lambda x: not x.title.startswith("Category:")
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
        return "{} possible external link(s) without {{{{tlx|lang icon|en}}}}".format(
            difference
        )
simple_reviews.append([external_links, "warning"])


#-
# Stacked Review
#-
stacked_reviews = []


def stacked_review(pages):
    for language, values in pages.items():
        pass