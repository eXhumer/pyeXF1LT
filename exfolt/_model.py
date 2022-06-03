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

from typing import Dict, Literal

from ._type import TimingDataStatus, TimingType


class AudioStreamData:
    def __init__(
        self,
        name: str,
        language: str,
        uri: str,
        path: str,
    ) -> None:
        self.__name = name
        self.__language = language
        self.__uri = uri
        self.__path = path

    def __repr__(self) -> str:
        return (
            "AudioStreamData(" +
            ", ".join((
                f"name={self.__name}",
                f"language={self.__language}",
                f"uri={self.__uri}",
                f"path={self.__path}",
            )) +
            ")"
        )


class DriverData:
    def __init__(
        self,
        racing_number: str,
        broadcast_name: str | None = None,
        full_name: str | None = None,
        tla: str | None = None,
        team_name: str | None = None,
        team_color: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        reference: str | None = None,
        headshot_url: str | None = None,
        country_code: str | None = None,
    ) -> None:
        self.__racing_number = racing_number
        self.__broadcast_name = broadcast_name
        self.__full_name = full_name
        self.__tla = tla
        self.__team_name = team_name
        self.__team_color = team_color
        self.__first_name = first_name
        self.__last_name = last_name
        self.__reference = reference
        self.__headshot_url = headshot_url
        self.__country_code = country_code

    def __repr__(self) -> str:
        return (
            "DriverData(" +
            ", ".join((
                f"racing_number={self.__racing_number}",
                f"broadcast_name={self.__broadcast_name}",
                f"full_name={self.__full_name}",
                f"tla={self.__tla}",
                f"team_name={self.__team_name}",
                f"team_color={self.__team_color}",
                f"first_name={self.__first_name}",
                f"last_name={self.__last_name}",
                f"reference={self.__reference}",
                f"headshot_url={self.__headshot_url}",
                f"country_code={self.__country_code}",
            )) +
            ")"
        )

    @property
    def racing_number(self):
        return self.__racing_number

    @property
    def broadcast_name(self):
        return self.__broadcast_name

    @property
    def full_name(self):
        return self.__full_name

    @property
    def tla(self):
        return self.__tla

    @property
    def team_name(self):
        return self.__team_name

    @property
    def team_color(self):
        return self.__team_color

    @property
    def first_name(self):
        return self.__first_name

    @property
    def last_name(self):
        return self.__last_name

    @property
    def reference(self):
        return self.__reference

    @property
    def headshot_url(self):
        return self.__headshot_url

    @property
    def country_code(self):
        return self.__country_code

    def __str__(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.racing_number})"

        return self.racing_number


class ExtrapolatedClockData:
    def __init__(
        self,
        remanining: str,
        extrapolating: bool,
        utc: str,
    ) -> None:
        self.__remaining = remanining
        self.__extrapolating = extrapolating
        self.__utc = utc

    def __repr__(self) -> str:
        return (
            "ExtrapolatedClockData(" +
            ", ".join((
                f"remanining={self.__remaining}",
                f"extrapolating={self.__extrapolating}",
                f"utc={self.__utc}",
            )) +
            ")"
        )

    @property
    def remaining(self):
        return self.__remaining

    @property
    def extrapolating(self):
        return self.__extrapolating

    @property
    def utc(self):
        return self.__utc

    @remaining.setter
    def set_remaining(self, remaining: str):
        self.__remaining = remaining

    @extrapolating.setter
    def set_extrapolating(self, extrapolating: bool):
        self.__extrapolating = extrapolating

    @utc.setter
    def set_utc(self, utc: str):
        self.__utc = utc


class InitialWeatherData:
    def __init__(
        self,
        airtemp: float,
        tracktemp: float,
        humidity: float,
        pressure: float,
        rainfall: bool,
        winddirection: int,
        windspeed: float,
    ) -> None:
        self.__airtemp = airtemp
        self.__tracktemp = tracktemp
        self.__humidity = humidity
        self.__pressure = pressure
        self.__rainfall = rainfall
        self.__winddirection = winddirection
        self.__windspeed = windspeed

    def __repr__(self) -> str:
        return (
            "InitialWeatherData(" +
            ", ".join((
                f"airtemp={self.__airtemp}",
                f"tracktemp={self.__tracktemp}",
                f"humidity={self.__humidity}",
                f"pressure={self.__pressure}",
                f"rainfall={self.__rainfall}",
                f"winddirection={self.__winddirection}",
                f"windspeed={self.__windspeed}",
            )) +
            ")"
        )

    @property
    def airtemp(self):
        return self.__airtemp

    @property
    def tracktemp(self):
        return self.__tracktemp

    @property
    def humidity(self):
        return self.__humidity

    @property
    def pressure(self):
        return self.__pressure

    @property
    def rainfall(self):
        return self.__rainfall

    @property
    def winddirection(self):
        return self.__winddirection

    @property
    def windspeed(self):
        return self.__windspeed


