from xml.etree import cElementTree as ET


class AttrDict(dict):

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def DefaultConverter(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        pass

    try:
        return float(v)
    except (ValueError, TypeError):
        pass

    if v == 'true':
        return True
    elif v == 'false':
        return False

    return v


# To bypass the `count` super element in chordNotes
class InlineContent(list):
    pass


def singular(names):
    if names.endswith('ies'):
        singular = names[:-4] + 'y'
    else:
        singular = names[:-1]
    return singular


def createXmlElem(name, o):
    if issubclass(type(o), dict):
        att = {}
        chi = {}
        for k, v in o.iteritems():
            if k.startswith('@'):
                att[k[1:]] = str(v)
            else:
                chi[k] = v
        e = ET.Element(name, att)
        for k, v in iter(sorted(chi.iteritems())):
            if type(v) is InlineContent:
                for x in v:
                    e.append(createXmlElem(singular(k), x))
            else:
                e.append(createXmlElem(k, v))

        return e

    if type(o) is list:
        e = ET.Element(name, count=str(len(o)))
        for v in o:
            e.append(createXmlElem(singular(name), v))

        return e

    e = ET.Element(name)
    e.text = str(o)
    return e


def json2xml(name, o):
    return ET.tostring(createXmlElem(name, o))


def createJsonElem(node, processor, notag):
    if node.text and node.text.strip():
        return processor(node.text.strip())
    if ['count'] == node.attrib.keys() \
            and len(node) == int(node.attrib['count']):
        return [createJsonElem(x, processor, notag) for x in node]

    d = {}
    for tag, v in node.attrib.iteritems():
        if notag:
            d[tag] = processor(v)
        else:
            d['@' + tag] = processor(v)

    for child in node:
        tag, v = child.tag, createJsonElem(child, processor, notag)
        if tag in d and type(d[tag]) is InlineContent:
            d[tag].append(v)
        elif tag in d:
            d[tag] = InlineContent([d[tag], v])
        else:
            d[tag] = v

    return AttrDict(d)


def xml2json(text, processor=DefaultConverter, notag=False):
    xml = ET.fromstring(text)
    return createJsonElem(xml, processor, notag)
