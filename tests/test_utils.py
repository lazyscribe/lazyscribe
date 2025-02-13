"""Test utils."""

import zoneinfo
from datetime import datetime

import time_machine

from lazyscribe._utils import utcnow


def test_utcnow():
    """Test UTCnow."""
    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("UTC")), tick=False
    ):
        assert utcnow() == datetime(2025, 1, 20, 13, 23, 30)

    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("EST")), tick=False
    ):
        assert utcnow() == datetime(2025, 1, 20, 18, 23, 30)

    with time_machine.travel(
        datetime(2025, 1, 20, 13, 23, 30, tzinfo=zoneinfo.ZoneInfo("MST")), tick=False
    ):
        assert utcnow() == datetime(2025, 1, 20, 20, 23, 30)
