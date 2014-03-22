#!/usr/bin/env python

"""
Generate JSON manifest and binary SNG for Rocksmith 2014 from source SNG XML.

Usage: xml2sng.py FILE...
"""

import binascii
import md5
import json
import random

from xmlhelpers import xml2json, AttrDict
import sngparser

MIDI_NOTES = [40, 45, 50, 55, 59, 64]

DNA_MAPPING = {
    'dna_none': 0,
    'dna_solo': 1,
    'dna_riff': 2,
    'dna_chord': 3
}

CHORD_MASK_ARPEGGIO = 0x00000001
CHORD_MASK_NOP = 0x00000002

NOTE_FLAGS_NUMBERED = 0x00000001

NOTE_MASK_CHORD = 0x00000002
NOTE_MASK_OPEN = 0x00000004
NOTE_MASK_FRETHANDMUTE = 0x00000008
NOTE_MASK_TREMOLO = 0x00000010
NOTE_MASK_HARMONIC = 0x00000020
NOTE_MASK_PALMMUTE = 0x00000040
NOTE_MASK_SLAP = 0x00000080
NOTE_MASK_PLUCK = 0x00000100
NOTE_MASK_POP = 0x00000100
NOTE_MASK_HAMMERON = 0x00000200
NOTE_MASK_PULLOFF = 0x00000400
NOTE_MASK_SLIDE = 0x00000800
NOTE_MASK_BEND = 0x00001000
NOTE_MASK_SUSTAIN = 0x00002000
NOTE_MASK_TAP = 0x00004000
NOTE_MASK_PINCHHARMONIC = 0x00008000
NOTE_MASK_VIBRATO = 0x00010000
NOTE_MASK_MUTE = 0x00020000
NOTE_MASK_IGNORE = 0x00040000
NOTE_MASK_LEFTHAND = 0x00080000
NOTE_MASK_RIGHTHAND = 0x00100000
NOTE_MASK_HIGHDENSITY = 0x00200000
NOTE_MASK_SLIDEUNPITCHEDTO = 0x00400000
NOTE_MASK_SINGLE = 0x00800000
NOTE_MASK_CHORDNOTES = 0x01000000
NOTE_MASK_DOUBLESTOP = 0x02000000
NOTE_MASK_ACCENT = 0x04000000
NOTE_MASK_PARENT = 0x08000000
NOTE_MASK_CHILD = 0x10000000
NOTE_MASK_ARPEGGIO = 0x20000000
NOTE_MASK_STRUM = 0x80000000


def note_mask(note, single):
    """Compute note mask"""
    mask = 0
    mask |= NOTE_MASK_SINGLE if single else 0
    mask |= NOTE_MASK_OPEN if note.fret == 0 else 0
    mask |= NOTE_MASK_PARENT if note.linkNext != 0 else 0
    mask |= NOTE_MASK_ACCENT if note.accent != 0 else 0
    mask |= NOTE_MASK_BEND if note.bend != 0 else 0
    mask |= NOTE_MASK_HAMMERON if note.hammerOn != 0 else 0
    mask |= NOTE_MASK_HARMONIC if note.harmonic != 0 else 0
    mask |= NOTE_MASK_IGNORE if single and note.ignore != 0 else 0
    mask |= NOTE_MASK_LEFTHAND if single and note.leftHand != -1 else 0
    mask |= NOTE_MASK_MUTE if note.mute != 0 else 0
    mask |= NOTE_MASK_PALMMUTE if note.palmMute != 0 else 0
    mask |= NOTE_MASK_PLUCK if note.pluck != -1 else 0
    mask |= NOTE_MASK_PULLOFF if note.pullOff != 0 else 0
    mask |= NOTE_MASK_SLAP if note.slap != -1 else 0
    mask |= NOTE_MASK_SLIDE if note.slideTo != -1 else 0
    mask |= NOTE_MASK_SUSTAIN if note.sustain != 0 else 0
    mask |= NOTE_MASK_TREMOLO if note.tremolo != 0 else 0
    mask |= NOTE_MASK_PINCHHARMONIC if note.harmonicPinch != 0 else 0
    mask |= NOTE_MASK_RIGHTHAND if note.rightHand != -1 else 0
    mask |= NOTE_MASK_SLIDEUNPITCHEDTO if note.slideUnpitchTo != -1 else 0
    mask |= NOTE_MASK_TAP if note.tap != 0 else 0
    mask |= NOTE_MASK_VIBRATO if note.vibrato != 0 else 0
    return mask


