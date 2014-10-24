import re
from string import ascii_uppercase


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
                result = review(page, language)
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
    elif list(page["content"].get_object(name=["DISPLAYTITLE"])):
        if [c for c in displaytitle_required
                if "Category:{}/{}".format(c, language) in page["categories"]]:
            return
        for category in displaytitle_notrequired:
            if "Category:{}/{}".format(category, language) in page["categories"]:
                return "Usage of {{tl|DISPLAYTITLE}} on inappropriate page."
simple_reviews.append([displaytitle, "error"])


def name_parameter(page, language):
    infobox = list(page["content"].get_object(name=["Item infobox"]))
    if infobox and list(filter(lambda x: re.search("^\s*?name\s*?$", x.tostring()), infobox[0]["namedp"].keys())):
        if "Category:Cosmetic items/{}".format(language) in page["categories"]:
            return "Usage of the {{code|name}} parameter in the item infobox on an item page."
simple_reviews.append([name_parameter, "error"])


def wikipedia_template(page, language):
    templates = list(page["content"].get_object(name=[re.compile("^w|W$")]))
    if templates:
        return "{} use(s) of {{{{tl|w}}}}; should be replaced with {{{{code|<nowiki>[[w:{}:Link|Caption]]</nowiki>}}}}.".format(
            len(templates),
            language
        )
simple_reviews.append([wikipedia_template, "error"])


def no_label(page, language):
    links = list(page["content"].get_object(type=["wikilink"]))
    bad_links = []
    for link in links:
        if link["label"].tostring() == "" and \
                link["link"].tostring().endswith("/{}".format(language)):
            bad_links.append(
                "{{{{code|<nowiki>{}</nowiki>}}}}".format(link.tostring())
            )
    if bad_links:
        return "No label on localized link(s) {}".format(
            ", ".join(bad_links)
        )
simple_reviews.append([no_label, "error"])


def wrong_category(page, language):
    categories = list(page["content"].get_object(type=["category"]))
    bad_categories = []
    for category in categories:
        if not category["category"].tostring().endswith("/{}".format(language)) and \
                not category["link"]:
            bad_categories.append(
                "{{{{code|<nowiki>{}</nowiki>}}}}".format(category.tostring()))
    if bad_categories:
        return "Wrong category/categories {}".format(
            ", ".join(bad_categories)
        )
simple_reviews.append([wrong_category, "error"])


def localized_template(page, language):
    templates = list(page["content"].get_object(type=["template"]))
    bad_templates = []
    for template in templates:
        if template["name"].tostring().endswith("/{}".format(language)):
            bad_templates.append(
                "{{{{code|<nowiki>{}</nowiki>}}}}".format(template.tostring())
            )
    if bad_templates:
        return "Wrong template(s); translated strings in this template may be moved to the correct one: {}".format(
            ", ".join(bad_templates)
        )
simple_reviews.append([localized_template, "error"])


def no_loadout_name(page, language):
    infobox = list(page["content"].get_object(name=["Item infobox"]))
    if infobox:
        for param in infobox[0]["namedp"]:
            if re.search("loadout-name", param.tostring()):
                break
        else:
            return "No usage of the {{code|loadout-name}} parameter in the item infobox"
simple_reviews.append([no_loadout_name, "warning"])


def external_links(page, language):
    templates = list(page["content"].get_object(name=[re.compile("[Ll]ang icon")]))
    externallinks = list(page["content"].get_object(type=["external link"]))
    difference = len(externallinks) - len(templates)
    if difference > 0:
        return "{} possible external link(s) without {{{{tlx|lang icon|en}}}}".format(difference)
simple_reviews.append([external_links, "warning"])


#-
# Stacked Review
#-
stacked_reviews = []


def stacked_review(pages):
    for language, values in pages.items():
        pass