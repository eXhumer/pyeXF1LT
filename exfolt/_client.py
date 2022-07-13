from base64 import b64decode
from datetime import date, datetime, timedelta, timezone
from json import dumps, loads
from logging import getLogger
from queue import Queue
from random import randint
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, urlencode
from zlib import decompress, MAX_WBITS

from requests import ConnectionError, HTTPError, Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)

from ._model import (
    AudioStream,
    Driver,
    ExtrapolatedClock,
    LapCountData,
    RaceControlMessageData,
    SessionInfoData,
    TeamRadioData,
    TimingAppData,
    TimingStatsData,
    TrackStatusData,
    WeatherData,
)
from ._type import TimingType
from ._utils import datetime_parser, timedelta_parser


class SignalRClient:
    """
    SignalR client to communicate with SignalR server.

    Currently only supports webSocket transport. Mainly created for use as F1 live timing client
    (F1LiveClient).
    """

    __client_protocol = "1.5"
    __logger = getLogger("exfolt.SignalRClient")
    __ping_interval = timedelta(minutes=5)

    def __init__(self, url: str, connection_data: Dict[str, List[str]], reconnect: bool = True):
        self.__cookies: List[str] = []
        self.__connection_data = connection_data
        self.__groups_token: Optional[str] = None
        self.__command_id = 0
        self.__last_ping_at: Optional[datetime] = None
        self.__id: Optional[str] = None
        self.__message_id: Optional[str] = None
        self.__negotiated_at: Optional[int] = None
        self.__reconnect = reconnect
        self.__token: Optional[str] = None
        self.__transport_type = "webSockets"
        self.__url = url
        self.__rest_transport = Session()

        if self.__transport_type == "webSockets":
            self.__transport = WebSocket(skip_utf8_validation=True)

        else:
            self.__transport = None

    def __enter__(self):
        SignalRClient.__logger.info("Entering SignalR client context!")
        return self.open()

    def __exit__(self, *args):
        SignalRClient.__logger.info("Exiting SignalR client context!")
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if not self.connected and self.__reconnect:
                self.__connect()

            if self.connected:
                try:
                    return self.__recv()

                except WebSocketConnectionClosedException:
                    SignalRClient.__logger.warning("Connection closed unexpectedly!")

                    if not self.__reconnect:
                        SignalRClient.__logger.info("Reconnection disabled! Raising exception!")
                        raise

                    SignalRClient.__logger.info("Attempting to reconnect!")
                    continue

            raise StopIteration

    def __repr__(self):
        __data = ", ".join((
            f"url={self.__url}",
            f"connection_data={self.__connection_data}",
            f"id={self.__id}",
            f"token={self.__token}",
            f"message_id={self.__message_id}",
            f"groups_token={self.__groups_token}",
        ))

        return f"{type(self).__name__}({__data})"

    def __str__(self):
        return self.__repr__()

    def __abort(self):
        if not self.__token:
            return False

        try:
            SignalRClient.__logger.info(f"Aborting SignalR connection with ID {self.__id}!")
            r = self.__rest_transport.post(
                f"{self.__url}/abort",
                params={
                    "transport": self.__transport_type,
                    "connectionToken": self.__token,
                    "clientProtocol": SignalRClient.__client_protocol,
                    "connectionData": dumps(
                        [{"name": hub} for hub in self.__connection_data.keys()],
                        separators=(',', ':'),
                    ),
                },
                json={},
            )
            r.raise_for_status()
            return True

        except (ConnectionError, HTTPError):
            SignalRClient.__logger.error("Error while trying to abort SignalR connection with " +
                                         f"ID {self.__id}!")
            return False

    def __close(self):
        if not self.__transport.connected:
            return

        SignalRClient.__logger.info(f"Closing SignalR connection with ID {self.__id}!")
        self.__transport.close()
        self.__id = None
        self.__token = None

    def __connect(self):
        try:
            assert not self.connected and self.__token
            SignalRClient.__logger.info(f"Connecting to SignalR transport with URL {self.__url}!")

        except AssertionError as ex:
            if self.connected:
                SignalRClient.__logger.warning("Connection already established!")

            if not self.__token:
                SignalRClient.__logger.warning("No connection token available!")

            raise ex

        while True:
            try:
                if self.__groups_token and self.__message_id:
                    self.__transport.connect(
                        f"{self.__url.replace('https://', 'wss://')}/reconnect" + "?" + urlencode(
                            {
                                "transport": self.__transport_type,
                                "groupsToken": self.__groups_token,
                                "messageId": self.__message_id,
                                "clientProtocol": SignalRClient.__client_protocol,
                                "connectionToken": self.__token,
                                "connectionData": dumps(
                                    [{"name": hub} for hub in self.__connection_data.keys()],
                                    separators=(',', ':'),
                                ),
                                "tid": randint(0, 11),
                            },
                            quote_via=quote,
                        ),
                        cookie=";".join(self.__cookies) if len(self.__cookies) > 0 else None,
                    )

                else:
                    self.__transport.connect(
                        f"{self.__url.replace('https://', 'wss://')}/connect" + "?" + urlencode(
                            {
                                "transport": self.__transport_type,
                                "clientProtocol": SignalRClient.__client_protocol,
                                "connectionToken": self.__token,
                                "connectionData": dumps(
                                    [{"name": hub} for hub in self.__connection_data.keys()],
                                    separators=(',', ':'),
                                ),
                                "tid": randint(0, 11),
                            },
                            quote_via=quote,
                        ),
                        cookie=";".join(self.__cookies) if len(self.__cookies) > 0 else None,
                    )

                self.__last_ping_at = datetime.utcnow()
                break

            except WebSocketBadStatusException as e:
                SignalRClient.__logger.warning("Connecting to SignalR transport failed due to " +
                                               "transport handshake exception!")

                if "set-cookie" in e.resp_headers:
                    set_cookie: str = e.resp_headers["set-cookie"]
                    self.__cookies = set_cookie
                    continue

                raise e

    def __negotiate(self):
        if self.__token:
            return

        SignalRClient.__logger.info("Negotiating for new SignalR connection!")
        self.__negotiated_at = int(datetime.utcnow().timestamp() * 1000)

        r = self.__rest_transport.get(
            f"{self.__url}/negotiate",
            params={
                "_": str(self.__negotiated_at),
                "clientProtocol": SignalRClient.__client_protocol,
                "connectionData": dumps(
                    [{"name": hub} for hub in self.__connection_data.keys()],
                    separators=(',', ':'),
                ),
            },
        )
        r.raise_for_status()

        r_json = r.json()
        conn_token: str = r_json["ConnectionToken"]
        conn_id: str = r_json["ConnectionId"]
        self.__token = conn_token
        self.__id = conn_id
        self.__cookies = [f"{cookie.name}={cookie.value}" for cookie in r.cookies]

    def __ping(self):
        if not self.__token:
            return False

        self.__negotiated_at += 1

        try:
            SignalRClient.__logger.info(f"Pinging SignalR connection with ID {self.__id}!")
            r = self.__rest_transport.get(
                f"{self.__url}/ping",
                params={"_": str(self.__negotiated_at)},
            )
            r.raise_for_status()
            response: str = r.json()["Response"]
            return response == "pong"

        except (ConnectionError, HTTPError):
            return False

    def __recv(self):
        assert self.connected and self.__last_ping_at

        while True:
            try:
                if datetime.utcnow() >= self.__last_ping_at + SignalRClient.__ping_interval:
                    self.__last_ping_at = datetime.utcnow()
                    self.__ping()

                opcode, raw_data = self.__transport.recv_data()
                opcode: int
                raw_data: bytes
                json_data = loads(raw_data)
                json_data: Dict[str, Any]

                if len(json_data) == 0:
                    SignalRClient.__logger.info("KeepAlive packet received at " +
                                                str(datetime.now(tz=timezone.utc)) +
                                                f" from SignalR connection with ID {self.__id}!")

                else:
                    SignalRClient.__logger.info("Received SignalR message from connection with " +
                                                f"ID {self.__id}!")

                if "C" in json_data:
                    message_id: str = json_data["C"]
                    self.__message_id = message_id

                if "G" in json_data:
                    groups_token: str = json_data["G"]
                    self.__groups_token = groups_token

                return opcode, json_data

            except WebSocketTimeoutException:
                continue

    def __start(self):
        if not self.__token:
            return False

        self.__negotiated_at += 1
        SignalRClient.__logger.info(f"Started SignalR connection with ID {self.__id}!")
        r = self.__rest_transport.get(
            f"{self.__url}/start",
            params={
                "transport": self.__transport_type,
                "clientProtocol": SignalRClient.__client_protocol,
                "connectionToken": self.__token,
                "connectionData": dumps(
                    [{"name": hub} for hub in self.__connection_data.keys()],
                    separators=(',', ':'),
                ),
                "_": str(self.__negotiated_at),
            },
        )
        r.raise_for_status()
        response: str = r.json()["Response"]
        return response == "started"

    def __subscribe(self):
        for hub, topics in self.__connection_data.items():
            SignalRClient.__logger.info(f"Subscribing SignalR connection with ID {self.__id} to " +
                                        f"hub '{hub}' for topics {topics}!")
            self.__transport.send(
                dumps(
                    {
                        "H": hub,
                        "M": "Subscribe",
                        "A": [topics],
                        "I": self.__command_id,
                    },
                    separators=(',', ':'),
                ),
            )
            self.__command_id += 1

    def __unsubscribe(self):
        for hub, topics in self.__connection_data.items():
            SignalRClient.__logger.info(f"Unsubscribing SignalR connection with ID {self.__id} " +
                                        f"from hub '{hub}' for topics {topics}!")
            self.__transport.send(
                dumps(
                    {
                        "H": hub,
                        "M": "Unsubscribe",
                        "A": [topics],
                        "I": self.__command_id,
                    },
                    separators=(',', ':'),
                ),
            )
            self.__command_id += 1

    def close(self):
        if self.connected:
            if self.__groups_token:
                self.__unsubscribe()

            self.__close()

        self.__abort()

    @property
    def connected(self):
        return self.__transport.connected

    def open(self):
        if not self.__token:
            self.__negotiate()

        if not self.connected:
            self.__connect()

        if not self.__groups_token:
            self.__subscribe()

        self.__start()

        return self


