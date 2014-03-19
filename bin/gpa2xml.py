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
from xmlhelpers import json2xml, xml2json, DefaultConverter, InlineContent

OFFSET = -10.0

DURATIONS = {
    'Whole': -2,
    'Half': -1,
    'Quarter': 0,
    'Eighth': 1,
    '16th': 2,
    '32nd': 3,
    '64th': 4
}

STANDARD_TUNING = [40, 45, 50, 55, 59, 64]

PROPERTIES = {
    'Tuning': 'Pitches',
    'CapoFret': 'Fret',
    'Slide': 'Flags'
}


def has_prop(o, prop_name):
    for p in o.Properties.Property:
        if p['@name'] == prop_name:
            return True
    return False


def get_prop(o, prop_name, default=None):
    for p in o.Properties.Property:
        if p['@name'] == prop_name:
            if prop_name in PROPERTIES:
                return p[PROPERTIES[prop_name]]
            else:
                return p[prop_name]

    return default


def get_tuning(track):
    tuning = get_prop(track, 'Tuning', STANDARD_TUNING)
    offset = [a - b for a, b in zip(tuning, STANDARD_TUNING)]
    return {'@string' + str(k): offset[k] for k in range(6)}


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


def text_for_sort(text):
    x = re.sub(r'(a|an|and|the)(\s+)', '', text, flags=re.IGNORECASE)
    return x.capitalize()


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
    sync = Bar2Time(sync, OFFSET)

    d = os.path.dirname(os.path.abspath(filename))
    gpx = load_gpx(d + os.path.sep + gpa.scoreUrl)

    return gpx, sync


# TODO

# Arrangement properties

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

