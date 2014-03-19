#!/usr/bin/env python

"""
Convert Go PlayAlong to Rocksmith

Usage:
    gpa2xml.py FILE
"""

from time import strftime
from numpy import interp
import os
import re

from gpx2xml import read_gp
import xmlhelpers

offset = -10.0

DURATIONS = {
    'Whole': -2,
    'Half': -1,
    'Quarter': 0,
    'Eighth': 1,
    '16th': 2,
    '32nd': 3,
    '64th': 4
}


class Bar2Time:
    def __init__(self, mapping, offset=-10.0):
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


def sorted_name(text):
    x = re.sub(r'(a|an|and|the)(\s+)', '', text, flags=re.IGNORECASE)
    return x.capitalize()


def load_gpx(filename):
    def process(x):
        """Transforms attrib like '1 2 3' in [1, 2, 3]"""
        y = xmlhelpers.DefaultSanitizer(x)
        if y == x:
            t = x.split(' ')
            if len(t) > 0 and t[0] != xmlhelpers.DefaultSanitizer(t[0]):
                return map(xmlhelpers.DefaultSanitizer, t)

        return y

    gp = xmlhelpers.xml2json(read_gp(filename), processor=process)

    # squashing arrays for convience
    for k in ['Track', 'MasterBar', 'Bar', 'Voice', 'Beat', 'Note', 'Rhythm']:
        gp[k + 's'] = gp[k + 's'][k]

    for n in gp.Notes:
        n.Properties = n.Properties.Property

    return gp


def load_goplayalong(filename):
    gpa = xmlhelpers.xml2json(open(filename).read())

    sync = [y.split(';') for y in gpa.sync.split('#')[1:]]
    sync = {float(b) + float(db): float(t) / 1000.0 for t, b, db, _ in sync}
    sync = Bar2Time(sync)

    d = os.path.dirname(os.path.abspath(filename))
    gpx = load_gpx(d + os.path.sep + gpa.scoreUrl)

    return gpx, sync


# tuning = {
#     '@string0': 0,
#     '@string1': 0,
#     '@string2': 0,
#     '@string3': 0,
#     '@string4': 0,
#     '@string5': 0
# }

# arrangementProperties = {
#     '@represent': 1,
#     '@bonusArr': 0,
#     '@standardTuning': 1,
#     '@nonStandardChords': 0,
#     '@barreChords': 0,
#     '@powerChords': 1,
#     '@dropDPower': 0,
#     '@openChords': 1,
#     '@fingerPicking': 0,
#     '@pickDirection': 0,
#     '@doubleStops': 1,
#     '@palmMutes': 1,
#     '@harmonics': 1,
#     '@pinchHarmonics': 0,
#     '@hopo': 1,
#     '@tremolo': 0,
#     '@slides': 1,
#     '@unpitchedSlides': 0,
#     '@bends': 1,
#     '@tapping': 0,
#     '@vibrato': 0,
#     '@fretHandMutes': 0,
#     '@slapPop': 0,
#     '@twoFingerPicking': 0,
#     '@fifthsAndOctaves': 0,
#     '@syncopation': 0,
#     '@bassPick': 0,
#     '@sustain': 1,
#     '@pathLead': 0,
#     '@pathRhythm': 0,
#     '@pathBass': 0
# }

# phrases = [{
#     '@disparity': 0,
#     '@ignore': 0,
#     '@maxDifficulty': 0,
#     '@name': 'COUNT',
#     '@solo': 0
# }]

# phraseIterations = [{
#     '@time': 0.000,
#     '@phraseId': 0,
#     '@variation': ''
# }]

# chordTemplates = [{
#     '@chordName': 'F#5',
#     '@displayName': 'F#5',
#     '@finger0': -1,
#     '@finger1': -1,
#     '@finger2': 1,
#     '@finger3': 1,
#     '@finger4': -1,
#     '@finger5': -1,
#     '@fret0': -1,
#     '@fret1': -1,
#     '@fret2': 11,
#     '@fret3': 11,
#     '@fret4': -1,
#     '@fret5': -1
# }]

# ebeats = [{
#     '@time': 0.000,
#     '@measure': 1
# }]

# sections = [{
#     '@name': 'chorus',
#     '@number': 1,
#     '@startTime': 12.501
# }]

# events = [{
#     '@time': 10.000,
#     '@code': 'B0'
# }]

# notes = [{
#     '@time': 5.235,
#     '@linkNext': 0,
#     '@accent': 0,
#     '@bend': 0,
#     '@fret': 4,
#     '@hammerOn': 0,
#     '@harmonic': 0,
#     '@hopo': 0,
#     '@ignore': 0,
#     '@leftHand': -1,
#     '@mute': 0,
#     '@palmMute': 0,
#     '@pluck': -1,
#     '@pullOff': 0,
#     '@slap': -1,
#     '@slideTo': -1,
#     '@string': 1,
#     '@sustain': 0.392,
#     '@tremolo': 0,
#     '@harmonicPinch': 0,
#     '@pickDirection': 0,
#     '@rightHand': -1,
#     '@slideUnpitchTo': -1,
#     '@tap': 0,
#     '@vibrato': 0,
#     'bendValues': [{
#         '@time': 279.748,
#         '@step': 1.000
#     }]
# }]

