import json
import zlib
from base64 import b64decode
from datetime import datetime, timedelta
from logging import getLogger
from queue import Queue
from random import randint
from typing import Any, Dict, List, Tuple, Union
from urllib.parse import quote, urlencode

from requests import ConnectionError, HTTPError, Session
from websocket import (
    WebSocket,
    WebSocketTimeoutException,
    WebSocketConnectionClosedException,
)

from ._model import (
    AudioStreamData,
    DriverData,
    ExtrapolatedClockData,
    LapCountData,
    RaceControlMessageData,
    SessionInfoData,
    TeamRadioData,
    TimingAppData,
    TrackStatusData,
    WeatherData,
)
from ._type import TimingType


class SRLiveClient:
    """SignalR client to communicate with SignalR server
    """
    __client_protocol = "1.5"
    __ping_interval = timedelta(minutes=5)

    def __init__(
        self,
        url: str,
        hub: str,
        *topics: str,
        reconnect: bool = True,
    ) -> None:
        self.__connected_at: datetime | None = None
        self.__gclb: str | None = None
        self.__groups_token: str | None = None
        self.__hub = hub
        self.__idx = 0
        self.__last_ping_at: datetime | None = None
        self.__message_id: str | None = None
        self.__negotiated_at: int | None = None
        self.__reconnect = reconnect
        self.__rs = Session()
        self.__token: str | None = None
        self.__topics = topics
        self.__url = url
        self.__ws = WebSocket(skip_utf8_validation=True)

    def __enter__(self):
        if not self.__token:
            self.__negotiate()

        if not self.connected:
            self.__connect()

        if not self.__groups_token:
            self.__subscribe()

        self.__start()

        return self

    def __exit__(self, *args):
        if self.connected:
            if self.__groups_token:
                self.__unsubscribe()

            self.__close()

        self.__abort()

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
                    if not self.__reconnect:
                        raise

                    continue

            raise StopIteration

    def __repr__(self):
        __data = ", ".join((
            f"url={self.__url}",
            f"hub={self.__hub}",
            f"token={self.__token}",
            f"topics={self.__topics}",
            f"message_id={self.__message_id}",
            f"groups_token={self.__groups_token}",
        ))

        return f"SRLiveClient({__data})"

    def __str__(self):
        return self.__repr__()

    def __abort(self):
        if not self.__token:
            return False

        try:
            r = self.__rs.post(
                f"{self.__url}/abort",
                params={
                    "transport": "webSockets",
                    "connectionToken": self.__token,
                    "clientProtocol": SRLiveClient.__client_protocol,
                    "connectionData": json.dumps(
                        [{"name": self.__hub}],
                        separators=(',', ':'),
                    ),
                },
                json={},
            )
            r.raise_for_status()
            return True

        except (ConnectionError, HTTPError):
            return False

    def __close(self):
        if not self.__ws.connected:
            return

        self.__ws.close()

    def __connect(self):
        assert not self.connected and self.__token

        if self.__groups_token and self.__message_id:
            self.__ws.connect(
                "/".join((
                    self.__url.replace("https://", "wss://"),
                    "reconnect",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "groupsToken": self.__groups_token,
                        "messageId": self.__message_id,
                        "clientProtocol":
                            SRLiveClient.__client_protocol,
                        "connectionToken": self.__token,
                        "connectionData": json.dumps(
                            [{"name": self.__hub}],
                            separators=(',', ':'),
                        ),
                        "tid": randint(0, 11),
                    },
                    quote_via=quote,
                ),
                cookie=f"GCLB={self.__gclb}" if self.__gclb else None,
            )
            self.__connected_at = datetime.now()
            self.__last_ping_at = None

        else:
            print(
                "/".join((
                    self.__url.replace("https://", "wss://"),
                    "connect",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "clientProtocol":
                            SRLiveClient.__client_protocol,
                        "connectionToken": self.__token,
                        "connectionData": json.dumps(
                            [{"name": self.__hub}],
                            separators=(',', ':'),
                        ),
                        "tid": randint(0, 11),
                    },
                    quote_via=quote,
                )
            )
            self.__ws.connect(
                "/".join((
                    self.__url.replace("https://", "wss://"),
                    "connect",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "clientProtocol":
                            SRLiveClient.__client_protocol,
                        "connectionToken": self.__token,
                        "connectionData": json.dumps(
                            [{"name": self.__hub}],
                            separators=(',', ':'),
                        ),
                        "tid": randint(0, 11),
                    },
                    quote_via=quote,
                ),
                cookie=f"GCLB={self.__gclb}" if self.__gclb else None,
            )
            self.__connected_at = datetime.now()

    def __negotiate(self):
        if self.__token:
            return

        self.__negotiated_at = int(datetime.now().timestamp() * 1000)

        r = self.__rs.get(
            f"{self.__url}/negotiate",
            params={
                "_": str(self.__negotiated_at),
                "clientProtocol": SRLiveClient.__client_protocol,
                "connectionData": json.dumps(
                    [{"name": self.__hub}],
                    separators=(',', ':'),
                ),
            },
        )
        r.raise_for_status()

        if "GCLB" in r.cookies:
            gclb: str = r.cookies["GCLB"]
            self.__gclb = gclb

        r_json = r.json()
        conn_token: str = r_json["ConnectionToken"]
        self.__token = conn_token

    def __ping(self):
        if not self.__token:
            return False

        self.__negotiated_at += 1

        try:
            r = self.__rs.get(
                f"{self.__url}/ping",
                params={"_": str(self.__negotiated_at)},
            )
            r.raise_for_status()
            response: str = r.json()["Response"]
            return response == "pong"

        except (ConnectionError, HTTPError):
            return False

    def __recv(self):
        assert self.connected

        while True:
            try:
                if self.__last_ping_at:
                    if (
                        datetime.now() >=
                        self.__last_ping_at +
                        SRLiveClient.__ping_interval
                    ):
                        self.__last_ping_at = datetime.now()
                        self.__ping()

                elif self.__connected_at:
                    if (
                        datetime.now() >=
                        self.__connected_at +
                        SRLiveClient.__ping_interval
                    ):
                        self.__last_ping_at = datetime.now()
                        self.__ping()

                opcode, raw_data = self.__ws.recv_data()
                opcode: int
                raw_data: bytes
                json_data = json.loads(raw_data)
                json_data: Dict[str, Any]

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

        r = self.__rs.get(
            f"{self.__url}/start",
            params={
                "transport": "webSockets",
                "clientProtocol": SRLiveClient.__client_protocol,
                "connectionToken": self.__token,
                "connectionData": json.dumps(
                    [{"name": self.__hub}],
                    separators=(',', ':'),
                ),
                "_": str(self.__negotiated_at),
            },
        )
        r.raise_for_status()
        response: str = r.json()["Response"]
        return response == "started"

    def __subscribe(self):
        self.__ws.send(
            json.dumps(
                {
                    "H": self.__hub,
                    "M": "Subscribe",
                    "A": [self.__topics],
                    "I": self.__idx,
                },
                separators=(',', ':'),
            ),
        )
        self.__idx += 1

    def __unsubscribe(self):
        self.__ws.send(
            json.dumps(
                {
                    "H": self.__hub,
                    "M": "Unsubscribe",
                    "A": [self.__topics],
                    "I": self.__idx,
                },
                separators=(',', ':'),
            ),
        )
        self.__idx += 1

    @property
    def connected(self):
        return self.__ws.connected