class LapCountData:
    def __init__(
        self,
        current_lap: int,
        total_laps: int,
    ) -> None:
        self.__current_lap = current_lap
        self.__total_laps = total_laps

    def __repr__(self):
        data = ", ".join((
            f"current_lap={self.__current_lap}",
            f"total_laps={self.__total_laps}",
        ))
        return f"LapCountData({data})"

    @property
    def current_lap(self):
        return self.__current_lap

    @property
    def total_laps(self):
        return self.__total_laps

    @current_lap.setter
    def set_current_lap(self, new_current_lap: int):
        self.__current_lap = new_current_lap

    @total_laps.setter
    def set_total_laps(self, new_total_laps: int):
        self.__total_laps = new_total_laps


class RaceControlMessageData:
    def __init__(
        self,
        category: str,
        message: str,
        flag: str | None = None,
        scope: str | None = None,
        racing_number: str | None = None,
        sector: int | None = None,
        lap: int | None = None,
        drs_status: str | None = None,
    ) -> None:
        self.__category = category
        self.__message = message
        self.__flag = flag
        self.__scope = scope
        self.__racing_number = racing_number
        self.__sector = sector
        self.__lap = lap
        self.__drs_status = drs_status

    def __repr__(self) -> str:
        return (
            "RaceControlMessageData(" +
            ", ".join((
                f"category={self.__category}",
                f"message={self.__message}",
                f"flag={self.__flag}",
                f"scope={self.__scope}",
                f"racing_number={self.__racing_number}",
                f"sector={self.__sector}",
                f"lap={self.__lap}",
                f"drs_status={self.__drs_status}",
            )) +
            ")"
        )

    @property
    def category(self):
        return self.__category

    @property
    def message(self):
        return self.__message

    @property
    def flag(self):
        return self.__flag

    @property
    def scope(self):
        return self.__scope

    @property
    def racing_number(self):
        return self.__racing_number

    @property
    def sector(self):
        return self.__sector

    @property
    def lap(self):
        return self.__lap

    @property
    def drs_status(self):
        return self.__drs_status


class SessionData:
    def __init__(
        self,
        lap: int | None = None,
        qualifying_part: int | None = None,
        track_status: str | None = None,
        session_status: str | None = None,
    ) -> None:
        self.__lap = lap
        self.__qualifying_part = qualifying_part
        self.__track_status = track_status
        self.__session_status = session_status

    def __repr__(self) -> str:
        return (
            "SessionData(" +
            ", ".join((
                f"lap={self.__lap}",
                f"qualifying_part={self.__qualifying_part}",
                f"track_status={self.__track_status}",
                f"session_status={self.__session_status}",
            )) +
            ")"
        )

    @property
    def lap(self):
        return self.__lap

    @property
    def qualifying_part(self):
        return self.__qualifying_part

    @property
    def track_status(self):
        return self.__track_status

    @property
    def session_status(self):
        return self.__session_status


class SessionInfoData:
    ArchiveStatusData = Dict[
        Literal["Status"],
        Literal["Complete", "Generating"],
    ]

    CircuitData = Dict[
        Literal[
            "Key",
            "ShortName",
        ],
        int | str,
    ]

    CountryData = Dict[
        Literal[
            "Key",
            "Code",
            "Name",
        ],
        int | str,
    ]

    MeetingData = Dict[
        Literal[
            "Key",
            "Name",
            "OfficialName",
            "Location",
            "Country",
            "Circuit",
        ],
        int | str | CountryData | CircuitData,
    ]

    def __init__(
        self,
        meeting: MeetingData,
        archive_status: ArchiveStatusData,
        key: int,
        type: str,
        name: str,
        start_date: str,
        end_date: str,
        gmt_offset: str,
        path: str,
        number: int | None = None,
    ) -> None:
        self.__meeting = meeting
        self.__archive_status = archive_status
        self.__key = key
        self.__type = type
        self.__name = name
        self.__start_date = start_date
        self.__end_date = end_date
        self.__gmt_offset = gmt_offset
        self.__path = path
        self.__number = number

    def __repr__(self) -> str:
        return (
            "SessionInfoData(" +
            ", ".join((
                f"meeting={self.__meeting}",
                f"archive_status={self.__archive_status}",
                f"key={self.__key}",
                f"type={self.__type}",
                f"name={self.__name}",
                f"start_date={self.__start_date}",
                f"end_date={self.__end_date}",
                f"gmt_offset={self.__gmt_offset}",
                f"path={self.__path}",
                f"number={self.__number}",
            )) +
            ")"
        )

    @property
    def meeting(self):
        return self.__meeting

    @property
    def archive_status(self):
        return self.__archive_status

    @property
    def key(self):
        return self.__key

    @property
    def type(self):
        return self.__type

    @property
    def name(self):
        return self.__name

    @property
    def start_date(self):
        return self.__start_date

    @property
    def end_date(self):
        return self.__end_date

    @property
    def gmt_offset(self):
        return self.__gmt_offset

    @property
    def path(self):
        return self.__path

    @property
    def number(self):
        return self.__number


