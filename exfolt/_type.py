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

from __future__ import annotations
from enum import StrEnum
from typing import Dict, List, Literal, NotRequired, Required, TypedDict


class ArchiveStatus(TypedDict, total=False):
    Status: Literal["Complete", "Generating"]


class AudioStream(TypedDict):
    Name: str
    Language: str
    Uri: str
    Path: str
    Utc: str


class AudioStreams(TypedDict, total=False):
    Streams: Dict[str, AudioStream] | List[AudioStream]


class BestSector(TypedDict, total=False):
    Position: int
    Value: str


class BestSpeed(TypedDict, total=False):
    Position: int
    Value: str


class BestSpeeds(TypedDict, total=False):
    I1: BestSpeed
    I2: BestSpeed
    FL: BestSpeed
    ST: BestSpeed


class CarData(TypedDict):
    Entries: List[CarDataEntry]


class CarDataChannel(StrEnum):
    RPM = "0"
    SPEED = "2"
    NGEAR = "3"
    THROTTLE = "4"
    BRAKE = "5"
    DRS = "45"


class CarDataEntry(TypedDict):
    Cars: Dict[str, Dict[CarDataChannel, int]]
    Utc: str


class ChampionshipPrediction(TypedDict, total=False):
    Drivers: Dict[str, DriverChampionshipPrediction]
    Teams: Dict[str, TeamChampionshipPrediction]


class Compound(StrEnum):
    SOFT = "SOFT"
    SUPERSOFT = "SUPERSOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    HYPERSOFT = "HYPERSOFT"
    INTERMEDIATE = "INTERMEDIATE"
    TEST_UNKNOWN = "TEST_UNKNOWN"
    WET = "WET"
    ULTRASOFT = "ULTRASOFT"
    UNKNOWN = "UNKNOWN"


class ContentStream(TypedDict):
    Type: str
    Name: str
    Language: str
    Uri: str
    Path: NotRequired[str]
    Utc: str


class ContentStreams(TypedDict, total=False):
    Streams: Dict[str, ContentStream] | List[ContentStream]


class CurrentTyre(TypedDict, total=False):
    Compound: Compound
    New: bool


class CurrentTyres(TypedDict, total=False):
    Tyres: Dict[str, CurrentTyre]


class Driver(TypedDict, total=False):
    RacingNumber: str
    BroadcastName: str
    FullName: str
    Tla: str
    Line: int
    TeamName: str
    TeamColour: str
    FirstName: str
    LastName: str
    Reference: str
    HeadshotUrl: str
    CountryCode: str


class DriverChampionshipPrediction(TypedDict, total=False):
    RacingNumber: str
    CurrentPosition: int
    PredictedPosition: int
    CurrentPoints: int
    PredictedPoints: int


class ExtrapolatedClock(TypedDict, total=False):
    Utc: str
    Remaining: str
    Extrapolating: bool


class FlagStatus(StrEnum):
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


class Hub(StrEnum):
    STREAMING = "streaming"


class LapCount(TypedDict, total=False):
    CurrentLap: int
    TotalLaps: int


class PersonalBestLapTime(TypedDict, total=False):
    Lap: int
    Position: int
    Value: str


class PitLaneTimeCollection(TypedDict):
    PitTimes: Dict[str, PitTime]


class PitTime(TypedDict):
    RacingNumber: str
    Duration: str
    Lap: str


class Position(TypedDict):
    Position: List[PositionData]


class PositionData(TypedDict):
    Timestamp: str
    Entries: Dict[str, PositionEntry]


class PositionEntry(TypedDict):
    Status: str
    X: int
    Y: int
    Z: int


class RaceControlMessage(TypedDict, total=False):
    Utc: Required[str]
    Message: Required[str]
    Category: Required[str]
    Lap: int
    Flag: FlagStatus
    Scope: str
    Sector: int
    Status: str
    Mode: str


class RaceControlMessages(TypedDict, total=False):
    Messages: Dict[str, RaceControlMessage] | List[RaceControlMessage]


class SessionData(TypedDict, total=False):
    Series: Dict[str, SessionSeries] | List[SessionSeries]
    StatusSeries: Dict[str, SessionStatusSeries] | List[SessionStatusSeries]


