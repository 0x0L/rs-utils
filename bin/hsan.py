#!/usr/bin/env python

"""
Generate xblock and HSAN db from a collection of JSON files

Usage: hsan.py FILES...
"""

import json

HSAN_KEYS = [
    'AlbumArt', 'AlbumName', 'AlbumNameSort', 'ArrangementName', 'ArtistName',
    'ArtistNameSort', 'CentOffset', 'DLC', 'DLCKey', 'DNA_Chords', 'DNA_Riffs',
    'DNA_Solo', 'EasyMastery', 'LeaderboardChallengeRating', 'ManifestUrn',
    'MasterID_RDV', 'MediumMastery', 'NotesEasy',  'NotesHard', 'NotesMedium',
    'PersistentID', 'SKU', 'Shipping', 'SongDiffEasy', 'SongDiffHard',
    'SongDiffMed', 'SongDifficulty', 'SongKey', 'SongLength', 'SongName',
    'SongNameSort', 'SongYear', 'Tuning'
]

XBLOCK_TEMPLATE = """
    <entity id="%(persistent_id)s" modelName="RSEnumerable_Song" name="%(SongKey)s" iterations="0">
      <properties>
        <property name="Header">
          <set value="urn:database:hsan-db:songs_dlc_%(name)s" />
        </property>
        <property name="Manifest">
          <set value="%(ManifestUrn)s" />
        </property>
        <property name="SngAsset">
          <set value="%(SongAsset)s" />
        </property>
        <property name="AlbumArtSmall">
          <set value="%(AlbumArt)s_64" />
        </property>
        <property name="AlbumArtMedium">
          <set value="%(AlbumArt)s_128" />
        </property>
        <property name="AlbumArtLarge">
          <set value="%(AlbumArt)s_256" />
        </property>
        <property name="LyricArt">
          <set value="" />
        </property>
        <property name="ShowLightsXMLAsset">
          <set value="%(ShowlightsXML)s" />
        </property>
        <property name="SoundBank">
          <set value="urn:audio:wwise-sound-bank:song_%(name)s" />
        </property>
        <property name="PreviewSoundBank">
          <set value="urn:audio:wwise-sound-bank:song_%(name)s_preview" />
        </property>
      </properties>
    </entity>"""


if __name__ == '__main__':
    from docopt import docopt

    args = docopt(__doc__)

    hsan_db = {}
    hsan_db['Entries'] = {}
    hsan_db['InsertRoot'] = 'Static.Songs.Headers'

    xblock = '<?xml version="1.0" encoding="utf-8"?>\n'
    xblock += '<game>\n'
    xblock += '  <entitySet>'

    name = ''

    for f in args['FILES']:
        print 'Processing', f

        with open(f, 'r') as stream:
            manifest = json.loads(stream.read())
            for persistent_id, e in manifest['Entries']:
                entry = e['Attributes']

                entry['name'] = e['internalName'].lower()
                entry['persistent_id'] = e['PersistentID'].lower()

                xblock += XBLOCK_TEMPLATE % entry

                hsan_entry = {}
                for k in HSAN_KEYS:
                    hsan_entry[k] = entry[k]

                prop = entry['ArrangementProperties']
                hsan_entry['RouteMask'] = prop['routeMask']
                hsan_entry['Representative'] = prop['represent']

                hsan_db['Entries'][persistent_id] = {'Attributes': hsan_entry}

                name = entry['name']

    xblock += '\n  </entitySet>\n'
    xblock += '</game>'

    with open('songs_dlc_' + name + '.hsan', 'w') as stream:
        stream.write(json.dumps(hsan_db, indent=4, sort_keys=True))

    with open(name + '.xblock', 'w') as stream:
        stream.write(xblock)