# events = [{
#     '@time': 10.000,
#     '@code': 'B0'
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

    def clear(self):
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

        self.measure = 0
        self.bar_idx = 0
        self.time = 0.0
        self.beats_per_bar = 0.0
        self.measure_offset = 0.0

    def json(self):
        score = self.song.Score

        internalName = filter(str.isalnum, score.Artist)
        internalName += filter(str.isalnum, score.Title)
        part = 1  # TODO

        centOffset = 0  # No cent offset in GPX ?

        songLength = self.ebeats[-1]['@time'] if len(self.ebeats) > 0 else 0
        offset = self.timefun.offset
        averageTempo = len(self.ebeats) / (songLength + offset) * 60
        averageTempo = int(averageTempo * 1000) / 1000.0

        arrangementProperties = {
            '@represent': 1,
            '@bonusArr': 0,
            '@standardTuning': 1,
            '@nonStandardChords': 0,
            '@barreChords': 0,
            '@powerChords': 1,
            '@dropDPower': 0,
            '@openChords': 1,
            '@fingerPicking': 0,
            '@pickDirection': 0,
            '@doubleStops': 1,
            '@palmMutes': 1,
            '@harmonics': 1,
            '@pinchHarmonics': 0,
            '@hopo': 1,
            '@tremolo': 0,
            '@slides': 1,
            '@unpitchedSlides': 0,
            '@bends': 1,
            '@tapping': 0,
            '@vibrato': 0,
            '@fretHandMutes': 0,
            '@slapPop': 0,
            '@twoFingerPicking': 0,
            '@fifthsAndOctaves': 0,
            '@syncopation': 0,
            '@bassPick': 0,
            '@sustain': 1,
            '@pathLead': 1,
            '@pathRhythm': 0,
            '@pathBass': 0
        }

        return {
            '@version': 8,
            'title': score.Title,
            'arrangement': self.track.Name,
            'wavefilepath': '',
            'part': 1,
            'offset': offset,
            'centOffset': centOffset,
            'songLength': songLength,
            'internalName': internalName,
            'songNameSort': text_for_sort(self.track.Name),
            'startBeat': 0.000,
            'averageTempo': averageTempo,
            'tuning': get_tuning(self.track),
            'capo': get_prop(self.track, 'CapoFret', 0),
            'artistName': score.Artist,
            'artistNameSort': text_for_sort(score.Artist),
            'albumName': score.Album,
            'albumNameSort': text_for_sort(score.Album),
            'albumYear': score.Copyright,
            'albumArt': internalName,
            'crowdSpeed': 1,
            'arrangementProperties': arrangementProperties,
            'lastConversionDateTime': strftime('%F %T'),
            'phrases': self.phrases,
            'phraseIterations': self.phraseIterations,
            'newLinkedDiffs': [],
            'linkedDiffs': [],
            'phraseProperties': [],
            'chordTemplates': self.chordTemplates,
            'fretHandMuteTemplates': [],
            'ebeats': self.ebeats,
            'sections': self.sections,
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

    def new_chord(self, notes):
        return {
            '@time': self.time,
            # '@linkNext': 0,
            # '@accent': 0,
            # '@chordId': 4,
            # '@fretHandMute': 0,
            # '@highDensity': 0,
            # '@ignore': 0,
            # '@palmMute': 0,
            # '@hopo': 0,
            # '@strum': 'down',
            'chordNotes': InlineContent(notes)
        }

    def new_notes(self, notes):
        ns = []
        for n in notes:
            note = self.song.Notes[n]
            # print note
            # if has_prop(note, 'Bended'):
            #     print note.Properties.Property
            ns.append({
                '@time': self.time,
                # '@linkNext': 0,
                # '@accent': 0,
                # '@bend': 0,
                '@fret': get_prop(note, 'Fret'),
                # '@hammerOn': 0,
                # '@harmonic': 0,
                # '@hopo': 0,
                # '@ignore': 0,
                # '@leftHand': -1,
                # '@mute': 0,
                # '@palmMute': 0,
                # '@pluck': -1,
                # '@pullOff': 0,
                # '@slap': -1,
                # '@slideTo': -1,
                '@string': get_prop(note, 'String'),
                # '@sustain': 0.0,
                # '@tremolo': 0,
                # '@harmonicPinch': 0,
                # '@pickDirection': 0,
                # '@rightHand': -1,
                # '@slideUnpitchTo': -1,
                # '@tap': 0,
                # '@vibrato': 0,
            })

        if len(ns) > 1:
            self.chords.append(self.new_chord(ns))
        else:
            self.notes += ns

    def new_beat(self, beat):
        # TODO tone change
        if 'Notes' in beat:
            if type(beat.Notes) is not list:
                beat.Notes = [beat.Notes]

            self.new_notes(beat.Notes)

        rhythm = self.song.Rhythms[beat.Rhythm['@ref']]

        inc = 1.0 / (2**DURATIONS[rhythm.NoteValue]) / self.beats_per_bar
        self.measure_offset += inc
        self.time = self.timefun(self.measure + self.measure_offset)

    def new_bar(self, bar, bar_settings):
        # print bar_settings
        num, den = map(int, bar_settings.Time.split('/'))
        self.beats_per_bar = 4.0 * num / den

        # TODO repeats

        if 'Section' in bar_settings:
            self.sections.append({
                '@name': bar_settings.Section.Text,
                '@number': len(self.sections),
                '@startTime': self.timefun(self.measure)
            })

        for i in range(int(self.beats_per_bar)):
            self.ebeats.append({
                '@time': self.timefun(self.measure + i / self.beats_per_bar),
                '@measure': self.measure + 1 if i == 0 else -1
            })

        self.measure_offset = 0.0
        for b in self.song.Voices[bar.Voices[0]].Beats:
            beat = self.song.Beats[b]
            self.new_beat(beat)

        # TODO logic for repeats

    def run(self):
        self.clear()
        while self.bar_idx < len(self.song.MasterBars):
            bar_settings = self.song.MasterBars[self.bar_idx]
            bar = self.song.Bars[bar_settings.Bars[self.track['@id']]]

            self.new_bar(bar, bar_settings)

            self.bar_idx += 1
            self.measure += 1

        return self.json()


if __name__ == '__main__':
    from docopt import docopt
    from xml.dom.minidom import parseString

    args = docopt(__doc__)

    gp, sync = load_goplayalong(args['FILE'])
    sng = SngBuilder(gp, gp.Tracks[0], sync)

    x = json2xml('song', sng.run())
    print parseString(x).toprettyxml()
