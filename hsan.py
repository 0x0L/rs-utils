#!/usr/bin/env python

"""
Generate HSAN db from a collection of JSON files

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

if __name__ == '__main__':
    from docopt import docopt
    import sngparser
    import os

    args = docopt(__doc__)

    output = {}
    output['Entries'] = {}

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
            u = a

            output['Entries'][id] = {}
            output['Entries'][id]['Attributes'] = a

    print json.dumps(output, indent=4, sort_keys=True)
