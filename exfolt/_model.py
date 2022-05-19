# pyeXF1LT - Unofficial F1 live timing client
# Copyright (C) 2022  eXhumer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from ._type import TimingDataStatus, TrackStatus


class DriverData:
    def __init__(
        self,
        racing_number: str,
        first_name: str | None = None,
        last_name: str | None = None,
        headshot_url: str | None = None,
    ) -> None:
        self.__rn = racing_number
        self.__fn = first_name
        self.__ln = last_name
        self.__hu = headshot_url

    def __repr__(self) -> str:
        return (
            "DriverData(" +
            ", ".join((
                f"racing_number={self.__rn}",
                f"first_name={self.__fn}",
                f"last_name={self.__ln}",
                f"headshot_url={self.__hu}",
            )) +
            ")"
        )

    @property
    def racing_number(self):
        return self.__rn

    @property
    def first_name(self):
        return self.__fn

    @property
    def last_name(self):
        return self.__ln

    @property
    def headshot_url(self):
        return self.__hu

    def __str__(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.racing_number})"

        return self.racing_number


class ExtrapolatedData:
    def __init__(
        self,
        remanining: str,
        extrapolating: bool | None = None,
    ) -> None:
        self.__remaining = remanining
        self.__extrapolating = extrapolating

    def __repr__(self) -> str:
        return (
            "ExtrapolatedData(" +
            ", ".join((
                f"remanining={self.__remaining}",
                f"extrapolating={self.__extrapolating}",
            )) +
            ")"
        )

    @property
    def remaining(self):
        return self.__remaining

    @property
    def extrapolating(self):
        return self.__extrapolating


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


class RaceControlMessageData:
    def __init__(
        self,
        category: str,
        message: str,
        flag: str | None = None,
        scope: str | None = None,
        driver_data: DriverData | None = None,
        sector: int | None = None,
        lap: int | None = None,
        drs_status: str | None = None,
    ) -> None:
        self.__category = category
        self.__message = message
        self.__flag = flag
        self.__scope = scope
        self.__driver_data = driver_data
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
                f"driver_data={self.__driver_data}",
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
    def driver_data(self):
        return self.__driver_data

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
    def __init__(
        self,
        official_name: str,
        name: str,
        location: str,
        country: str,
        circuit: str,
        type: str,
        start_date: str,
        end_date: str,
        gmt_offset: str,
    ) -> None:
        self.__official_name = official_name
        self.__name = name
        self.__location = location
        self.__country = country
        self.__circuit = circuit
        self.__type = type
        self.__start_date = start_date
        self.__end_date = end_date
        self.__gmt_offset = gmt_offset

    def __repr__(self) -> str:
        return (
            "SessionInfoData(" +
            ", ".join((
                f"official_name={self.__official_name}",
                f"name={self.__name}",
                f"location={self.__location}",
                f"country={self.__country}",
                f"circuit={self.__circuit}",
                f"type={self.__type}",
                f"start_date={self.__start_date}",
                f"end_date={self.__end_date}",
                f"gmt_offset={self.__gmt_offset}",
            )) +
            ")"
        )

    @property
    def official_name(self):
        return self.__official_name

    @property
    def name(self):
        return self.__name

    @property
    def location(self):
        return self.__location

    @property
    def country(self):
        return self.__country

    @property
    def circuit(self):
        return self.__circuit

    @property
    def type(self):
        return self.__type

    @property
    def start_date(self):
        return self.__start_date

    @property
    def end_date(self):
        return self.__end_date

    @property
    def gmt_offset(self):
        return self.__gmt_offset


class TimingData:
    def __init__(
        self,
        driver_data: DriverData,
        sector_number: int,
        segment_number: int,
        segment_status: TimingDataStatus,
    ) -> None:
        self.__dd = driver_data
        self.__sec_num = sector_number
        self.__seg_num = segment_number
        self.__seg_sta = segment_status

    def __repr__(self) -> str:
        return (
            "TimingData(" +
            ", ".join((
                f"driver_data={self.__dd}",
                f"sector_number={self.__sec_num}",
                f"segment_number={self.__seg_num}",
                f"segment_status={self.__seg_sta}",
            )) +
            ")"
        )

    @property
    def driver_data(self):
        return self.__dd

    @property
    def sector_number(self):
        return self.__sec_num

    @property
    def segment_number(self):
        return self.__seg_num

    @property
    def segment_status(self):
        return self.__seg_sta


class TrackStatusData:
    def __init__(self, status: TrackStatus, message: str) -> None:
        self.__status = status
        self.__message = message

    def __repr__(self) -> str:
        return (
            "TrackStatusData(" +
            ", ".join((
                f"status={self.status}",
                f"message={self.__message}",
            )) +
            ")"
        )

    @property
    def status(self):
        if self.__status == TrackStatus.ALL_CLEAR:
            return "All Clear"

        elif self.__status == TrackStatus.YELLOW:
            return "Yellow"

        elif self.__status == TrackStatus.GREEN:
            return "Green"

        elif self.__status == TrackStatus.SC_DEPLOYED:
            return "Safety Car Deployed"

        elif self.__status == TrackStatus.RED:
            return "Red"

        elif self.__status == TrackStatus.VSC_DEPLOYED:
            return "Virtual Safety Car Deployed"

        elif self.__status == TrackStatus.VSC_ENDING:
            return "Virtual Safety Car Ending"

        else:
            return self.__status

    @property
    def message(self):
        return self.__message


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
