"""Utilities specifically for audio files recoreded by AudioMoths and other ARUs"""

from pathlib import Path
from datetime import datetime

import pytz
from aru_metadata_parser.utils import hex_to_time, load_metadata
import warnings

from dateutil.parser import parse as dateutil_parse
from dateutil.parser import ParserError


class ARUFileTimestampParser:
    """Parse start times from ARU filenames, caching the last successful strategy.

    When parsing thousands of files with the same naming convention, this avoids
    retrying earlier (failing) strategies on every call. The first successful
    strategy is tried first on all subsequent calls; if it fails the full list
    is tried as a fallback.

    Args:
        filename_timezone: (str) pytz timezone name for the recorder's clock.
            If None, returns naive datetime objects unless timezone is encoded in the file name
            (Does not override timezone if encoded in file name)
        output_timezone: (str) pytz timezone name to convert results to.
            Requires filename_timezone to be set.
            If None, returns timestamps in the timezone specified by
            `filename_timezone` or as encoded in the file name if available,
            otherwise returns naive datetime objects

    Example:
        parser = ARUFileTimestampParser(filename_timezone="UTC", output_timezone="US/Eastern")
        datetimes = [parser.parse(f) for f in files]
    """

    def __init__(self, filename_timezone=None, output_timezone=None):
        self.filename_timezone = filename_timezone
        self.output_timezone = output_timezone
        self._last_index = 0

    def _build_strategies(self, name, file):
        tz, otz = self.filename_timezone, self.output_timezone
        return [
            lambda: audiomoth_start_time(
                name, filename_timezone=tz, output_timezone=otz
            ),
            lambda: songmeter_start_time(
                name, filename_timezone=tz, output_timezone=otz
            ),
            lambda: owlsense_start_time(
                name, filename_timezone=tz, output_timezone=otz
            ),
            lambda: swift_start_time(name, output_timezone=otz),
            lambda: dateutil_parse(name.replace("_", " "), fuzzy=False),
            lambda: _parse_yyyymmdd_hhmmss_from_parts(name),
            lambda: _parse_yyyymmdd_hhmmss_from_parts(name, sep="-"),
            lambda: dateutil_parse(Path(file).stem, fuzzy=True),
            lambda: dateutil_parse("_".join(name.split("_")[-3:]), fuzzy=True),
            lambda: dateutil_parse("_".join(name.split("_")[-2:]), fuzzy=True),
        ]

    def parse(self, file):
        """Parse start time from an ARU filename.

        Args:
            file: (str) path or filename of an ARU recording
        Returns:
            datetime object
        """
        name = Path(file).stem
        all_strategies = self._build_strategies(name, file)
        indices = [self._last_index] + [
            i for i in range(len(all_strategies)) if i != self._last_index
        ]
        dt = None
        for i in indices:
            try:
                dt = all_strategies[i]()
                self._last_index = i
                break
            except (ParserError, ValueError):
                continue
        if dt is None:
            raise ValueError(
                f"could not parse start time from file name: {file} using any available strategy"
            )
        if self.filename_timezone is not None and dt.tzinfo is None:
            dt = pytz.timezone(self.filename_timezone).localize(dt)
        if self.output_timezone is not None:
            assert (
                dt.tzinfo is not None
            ), "dt must be timezone-aware to convert to output_timezone"
            dt = dt.astimezone(pytz.timezone(self.output_timezone))
        return dt


def parse_aru_file_start_time(
    file, recorder_type=None, filename_timezone=None, output_timezone=None
):
    """parse ARU file name into a time stamp

    Wrapper function to parse start time from various ARU recorder file names.

    If recorder_type is not provided, attempts to parse arbitrary file name
    containing date and time information. When parsing many files with the same
    naming convention, prefer ARUFileTimestampParser which caches the
    last successful strategy.

    Args:
        file: (str) path or file name from ARU recording
        recorder_type: (str) type of recorder. One of:
            'audiomoth', 'songmeter',  'owlsense', 'swift'
        filename_timezone: (str) name of a pytz time zone (for options see
            pytz.all_timezones). This is the time zone that the recorder
            uses to record its name, which may or may not be local to the recording
            site. If None, returns a naive datetime object.
            [only used for 'audiomoth', 'songmeter', and 'owlsense' recorder types]
        output_timezone: (str) name of a pytz time zone to convert the timestamp to.
            If None, returns timestamp in the timezone specified by `filename_timezone`
    Returns:
        datetime object
        - if filename_timezone is None, returns naive datetime object
        - if filename_timezone is provided, returns timezone-aware datetime object
          localized to `filename_timezone` or `output_timezone` if provided
    """
    if recorder_type is None:
        return ARUFileTimestampParser(
            filename_timezone=filename_timezone,
            output_timezone=output_timezone,
        ).parse(file)
    else:  # user specified recorder type
        name = Path(file).stem
        recorder_type = recorder_type.lower().strip()

        if recorder_type == "audiomoth":
            return audiomoth_start_time(
                name,
                filename_timezone=filename_timezone,
                output_timezone=output_timezone,
            )
        elif recorder_type == "songmeter":
            return songmeter_start_time(
                name,
                filename_timezone=filename_timezone,
                output_timezone=output_timezone,
            )
        elif recorder_type == "owlsense":
            return owlsense_start_time(
                name,
                filename_timezone=filename_timezone,
                output_timezone=output_timezone,
            )
        elif recorder_type == "swift":
            return swift_start_time(
                name,
                output_timezone=output_timezone,
            )
        else:
            raise ValueError(
                f"recorder_type {recorder_type} not recognized. must be one of: None, 'audiomoth', 'songmeter',  'owlsense', 'swift'"
            )


