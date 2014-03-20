#!/usr/bin/env python

"""
Convert Go PlayAlong to Rocksmith

Usage:
    gpa2xml.py FILE
"""

from time import strftime
import re

from gpx2xml import has_prop, get_prop, load_goplayalong, Bar2Time
from xmlhelpers import json2xml, InlineContent


DURATIONS = {
    'Long': -4,
    'DoubleWhole': -3,
    'Whole': -2,
    'Half': -1,
    'Quarter': 0,
    'Eighth': 1,
    '16th': 2,
    '32nd': 3,
    '64th': 4,
    '128th': 5,
    '256th': 6,
}


def text_for_sort(text):
    x = re.sub(r'(a|an|the)(\s+)', '', text, flags=re.IGNORECASE)
    return x.capitalize()


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

    def get_tuning(self):
        STANDARD_TUNING = [40, 45, 50, 55, 59, 64]
        tuning = get_prop(self.track, 'Tuning', STANDARD_TUNING)
        offset = [a - b for a, b in zip(tuning, STANDARD_TUNING)]
        return {'@string' + str(k): offset[k] for k in range(6)}

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
            '@barreChords': 0,
            '@bassPick': 0,
            '@bends': int(any(n['@bend'] for n in self.notes)),
            '@bonusArr': 0,
            '@doubleStops': 1,
            '@dropDPower': 0,
            '@fifthsAndOctaves': 0,
            '@fingerPicking': 0,
            '@fretHandMutes': int(any(n['@fretHandMute'] for n in self.chords)),
            '@harmonics': int(any(n['@harmonic'] for n in self.notes)),
            '@hopo': int(any(n['@hopo'] for n in self.chords + self.notes)),
            '@nonStandardChords': 0,
            '@openChords': 1,
            '@palmMutes': int(any(n['@palmMute'] for n in self.chords + self.notes)),
            '@pathBass': 0,
            '@pathLead': 1,
            '@pathRhythm': 0,
            '@pickDirection': 0,
            '@pinchHarmonics': int(any(n['@harmonicPinch'] for n in self.notes)),
            '@powerChords': 1,
            '@represent': 1,
            '@slapPop': int(any(n['@slap'] or n['@pluck'] for n in self.notes)),
            '@slides': int(any(n['@slideTo'] != -1 for n in self.notes)),
            '@standardTuning': 1,
            '@sustain': 1,
            '@syncopation': 0,
            '@tapping': int(any(n['@tap'] for n in self.notes)),
            '@tremolo': int(any(n['@tremolo'] for n in self.notes)),
            '@twoFingerPicking': 0,
            '@unpitchedSlides': int(any(n['@slideUnpitchTo'] != -1 for n in self.notes)),
            '@vibrato': int(any(n['@vibrato'] for n in self.notes))
        }

        return {
            '@version': 8,
            'albumArt': internalName,
            'albumName': score.Album,
            'albumNameSort': text_for_sort(score.Album),
            'albumYear': score.Copyright,
            'arrangement': self.track.Name,
            'arrangementProperties': arrangementProperties,
            'artistName': score.Artist,
            'artistNameSort': text_for_sort(score.Artist),
            'averageTempo': averageTempo,
            'capo': get_prop(self.track, 'CapoFret', 0),
            'centOffset': centOffset,
            'chordTemplates': self.chordTemplates,
            'crowdSpeed': 1,
            'ebeats': self.ebeats,
            'events': self.events,
            'fretHandMuteTemplates': [],
            'internalName': internalName,
            'lastConversionDateTime': strftime('%F %T'),
            'levels': [{
                '@difficulty': 0,
                'anchors': self.anchors,
                'chords': self.chords,
                'fretHandMutes': [],
                'handShapes': self.handShapes,
                'notes': self.notes
            }],
            'linkedDiffs': [],
            'newLinkedDiffs': [],
            'offset': offset,
            'part': part,
            'phraseIterations': self.phraseIterations,
            'phraseProperties': [],
            'phrases': self.phrases,
            'sections': self.sections,
            'songLength': songLength,
            'songNameSort': text_for_sort(self.track.Name),
            'startBeat': 0.000,
            'title': score.Title,
            'tone_A': '',
            'tone_B': '',
            'tone_C': '',
            'tone_D': '',
            'tone_Base': '',
            'tone_Multiplayer': '',
            'tones': self.tones,
            'transcriptionTrack': {
                '@difficulty': -1,
                'anchors': [],
                'chords': [],
                'handShapes': [],
                'notes': []
            },
            'tuning': self.get_tuning(),
            'wavefilepath': ''
        }

    def new_chord(self, brush, notes):
        # TODO check any or all ?
        return {
            '@accent': int(any(n['@accent'] for n in notes)),
            '@chordId': 0,
            '@fretHandMute': int(any(n['@mute'] for n in notes)),
            '@highDensity': 0,
            '@hopo': int(any(n['@hopo'] for n in notes)),
            '@ignore': int(any(n['@ignore'] for n in notes)),
            '@linkNext': int(any(n['@linkNext'] for n in notes)),
            '@palmMute': int(any(n['@palmMute'] for n in notes)),
            '@strum': 'down',  # TODO from brush
            '@time': self.time,
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

            # TODO slide, bend, hopo
            # sustain
            # left/rightHand ?

            harmonic = get_prop(note, 'HarmonicType')
            brush = get_prop(beat, 'Brush')

            ns.append({
                '@accent': int('Accent' in note),
                '@bend': 0,
                '@fret': get_prop(note, 'Fret'),
                '@hammerOn': 0,
                '@harmonic': int(harmonic == 'Artificial'),
                '@harmonicPinch': int(harmonic == 'Pinch'),
                '@hopo': 0,
                '@ignore': 0,
                '@leftHand': -1,
                '@linkNext': int('Tie' in note and note.Tie['@origin']),
                '@mute': int(has_prop(note, 'Muted')),
                '@palmMute': int(has_prop(note, 'PalmMuted')),
                '@pickDirection': 0,
                '@pluck': int(has_prop(beat, 'Popped')),
                '@pullOff': 0,
                '@rightHand': -1,
                '@slap': int(has_prop(beat, 'Slapped')),
                '@slideTo': -1,
                '@slideUnpitchTo': -1,
                '@string': get_prop(note, 'String'),
                '@sustain': 0.0,
                '@tap': int(has_prop(note, 'Tapped')),
                '@time': self.time,
                '@tremolo': int('Tremolo' in beat),
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

            self.bar_idx += 1  # no repeats
            self.measure += 1  # counting repeats

        return self.json()


if __name__ == '__main__':
    from docopt import docopt
    from xml.dom.minidom import parseString

    args = docopt(__doc__)

    gp, sync = load_goplayalong(args['FILE'])
    sng = SngBuilder(gp, gp.Tracks[0], sync)

    x = json2xml('song', sng.run())
    print parseString(x).toprettyxml()
