#!/usr/bin/env python

"""
Extract XML data from Guitar Pro GPX files

Usage:
    gpx2xml.py FILE
"""

import struct
from numpy import interp
from xmlhelpers import xml2json, DefaultConverter
import os


def clean_prop(o):
    if not 'Property' in o.Properties:
        o.Properties['Property'] = []
    if not issubclass(type(o.Properties.Property), list):
        o.Properties.Property = [o.Properties.Property]


def has_prop(o, prop_name):
    clean_prop(o)
    for p in o.Properties.Property:
        if p['@name'] == prop_name:
            return True
    return False


def get_prop(o, prop_name, default=None):
    clean_prop(o)
    for p in o.Properties.Property:
        if p['@name'] == prop_name:
            u = p.keys()
            u.remove('@name')
            return p[u[0]]
    return default


class Bar2Time:
    def __init__(self, mapping, offset):
        self.offset = offset
        self._X = []
        self._Y = []
        for x, y in iter(sorted(mapping.iteritems())):
            self._X.append(x)
            self._Y.append(y)

    @staticmethod
    def __extrapolate__(z, xs, ys):
        x1, x2 = xs
        y1, y2 = ys
        alpha = (y2 - y1) / (x2 - x1)
        return y1 + alpha * (z - x1)

    def __call__(self, z):
        if z < self._X[0]:
            t = Bar2Time.__extrapolate__(z, self._X[:2], self._Y[:2])
        elif z > self._X[-1]:
            t = Bar2Time.__extrapolate__(z, self._X[-2:], self._Y[-2:])
        else:
            t = interp(z, self._X, self._Y)

        return int(1000 * (t - self.offset)) / 1000.0


def load_gpx(filename):
    def process(x):
        """Transform attributes such as '1 2 3' in [1, 2, 3]"""
        y = DefaultConverter(x)
        if y == x:
            t = x.split(' ')
            if len(t) > 0 and t[0] != DefaultConverter(t[0]):
                return map(DefaultConverter, t)
        return y

    gp = xml2json(read_gp(filename), processor=process)

    # squashing arrays for convience
    for k in ['Track', 'MasterBar', 'Bar', 'Voice', 'Beat', 'Note', 'Rhythm']:
        gp[k + 's'] = gp[k + 's'][k]

    return gp


def load_goplayalong(filename):
    gpa = xml2json(open(filename).read())

    sync = [y.split(';') for y in gpa.sync.split('#')[1:]]
    sync = {float(b) + float(db): float(t) / 1000.0 for t, b, db, _ in sync}
    sync = Bar2Time(sync, -10.0)

    d = os.path.dirname(os.path.abspath(filename))
    gpx = load_gpx(d + os.path.sep + gpa.scoreUrl)

    return gpx, sync


class BitReader:

    def __init__(self, stream):
        self.stream = stream
        self.position = 8

    def read_bit(self):
        if self.position >= 8:
            x = self.stream.read(1)
            if x == '':
                x = '\x00'
            self.current_byte = ord(x)
            self.position = 0

        value = (self.current_byte >> (8 - self.position - 1)) & 0x01
        self.position += 1
        return value

    def read_bits(self, count):
        result = 0
        for i in range(count):
            result = result | (self.read_bit() << (count - i - 1))
        return result

    def read_byte(self):
        return self.read_bits(8)

    def read_bits_reversed(self, count):
        result = 0
        for i in range(count):
            result = result | (self.read_bit() << i)
        return result


def filesystem(data):
    from itertools import takewhile

    SECTOR_SIZE = 0x1000

    fs = {}
    data = data[4:]  # skip header BCFS

    def getint(pos):
        return struct.unpack('<L', data[pos:pos + 4])[0]

    offset = 0
    while offset + SECTOR_SIZE + 3 < len(data):
        if getint(offset) == 2:
            content = ''
            name = ''.join(takewhile(lambda x: ord(x) != 0, data[offset + 4:]))
            size = getint(offset + 0x8c)

            blocks_offset = offset + 0x94

            block_count = 0
            block_id = getint(blocks_offset + 4 * block_count)
            while block_id != 0:
                offset = block_id * SECTOR_SIZE
                content += data[offset:offset + SECTOR_SIZE]

                block_count += 1
                block_id = getint(blocks_offset + 4 * block_count)

            fs[name] = content[:size]

        offset += SECTOR_SIZE

    return fs


def read_gp(filename):
    data = open(filename, 'rb')

    header = data.read(4)
    assert header == 'BCFZ'

    expected_length = struct.unpack('<L', data.read(4))[0]

    io = BitReader(data)
    result = []

    while len(result) < expected_length:
        flag = io.read_bit()
        if flag == 1:
            word_size = io.read_bits(4)
            offset = io.read_bits_reversed(word_size)
            size = io.read_bits_reversed(word_size)
            source_position = len(result) - offset
            to_read = min([offset, size])
            result += result[source_position:source_position + to_read]
        else:
            size = io.read_bits_reversed(2)
            for i in range(size):
                result.append(io.read_byte())

    uncompressed = ''.join(map(chr, result))

    fs = filesystem(uncompressed)
    return fs['score.gpif']


if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    print read_gp(args['FILE'])