def _parse_yyyymmdd_hhmmss_from_parts(name, sep="_"):
    """scan underscore-split parts for a consecutive YYYYMMDD + HHMMSS pair"""
    parts = name.split(sep)
    for i in range(len(parts) - 1):
        a, b = parts[i], parts[i + 1]
        if len(a) == 8 and a.isnumeric() and len(b) == 6 and b.isnumeric():
            return datetime.strptime(f"{a}_{b}", "%Y%m%d_%H%M%S")
    raise ValueError(f"no YYYYMMDD_HHMMSS pair found in: {name}")


def swift_start_time(file, output_timezone=None):
    """parse Swift file name into a time stamp

    Swift recorders create their file name based on the time that recording starts.
    This function parses the name into a timestamp.

    Args:
        file: (str) path or file name from Swift recording
        output_timezone: (str) name of a pytz time zone to convert the timestamp to.
            If None, returns timestamp in the timezone specified by `filename_timezone`
    Returns:
        time-zone aware datetime object
    """
    # pattern: SwiftOne_YYYYMMDD_HHMMSS_-0400.wav
    # eg SwiftOne_20220719_000000_-0400.wav
    name = Path(file).stem
    trimmed_name = "_".join(name.split("_")[-3:])  # get last three parts
    file_datetime = datetime.strptime(trimmed_name, "%Y%m%d_%H%M%S_%z")
    if output_timezone is not None:
        file_datetime = file_datetime.astimezone(pytz.timezone(output_timezone))
    return file_datetime


def owlsense_start_time(file, filename_timezone=None, output_timezone=None):
    """parse OwlSense file name into a time stamp

    OwlSense recorders create their file name based on the time that recording starts.
    This function parses the name into a timestamp.

    Args:
        file: (str) path or file name from OwlSense recording
        filename_timezone: (str) name of a pytz time zone (for options see
            pytz.all_timezones). This is the time zone that the OwlSense
            uses to record its name, which may or may not be local to the recording
            site. If None, returns a naive datetime object.
        output_timezone: (str) name of a pytz time zone to convert the timestamp to.
            If None, returns timestamp in the timezone specified by `filename_timezone`
            Only supported if `filename_timezone` is not None.
    Returns:
        datetime object
        - if filename_timezone is None, returns naive datetime object
        - if filename_timezone is provided, returns timezone-aware datetime object
          localized to `filename_timezone` or `output_timezone` if provided
    """
    # pattern: <FILE_PREFIX>_<RECORDER_ID>_YYYY-MM-DD_THH-MM-SS.WAV
    # eg OWL_123456_2022-07-19_T00-00-00.WAV
    name = Path(file).stem
    trimmed_name = "_".join(name.split("_")[-2:])  # get last two parts
    file_datetime = datetime.strptime(trimmed_name, "%Y-%m-%d_T%H-%M-%S")
    if filename_timezone is not None:
        # convert the naive datetime into a localized datetime based on the
        # timezone provided by the user. (This is the time zone that the OwlSense
        # uses to record its name, not the time zone local to the recording site.)
        localized_dt = pytz.timezone(filename_timezone).localize(file_datetime)
        if output_timezone is not None:
            return localized_dt.astimezone(pytz.timezone(output_timezone))
        else:
            return localized_dt
    else:
        return file_datetime


