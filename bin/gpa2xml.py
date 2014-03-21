#!/usr/bin/env python

"""
Convert Go PlayAlong to Rocksmith

Usage:
    gpa2xml.py FILE
"""

from time import strftime
import re

from gpx2xml import has_prop, get_prop, load_goplayalong
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
            '@name': 'default',
            '@solo': 0
        }]

        self.phraseIterations = [{
            '@time': 0.000,
            '@phraseId': 0,
            '@variation': ''
        }]

    def json(self):
        score = self.song.Score

        internalName = filter(str.isalnum, score.Artist)
        internalName += filter(str.isalnum, score.Title)
        part = 1  # TODO

        centOffset = 0  # No cent offset in GPX ?

        songLength = self.ebeats[-1]['@time'] if len(self.ebeats) > 0 else 0
        offset = self.timefun.offset
        averageTempo = (len(self.ebeats) - 1) / (songLength + offset) * 60
        averageTempo = int(averageTempo * 1000) / 1000.0

        STANDARD_TUNING = [40, 45, 50, 55, 59, 64]
        tuning = get_prop(self.track, 'Tuning', STANDARD_TUNING)
        standardTuning = int(tuning == STANDARD_TUNING)

        tuning = [a - b for a, b in zip(tuning, STANDARD_TUNING)]
        tuning = {'@string' + str(k): tuning[k] for k in range(6)}

        def xany(s, prop):
            return int(any(n[prop] for n in s))

        arrangementProperties = {
            '@barreChords': 0,
            '@bassPick': 0,
            '@bends': xany(self.notes, '@bend'),
            '@bonusArr': 0,
            '@doubleStops': 0,
            '@dropDPower': 0,
            '@fifthsAndOctaves': 0,
            '@fingerPicking': 0,
            '@fretHandMutes': xany(self.chords, '@fretHandMute'),
            '@harmonics': xany(self.notes, '@harmonic'),
            '@hopo': xany(self.chords + self.notes, '@hopo'),
            '@nonStandardChords': 0,
            '@openChords': 0,
            '@palmMutes': xany(self.chords + self.notes, '@palmMute'),
            '@pathBass': 0,
            '@pathLead': 1,
            '@pathRhythm': 0,
            '@pickDirection': 0,
            '@pinchHarmonics': xany(self.notes, '@harmonicPinch'),
            '@powerChords': 0,
            '@represent': 1,
            '@slapPop': xany(self.notes, '@pluck') | xany(self.notes, '@slap'),
            '@slides': int(any(n['@slideTo'] != -1 for n in self.notes)),
            '@standardTuning': standardTuning,
            '@sustain': xany(self.notes, '@sustain'),
            '@syncopation': 0,
            '@tapping': xany(self.notes, '@tap'),
            '@tremolo': xany(self.notes, '@tremolo'),
            '@twoFingerPicking': 0,
            '@unpitchedSlides': int(any(n['@slideUnpitchTo'] != -1 for n in self.notes)),
            '@vibrato': xany(self.notes, '@vibrato')
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
            'tuning': tuning,
            'wavefilepath': ''
        }

    def new_chord(self, beat, notes):
        chordTemplate = {
            '@chordName': '',  # TODO
            '@displayName': '',  # TODO
            '@finger0': -1,
            '@finger1': -1,
            '@finger2': -1,
            '@finger3': -1,
            '@finger4': -1,
            '@finger5': -1,
            '@fret0': -1,
            '@fret1': -1,
            '@fret2': -1,
            '@fret3': -1,
            '@fret4': -1,
            '@fret5': -1
        }
        for n in notes:
            string, fret = n['@string'], n['@fret']
            chordTemplate['@finger' + str(string)] = -1  # TODO
            chordTemplate['@fret' + str(string)] = fret

        if 'Arpeggio' in beat:
            chordTemplate['@displayName'] += '_arp'

        if not chordTemplate in self.chordTemplates:
            chordId = len(self.chordTemplates)
            self.chordTemplates.append(chordTemplate)
        else:
            chordId = self.chordTemplates.index(chordTemplate)

        # TODO check any or all ?
        return {
            '@accent': int(any(n['@accent'] for n in notes)),
            '@chordId': chordId,
            '@fretHandMute': int(any(n['@mute'] for n in notes)),
            '@highDensity': 0,
            '@hopo': int(any(n['@hopo'] for n in notes)),
            '@ignore': int(any(n['@ignore'] for n in notes)),
            '@linkNext': int(any(n['@linkNext'] for n in notes)),
            '@palmMute': int(any(n['@palmMute'] for n in notes)),
            '@strum': get_prop(beat, 'Direction', 'Down').lower(),
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
            self.chords.append(self.new_chord(beat, ns))
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
