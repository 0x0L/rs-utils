#!/usr/bin/env python

"""
Generate aggregated graph for the package

Usage: xgraph.py DIRS...
"""

import os
import uuid

COMMON_TAG = \
    """<urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/canonical> "%(dpath)s".
    <urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/name> "%(fname)s".
    <urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/relpath> "%(fullpath)s".
    """

TAG_TEMPLATE = \
    '<urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/tag> "%(tag)s".\n'

TAGS = {
    '.json': ['database', 'json-db'],
    '.hsan': ['database', 'hsan-db'],
    '.xblock': ['emergent-world', 'x-world'],
    '.sng': ['application', 'macos', 'musicgame-song'],
    '.xml': ['application', 'xml'],
    '.dds': ['dds', 'image'],
    '.bnk': ['audio', 'wwise-sound-bank']  # ,'macos']
}

# EXT_TEMPLATE for sng, xml, dds, bnk
# logpath pour sng et bnk sans platform
EXT_TEMPLATE = \
    """<urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/llid> "%(llid)s".
    <urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/logpath> "%(logpath)s".
    """

if __name__ == '__main__':
    from docopt import docopt

    args = docopt(__doc__)

    for path in args['DIRS']:
        output = ''
        path = os.path.normpath(path)
        print 'Processing', path

        for dirpath, _, filenames in os.walk(path):
            dpath = dirpath[len(path):]
            for file in filenames:
                fname, ext = os.path.splitext(file)

                if ext in TAGS:
                    fullpath = dpath + '/' + file
                    uid = uuid.uuid3(uuid.NAMESPACE_URL, fullpath)

                    output += COMMON_TAG % locals()
                    for tag in TAGS[ext]:
                        output += TAG_TEMPLATE % locals()

                    if ext in ['.sng', '.xml', '.dds', '.bnk']:
                        llid = str(uid)[:8] + '-0000-0000-0000-000000000000'
                        logpath = fullpath.replace(
                            'macos/', '').replace('mac/', '')
                        output += EXT_TEMPLATE % locals()

        fname = path + '/' + os.path.basename(path) + '_aggregategraph.nt'
        with open(fname, 'w') as fstream:
            fstream.write(output)