def phraseiteration(sng, time, include_end=False):
    """Returns the index of the phrase iteration containing time."""
    for i, piter in enumerate(sng.phraseIterations[1:]):
        if piter.time > time or (include_end and piter.time == time):
            return i
    return len(sng.phraseIterations) - 1


def midi(sng, strg, fret):
    """Computes standard MIDI note value"""

    if fret == -1:
        return -1

    base = MIDI_NOTES[strg] + sng.tuning['string' + str(strg)]
    base -= 12 if sng.arrangement == 'Bass' else 0

    return base + fret


def process_ebeats(sng):
    if sng.ebeats:
        sng.ebeats[0]['beat'] = 0
    for ebeat, previous in zip(sng.ebeats[1:], sng.ebeats[:-1]):
        if ebeat.measure > -1:
            ebeat['beat'] = 0
        else:
            ebeat.measure = previous.measure
            ebeat['beat'] = previous.beat + 1

    for b in sng.ebeats:
        b['mask'] = 1 + (b.measure % 2 == 0) * 2 if b.beat == 0 else 0
        b['phraseIteration'] = phraseiteration(sng, b.time, True)


def process_chord_template(sng, template):
    template['mask'] = 0
    template.displayName = str(template.displayName)
    if template.displayName.endswith('arp'):
        template.mask |= CHORD_MASK_ARPEGGIO
    if template.displayName.endswith('nop'):
        template.mask |= CHORD_MASK_NOP

    template.notes = [midi(sng, k, template['fret' + str(k)])
                      for k in range(6)]


def process_phrase_iterations(sng):
    if sng.phraseIterations:
        sng.phraseIterations[-1]['endTime'] = sng.songLength
    for i, nexti in zip(sng.phraseIterations[:-1], sng.phraseIterations[1:]):
        i.endTime = nexti.time

    for i in sng.phraseIterations:
        i.difficulty = [0, 0, sng.phrases[i.phraseId].maxDifficulty]
        if 'heroLevels' in i:
            for herolevel in i.heroLevels:
                i.difficulty[herolevel.hero - 1] = herolevel.difficulty


def process_sections(sng):
    if sng.sections:
        sng.sections[-1]['endTime'] = sng.songLength
    for section, nextsection in zip(sng.sections[:-1], sng.sections[1:]):
        section['endTime'] = nextsection.startTime

    for s in sng.sections:
        s['startPhraseIterationId'] = phraseiteration(sng, s.startTime, False)
        s['endPhraseIterationId'] = phraseiteration(sng, s.endTime, True)

        s['isSolo'] = s.name == 'solo'
        for piter in sng.phraseIterations[
                s.startPhraseIterationId:s.endPhraseIterationId]:
            if sng.phrases[piter.phraseId].solo > 0:
                s['isSolo'] = True

        stringmask = 36 * [0]
        maxdifficulty = max([p.maxDifficulty for p in sng.phrases])
        for j in range(maxdifficulty, -1, -1):
            level = sng.levels[j]
            mask = 0
            for note in level.notes:
                if s.startTime <= note.time < s.endTime:
                    mask |= 1 << note.string
            for chord in level.chords:
                if s.startTime <= chord.time < s.endTime:
                    chordtemplate = sng.chordTemplates[chord.chordId]
                    for i in range(6):
                        if chordtemplate['fret' + str(i)] > -1:
                            mask |= 1 << i
            if mask == 0 and j < maxdifficulty:
                mask = stringmask[j + 1]
            stringmask[j] = mask
        s['stringMask'] = stringmask


def process_note(sng, note, single=True):
    note['flags'] = 0
    note['anchorFret'] = -1
    note['anchorWidth'] = -1
    note['chordId'] = -1
    note['chordNoteId'] = -1
    note['fingerPrintId'] = [-1, -1]
    note['nextIterNote'] = -1
    note['prevIterNote'] = -1
    note['parentPrevNote'] = -1
    if not 'bendValues' in note:
        note['bendValues'] = []
    for bend in note.bendValues:
        bend['UNK'] = 0

    note['phraseIterationId'] = phraseiteration(sng, note.time, False)
    note['phraseId'] = sng.phraseIterations[note.phraseIterationId].phraseId
    note['mask'] = note_mask(note, single)
    note['hash'] = binascii.crc32(str(note.values()))


