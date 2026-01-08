"""test for parse module"""

import datetime
import pytz
import pytest
import math
from aru_metadata_parser import parse
import dateutil


@pytest.fixture()
def veryshort_wav_str():
    return "tests/audio/veryshort.wav"


@pytest.fixture()
def silence_10s_mp3_str():
    return "tests/audio/silence_10s.mp3"


def test_audiomoth_start_time():
    filename = "20191219_123300.WAV"
    dt = datetime.datetime.strptime("20191219 12:33:00", "%Y%m%d %H:%M:%S")
    dt = pytz.utc.localize(dt)
    assert parse.audiomoth_start_time(filename, filename_timezone="UTC") == dt


def test_audiomoth_start_time_hex_format():
    filename = "5DFB6DFC.WAV"
    dt = datetime.datetime.strptime("20191219 12:33:00", "%Y%m%d %H:%M:%S")
    dt = pytz.utc.localize(dt)
    assert parse.audiomoth_start_time(filename, filename_timezone="UTC") == dt


def test_audiomoth_start_time_other_timezone():
    """test behavior when filename timezone is not UTC

    - should read the file name assuming it was written based on US/Eastern
    """
    filename = "20191219_073300.WAV"  # written in EST rather than UTC
    dt = datetime.datetime.strptime("20191219 12:33:00", "%Y%m%d %H:%M:%S")
    dt = pytz.utc.localize(dt)
    dt_read = parse.audiomoth_start_time(
        filename, filename_timezone="US/Eastern", to_utc=False
    )
    assert dt_read == dt
    assert dt_read.tzname() == "EST"

    # should also work if we convert to UTC
    dt_read = parse.audiomoth_start_time(
        filename, filename_timezone="US/Eastern", to_utc=True
    )
    assert dt_read == dt


def test_parse_audiomoth_metadata():
    metadata = {
        "filesize": 115200360,
        "album": None,
        "albumartist": None,
        "artist": "AudioMoth 24526B065D325963",
        "audio_offset": None,
        "bitrate": 500.0,
        "channels": 1,
        "comment": "Recorded at 10:25:00 04/04/2020 (UTC) by AudioMoth 24526B065D325963 at gain setting 2 while battery state was 4.7V.",
        "composer": None,
        "disc": None,
        "disc_total": None,
        "duration": 1800.0,
        "extra": {},
        "genre": None,
        "samplerate": 32000,
        "title": None,
        "track": None,
        "track_total": None,
        "year": None,
        "audio_offest": 352,
    }
    new_metadata = parse.parse_audiomoth_metadata(metadata)
    assert new_metadata["device_id"] == "AudioMoth 24526B065D325963"
    assert new_metadata["gain_setting"] == 2
    assert new_metadata["battery_state"] == 4.7
    assert new_metadata["recording_start_time"] == pytz.utc.localize(
        datetime.datetime(2020, 4, 4, 10, 25)
    )


def test_parse_audiomoth_metadata_with_timezone():
    metadata = {
        "filesize": 115200360,
        "album": None,
        "albumartist": None,
        "artist": "AudioMoth 24526B065D325963",
        "audio_offset": None,
        "bitrate": 500.0,
        "channels": 1,
        "comment": "Recorded at 19:22:55 14/12/2020 (UTC-5) by AudioMoth 24E144055DDD3203 at medium gain setting while battery state was 4.0V and temperature was 24.5C.",
        "composer": None,
        "disc": None,
        "disc_total": None,
        "duration": 1800.0,
        "extra": {},
        "genre": None,
        "samplerate": 32000,
        "title": None,
        "track": None,
        "track_total": None,
        "year": None,
        "audio_offest": 352,
    }
    new_metadata = parse.parse_audiomoth_metadata(metadata)
    assert new_metadata["recording_start_time"] == pytz.utc.localize(
        datetime.datetime(2020, 12, 15, 00, 22, 55)
    )


def test_parse_audiomoth_metadata_with_deployment_name():
    """sometimes comment string includes `during deployment ###`"""
    metadata = {
        "artist": "AudioMoth 243B1F075C7B4301",
        "comment": "Recorded at 10:00:00 15/05/2021 (UTC) during deployment 41C351E84E9996C2 at medium gain setting while battery state was 4.7V and temperature was 3.7C.",
        "samplerate": 32000,
        "format": "WAV",
        "frames": 230400000,
        "sections": 1,
        "subtype": "PCM_16",
        "channels": 1,
        "duration": 7200.0,
    }
    new_metadata = parse.parse_audiomoth_metadata(metadata)
    assert new_metadata["recording_start_time"] == pytz.utc.localize(
        datetime.datetime(2021, 5, 15, 10, 00, 00)
    )


