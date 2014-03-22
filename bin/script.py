import shutil
import os
import json
import subprocess
import tarfile

from gpa2xml import load_goplayalong, SngBuilder
from wem2bnk import BnkGenerator
import xmlhelpers
import hsan
import xml2sng
import xgraph

d1 = '../test/'
f = d1 + 'tab.xml'

gp, mp3, sync = load_goplayalong(f)

internalName = filter(str.isalnum, gp.Score.Artist)
internalName += filter(str.isalnum, gp.Score.Title)

internal_name = internalName.lower()

d = '../test/pack3/' + internal_name + '_m/'

try:
    os.makedirs(d + 'audio/mac/')
    os.makedirs(d + 'flatmodels/rs/')
    os.makedirs(d + 'gamexblocks/nsongs/')
    os.makedirs(d + 'gfxassets/album_art/')
    os.makedirs(d + 'manifests/songs_dlc_' + internal_name + '/')
    os.makedirs(d + 'songs/arr/')
    os.makedirs(d + 'songs/bin/macos/')
except:
    pass

with open(d + 'appid.appid', 'w') as appid:
    appid.write('248750')

shutil.copyfile('../share/rsenumerable_root.flat', d + 'flatmodels/rs/rsenumerable_root.flat')
shutil.copyfile('../share/rsenumerable_song.flat', d + 'flatmodels/rs/rsenumerable_song.flat')
shutil.copyfile('../share/showlights.xml', d + 'songs/arr/' + internal_name + '_showlights.xml')

i = d1 + 'tab.jpg'
for s in [64, 128, 256]:
    output = d + 'gfxassets/album_art/album_' + internal_name + '_' + str(s) + '.dds'
    subprocess.call(['wine', '../share/nvdxt.exe',
                     '-file', i,
                     '-output', output,
                     '-prescale', str(s), str(s),
                     '-nomipmap', '-RescaleBox', '-dxt1a'])

SILENCE = 10
OFFSET_PREVIEW = 20

audio_dir = d + 'audio/mac/'

def extractTar(d):
    with tarfile.open('../share/Wwise_Template.tar.gz', 'r:gz') as tfile:
        tfile.extractall(d)

def runWwise(d):
    p = subprocess.Popen(['/Users/xav/Projects/Rocksmith2014/utils/bin/WwiseCLI',
                      'Template.wproj', '-GenerateSoundBanks'],
                       cwd=d)
    p.wait()

def getWEM(d, name, preview=False):
    u = d + 'Wwise_Template/.cache/Windows/SFX/'
    for x in os.listdir(u):
        if x.endswith(".wem"):
            wem = BnkGenerator(u + x, preview)
            fileid, bnk = wem.build_bnk(name)

            fn = d + 'song_' + name.lower()
            if preview:
                fn += '_preview'

            with open(fn + '.bnk', 'wb') as bnkfile:
                bnkfile.write(bnk)

            shutil.copy(u + x, d + str(fileid) + '.wem')
            break

f = audio_dir + 'Wwise_Template/Originals/SFX/SONG.wav'

extractTar(audio_dir)
subprocess.call(['ffmpeg', '-i', d1 + mp3, '-filter_complex',
                 'aevalsrc=0:d=' + str(SILENCE) + '[slug];[slug][0]concat=n=2:v=0:a=1[out]',
                 '-map', "['out']", f])

runWwise(audio_dir + 'Wwise_Template')
getWEM(audio_dir, internalName)
shutil.rmtree(audio_dir + 'Wwise_Template/')

extractTar(audio_dir)
subprocess.call(['ffmpeg', '-i', d1 + mp3, '-ss', str(OFFSET_PREVIEW), '-t', '30', f])
runWwise(audio_dir + 'Wwise_Template')
getWEM(audio_dir, internalName + '_preview')
shutil.rmtree(audio_dir + 'Wwise_Template/')



gpa = SngBuilder(gp, gp.Tracks[0], sync)
x = xmlhelpers.json2xml('song', gpa.run())
z = xml2sng.compile_xml(x)

urns = [z[0]]
manifests = [z[1]]
sngs = [z[2]]

hsandb, xblock = hsan.hsan(manifests)

for urn, sng in zip(urns, sngs):
    u = d + 'songs/bin/macos/'
    with open(u + urn + '.sng', 'wb') as s:
        s.write(sng)

u = d + 'manifests/songs_dlc_' + internal_name + '/'
for urn, manifest in zip(urns, manifests):
    with open(u + urn + '.json', 'w') as s:
        s.write(json.dumps(manifest, indent=2, sort_keys=True))

with open(u + 'songs_dlc_' + internal_name + '.hsan', 'w') as s:
    s.write(hsandb)

u = d + 'gamexblocks/nsongs/' + internal_name + '.xblock'
with open(u, 'w') as s:
    s.write(xblock)


with open(d + internal_name + '_aggregategraph.nt', 'w') as s:
    s.write(xgraph.run(d))