def process_chord_note(sng, chord):
    if not 'chordNote' in chord:
        chord.chordNote = []

    for note in chord.chordNote:
        process_note(sng, note, False)

    technique = False
    mask = 6 * [0]
    slideto = 6 * [-1]
    slideunpitcho = 6 * [-1]
    vibrato = 6 * [0]

    # not using multiplicative notation (references...)
    bend = [AttrDict(
        {'usedCount':  0,
         'bendValues': [AttrDict({'time': 0.0,
                                  'step': 0,
                                  'UNK': 0}) for _ in range(32)]
         }) for _ in range(6)]

    for n in chord.chordNote:
        mask[n.string] = n.mask
        technique |= n.mask != 0
        vibrato[n.string] = n.vibrato
        slideto[n.string] = n.slideTo
        slideunpitcho[n.string] = n.slideUnpitchTo

        bend[n.string]['usedCount'] = len(n.bendValues)
        bend[n.string]['bendValues'][0:len(n.bendValues)] = n.bendValues

    cn = AttrDict({
        'mask': mask,
        'bendValues32': bend,
        'slideTo': slideto,
        'slideUnpitchTo': slideunpitcho,
        'vibrato': vibrato
    })
    if technique and not cn in sng.chordNotes:
        sng.chordNotes.append(cn)

    return cn


def process_chord(sng, chord):
    cn = process_chord_note(sng, chord)

    chord['flags'] = 0
    if cn in sng.chordNotes:
        chord['chordNoteId'] = sng.chordNotes.index(cn)
    else:
        chord['chordNoteId'] = -1
    chord['string'] = -1
    chord['fret'] = -1
    chord['anchorFret'] = -1
    chord['anchorWidth'] = -1
    chord['fingerPrintId'] = [-1, -1]
    chord['prevIterNote'] = -1
    chord['parentPrevNote'] = -1
    chord['nextIterNote'] = -1
    chord['slideTo'] = -1
    chord['slideUnpitchTo'] = -1
    chord['leftHand'] = -1
    chord['vibrato'] = 0
    chord['bend'] = 0
    chord['tap'] = 0
    chord['pickDirection'] = -1
    chord['slap'] = -1
    chord['pluck'] = -1
    chord['bendValues'] = []

    chord['phraseIterationId'] = phraseiteration(sng, chord.time, False)
    chord['phraseId'] = sng.phraseIterations[chord.phraseIterationId].phraseId

    if len(chord.chordNote):
        chord['sustain'] = max([n.sustain for n in chord.chordNote])
    else:
        chord['sustain'] = 0.0

    count = len([0 for k in range(6) if
                sng.chordTemplates[chord.chordId]['fret' + str(k)] != -1])

    mask = NOTE_MASK_CHORD
    mask |= NOTE_MASK_CHORDNOTES if chord.chordNoteId > -1 else 0
    mask |= NOTE_MASK_PARENT if chord.linkNext else 0
    mask |= NOTE_MASK_ACCENT if chord.accent else 0
    mask |= NOTE_MASK_FRETHANDMUTE if chord.fretHandMute else 0
    mask |= NOTE_MASK_HIGHDENSITY if chord.highDensity else 0
    mask |= NOTE_MASK_IGNORE if chord.ignore else 0
    mask |= NOTE_MASK_PALMMUTE if chord.palmMute else 0
    mask |= NOTE_MASK_SUSTAIN if chord.sustain > 0 else 0
    mask |= NOTE_MASK_DOUBLESTOP if count == 2 else 0
    chord['mask'] = mask

    chord['hash'] = binascii.crc32(str(chord.values()))


