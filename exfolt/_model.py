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
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional, Union

from ._type import F1LTType
from ._utils import datetime_parser


class F1LTModel:
    class ArchiveStatus:
        def __init__(self, status: Literal["Complete", "Generating"]):
            self.__status = status

        def __repr__(self):
            data = ", ".join((
                f"status={self.__status}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def status(self):
            return self.__status

        @status.setter
        def status(self, status: Literal["Complete", "Generating"]):
            self.__status = status

    class AudioStream:
        def __init__(self, name: str, language: str, uri: str, path: str):
            self.__name = name
            self.__language = language
            self.__uri = uri
            self.__path = path

        def __repr__(self):
            data = ", ".join((
                f"name={self.__name}",
                f"language={self.__language}",
                f"uri={self.__uri}",
                f"path={self.__path}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def name(self):
            return self.__name

        @property
        def language(self):
            return self.__language

        @property
        def uri(self):
            return self.__uri

        @property
        def path(self):
            return self.__path

    class CarDataEntry:
        class ChannelData:
            def __init__(self, rpm: int, speed: int, ngear: int, throttle: int, brake: int,
                         drs: int):
                self.__rpm = rpm
                self.__speed = speed
                self.__ngear = ngear
                self.__throttle = throttle
                self.__brake = brake
                self.__drs = drs

            def __repr__(self):
                data = ", ".join((
                    f"rpm={self.__rpm}",
                    f"speed={self.__speed}",
                    f"ngear={self.__ngear}",
                    f"throttle={self.__throttle}",
                    f"brake={self.__brake}",
                    f"drs={self.__drs}",
                ))

                return f"{type(self).__name__}({data})"

        def __init__(
            self,
            entry_data: Dict[
                str,
                Dict[
                    Literal["Channels"],
                    Dict[
                        Literal["0", "2", "3", "4", "5", "45"],
                        int
                    ]
                ]
            ],
            timestamp: datetime,
        ):
            self.__timestamp = timestamp
            self.__channel_data: Dict[str, F1LTModel.CarDataEntry.ChannelData] = {}

            for rn, data in entry_data.items():
                self.__channel_data |= {
                    rn: F1LTModel.CarDataEntry.ChannelData(
                        data["Channels"]["0"],
                        data["Channels"]["2"],
                        data["Channels"]["3"],
                        data["Channels"]["4"],
                        data["Channels"]["5"],
                        data["Channels"]["45"],
                    )
                }

        def __repr__(self):
            data = ", ".join((
                f"timestamp={self.__timestamp}",
                f"channel_data={self.__channel_data}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def timestamp(self):
            return self.__timestamp

        @property
        def channel_data(self):
            return self.__channel_data

    class CurrentTyre:
        def __init__(self, compound: F1LTType.TyreCompound, new: bool):
            self.__compound = compound
            self.__new = new

        def __repr__(self):
            data = ", ".join((
                f"compound={self.__compound}",
                f"new={self.__new}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def compound(self):
            return self.__compound

        @compound.setter
        def compound(self, new_compound: F1LTType.TyreCompound):
            self.__compound = new_compound

        @property
        def new(self):
            return self.__new

        @new.setter
        def new(self, new_value: bool):
            self.__new = new_value

    class Driver:
        def __init__(self, racing_number: str, broadcast_name: Optional[str] = None,
                     full_name: Optional[str] = None, tla: Optional[str] = None,
                     team_name: Optional[str] = None, team_color: Optional[str] = None,
                     first_name: Optional[str] = None, last_name: Optional[str] = None,
                     reference: Optional[str] = None, headshot_url: Optional[str] = None,
                     country_code: Optional[str] = None):
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

        def __repr__(self):
            data = ", ".join((
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
            ))

            return f"{type(self).__name__}({data})"

        def __str__(self):
            if self.first_name and self.last_name:
                return f"{self.first_name} {self.last_name} ({self.racing_number})"

            return self.racing_number

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

        @team_name.setter
        def team_name(self, team_name: str):
            self.__team_name = team_name

        @property
        def team_color(self):
            return self.__team_color

        @team_color.setter
        def team_color(self, team_color: str):
            self.__team_color = team_color

        @property
        def first_name(self):
            return self.__first_name

        @first_name.setter
        def first_name(self, first_name: str):
            self.__first_name = first_name

        @property
        def last_name(self):
            return self.__last_name

        @last_name.setter
        def last_name(self, last_name: str):
            self.__last_name = last_name

        @property
        def reference(self):
            return self.__reference

        @reference.setter
        def reference(self, reference: str):
            self.__reference = reference

        @property
        def headshot_url(self):
            return self.__headshot_url

        @headshot_url.setter
        def headshot_url(self, headshot_url: str):
            self.__headshot_url = headshot_url

        @property
        def country_code(self):
            return self.__country_code

        @country_code.setter
        def country_code(self, country_code: str):
            self.__country_code = country_code

    class ExtrapolatedClock:
        def __init__(self, remanining: str, extrapolating: bool, timestamp: datetime):
            self.__remaining = remanining
            self.__extrapolating = extrapolating
            self.__timestamp = timestamp

        def __repr__(self):
            data = ", ".join((
                f"remanining={self.__remaining}",
                f"extrapolating={self.__extrapolating}",
                f"timestamp={self.__timestamp}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def remaining(self):
            return self.__remaining

        @property
        def extrapolating(self):
            return self.__extrapolating

        @property
        def timestamp(self):
            return self.__timestamp

        @remaining.setter
        def remaining(self, remaining: str):
            self.__remaining = remaining

        @extrapolating.setter
        def extrapolating(self, extrapolating: bool):
            self.__extrapolating = extrapolating

        @timestamp.setter
        def timestamp(self, timestamp: datetime):
            self.__timestamp = timestamp

    class LapCount:
        def __init__(self, current_lap: int, total_laps: int):
            self.__current_lap = current_lap
            self.__total_laps = total_laps

        def __repr__(self):
            data = ", ".join((
                f"current_lap={self.__current_lap}",
                f"total_laps={self.__total_laps}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def current_lap(self):
            return self.__current_lap

        @property
        def total_laps(self):
            return self.__total_laps

        @current_lap.setter
        def current_lap(self, new_current_lap: int):
            self.__current_lap = new_current_lap

        @total_laps.setter
        def total_laps(self, new_total_laps: int):
            self.__total_laps = new_total_laps

    class PositionEntry:
        class PositionData:
            def __init__(self, status: str, x: int, y: int, z: int):
                self.__status = status
                self.__x = x
                self.__y = y
                self.__z = z

            def __repr__(self):
                data = ", ".join((
                    f"status={self.__status}",
                    f"x={self.__x}",
                    f"y={self.__y}",
                    f"z={self.__z}",
                ))

                return f"{type(self).__name__}({data})"

            @property
            def status(self):
                return self.__status

            @property
            def x(self):
                return self.__x

            @property
            def y(self):
                return self.__y

            @property
            def z(self):
                return self.__z

        def __init__(
            self,
            entry_data: Dict[str, Dict[Literal["Status", "X", "Y", "Z"], str | int]],
            timestamp: datetime,
        ):
            self.__timestamp = timestamp
            self.__position_data: Dict[str, F1LTModel.PositionEntry.PositionData] = {}

            for rn, data in entry_data.items():
                self.__position_data |= {
                    rn: F1LTModel.PositionEntry.PositionData(data["Status"], data["X"], data["Y"],
                                                             data["Z"]),
                }

        def __repr__(self):
            data = ", ".join((
                f"timestamp={self.__timestamp}",
                f"position_data={self.__position_data}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def timestamp(self):
            return self.__timestamp

        @property
        def position_data(self):
            return self.__position_data

    class RaceControlMessage:
        def __init__(self, category: str, message: str, flag: Optional[str] = None,
                     scope: Optional[str] = None, racing_number: Optional[str] = None,
                     sector: Optional[int] = None, lap: Optional[int] = None,
                     status: Optional[str] = None):
            self.__category = category
            self.__message = message
            self.__flag = flag
            self.__scope = scope
            self.__racing_number = racing_number
            self.__sector = sector
            self.__lap = lap
            self.__status = status

        def __repr__(self):
            data = ", ".join((
                f"category={self.__category}",
                f"message={self.__message}",
                f"flag={self.__flag}",
                f"scope={self.__scope}",
                f"racing_number={self.__racing_number}",
                f"sector={self.__sector}",
                f"lap={self.__lap}",
                f"status={self.__status}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def category(self):
            return self.__category

        @property
        def message(self):
            return self.__message

        @property
        def flag(self):
            if not self.__flag:
                return

            return F1LTType.FlagStatus[self.__flag.replace(" ", "_")]

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
        def status(self):
            return self.__status

    class SessionData:
        class SeriesData:
            def __init__(self, **series_data: Union[str, int]):
                self.__lap: Optional[int] = series_data.get("Lap", None)
                self.__qualifying_part: Optional[int] = series_data.get("QualifyingPart", None)
                self.__timestamp = datetime_parser(series_data["Utc"])

            def __repr__(self):
                data = ", ".join((
                    f"timestamp={self.__timestamp}",
                    f"lap={self.__lap}",
                    f"qualifying_part={self.__qualifying_part}",
                ))

                return f"{type(self).__name__}({data})"

            @property
            def lap(self):
                return self.__lap

            @property
            def qualifying_part(self):
                return self.__qualifying_part

            @property
            def timestamp(self):
                return self.__timestamp

        class StatusSeriesData:
            def __init__(self, **status_series_data: Union[str, F1LTType.SessionStatus,
                                                           F1LTType.TrackStatus2]):
                self.__session_status: Optional[F1LTType.SessionStatus] = \
                    status_series_data.get("SessionStatus", None)
                self.__timestamp = datetime_parser(status_series_data["Utc"])
                self.__track_status: Optional[F1LTType.TrackStatus2] = \
                    status_series_data.get("TrackStatus", None)

            def __repr__(self):
                data = ", ".join((
                    f"session_status={self.__session_status}",
                    f"timestamp={self.__timestamp}",
                    f"track_status={self.__track_status}",
                ))

                return f"{type(self).__name__}({data})"

            @property
            def session_status(self):
                return self.__session_status

            @property
            def timestamp(self):
                return self.__timestamp

            @property
            def track_status(self):
                return self.__track_status

        def __init__(self, series_data: List[Dict[str, Union[str, int]]],
                     status_series_data: List[Dict[str, Union[str, F1LTType.SessionStatus,
                                                              F1LTType.TrackStatus2]]]):
            self.__series_data: List[F1LTModel.SessionData.SeriesData] = []
            self.__status_series_data: List[F1LTModel.SessionData.StatusSeriesData] = []

            for data in series_data:
                self.add_series_data(**data)

            for data in status_series_data:
                self.add_status_series_data(**data)

        def __repr__(self):
            data = ", ".join((
                f"series_data={self.__series_data}",
                f"status_series_data={self.__status_series_data}",
            ))

            return f"{type(self).__name__}({data})"

        def add_series_data(self, **series_data: Union[str, int]):
            self.__series_data.append(F1LTModel.SessionData.SeriesData(**series_data))

        def add_status_series_data(
            self,
            **status_series_data: Union[str, F1LTType.SessionStatus, F1LTType.TrackStatus2],
        ):
            self.__status_series_data.append(
                F1LTModel.SessionData.StatusSeriesData(**status_series_data),
            )

        @property
        def series_data(self):
            return self.__series_data

        @property
        def status_series_data(self):
            return self.__status_series_data

    class SessionInfo:
        class Meeting:
            class Circuit:
                def __init__(self, **data: Union[int, str]):
                    self.__key: int = data["Key"]
                    self.__short_name: str = data["ShortName"]

                def __repr__(self):
                    data = ", ".join((
                        f"key={self.__key}",
                        f"short_name={self.__short_name}",
                    ))

                    return f"{type(self).__name__}({data})"

                @property
                def key(self):
                    return self.__key

                @property
                def short_name(self):
                    return self.__short_name

            class Country:
                def __init__(self, **data: Union[int, str]):
                    self.__code: str = data["Code"]
                    self.__key: int = data["Key"]
                    self.__name: str = data["Name"]

                def __repr__(self):
                    data = ", ".join((
                        f"code={self.__code}",
                        f"key={self.__key}",
                        f"name={self.__name}",
                    ))

                    return f"{type(self).__name__}({data})"

                @property
                def key(self):
                    return self.__key

                @property
                def code(self):
                    return self.__code

                @property
                def name(self):
                    return self.__name

            def __init__(self, **data: Union[int, str, Dict[str, Union[str, int]]]):
                self.__key: int = data["Key"]
                self.__name: str = data["Name"]
                self.__official_name: str = data["OfficialName"]
                self.__location: str = data["Location"]
                self.__country = F1LTModel.SessionInfo.Meeting.Country(**data["Country"])
                self.__circuit = F1LTModel.SessionInfo.Meeting.Circuit(**data["Circuit"])

            def __repr__(self):
                data = ", ".join((
                    f"key={self.__key}",
                    f"name={self.__name}",
                    f"official_name={self.__official_name}",
                    f"location={self.__location}",
                    f"country={self.__country}",
                    f"circuit={self.__circuit}",
                ))

                return f"{type(self).__name__}({data})"

            @property
            def key(self):
                return self.__key

            @property
            def name(self):
                return self.__name

            @property
            def official_name(self):
                return self.__official_name

            @property
            def location(self):
                return self.__location

            @property
            def country(self):
                return self.__country

            @property
            def circuit(self):
                return self.__circuit

        def __init__(self, meeting: Dict[Literal["Key", "Name", "OfficialName", "Location",
                                                 "Country", "Circuit"], Union[int, str]],
                     archive_status: Dict[Literal["Status"], Literal["Complete", "Generating"]],
                     key: int, type: str, name: str, start_date: str, end_date: str,
                     gmt_offset: str, path: str, number: Optional[int] = None):
            self.__meeting = F1LTModel.SessionInfo.Meeting(**meeting)
            self.__archive_status = F1LTModel.ArchiveStatus(archive_status["Status"])
            self.__key = key
            self.__type = type
            self.__name = name
            self.__start_date = start_date
            self.__end_date = end_date
            self.__gmt_offset = gmt_offset
            self.__path = path
            self.__number = number

        def __repr__(self):
            data = ", ".join((
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
            ))

            return f"{type(self).__name__}({data})"

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

    class TeamRadio:
        def __init__(self, racing_number: str, path: str, timestamp: str):
            self.__racing_number = racing_number
            self.__path = path
            self.__timestamp = timestamp

        def __repr__(self):
            data = ", ".join((
                f"racing_number={self.__racing_number}",
                f"path={self.__path}",
                f"timestamp={self.__timestamp}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def racing_number(self):
            return self.__racing_number

        @property
        def path(self):
            return self.__path

        @property
        def timestamp(self):
            return self.__timestamp

    class TimingAppData:
        class Stint:
            def __init__(
                self,
                lap_flags: int,
                compound: F1LTType.TyreCompound,
                new: bool,
                tyre_not_changed: bool,
                total_laps: int,
                start_laps: int,
                lap_time: Optional[str] = None,
                lap_number: Optional[int] = None,
            ):
                self.__lap_flags = lap_flags
                self.__compound = compound
                self.__new = new
                self.__tyre_not_changed = tyre_not_changed
                self.__total_laps = total_laps
                self.__start_laps = start_laps
                self.__lap_time = lap_time
                self.__lap_number = lap_number
                self.__corrected = False

            def __repr__(self):
                data = ", ".join((
                    f"lap_flags={self.__lap_flags}",
                    f"compound={self.__compound}",
                    f"new={self.__new}",
                    f"tyre_not_changed={self.__tyre_not_changed}",
                    f"total_laps={self.__total_laps}",
                    f"start_laps={self.__start_laps}",
                    f"lap_time={self.__lap_time}",
                    f"lap_number={self.__lap_number}",
                    f"corrected={self.__corrected}",
                ))

                return f"{type(self).__name__}({data})"

            @property
            def corrected(self):
                return self.__corrected

            @property
            def lap_flags(self):
                return self.__lap_flags

            @lap_flags.setter
            def lap_flags(self, new_lap_flags: int):
                self.__lap_flags = new_lap_flags

            @property
            def compound(self):
                return self.__compound

            @compound.setter
            def compound(self, new_compound: F1LTType.TyreCompound):
                self.__corrected = True
                self.__compound = new_compound

            @property
            def new(self):
                return self.__new

            @new.setter
            def new(self, new_value: bool):
                self.__corrected = True
                self.__new = new_value

            @property
            def tyre_not_changed(self):
                return self.__tyre_not_changed

            @tyre_not_changed.setter
            def tyre_not_changed(self, new_tyre_not_changed: bool):
                self.__corrected = True
                self.__tyre_not_changed = new_tyre_not_changed

            @property
            def total_laps(self):
                return self.__total_laps

            @total_laps.setter
            def total_laps(self, new_total_laps: int):
                self.__total_laps = new_total_laps

            @property
            def start_laps(self):
                return self.__start_laps

            @start_laps.setter
            def start_laps(self, new_start_laps: int):
                self.__start_laps = new_start_laps

            @property
            def lap_time(self):
                return self.__lap_time

            @lap_time.setter
            def lap_time(self, new_lap_time: str):
                self.__lap_time = new_lap_time

            @property
            def lap_number(self):
                return self.__lap_number

            @lap_number.setter
            def lap_number(self, new_lap_number: int):
                self.__lap_number = new_lap_number

        def __init__(
            self,
            racing_number: str,
            grid_position: Optional[str] = None,
        ):
            self.__racing_number = racing_number
            self.__grid_position = grid_position
            self.__stints: List[F1LTModel.TimingAppData.Stint] = []

        def __repr__(self):
            data = ", ".join((
                f"racing_number={self.__racing_number}",
                f"grid_position={self.__grid_position}",
                f"stints={self.__stints}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def racing_number(self):
            return self.__racing_number

        @property
        def grid_position(self):
            return self.__grid_position

        @grid_position.setter
        def grid_position(self, new_position: str):
            self.__grid_position = new_position

        @property
        def stints(self):
            return self.__stints

    class TimingStats:
        def __init__(
            self,
            racing_number: str,
            best_lap_time: Optional[str] = None,
            best_time_lap_number: Optional[int] = None,
            best_time_position: Optional[int] = None,
            best_sector_1_time: Optional[str] = None,
            sector_1_position: Optional[int] = None,
            best_sector_2_time: Optional[str] = None,
            sector_2_position: Optional[int] = None,
            best_sector_3_time: Optional[str] = None,
            sector_3_position: Optional[int] = None,
            best_intermediate_1_speed: Optional[str] = None,
            intermediate_1_position: Optional[int] = None,
            best_intermediate_2_speed: Optional[str] = None,
            intermediate_2_position: Optional[int] = None,
            best_finish_line_speed: Optional[str] = None,
            finish_line_position: Optional[int] = None,
            best_speed_trap_speed: Optional[str] = None,
            speed_trap_position: Optional[int] = None,
        ):
            self.__racing_number = racing_number

            if best_lap_time:
                [lap_min, lap_sec] = best_lap_time.split(":")
                self.__best_lap_time = timedelta(minutes=int(lap_min),
                                                 seconds=round(float(lap_sec), 3))

            else:
                self.__best_lap_time = None

            if best_time_lap_number:
                self.__best_time_lap_number = best_time_lap_number

            else:
                self.__best_time_lap_number = None

            if best_time_position:
                self.__best_time_position = best_time_position

            else:
                self.__best_time_position = None

            if best_sector_1_time:
                self.__best_sector_1 = round(float(best_sector_1_time), 3)

            else:
                self.__best_sector_1 = None

            if sector_1_position:
                self.__sector_1_position = sector_1_position

            else:
                self.__sector_1_position = None

            if best_sector_2_time:
                self.__best_sector_2 = round(float(best_sector_2_time), 3)

            else:
                self.__best_sector_2 = None

            if sector_2_position:
                self.__sector_2_position = sector_2_position

            else:
                self.__sector_2_position = None

            if best_sector_3_time:
                self.__best_sector_3 = round(float(best_sector_3_time), 3)

            else:
                self.__best_sector_3 = None

            if sector_3_position:
                self.__sector_3_position = sector_3_position

            else:
                self.__sector_3_position = None

            if best_intermediate_1_speed:
                self.__best_intermediate_1_speed = int(best_intermediate_1_speed)

            else:
                self.__best_intermediate_1_speed = None

            if intermediate_1_position:
                self.__intermediate_1_position = intermediate_1_position

            else:
                self.__intermediate_1_position = None

            if best_intermediate_2_speed:
                self.__best_intermediate_2_speed = int(best_intermediate_2_speed)

            else:
                self.__best_intermediate_2_speed = None

            if intermediate_2_position:
                self.__intermediate_2_position = intermediate_2_position

            else:
                self.__intermediate_2_position = None

            if best_finish_line_speed:
                self.__best_finish_line_speed = int(best_finish_line_speed)

            else:
                self.__best_finish_line_speed = None

            if finish_line_position:
                self.__finish_line_position = finish_line_position

            else:
                self.__finish_line_position = None

            if best_speed_trap_speed:
                self.__best_speed_trap_speed = int(best_speed_trap_speed)

            else:
                self.__best_speed_trap_speed = None

            if speed_trap_position:
                self.__speed_trap_position = speed_trap_position

            else:
                self.__speed_trap_position = None

        @property
        def racing_number(self):
            return self.__racing_number

        @property
        def best_lap_time(self):
            return self.__best_lap_time

        @best_lap_time.setter
        def best_lap_time(self, new_lap_time: str):
            [lap_min, lap_sec] = new_lap_time.split(":")
            self.__best_lap_time = timedelta(minutes=int(lap_min),
                                             seconds=round(float(lap_sec), 3))

        @property
        def best_time_lap_number(self):
            return self.__best_time_lap_number

        @best_time_lap_number.setter
        def best_time_lap_number(self, new_lap_number: int):
            self.__best_time_lap_number = new_lap_number

        @property
        def best_time_position(self):
            return self.__best_time_position

        @best_time_position.setter
        def best_time_position(self, new_position: int):
            self.__best_time_position = new_position

        @property
        def best_sector_1(self):
            return self.__best_sector_1

        @best_sector_1.setter
        def best_sector_1(self, new_sector_time: str):
            self.__best_sector_1 = round(float(new_sector_time), 3)

        @property
        def sector_1_position(self):
            return self.__sector_1_position

        @sector_1_position.setter
        def sector_1_position(self, sector_position: int):
            self.__sector_1_position = sector_position

        @property
        def best_sector_2(self):
            return self.__best_sector_2

        @best_sector_2.setter
        def best_sector_2(self, new_sector_time: str):
            self.__best_sector_2 = round(float(new_sector_time), 3)

        @property
        def sector_2_position(self):
            return self.__sector_2_position

        @sector_2_position.setter
        def sector_2_position(self, sector_position: int):
            self.__sector_2_position = sector_position

        @property
        def best_sector_3(self):
            return self.__best_sector_3

        @best_sector_3.setter
        def best_sector_3(self, new_sector_time: str):
            self.__best_sector_3 = round(float(new_sector_time), 3)

        @property
        def sector_3_position(self):
            return self.__sector_3_position

        @sector_3_position.setter
        def sector_3_position(self, sector_position: int):
            self.__sector_3_position = sector_position

        @property
        def best_intermediate_1_speed(self):
            return self.__best_intermediate_1_speed

        @best_intermediate_1_speed.setter
        def best_intermediate_1_speed(self, new_speed: str):
            self.__best_intermediate_1_speed = int(new_speed)

        @property
        def intermediate_1_position(self):
            return self.__intermediate_1_position

        @intermediate_1_position.setter
        def intermediate_1_position(self, new_position: int):
            self.__intermediate_1_position = int(new_position)

        @property
        def best_intermediate_2_speed(self):
            return self.__best_intermediate_2_speed

        @best_intermediate_2_speed.setter
        def best_intermediate_2_speed(self, new_speed: str):
            self.__best_intermediate_2_speed = int(new_speed)

        @property
        def intermediate_2_position(self):
            return self.__intermediate_2_position

        @intermediate_2_position.setter
        def intermediate_2_position(self, new_position: int):
            self.__intermediate_2_position = int(new_position)

        @property
        def best_finish_line_speed(self):
            return self.__best_finish_line_speed

        @best_finish_line_speed.setter
        def best_finish_line_speed(self, new_speed: str):
            self.__best_finish_line_speed = int(new_speed)

        @property
        def finish_line_position(self):
            return self.__finish_line_position

        @finish_line_position.setter
        def finish_line_position(self, new_position: int):
            self.__finish_line_position = int(new_position)

        @property
        def best_speed_trap_speed(self):
            return self.__best_speed_trap_speed

        @best_speed_trap_speed.setter
        def best_speed_trap_speed(self, new_speed: str):
            self.__best_speed_trap_speed = int(new_speed)

        @property
        def speed_trap_position(self):
            return self.__speed_trap_position

        @speed_trap_position.setter
        def speed_trap_position(self, new_position: int):
            self.__speed_trap_position = int(new_position)

        def __repr__(self):
            data = ", ".join((
                f"racing_number={self.__racing_number}",
                f"best_lap_time={self.__best_lap_time}",
                f"best_time_lap_number={self.__best_time_lap_number}",
                f"best_time_position={self.__best_time_position}",
                f"best_sector_1={self.__best_sector_1}",
                f"sector_1_position={self.__sector_1_position}",
                f"best_sector_2={self.__best_sector_2}",
                f"sector_2_position={self.__sector_2_position}",
                f"best_sector_3={self.__best_sector_3}",
                f"sector_3_position={self.__sector_3_position}",
                f"best_intermediate_1_speed={self.__best_intermediate_1_speed}",
                f"intermediate_1_position={self.__intermediate_1_position}",
                f"best_intermediate_2_speed={self.__best_intermediate_2_speed}",
                f"intermediate_2_position={self.__intermediate_2_position}",
                f"best_finish_line_speed={self.__best_finish_line_speed}",
                f"finish_line_position={self.__finish_line_position}",
                f"best_speed_trap_speed={self.__best_speed_trap_speed}",
                f"speed_trap_position={self.__speed_trap_position}",
            ))

            return f"{type(self).__name__}({data})"

    class TrackStatus:
        def __init__(self, status: F1LTType.TrackStatus, message: str):
            self.__status = status
            self.__message = message

        def __repr__(self):
            data = ", ".join((
                f"status={self.status_string}",
                f"message={self.__message}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def status(self):
            return self.__status

        @property
        def status_string(self):
            if self.__status == F1LTType.TrackStatus.ALL_CLEAR:
                return "All Clear"

            elif self.__status == F1LTType.TrackStatus.YELLOW:
                return "Yellow"

            elif self.__status == F1LTType.TrackStatus.GREEN:
                return "Green"

            elif self.__status == F1LTType.TrackStatus.SC_DEPLOYED:
                return "Safety Car Deployed"

            elif self.__status == F1LTType.TrackStatus.RED:
                return "Red"

            elif self.__status == F1LTType.TrackStatus.VSC_DEPLOYED:
                return "Virtual Safety Car Deployed"

            elif self.__status == F1LTType.TrackStatus.VSC_ENDING:
                return "Virtual Safety Car Ending"

            else:
                return self.__status

        @property
        def message(self):
            return self.__message

        @status.setter
        def status(self, status: F1LTType.TrackStatus):
            self.__status = status

        @message.setter
        def message(self, message: str):
            self.__message = message

    class WeatherData:
        def __init__(self, air_temp: str, humidity: str, pressure: str, rainfall: str,
                     track_temp: str, wind_direction: str, wind_speed: str):
            self.__air_temp = round(float(air_temp), 1)
            self.__humidity = round(float(humidity), 1)
            self.__pressure = round(float(pressure), 1)
            self.__rainfall = int(rainfall) == 1
            self.__track_temp = round(float(track_temp), 1)
            self.__wind_direction = int(wind_direction)
            self.__wind_speed = round(float(wind_speed) * 3.6, 2)

        def __repr__(self):
            data = ", ".join((
                f"air_temp={self.__air_temp}",
                f"humidity={self.__humidity}",
                f"pressure={self.__pressure}",
                f"rainfall={self.__rainfall}",
                f"track_temp={self.__track_temp}",
                f"wind_direction={self.__wind_direction}",
                f"wind_speed={self.__wind_speed}",
            ))

            return f"{type(self).__name__}({data})"

        @property
        def air_temp(self):
            return self.__air_temp

        @air_temp.setter
        def air_temp(self, new_air_temp: str):
            self.__air_temp = round(float(new_air_temp), 1)

        @property
        def humidity(self):
            return self.__humidity

        @humidity.setter
        def humidity(self, new_humidity: str):
            self.__humidity = round(float(new_humidity), 1)

        @property
        def pressure(self):
            return self.__pressure

        @pressure.setter
        def pressure(self, new_pressure: str):
            self.__pressure = round(float(new_pressure), 1)

        @property
        def rainfall(self):
            return self.__rainfall

        @rainfall.setter
        def rainfall(self, new_rainfall: str):
            self.__rainfall = int(new_rainfall) == 1

        @property
        def track_temp(self):
            return self.__track_temp

        @track_temp.setter
        def track_temp(self, new_track_temp: str):
            self.__track_temp = round(float(new_track_temp), 1)

        @property
        def wind_direction(self):
            return self.__wind_direction

        @wind_direction.setter
        def wind_direction(self, new_wind_direction: str):
            self.__wind_direction = int(new_wind_direction)

        @property
        def wind_speed(self):
            return self.__wind_speed

        @wind_speed.setter
        def wind_speed(self, new_wind_speed: str):
            self.__wind_speed = round(float(new_wind_speed) * 3.6, 2)
