rs-utils
========
A collection of scripts to deal with Rocksmith 2014.

Usage
-----
  * `hsan.py` generates a HSAN database from a collection of JSON manifests
  * `img2dds` DDS generation for album artwork
  * `psarc.py` packs, unpacks and converts PSARC files (Windows and OSX only)
  * `tones.py` extracts tones JSON from profiles and PSARC packages
  * `wav2wem` WAV audio to Wwise WEM
  * `wem2bnk` generates BNK files from WEM files
  * `xgraph.py` generates the aggregated graph file for a package
  * `xml2sng.py` RS XML to binary SNG and JSON manifests

Setup
-----
To install Wwise authoring tools on OSX with Wine, we'll use [Homebrew](http://brew.sh/).

Download `Authoring_Win32.msi` and `Authoring_Data.msi` from
[Audiokinetic](https://www.audiokinetic.com/downloads/)
```sh
brew install wine winetricks
winetricks dotnet35sp1 dotnet40 vcrun2008 vcrun2010
wine msiexec /i Authoring_Win32.msi
wine msiexec /i Authoring_Data.msi
```

Install the Python dependencies with
```sh
pip install -r requirements.txt
```

Install the Ruby dependencies with
```sh
gem install bundle
bundle install
```

TODO
----
* Tones and lyrics need more a bit more work (JSON, HSAN)
* Next milestone will be to have a working GP -> XML conversion tool (gp2xml.rb)
* Build a proper package generator
* Better Windows integration: `.bat` instead of `sh` scripts
