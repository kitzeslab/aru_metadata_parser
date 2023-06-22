# aru_metadata_parser
Parse audio file metadata from common ARUs including the AudioMoth

This package aims to provide support for parsing metadata from common ARU (autonomous recording unit) audio files. Currently, AudioMoth metadata from firmware versions up to 0.8.1 are supported. 

Please use Issues to report failures in metadata parsing, and to request parsing for other metadata formats. 
r
## Installation:

The package is available on PyPI and can be installed with PIP: 

`pip install aru_metadata_parser`

## Usage

Parses metadata from audio files recorded by AudioMoth, storing metadata as a dictionary:

```
from aru_metadata_parser import parse
metadata_dictionary = parse.parse_audiomoth_metadata_from_path("audiomoth_recording.WAV")
```



Parses audiomoth filenames into datetimes (including hexidecimal names created by early AudioMoth firmware versions). This function assumes the time is provided in UTC unless otherwise specified

```
parse.audiomoth_start_time("/path/20200404_102500.WAV") #returns datetime object
```

If the file name corresponds to another time zone, we can specify which time zone it refers to:

```
parse.audiomoth_start_time("20200404_102500.WAV",filename_timezone="US/Eastern")
```

## Contribution:

We use Poetry for development, with `black` formatting and `pytest` testing. Contributions to the code base are welcome. 

## License and attribution:

This package is provided under the MIT Open-source license.

Suggested citation:

```
Lapp, Syunkova, and Kitzes, 2023. ARU Metadata Parser v0.1.0. github.com/kitzeslab/aru_metadata_parser. 
```

