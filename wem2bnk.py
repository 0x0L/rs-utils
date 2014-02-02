#!/usr/bin/env python

"""
Generate Wwise banks suitable for Rocksmith from an Audiokinetic WEM file.

Usage: wem2bnk.py [options] --fileid=ID FILE

Options:
    --preview       Generate a preview soundbank.
    --volume=VOL    Set volume. [default: -5.0]
"""
import random
import struct
import os
# import shutil

CHUNK_SIZE = 51200

PREVIEW = False
VOLUME  = -5.0
FILE_ID = random.randint(0, 2**32)

SOUND_ID  = random.randint(0, 2**32)
BANK_ID   = random.randint(0, 2**32)
ACTION_ID = random.randint(0, 2**32)
BUS_ID    = random.randint(0, 2**32)

# True constants
MIXER_ID         = 0x26c77444
PLUGIN_ID        = 0x40001
DIRECT_PARENT_ID = 0x10000
PARENT_BUS_ID    = 0x9bf0fc29
UNK_ID           = 0xf908c29a
UNK_ID2          = 0x10100

def section(section_name, content):
    """Append header to a section"""

    return section_name + struct.pack('<L', len(content)) + content

def header():
    """Header section"""

    bkhd = struct.pack('<LL', 91, BANK_ID)
    # TODO padding function of CHUNK_SIZE
    bkhd += 20 * chr(0)

    return bkhd

def dataindex():
    """Data Index section"""

    didx = struct.pack('<LLL', FILE_ID, 0, CHUNK_SIZE)
    return didx

def hierarchy():
    """Hierarchy section"""

    # TODO make this tidier and more readable

    sound = struct.pack('<LLLLL', SOUND_ID, PLUGIN_ID, 2, FILE_ID, FILE_ID)
    sound += 3*chr(0)
    sound += struct.pack('<LL', BUS_ID, DIRECT_PARENT_ID)
    sound += struct.pack('<LL', UNK_ID*PREVIEW, MIXER_ID)
    sound += 3*chr(0) + chr(3) + chr(0) + chr(0x2e) + chr(0x2f)
    sound += struct.pack('<fLL', VOLUME, 1, 3)
    sound += 6*chr(0) + 2*chr(PREVIEW) + chr(0)
    sound += struct.pack('<H', PREVIEW)
    sound += 2*chr(0) + chr(PREVIEW) + 11*chr(0)

    mixer = struct.pack('<LHLLLL', MIXER_ID, 0, PARENT_BUS_ID, 0, 0, UNK_ID2)
    mixer += 22*chr(0)
    mixer += struct.pack('<HLL', 0, 1, SOUND_ID)

    action = struct.pack('<LHL', ACTION_ID, 0x403, SOUND_ID)
    action += 3*chr(0) + chr(4)
    action += struct.pack('<L', BANK_ID)

    event = struct.pack('<LLL', random.randint(0, 2**32), 1, ACTION_ID)

    hirc = struct.pack('<L', 4)
    hirc += struct.pack('<BL', 2, len(sound)) + sound
    hirc += struct.pack('<BL', 7, len(mixer)) + mixer
    hirc += struct.pack('<BL', 3, len(action)) + action
    hirc += struct.pack('<BL', 4, len(event)) + event

    return hirc

def stringid(name):
    """StrindID section"""

    stid = struct.pack('<LLLB', 1, 1, BANK_ID, len(name))
    stid += name
    return stid

def build_bnk(name, data):
    """Build a soundbank for the given data chunk"""

    bnk  = section('BKHD', header())
    bnk += section('DIDX', dataindex())
    bnk += section('DATA', data)
    bnk += section('HIRC', hierarchy())
    bnk += section('STID', stringid('Song_' + name))

    return bnk

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    if args['--preview']:
        PREVIEW = True

    FILE_ID = int(args['FILE_ID'])
    VOLUME  = float(args['--volume'])

    f = os.path.basename(args['FILE'])
    base = os.path.basename(os.path.splitext(f)[0])

    chunk = ''
    with open(args['FILE'], 'rb') as fstream:
        chunk = fstream.read(CHUNK_SIZE)
        # with open(str(FILE_ID) + '.wem', 'wb') as cstream:
        #     cstream.write(chunk)
        #     cstream.write(fstream.read())

    with open('song_' + base.lower() + '.bnk', 'wb') as fstream:
        fstream.write(build_bnk(base, chunk))