def test_parse_audiomoth_metadata_with_low_battery():
    metadata = {
        "filesize": 115200360,
        "album": None,
        "albumartist": None,
        "artist": "AudioMoth 24526B065D325963",
        "audio_offset": None,
        "bitrate": 500.0,
        "channels": 1,
        "comment": "Recorded at 10:00:00 15/05/2021 (UTC) by AudioMoth 249BC3055C02FE06 at medium gain setting while battery state was less than 2.5V and temperature was 2.1C.",
        "composer": None,
        "disc": None,
        "disc_total": None,
        "duration": 1800.0,
        "extra": {},
        "genre": None,
        "samplerate": 32000,
        "title": None,
        "track": None,
        "track_total": None,
        "year": None,
        "audio_offest": 352,
    }
    new_metadata = parse.parse_audiomoth_metadata(metadata)
    assert new_metadata["gain_setting"] == "medium"
    assert new_metadata["recording_start_time"] == pytz.utc.localize(
        datetime.datetime(2021, 5, 15, 10, 00, 00)
    )


def test_parse_audiomoth_from_path_wrong_metadata(veryshort_wav_str):
    with pytest.raises(ValueError):
        parse.parse_audiomoth_metadata_from_path(veryshort_wav_str)


def test_parse_audiomoth_metadata_v16_to_v181():
    """Firmware versions 1.6.0 through 1.8.2 (latest release as of Sept. 2022) use this comment syntax

    note the difference between how gain and battery are written

    """
    metadata = {
        "filesize": 115200360,
        "album": None,
        "albumartist": None,
        "artist": "AudioMoth 24526B065D325963",
        "audio_offset": None,
        "bitrate": 500.0,
        "channels": 1,
        "comment": "Recorded at 10:00:00 15/05/2021 (UTC) by AudioMoth 249BC3055C02FE06 at medium gain while battery was 4.5V and temperature was 21.1C. Recording stopped due to switch position change.",
        "composer": None,
        "disc": None,
        "disc_total": None,
        "duration": 1800.0,
        "extra": {},
        "genre": None,
        "samplerate": 32000,
        "title": None,
        "track": None,
        "track_total": None,
        "year": None,
        "audio_offest": 352,
    }
    new_metadata = parse.parse_audiomoth_metadata(metadata)
    assert new_metadata["gain_setting"] == "medium"
    assert math.isclose(new_metadata["battery_state"], 4.5, abs_tol=1e-5)


def test_parse_aru_file_start_time():
    """test handling of various formats"""

    # various formats across ARUS models and firmware:
    # Audiomoth hexadecimal unix time: 5F2A1C00 (convert hex to int timestamp and then to datetime)
    # Audiomoth human-readable: 20220719_000000 (YYYYMMDD_HHMMSS)
    # SongMeter Micro: SMM03873_20220719_000000.wav (deviceID_YYYYMMDD_HHMMSS)
    # SongMeter Micro 2: 2MM04797_20241127_155140.wav (deviceID_YYYYMMDD_HHMMSS)
    # SMM with 2 channels: SBT-6-76-18_0+1_0_20160621_080000.wav (deviceID_YYYYMMDD_HHMMSS)
    # OwlSense: 55063_2024-11-27_T16-47-33.wav (deviceID_YYYY-MM-DD_THH-MM-SS)
    # Swift: SwiftOne_20220719_000000_-0400.wav (SwiftOne_YYYYMMDD_HHMMSS_UTCoffset)
    #
    test_cases = [
        (
            "20220719_000000.WAV",
            datetime.datetime(2022, 7, 19, 0, 0, 0),
        ),
        (
            "SMM03873_20220719_000000.wav",
            datetime.datetime(2022, 7, 19, 0, 0, 0),
        ),
        (
            "2MM04797_20241127_155140.wav",
            datetime.datetime(2024, 11, 27, 15, 51, 40),
        ),
        (
            "SBT-6-76-18_0+1_0_20160621_080000.wav",
            datetime.datetime(2016, 6, 21, 8, 0, 0),
        ),
        (
            "55063_2024-11-27_T16-47-33.wav",
            datetime.datetime(2024, 11, 27, 16, 47, 33),
        ),
        (
            "SwiftOne_20220719_000000_-0400.wav",
            dateutil.parser.parse("20220719 000000 -0400"),
        ),
    ]
    for filename, expected_dt in test_cases:
        parsed_dt = parse.parse_aru_file_start_time(filename)
        assert parsed_dt == expected_dt, f"{filename} {parsed_dt} {expected_dt}"
