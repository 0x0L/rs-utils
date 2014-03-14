#!/usr/bin/env python

"""
Generate xblock and HSAN db from a collection of JSON files

Usage: hsan.py FILES...
"""

import json

keys = [
    'AlbumArt',
    'AlbumName',
    'AlbumNameSort',
    'ArrangementName',
    'ArtistName',
    'ArtistNameSort',
    'CentOffset',
    'DLC',
    'DLCKey',
    'DNA_Chords',
    'DNA_Riffs',
    'DNA_Solo',
    'EasyMastery',
    'LeaderboardChallengeRating',
    'ManifestUrn',
    'MasterID_RDV',
    'MediumMastery',
    'NotesEasy',
    'NotesHard',
    'NotesMedium',
    'PersistentID',
    'SKU',
    'Shipping',
    'SongDiffEasy',
    'SongDiffHard',
    'SongDiffMed',
    'SongDifficulty',
    'SongKey',
    'SongLength',
    'SongName',
    'SongNameSort',
    'SongYear',
    'Tuning'
]

xblock_template = """
    <entity id="%(entry_id)s" modelName="RSEnumerable_Song" name="%(internalName)s_%(arrangement)s" iterations="0">
      <properties>
        <property name="Header">
          <set value="urn:database:hsan-db:songs_dlc_%(internal_name)s" />
        </property>
        <property name="Manifest">
          <set value="urn:database:json-db:%(internal_name)s_%(arrangement_name)s" />
        </property>
        <property name="SngAsset">
          <set value="urn:application:musicgame-song:%(internal_name)s_%(arrangement_name)s" />
        </property>
        <property name="AlbumArtSmall">
          <set value="urn:image:dds:album_%(internal_name)s_64" />
        </property>
        <property name="AlbumArtMedium">
          <set value="urn:image:dds:album_%(internal_name)s_128" />
        </property>
        <property name="AlbumArtLarge">
          <set value="urn:image:dds:album_%(internal_name)s_256" />
        </property>
        <property name="LyricArt">
          <set value="" />
        </property>
        <property name="ShowLightsXMLAsset">
          <set value="urn:application:xml:%(internal_name)s_showlights" />
        </property>
        <property name="SoundBank">
          <set value="urn:audio:wwise-sound-bank:song_%(internal_name)s" />
        </property>
        <property name="PreviewSoundBank">
          <set value="urn:audio:wwise-sound-bank:song_%(internal_name)s_preview" />
        </property>
      </properties>
    </entity>"""


if __name__ == '__main__':
    from docopt import docopt

    args = docopt(__doc__)

    output = {}
    output['Entries'] = {}
    output['InsertRoot'] = 'Static.Songs.Headers'

    xblock = '<?xml version="1.0" encoding="utf-8"?>\n'
    xblock += '<game>\n'
    xblock += '  <entitySet>'

    name = ''

    for f in args['FILES']:
        print 'Processing', f

        with open(f, 'r') as fstream:
            o = json.loads(fstream.read())
            id = o['Entries'].keys()[0]

            u = o['Entries'][id]['Attributes']
            a = {}
            a['RouteMask'] = u['ArrangementProperties']['RouteMask']
            a['Representative'] = u['ArrangementProperties']['represent']
            for k in keys:
                a[k] = u[k]

            dict = {
                'entry_id': id.lower(),
                'internal_name': u['BlockAsset'][19:],
                'internalName': u['DLCKey'],
                'arrangement': u['ArrangementName'],
                'arrangement_name': u['ArrangementName'].lower()
            }
            name = dict['internal_name']
            xblock += xblock_template % dict

            u = a

            output['Entries'][id] = {}
            output['Entries'][id]['Attributes'] = a

    xblock += '\n  </entitySet>\n'
    xblock += '</game>'

    with open('songs_dlc_' + name + '.hsan', 'w') as fstream:
      fstream.write(json.dumps(output, indent=4, sort_keys=True))
    with open(name + '.xblock', 'w') as fstream:
      fstream.write(xblock)
