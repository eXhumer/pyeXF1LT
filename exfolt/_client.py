from datetime import date, datetime, timedelta
from json import loads
from queue import Queue
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from requests import Session

from ._model import F1LTModel
from ._signalr import SignalRClient
from ._type import F1LTType
from ._utils import datetime_parser, decompress_zlib_data, timedelta_parser


class F1ArchiveClient:
    """
    F1 client to receive SignalR messages from an archived session
    """

    STATIC_URL = "https://livetiming.formula1.com/static"

    def __init__(self, path: str, *topics: F1LTType.StreamingTopic,
                 session: Optional[Session] = None):
        if not session:
            session = Session()

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/{path}ArchiveStatus.json")
        res.raise_for_status()

        archive_status: str = loads(res.content.decode("utf-8-sig"))["Status"]
        assert archive_status == "Complete", f"Unexpected archive status \"{archive_status}\"!"

        self.__path = path
        self.__topics = topics
        self.__session = session
        self.__data_queue: Queue[Tuple[F1LTType.StreamingTopic, Dict[str, Any], timedelta]] = \
            Queue()
        self.__load_data()

    def __iter__(self):
        return self

    def __next__(self):
        if self.__data_queue.qsize() == 0:
            raise StopIteration

        return self.__data_queue.get()

    def __load_data(self):
        data_entries: List[Tuple[F1LTType.StreamingTopic, Dict[str, Any], timedelta]] = []

        for topic in self.__topics:
            res = self.__session.get(
                "".join((
                    f"{F1ArchiveClient.STATIC_URL}/{self.__path}",
                    f"{topic}.jsonStream",
                )),
            )
            res.raise_for_status()

            if not topic.endswith(".z"):
                data_entries.extend([
                    (topic, loads(data_entry[12:]), timedelta_parser(data_entry[:12]))
                    for data_entry
                    in res.content.decode(encoding="utf-8-sig").replace("\r", "").split("\n")
                    if len(data_entry) > 0
                ])

            else:
                data_entries.extend([
                    (
                        topic,
                        loads(decompress_zlib_data(data_entry[13:-1])),
                        timedelta_parser(data_entry[:12])
                    )
                    for data_entry
                    in res.content.decode(encoding="utf-8-sig").replace("\r", "").split("\n")
                    if len(data_entry) > 0
                ])

        data_entries.sort(key=lambda entry: entry[2])

        for data_entry in data_entries:
            self.__data_queue.put(data_entry)

    @classmethod
    def get_session(
        cls,
        event_name: str,
        event_date: date,
        session_name: str,
        session_date: date,
        *topics: F1LTType.StreamingTopic,
        session: Optional[Session] = None,
    ):
        if not session:
            session = Session()

        path = "/".join((
            str(event_date.year),
            "_".join((
                event_date.strftime("%Y-%m-%d"),
                event_name.replace(" ", "_"),
            )),
            "_".join((
                session_date.strftime("%Y-%m-%d"),
                session_name.replace(" ", "_"),
            )),
        )) + "/"

        return cls(path, *topics, session=session)

    @classmethod
    def get_last_session(cls, *topics: F1LTType.StreamingTopic, session: Optional[Session] = None):
        if not session:
            session = Session()

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/StreamingStatus.json")
        res.raise_for_status()
        streaming_status = loads(res.content.decode("utf-8-sig"))
        assert streaming_status["Status"] == "Offline", "Use F1LiveClient class for live sessions!"

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/SessionInfo.json")
        res.raise_for_status()
        session_info = loads(res.content.decode("utf-8-sig"))

        return cls(session_info["Path"], *topics, session=session)


class F1LiveClient(SignalRClient):
    """
    F1 client to receive SignalR messages from a live session
    """

    URL = "https://livetiming.formula1.com/signalr"

    def __init__(self, *topics: F1LTType.StreamingTopic, reconnect: bool = True):
        super().__init__(F1LiveClient.URL, {F1LTType.Hub.STREAMING: topics}, reconnect=reconnect)