class TeamRadioData:
    def __init__(
        self,
        racing_number: str,
        path: str,
        timestamp: str,
    ) -> None:
        self.__racing_number = racing_number
        self.__path = path
        self.__timestamp = timestamp

    def __repr__(self) -> str:
        return (
            "TeamRadioData(" +
            ", ".join((
                f"racing_number={self.__racing_number}",
                f"path={self.__path}",
                f"timestamp={self.__timestamp}",
            )) +
            ")"
        )

    @property
    def racing_number(self):
        return self.__racing_number

    @property
    def path(self):
        return self.__path

    @property
    def timestamp(self):
        return self.__timestamp


class TimingData:
    def __init__(
        self,
        racing_number: str,
        sector_number: int,
        segment_number: int,
        segment_status: TimingDataStatus,
    ) -> None:
        self.__racing_number = racing_number
        self.__sector_number = sector_number
        self.__segment_number = segment_number
        self.__segment_status = segment_status

    def __repr__(self) -> str:
        return (
            "TimingData(" +
            ", ".join((
                f"racing_number={self.__racing_number}",
                f"sector_number={self.__sector_number}",
                f"segment_number={self.__segment_number}",
                f"segment_status={self.__segment_status}",
            )) +
            ")"
        )

    @property
    def racing_number(self):
        return self.__racing_number

    @property
    def sector_number(self):
        return self.__sector_number

    @property
    def segment_number(self):
        return self.__segment_number

    @property
    def segment_status(self):
        return self.__segment_status


class TrackStatusData:
    def __init__(self, status: TimingType.TrackStatus, message: str) -> None:
        self.__status = status
        self.__message = message

    def __repr__(self) -> str:
        return (
            "TrackStatusData(" +
            ", ".join((
                f"status={self.status_string}",
                f"message={self.__message}",
            )) +
            ")"
        )

    @property
    def status(self):
        return self.__status

    @property
    def status_string(self):
        if self.__status == TimingType.TrackStatus.ALL_CLEAR:
            return "All Clear"

        elif self.__status == TimingType.TrackStatus.YELLOW:
            return "Yellow"

        elif self.__status == TimingType.TrackStatus.GREEN:
            return "Green"

        elif self.__status == TimingType.TrackStatus.SC_DEPLOYED:
            return "Safety Car Deployed"

        elif self.__status == TimingType.TrackStatus.RED:
            return "Red"

        elif self.__status == TimingType.TrackStatus.VSC_DEPLOYED:
            return "Virtual Safety Car Deployed"

        elif self.__status == TimingType.TrackStatus.VSC_ENDING:
            return "Virtual Safety Car Ending"

        else:
            return self.__status

    @property
    def message(self):
        return self.__message

    @status.setter
    def set_status(self, status: TimingType.TrackStatus):
        self.__status = status

    @message.setter
    def set_message(self, message: str):
        self.__message = message


class WeatherDataChange:
    def __init__(
        self,
        title: str,
        change: str | None = None,
        previous: str | None = None,
        new: str | None = None,
    ) -> None:
        self.__title = title
        self.__change = change
        self.__previous = previous
        self.__new = new

    def __repr__(self) -> str:
        return (
            "WeatherDataChange(" +
            ", ".join((
                f"title={self.__title}",
                f"change={self.__change}",
                f"previous={self.__previous}",
                f"new={self.__new}",
            )) +
            ")"
        )

    @property
    def title(self):
        return self.__title

    @property
    def change(self):
        return self.__change

    @property
    def previous(self):
        return self.__previous

    @property
    def new(self):
        return self.__new