class SessionInfo(TypedDict, total=False):
    Meeting: SessionInfoMeeting
    ArchiveStatus: ArchiveStatus
    Key: int
    Type: str
    Name: str
    StartDate: str
    EndDate: str
    GmtOffset: str
    Path: str


class SessionInfoMeeting(TypedDict):
    Key: int
    Name: str
    OfficialName: str
    Location: str
    Country: SessionInfoMeetingCountry
    Circuit: SessionInfoMeetingCircuit


class SessionInfoMeetingCircuit(TypedDict):
    Key: int
    ShortName: str


class SessionInfoMeetingCountry(TypedDict):
    Key: int
    Code: str
    Name: str


class SessionSeries(TypedDict, total=False):
    Utc: Required[str]
    Lap: int
    QualifyingPart: int


class SessionStatus(TypedDict, total=False):
    Status: SessionStatusEnum


class SessionStatusEnum(StrEnum):
    INACTIVE = "Inactive"
    STARTED = "Started"
    ABORTED = "Aborted"
    FINISHED = "Finished"
    FINALISED = "Finalised"
    ENDS = "Ends"


class SessionStatusSeries(TypedDict, total=False):
    Utc: Required[str]
    TrackStatus: str
    SessionStatus: str


class StreamingStatus(TypedDict):
    Status: Literal["Available", "Offline"]


class StreamingTopic(StrEnum):
    """
    F1 live timing SignalR streaming topics
    """

    ARCHIVE_STATUS = "ArchiveStatus"
    AUDIO_STREAMS = "AudioStreams"
    CAR_DATA_Z = "CarData.z"
    CHAMPIONSHIP_PREDICTION = "ChampionshipPrediction"
    CONTENT_STREAMS = "ContentStreams"
    CURRENT_TYRES = "CurrentTyres"
    DRIVER_LIST = "DriverList"
    DRIVER_RACE_INFO = "DriverRaceInfo"
    DRIVER_SCORE = "DriverScore"
    EXTRAPOLATED_CLOCK = "ExtrapolatedClock"
    HEARTBEAT = "Heartbeat"
    LAP_COUNT = "LapCount"
    LAP_SERIES = "LapSeries"
    PIT_LANE_TIME_COLLECTION = "PitLaneTimeCollection"
    POSITION_Z = "Position.z"
    RACE_CONTROL_MESSAGES = "RaceControlMessages"
    SESSION_DATA = "SessionData"
    SESSION_INFO = "SessionInfo"
    SESSION_STATUS = "SessionStatus"
    SP_FEED = "SPFeed"
    TEAM_RADIO = "TeamRadio"
    TIMING_APP_DATA = "TimingAppData"
    TIMING_DATA = "TimingData"
    TIMING_DATA_F1 = "TimingDataF1"
    TIMING_STATS = "TimingStats"
    TLA_RCM = "TlaRcm"
    TOP_THREE = "TopThree"
    TRACK_STATUS = "TrackStatus"
    TYRE_STINT_SERIES = "TyreStintSeries"
    WEATHER_DATA = "WeatherData"
    WEATHER_DATA_SERIES = "WeatherDataSeries"


class TeamChampionshipPrediction(TypedDict, total=False):
    TeamName: str
    CurrentPosition: int
    PredictedPosition: int
    CurrentPoints: int
    PredictedPoints: int


class TeamRadio(TypedDict, total=False):
    Captures: Dict[str, TeamRadioCapture] | List[TeamRadioCapture]


class TeamRadioCapture(TypedDict):
    Utc: str
    RacingNumber: str
    Path: str


class TimingAppData(TypedDict, total=False):
    Lines: Dict[str, TimingDriverAppData]


class TimingBestLapTime(TypedDict, total=False):
    Value: str
    Lap: int


class TimingData(TypedDict, total=False):
    Lines: Dict[str, TimingDriverData]


class TimingDriverAppData(TypedDict, total=False):
    RacingNumber: str
    Line: int
    GridPos: str
    Stints: Dict[str, TimingStint] | List[TimingStint]


