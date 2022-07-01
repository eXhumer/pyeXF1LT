# eXF1LT - Unofficial F1 live timing client
# Copyright (C) 2022  eXhumer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 of the
# License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Unofficial F1 live timing client package
"""

from pkg_resources import require

from ._client import F1LiveClient, F1ReplayClient, TimingClient  # noqa: F401
from ._type import TimingType  # noqa: F401
from ._model import (  # noqa: F401
    AudioStreamData,
    DriverData,
    ExtrapolatedClockData,
    LapCountData,
    RaceControlMessageData,
    SessionData,
    SessionInfoData,
    TeamRadioData,
    TimingAppData,
    TimingStatsData,
    TrackStatusData,
    WeatherData,
)

__version__ = require(__package__)[0].version
