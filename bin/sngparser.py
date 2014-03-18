"""
Parser/builder for binary Rocksmith 2014 SNG files.

Port of the HSL file description to python. Requires the construct library.

Usage:
    >>> from sngparser import SONG
    >>> raw_input = open('myfile.sng','rb').read()
    >>> sng = SONG.parse(raw_input)
    >>> build_output = SONG.build(sng)
    >>> build_output == raw_input
    True
"""

from construct import Struct, If, Array, PrefixedArray, Padding, \
    SLInt8, ULInt16, SLInt16, ULInt32, SLInt32, LFloat32, LFloat64, String


def array(struct):
    """Standard prefixed arrays."""
    return PrefixedArray(struct, ULInt32('count'))

BEAT = Struct(
    'ebeats',
    LFloat32('time'),
    ULInt16('measure'),
    ULInt16('beat'),
    ULInt32('phraseIteration'),
    ULInt32('mask')
)

PHRASE = Struct(
    'phrases',
    SLInt8('solo'),
    SLInt8('disparity'),
    SLInt8('ignore'),
    Padding(1),
    ULInt32('maxDifficulty'),
    ULInt32('phraseIterationLinks'),
    String('name', 32, padchar='\x00')
)

CHORD_TEMPLATE = Struct(
    'chordTemplates',
    ULInt32('mask'),
    SLInt8('fret0'),
    SLInt8('fret1'),
    SLInt8('fret2'),
    SLInt8('fret3'),
    SLInt8('fret4'),
    SLInt8('fret5'),
    SLInt8('finger0'),
    SLInt8('finger1'),
    SLInt8('finger2'),
    SLInt8('finger3'),
    SLInt8('finger4'),
    SLInt8('finger5'),
    Array(6, SLInt32('notes')),
    String('chordName', 32, padchar='\x00')
)

BEND_VALUE = Struct(
    'bendValues',
    LFloat32('time'),
    LFloat32('step'),
    Padding(3),
    # Seens values: 0 1 3 31 32 36..49 51..54 56
    SLInt8('UNK')
)

BEND_VALUES_32 = Struct(
    'bendValues32',
    Array(32, BEND_VALUE),
    ULInt32('usedCount')
)

CHORD_NOTE = Struct(
    'chordNotes',
    Array(6, ULInt32('mask')),
    Array(6, BEND_VALUES_32),
    Array(6, SLInt8('slideTo')),
    Array(6, SLInt8('slideUnpitchTo')),
    Array(6, SLInt16('vibrato')),
)

VOCAL = Struct(
    'vocals',
    LFloat32('time'),
    SLInt32('note'),
    LFloat32('length'),
    String('lyric', 48, padchar='\x00')
)

TEXTURE = Struct(
    'textures',
    String('fontPath', 128, padchar='\x00'),
    ULInt32('fontPathLength'),
    Padding(4),
    ULInt32('width'),
    ULInt32('height')
)

DEFINITION = Struct(
    'definitions',
    String('utf8', 12, padchar='\x00'),
    Array(4, LFloat32('rect1')),
    Array(4, LFloat32('rect2'))
)

SYMBOLS = Struct(
    'symbols',
    array(Array(8, SLInt32('header'))),
    array(TEXTURE),
    array(DEFINITION)
)

PHRASE_ITERATION = Struct(
    'phraseIterations',
    ULInt32('phraseId'),
    LFloat32('time'),
    LFloat32('endTime'),
    Array(3, ULInt32('difficulty')),
)

PHRASE_EXTRA_INFO_BY_LEVEL = Struct(
    'phraseExtraInfoByLevel',
    ULInt32('phraseId'),
    ULInt32('difficulty'),
    ULInt32('empty'),
    SLInt8('levelJump'),
    SLInt16('redundant'),
    Padding(1)
)

NEW_LINKED_DIFF = Struct(
    'newLinkedDiffs',
    SLInt32('levelBreak'),
    array(ULInt32('nld_phrase'))
)

