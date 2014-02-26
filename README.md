rs-utils
========
A collection of scripts to deal with Rocksmith 2014 resources on OSX.

Usage
-----
In `WwiseCLI` adjust the path to point to your Wwise install.

  * `psarc.py` pack, unpack and convert PSARC files (PC and Mac)
  * `xml2sng.py` compile Rocksmith XML (from EoF) to binary SNG
  * `wav2wem` automated convertion using Wwise CLI (see note above)
  * `wem2bnk` create BNK files from WEM files
  * `img2dds` generate DDS files from an image


Requirements
------------
Install the python dependencies with

      pip install -r requirements.txt

To install Wwise with Wine, use `winetricks`

      brew install wine winetricks
      winetricks dotnet35sp1 dotnet40 vcrun2008 vcrun2010