def songmeter_start_time(file, filename_timezone=None, output_timezone=None):
    """parse songmeter file name into a time stamp

    Song Meter SM2/3/4, Mini, and Micro create their file name based on the time that recording starts.
    This function parses the name into a timestamp.

    Note: the SongMeter does not record the time zone of the recording, but
    uses the time zone in which the device was configured or localized when constructing
    the file name.

    The function asssumes that the file name is separated into parts by underscores,
    with the date and time in the last two parts, e.g.
    SMM03873_20220719_000000.wav or SBT-6-76-18_0+1_0_20160621_080000.wav

    Args:
        file: (str) path or file name from Song Meter recording
        filename_timezone: (str) name of a pytz time zone (for options see
            pytz.all_timezones). This is the time zone that the Song Meter
            uses to record its name, which may or may not be local to the recording
            site. If None, returns a naive datetime object.
        output_timezone: (str) name of a pytz time zone to convert the timestamp to.
            If None, returns timestamp in the timezone specified by `filename_timezone`
            Only supported if `filename_timezone` is not None.
    Returns:
        datetime object
        - if filename_timezone is None, returns naive datetime object
        - if filename_timezone is provided, returns timezone-aware datetime object
          localized to `filename_timezone` or `output_timezone` if provided
    """
    if (filename_timezone is None) and (output_timezone is not None):
        raise ValueError(
            "output_timezone can only be provided if filename_timezone is also provided"
        )
    # file name pattern: SMM03873_20220719_000000.wav or SBT-6-76-18_0+1_0_20160621_080000.wav
    name = Path(file).stem
    trimmed_name = name.split("_")[-2] + "_" + name.split("_")[-1]
    file_datetime = datetime.strptime(trimmed_name, "%Y%m%d_%H%M%S")
    if filename_timezone is not None:
        # convert the naive datetime into a localized datetime based on the
        # timezone provided by the user. (This is the time zone that the Song Meter
        # uses to record its name, not the time zone local to the recording site.)
        localized_dt = pytz.timezone(filename_timezone).localize(file_datetime)
        if output_timezone is not None:
            return localized_dt.astimezone(pytz.timezone(output_timezone))
        else:
            return localized_dt
    else:
        return file_datetime


def audiomoth_start_time(
    file, filename_timezone=None, to_utc=False, output_timezone=None
):
    """parse audiomoth file name into a time stamp

    AudioMoths create their file name based on the time that recording starts.
    This function parses the name into a timestamp. Older AudioMoth firmwares
    used a hexadecimal unix time format, while newer firmwares use a
    human-readable naming convention. This function handles both conventions.

    Args:
        file: (str) path or file name from AudioMoth recording
        filename_timezone: (str) name of a pytz time zone (for options see
            pytz.all_timezones). This is the time zone that the AudioMoth
            uses to record its name, not the time zone local to the recording
            site. Note: AudioMoth records file names in UTC unless configured otherwise,
            so you might want to pass "UTC" here.
            If None, returns a naive datetime object.
        to_utc: [deprecated] if True, converts timestamps to UTC localized time stamp.
            Otherwise, will return timestamp localized to `timezone` argument
            [default: False]
        output_timezone: (str) name of a pytz time zone to convert the timestamp to.
            If None, returns timestamp in the timezone specified by `filename_timezone`
    Returns:
        localized datetime object
        - if to_utc=True, datetime is always "localized" to UTC
    """
    name = Path(file).stem
    if len(name) == 8:
        # HEX filename convention (old firmware)
        if filename_timezone not in ("UTC", None):
            raise ValueError('hexadecimal file names must have filename_timezone="UTC"')
        file_datetime = hex_to_time(Path(file).stem)  # returns UTC localized dt
    elif len(name) == 15:
        # human-readable format (newer firmware)
        file_datetime = datetime.strptime(name, "%Y%m%d_%H%M%S")

        # convert the naive datetime into a localized datetime based on the
        # timezone provided by the user. (This is the time zone that the AudioMoth
        # uses to record its name, not the time zone local to the recording site.)
        if filename_timezone is not None:
            file_datetime = pytz.timezone(filename_timezone).localize(file_datetime)

    else:
        raise ValueError(f"file had unsupported name format: {name}")

    if to_utc:
        warnings.warn(
            "`to_utc` argument is deprecated. please use `output_timezone='UTC'` instead.",
            DeprecationWarning,
        )
        output_timezone = "UTC"

    if output_timezone is not None:
        assert (
            file_datetime.tzinfo is not None
        ), "file_datetime must be timezone-aware to convert to output_timezone"
        return file_datetime.astimezone(pytz.timezone(output_timezone))
    else:
        return file_datetime


