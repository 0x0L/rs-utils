rs-utils
========

A collection of Python scripts for Rocksmith 2014.


Usage
-----

  * `psarc.py` pack, unpack and convert PSARC
  * `tones.py` extract tones from profile and PSARC
  * `wav2wem` convert WAV to Wwise WEM

Tools can be used with multiple inputs or wildcards. Examples:
```sh
bin/psarc.py convert /path/to/dlc/*_p.psarc
bin/tones.py /path/to/dlc/*.psarc > tone_library.json
```


Setup
-----

* Install the Python dependencies with

    ```sh
    pip install -r requirements.txt
    ```

* To install Wwise authoring tools on OSX with Wine, we'll use [Homebrew](http://brew.sh/).

    Download `Authoring_Win32.msi` and `Authoring_Data.msi` from
    [Audiokinetic](https://www.audiokinetic.com/downloads/)

    ```sh
    brew install wine winetricks
    winetricks dotnet35sp1 dotnet40 vcrun2008 vcrun2010
    wine msiexec /i Authoring_Win32.msi
    wine msiexec /i Authoring_Data.msi
    ```

    In `bin/WwiseCLI`, make sure the version in the path matches the version installed on your machine.
