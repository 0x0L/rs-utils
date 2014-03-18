#!/usr/bin/env ruby

# Takes a Go PlayAlong XML file with synchronization data and Guitar Pro tab
# and produces Rocksmith 2014 XML tracks.

# Put sync points on signature change ! Use expand repeats !
# Section are markers
# Phrase are double bars
# Anchors are determined by fingering
# Copyright => Year
# AlbumArt =>
# Tones => Note.text defines tone name and tone change
# base tone is 'ToneBase'
# cent offset ??

require 'rexml/document'
require 'interpolator'
require 'guitar_pro_parser'
require 'gyoku'
require 'matrix'

# To be removed since it already exists in master for guitar_pro_parser
def GuitarProHelper.note_to_digit(note)
  result = 0
  result += 1 until GuitarProHelper.digit_to_note(result) == note
  result
end

## HELPERS

TONEBASE = 'ToneBase'

def time_interpolator(sync)
  s = sync.split '#'
  s.shift

  t = s.map { |u| u.split ';' }

  m = t.map do |time, bar, bar_fraction, beat_duration|
    { bar.to_f + bar_fraction.to_f => time.to_f / 1000.0 }
  end

  Interpolator::Table.new m.reduce Hash.new, :merge
end

I_DURATIONS = GuitarProHelper::DURATIONS.invert

STANDARD_TUNING = %w(E3 A3 D4 G4 B4 E5).map do |n|
  GuitarProHelper.note_to_digit(n)
end

def sortable_name(n)
  n.sub(/^(the|a|an)\s+/i, '').capitalize
end

# Counted arrays
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

## MAIN STUFF

# TODO: add time offset ?
# Build notes and chords, mostly effects
# anchors
# handshapes
# chord templates
# fingering
# arrangement properties
# section played number
# alternate endings ?

