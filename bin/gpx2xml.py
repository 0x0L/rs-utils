#!/usr/bin/env python

"""
Extract XML data from Guitar Pro GPX files

Usage:
    gpx2xml.py FILE
"""

import struct


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
    gp_xml = uncompressed[
        uncompressed.find('<GPIF>') - 39:uncompressed.find('</GPIF>') + 7]

    return gp_xml

if __name__ == '__main__':
    from docopt import docopt
    args = docopt(__doc__)

    print read_gp(args['FILE'])