class TimingClient:
    """
    Timing client to handle streamed session data from F1 sessions.
    """
    __logger = getLogger("exfolt.TimingClient")

    def __init__(self) -> None:
        self.__audio_streams: List[AudioStreamData] = []
        self.__drivers: Dict[str, DriverData] = {}
        self.__timing_app_data: Dict[str, TimingAppData] = {}
        self.__extrapolated_clock: ExtrapolatedClockData | None = None
        self.__lap_count_data: LapCountData | None = None
        self.__message_queue: Queue[
            Tuple[
                TimingType.Topic,
                Union[
                    AudioStreamData,
                    ExtrapolatedClockData,
                    RaceControlMessageData,
                    SessionInfoData,
                    TeamRadioData,
                    TimingAppData,
                    TimingType.SessionStatus,
                    TrackStatusData,
                    WeatherData,
                    str,
                ],
                datetime,
            ]
        ] = Queue()
        self.__rcm_msgs: List[RaceControlMessageData] = []
        self.__session_info: SessionInfoData | None = None
        self.__session_status: TimingType.SessionStatus | None = None
        self.__team_radios: List[TeamRadioData] = []
        self.__track_status: TrackStatusData | None = None
        self.__weather_data: WeatherData | None = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.__message_queue.qsize() > 0:
            return self.__message_queue.get()

        raise StopIteration

    @staticmethod
    def __decompress_zlib_data(data: str):
        return zlib.decompress(b64decode(data.encode("ascii"))).decode("utf8")

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
        data: Dict[str, Any] | str,
        timestamp: datetime,
    ):
        TimingClient.__logger.debug(f"Topic: {topic}")
        TimingClient.__logger.debug(f"Data: {data}")
        TimingClient.__logger.debug(f"Timestamp: {timestamp}")

        if topic in (
            TimingType.Topic.CAR_DATA_Z,
            TimingType.Topic.POSITION_Z,
        ):
            assert isinstance(data, str)
            decompressed_data = TimingClient.__decompress_zlib_data(data)
            TimingClient.__logger.debug("Decompressed Data: " +
                                        decompressed_data)
            self.__message_queue.put((
                topic,
                decompressed_data,
                timestamp,
            ))

        else:
            assert isinstance(data, dict)

            if topic == TimingType.Topic.AUDIO_STREAMS:
                self.__audio_streams = []

                for stream in data["Streams"]:
                    stream_data = AudioStreamData(
                        stream["Name"],
                        stream["Language"],
                        stream["Uri"],
                        stream["Path"],
                    )
                    self.__audio_streams.append(stream_data)
                    self.__message_queue.put((topic, stream_data, timestamp))

            elif topic == TimingType.Topic.DRIVER_LIST:
                for key, value in data.items():
                    if key.startswith("_"):
                        continue

                    assert isinstance(value, dict)

                    if len(value) == 1 and "Line" in value:
                        continue

                    else:
                        self.__drivers[key] = DriverData(
                            value["RacingNumber"],
                            broadcast_name=value["BroadcastName"],
                            full_name=value["FullName"],
                            tla=value["Tla"],
                            team_name=value["TeamName"],
                            team_color=value["TeamColour"],
                            first_name=value["FirstName"],
                            last_name=value["LastName"],
                            reference=value["Reference"],
                            headshot_url=(
                                value["HeadshotUrl"]
                                if "HeadshotUrl" in value
                                else None
                            ),
                            country_code=value["CountryCode"],
                        )

            elif topic == TimingType.Topic.EXTRAPOLATED_CLOCK:
                if self.__extrapolated_clock is None:
                    self.__extrapolated_clock = ExtrapolatedClockData(
                        data["Remaining"],
                        data["Extrapolating"],
                        data["Utc"],
                    )

                else:
                    if "Remaining" in data:
                        self.__extrapolated_clock.remaining = data["Remaining"]

                    if "Extrapolating" in data:
                        self.__extrapolated_clock.extrapolating = \
                            data["Extrapolating"]

                    if "Utc" in data:
                        self.__extrapolated_clock.remaining = data["Utc"]

                self.__message_queue.put((
                    topic,
                    self.__extrapolated_clock,
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

                self.__message_queue.put((
                    topic,
                    self.__lap_count_data,
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
                    drs_status=(
                        rcm_msg["Status"]
                        if "Status" in rcm_msg
                        else None
                    ),
                )

                self.__rcm_msgs.append(rcm_data)
                self.__message_queue.put((topic, rcm_data, timestamp))

            elif topic == TimingType.Topic.SESSION_INFO:
                self.__session_info = SessionInfoData(
                    data["ArchiveStatus"],
                    data["Meeting"],
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
                self.__message_queue.put((
                    topic,
                    self.__session_info,
                    timestamp,
                ))

            elif topic == TimingType.Topic.SESSION_STATUS:
                status: TimingType.SessionStatus = data["Status"]
                self.__session_status = status
                self.__message_queue.put((
                    topic,
                    self.__session_status,
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
                    self.__message_queue.put((topic, tr_data, timestamp))

            elif topic == TimingType.Topic.TIMING_APP_DATA:
                for drv_num, timing_app_data in data["Lines"].items():
                    if drv_num.startswith("_"):
                        continue

                    if (
                        "RacingNumber" in timing_app_data and
                        "Line" in timing_app_data and
                        "GridPos" in timing_app_data
                    ):
                        self.__timing_app_data[drv_num] = TimingAppData(
                            timing_app_data["RacingNumber"],
                            timing_app_data["GridPos"],
                        )

                    else:
                        tad = self.__timing_app_data[drv_num]

                        if "Stints" in timing_app_data:
                            timing_stints = timing_app_data["Stints"]

                            if isinstance(timing_stints, list):
                                tad.stints.clear()

                                if len(timing_stints) > 0:
                                    for idx, stint_data in enumerate(
                                        timing_stints
                                    ):
                                        tad.stints.append(
                                            TimingAppData.Stint(
                                                stint_data["LapFlags"],
                                                stint_data["Compound"],
                                                stint_data["New"] == "true",
                                                stint_data["TyresNotChanged"]
                                                == "1",
                                                stint_data["TotalLaps"],
                                                stint_data["StartLaps"],
                                            )
                                        )

                            else:
                                for idx, stint_data in timing_stints.items():
                                    if (
                                        "LapFlags" in stint_data and
                                        "Compound" in stint_data and
                                        "New" in stint_data and
                                        "TyresNotChanged" in stint_data
                                    ):
                                        tad.stints.append(
                                            TimingAppData.Stint(
                                                stint_data["LapFlags"],
                                                stint_data["Compound"],
                                                stint_data["New"] == "true",
                                                stint_data["TyresNotChanged"]
                                                == "1",
                                                stint_data["TotalLaps"],
                                                stint_data["StartLaps"],
                                                lap_time=(
                                                    stint_data["LapTime"]
                                                    if "LapTime" in stint_data
                                                    else None
                                                ),
                                                lap_number=(
                                                    stint_data["LapNumber"]
                                                    if "LapNumber"
                                                    in stint_data
                                                    else None
                                                ),
                                            )
                                        )

                                    else:
                                        stint = tad.stints[int(idx)]

                                        if "Compound" in stint_data:
                                            compound: TimingType.TypeCompound \
                                                = stint_data["Compound"]
                                            stint.compound = compound

                                        if "New" in stint_data:
                                            new: bool = \
                                                stint_data["New"] == "true"
                                            stint.new = new

                                        if "TyresNotChanged" in stint_data:
                                            tyres_not_changed: bool = (
                                                stint_data["TyresNotChanged"]
                                                == "1"
                                            )
                                            stint.tyre_not_changed = \
                                                tyres_not_changed

                                        if "TotalLaps" in stint_data:
                                            total_laps: int = \
                                                stint_data["TotalLaps"]
                                            stint.total_laps = total_laps

                                        if "LapTime" in stint_data:
                                            lap_time: str = \
                                                stint_data["LapTime"]
                                            stint.lap_time = lap_time

                                        if "LapNumber" in stint_data:
                                            lap_number: int = \
                                                stint_data["LapNumber"]
                                            stint.lap_number = lap_number

                                        if "LapFlags" in stint_data:
                                            lap_flags: int = \
                                                stint_data["LapFlags"]
                                            stint.lap_flags = lap_flags

                        if "GridPos" in timing_app_data:
                            grid_position: str = timing_app_data["GridPos"]
                            self.__timing_app_data[drv_num].grid_position = \
                                grid_position

                    self.__message_queue.put((
                        topic,
                        self.__timing_app_data[drv_num],
                        timestamp,
                    ))

            elif topic == TimingType.Topic.TIMING_DATA:
                # TODO: Process data correctly
                pass

            elif topic == TimingType.Topic.TIMING_STATS:
                # TODO: Process data correctly
                pass

            elif topic == TimingType.Topic.TRACK_STATUS:
                if not self.__track_status:
                    self.__track_status = TrackStatusData(
                        data["Status"],
                        data["Message"],
                    )

                else:
                    self.__track_status.message = data["Message"]
                    self.__track_status.status = data["Status"]

                self.__message_queue.put((
                    topic,
                    self.__track_status,
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

                self.__message_queue.put((
                    topic,
                    self.__weather_data,
                    timestamp,
                ))

    def process_old_data(
        self,
        old_data: Dict[TimingType.Topic, Any],
    ):
        for d_key, d_val in old_data.items():
            if d_key == TimingType.Topic.AUDIO_STREAMS:
                if len(d_val) == 0:
                    continue

                for stream in d_val["Streams"]:
                    stream_data = AudioStreamData(
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

                    self.__drivers[drv_num] = DriverData(
                        drv_data["RacingNumber"],
                        broadcast_name=drv_data["BroadcastName"],
                        full_name=drv_data["FullName"],
                        tla=drv_data["Tla"],
                        team_name=drv_data["TeamName"],
                        team_color=drv_data["TeamColour"],
                        first_name=drv_data["FirstName"],
                        last_name=drv_data["LastName"],
                        reference=drv_data["Reference"],
                        headshot_url=(
                            drv_data["HeadshotUrl"]
                            if "HeadshotUrl" in drv_data
                            else None
                        ),
                        country_code=drv_data["CountryCode"],
                    )

            elif d_key == TimingType.Topic.EXTRAPOLATED_CLOCK:
                if len(d_val) == 0:
                    continue

                self.__extrapolated_clock = ExtrapolatedClockData(
                    d_val["Remaining"],
                    d_val["Extrapolating"],
                    d_val["Utc"],
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
                            drs_status=(
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

                status: TimingType.SessionStatus = d_val["Status"]
                self.__session_status = status

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
                        timing_data["GridPos"],
                    )

                    if (
                        "Stints" in timing_data and
                        len(timing_data["Stints"]) > 0
                    ):
                        for stint in timing_data["Stints"]:
                            data.stints.append(
                                TimingAppData.Stint(
                                    stint["LapFlags"],
                                    stint["Compound"],
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

                    self.__timing_app_data.update({drv_num: data})

            elif d_key == TimingType.Topic.TRACK_STATUS:
                if len(d_val) == 0:
                    continue

                self.__track_status = TrackStatusData(
                    d_val["Status"],
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
    def track_status(self):
        return self.__track_status

    @property
    def weather_data(self):
        return self.__weather_data
