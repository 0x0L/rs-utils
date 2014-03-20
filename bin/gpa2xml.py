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

import gpx2xml
from xmlhelpers import json2xml, xml2json, DefaultConverter, InlineContent


DURATIONS = {
    'Whole': -2,
    'Half': -1,
    'Quarter': 0,
    'Eighth': 1,
    '16th': 2,
    '32nd': 3,
    '64th': 4
}


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


def get_tuning(track):
    STANDARD_TUNING = [40, 45, 50, 55, 59, 64]
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

    gp = xml2json(gpx2xml.read_gp(filename), processor=process)

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


# TODO


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
        self.time = self.timefun(0)
        self.beats_per_bar = 0.0
        self.measure_offset = 0.0

        self.phrases = [{
            '@disparity': 0,
            '@ignore': 0,
            '@maxDifficulty': 0,
            '@name': 'COUNT',
            '@solo': 0
        }]

        self.phraseIterations = [{
            '@time': 0.000,
            '@phraseId': 0,
            '@variation': ''
        }]

        self.chordTemplates = [{
            '@chordName': 'F#5',
            '@displayName': 'F#5',
            '@finger0': -1,
            '@finger1': -1,
            '@finger2': 1,
            '@finger3': 1,
            '@finger4': -1,
            '@finger5': -1,
            '@fret0': -1,
            '@fret1': -1,
            '@fret2': 11,
            '@fret3': 11,
            '@fret4': -1,
            '@fret5': -1
        }]

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
                '@difficulty': 0,
                'notes': self.notes,
                'chords': self.chords,
                'anchors': self.anchors,
                'handShapes': self.handShapes,
                'fretHandMutes': []
            }],
            'tones': self.tones,
            'tone_A': '',
            'tone_B': '',
            'tone_C': '',
            'tone_D': '',
            'tone_Base': '',
            'tone_Multiplayer': ''
        }

    def new_chord(self, brush, notes):
        return {
            '@time': self.time,
            '@linkNext': 0,
            '@accent': 0,
            '@chordId': 0,
            '@fretHandMute': 0,
            '@highDensity': 0,
            '@ignore': 0,
            '@palmMute': 0,
            '@hopo': 0,
            '@strum': 'down',
            'chordNotes': InlineContent(notes)
        }

    def new_notes(self, beat, notes):
        ns = []
        for n in notes:
            note = self.song.Notes[n]
            # print note

            # if has_prop(note, 'Slide'):
                # print note.Properties.Property
                # print get_prop(note, 'Slide')

            # if has_prop(note, 'Bended'):
            #     print note.Properties.Property

            harmonic = get_prop(note, 'HarmonicType')
            brush = get_prop(beat, 'Brush')

            ns.append({
                '@time': self.time,
                '@linkNext': int('Tie' in note and note.Tie['@origin']),
                '@accent': int('Accent' in note),
                '@bend': 0,
                '@fret': get_prop(note, 'Fret'),
                '@hammerOn': 0,
                '@harmonic': int(harmonic == 'Artificial'),
                '@hopo': 0,
                '@ignore': 0,
                '@leftHand': -1,
                '@mute': int(has_prop(note, 'Muted')),
                '@palmMute': int(has_prop(note, 'PalmMuted')),
                '@pluck': int(has_prop(beat, 'Popped')),
                '@pullOff': 0,
                '@slap': int(has_prop(beat, 'Slapped')),
                '@slideTo': -1,
                '@string': get_prop(note, 'String'),
                '@sustain': 0.0,
                '@tremolo': int('Tremolo' in beat),
                '@harmonicPinch': int(harmonic == 'Pinch'),
                '@pickDirection': 0,
                '@rightHand': -1,
                '@slideUnpitchTo': -1,
                '@tap': int(has_prop(note, 'Tapped')),
                '@vibrato': int('Vibrato' in note),
                'bendValues': []
            })

        if len(ns) > 1:
            self.chords.append(self.new_chord(brush, ns))
        else:
            self.notes += ns

    def new_beat(self, beat):
        rhythm = self.song.Rhythms[beat.Rhythm['@ref']]
        inc = 1.0 / (2**DURATIONS[rhythm.NoteValue]) / self.beats_per_bar

        if 'GraceNotes' in beat and beat.GraceNotes == 'BeforeBeat':
            self.measure_offset -= inc
            self.time = self.timefun(self.measure + self.measure_offset)

        if 'FreeText' in beat:
            self.tones.append({
                '@id': 0,  # TODO
                '@time': self.time
            })

        if 'Notes' in beat:
            if type(beat.Notes) is not list:
                beat.Notes = [beat.Notes]

            self.new_notes(beat, beat.Notes)

        self.measure_offset += inc
        self.time = self.timefun(self.measure + self.measure_offset)
        if 'GraceNotes' in beat and beat.GraceNotes == 'OnBeat':
            self.measure_offset -= inc

    def new_bar(self, bar, bar_settings):
        num, den = map(int, bar_settings.Time.split('/'))
        self.beats_per_bar = 4.0 * num / den

        if 'Repeat' in bar_settings and bar_settings.Repeat['@start']:
            self.start_repeat_bar = self.bar_idx

        if 'Section' in bar_settings:
            self.sections.append({
                '@name': bar_settings.Section.Text,
                '@number': len(self.sections),  # TODO
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

        if 'Repeat' in bar_settings and bar_settings.Repeat['@end']:
            if not hasattr(self, 'repeats_count'):
                self.repeats_count = bar_settings.Repeat['@count']

            if self.repeats_count > 1:
                self.bar_idx = self.start_repeat_bar - 1
                self.repeats_count -= 1
            else:
                del self.repeats_count
                del self.start_repeat_bar

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
