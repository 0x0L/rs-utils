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

SAVE_IO_KEY = '728B369E24ED0134768511021812AFC0A3C25D02065F166B4BCC58CD2644F29E'

def append_if_unseen(tones, t):
    try:
        tones.index(t)
    except:
        tones.append(t)

def process_psarc(stream):
    tones = []

    entries = psarc.read_toc(stream)
    for idx, entry in enumerate(entries):
        if not entry['filepath'].endswith('.json'):
            continue

        data = psarc.read_entry(stream, entry)
        x = json.loads(data)

        entry_id = x['Entries'].keys()[0]
        o = x['Entries'][entry_id]['Attributes']
        if o.has_key('Tones'):
            for t in o['Tones']:
                append_if_unseen(tones, t)

    return tones

pKeys = ['Tones', 'BassTones', 'DemoTones', 'CustomTones']
def process_profile(stream):
    tones = []

    s = stream.read()
    size = struct.unpack('<L', s[16:20])[0]

    cipher = AES.new(SAVE_IO_KEY.decode('hex'))
    x = zlib.decompress(cipher.decrypt(psarc.pad(s[20:])))
    assert( size == len(x) )

    x = json.loads(x[:-1])
    for u in pKeys:
        for t in x[u]:
            if t != None:
                append_if_unseen(tones, t)

    return tones

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    tones = []
    for fname in args['FILES']:
        with open(fname, 'rb') as f:
            if fname.endswith('.psarc'):
                tones += process_psarc(f)
            elif fname.endswith('_prfldb'):
                tones += process_profile(f)

    print json.dumps(tones, indent=2)