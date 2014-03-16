#!/usr/bin/env ruby

require 'rexml/document'
require 'interpolator'
require 'guitar_pro_parser'
require 'gyoku'
require 'matrix'

# Converts note to its digit representation
# To be removed since it exists in master for gem
def GuitarProHelper.note_to_digit(note)
  result = 0
  result += 1 until GuitarProHelper.digit_to_note(result) == note
  result
end

I_DURATIONS = GuitarProHelper::DURATIONS.invert

STANDARD_TUNING = %w(E3 A3 D4 G4 B4 E5).map do |n|
  GuitarProHelper.note_to_digit(n)
end

## HELPERS

def sortable_name(n)
  n.sub(/^(the|a|an)\s+/i, '').capitalize
end

# Helper for counted arrays
def carray(symbol, arr)
  {
    :@count => arr.count,
    :content! => { symbol => arr }
  }
end

def compute_tuning(gp_tuning)
  t = gp_tuning.reverse.map { |n| GuitarProHelper.note_to_digit(n) }
  x = Vector.elements(t) - Vector.elements(STANDARD_TUNING)

  {
    :@string0 => x[0], :@string1 => x[1], :@string2 => x[2],
    :@string3 => x[3], :@string4 => x[4], :@string5 => x[5]
  }
end

## OVERVIEW

# Ebeats
# Build notes and chords
# Tone change from beat markers
# sections
# anchors
# handshapes
# chord templates
# fingering
# tuning, metadat, arrangement properties

# TODO
# cent offset is missing from GP
# compute internalName, sort names
# albumArt
# ToneA, ..., D

