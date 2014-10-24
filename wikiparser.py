"""
This uses a rather unusual approach to parsing. Could be buggy, but shouldn't
most of the time. Simpler solutions would be possible, but I wanted to do
something else with this some time ago. I'll see how this continues.

The commented 'print' statements are just there to be actived quickly for
debugging when a page couldn't be parsed.

Oh, and documentation will follow... maybe.
"""

from collections import OrderedDict
import re


REGEX_TYPE = type(re.compile(""))


class Container(list):
    def __init__(self, seq=None):
        if not seq:
            super().__init__()
        elif isinstance(seq, WikitextObject):
            super().__init__([seq])
        else:
            super().__init__(seq)

    def __contains__(self, item):
        for i in self:
            if re.search(item, i.tostring()):
                return True
        else:
            return False

    def get_object(self, ignoring=True, **kwargs):
        for item in self:
            for sub in item.get_object(ignoring, **kwargs):
                yield sub

    def tostring(self, sep=""):
        return sep.join(item.tostring() for item in self if item)


class ContainerDict(OrderedDict):
    def get_object(self, ignoring=True, **kwargs):
        for value in self.values():
            for sub in value.get_object(ignoring, **kwargs):
                yield sub

    def tostring(self, sep1="|", sep2="="):
        return sep1.join(
            [k.tostring() + sep2 + v.tostring()
             for k, v in self.items()]
        )


class WikitextObject:
    def __str__(self):
        return self.tostring()

    def __getitem__(self, item):
        return self.__dict__[item]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    # Just encapsuling the loops
    def _check_dict(self, **kwargs):
        for key, value in self.__dict__.items():
            if not isinstance(value,
                              (WikitextObject, Container, ContainerDict)):
                value = Text(value)
            if key in kwargs:
                for outer_value in kwargs[key]:
                    if isinstance(outer_value, str) and \
                            outer_value in value.tostring():
                        return True
                    elif isinstance(outer_value, REGEX_TYPE) and \
                            outer_value.search(value.tostring()):
                        return True
        else:
            return False

    def get_object(self, ignoring=True, **kwargs):
        if self.type == "ignore" and ignoring:
            return

        if self._check_dict(**kwargs):
            yield self

        for value in self.__dict__.values():
            if isinstance(value, (WikitextObject, Container, ContainerDict)):
                for sub in value.get_object(ignoring, **kwargs):
                    yield sub

    def tostring(self):
        raise NotImplementedError


class Text(WikitextObject):
    def __init__(self, text=""):
        self.type = "text"
        self.text = text

    def __bool__(self):
        return bool(self.text)

    def __iadd__(self, other):
        return self.text + other

    def tostring(self):
        return self.text


class Category(WikitextObject):
    def __init__(self, category=None, sub=None, link=False):
        self.type = "category"
        self.category = Container(category if category else None)
        self.sub = Container(sub if sub else None)
        self.link = link

    def tostring(self):
        return "[[{0}Category:{01}{2}]]".format(
            ":" if self.link else "",
            self.category.tostring(),
            "|" + self.sub.tostring() if self.sub else ""
        )


class ExternalLink(WikitextObject):
    def __init__(self, link=None, label=None):
        self.type = "external link"
        self.link = Container(link if link else None)
        self.label = Container(label if label else None)

    def tostring(self):
        return "[http{0} {1}]".format(
            self.link.tostring(),
            self.label.tostring()
        )


class File(WikitextObject):
    def __init__(self, prefix=None, file=None, params=None):
        self.type = "file"
        self.prefix = Text(prefix)
        self.file = Container(file if file else None)
        self.params = Container(params if params else None)

    def tostring(self):
        return "[[{0}:{1}{2}]]".format(
            self.prefix.tostring(),
            self.file.tostring(),
            "|" + self.params.tostring("|") if self.params else ""
        )


class Ignore(WikitextObject):
    def __init__(self, content=None, tagopen="", tagclose=""):
        self.type = "ignore"
        self.content = Container(content if content else None)
        self.tagopen = tagopen
        self.tagclose = tagclose

    def tostring(self):
        return "{0}{1}{2}".format(
            self.tagopen,
            self.content.tostring(),
            self.tagclose
        )


class Template(WikitextObject):
    def __init__(self, name=Text(), unnamedp=None, namedp=None):
        self.type = "template"
        self.name = Container(name)
        self.unnamedp = unnamedp if unnamedp else Container()
        self.namedp = namedp if namedp else ContainerDict()

    def tostring(self):
        return "{{{{{0}{1}{2}}}}}".format(
            self.name.tostring(),
            "|" + self.unnamedp.tostring("|") if self.unnamedp else "",
            "|" + self.namedp.tostring() if self.namedp else ""
        )