class SngXmlBuilder
  def initialize(song, track, timefun)
    @song = song
    @track = track
    @timerinter = timefun

    @internal_name = @song.artist.gsub(/[^0-9a-z]/i, '') + '_'
    @internal_name += @song.title.gsub(/[^0-9a-z]/i, '')

    @signature = 4.0 # 4/4 default signature

    @notes = []
    @chords = []
    @ebeats = []
    @sections = []
    @tones = []
    @tone_map = [TONEBASE]

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
        :@phraseId => 0,
        :@variation => ''
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
        :@chordId => 0,
        :@endTime => 5.728,
        :@startTime => 5.672
      }
    ]
  end

  def fraction_of_bar(duration)
    # this name is a bit confusing
    1.0 / (2**Integer(I_DURATIONS[duration])) / @signature
  end

  def bar2time(barfraction)
    t = @timerinter.read(barfraction)
    (t * 1000).round / 1000.0
  end

  def new_note(string, note)
    bb = []
    if note.bend
      note.bend[:points].each do |b|
        bb << {
          :@time => @time + b[:time] / 1000.0,
          :@step => b[:pitch_alteration] / 100.0
        } # unless b[:time] == 0 and b[:pitch_alteration] == 0
      end
    end

    if note.slide
    end

    if note.hammer_or_pull
    end

    if note.grace
    end

    # sustain
    # hammer / pull / hopo
    # slides

    n = {
      :@time => @time,
      # :@linkNext => 0,
      :@accent => note.accentuated ? 1 : 0,
      :@bend => bb.count > 0 ? 1 : 0,
      :@fret => note.fret,
      # :@hammerOn => 0,
      :@harmonic => note.harmonic != :none ? 1 : 0, # note.harmonic != :pinch
      # :@hopo => 0,
      :@ignore => 0,
      :@leftHand => -1,
      :@mute => note.type == :dead ? 1 : 0,
      :@palmMute => note.palm_mute ? 1 : 0,
      :@pluck => -1,
      # :@pullOff => 0,
      :@slap => -1,
      # :@slideTo => -1,
      :@string => string,
      # :@sustain => 1.130,
      :@tremolo => note.tremolo ? 1 : 0,
      :@harmonicPinch => note.harmonic == :pinch ? 1 : 0,
      :@pickDirection => 0,
      :@rightHand => -1,
      # :@slideUnpitchTo => -1,
      :@tap => 0,
      :@vibrato => 0,
      :bendValues => carray(:bendValue, bb)
    }
    n
  end

  def new_chord(notes)
    # TODO: bendValues
    notes.each { |n| n.delete(:bendValues) }

    {
      :@time => @time,
      # :@linkNext => 0,
      :@accent => (notes.any? { |n| n[:@accent] == 1 }) ? 1 : 0,
      # :@chordId => 12,
      # :@fretHandMute => 0,
      # :@highDensity => 0, # criterion needed here
      :@ignore => notes.any? { |n| n[:@ignore] == 1 } ? 1 : 0,
      :@palmMute => notes.all? { |n| n[:@palmMute] == 1 } ? 1 : 0,
      :@hopo => notes.any? { |n| n[:@hopo] == 1 } ? 1 : 0,
      # :@strum => "down", # in the beat actually
      :chordNote => notes
    }
  end

  def new_bar(bar_settings)
    if bar_settings.new_time_signature
      s = bar_settings.new_time_signature
      @signature = 4.0 * s[:numerator] / s[:denominator]
    end

    @start_reapeat_bar = @bar_idx if bar_settings.has_start_of_repeat

    @sections << {
      :@name => bar_settings.marker[:name],
      :@number => @sections.count + 1,
      :@startTime => bar2time(@measure)
    } if bar_settings.marker

    @ebeats << {
      :@time => bar2time(@measure),
      :@measure => (@measure + 1).to_i
    }
    1.upto(@signature - 1).each do |i|
      @ebeats << {
        :@time => bar2time(@measure + i / @signature),
        :@measure => -1
      }
    end
  end

  def new_tone_change(tone_name)
    idx = @tone_map.index(tone_name)
    unless idx
      idx = @tone_map.count
      @tone_map << tone_name
    end

    @tones << {
      :@id => idx,
      :@time => @time
    }
  end

  def new_gp_beat(beat)
    new_tone_change beat.text if beat.text

    ns = beat.strings.map do |string, note|
      string = @track.strings.count - string.to_i
      new_note string, note
    end
    @notes << ns[0] if ns.count == 1
    @chords << new_chord(ns) if ns.count > 1

    @previous_notes = ns
  end

  def run
    @measure = 0.0
    @bar_idx = 0 # to handle repeats

    u = @track.bars.zip(@song.bars_settings)
    while @bar_idx < u.count
      bar, bar_settings = u[@bar_idx]
      new_bar bar_settings

      measure_fraction = 0.0
      bar.voices[:lead].each do |beat|
        @time = bar2time(@measure + measure_fraction)

        new_gp_beat beat

        measure_fraction += fraction_of_bar(beat.duration)
      end

      if bar_settings.has_end_of_repeat
        @repeats_count = bar_settings.repeats_count unless @repeats_count
      end

      if bar_settings.has_end_of_repeat && @repeats_count > 0
        @bar_idx = @start_reapeat_bar - 1
        @repeats_count -= 1
      elsif bar_settings.has_end_of_repeat && @repeats_count == 0
        @repeats_count = nil
        @start_reapeat_bar = nil
      end

      @bar_idx += 1
      @measure += 1.0
    end
  end

  def xml
    {
      :@version       => 8,
      :title          => @song.title,
      :arrangement    => @track.name,
      :wavefilepath   => '',
      :part           => 1,
      :offset         => -10.000,
      :centOffset     => 0,
      :songLength     => 0.000,
      :internalName   => @internal_name,
      :songNameSort   => sortable_name(@song.title),
      :startBeat      => 0.000,
      :averageTempo   => @song.bpm,
      :tuning         => compute_tuning(@track.strings),
      :capo           => @track.capo,
      :artistName     => @song.artist,
      :artistNameSort => sortable_name(@song.artist),
      :albumName      => @song.album,
      :albumNameSort  => sortable_name(@song.album),
      :albumYear      => @song.copyright.to_i,
      :albumArt       => '',
      :crowdSpeed     => 1,
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

      :tone__A => @tone_map.count > 1 ? @tone_map[1] : '',
      :tone__B => @tone_map.count > 2 ? @tone_map[2] : '',
      :tone__C => @tone_map.count > 3 ? @tone_map[3] : '',
      :tone__D => @tone_map.count > 4 ? @tone_map[4] : '',
      :tone__Base => '', # TODO: default values
      :tone__Multiplayer => '',
      :tones => carray(:tone, @tones),

      :phrases => carray(:phrase, @phrases),
      :phraseIterations => carray(:phraseIteration, @phrase_iterations),
      :newLinkedDiffs => carray(:newLinkedDiff, []),
      :linkedDiffs => carray(:linkedDiff, []),
      :phraseProperties => carray(:phrase, []),
      :chordTemplates => carray(:chordTemplate, @chord_templates),
      :fretHandMuteTemplates => carray(:fretHandMuteTemplate, []),
      :ebeats => carray(:ebeat, @ebeats),
      :sections => carray(:section, @sections),
      :events => carray(:event, @events),

      :transcriptionTrack => { :@difficulty => -1 },

      :levels => carray(:level, [
        {
          :@difficulty => 0,
          :notes => carray(:note, @notes),
          :chords => carray(:chord, @chords),
          :fretHandMutes => carray(:fretHandMute, @fret_hand_mutes),
          :anchors => carray(:anchor, @anchors),
          :handShapes => carray(:handShape, @hand_shapes)
        }
      ])
    }
  end
end

## SCRIPT
debug = 1 unless ARGV[0]
ARGV[0] = '../test/tab.xml' unless ARGV[0]

ARGV[0] = File.realpath ARGV[0]
dir = File.dirname ARGV[0]

gpa_xml = REXML::Document.new File.new(ARGV[0], 'r')
score_url = gpa_xml.elements['track'].elements['scoreUrl'].text
# mp3_url = gpa_xml.elements['track'].elements['mp3Url'].text
sync = gpa_xml.elements['track'].elements['sync'].text

# TODO: if no sync data use bpm
tabsong = GuitarProParser.read_file(dir + File::SEPARATOR + score_url)

tabsong.tracks[0, 1].each do |track|
  builder = SngXmlBuilder.new tabsong, track, time_interpolator(sync)
  builder.run
  puts Gyoku.xml :song => builder.xml unless debug == 1
end
