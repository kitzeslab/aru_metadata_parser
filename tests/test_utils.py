import datetime

import pytz

from aru_metadata_parser import utils


def test_hex_to_time():
    t = utils.hex_to_time("5F16A04E")
    assert t == datetime.datetime(2020, 7, 21, 7, 59, 10, tzinfo=pytz.utc)


def test_hex_to_time_convert_est():
    t = utils.hex_to_time("5F16A04E")
    t = t.astimezone(pytz.timezone("US/Eastern"))
    f = pytz.timezone("US/Eastern").localize(datetime.datetime(2020, 7, 21, 3, 59, 10))
    assert t == f