# chordNotes = [{
#     '@time': 5.235,
#     '@linkNext': 0,
#     '@accent': 0,
#     '@bend': 0,
#     '@fret': 4,
#     '@hammerOn': 0,
#     '@harmonic': 0,
#     '@hopo': 0,
#     '@ignore': 0,
#     '@leftHand': -1,
#     '@mute': 0,
#     '@palmMute': 0,
#     '@pluck': -1,
#     '@pullOff': 0,
#     '@slap': -1,
#     '@slideTo': -1,
#     '@string': 1,
#     '@sustain': 0.392,
#     '@tremolo': 0,
#     '@harmonicPinch': 0,
#     '@pickDirection': 0,
#     '@rightHand': -1,
#     '@slideUnpitchTo': -1,
#     '@tap': 0,
#     '@vibrato': 0,
# }]

# chords = [{
#     '@time': 5.672,
#     '@linkNext': 0,
#     '@accent': 0,
#     '@chordId': 4,
#     '@fretHandMute': 0,
#     '@highDensity': 0,
#     '@ignore': 0,
#     '@palmMute': 0,
#     '@hopo': 0,
#     '@strum': 'down',
#     'chordNotes': InlineContent(chordNotes)
# }]

# anchors = [{
#     '@time': 5.235,
#     '@fret': 4,
#     '@width': 4.000
# }]

# handShapes = [{
#     '@chordId': 4,
#     '@endTime': 5.728,
#     '@startTime': 5.672
# }]

# tones = [{
#     '@id': 0,
#     '@time': 45.234
# }]

class SngBuilder:
    def __init__(self, song, track, timefun):
        self.song = song
        self.track = track
        self.timefun = timefun

        self.signature = 4.0  # 4/4 default signature

        self.phrases = []
        self.phraseIterations = []
        self.chordTemplates = []
        self.notes = []
        self.chords = []
        self.anchors = []
        self.handShapes = []
        self.ebeats = []
        self.events = []
        self.sections = []
        self.tones = []

        self.measure = 0.0
        self.bar_idx = 0

    def fraction_of_bar(self, duration):
        return 1.0 / (2**DURATIONS[duration]) / self.signature

    def run(self):
        self.measure = 0.0
        self.bar_idx = 0

        while self.bar_idx < len(self.song.MasterBars):
            bar_settings = self.song.MasterBars[self.bar_idx]
            bar = self.song.Bars[bar_settings.Bars[self.track['@id']]]

            self.measure_fraction = 0.0
            for b in self.song.Voices[bar.Voices[0]].Beats:
                time = self.timefun(self.measure + self.measure_fraction)
                print time

                beat = self.song.Beats[b]
                rhythm = self.song.Rhythms[beat.Rhythm['@ref']]
                f = self.fraction_of_bar(rhythm.NoteValue)

                self.measure_fraction += f

            self.bar_idx += 1
            self.measure += 1.0

    def get(self):
        song = self.song
        internalName = 'toto'
        songLength = self.ebeats[-1]['@time'] if len(self.ebeats) > 0 else 0

        return {
            '@version': 8,
            'title': song.Score.Title,
            'arrangement': self.track.Name,
            'wavefilepath': '',
            'part': 1,
            'offset': offset,
            'centOffset': 0, #centOffset,
            'songLength': songLength,
            'internalName': internalName,
            'songNameSort': sorted_name(self.track.Name),
            'startBeat': 0, #startBeat,
            'averageTempo': 90, #averageTempo,
            'tuning': 0, #tuning,
            'capo': 0, #capo,
            'artistName': song.Score.Artist,
            'artistNameSort': sorted_name(song.Score.Artist),
            'albumName': song.Score.Album,
            'albumNameSort': sorted_name(song.Score.Album),
            'albumYear': song.Score.Copyright,
            'albumArt': internalName,
            'crowdSpeed': 1,
            'arrangementProperties': 0, #self.arrangementProperties,
            'lastConversionDateTime': strftime('%F %T'),
            'phrases': self.phrases,
            'phraseIterations': self.phraseIterations,
            'newLinkedDiffs': [],
            'linkedDiffs': [],
            'phraseProperties': [],
            'chordTemplates': self.chordTemplates,
            'fretHandMuteTemplates': [],
            'ebeats': self.ebeats,
            'events': self.events,
            'transcriptionTrack': {
                '@difficulty': -1,
                'notes': [],
                'chords': [],
                'anchors': [],
                'handShapes': []
            },
            'levels': [{
                '@difficulty': -1,
                'notes': self.notes,
                'chords': self.chords,
                'anchors': self.anchors,
                'handShapes': self.handShapes,
                'fretHandMutes': []
            }],
            'tones': self.tones
        }


def runHelper(filename):
    gp, sync = load_goplayalong(filename)

    sng = SngBuilder(gp, gp.Tracks[0], sync)
    sng.run()

    return xmlhelpers.json2xml('song', sng.get())


if __name__ == '__main__':
    from docopt import docopt
    import xml.dom.minidom

    args = docopt(__doc__)

    x = runHelper(args['FILE'])
    print xml.dom.minidom.parseString(x).toprettyxml()
