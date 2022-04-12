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

import json
from datetime import datetime, timedelta
from random import randint
from typing import Any, Dict
from urllib.parse import quote, urlencode

from requests import ConnectionError, Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)


class F1Client:
    """F1 Live Timing Client"""
    __ping_interval = timedelta(minutes=5)
    __client_protocol = "1.5"

    def __init__(
        self,
        signalr_url: str = "https://livetiming.formula1.com/signalr",
        reconnect: bool = True,
    ) -> None:
        self.__signalr_rest_url = signalr_url
        self.__signalr_wss_url = signalr_url.replace("https://", "wss://")
        self.__rest_session = Session()
        self.__ws = WebSocket(skip_utf8_validation=True)
        self.__connection_token: str | None = None
        self.__message_id: str | None = None
        self.__groups_token: str | None = None
        self.__connected_at: datetime | None = None
        self.__last_ping_at: datetime | None = None
        self.__old_data: Any | None = None
        self.__reconnect = reconnect

    def __enter__(self):
        self.__connect()
        return self

    def __exit__(self, *args):
        self.__close()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if not self.__ws.connected and self.__reconnect:
                self.__connect()

            if self.__ws.connected:
                try:
                    return self.message()

                except WebSocketConnectionClosedException:
                    if not self.__reconnect:
                        raise

                    continue

            raise StopIteration

    def __close(self):
        if self.__connection_token:
            try:
                res = self.__rest_session.post(
                    "/".join((
                        self.__signalr_rest_url,
                        "abort",
                    )) + "?" + urlencode(
                        {
                            "transport": "webSockets",
                            "connectionToken": self.__connection_token,
                            "clientProtocol": F1Client.__client_protocol,
                            "connectionData": [{"name": "streaming"}],
                        },
                        quote_via=quote,
                    ),
                    json={},
                )
                res.raise_for_status()

            except ConnectionError:
                print("Connection error while closing active connection!")

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
            while not self.__ws.connected:
                try:
                    self.__ws.connect(
                        "/".join((
                            self.__signalr_wss_url,
                            "reconnect",
                        )) + "?" + urlencode(
                            {
                                "transport": "webSockets",
                                "groupsToken": self.__groups_token,
                                "messageId": self.__message_id,
                                "clientProtocol": F1Client.__client_protocol,
                                "connectionToken": self.__connection_token,
                                "connectionData": [{"name": "streaming"}],
                                "tid": randint(0, 11),
                            },
                            quote_via=quote,
                        ),
                    )

                except WebSocketBadStatusException:
                    continue

            self.__connected_at = datetime.now()
            self.__last_ping_at = None

        else:
            while not self.__ws.connected:
                try:
                    self.__ws.connect(
                        "/".join((
                            self.__signalr_wss_url,
                            "connect",
                        )) + "?" + urlencode(
                            {
                                "transport": "webSockets",
                                "clientProtocol": F1Client.__client_protocol,
                                "connectionToken": self.__connection_token,
                                "connectionData": [{"name": "streaming"}],
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

            while "R" not in (msg := self.__recv()[1]):
                continue

            self.__old_data = msg["R"]
            print(self.__old_data)
            self.__start()

    def __negotiate(self):
        res = self.__rest_session.get(
            "/".join((
                self.__signalr_rest_url,
                "negotiate",
            )) + "?" + urlencode(
                {
                    "_": str(int(datetime.now().timestamp() * 1000)),
                    "clientProtocol": F1Client.__client_protocol,
                    "connectionData": [{"name": "streaming"}],
                },
                quote_via=quote,
            ),
        )
        res.raise_for_status()
        res_json = res.json()
        self.__connection_token: str = res_json["ConnectionToken"]
        self.__ws.settimeout(20)

    def __ping(self) -> str | None:
        try:
            res = self.__rest_session.get(
                "/".join((
                    self.__signalr_rest_url,
                    "ping",
                )) + "?" + urlencode({
                    "_": str(int(datetime.now().timestamp() * 1000))
                }),
            )
            res.raise_for_status()
            return res.json()["Response"]

        except ConnectionError:
            print("Connection error while pinging!")

    def __recv(self):
        assert self.__ws.connected

        while True:
            try:
                if self.__last_ping_at:
                    if (
                        datetime.now() >=
                        self.__last_ping_at + F1Client.__ping_interval
                    ):
                        self.__last_ping_at = datetime.now()
                        self.__ping()

                elif self.__connected_at:
                    if (
                        datetime.now() >=
                        self.__connected_at + F1Client.__ping_interval
                    ):
                        self.__last_ping_at = datetime.now()
                        self.__ping()

                opcode, recv_data = self.__ws.recv_data()
                opcode: int
                json_data: Dict[str, Any] = json.loads(recv_data)

                if "C" in json_data:
                    self.__message_id: str = json_data["C"]

                if "G" in json_data:
                    self.__groups_token: str = json_data["G"]

                return opcode, json_data

            except WebSocketTimeoutException:
                continue

    def __start(self) -> str:
        assert self.__connection_token

        res = self.__rest_session.get(
            "/".join((
                self.__signalr_rest_url,
                "start",
            )) + "?" + urlencode(
                {
                    "transport": "webSockets",
                    "clientProtocol": F1Client.__client_protocol,
                    "connectionToken": self.__connection_token,
                    "connectionData": [{"name": "streaming"}],
                    "_": str(int(datetime.now().timestamp() * 1000)),
                },
                quote_via=quote,
            ),
        )
        res.raise_for_status()
        return res.json()["Response"]

    def message(self):
        assert self.__ws.connected

        opcode, json_data = self.__recv()
        return json_data

    def streaming_status(self) -> str:
        res = self.__rest_session.get(
            "/".join((
                "https://livetiming.formula1.com",
                "static",
                "StreamingStatus.json",
            )),
        )
        res.raise_for_status()
        res_json = json.loads(res.content.decode("utf-8-sig"))
        streaming_status = res_json["Status"]
        return streaming_status
