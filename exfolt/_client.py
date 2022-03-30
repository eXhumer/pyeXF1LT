import json
from asyncio import TimeoutError
from datetime import datetime, timedelta
from random import randint
from typing import Any, Dict
from urllib.parse import quote, urlencode

from aiohttp import ClientSession, ClientWebSocketResponse
from requests import Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
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
        self.__dt = int(datetime.now().timestamp() * 1000)
        self.__connected_at: datetime | None = None
        self.__last_ping_at: datetime | None = None
        self.__reconnect = reconnect

    def __enter__(self):
        self.__connect()
        return self

    def __exit__(self, *args):
        self.__close()

    def __iter__(self):
        return self

    def __next__(self):
        if not self.__ws.connected and self.__reconnect:
            self.__connect()

        if self.__ws.connected:
            return self.message()

        raise StopIteration

    def __close(self):
        if self.__connection_token:
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

            while "C" in self.__recv()[1]:
                continue

            self.__start()

    def __negotiate(self):
        res = self.__rest_session.get(
            "/".join((
                self.__signalr_rest_url,
                "negotiate",
            )) + "?" + urlencode(
                {
                    "_": str(self.__dt),
                    "clientProtocol": F1Client.__client_protocol,
                    "connectionData": [{"name": "streaming"}],
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
                self.__signalr_rest_url,
                "ping",
            )) + "?" + urlencode({"_": str(self.__dt)}),
        )
        res.raise_for_status()
        self.__dt += 1
        return res.json()["Response"]

    def __recv(self):
        assert self.__ws.connected

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

        else:
            assert False, "Unreachable code!"

        while True:
            try:
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
        if self.__connection_token:
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
                        "_": str(self.__dt),
                    },
                    quote_via=quote,
                ),
            )
            res.raise_for_status()
            self.__dt += 1
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


class AsyncF1Client:
    """F1 Live Timing Client"""
    __ping_interval = timedelta(minutes=5)
    __client_protocol = "1.5"

    def __init__(
        self,
        signalr_url: str = "https://livetiming.formula1.com/signalr",
    ) -> None:
        self.__signalr_rest_url = signalr_url
        self.__signalr_wss_url = signalr_url.replace("https://", "wss://")
        self.__session = ClientSession()
        self.__ws: ClientWebSocketResponse | None = None
        self.__connection_token: str | None = None
        self.__message_id: str | None = None
        self.__groups_token: str | None = None
        self.__dt = int(datetime.now().timestamp() * 1000)
        self.__connected_at: datetime | None = None
        self.__last_ping_at: datetime | None = None

    async def __aenter__(self):
        await self.__connect()
        return self

    async def __aexit__(self, *args):
        await self.__close()
        await self.__session.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if (not self.__ws or self.__ws.closed) and self.__reconnect:
            await self.__connect()

        if self.__ws and not self.__ws.closed:
            return await self.message()

        raise StopAsyncIteration

    async def __close(self):
        if self.__connection_token:
            res = await self.__session.post(
                "/".join((
                    self.__signalr_rest_url,
                    "abort",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "connectionToken": self.__connection_token,
                        "clientProtocol": AsyncF1Client.__client_protocol,
                        "connectionData": [{"name": "streaming"}],
                    },
                    quote_via=quote,
                ),
                json={},
            )
            res.raise_for_status()
            res.close()

        if self.__ws and not self.__ws.closed:
            await self.__ws.close()

        self.__connection_token = None
        self.__message_id = None
        self.__groups_token = None

    async def __connect(self):
        if self.__ws and not self.__ws.closed:
            return

        if not self.__connection_token:
            await self.__negotiate()

        if self.__groups_token and self.__message_id:
            self.__ws = await self.__session.ws_connect(
                "/".join((
                    self.__signalr_wss_url,
                    "reconnect",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "groupsToken": self.__groups_token,
                        "messageId": self.__message_id,
                        "clientProtocol": AsyncF1Client.__client_protocol,
                        "connectionToken": self.__connection_token,
                        "connectionData": [{"name": "streaming"}],
                        "tid": randint(0, 11),
                    },
                    quote_via=quote,
                ),
                timeout=60,
            )

        else:
            self.__ws = await self.__session.ws_connect(
                "/".join((
                    self.__signalr_wss_url,
                    "connect",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "clientProtocol": AsyncF1Client.__client_protocol,
                        "connectionToken": self.__connection_token,
                        "connectionData": [{"name": "streaming"}],
                        "tid": randint(0, 11),
                    },
                    quote_via=quote,
                ),
                timeout=60,
            )

            self.__connected_at = datetime.now()
            await self.__ws.send_str(
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

            while "C" in await self.__recv():
                continue

            await self.__start()

    async def __negotiate(self):
        res = await self.__session.get(
            "/".join((
                self.__signalr_rest_url,
                "negotiate",
            )) + "?" + urlencode(
                {
                    "_": str(self.__dt),
                    "clientProtocol": AsyncF1Client.__client_protocol,
                    "connectionData": [{"name": "streaming"}],
                },
                quote_via=quote,
            ),
        )
        res.raise_for_status()
        self.__dt += 1
        res_json = await res.json()
        self.__connection_token: str = res_json["ConnectionToken"]

    async def __ping(self) -> str:
        res = await self.__session.get(
            "/".join((
                self.__signalr_rest_url,
                "ping",
            )) + "?" + urlencode({"_": str(self.__dt)}),
        )
        res.raise_for_status()
        self.__dt += 1
        return (await res.json())["Response"]

    async def __recv(self):
        assert self.__ws and not self.__ws.closed

        if self.__last_ping_at:
            if (
                datetime.now() >=
                self.__last_ping_at + AsyncF1Client.__ping_interval
            ):
                self.__last_ping_at = datetime.now()
                await self.__ping()

        elif self.__connected_at:
            if (
                datetime.now() >=
                self.__connected_at + AsyncF1Client.__ping_interval
            ):
                self.__last_ping_at = datetime.now()
                await self.__ping()

        else:
            assert False, "Unreachable code!"

        while True:
            try:
                recv_data = await self.__ws.receive_str()
                json_data: Dict[str, Any] = json.loads(recv_data)

                if "C" in json_data:
                    self.__message_id: str = json_data["C"]

                if "G" in json_data:
                    self.__groups_token: str = json_data["G"]

                return json_data

            except TimeoutError:
                continue

    async def __start(self) -> str:
        if self.__connection_token:
            res = await self.__session.get(
                "/".join((
                    self.__signalr_rest_url,
                    "start",
                )) + "?" + urlencode(
                    {
                        "transport": "webSockets",
                        "clientProtocol": AsyncF1Client.__client_protocol,
                        "connectionToken": self.__connection_token,
                        "connectionData": [{"name": "streaming"}],
                        "_": str(self.__dt),
                    },
                    quote_via=quote,
                ),
            )
            res.raise_for_status()
            self.__dt += 1
            return (await res.json())["Response"]

    async def message(self):
        assert self.__ws and not self.__ws.closed
        return await self.__recv()

    async def streaming_status(self) -> str:
        res = await self.__session.get(
            "/".join((
                "https://livetiming.formula1.com",
                "static",
                "StreamingStatus.json",
            )),
        )
        res.raise_for_status()
        res_json = json.loads((await res.content.read()).decode("utf-8-sig"))
        streaming_status = res_json["Status"]
        return streaming_status