def parse_audiomoth_metadata(metadata):
    """parse a dictionary of AudioMoth .wav file metadata

    -parses the comment field
    -adds keys for gain_setting, battery_state, recording_start_time
    -if available (firmware >=1.4.0), adds temperature

    Notes on comment field:
    - Starting with Firmware 1.4.0, the audiomoth logs Temperature to the
      metadata (wav header) eg "and temperature was 11.2C."
    - At some point the firmware shifted from writing "gain setting 2" to
      "medium gain setting" and later to just "medium gain". Should handle both modes.
    - In later versions of the firmware, "state" was ommitted from "battery state" in
      the comment field. Handles either phrasing.

    Tested for AudioMoth firmware versions:
        1.5.0 through 1.8.1

    Args:
        metadata: dictionary with audiomoth metadata

    Returns:
        metadata dictionary with added keys and values
    """
    assert (
        type(metadata) == dict
    ), "metadata should be a dictionary. use `parse_audiomoth_metadata_from_path` if you want to pass a file path."

    comment = metadata["comment"]

    # parse recording start time (can have timzeone info like "UTC-5")
    metadata["recording_start_time"] = _parse_audiomoth_comment_dt(comment)

    # gain setting can be written "medium gain" or "gain setting 2"
    if "gain setting" in comment:
        try:
            metadata["gain_setting"] = int(comment.split("gain setting ")[1][:1])
        except ValueError:
            metadata["gain_setting"] = comment.split(" gain setting")[0].split(" ")[-1]
    else:
        metadata["gain_setting"] = comment.split(" gain")[0].split(" ")[-1]

    metadata["battery_state"] = _parse_audiomoth_battery_info(comment)
    # if artist field doesn't exist for some reason, set it to None (to avoid KeyError)
    if "artist" not in list(metadata.keys()):
        metadata["artist"] = None
    metadata["device_id"] = metadata["artist"]
    if "temperature" in comment:
        metadata["temperature_C"] = float(
            comment.split("temperature was ")[1].split("C")[0]
        )

    return metadata


def parse_audiomoth_metadata_from_path(file_path):
    """Load and parse audiomoth metadata into a dictionary

    wraps load_metadata and parse_audiomoth_metadata

    Args:
        file_path: path to AudioMoth WAV file
    """
    metadata = load_metadata(file_path)

    if metadata is None:
        raise ValueError(f"{file_path} does not contain metadata")
    else:
        artist = metadata.get("artist", None)
        if not artist or (not "AudioMoth" in artist):
            raise ValueError(
                f"It looks like the file: {file_path} does not contain AudioMoth metadata."
            )
        else:
            return parse_audiomoth_metadata(metadata)


def _parse_audiomoth_comment_dt(comment):
    """parses start times as written in metadata Comment field of AudioMoths

    examples of Comment Field date-times:
    19:22:55 14/12/2020 (UTC-5)
    10:00:00 15/05/2021 (UTC)

    note that UTC-5 is not parseable by datetime, hence custom parsing
    also note day-month-year format of date

    Args:
        comment: the full comment string from an audiomoth metadata Comment field
    Returns:
        localized datetime object in timezone specified by original metadata
    """
    # extract relevant portion of comment
    # datetime content ends after `)`
    dt_str = comment.split("Recorded at ")[1].split(")")[0] + ")"

    # handle formats like "UTC-5" or "UTC+0130"
    if "UTC-" in dt_str or "UTC+" in dt_str:
        marker = "UTC-" if "UTC-" in dt_str else "UTC+"
        dt_str_utc_offset = dt_str.split(marker)[1][:-1]
        if len(dt_str_utc_offset) <= 2:
            dt_str_tz_str = f"{marker}{int(dt_str_utc_offset):02n}00"
        else:
            dt_str_tz_str = f"{marker}{int(dt_str_utc_offset):04n}"

        dt_str = f"{dt_str.split(marker)[0]}{dt_str_tz_str})"
    else:  #
        dt_str = dt_str.replace("(UTC)", "(UTC-0000)")
    parsed_datetime = datetime.strptime(
        dt_str, "%H:%M:%S %d/%m/%Y (%Z%z)"
    )  # .astimezone(final_tz)
    return parsed_datetime


def _parse_audiomoth_battery_info(comment):
    """attempt to parse battery info from metadata comment

    examples:
    ...battery state was 4.7V.
    ...battery state was less than 2.5V
    ...battery state was 3.5V and temperature....
    ...battery was 4.6V and...

    Args:
        comment: the full comment string from an audiomoth metadata Comment field
    Returns:
        float of voltage or string describing voltage, eg "less than 2.5V"
    """
    if "battery state" in comment:
        battery_str = comment.split("battery state was ")[1].split("V")[0] + "V"
    else:
        battery_str = comment.split("battery was ")[1].split("V")[0] + "V"
    if len(battery_str) == 4:
        return float(battery_str[:-1])
    else:
        return battery_str
