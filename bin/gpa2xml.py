#!/usr/bin/env python

"""
Convert Go PlayAlong to Rocksmith

Usage:
    gpa2xml.py FILE
"""

from time import strftime
import re
import json

from gpx2xml import has_prop, get_prop, load_goplayalong
from xmlhelpers import json2xml, InlineContent


DURATIONS = {
    'Long': 16.0,
    'DoubleWhole': 8.0,
    'Whole': 4.0,
    'Half': 2.0,
    'Quarter': 1.0,
    'Eighth': 1.0 / 2.0,
    '16th': 1.0 / 4.0,
    '32nd': 1.0 / 8.0,
    '64th': 1.0 / 16.0,
    '128th': 1.0 / 32.0,
    '256th': 1.0 / 64.0,
}


def text_for_sort(text):
    x = re.sub(r'(a|an|the)(\s+)', '', text, flags=re.IGNORECASE)
    return x.capitalize()


CH_TEMPLATES = json.loads(open('../share/chords.database.json').read())
CH_TEMPLATES = CH_TEMPLATES['Static']['Chords']['Entries']


# TODO: make the logic clearer :)
def find_fingering(chord):
    f0 = [chord['@fret' + str(k)] for k in range(6)]
    mask = [x > -1 for x in f0]
    f = f0
    min_fret = min([x for x in f if x > -1])
    if min_fret > 0:
        f = [x - min_fret + 1 for x in f]

    w = None
    for c in CH_TEMPLATES:
        z = [x < 0 or x == y for x, y in zip(f, c['Frets'])]
        if all(z):
            w = c
            break

    if w:
        k = [-1 if not y else x for x, y in zip(c['Fingers'], mask)]
        for kk in range(6):
            chord['@finger' + str(kk)] = k[kk]
            # print chord
        # print f0, '=>', k
    # else:
    #     print '### Not found', f0


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
        self.handShapes = []
        self.ebeats = []
        self.events = []
        self.sections = []
        self.tones = []

        self.measure = 0
        self.bar_idx = 0
        self.time = self.timefun(0)
        self.quarters_per_bar = 0.0
        self.offset_in_measure = 0.0

        self.anchors = [{
            '@time': 10.000,
            '@fret': 2,
            '@width': 4.000
        }]

        # TODO: from sections, double bar and repeats
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

        # TODO: check for techniques...
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
            '@slapPop': int(any(n['@slap'] != -1 or n['@pluck'] != -1 for n in self.notes)),
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
            '@finger0': -1, '@finger1': -1, '@finger2': -1,
            '@finger3': -1, '@finger4': -1, '@finger5': -1,
            '@fret0': -1, '@fret1': -1, '@fret2': -1,
            '@fret3': -1, '@fret4': -1, '@fret5': -1
        }
        for n in notes:
            string, fret = n['@string'], n['@fret']
            chordTemplate['@fret' + str(string)] = fret

        find_fingering(chordTemplate)

        # print chordTemplate
        for n in notes:
            n['@leftHand'] = chordTemplate['@finger' + str(n['@string'])]

        if 'Arpeggio' in beat:
            chordTemplate['@displayName'] += '_arp'

        if not chordTemplate in self.chordTemplates:
            chordId = len(self.chordTemplates)
            self.chordTemplates.append(chordTemplate)
        else:
            chordId = self.chordTemplates.index(chordTemplate)

        self.handShapes.append({
            '@chordId': chordId,
            '@endTime': self.time + self.current_beat_length * 0.90,
            '@startTime': self.time
        })

        lowest_fret = [n['@fret'] for n in notes if n['@fret'] > -1]
        if lowest_fret != []:
            lowest_fret = min(lowest_fret)
            self.anchors.append({
                '@time': self.time,
                '@fret': lowest_fret,
                '@width': 4.000
            })

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

            # TODO slide, bend, hopo, sustain
            # handle fingering already there

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
                '@pluck': -1,  # int(has_prop(beat, 'Popped')),
                '@pullOff': 0,
                '@rightHand': -1,
                '@slap': -1,  # int(has_prop(beat, 'Slapped')),
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
        inc = DURATIONS[rhythm.NoteValue] / self.quarters_per_bar

        if 'PrimaryTuplet' in rhythm:
            tuplet = rhythm['PrimaryTuplet']
            inc *= tuplet['@den'] / tuplet['@num']

        if 'AugmentationDot' in rhythm:
            inc *= 1.5

        if 'GraceNotes' in beat and beat.GraceNotes == 'BeforeBeat':
            self.offset_in_measure -= inc
            self.time = self.timefun(self.measure + self.offset_in_measure)

        # TODO: hmmm
        self.current_beat_length = self.timefun(self.measure + self.offset_in_measure + inc) - self.time

        if 'FreeText' in beat:
            self.tones.append({
                '@id': 0,  # TODO
                '@time': self.time
            })

        # TODO: handle current hand position
        if 'Notes' in beat:
            if type(beat.Notes) is not list:
                beat.Notes = [beat.Notes]

            self.new_notes(beat, beat.Notes)

        self.offset_in_measure += inc
        self.time = self.timefun(self.measure + self.offset_in_measure)

        # Time stays the same but next note duration is diminished by inc
        if 'GraceNotes' in beat and beat.GraceNotes == 'OnBeat':
            self.offset_in_measure -= inc

    def new_bar(self, bar, bar_settings):
        num, den = map(int, bar_settings.Time.split('/'))
        self.quarters_per_bar = 4.0 * num / den

        if 'Repeat' in bar_settings and bar_settings.Repeat['@start']:
            self.start_repeat_bar = self.bar_idx

        # Need to update phrases too
        # if 'Section' in bar_settings:
        #     self.sections.append({
        #         '@name': bar_settings.Section.Text,
        #         '@number': len(self.sections),  # TODO
        #         '@startTime': self.timefun(self.measure)
        #     })

        for i in range(int(self.quarters_per_bar)):
            self.ebeats.append({
                '@time': self.timefun(self.measure + i / self.quarters_per_bar),
                '@measure': self.measure + 1 if i == 0 else -1
            })

        self.offset_in_measure = 0.0
        # TODO: other voices
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

            # TODO: beat value
            # gp.MasterTrack['Automations']['Automation']['Type'] == 'Tempo'
            self.new_bar(bar, bar_settings)

            self.bar_idx += 1  # no repeats -> get position in score
            self.measure += 1  # counting repeats -> compute time

        return self.json()


if __name__ == '__main__':
    from docopt import docopt
    from xml.dom.minidom import parseString

    args = docopt(__doc__)

    gp, mp3, sync = load_goplayalong(args['FILE'])

    # TODO: other tracks
    sng = SngBuilder(gp, gp.Tracks[0], sync)

    x = json2xml('song', sng.run())
    print parseString(x).toprettyxml()
