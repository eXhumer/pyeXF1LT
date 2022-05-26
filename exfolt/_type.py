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


class TimingDataStatus(IntEnum):
    YELLOW = 2048
    GREEN = 2049
    PURPLE = 2051
    STOPPED = 2052
    PITTED = 2064
    PIT_ISSUE = 2068


class TrackStatus(str, Enum):
    ALL_CLEAR = "1"
    YELLOW = "2"
    GREEN = "3"
    SC_DEPLOYED = "4"
    RED = "5"
    VSC_DEPLOYED = "6"
    VSC_ENDING = "7"
