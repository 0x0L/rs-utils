#!/usr/bin/env python

"""
Extracts tones from profile _prfldb files and .psarc files

Usage:
    tones.py FILES...
"""

from Crypto.Cipher import AES
import zlib
import struct
import json

import psarc


def append_if_unseen(tones, t):
    try:
        tones.index(t)
    except:
        tones.append(t)


def extract_from_psarc(filename):
    tones = []

    with open(filename, 'rb') as stream:
        entries = psarc.read_toc(stream)
        for idx, entry in enumerate(entries):
            if not entry['filepath'].endswith('.json'):
                continue

            data = psarc.read_entry(stream, entry)
            x = json.loads(data)

            entry_id = x['Entries'].keys()[0]
            o = x['Entries'][entry_id]['Attributes']
            if 'Tones' in o:
                for t in o['Tones']:
                    append_if_unseen(tones, t)

    return tones


PRF_KEY = '728B369E24ED0134768511021812AFC0A3C25D02065F166B4BCC58CD2644F29E'


def extract_from_profile(filename):
    tones = []

    keys = ['Tones', 'BassTones', 'DemoTones', 'CustomTones']
    with open(filename, 'rb') as stream:
        s = stream.read()
        size = struct.unpack('<L', s[16:20])[0]

        cipher = AES.new(PRF_KEY.decode('hex'))
        x = zlib.decompress(cipher.decrypt(psarc.pad(s[20:])))
        assert(size == len(x))

        x = json.loads(x[:-1])
        for u in keys:
            for t in x[u]:
                if t is not None:
                    append_if_unseen(tones, t)

    return tones

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    tones = []
    for f in args['FILES']:
        if f.endswith('.psarc'):
            tones += extract_from_psarc(f)
        elif f.endswith('_prfldb'):
            tones += extract_from_profile(f)

    print json.dumps(tones, indent=2)