ACTION = Struct(
    'actions',
    LFloat32('time'),
    String('name', 256, padchar='\x00')
)

EVENT = Struct(
    'events',
    LFloat32('time'),
    String('code', 256, padchar='\x00')
)

TONE = Struct(
    'tones',
    LFloat32('time'),
    ULInt32('id')
)

DNA = Struct(
    'dnas',
    LFloat32('time'),
    ULInt32('id')
)

SECTION = Struct(
    'sections',
    String('name', 32, padchar='\x00'),
    ULInt32('number'),
    LFloat32('startTime'),
    LFloat32('endTime'),
    ULInt32('startPhraseIterationId'),
    ULInt32('endPhraseIterationId'),
    Array(36, SLInt8('stringMask'))
)

ANCHOR = Struct(
    'anchors',
    LFloat32('time'),
    LFloat32('endTime'),
    LFloat32('UNK_time'),
    LFloat32('UNK_time2'),
    SLInt32('fret'),
    SLInt32('width'),
    ULInt32('phraseIterationId'),
)

ANCHOR_EXTENSION = Struct(
    'anchorExtensions',
    LFloat32('time'),
    SLInt8('fret'),
    Padding(7)
)

FINGERPRINT = Struct(
    'fingerPrints',
    ULInt32('chordId'),
    LFloat32('startTime'),
    LFloat32('endTime'),
    LFloat32('UNK_startTime'),
    LFloat32('UNK_endTime'),
)

NOTE = Struct(
    'notes',
    ULInt32('mask'),
    ULInt32('flags'),
    SLInt32('hash'),
    LFloat32('time'),
    SLInt8('string'),
    SLInt8('fret'),
    SLInt8('anchorFret'),
    SLInt8('anchorWidth'),
    SLInt32('chordId'),
    SLInt32('chordNoteId'),
    SLInt32('phraseId'),
    SLInt32('phraseIterationId'),
    Array(2, SLInt16('fingerPrintId')),
    SLInt16('nextIterNote'),
    SLInt16('prevIterNote'),
    SLInt16('parentPrevNote'),
    SLInt8('slideTo'),
    SLInt8('slideUnpitchTo'),
    SLInt8('leftHand'),
    SLInt8('tap'),
    SLInt8('pickDirection'),
    SLInt8('slap'),
    SLInt8('pluck'),
    SLInt16('vibrato'),
    LFloat32('sustain'),
    LFloat32('bend'),
    array(BEND_VALUE)
)

LEVEL = Struct(
    'levels',
    ULInt32('difficulty'),
    array(ANCHOR),
    array(ANCHOR_EXTENSION),
    Array(2, array(FINGERPRINT)),
    array(NOTE),
    array(LFloat32('averageNotesPerIter')),
    array(ULInt32('notesInIterCountNoIgnored')),
    array(ULInt32('notesInIterCount'))
)

METADATA = Struct(
    'metadata',
    LFloat64('maxScore'),
    LFloat64('maxNotes'),
    LFloat64('maxNotesNoIgnored'),
    LFloat64('pointsPerNote'),
    LFloat32('firstBeatLength'),
    LFloat32('startTime'),
    SLInt8('capo'),
    String('lastConversionDateTime', 32, padchar='\x00'),
    SLInt16('part'),
    LFloat32('songLength'),
    array(SLInt16('tuning')),
    LFloat32('firstNoteTime'),
    LFloat32('firstNoteTime2'),
    SLInt32('maxDifficulty')
)

SONG = Struct(
    'song',
    array(BEAT),
    array(PHRASE),
    array(CHORD_TEMPLATE),
    array(CHORD_NOTE),
    array(VOCAL),
    If(lambda ctx: len(ctx['vocals']) > 0, SYMBOLS),
    array(PHRASE_ITERATION),
    array(PHRASE_EXTRA_INFO_BY_LEVEL),
    array(NEW_LINKED_DIFF),
    array(ACTION),
    array(EVENT),
    array(TONE),
    array(DNA),
    array(SECTION),
    array(LEVEL),
    METADATA
)
