import json
from datetime import datetime, timedelta
from random import randint
from urllib.parse import quote, urlencode

from requests import Session
from websocket import WebSocket, WebSocketBadStatusException


class Client:
    """F1 Live Timing Client"""
    __base_rest_url = "https://livetiming.formula1.com"
    __base_wss_url = "wss://livetiming.formula1.com"
    __long_poll_interval = timedelta(minutes=5)
    __client_protocol = "1.5"

    def __init__(self) -> None:
        self.__rest_session = Session()
        self.__ws = WebSocket()
        self.__connection_token: str | None = None
        self.__message_id: str | None = None
        self.__groups_token: str | None = None
        self.__dt = int(datetime.now().timestamp() * 1000)
        self.__connected_at: datetime | None = None
        self.__last_long_poll_at: datetime | None = None

    def __enter__(self):
        self.__connect()
        return self

    def __exit__(self, *args):
        self.__close()

    def __close(self):
        if self.__connection_token:
            res = self.__rest_session.post(
                "/".join((
                    Client.__base_rest_url,
                    "signalr",
                    "abort",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "connectionToken": self.__connection_token,
                        "clientProtocol": Client.__client_protocol,
                        "connectionData": "[{\"name\":\"streaming\"}]",
                    },
                    quote_via=quote,
                ),
                json={},
            )
            res.raise_for_status()

        if self.__ws.connected:
            self.__ws.close()

        self.__connection_token = None
        self.__message_id = None
        self.__groups_token = None

    def __connect(self):
        if self.__ws.connected:
            return

        if not self.__connection_token:
            self.__negotiate()

        if self.__groups_token and self.__message_id:
            self.__ws.connect(
                "/".join((
                    Client.__base_wss_url,
                    "signalr",
                    "reconnect",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "groupsToken": self.__groups_token,
                        "messageId": self.__message_id,
                        "clientProtocol": Client.__client_protocol,
                        "connectionToken": self.__connection_token,
                        "connectionData": "[{\"name\":\"streaming\"}]",
                        "tid": randint(0, 11),
                    },
                    quote_via=quote,
                ),
            )

        else:
            while not self.__ws.connected:
                try:
                    self.__ws.connect(
                        "/".join((
                            Client.__base_wss_url,
                            "signalr",
                            "connect",
                        )) + "?" + urlencode(
                            {
                                "transport": "webSockets",
                                "clientProtocol": Client.__client_protocol,
                                "connectionToken": self.__connection_token,
                                "connectionData": "[{\"name\":\"streaming\"}]",
                                "tid": randint(0, 11),
                            },
                            quote_via=quote,
                        ),
                    )

                except WebSocketBadStatusException:
                    continue

            self.__connected_at = datetime.now()
            self.__ws.send(
                json.dumps(
                    {
                        "H": "streaming",
                        "M": "Subscribe",
                        "A": [[
                            "Heartbeat",
                            "CarData.z",
                            "Position.z",
                            "ExtrapolatedClock",
                            "TopThree",
                            "RcmSeries",
                            "TimingStats",
                            "TimingAppData",
                            "WeatherData",
                            "TrackStatus",
                            "DriverList",
                            "RaceControlMessages",
                            "SessionInfo",
                            "SessionData",
                            "LapCount",
                            "TimingData",
                        ]],
                        "I": 0
                    },
                    separators=(',', ':'),
                ),
            )

            while "C" in self.recv()[1]:
                continue

            self.__start()

    def __negotiate(self):
        res = self.__rest_session.get(
            "/".join((
                Client.__base_rest_url,
                "signalr",
                "negotiate",
            )) + "?" + urlencode(
                {
                    "_": str(self.__dt),
                    "clientProtocol": Client.__client_protocol,
                    "connectionData": "[{\"name\":\"streaming\"}]",
                },
                quote_via=quote,
            ),
        )
        res.raise_for_status()
        self.__dt += 1
        res_json = res.json()
        self.__connection_token: str = res_json["ConnectionToken"]
        self.__ws.settimeout(60)

    def __ping(self) -> str:
        res = self.__rest_session.get(
            "/".join((
                Client.__base_rest_url,
                "signalr",
                "ping",
            )) + "?" + urlencode({"_": str(self.__dt)}),
        )
        res.raise_for_status()
        self.__dt += 1
        return res.json()["Response"]

    def __start(self) -> str:
        if self.__connection_token:
            res = self.__rest_session.get(
                "/".join((
                    Client.__base_rest_url,
                    "signalr",
                    "start",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "clientProtocol": Client.__client_protocol,
                        "connectionToken": self.__connection_token,
                        "connectionData": "[{\"name\":\"streaming\"}]",
                        "_": str(self.__dt),
                    },
                    quote_via=quote,
                ),
            )
            res.raise_for_status()
            self.__dt += 1
            return res.json()["Response"]

    def recv(self):
        if self.__ws.connected:
            if self.__last_long_poll_at:
                if (
                    datetime.now() >=
                    self.__last_long_poll_at + Client.__long_poll_interval
                ):
                    self.__last_long_poll_at = datetime.now()
                    self.__ping()

            elif self.__connected_at:
                if (
                    datetime.now() >=
                    self.__connected_at + Client.__long_poll_interval
                ):
                    self.__last_long_poll_at = datetime.now()
                    self.__ping()

            else:
                assert False, "Unreachable code!"

            opcode, recv_data = self.__ws.recv_data()
            opcode: int
            recv_data: bytes
            json_data = json.loads(recv_data)

            if "C" in json_data:
                self.__message_id = json_data["C"]

            if "G" in json_data:
                self.__groups_token = json_data["G"]

            return opcode, json_data

    def streaming_status(self) -> str:
        res = self.__rest_session.get(
            "/".join((
                Client.__base_rest_url,
                "static",
                "StreamingStatus.json",
            )),
        )
        res.raise_for_status()
        res_json = json.loads(res.content.decode("utf-8-sig"))
        streaming_status = res_json["Status"]
        return streaming_status