class Wikilink(WikitextObject):
    def __init__(self, link=None, label=None, anchor=None, interwiki=None):
        self.type = "wikilink"
        self.link = Container(link if link else None)
        self.label = Container(label if label else None)
        self.anchor = Container(anchor if anchor else None)
        self.interwiki = Container(interwiki if interwiki else None)

    def tostring(self):
        return "[[{0}{1}{2}{3}]]".format(
            self.interwiki.tostring(":") + ":" if self.interwiki else "",
            self.link.tostring() if self.link else "",
            "#" + self.anchor.tostring() if self.anchor else "",
            "|" + self.label.tostring() if self.label else ""
        )


class Wikitext:
    def __init__(self, wikitext):
        self.wikitext = wikitext
        self.wikitext_parsed = Container()
        self.childs = Container()
        self.states = []
        self.text_buffer = Container()

    def add_child(self, child):
        if not self.childs or len(self.states) == 1 and self.states[-1][0]:
            self.wikitext_parsed.append(child)
            self.childs.append(child)
        elif len(self.states) > 1:
            state = self.states[-2]
            if state[0] == "file":
                self.childs[-1][state[1]].append(child)
            elif state[0] == "template":
                if len(state) == 1:
                    self.childs[-1]["name"].append(child)
                elif state[1] == "namedp":
                    self.childs[-1]["namedp"][state[2]].append(Container(child))
                elif state[1] == "unnamedp":
                    self.childs[-1]["unnamedp"][-1].extend(Container(child))
            elif state[0] == "wikilink":
                if len(state) > 1:
                    self.childs[-1][state[1]].append(child)
                else:
                    self.childs[-1]["link"].append(child)
            elif state[0] in ["nowiki", "comment"]:
                self.childs[-1]["content"].append(child)
            self.childs.append(child)

    def del_child(self):
        if self.childs:
            self.childs.pop()

    def add_state(self, state):
        self.states.append(state)
        #print("ADD_STATE:", state, "=", self.states)

    def del_state(self, *states):
        if self.states:
            for state in states:
                if state == self.states[-1][:2]:
                    self.states.pop()
                    #print("DEL_STATE:", state, "=", self.states)
                    return True
            else:
                return False

    def _handle_category(self, item):
        category_split = item.split("|")
        self.childs[-1]["category"].append(Text(category_split[0]))
        if len(category_split) == 2:
            self.childs[-1]["sub"].append(Text(category_split[1]))

    def _handle_external_link(self, item):
        if self.states[-1][1] == "link":
            link_split = item.split(" ", maxsplit=1)
            self.childs[-1]["link"].append(Text(link_split.pop(0)))
            if link_split:
                self.childs[-1]["label"].append(Text(link_split[0]))
            self.states[-1][1] = "label"
        elif self.states[-1][1] == "label":
            self.childs[-1]["label"].append(Text(item))

    def _handle_file(self, item):
        split = re.split(
            "("
            "(?!<\{\{)\|(?!\}\})"
            ")",
            item
        )
        for part in split:
            if self.states[-1][1] == "file":
                if item == "|":
                    self.del_state(["file", "file"])
                    self.add_state(["file", "params"])
                else:
                    self.childs[-1]["file"].append(Text(part))
            else:
                self.childs[-1]["params"].append(Text(part))

    def _handle_headline(self, item):
        self.childs[-1]["text"].append(Text(item))

    def _handle_link(self, item):
        split = re.split(
            "("
            "(?<!\{\{)\|(?!\}\})|"
            "(?<!:|\s)#|"
            "(?<=\w):(?=\w)|"
            ")",
            item,
            flags=re.UNICODE)
        for part in split:
            if part == "|":
                self.del_state(["wikilink"],
                               ["wikilink", "anchor"],
                               ["wikilink", "link"])
                self.add_state(["wikilink", "label"])
            elif part == "#" and self.states[-1] != ["wikilink", "label"]:
                self.del_state(["wikilink"], ["wikilink", "link"])
                self.add_state(["wikilink", "anchor"])
            elif part == ":":
                self.childs[-1]["interwiki"].append(Text(last))
                self.childs[-1]["link"].pop()
            else:
                if self.states[-1] == ["wikilink"]:
                    self.childs[-1]["link"].append(Text(part))
                else:
                    state = self.states[-1][1]
                    self.childs[-1][state].append(Text(part))

                last = part

    def _handle_nowiki(self, item):
        self.childs[-1]["content"].append(Text(item))

    def _handle_template(self, item):
        template_split = re.split("(\|)", item)
        if not self.childs[-1].name.tostring():
            template_name = template_split.pop(0)
            if template_split:
                template_split.pop(0)  # Pop the '|'
            self.childs[-1].name.append(Text(template_name))

        for param in [re.split("(?<!\{)=", param) for param in template_split]:
            if param == ["|"]:
                self.states[-1] = [self.states[-1][0]]
            elif self.states[-1][:2] == ["template", "unnamedp"]:
                self.childs[-1].unnamedp[-1].append(Text(param[0]))
            elif self.states[-1][:2] == ["template", "namedp"]:
                last_key = list(self.childs[-1].namedp.keys())[-1]
                self.childs[-1].namedp[last_key].append(Text(param[0]))
            else:
                if len(param) == 1:
                    self.childs[-1].unnamedp.append(Container(Text(param[0])))
                    self.states[-1].extend(["unnamedp"])
                elif len(param) == 2:
                    key = Text(param[0])
                    value = Text(param[1])
                    self.childs[-1].namedp[key] = Container(value)
                    self.states[-1].extend(["namedp", key])

    def fromstring(self):
        wikitext_original = re.split(("("
                                      "\{\{|\}\}|"              # Templates
                                      "\[\[:?Category:|"          # Categories
                                      "\[\[:?File:|"            # Files
                                      "\[\[:?Image:|"
                                      "\[\[:?Media:|"
                                      "\[\[|\]\]|"              # Links & closing brackets
                                      "</?nowiki>|"             # <nowiki> tags
                                      "<!--|-->|"               # HTML comments
                                      "\[http(?=s?://)|(?<=.)\](?!=\])"  # External Links
                                      ")"),
                                     self.wikitext,
                                     flags=re.IGNORECASE)

        #print(wikitext_original)
        for item in wikitext_original:
            #print("item:", item)
            if not item:
                continue
            elif item == "<nowiki>":
                self.add_state(["nowiki"])
                self.add_child(Ignore(tagopen="<nowiki>", tagclose="</nowiki>"))
            elif item == "<!--":
                self.add_state(["comment"])
                self.add_child(Ignore(tagopen="<!--", tagclose="-->"))
            elif item == "</nowiki>":
                self.del_state(["nowiki"])
                self.del_child()
            elif item == "-->":
                self.del_state(["comment"])
                self.del_child()
            elif item == "{{":
                self.add_state(["template"])
                self.add_child(Template())
            elif item == "}}":
                self.del_state(["template"],
                               ["template", "unnamedp"],
                               ["template", "namedp"])
                self.del_child()
            elif item == "[[":
                self.add_state(["wikilink"])
                self.add_child(Wikilink())
            elif item == "]]":
                self.del_state(["wikilink"],
                               ["wikilink", "link"],
                               ["wikilink", "label"],
                               ["wikilink", "anchor"],
                               ["category"],
                               ["file", "file"],
                               ["file", "params"])
                self.del_child()
            elif re.match("\[\[:?Category:", item):
                self.add_state(["category"])
                if item.startswith("[[:"):
                    link = True
                else:
                    link = False
                self.add_child(Category(link=link))
            elif re.match("\[\[:?(File|Media|Image):$", item, flags=re.IGNORECASE):
                self.add_state(["file", "file"])
                file_type = item[2:-1]
                self.add_child(File(prefix=file_type))
            elif re.match("\[http", item):
                self.add_state(["externallink", "link"])
                self.add_child(ExternalLink())
            elif item == "]":
                if self.states and self.states[-1][0] == "externallink":
                    self.del_state(["externallink", "link"],
                                   ["externallink", "label"])
                    self.del_child()
            else:
                if self.states:
                    if self.states[-1][0] == "category":
                        self._handle_category(item)
                    elif self.states[-1][0] == "externallink":
                        self._handle_external_link(item)
                    elif self.states[-1][0] == "file":
                        self._handle_file(item)
                    elif self.states[-1][0] == "template":
                        self._handle_template(item)
                    elif self.states[-1][0] == "wikilink":
                        self._handle_link(item)
                    elif self.states[-1][0] in ["nowiki", "comment"]:
                        self._handle_nowiki(item)
                    else:
                        self.wikitext_parsed.append(Text(item))
                else:
                    self.wikitext_parsed.append(Text(item))
        return self.wikitext_parsed