def process_level(sng, level):
    if level.anchors:
        level.anchors[-1]['endTime'] = sng.phraseIterations[-1].time
    for anchor, nexta in zip(level.anchors[:-1], level.anchors[1:]):
        anchor['endTime'] = nexta.time
    for anchor in level.anchors:
        anchor['UNK_time'] = 0
        anchor['UNK_time2'] = 0
        anchor.width = int(anchor.width)

    for anchor in level.anchors:
        anchor['phraseIterationId'] = phraseiteration(sng, anchor.time, False)

    for h in level.handShapes:
        h['UNK_startTime'] = 0
        h['UNK_endTime'] = 0

    level.fingerPrints = []

    def is_arpeggio(u):
        return sng.chordTemplates[u.chordId].mask & CHORD_MASK_ARPEGGIO
    level.fingerPrints.append(filter(lambda x: not is_arpeggio(x),
                                     level.handShapes))
    level.fingerPrints.append(filter(is_arpeggio, level.handShapes))

    for note in level.notes:
        process_note(sng, note)

    for chord in level.chords:
        process_chord(sng, chord)
        level.notes.append(chord)

    level.notes.sort(key=lambda x: x.time)

    if len(level.notes) and sng.firstNoteTime > level.notes[0].time:
        sng.firstNoteTime = level.notes[0].time

    for note in level.notes:
        for j in range(2):
            for i, fp in enumerate(level.fingerPrints[j]):
                if fp.startTime <= note.time < fp.endTime:
                    note.fingerPrintId[j] = i
                    note.mask |= NOTE_MASK_ARPEGGIO if j == 1 else 0
                    if fp.startTime == note.time and note.chordId != -1:
                        note.mask |= NOTE_MASK_STRUM
                    if fp.UNK_startTime == 0:
                        fp.UNK_startTime = note.time
                    fp.UNK_endTime = note.time
                    if note.time + note.sustain < fp.endTime:
                        fp.UNK_endTime += note.sustain

        for anchor in level.anchors:
            if anchor.time <= note.time < anchor.endTime:
                note.anchorWidth = anchor.width
                note.anchorFret = anchor.fret
                if anchor.UNK_time == 0:
                    anchor.UNK_time = note.time
                anchor.UNK_time2 = note.time
                if note.time + note.sustain < anchor.endTime - 0.1:
                    anchor.UNK_time2 += note.sustain

    for anchor in level.anchors:
        if anchor.UNK_time == 0:
            anchor.UNK_time = anchor.time
            anchor.UNK_time2 = anchor.time + 0.1

    for i in sng.phraseIterations:
        count = 0
        for j, note in enumerate(level.notes):
            if note.time < i.time:
                continue
            if i.endTime <= note.time:
                break
            note.nextIterNote = j + 1
            if count > 0:
                note.prevIterNote = j - 1
            count += 1
        if count > 0:
            level.notes[j].nextIterNote = -1

    for j in range(1, len(level.notes)):
        note = level.notes[j]
        previous = level.notes[j - 1]
        prevnote = 1
        if note.time != previous.time:
            prevnote = 1
        else:
            for i in range(len(level.notes)):
                if j - i < 1:
                    prevnote = i
                    break
                prv = level.notes[j - i]
                if prv.time != note.time:
                    if prv.chordId != -1 or prv.string == note.string:
                        prevnote = i
                        break
        prev = level.notes[j - prevnote]
        if prev.mask & NOTE_MASK_PARENT:
            note.parentPrevNote = prev.nextIterNote - 1
            note.mask |= NOTE_MASK_CHILD

    level.anchorExtensions = []
    for note in level.notes:
        if note.slideTo != -1:
            level.anchorExtensions.append(AttrDict({
                'fret': note.slideTo,
                'time': note.time + note.sustain,
            }))

    level.notesInIterCount = len(sng.phraseIterations) * [0]
    level.notesInIterCountNoIgnored = len(sng.phraseIterations) * [0]
    for note in level.notes:
        for i, piter in enumerate(sng.phraseIterations[1:]):
            if piter.time > note.time:
                if note.ignore == 0:
                    level.notesInIterCountNoIgnored[i] += 1
                level.notesInIterCount[i] += 1
                break

    level.averageNotesPerIter = len(sng.phrases) * [0.0]
    iter_count = len(sng.phrases) * [0]
    for i, piter in enumerate(sng.phraseIterations):
        level.averageNotesPerIter[piter.phraseId] += level.notesInIterCount[i]
        iter_count[piter.phraseId] += 1
    for i, count in enumerate(iter_count):
        level.averageNotesPerIter[i] /= count

    # TODO this code needs rewrite
    p = 0
    i = 0
    while i < len(level.notes):
        if i == len(level.notes):
            break
        note = level.notes[i]
        if note.fret == 0:
            i += 1
            continue
        if sng.phraseIterations[p].endTime <= note.time:
            p += 1
            continue
        repeat = False
        start = i - 8
        if start < 0:
            start = 0
        j = i - 1
        while j >= start:
            if level.notes[j].time + 2.0 < note.time:
                j -= 1
                continue
            if level.notes[j].time < sng.phraseIterations[p].time:
                j -= 1
                continue
            if (note.chordId == -1 and level.notes[j].fret == note.fret) \
                or (note.chordId != -1
                    and level.notes[j].chordId == note.chordId):
                if level.notes[j].flags & NOTE_FLAGS_NUMBERED:
                    repeat = True
                    break
            j -= 1

        if not repeat:
            note.flags |= NOTE_FLAGS_NUMBERED
        i += 1


