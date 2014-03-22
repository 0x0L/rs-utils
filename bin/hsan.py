import json

HSAN_KEYS = [
    'AlbumArt', 'AlbumName', 'AlbumNameSort', 'ArrangementName', 'ArtistName',
    'ArtistNameSort', 'CentOffset', 'DLC', 'DLCKey', 'DNA_Chords', 'DNA_Riffs',
    'DNA_Solo', 'EasyMastery', 'LeaderboardChallengeRating', 'ManifestUrn',
    'MasterID_RDV', 'MediumMastery', 'NotesEasy', 'NotesHard', 'NotesMedium',
    'PersistentID', 'SKU', 'Shipping', 'SongDiffEasy', 'SongDiffHard',
    'SongDiffMed', 'SongDifficulty', 'SongKey', 'SongLength', 'SongName',
    'SongNameSort', 'SongYear', 'Tuning'
]

# TODO use json2xml instead of ugly templates
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


def hsan(manifests):
    """Returns .hsan, .xblock"""

    hsan_db = {}
    hsan_db['Entries'] = {}
    hsan_db['InsertRoot'] = 'Static.Songs.Headers'

    xblock = '<?xml version="1.0" encoding="utf-8"?>\n'
    xblock += '<game>\n'
    xblock += '  <entitySet>'

    name = ''

    for manifest in manifests:
        for persistent_id, e in manifest['Entries'].iteritems():
            entry = e['Attributes']

            entry['name'] = entry['DLCKey'].lower()
            entry['persistent_id'] = entry['PersistentID'].lower()

            xblock += XBLOCK_TEMPLATE % entry

            hsan_entry = {}
            for k in HSAN_KEYS:
                if k in entry:
                    hsan_entry[k] = entry[k]

            if 'ArrangementProperties' in entry:
                prop = entry['ArrangementProperties']
                hsan_entry['RouteMask'] = prop['routeMask']
                hsan_entry['Representative'] = prop['represent']

            hsan_db['Entries'][persistent_id] = {'Attributes': hsan_entry}

            name = entry['name']

    xblock += '\n  </entitySet>\n'
    xblock += '</game>'

    return json.dumps(hsan_db, indent=4, sort_keys=True), xblock
