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
    tuning = get_prop(track, 'Tuning')
    if not tuning:
        return [0, 0, 0, 0, 0]

    return [a - b for a, b in zip(tuning, STANDARD_TUNING)]


def get_capo(track):
    capo = get_prop(track, 'CapoFret')
    if not capo:
        return 0
    return capo


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

    # for n in gp.Notes:
    #     n.Properties = n.Properties.Property

    return gp


def load_goplayalong(filename):
    gpa = xmlhelpers.xml2json(open(filename).read())

    sync = [y.split(';') for y in gpa.sync.split('#')[1:]]
    sync = {float(b) + float(db): float(t) / 1000.0 for t, b, db, _ in sync}
    sync = Bar2Time(sync)

    d = os.path.dirname(os.path.abspath(filename))
    gpx = load_gpx(d + os.path.sep + gpa.scoreUrl)

    return gpx, sync

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

        self.measure = 0
        self.bar_idx = 0
        self.time = 0.0

    def fraction_of_bar(self, duration):
        return 1.0 / (2**DURATIONS[duration]) / self.signature

    def new_bar(self, bar_settings):
        # print bar_settings
        num, den = map(int, bar_settings.Time.split('/'))
        self.signature = 4.0 * num / den

        # TODO repeats

        if 'Section' in bar_settings:
            self.sections.append({
                '@name': bar_settings.Section.Text,
                '@number': len(self.sections),
                '@startTime': self.timefun(self.measure)
            })

        for i in range(int(self.signature) - 1):
            self.ebeats.append({
                '@time': self.timefun(self.measure + i / self.signature),
                '@measure': self.measure + 1 if i == 0 else -1
            })

    def new_beat(self, beat):
        # TODO tone change

        if 'Notes' in beat:
            if type(beat.Notes) is not list:
                beat.Notes = [beat.Notes]

            ns = []
            for n in beat.Notes:
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
            'chordNotes': xmlhelpers.InlineContent(notes)
        }

    def run(self):
        song = self.song

        self.measure = 0
        self.bar_idx = 0

        while self.bar_idx < len(song.MasterBars):
            bar_settings = song.MasterBars[self.bar_idx]
            bar = song.Bars[bar_settings.Bars[self.track['@id']]]

            self.new_bar(bar_settings)

            self.measure_fraction = 0.0
            for b in song.Voices[bar.Voices[0]].Beats:
                self.time = self.timefun(self.measure + self.measure_fraction)

                beat = song.Beats[b]
                self.new_beat(beat)

                rhythm = song.Rhythms[beat.Rhythm['@ref']]
                f = self.fraction_of_bar(rhythm.NoteValue)

                self.measure_fraction += f

            # TODO logic for repeats

            self.bar_idx += 1
            self.measure += 1

    def get(self):
        song = self.song

        internalName = filter(str.isalnum, song.Score.Artist)
        internalName += filter(str.isalnum, song.Score.Title)

        songLength = self.ebeats[-1]['@time'] if len(self.ebeats) > 0 else 0

        raw_tuning = get_tuning(self.track)
        tuning = {'@string' + str(k): raw_tuning[k] for k in range(6)}

        centOffset = 0  # No cent offset in GPX ?
        part = 1  # TODO

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
            '@pathLead': 0,
            '@pathRhythm': 0,
            '@pathBass': 0
        }

        return {
            '@version': 8,
            'title': song.Score.Title,
            'arrangement': self.track.Name,
            'wavefilepath': '',
            'part': 1,
            'offset': offset,
            'centOffset': centOffset,
            'songLength': songLength,
            'internalName': internalName,
            'songNameSort': sorted_name(self.track.Name),
            'startBeat': 0, #startBeat,
            'averageTempo': 90, #averageTempo,
            'tuning': tuning,
            'capo': get_capo(self.track),
            'artistName': song.Score.Artist,
            'artistNameSort': sorted_name(song.Score.Artist),
            'albumName': song.Score.Album,
            'albumNameSort': sorted_name(song.Score.Album),
            'albumYear': song.Score.Copyright,
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


if __name__ == '__main__':
    from docopt import docopt
    import xml.dom.minidom

    args = docopt(__doc__)

    gp, sync = load_goplayalong(args['FILE'])
    sng = SngBuilder(gp, gp.Tracks[0], sync)
    sng.run()

    x = xmlhelpers.json2xml('song', sng.get())
    print xml.dom.minidom.parseString(x).toprettyxml()
