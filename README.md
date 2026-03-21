# aru_metadata_parser
Parse audio file metadata from common ARUs including the AudioMoth

This package aims to provide support for parsing metadata from common ARU (autonomous recording unit) audio files. Currently, AudioMoth metadata from firmware versions up to 1.8.1 are supported.

Please use Issues to report failures in metadata parsing, and to request parsing for other metadata formats. 
r
## Installation:

The package is available on PyPI and can be installed with PIP: 

`pip install aru_metadata_parser`

## Usage

### Parse start time from any ARU filename

The top-level `parse_aru_file_start_time` function supports AudioMoth, Song Meter, OwlSense, and Swift recorders. If no `recorder_type` is specified, it tries all known formats automatically before falling back to fuzzy date parsing.

If you find an ARU file name pattern that does not work, please open an issue with an example of the naming pattern and how file names are generated (eg what hardware or software).

```python
from aru_metadata_parser import parse

# Auto-detect recorder type
dt = parse.parse_aru_file_start_time("SMM03873_20220719_000000.wav")

# Specify recorder type explicitly
dt = parse.parse_aru_file_start_time(
    "SMM03873_20220719_000000.wav",
    recorder_type="songmeter",         # one of: 'audiomoth', 'songmeter', 'owlsense', 'swift'
    filename_timezone="US/Eastern",    # timezone the recorder used when naming the file
    output_timezone="UTC",             # convert result to this timezone
)
```

### Recorder-specific parsing

**AudioMoth** — supports both hex filenames (old firmware) and human-readable filenames (new firmware):

```python
# New firmware (human-readable)
dt = parse.audiomoth_start_time("20200404_102500.WAV")

# With timezone info
dt = parse.audiomoth_start_time("20200404_102500.WAV", filename_timezone="UTC", output_timezone="US/Eastern")

# Old firmware (hexadecimal filename, always UTC)
dt = parse.audiomoth_start_time("5E886A48.WAV", filename_timezone="UTC")
```

**Song Meter** (SM2/3/4, Mini, Micro) — filename pattern: `SMM03873_20220719_000000.wav`:

```python
dt = parse.songmeter_start_time("SMM03873_20220719_000000.wav")
dt = parse.songmeter_start_time("SMM03873_20220719_000000.wav", filename_timezone="US/Eastern", output_timezone="UTC")
```

**OwlSense** — filename pattern: `OWL_123456_2022-07-19_T00-00-00.WAV`:

```python
dt = parse.owlsense_start_time("OWL_123456_2022-07-19_T00-00-00.WAV")
dt = parse.owlsense_start_time("OWL_123456_2022-07-19_T00-00-00.WAV", filename_timezone="UTC", output_timezone="US/Eastern")
```

**Swift** — filename pattern: `SwiftOne_20220719_000000_-0400.wav` (UTC offset embedded in filename):

```python
dt = parse.swift_start_time("SwiftOne_20220719_000000_-0400.wav")
dt = parse.swift_start_time("SwiftOne_20220719_000000_-0400.wav", output_timezone="UTC")
```

### Parse AudioMoth WAV file metadata

Reads and parses metadata from the WAV header of an AudioMoth recording. Returns a dictionary with keys including `gain_setting`, `battery_state`, `recording_start_time`, `device_id`, and (for firmware >=1.4.0) `temperature_C`:

```python
# From a file path
metadata = parse.parse_audiomoth_metadata_from_path("audiomoth_recording.WAV")
print(metadata["gain_setting"])        # e.g. 'medium' or 2
print(metadata["battery_state"])       # e.g. 4.7 (volts)
print(metadata["recording_start_time"])  # localized datetime
print(metadata["temperature_C"])       # e.g. 11.2

# From an already-loaded metadata dictionary
metadata = parse.parse_audiomoth_metadata(metadata_dict)
```

### Timezone handling

- `filename_timezone`: the timezone the recorder used when constructing its filename (e.g. `"UTC"`, `"US/Eastern"`). If `None`, returns a naive datetime object.
- `output_timezone`: timezone to convert the result to. Requires `filename_timezone` to be set (except for Swift, which embeds UTC offset in the filename).
- Timezone strings must be valid [pytz](https://pythonhosted.org/pytz/) timezone names (see `pytz.all_timezones`).

## Contribution:

We use Poetry for development, with `black` formatting and `pytest` testing. Contributions to the code base are welcome. 

## License and attribution:

This package is provided under the MIT Open-source license.

Suggested citation:

```
Lapp, Syunkova, and Kitzes, 2023. ARU Metadata Parser v0.1.0. github.com/kitzeslab/aru_metadata_parser. 
```

