rs-utils
========
A collection of scripts to deal with Rocksmith 2014.

Usage
-----
  * `psarc.py` packs, unpacks and converts PSARC files (Windows and OSX only)
  * `xml2sng.py` compiles Rocksmith XML to binary SNG and generates
    JSON manifests
  * `hsan.py` generates HSAN db from a collection of JSON manifests
  * `xgraph.py` generates the graph file for a package
  * `wav2wem` converts WAV to Wwise WEM
  * `wem2bnk` generates BNK files from WEM files
  * `img2dds` automatically generates DDS files from an image
  * `tones.py` extracts tones JSON from profiles and PSARCs

Setup
-----
To install Wwise authoring tools on OSX with Wine, we'll use `winetricks`.
Start by downloading `Authoring_Win32.msi` and `Authoring_Data.msi` from
[Audiokinetic](https://www.audiokinetic.com/downloads/). Then:

```sh
brew install wine winetricks
winetricks dotnet35sp1 dotnet40 vcrun2008 vcrun2010
wine msiexec /i Authoring_Win32.msi
wine msiexec /i Authoring_Data.msi
```

Install the python dependencies with

```sh
pip install -r requirements.txt
```

TODO
----
Core functionalities are now almost equivalent to the RocksmithToolkit (with no
console support though).

* Lyrics support needs more a bit more work (JSON, HSAN)

* Build a proper package generator

* Next big step is to generate RS xml source files from a Guitar Pro tab synched
using Go Play Along. I first thought of extracting code from EoF but I guess
it'll be too painful. Current idea is to use Ruby for this one,
see https://github.com/ImmaculatePine/guitar_pro_parser

* Proper Windows testing and integration (I can't do that as I don't have win)
