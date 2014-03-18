from xml.etree import cElementTree as ET


class AttrDict(dict):

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def DefaultSanitizer(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        pass

    try:
        return float(v)
    except (ValueError, TypeError):
        pass

    return v


def xml2AttrDict(text, sanitizer=DefaultSanitizer):
    xml = ET.fromstring(text)

    def helper(node):
        if node.text and node.text.strip():
            return sanitizer(node.text.strip())
        if 'count' in node.attrib:
            return [helper(x) for x in node]

        d = {}
        for tag, v in node.attrib.iteritems():
            d[tag] = sanitizer(v)
        for child in node:
            tag, v = child.tag, helper(child)
            if tag in d and type(d[tag]) == list:
                d[tag].append(v)
            elif tag in d:
                d[tag] = [d[tag], v]
            else:
                d[tag] = v

        return AttrDict(d)

    return helper(xml)