class TimingDriverData(TypedDict, total=False):
    GapToLeader: str
    IntervalToPositionAhead: TimingIntervalData
    Line: int
    Position: str
    ShowPosition: bool
    RacingNumner: str
    Retired: bool
    InPit: bool
    PitOut: bool
    Stopped: bool
    Status: int
    NumberOfLaps: int
    NumberOfPitStops: int
    Sectors: List[TimingSector]
    Speeds: TimingSpeeds
    BestLapTime: TimingBestLapTime
    LastLapTime: TimingLastLapTime


class TimingIntervalData(TypedDict, total=False):
    Value: str
    Catching: bool


class TimingLastLapTime(TypedDict, total=False):
    Value: str
    Status: int
    OverallFastest: bool
    PersonalFastest: bool


class TimingSector(TypedDict, total=False):
    Stopped: bool
    PreviousValue: str
    Segments: List[TimingSegment]
    Value: str
    Status: int
    OverallFastest: bool
    PersonalFastest: bool


class TimingSegment(TypedDict, total=False):
    Status: int


class TimingSpeed(TypedDict, total=False):
    Value: str
    Status: int
    OverallFastest: bool
    PersonalFastest: bool


class TimingSpeeds(TypedDict, total=False):
    I1: TimingSpeed
    I2: TimingSpeed
    FL: TimingSpeed
    ST: TimingSpeed


class TimingStats(TypedDict, total=False):
    Withheld: bool
    Lines: Dict[str, TimingStatsLine]
    SessionType: Literal["Race", "Qualifying", "Practice"]


class TimingStatsLine(TypedDict, total=False):
    Line: int
    RacingNumber: str
    PersonalBestLapTime: PersonalBestLapTime
    BestSectors: Dict[str, BestSector] | List[BestSector]
    BestSpeeds: BestSpeeds


class TimingStint(TypedDict, total=False):
    LapTime: str
    LapNumber: int
    LapFlags: int
    Compound: Compound
    New: Literal["true", "false"]
    TyresNotChanged: str
    TotalLaps: int
    StartLaps: int


class TopThree(TypedDict, total=False):
    Withheld: bool
    Lines: List[TopThreeLine]


class TopThreeLine(TypedDict, total=False):
    Position: int
    ShowPosition: bool
    RacingNumber: str
    Tla: str
    BroadcastName: str
    FullName: str
    Team: str
    TeamColour: str
    LapTime: str
    LapState: int
    DiffToAhead: str
    DiffToLeader: str
    OvertallFastest: bool
    PersonalFastest: bool


class TrackStatus(TypedDict):
    Status: TrackStatusStatus
    Message: TrackStatusMessage


class TrackStatusStatus(StrEnum):
    ALL_CLEAR = "1"
    YELLOW = "2"
    GREEN = "3"
    SC_DEPLOYED = "4"
    RED = "5"
    VSC_DEPLOYED = "6"
    VSC_ENDING = "7"


class TrackStatusMessage(StrEnum):
    ALL_CLEAR = "AllClear"
    YELLOW = "Yellow"
    GREEN = "Green"
    SC_DEPLOYED = "SCDeployed"
    RED = "Red"
    VSC_DEPLOYED = "VSCDeployed"
    VSC_ENDING = "VSCEnding"


class TyreStintSeries(TypedDict):
    Stints: Dict[str, Dict[str, TimingStint] | List[TimingStint]]


class WeatherData(TypedDict):
    AirTemp: str
    Humidity: str
    Pressure: str
    Rainfall: str
    TrackTemp: str
    WindDirection: str
    WindSpeed: str


class YearIndex(TypedDict):
    Year: int
    Meetings: List[YearMeetingIndex]


class YearMeetingIndex(TypedDict):
    Sessions: List[YearSessionIndex]
    Key: int
    Code: str
    Number: int
    Location: str
    OfficialName: str
    Name: str
    Country: SessionInfoMeetingCountry
    Circuit: SessionInfoMeetingCircuit


class YearSessionIndex(TypedDict):
    Key: int
    Type: str
    Number: NotRequired[int]
    Name: str
    StartDate: str
    EndDate: str
    GmtOffset: str
    Path: NotRequired[str]
