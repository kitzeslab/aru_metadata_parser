import soundfile
import datetime
import pytz


def hex_to_time(s):
    """convert a hexidecimal, Unix time string to a datetime timestamp in utc

    Example usage:
    ```
    # Get the UTC timestamp
    t = hex_to_time('5F16A04E')

    # Convert it to a desired timezone
    my_timezone = pytz.timezone("US/Mountain")
    t = t.astimezone(my_timezone)
    ```

    Args:
        s (string): hexadecimal Unix epoch time string, e.g. '5F16A04E'

    Returns:
        datetime.datetime object representing the date and time in UTC
    """
    sec = int(s, 16)
    timestamp = datetime.datetime.utcfromtimestamp(sec).replace(tzinfo=pytz.utc)
    return timestamp


def load_metadata(path, raise_exceptions=False):
    """use soundfile to load metadata from WAV or AIFF file

    Args:
        path: file path to WAV of AIFF file
        raise_exceptions: if True, raises exception,
            if False returns None if exception occurs
            [default: False]

    Returns:
        dictionary containing audio file metadata
    """

    try:
        with soundfile.SoundFile(path, "r") as f:
            metadata = f.copy_metadata()
            metadata["samplerate"] = f.samplerate
            metadata["format"] = f.format
            metadata["frames"] = f.frames
            metadata["sections"] = f.sections
            metadata["subtype"] = f.subtype
            return metadata
    except:
        if raise_exceptions:
            raise
        else:
            return None