class F1LiveClient(SignalRClient):
    """
    F1 timing client to receive messages from a live session
    """

    URL = "https://livetiming.formula1.com/signalr"

    def __init__(self, *topics: TimingType.Topic, reconnect: bool = True):
        super().__init__(F1LiveClient.URL, {TimingType.Hub.STREAMING: topics}, reconnect=reconnect)


class F1ArchiveClient:
    """
    F1 timing client to receive messages from an archived session
    """

    STATIC_URL = "https://livetiming.formula1.com/static"

    def __init__(self, path: str, *topics: TimingType.Topic, session: Optional[Session] = None):
        if not session:
            session = Session()

        res = session.get(f"{F1ArchiveClient.STATIC_URL}/{path}ArchiveStatus.json")
        res.raise_for_status()

        archive_status: str = loads(res.content.decode("utf-8-sig"))["Status"]
        assert archive_status == "Complete", f"Unexpected archive status \"{archive_status}\"!"

        self.__path = path
        self.__topics = topics
        self.__session = session
        self.__data_queue: Queue[
            Tuple[
                TimingType.Topic,
                Union[Dict[str, Any], str],
                timedelta,
            ]
        ] = Queue()

        self.__load_data()

    def __iter__(self):
        return self

    def __next__(self):
        if self.__data_queue.qsize() == 0:
            raise StopIteration

        return self.__data_queue.get()

    def __load_data(self):
        data_entries: List[Tuple[TimingType.Topic, Dict[str, Any], timedelta]] = []

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
                    (topic, data_entry[13:-1], timedelta_parser(data_entry[:12]))
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
        *topics: TimingType.Topic,
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
    def get_last_session(cls, *topics: TimingType.Topic, session: Optional[Session] = None):
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