class SngXmlBuilder
  def initialize(gp_song, track, sync_data)
    @gp_song = gp_song
    @track = track
    @bar2time = sync_data

    @notes = []
    @chords = []

    @phrases = [
      {
        :@disparity => 0,
        :@name => '',
        :@ignore => 0,
        :@maxDifficulty => 0,
        :@solo => 0
      }
    ]

    @phrase_iterations = [
      {
        :@time => 10.000,
        :@phraseId => 1,
        :@variation => ''
      }
    ]

    @new_linked_diffs = [{ :@id => 1 }]

    @linked_diffs = [
      {
        :@childId => 1,
        :@parentId => 1
      }
    ]

    @chord_templates = [
      {
        :@chordName => '',
        :@displayName => 'g5p5',
        :@finger0 => -1,
        :@finger1 => -1,
        :@finger2 => -1,
        :@finger3 => -1,
        :@finger4 => 1,
        :@finger5 => 1,
        :@fret0 => -1,
        :@fret1 => -1,
        :@fret2 => -1,
        :@fret3 => -1,
        :@fret4 => 5,
        :@fret5 => 5
      }
    ]

    @ebeats = [
      {
        :@time => 10.0,
        :@measure => 0
      }
    ]

    @sections = [
      {
        :@name => 'chorus',
        :@number => 1,
        :@startTime => 12.01
      }
    ]

    @events = [
      {
        :@time => 10.0,
        :@code => 'B0'
      }
    ]

    @fret_hand_mutes = []

    @anchors = [
      {
        :@time => 275.931,
        :@fret => 13,
        :@width => 4.000
      }
    ]

    @hand_shapes = [
      {
        :@chordId => 4,
        :@endTime => 5.728,
        :@startTime => 5.672
      }
    ]
  end

  def buildXML
    {
      :@version      => 8,
      :title         => @gp_song.title,
      :arrangement   => @track.name,
      :wavefilepath  => '',
      :part          => 1,
      :offset        => -10.000,
      :centOffset    => 0,
      :songLength    => 0.000,
      :internalName  => '',
      :songNameSort  => '',
      :startBeat     => 0.000,
      :averageTempo  => @gp_song.bpm,
      :tuning        => compute_tuning(@track.strings),
      :capo          => @track.capo,
      :artistName    => @gp_song.artist,
      :artistNameSort => '',
      :albumName     => @gp_song.album,
      :albumNameSort => '',
      :albumYear     => @gp_song.copyright,
      :albumArt      => '',
      :crowdSpeed    => 1,
      :arrangementProperties => {
        :@represent         => 1,
        :@bonusArr          => 0,
        :@standardTuning    => 1,
        :@nonStandardChords => 0,
        :@barreChords       => 0,
        :@powerChords       => 0,
        :@dropDPower        => 0,
        :@openChords        => 0,
        :@fingerPicking     => 0,
        :@pickDirection     => 0,
        :@doubleStops       => 0,
        :@palmMutes         => 0,
        :@harmonics         => 0,
        :@pinchHarmonics    => 0,
        :@hopo              => 0,
        :@tremolo           => 0,
        :@slides            => 0,
        :@unpitchedSlides   => 0,
        :@bends             => 0,
        :@tapping           => 0,
        :@vibrato           => 0,
        :@fretHandMutes     => 0,
        :@slapPop           => 0,
        :@twoFingerPicking  => 0,
        :@fifthsAndOctaves  => 0,
        :@syncopation       => 0,
        :@bassPick          => 0,
        :@sustain           => 0,
        :@pathLead          => 1,
        :@pathRhythm        => 0,
        :@pathBass          => 0
      },
      :lastConversionDateTime => Time.now.strftime('%F %T'),

      :toneA => '',
      :toneB => '',
      :toneC => '',
      :toneD => '',
      :tones => [{
        # :tone => {
        #   :@id => 0,
        #   :@time => 10.0
        # }
      }],

      :phrases => carray(:phrase, @phrases),

      :phraseIterations => carray(:phraseIteration, @phrase_iterations),

      :newLinkedDiffs => carray(:nld_phrase, @new_linked_diffs),

      :linkedDiffs => carray(:linkedDiff, @linked_diffs),

      :phraseProperties => [],

      :chordTemplates => carray(:chordTemplate, @chord_templates),

      :fretHandMuteTemplates => carray(:fretHandMuteTemplate, []),

      :ebeats => carray(:ebeat, @ebeats),

      :sections => carray(:section, @sections),

      :events => carray(:event, @events),

      :transcriptionTrack => {
        :@difficulty => -1
      },

      :levels => carray(:level, [{
        :@difficulty => 0,
        :notes => carray(:note, @notes),
        :chords => carray(:chord, @chords),
        :fretHandMutes => carray(:fretHandMute, @fret_hand_mutes),
        :anchors => carray(:anchor, @anchors),
        :handShapes => carray(:handShape, @hand_shapes)
      }])
    }
  end

  def create_note(time, string, note)
    bb = []
    if note.bend
      # TODO: skip first if step == 0 ?
      note.bend[:points].each do |b|
        bb << {
          :@time => b[:time],
          :@step => b[:pitch_alteration] / 100.0
        }
      end
    end

    if note.slide
      # puts time, note.inspect
    end

    if note.hammer_or_pull
      # puts time, note.inspect
      # puts note.hammer_or_pull
    end

    if note.grace
      # puts time, note.grace
    end

    # puts note.fingers[:left] if note.fingers[:left]
    # puts note.fingers[:right] if note.fingers[:right]

    # what needs to look at the next note
    # sustain
    # hammer / pull

    n = {
      :@time => time,
      #     :@linkNext => 0,
      :@accent => note.accentuated ? 1 : 0,
      :@bend => bb.count > 0 ? 1 : 0,
      :@fret => note.fret,
      #     :@hammerOn => 0,
      :@harmonic => note.harmonic != :none ? 1 : 0, # note.harmonic != :pinch
      # :@hopo => 0, ## ???
      :@ignore => 0,
      :@leftHand => -1,
      :@mute => note.type == :dead ? 1 : 0,
      :@palmMute => note.palm_mute ? 1 : 0,
      :@pluck => -1,
      #     :@pullOff => 0,
      :@slap => -1,
      #     :@slideTo => -1,
      :@string => string,
      #     :@sustain => 1.130,
      :@tremolo => note.tremolo ? 1 : 0,
      :@harmonicPinch => note.harmonic == :pinch ? 1 : 0,
      :@pickDirection => 0,
      :@rightHand => -1,
      #     :@slideUnpitchTo => -1,
      :@tap => 0,
      :@vibrato => 0,
      :bendValues => carray(:bendValue, bb)
    }
    n
  end

  #   chords = []
  def create_chord(time, notes)
    {
      :@time => bar2time(time),
      # :@linkNext => 0,
      # :@accent => 0,
      # :@chordId => 12,
      # :@fretHandMute => 0,
      # :@highDensity => 0,
      # :@ignore => 0,
      # :@palmMute => 0,
      # :@hopo => 0,
      # :@strum => "down",
      :@chordNotes => notes # no bend values
    }
  end

  def build
    measure = 0

    @track.bars.zip(@gp_song.bars_settings).each do |bar, bar_settings|
      measure_fraction = 0.0

      if bar_settings.new_time_signature
        s = bar_settings.new_time_signature
        @signature = s[:numerator] / s[:denominator] * 4.0
      end

      bar.voices[:lead].each do |beat|
        t = fraction_in_bar(beat.duration)

        nn = beat.strings.map do |string, note|
          string = @track.strings.count - string.to_i
          create_note(@bar2time.read(measure + measure_fraction), string, note)
        end

        @notes << nn if nn.count == 1
        # Chords
        # cc = create_chord(measure + measure_fraction, nn) if nn.count > 1
        # puts "#{cc}" if nn.count > 1

        measure_fraction += t
      end

      measure += 1.0
    end
  end

  def fraction_in_bar(d)
    1.0 / (2**Integer(I_DURATIONS[d])) / @signature
  end
end

def time_interpolator(sync_data)
  s = sync_data.split '#'
  s.shift

  t = s.map { |u| u.split ';' }

  m = t.map do |time, bar, bar_fraction, beat_duration|
    { bar.to_f + bar_fraction.to_f => time.to_f / 1000.0 }
  end

  Interpolator::Table.new m.reduce Hash.new, :merge
end

## SCRIPT

gpa_xml = REXML::Document.new File.new(ARGV[0], 'r')
score_url = gpa_xml.elements['track'].elements['scoreUrl'].text
# mp3_url = gpa_xml.elements['track'].elements['mp3Url'].text
sync_data = gpa_xml.elements['track'].elements['sync'].text

# TODO: if no sync data use bpm

tabsong = GuitarProParser.read_file(score_url)

tabsong.tracks[0, 1].each do |track|
  xml = SngXmlBuilder.new tabsong, track, time_interpolator(sync_data)
  xml.build

  puts Gyoku.xml :song => xml.buildXML
end
