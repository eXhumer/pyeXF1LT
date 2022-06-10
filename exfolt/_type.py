# pyeXF1LT - Unofficial F1 live timing client
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

from enum import Enum, IntEnum


class TimingDataStatus(IntEnum):
    YELLOW = 2048
    GREEN = 2049
    PURPLE = 2051
    STOPPED = 2052
    PITTED = 2064
    PIT_ISSUE = 2068


class TimingType:
    """
    F1 live timing related types
    """

    class FlagStatus(str, Enum):
        BLACK = "BLACK"
        BLACK_AND_ORANGE = "BLACK AND ORANGE"
        BLACK_AND_WHITE = "BLACK AND WHITE"
        BLUE = "BLUE"
        CHEQUERED = "CHEQUERED"
        CLEAR = "CLEAR"
        GREEN = "GREEN"
        YELLOW = "YELLOW"
        DOUBLE_YELLOW = "DOUBLE YELLOW"
        RED = "RED"

    class Hub(str, Enum):
        """
        F1 live timing SignalR hubs
        """

        STREAMING = "streaming"

    class SessionStatus(str, Enum):
        INACTIVE = "Inactive"
        STARTED = "Started"
        ABORTED = "Aborted"
        FINISHED = "Finished"
        FINALISED = "Finalised"
        ENDS = "Ends"

    class Topic(str, Enum):
        """
        F1 live timing SignalR topics
        """

        ARCHIVE_STATUS = "ArchiveStatus"
        AUDIO_STREAMS = "AudioStreams"
        CAR_DATA_Z = "CarData.z"
        CHAMPIONSHIP_PREDICTION = "ChampionshipPrediction"
        CONTENT_STREAMS = "ContentStreams"
        CURRENT_TYRES = "CurrentTyres"
        DRIVER_LIST = "DriverList"
        EXTRAPOLATED_CLOCK = "ExtrapolatedClock"
        HEARTBEAT = "Heartbeat"
        LAP_COUNT = "LapCount"
        POSITION_Z = "Position.z"
        RACE_CONTROL_MESSAGES = "RaceControlMessages"
        SESSION_DATA = "SessionData"
        SESSION_INFO = "SessionInfo"
        SESSION_STATUS = "SessionStatus"
        TEAM_RADIO = "TeamRadio"
        TIMING_APP_DATA = "TimingAppData"
        TIMING_DATA = "TimingData"
        TIMING_STATS = "TimingStats"
        TOP_THREE = "TopThree"
        TRACK_STATUS = "TrackStatus"
        WEATHER_DATA = "WeatherData"

    class TrackStatus(str, Enum):
        ALL_CLEAR = "1"
        YELLOW = "2"
        GREEN = "3"
        SC_DEPLOYED = "4"
        RED = "5"
        VSC_DEPLOYED = "6"
        VSC_ENDING = "7"

    class TyreCompound(str, Enum):
        SOFT = "SOFT"
        MEDIUM = "MEDIUM"
        HARD = "HARD"
        INTERMEDIATE = "INTERMEDIATE"
        WET = "WET"
        UNKNOWN = "UNKNOWN"