class TimingClient:
    """
    Timing client to handle streamed session data from F1 sessions.
    """

    def __init__(self):
        self.__audio_streams: List[AudioStream] = []
        self.__drivers: Dict[str, Driver] = {}
        self.__timing_app_data: Dict[str, TimingAppData] = {}
        self.__timing_stats: Dict[str, TimingStatsData] = {}
        self.__extrapolated_clock: Optional[ExtrapolatedClock] = None
        self.__lap_count_data: Optional[LapCountData] = None
        self.__msg_q: Queue[
            Tuple[
                TimingType.Topic,
                Union[
                    AudioStream,
                    ExtrapolatedClock,
                    RaceControlMessageData,
                    SessionInfoData,
                    TeamRadioData,
                    TimingAppData,
                    TimingType.SessionStatus,
                    TrackStatusData,
                    WeatherData,
                    Dict[str, TimingStatsData],
                    Dict[str, Any],
                ],
                Union[Dict[str, Any], str],
                datetime,
            ]
        ] = Queue()
        self.__rcm_msgs: List[RaceControlMessageData] = []
        self.__session_info: Optional[SessionInfoData] = None
        self.__session_status: Optional[TimingType.SessionStatus] = None
        self.__team_radios: List[TeamRadioData] = []
        self.__track_status: Optional[TrackStatusData] = None
        self.__weather_data: Optional[WeatherData] = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.__msg_q.qsize() > 0:
            return self.__msg_q.get()

        raise StopIteration

    @staticmethod
    def __decompress_zlib_data(data: str):
        return decompress(b64decode(data.encode("ascii")), -MAX_WBITS).decode("utf8")

    def __update_driver_timing_stats(self, timing_stats_data):
        for racing_number, driver_timing_stats in timing_stats_data["Lines"].items():
            if "RacingNumber" in driver_timing_stats:
                self.__timing_stats |= {
                    racing_number: TimingStatsData(driver_timing_stats["RacingNumber"]),
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
    def audio_streams(self):
        return self.__audio_streams

    @property
    def drivers(self):
        return self.__drivers

    @property
    def extrapolated_clock(self):
        return self.__extrapolated_clock

    @property
    def lap_count(self):
        return self.__lap_count_data

    def process_data(
        self,
        topic: TimingType.Topic,
        data: Union[Dict[str, Any], str],
        timestamp: datetime,
    ):
        if topic in (
            TimingType.Topic.CAR_DATA_Z,
            TimingType.Topic.POSITION_Z,
        ):
            assert isinstance(data, str)
            decompressed_data = TimingClient.__decompress_zlib_data(data)
            self.__msg_q.put((
                topic,
                loads(decompressed_data),
                data,
                timestamp,
            ))

        else:
            assert isinstance(data, dict)

            if topic == TimingType.Topic.AUDIO_STREAMS:
                self.__audio_streams = []

                for stream in data["Streams"]:
                    stream_data = AudioStream(
                        stream["Name"],
                        stream["Language"],
                        stream["Uri"],
                        stream["Path"],
                    )
                    self.__audio_streams.append(stream_data)
                    self.__msg_q.put((topic, stream_data, data, timestamp))

            elif topic == TimingType.Topic.DRIVER_LIST:
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
                        self.__drivers[key] = Driver(
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

            elif topic == TimingType.Topic.EXTRAPOLATED_CLOCK:
                if self.__extrapolated_clock is None:
                    self.__extrapolated_clock = ExtrapolatedClock(
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

                self.__msg_q.put((
                    topic,
                    self.__extrapolated_clock,
                    data,
                    timestamp,
                ))

            elif topic == TimingType.Topic.LAP_COUNT:
                if self.__lap_count_data is None:
                    self.__lap_count_data = LapCountData(
                        data["CurrentLap"],
                        data["TotalLaps"],
                    )

                else:
                    if "CurrentLap" in data:
                        self.__lap_count_data.current_lap = data["CurrentLap"]

                    if "TotalLaps" in data:
                        self.__lap_count_data.total_laps = data["TotalLaps"]

                self.__msg_q.put((
                    topic,
                    self.__lap_count_data,
                    data,
                    timestamp,
                ))

            elif topic == TimingType.Topic.RACE_CONTROL_MESSAGES:
                rcm_msg = data["Messages"]

                if isinstance(rcm_msg, list):
                    self.__rcm_msgs = []
                    rcm_msg = rcm_msg[0]

                else:
                    rcm_msg = list(rcm_msg.values())[0]

                rcm_data = RaceControlMessageData(
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
                )

                self.__rcm_msgs.append(rcm_data)
                self.__msg_q.put((topic, rcm_data, data, timestamp))

            elif topic == TimingType.Topic.SESSION_INFO:
                if "ArchiveStatus" in data and len(data) == 1:
                    self.__session_info.archive_status["Status"] = data["ArchiveStatus"]["Status"]

                else:
                    self.__session_info = SessionInfoData(
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

                self.__msg_q.put((
                    topic,
                    self.__session_info,
                    data,
                    timestamp,
                ))

            elif topic == TimingType.Topic.SESSION_STATUS:
                self.__session_status = TimingType.SessionStatus[
                    data["Status"].upper()
                ]
                self.__msg_q.put((
                    topic,
                    self.__session_status,
                    data,
                    timestamp,
                ))

            elif topic == TimingType.Topic.TEAM_RADIO:
                team_radio_captures = data["Captures"]

                if isinstance(team_radio_captures, list):
                    self.__team_radios = []
                    team_radios = [team_radio_captures[0]]

                else:
                    team_radios = list(team_radio_captures.values())

                for team_radio in team_radios:
                    tr_data = TeamRadioData(
                        team_radio["RacingNumber"],
                        team_radio["Path"],
                        team_radio["Utc"],
                    )

                    self.__team_radios.append(tr_data)
                    self.__msg_q.put((topic, tr_data, data, timestamp))

            elif topic == TimingType.Topic.TIMING_APP_DATA:
                for drv_num, timing_app_data in data["Lines"].items():
                    if drv_num == "_kf":
                        continue

                    if "RacingNumber" in timing_app_data:
                        tad = self.__timing_app_data[drv_num] = TimingAppData(
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
                                    TimingAppData.Stint(
                                        stint_data["LapFlags"],
                                        TimingType.TyreCompound[stint_data["Compound"]],
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
                                        TimingAppData.Stint(
                                            stint_data["LapFlags"],
                                            TimingType.TyreCompound[stint_data["Compound"]],
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
                                            TimingType.TyreCompound[stint_data["Compound"]]

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

                    self.__msg_q.put((
                        topic,
                        self.__timing_app_data[drv_num],
                        data["Lines"][drv_num],
                        timestamp,
                    ))

            elif topic == TimingType.Topic.TIMING_STATS:
                self.__update_driver_timing_stats(data)

                self.__msg_q.put((
                    topic,
                    self.__timing_stats,
                    data,
                    timestamp,
                ))

            elif topic == TimingType.Topic.TRACK_STATUS:
                if not self.__track_status:
                    self.__track_status = TrackStatusData(
                        data["Status"],
                        data["Message"],
                    )

                else:
                    self.__track_status.message = data["Message"]
                    self.__track_status.status = data["Status"]

                self.__msg_q.put((
                    topic,
                    self.__track_status,
                    data,
                    timestamp,
                ))

            elif topic == TimingType.Topic.WEATHER_DATA:
                if self.__weather_data is None:
                    self.__weather_data = WeatherData(
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

                self.__msg_q.put((
                    topic,
                    self.__weather_data,
                    data,
                    timestamp,
                ))

    def process_old_data(self, old_data: Dict[TimingType.Topic, Any]):
        for d_key, d_val in old_data.items():
            if d_key == TimingType.Topic.AUDIO_STREAMS:
                if len(d_val) == 0:
                    continue

                for stream in d_val["Streams"]:
                    stream_data = AudioStream(
                        stream["Name"],
                        stream["Language"],
                        stream["Uri"],
                        stream["Path"],
                    )
                    self.__audio_streams.append(stream_data)

            elif d_key == TimingType.Topic.DRIVER_LIST:
                if len(d_val) == 0:
                    continue

                for drv_num, drv_data in d_val.items():
                    if drv_num == "_kf":
                        continue

                    self.__drivers[drv_num] = Driver(
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

            elif d_key == TimingType.Topic.EXTRAPOLATED_CLOCK:
                if len(d_val) == 0:
                    continue

                self.__extrapolated_clock = ExtrapolatedClock(
                    d_val["Remaining"],
                    d_val["Extrapolating"],
                    datetime_parser(d_val["Utc"]),
                )

            elif d_key == TimingType.Topic.LAP_COUNT:
                if len(d_val) == 0:
                    continue

                self.__lap_count_data = LapCountData(
                    d_val["CurrentLap"],
                    d_val["TotalLaps"],
                )

            elif d_key == TimingType.Topic.RACE_CONTROL_MESSAGES:
                if len(d_val) == 0:
                    continue

                for rcm_msg in d_val["Messages"]:
                    self.__rcm_msgs.append(
                        RaceControlMessageData(
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

            elif d_key == TimingType.Topic.SESSION_INFO:
                if len(d_val) == 0:
                    continue

                self.__session_info = SessionInfoData(
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

            elif d_key == TimingType.Topic.SESSION_STATUS:
                if len(d_val) == 0:
                    continue

                self.__session_status = TimingType.SessionStatus[
                    d_val["Status"].upper()
                ]

            elif d_key == TimingType.Topic.TEAM_RADIO:
                if len(d_val) == 0:
                    continue

                for capture in d_val["Captures"]:
                    self.__team_radios.append(
                        TeamRadioData(
                            capture["RacingNumber"],
                            capture["Path"],
                            capture["Utc"],
                        ),
                    )

            elif d_key == TimingType.Topic.TIMING_APP_DATA:
                if len(d_val) == 0:
                    continue

                for drv_num, timing_data in d_val["Lines"].items():
                    data = TimingAppData(
                        timing_data["RacingNumber"],
                        timing_data["GridPos"] if "GridPos" in timing_data else None,
                    )

                    if (
                        "Stints" in timing_data and
                        len(timing_data["Stints"]) > 0
                    ):
                        for stint in timing_data["Stints"]:
                            data.stints.append(
                                TimingAppData.Stint(
                                    stint["LapFlags"],
                                    TimingType.TyreCompound[
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

            elif d_key == TimingType.Topic.TIMING_STATS:
                if len(d_val) == 0:
                    continue

                self.__update_driver_timing_stats(d_val)

            elif d_key == TimingType.Topic.TRACK_STATUS:
                if len(d_val) == 0:
                    continue

                self.__track_status = TrackStatusData(
                    TimingType.TrackStatus(d_val["Status"]),
                    d_val["Message"],
                )

            elif d_key == TimingType.Topic.WEATHER_DATA:
                if len(d_val) == 0:
                    continue

                self.__weather_data = WeatherData(
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
        return self.__rcm_msgs

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