class F1TimingClient:
    """
    Timing client to handle streamed session data from F1 sessions.
    """

    def __init__(self):
        self.__archive_status: Optional[F1LTModel.ArchiveStatus] = None
        self.__audio_streams: List[F1LTModel.AudioStream] = []
        self.__car_data_entries: List[F1LTModel.CarDataEntry] = []
        self.__change_queue: Queue[
            Tuple[
                F1LTType.StreamingTopic,
                Union[
                    F1LTModel.ArchiveStatus,
                    F1LTModel.AudioStream,
                    F1LTModel.CurrentTyre,
                    F1LTModel.ExtrapolatedClock,
                    F1LTModel.LapCount,
                    F1LTModel.RaceControlMessage,
                    F1LTModel.SessionData,
                    F1LTModel.SessionInfo,
                    F1LTType.SessionStatus,
                    F1LTModel.TeamRadio,
                    F1LTModel.TimingAppData,
                    F1LTModel.TrackStatus,
                    F1LTModel.WeatherData,
                    Dict[str, F1LTModel.TimingStats],
                    List[F1LTModel.CarDataEntry],
                    List[F1LTModel.PositionEntry],
                ],
                Dict[str, Any],
                Union[datetime, timedelta],
            ]
        ] = Queue()
        self.__current_tyres: Dict[str, F1LTModel.CurrentTyre] = {}
        self.__drivers: Dict[str, F1LTModel.Driver] = {}
        self.__extrapolated_clock: Optional[F1LTModel.ExtrapolatedClock] = None
        self.__lap_count: Optional[F1LTModel.LapCount] = None
        self.__position_entries: List[F1LTModel.PositionEntry] = []
        self.__race_control_messages: List[F1LTModel.RaceControlMessage] = []
        self.__session_data: Optional[F1LTModel.SessionData] = None
        self.__session_info: Optional[F1LTModel.SessionInfo] = None
        self.__session_status: Optional[F1LTType.SessionStatus] = None
        self.__team_radios: List[F1LTModel.TeamRadio] = []
        self.__timing_app_data: Dict[str, F1LTModel.TimingAppData] = {}
        self.__timing_stats: Dict[str, F1LTModel.TimingStats] = {}
        self.__track_status: Optional[F1LTModel.TrackStatus] = None
        self.__weather_data: Optional[F1LTModel.WeatherData] = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.__change_queue.qsize() > 0:
            return self.__change_queue.get()

        raise StopIteration

    def __repr__(self):
        data = ", ".join((
            f"archive_status={self.__archive_status}",
            f"audio_streams={self.__audio_streams}",
            f"car_data_entries={self.__car_data_entries}",
            f"change_queue={self.__change_queue}",
            f"current_tyres={self.__current_tyres}",
            f"drivers={self.__drivers}",
            f"extrapolated_clock={self.__extrapolated_clock}",
            f"lap_count={self.__lap_count}",
            f"position_entries={self.__position_entries}",
            f"race_control_messages={self.__race_control_messages}",
            f"session_data={self.__session_data}",
            f"session_info={self.__session_info}",
            f"session_status={self.__session_status}",
            f"team_radios={self.__team_radios}",
            f"timing_app_data={self.__timing_app_data}",
            f"timing_stats={self.__timing_stats}",
            f"track_status={self.__track_status}",
            f"weather_data={self.__weather_data}",
        ))

        return f"{type(self).__name__}({data})"

    def __update_driver_timing_stats(
        self,
        timing_stats_data: Dict[
            Literal["Lines"],
            Dict[
                Literal["RacingNumber", "PersonalBestLapTime", "BestSectors", "BestSpeeds"],
                Union[
                    str,
                    Dict[
                        Literal["Value", "Lap", "Position"],
                        Union[str, int],
                    ],
                    List[
                        Dict[
                            Literal["Value", "Position"],
                            Union[str, int],
                        ],
                    ],
                    Dict[
                        Literal["0", "1", "2"],
                        Dict[
                            Literal["Value", "Position"],
                            Union[str, int],
                        ],
                    ],
                    Dict[
                        Literal["I1", "I2", "ST", "FL"],
                        Dict[
                            Literal["Value", "Position"],
                            Union[str, int],
                        ],
                    ],
                ],
            ],
        ],
    ):
        for racing_number, driver_timing_stats in timing_stats_data["Lines"].items():
            if "RacingNumber" in driver_timing_stats:
                self.__timing_stats |= {
                    racing_number: F1LTModel.TimingStats(driver_timing_stats["RacingNumber"]),
                }

            if "PersonalBestLapTime" in driver_timing_stats:
                if "Value" in driver_timing_stats["PersonalBestLapTime"]:
                    if len(driver_timing_stats["PersonalBestLapTime"]["Value"]) > 0:
                        lap_time: str = driver_timing_stats["PersonalBestLapTime"]["Value"]
                        self.__timing_stats[racing_number].best_lap_time = lap_time

                if "Lap" in driver_timing_stats["PersonalBestLapTime"]:
                    lap: int = driver_timing_stats["PersonalBestLapTime"]["Lap"]
                    self.__timing_stats[racing_number].best_time_lap_number = lap

                if "Position" in driver_timing_stats["PersonalBestLapTime"]:
                    pos: int = driver_timing_stats["PersonalBestLapTime"]["Position"]
                    self.__timing_stats[racing_number].best_time_position = pos

            if "BestSectors" in driver_timing_stats:
                if isinstance(driver_timing_stats["BestSectors"], list):
                    if len(driver_timing_stats["BestSectors"][0]["Value"]) > 0:
                        sector_time: str = driver_timing_stats["BestSectors"][0]["Value"]
                        self.__timing_stats[racing_number].best_sector_1 = sector_time

                    if "Position" in driver_timing_stats["BestSectors"][0]:
                        position: int = driver_timing_stats["BestSectors"][0]["Position"]
                        self.__timing_stats[racing_number].sector_1_position = position

                    if len(driver_timing_stats["BestSectors"][1]["Value"]) > 0:
                        sector_time: str = driver_timing_stats["BestSectors"][1]["Value"]
                        self.__timing_stats[racing_number].best_sector_2 = sector_time

                    if "Position" in driver_timing_stats["BestSectors"][1]:
                        position: int = driver_timing_stats["BestSectors"][1]["Position"]
                        self.__timing_stats[racing_number].sector_2_position = position

                    if len(driver_timing_stats["BestSectors"][2]["Value"]) > 0:
                        sector_time: str = driver_timing_stats["BestSectors"][2]["Value"]
                        self.__timing_stats[racing_number].best_sector_3 = sector_time

                    if "Position" in driver_timing_stats["BestSectors"][2]:
                        position: int = driver_timing_stats["BestSectors"][2]["Position"]
                        self.__timing_stats[racing_number].sector_3_position = position

                else:
                    for idx, sector_data in driver_timing_stats["BestSectors"].items():
                        assert idx in ["0", "1", "2"]

                        if "Value" in sector_data:
                            if len(sector_data["Value"]) > 0:
                                sector_time: str = sector_data["Value"]

                                if idx == "0":
                                    self.__timing_stats[racing_number].best_sector_1 = sector_time

                                elif idx == "1":
                                    self.__timing_stats[racing_number].best_sector_2 = sector_time

                                elif idx == "2":
                                    self.__timing_stats[racing_number].best_sector_3 = sector_time

                        if "Position" in sector_data:
                            position: int = sector_data["Position"]

                            if idx == "0":
                                self.__timing_stats[racing_number].sector_1_position = position

                            elif idx == "1":
                                self.__timing_stats[racing_number].sector_2_position = position

                            elif idx == "2":
                                self.__timing_stats[racing_number].sector_3_position = position

            if "BestSpeeds" in driver_timing_stats:
                if "I1" in driver_timing_stats["BestSpeeds"]:
                    if "Value" in driver_timing_stats["BestSpeeds"]["I1"]:
                        if len(driver_timing_stats["BestSpeeds"]["I1"]["Value"]) > 0:
                            speed: str = driver_timing_stats["BestSpeeds"]["I1"]["Value"]
                            self.__timing_stats[racing_number].best_intermediate_1_speed = speed

                    if "Position" in driver_timing_stats["BestSpeeds"]["I1"]:
                        position: int = driver_timing_stats["BestSpeeds"]["I1"]["Position"]
                        self.__timing_stats[racing_number].intermediate_1_position = position

                if "I2" in driver_timing_stats["BestSpeeds"]:
                    if "Value" in driver_timing_stats["BestSpeeds"]["I2"]:
                        if len(driver_timing_stats["BestSpeeds"]["I2"]["Value"]) > 0:
                            speed: str = driver_timing_stats["BestSpeeds"]["I2"]["Value"]
                            self.__timing_stats[racing_number].best_intermediate_2_speed = speed

                    if "Position" in driver_timing_stats["BestSpeeds"]["I2"]:
                        position: int = driver_timing_stats["BestSpeeds"]["I2"]["Position"]
                        self.__timing_stats[racing_number].intermediate_2_position = position

                if "FL" in driver_timing_stats["BestSpeeds"]:
                    if "Value" in driver_timing_stats["BestSpeeds"]["FL"]:
                        if len(driver_timing_stats["BestSpeeds"]["FL"]["Value"]) > 0:
                            speed: str = driver_timing_stats["BestSpeeds"]["FL"]["Value"]
                            self.__timing_stats[racing_number].best_finish_line_speed = speed

                    if "Position" in driver_timing_stats["BestSpeeds"]["FL"]:
                        position: int = driver_timing_stats["BestSpeeds"]["FL"]["Position"]
                        self.__timing_stats[racing_number].finish_line_position = position

                if "ST" in driver_timing_stats["BestSpeeds"]:
                    if "Value" in driver_timing_stats["BestSpeeds"]["ST"]:
                        if len(driver_timing_stats["BestSpeeds"]["ST"]["Value"]) > 0:
                            speed: str = driver_timing_stats["BestSpeeds"]["ST"]["Value"]
                            self.__timing_stats[racing_number].best_speed_trap_speed = speed

                    if "Position" in driver_timing_stats["BestSpeeds"]["ST"]:
                        position: int = driver_timing_stats["BestSpeeds"]["ST"]["Position"]
                        self.__timing_stats[racing_number].speed_trap_position = position

    @property
    def archive_status(self):
        return self.__archive_status

    @property
    def audio_streams(self):
        return self.__audio_streams

    @property
    def car_data_entries(self):
        return self.__car_data_entries

    @property
    def current_tyres(self):
        return self.__current_tyres

    @property
    def drivers(self):
        return self.__drivers

    @property
    def extrapolated_clock(self):
        return self.__extrapolated_clock

    @property
    def lap_count(self):
        return self.__lap_count

    @property
    def position_entries(self):
        return self.__position_entries

    def process_data(
        self,
        topic: F1LTType.StreamingTopic,
        data: Dict[str, Any],
        timestamp: Union[datetime, timedelta],
    ):
        if isinstance(timestamp, timedelta):
            timestamp = datetime.utcnow() + timestamp

        if topic in (
            F1LTType.StreamingTopic.CAR_DATA_Z,
            F1LTType.StreamingTopic.POSITION_Z,
        ):
            if topic == F1LTType.StreamingTopic.CAR_DATA_Z:
                car_data_entries: List[F1LTModel.CarDataEntry] = []

                for car_data in data["Entries"]:
                    car_data_entries.append(
                        F1LTModel.CarDataEntry(
                            car_data["Cars"],
                            datetime_parser(car_data["Utc"]),
                        ),
                    )

                self.__car_data_entries.extend(car_data_entries)

                self.__change_queue.put((
                    topic,
                    car_data_entries,
                    data,
                    timestamp,
                ))

            else:
                position_entries: List[F1LTModel.PositionEntry] = []

                for position_data in data["Position"]:
                    position_entries.append(
                        F1LTModel.PositionEntry(position_data["Entries"],
                                                datetime_parser(position_data["Timestamp"])),
                    )

                self.__position_entries.extend(position_entries)

                self.__change_queue.put((
                    topic,
                    position_entries,
                    data,
                    timestamp,
                ))

        else:
            assert isinstance(data, dict)

            if topic == F1LTType.StreamingTopic.ARCHIVE_STATUS:
                self.__archive_status = F1LTModel.ArchiveStatus(data["Status"])
                self.__change_queue.put((topic, self.__archive_status, data, timestamp))

            elif topic == F1LTType.StreamingTopic.AUDIO_STREAMS:
                self.__audio_streams = []

                for stream in data["Streams"]:
                    stream_data = F1LTModel.AudioStream(
                        stream["Name"],
                        stream["Language"],
                        stream["Uri"],
                        stream["Path"],
                    )
                    self.__audio_streams.append(stream_data)
                    self.__change_queue.put((topic, stream_data, data, timestamp))

            elif topic == F1LTType.StreamingTopic.CURRENT_TYRES:
                for racing_number, tyre_data in data["Tyres"].items():
                    if racing_number not in self.__current_tyres:
                        self.__current_tyres[racing_number] = \
                            F1LTModel.CurrentTyre(F1LTType.TyreCompound(tyre_data["Compound"]),
                                                  tyre_data["New"])

                    elif "Compound" in tyre_data:
                        self.__current_tyres[racing_number].compound = \
                            F1LTType.TyreCompound(tyre_data["Compound"])

                    elif "New" in tyre_data:
                        new: bool = tyre_data["New"]
                        self.__current_tyres[racing_number].new = new

                    self.__change_queue.put((topic, self.__current_tyres[racing_number], data,
                                             timestamp))

            elif topic == F1LTType.StreamingTopic.DRIVER_LIST:
                for key, value in data.items():
                    if key.startswith("_"):
                        continue

                    assert isinstance(value, dict)

                    if len(value) == 1 and "Line" in value:
                        continue

                    elif (
                        "RacingNumber" in value and
                        "BroadcastName" in value and
                        "FullName" in value and
                        "Tla" in value
                    ):
                        self.__drivers[key] = F1LTModel.Driver(
                            value["RacingNumber"],
                            broadcast_name=value["BroadcastName"],
                            full_name=value["FullName"],
                            tla=value["Tla"],
                            team_name=(
                                value["TeamName"]
                                if "TeamName" in value
                                else None
                            ),
                            team_color=(
                                value["TeamColour"]
                                if "TeamColour" in value
                                else None
                            ),
                            first_name=(
                                value["FirstName"]
                                if "FirstName" in value
                                else None
                            ),
                            last_name=(
                                value["LastName"]
                                if "LastName" in value
                                else None
                            ),
                            reference=(
                                value["Reference"]
                                if "Reference" in value
                                else None
                            ),
                            headshot_url=(
                                value["HeadshotUrl"]
                                if "HeadshotUrl" in value
                                else None
                            ),
                            country_code=(
                                value["CountryCode"]
                                if "CountryCode" in value
                                else None
                            ),
                        )

                    else:
                        drv_obj = self.__drivers[key]

                        if "TeamName" in value:
                            data: str = value["TeamName"]
                            drv_obj.team_name = data

                        if "TeamColour" in value:
                            data: str = value["TeamColour"]
                            drv_obj.team_color = data

                        if "FirstName" in value:
                            data: str = value["FirstName"]
                            drv_obj.first_name = data

                        if "LastName" in value:
                            data: str = value["LastName"]
                            drv_obj.last_name = data

                        if "Reference" in value:
                            data: str = value["Reference"]
                            drv_obj.reference = data

                        if "HeadshotUrl" in value:
                            data: str = value["HeadshotUrl"]
                            drv_obj.headshot_url = data

                        if "CountryCode" in value:
                            data: str = value["CountryCode"]
                            drv_obj.country_code = data

            elif topic == F1LTType.StreamingTopic.EXTRAPOLATED_CLOCK:
                if self.__extrapolated_clock is None:
                    self.__extrapolated_clock = F1LTModel.ExtrapolatedClock(
                        data["Remaining"],
                        data["Extrapolating"],
                        datetime_parser(data["Utc"]),
                    )

                else:
                    if "Remaining" in data:
                        self.__extrapolated_clock.remaining = data["Remaining"]

                    if "Extrapolating" in data:
                        self.__extrapolated_clock.extrapolating = \
                            data["Extrapolating"]

                    if "Utc" in data:
                        self.__extrapolated_clock.timestamp = datetime_parser(data["Utc"])

                self.__change_queue.put((
                    topic,
                    self.__extrapolated_clock,
                    data,
                    timestamp,
                ))

            elif topic == F1LTType.StreamingTopic.LAP_COUNT:
                if self.__lap_count is None:
                    self.__lap_count = F1LTModel.LapCount(data["CurrentLap"], data["TotalLaps"])

                else:
                    if "CurrentLap" in data:
                        self.__lap_count.current_lap = data["CurrentLap"]

                    if "TotalLaps" in data:
                        self.__lap_count.total_laps = data["TotalLaps"]

                self.__change_queue.put((
                    topic,
                    self.__lap_count,
                    data,
                    timestamp,
                ))

            elif topic == F1LTType.StreamingTopic.RACE_CONTROL_MESSAGES:
                messages = data["Messages"]

                if isinstance(messages, dict):
                    messages = list(messages.values())

                for message in messages:
                    rcm_data = F1LTModel.RaceControlMessage(
                        message["Category"],
                        message["Message"],
                        flag=(
                            message["Flag"]
                            if "Flag" in message
                            else None
                        ),
                        scope=(
                            message["Scope"]
                            if "Scope" in message
                            else None
                        ),
                        racing_number=(
                            messages["RacingNumber"]
                            if "RacingNumber" in messages
                            else None
                        ),
                        sector=(
                            messages["Sector"]
                            if "Sector" in messages
                            else None
                        ),
                        lap=(
                            messages["Lap"]
                            if "Lap" in messages
                            else None
                        ),
                        status=(
                            messages["Status"]
                            if "Status" in messages
                            else None
                        ),
                    )
                    self.__race_control_messages.append(rcm_data)
                    self.__change_queue.put((topic, rcm_data, data, timestamp))

            elif topic == F1LTType.StreamingTopic.SESSION_DATA:
                if (
                    "Series" in data and isinstance(data["Series"], list) and
                    "StatusSeries" in data and isinstance(data["StatusSeries"], list)
                ):
                    self.__session_data = F1LTModel.SessionData(
                        data["Series"],
                        data["StatusSeries"],
                    )

                assert self.__session_data

                if "Series" in data and isinstance(data["Series"], dict):
                    for series_data in data["Series"].values():
                        self.__session_data.add_series_data(**series_data)

                if "StatusSeries" in data and isinstance(data["StatusSeries"], dict):
                    for status_series_data in data["StatusSeries"].values():
                        self.__session_data.add_status_series_data(**status_series_data)

                self.__change_queue.put((topic, self.__session_data, data, timestamp))

            elif topic == F1LTType.StreamingTopic.SESSION_INFO:
                if "ArchiveStatus" in data and len(data) == 1:
                    self.__session_info.archive_status["Status"] = data["ArchiveStatus"]["Status"]

                else:
                    self.__session_info = F1LTModel.SessionInfo(
                        data["Meeting"],
                        data["ArchiveStatus"],
                        data["Key"],
                        data["Type"],
                        data["Name"],
                        data["StartDate"],
                        data["EndDate"],
                        data["GmtOffset"],
                        data["Path"],
                        number=(
                            data["Number"]
                            if "Number" in data
                            else None
                        ),
                    )

                self.__change_queue.put((
                    topic,
                    self.__session_info,
                    data,
                    timestamp,
                ))

            elif topic == F1LTType.StreamingTopic.SESSION_STATUS:
                self.__session_status = F1LTType.SessionStatus[
                    data["Status"].upper()
                ]
                self.__change_queue.put((
                    topic,
                    self.__session_status,
                    data,
                    timestamp,
                ))

            elif topic == F1LTType.StreamingTopic.TEAM_RADIO:
                team_radio_captures = data["Captures"]

                if isinstance(team_radio_captures, list):
                    self.__team_radios = []
                    team_radios = [team_radio_captures[0]]

                else:
                    team_radios = list(team_radio_captures.values())

                for team_radio in team_radios:
                    tr_data = F1LTModel.TeamRadio(
                        team_radio["RacingNumber"],
                        team_radio["Path"],
                        team_radio["Utc"],
                    )

                    self.__team_radios.append(tr_data)
                    self.__change_queue.put((topic, tr_data, data, timestamp))

            elif topic == F1LTType.StreamingTopic.TIMING_APP_DATA:
                for drv_num, timing_app_data in data["Lines"].items():
                    if drv_num == "_kf":
                        continue

                    if "RacingNumber" in timing_app_data:
                        tad = self.__timing_app_data[drv_num] = F1LTModel.TimingAppData(
                            timing_app_data["RacingNumber"],
                        )

                    else:
                        tad = self.__timing_app_data[drv_num]

                    if "Stints" in timing_app_data:
                        timing_stints = timing_app_data["Stints"]

                        if isinstance(timing_stints, list):
                            tad.stints.clear()

                            for stint_data in timing_stints:
                                tad.stints.append(
                                    F1LTModel.TimingAppData.Stint(
                                        stint_data["LapFlags"],
                                        F1LTType.TyreCompound[stint_data["Compound"]],
                                        stint_data["New"] == "true",
                                        stint_data["TyresNotChanged"] == "1",
                                        stint_data["TotalLaps"],
                                        stint_data["StartLaps"],
                                    )
                                )

                        else:
                            for idx, stint_data in timing_stints.items():
                                if int(idx) == len(tad.stints):
                                    assert "LapFlags" in stint_data
                                    assert "Compound" in stint_data
                                    assert "New" in stint_data
                                    assert "TyresNotChanged" in stint_data
                                    assert "TotalLaps" in stint_data
                                    assert "StartLaps" in stint_data

                                    tad.stints.append(
                                        F1LTModel.TimingAppData.Stint(
                                            stint_data["LapFlags"],
                                            F1LTType.TyreCompound[stint_data["Compound"]],
                                            stint_data["New"] == "true",
                                            stint_data["TyresNotChanged"] == "1",
                                            stint_data["TotalLaps"],
                                            stint_data["StartLaps"],
                                        )
                                    )

                                elif int(idx) > len(tad.stints):
                                    assert False

                                else:
                                    stint = tad.stints[int(idx)]

                                    if "Compound" in stint_data:
                                        stint.compound = \
                                            F1LTType.TyreCompound[stint_data["Compound"]]

                                    if "New" in stint_data:
                                        new: str = stint_data["New"]
                                        stint.new = new == "true"

                                    if "TyresNotChanged" in stint_data:
                                        tyres_not_changed: str = stint_data["TyresNotChanged"]
                                        stint.tyre_not_changed = tyres_not_changed == "1"

                                    if "TotalLaps" in stint_data:
                                        total_laps: int = stint_data["TotalLaps"]
                                        stint.total_laps = total_laps

                                    if "StartLaps" in stint_data:
                                        start_laps: int = stint_data["StartLaps"]
                                        stint.start_laps = start_laps

                                    if "LapNumber" in stint_data:
                                        lap_number: int = stint_data["LapNumber"]
                                        stint.lap_number = lap_number

                                    if "LapFlags" in stint_data:
                                        lap_flags: int = stint_data["LapFlags"]
                                        stint.lap_flags = lap_flags

                                    if "LapTime" in stint_data:
                                        lap_time: str = stint_data["LapTime"]
                                        stint.lap_time = lap_time

                    if "GridPos" in timing_app_data:
                        grid_position: str = timing_app_data["GridPos"]
                        self.__timing_app_data[drv_num].grid_position = grid_position

                    self.__change_queue.put((
                        topic,
                        self.__timing_app_data[drv_num],
                        data["Lines"][drv_num],
                        timestamp,
                    ))

            elif topic == F1LTType.StreamingTopic.TIMING_STATS:
                self.__update_driver_timing_stats(data)

                self.__change_queue.put((
                    topic,
                    self.__timing_stats,
                    data,
                    timestamp,
                ))

            elif topic == F1LTType.StreamingTopic.TRACK_STATUS:
                if not self.__track_status:
                    self.__track_status = F1LTModel.TrackStatus(
                        data["Status"],
                        data["Message"],
                    )

                else:
                    self.__track_status.message = data["Message"]
                    self.__track_status.status = data["Status"]

                self.__change_queue.put((
                    topic,
                    self.__track_status,
                    data,
                    timestamp,
                ))

            elif topic == F1LTType.StreamingTopic.WEATHER_DATA:
                if self.__weather_data is None:
                    self.__weather_data = F1LTModel.WeatherData(
                        data["AirTemp"],
                        data["Humidity"],
                        data["Pressure"],
                        data["Rainfall"],
                        data["TrackTemp"],
                        data["WindDirection"],
                        data["WindSpeed"],
                    )

                else:
                    self.__weather_data.air_temp = data["AirTemp"]
                    self.__weather_data.humidity = data["Humidity"]
                    self.__weather_data.pressure = data["Pressure"]
                    self.__weather_data.rainfall = data["Rainfall"]
                    self.__weather_data.track_temp = data["TrackTemp"]
                    self.__weather_data.wind_direction = data["WindDirection"]
                    self.__weather_data.wind_speed = data["WindSpeed"]

                self.__change_queue.put((
                    topic,
                    self.__weather_data,
                    data,
                    timestamp,
                ))

    def process_old_data(self, old_data: Dict[F1LTType.StreamingTopic, Any]):
        for d_key, d_val in old_data.items():
            if d_key == F1LTType.StreamingTopic.AUDIO_STREAMS:
                if len(d_val) == 0:
                    continue

                for stream in d_val["Streams"]:
                    stream_data = F1LTModel.AudioStream(
                        stream["Name"],
                        stream["Language"],
                        stream["Uri"],
                        stream["Path"],
                    )
                    self.__audio_streams.append(stream_data)

            elif d_key == F1LTType.StreamingTopic.DRIVER_LIST:
                if len(d_val) == 0:
                    continue

                for drv_num, drv_data in d_val.items():
                    if drv_num == "_kf":
                        continue

                    self.__drivers[drv_num] = F1LTModel.Driver(
                        drv_data["RacingNumber"],
                        broadcast_name=drv_data["BroadcastName"],
                        full_name=drv_data["FullName"],
                        tla=drv_data["Tla"],
                        team_name=(
                            drv_data["TeamName"]
                            if "TeamName" in drv_data
                            else None
                        ),
                        team_color=(
                            drv_data["TeamColour"]
                            if "TeamColour" in drv_data
                            else None
                        ),
                        first_name=(
                            drv_data["FirstName"]
                            if "FirstName" in drv_data
                            else None
                        ),
                        last_name=(
                            drv_data["LastName"]
                            if "LastName" in drv_data
                            else None
                        ),
                        reference=(
                            drv_data["Reference"]
                            if "Reference" in drv_data
                            else None
                        ),
                        headshot_url=(
                            drv_data["HeadshotUrl"]
                            if "HeadshotUrl" in drv_data
                            else None
                        ),
                        country_code=(
                            drv_data["CountryCode"]
                            if "" in drv_data
                            else None
                        ),
                    )

            elif d_key == F1LTType.StreamingTopic.EXTRAPOLATED_CLOCK:
                if len(d_val) == 0:
                    continue

                self.__extrapolated_clock = F1LTModel.ExtrapolatedClock(
                    d_val["Remaining"],
                    d_val["Extrapolating"],
                    datetime_parser(d_val["Utc"]),
                )

            elif d_key == F1LTType.StreamingTopic.LAP_COUNT:
                if len(d_val) == 0:
                    continue

                self.__lap_count = F1LTModel.LapCount(
                    d_val["CurrentLap"],
                    d_val["TotalLaps"],
                )

            elif d_key == F1LTType.StreamingTopic.RACE_CONTROL_MESSAGES:
                if len(d_val) == 0:
                    continue

                for rcm_msg in d_val["Messages"]:
                    self.__race_control_messages.append(
                        F1LTModel.RaceControlMessage(
                            rcm_msg["Category"],
                            rcm_msg["Message"],
                            flag=(
                                rcm_msg["Flag"]
                                if "Flag" in rcm_msg
                                else None
                            ),
                            scope=(
                                rcm_msg["Scope"]
                                if "Scope" in rcm_msg
                                else None
                            ),
                            racing_number=(
                                rcm_msg["RacingNumber"]
                                if "RacingNumber" in rcm_msg
                                else None
                            ),
                            sector=(
                                rcm_msg["Sector"]
                                if "Sector" in rcm_msg
                                else None
                            ),
                            lap=(
                                rcm_msg["Lap"]
                                if "Lap" in rcm_msg
                                else None
                            ),
                            status=(
                                rcm_msg["Status"]
                                if "Status" in rcm_msg
                                else None
                            ),
                        ),
                    )

            elif d_key == F1LTType.StreamingTopic.SESSION_INFO:
                if len(d_val) == 0:
                    continue

                self.__session_info = F1LTModel.SessionInfo(
                    d_val["Meeting"],
                    d_val["ArchiveStatus"],
                    d_val["Key"],
                    d_val["Type"],
                    d_val["Name"],
                    d_val["StartDate"],
                    d_val["EndDate"],
                    d_val["GmtOffset"],
                    d_val["Path"],
                    number=(
                        d_val["Number"]
                        if "Number" in d_val
                        else None
                    ),
                )

            elif d_key == F1LTType.StreamingTopic.SESSION_STATUS:
                if len(d_val) == 0:
                    continue

                self.__session_status = F1LTType.SessionStatus[
                    d_val["Status"].upper()
                ]

            elif d_key == F1LTType.StreamingTopic.TEAM_RADIO:
                if len(d_val) == 0:
                    continue

                for capture in d_val["Captures"]:
                    self.__team_radios.append(
                        F1LTModel.TeamRadio(
                            capture["RacingNumber"],
                            capture["Path"],
                            capture["Utc"],
                        ),
                    )

            elif d_key == F1LTType.StreamingTopic.TIMING_APP_DATA:
                if len(d_val) == 0:
                    continue

                for drv_num, timing_data in d_val["Lines"].items():
                    data = F1LTModel.TimingAppData(
                        timing_data["RacingNumber"],
                        timing_data["GridPos"] if "GridPos" in timing_data else None,
                    )

                    if (
                        "Stints" in timing_data and
                        len(timing_data["Stints"]) > 0
                    ):
                        for stint in timing_data["Stints"]:
                            data.stints.append(
                                F1LTModel.TimingAppData.Stint(
                                    stint["LapFlags"],
                                    F1LTType.TyreCompound[
                                        stint["Compound"]
                                    ],
                                    stint["New"] == "true",
                                    stint["TyresNotChanged"] == "1",
                                    stint["TotalLaps"],
                                    stint["StartLaps"],
                                    lap_time=(
                                        stint["LapTime"]
                                        if "LapTime" in stint
                                        else None
                                    ),
                                    lap_number=(
                                        stint["LapNumber"]
                                        if "LapNumber" in stint
                                        else None
                                    ),
                                ),
                            )

                    self.__timing_app_data |= {drv_num: data}

            elif d_key == F1LTType.StreamingTopic.TIMING_STATS:
                if len(d_val) == 0:
                    continue

                self.__update_driver_timing_stats(d_val)

            elif d_key == F1LTType.StreamingTopic.TRACK_STATUS:
                if len(d_val) == 0:
                    continue

                self.__track_status = F1LTModel.TrackStatus(
                    F1LTType.TrackStatus(d_val["Status"]),
                    d_val["Message"],
                )

            elif d_key == F1LTType.StreamingTopic.WEATHER_DATA:
                if len(d_val) == 0:
                    continue

                self.__weather_data = F1LTModel.WeatherData(
                    d_val["AirTemp"],
                    d_val["Humidity"],
                    d_val["Pressure"],
                    d_val["Rainfall"],
                    d_val["TrackTemp"],
                    d_val["WindDirection"],
                    d_val["WindSpeed"],
                )

    @property
    def race_control_messages(self):
        return self.__race_control_messages

    @property
    def session_data(self):
        return self.__session_data

    @property
    def session_info(self):
        return self.__session_info

    @property
    def session_status(self):
        return self.__session_status

    @property
    def team_radios(self):
        return self.__team_radios

    @property
    def timing_app_data(self):
        return self.__timing_app_data

    @property
    def timing_stats(self):
        return self.__timing_stats

    @property
    def track_status(self):
        return self.__track_status

    @property
    def weather_data(self):
        return self.__weather_data