def process_metadata(sng):
    r1, r2 = [], []
    for i, piter in enumerate(sng.phraseIterations):
        j = sng.phrases[piter.phraseId].maxDifficulty
        r1.append(sng.levels[j].notesInIterCount[i])
        r2.append(sng.levels[j].notesInIterCountNoIgnored[i])

    maxnotes, maxnotes_noignored = float(sum(r1)), float(sum(r2))

    maxdifficulty = max([p.maxDifficulty for p in sng.phrases])
    sng.levels = sng.levels[:maxdifficulty + 1]

    sng['metadata'] = AttrDict({
        'maxScore': 100000.0,
        'maxNotes': maxnotes,
        'maxNotesNoIgnored': maxnotes_noignored,
        'pointsPerNote': 100000.0 / maxnotes if maxnotes > 0 else 0.0,
        'firstBeatLength': sng.ebeats[1].time - sng.ebeats[0].time,
        'startTime': sng.offset * -1.0,
        'capo': sng.capo if sng.capo != 0 else -1,
        'lastConversionDateTime': sng.lastConversionDateTime,
        'part': sng.part,
        'songLength': sng.songLength,
        'tuning': [sng.tuning['string' + str(k)] for k in range(6)],
        'firstNoteTime': sng.firstNoteTime,
        'firstNoteTime2': sng.firstNoteTime,
        'maxDifficulty': maxdifficulty
    })


def process_sng(sng):
    """Compile SNG."""

    # Sanitize a few things
    if not 'internalName' in sng:
        sng['internalName'] = sng.title

    if not 'albumNameSort' in sng:
        sng['albumNameSort'] = sng.albumName
    if not 'songNameSort' in sng:
        sng['songNameSort'] = sng.title

    if not 'vocals' in sng:
        sng['vocals'] = []
        sng['symbols'] = []

    if not 'tones' in sng:
        sng['tones'] = []
        sng['tone_Base'] = ''  # TODO: default value..
        sng['tone_A'] = ''
        sng['tone_B'] = ''
        sng['tone_C'] = ''
        sng['tone_D'] = ''
        sng['tone_Multiplayer'] = ''

    # Let's go
    sng['firstNoteTime'] = 1.0e6
    sng['phraseExtraInfoByLevel'] = []
    sng['actions'] = []
    sng['chordNotes'] = []

    process_ebeats(sng)

    for i, phrase in enumerate(sng.phrases):
        links = len([0 for pi in sng.phraseIterations if pi.phraseId == i])
        phrase.phraseIterationLinks = links

    for template in sng.chordTemplates:
        process_chord_template(sng, template)

    process_phrase_iterations(sng)

    for nld in sng.newLinkedDiffs:
        if not issubclass(type(nld.nld_phrase), list):
            nld.nld_phrase = [nld.nld_phrase]
        nld.nld_phrase = [x.id for x in nld.nld_phrase]

    sng['dnas'] = []
    for event in sng.events:
        if event.code in DNA_MAPPING:
            event.id = DNA_MAPPING[event.code]
            sng.dnas.append(event)

    process_sections(sng)

    for level in sng.levels:
        process_level(sng, level)

    process_metadata(sng)


