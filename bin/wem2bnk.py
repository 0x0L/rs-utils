import random
import struct

CHUNK_SIZE = 51200

MIXER_ID = 0x26c77444
PLUGIN_ID = 0x40001
DIRECT_PARENT_ID = 0x10000
PARENT_BUS_ID = 0x9bf0fc29
UNK_ID = 0xf908c29a
UNK_ID2 = 0x10100


def hush(x):
    x = x.lower()
    ha = 2166136261
    for c in x:
        ha *= 16777619
        ha = ha ^ ord(c)
        ha &= 0xFFFFFFFF
    return ha

class BnkGenerator:
    def __init__(self, inputfile, preview=False):
        with open(inputfile, 'rb') as fstream:
            self.data = fstream.read(CHUNK_SIZE)
        self.CHUNK_SIZE = len(self.data)

        self.preview = preview
        self.volume = -5.0

        self.FILE_ID = random.randint(0, 2 ** 32)
        self.SOUND_ID = random.randint(0, 2 ** 32)
        self.BANK_ID = random.randint(0, 2 ** 32)
        self.ACTION_ID = random.randint(0, 2 ** 32)
        self.BUS_ID = random.randint(0, 2 ** 32)

    def header(self):
        """Header section"""

        bkhd = struct.pack('<LL', 91, self.BANK_ID)
        # TODO padding function of CHUNK_SIZE
        bkhd += 20 * chr(0)

        return bkhd


    def dataindex(self):
        """Data Index section"""

        didx = struct.pack('<LLL', self.FILE_ID, 0, self.CHUNK_SIZE)
        return didx


    def hierarchy(self, name):
        """Hierarchy section"""

        # TODO make this tidier and more readable

        sound = struct.pack('<LLLLL', self.SOUND_ID, PLUGIN_ID, 2, self.FILE_ID, self.FILE_ID)
        sound += 3 * chr(0)
        sound += struct.pack('<LL', self.BUS_ID, DIRECT_PARENT_ID)
        sound += struct.pack('<LL', UNK_ID * self.preview, MIXER_ID)
        sound += 3 * chr(0) + chr(3) + chr(0) + chr(0x2e) + chr(0x2f)
        sound += struct.pack('<fLL', self.volume, 1, 3)
        sound += 6 * chr(0) + 2 * chr(self.preview) + chr(0)
        sound += struct.pack('<H', self.preview)
        sound += 2 * chr(0) + chr(self.preview) + 11 * chr(0)

        mixer = struct.pack('<LHLLLL', MIXER_ID, 0, PARENT_BUS_ID, 0, 0, UNK_ID2)
        mixer += 22 * chr(0)
        mixer += struct.pack('<HLL', 0, 1, self.SOUND_ID)

        action = struct.pack('<LHL', self.ACTION_ID, 0x403, self.SOUND_ID)
        action += 3 * chr(0) + chr(4)
        action += struct.pack('<L', self.BANK_ID)

        event = struct.pack('<LLL', hush(name), 1, self.ACTION_ID)

        hirc = struct.pack('<L', 4)
        hirc += struct.pack('<BL', 2, len(sound)) + sound
        hirc += struct.pack('<BL', 7, len(mixer)) + mixer
        hirc += struct.pack('<BL', 3, len(action)) + action
        hirc += struct.pack('<BL', 4, len(event)) + event

        return hirc


    def stringid(self, name):
        """StrindID section"""

        stid = struct.pack('<LLLB', 1, 1, self.BANK_ID, len(name))
        stid += name
        return stid


    def build_bnk(self, name):
        """Build a soundbank for the given data chunk"""

        def section(section_name, content):
            return section_name + struct.pack('<L', len(content)) + content

        suffix = '_Preview' if self.preview else ''

        bnk = section('BKHD', self.header())
        bnk += section('DIDX', self.dataindex())
        bnk += section('DATA', self.data)
        bnk += section('HIRC', self.hierarchy('Play_' + name + suffix))
        bnk += section('STID', self.stringid('Song_' + name + suffix))

        return self.FILE_ID, bnk
