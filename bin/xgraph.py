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

EXT_TEMPLATE = \
"""<urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/llid> "%(llid)s".
<urn:uuid:%(uid)s> <http://emergent.net/aweb/1.0/logpath> "%(logpath)s".
"""

def run(path):
    output = ''
    path = os.path.normpath(path)

    for dirpath, _, filenames in os.walk(path):
        dpath = dirpath[len(path):]
        for file in filenames:
            fname, ext = os.path.splitext(file)

            if not ext in TAGS:
                continue

            fullpath = dpath + '/' + file
            uid = uuid.uuid3(uuid.NAMESPACE_URL, fullpath)

            output += COMMON_TAG % locals()
            for tag in TAGS[ext]:
                if tag == 'macos' and fullpath.find('audio/windows') > -1:
                    tag = 'dx9'
                output += TAG_TEMPLATE % locals()

            if ext in ['.sng', '.xml', '.dds', '.bnk']:
                llid = str(uid)[:8] + '-0000-0000-0000-000000000000'
                logpath = fullpath.replace(
                    'bin/macos', 'bin').replace('audio/mac', 'audio')
                logpath = logpath.replace(
                    'bin/generic', 'bin').replace('audio/windows', 'audio')
                output += EXT_TEMPLATE % locals()

    return output