# TODO vocals, arrangementType, difficulty
# chords, techniques, tones
def build_manifest(sng):

    urn_base = sng.internalName.lower()
    fullname = sng.internalName + '_' + sng.arrangement
    urn_full = fullname.lower()

    entry_id = md5.new(urn_full).hexdigest().upper()

    sng.arrangementProperties['routeMask'] = 0  # ROUTETYPE_MASK_UNDEFINED
    # ROUTETYPE_MASK_ANY = 8 ?
    if sng.arrangementProperties.pathLead:
        sng.arrangementProperties['routeMask'] = 1  # ROUTETYPE_MASK_LEAD
    elif sng.arrangementProperties.pathRhythm:
        sng.arrangementProperties['routeMask'] = 2  # ROUTETYPE_MASK_RHYTHM
    elif sng.arrangementProperties.pathBass:
        sng.arrangementProperties['routeMask'] = 4  # ROUTETYPE_MASK_BASS

    # TODO
    arrangementType = 0

    dnaSolo = max([0.0] + [e.time for e in sng.dnas if e.id == 1])
    dnaRiffs = max([0.0] + [e.time for e in sng.dnas if e.id == 2])
    dnaChords = max([0.0] + [e.time for e in sng.dnas if e.id == 3])

    score_PNV = 1.0
    if sng.metadata.maxNotes > 0.0:
        score_PNV = sng.metadata.maxScore / sng.metadata.maxNotes

    r = []
    for i, piter in enumerate(sng.phraseIterations):
        r.append([sng.levels[j].notesInIterCount[i] for j in piter.difficulty])

    notesEasy, notesMedium, notesHard = map(sum, zip(*r))
    easyMastery = 1.0
    mediumMastery = 1.0
    if notesHard > 0:
        easyMastery = notesEasy / notesHard
        mediumMastery = notesMedium / notesHard

    # TODO: no idea how those are computed
    songDiffEasy = 0.5
    songDiffMed = 0.5
    songDiffHard = 0.5

    sections = []
    for s in sng.sections:
        sections.append({
            'Name': s.name,
            'UIName': sng.title + ' ' + s.name + ' [' + str(s.number) + ']',
            'Number': s.number,
            'StartTime': s.startTime,
            'EndTime': s.endTime,
            'StartPhraseIterationIndex': s.startPhraseIterationId,
            'EndPhraseIterationIndex': s.endPhraseIterationId,
            'IsSolo': s.isSolo
        })

    phrases = []
    for p in sng.phrases:
        phrases.append({
            "MaxDifficulty": p.maxDifficulty,
            "Name": p.name,
            "IterationCount": p.phraseIterationLinks
        })

    phraseIterations = []
    for piter in sng.phraseIterations:
        phraseIterations.append({
            'PhraseIndex': piter.phraseId,
            'MaxDifficulty': max(piter.difficulty),
            'Name': sng.phrases[piter.phraseId].name,
            'StartTime': piter.time,
            'EndTime': piter.endTime
        })

    chordTemplates = []
    for idx, chord in enumerate(sng.chordTemplates):
        if chord.chordName == '':
            continue
        chordTemplates.append({
            'ChordId': idx,
            'ChordName': chord.chordName,
            'Fingers': [chord.finger0, chord.finger1, chord.finger2,
                        chord.finger3, chord.finger4, chord.finger5],
            'Frets': [chord.fret0, chord.fret1, chord.fret2,
                      chord.fret3, chord.fret4, chord.fret5]
        })

    # TODO
    chords = {}
    techniques = {}
    tones = []
    sng.tone_Base = "Baptisms of Fire2",
    tones = [{
        "GearList": {
          "Rack1": {
            "Type": "Racks",
            "KnobValues": {
              "Rack_StudioCompressor_Threshold": -18.0,
              "Rack_StudioCompressor_Ratio": 1.0,
              "Rack_StudioCompressor_Attack": 55.0,
              "Rack_StudioCompressor_Release": 120.0
            },
            "Key": "Rack_StudioCompressor",
            "Category": "Dynamics"
          },
          "Amp": {
            "Type": "Amps",
            "KnobValues": {
              "Amp_MarshallJTM45_Gain": 88.0,
              "Amp_MarshallJTM45_Bass": 75.0,
              "Amp_MarshallJTM45_Mid": 66.0,
              "Amp_MarshallJTM45_Treble": 66.0,
              "Amp_MarshallJTM45_Pres": 30.0
            },
            "Key": "Amp_MarshallJTM45",
            "Category": "Amp"
          },
          "Cabinet": {
            "Type": "Cabinets",
            "KnobValues": {},
            "Key": "Cab_Marshall1960a_Condenser_OffAxis",
            "Category": "Condenser_OffAxis"
          },
          "PrePedal1": {
            "Type": "Pedals",
            "KnobValues": {
              "Pedal_SpringReverb_Time": 37.0,
              "Pedal_SpringReverb_Depth": 40.0,
              "Pedal_SpringReverb_Mix": 53.0
            },
            "Key": "Pedal_SpringReverb",
            "Category": "Reverb"
          }
        },
        "IsCustom": True,
        "Volume": "-20",
        "ToneDescriptors": [
          "$[35750]SPECIAL EFFECT"
        ],
        "Key": "Baptisms of Fire2",
        "NameSeparator": " - ",
        "Name": "Baptisms of Fire2",
        "SortOrder": 0.0
    }]

    return urn_full, {
        'AlbumArt': 'urn:image:dds:album_' + urn_base,
        'AlbumName': sng.albumName,
        'AlbumNameSort': sng.albumNameSort,
        'ArrangementName': sng.arrangement,
        'ArrangementProperties': sng.arrangementProperties,
        'ArrangementSort': 0,
        'ArrangementType': arrangementType,
        'ArtistName': sng.artistName,
        'ArtistNameSort': sng.artistNameSort,
        'BlockAsset': 'urn:emergent-world:' + urn_base,
        'CentOffset': float(sng.centOffset),
        'Chords': chords,
        'ChordTemplates': chordTemplates,
        'DLC': True,
        'DLCKey': sng.internalName,
        'DNA_Chords': dnaChords,
        'DNA_Riffs': dnaRiffs,
        'DNA_Solo': dnaSolo,
        'DynamicVisualDensity': 20 * [2.0],
        'EasyMastery': easyMastery,
        'FullName': fullname,
        'LastConversionDateTime': sng.lastConversionDateTime,
        'LeaderboardChallengeRating': 0,
        'ManifestUrn': 'urn:database:json-db:' + urn_full,
        'MasterID_PS3': -1,
        'MasterID_RDV': random.randint(0, 2 ** 32 - 1),  # todo VOCAL
        'MasterID_XBox360': -1,
        'MaxPhraseDifficulty': sng.metadata.maxDifficulty,
        'MediumMastery': mediumMastery,
        'NotesEasy': notesEasy,
        'NotesHard': notesHard,
        'NotesMedium': notesMedium,
        'Phrases': phrases,
        'PhraseIterations': phraseIterations,
        'PreviewBankPath': 'song_' + urn_base + '_preview.bnk',
        'RelativeDifficulty': 0,
        'Representative': not(sng.arrangementProperties.bonusArr),
        'Score_MaxNotes': sng.metadata.maxNotes,
        'Score_PNV': score_PNV,
        'Sections': sections,
        'Shipping': True,
        'ShowlightsXML': 'urn:application:xml:' + urn_base + '_showlights',
        'SKU': 'RS2',
        'SongAsset': 'urn:application:musicgame-song:' + urn_full,
        'SongAverageTempo': sng.averageTempo,
        'SongBank': 'song_' + urn_base + '.bnk',
        'SongDiffEasy': songDiffEasy,
        'SongDiffHard': songDiffHard,
        'SongDifficulty': songDiffHard,
        'SongDiffMed': songDiffMed,
        'SongEvent': 'Play_' + sng.internalName,
        'SongKey': sng.internalName,
        'SongLength': sng.songLength,
        'SongName': sng.title,
        'SongNameSort': sng.songNameSort,
        'SongOffset': sng.offset,
        'SongPartition': sng.part,
        'SongXml': 'urn:application:xml:' + urn_full,
        'SongYear': sng.albumYear,
        'TargetScore': sng.metadata.maxScore,
        'Techniques': techniques,
        'Tone_A': sng.tone_A,
        'Tone_B': sng.tone_B,
        'Tone_Base': sng.tone_Base,
        'Tone_C': sng.tone_C,
        'Tone_D': sng.tone_D,
        'Tone_Multiplayer': sng.tone_Multiplayer,
        'Tones': tones,
        'Tuning': sng.tuning,
        'PersistentID': entry_id
    }


def manifest_header(manifest):
    return {
        'Entries': {
            manifest['PersistentID']: {
                'Attributes': manifest
            }
        },
        'ModelName': 'RSEnumerable_Song',
        'IterationVersion': 2,
        'InsertRoot': 'Static.Songs.Entries'
    }


def compile_xml(text):
    sng = xml2json(text, notag=True)
    process_sng(sng)
    urn, manifest = build_manifest(sng)
    return urn, manifest_header(manifest), sngparser.SONG.build(sng)
