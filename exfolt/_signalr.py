from __future__ import annotations
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from json import dumps, loads
from logging import getLogger
from random import randint
from typing import List, TypedDict
from urllib.parse import quote, urlencode

from requests import ConnectionError, HTTPError, Session
from websocket import WebSocket, WebSocketBadStatusException, WebSocketConnectionClosedException, \
    WebSocketTimeoutException

from ._type import JSONValueDataType


class SignalRNegotiationData(TypedDict):
    """SignalR negotiation data"""

    Url: str
    ConnectionToken: str
    ConnectionId: str
    KeepAliveTimeout: float
    DisconnectTimeout: float
    TryWebSockets: bool
    ProtocolVersion: str
    TransportConnectTimeout: float
    LongPollDelay: float


class SignalRInvokation(TypedDict):
    """SignalR hub method invokation data"""

    H: str
    M: str
    A: List[JSONValueDataType]


class SignalRData(TypedDict, total=False):
    C: str
    G: str
    I: int
    M: List[SignalRInvokation]
    R: JSONValueDataType
    S: int


class SignalRClient:
    """
    SignalR client to communicate with SignalR server.

    Supports webSocket transport. Mainly created for use as F1 live timing client (F1LiveClient).
    """

    __protocol = "1.5"
    __logger = getLogger("eXF1LT.SignalRClient")
    __ping_interval = timedelta(minutes=5)

    def __init__(self, url: str, *hubs: str, reconnect: bool = True):
        self.__command_id = 0
        self.__cookies: List[str] = []
        self.__groups_token = None
        self.__hubs = [hub for hub in hubs]
        self.__last_ping_at = None
        self.__message_id = None
        self.__negotiated_at = None
        self.__negotiation_data = None
        self.__reconnect = reconnect
        self.__rest_transport = Session()
        self.__url = url
        self.__ws_transport = WebSocket(skip_utf8_validation=True)

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
            f"command_id={self.__command_id}",
            f"groups_token={self.__groups_token}",
            f"hubs={self.__hubs}",
            f"last_ping_at={self.__last_ping_at}",
            f"message_id={self.__message_id}",
            f"negotiated_at={self.__negotiated_at}",
            f"negotiation_data={self.__negotiation_data}",
            f"reconnect={self.__reconnect}",
            f"url={self.__url}",
        ))

        return f"{type(self).__name__}({__data})"

    def __str__(self):
        return self.__repr__()

    def __abort(self):
        if not self.__negotiation_data:
            return False

        try:
            connection_id = self.__negotiation_data["ConnectionId"]
            connection_token = self.__negotiation_data["ConnectionToken"]
            SignalRClient.__logger.info(f"Aborting SignalR connection with ID {connection_id}!")
            r = self.__rest_transport.post(f"{self.__url}/abort",
                                           params={"transport": "webSockets",
                                                   "connectionToken": connection_token,
                                                   "clientProtocol": SignalRClient.__protocol,
                                                   "connectionData": dumps([{"name": hub} for hub
                                                                            in self.__hubs],
                                                                           separators=(",", ":"))},
                                           json={})
            r.raise_for_status()
            return True

        except (ConnectionError, HTTPError):
            SignalRClient.__logger.error("Error while trying to abort SignalR connection with " +
                                         f"ID {self.__negotiation_data['ConnectionId']}!")
            return False

    def __close(self):
        if not self.__ws_transport.connected:
            return

        SignalRClient.__logger.info("Closing SignalR connection with ID " +
                                    f"{self.__negotiation_data['ConnectionId']}!")
        self.__ws_transport.close()
        self.__negotiation_data = None

    def __connect(self):
        try:
            assert not self.connected and self.__negotiation_data
            SignalRClient.__logger.info(f"Connecting to SignalR transport with URL {self.__url}!")

        except AssertionError as ex:
            if self.connected:
                SignalRClient.__logger.warning("Connection already established!")

            if not self.__negotiation_data:
                SignalRClient.__logger.warning("No negotiation data available!")

            raise ex

        while True:
            try:
                if self.__groups_token and self.__message_id:
                    self.__ws_transport.connect(
                        f"{self.__url.replace('https://', 'wss://')}/reconnect" + "?" + urlencode(
                            {
                                "transport": "webSockets",
                                "groupsToken": self.__groups_token,
                                "messageId": self.__message_id,
                                "clientProtocol": SignalRClient.__protocol,
                                "connectionToken": self.__negotiation_data["ConnectionToken"],
                                "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                                        separators=(",", ":")),
                                "tid": randint(0, 11),
                            },
                            quote_via=quote,
                        ),
                        cookie=";".join(self.__cookies) if len(self.__cookies) > 0 else None,
                    )

                else:
                    self.__ws_transport.connect(
                        f"{self.__url.replace('https://', 'wss://')}/connect" + "?" + urlencode(
                            {
                                "transport": "webSockets",
                                "clientProtocol": SignalRClient.__protocol,
                                "connectionToken": self.__negotiation_data["ConnectionToken"],
                                "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                                        separators=(",", ":")),
                                "tid": randint(0, 11),
                            },
                            quote_via=quote,
                        ),
                        cookie=";".join(self.__cookies) if len(self.__cookies) > 0 else None,
                    )

                self.__last_ping_at = datetime.utcnow()
                break

            except WebSocketBadStatusException as e:
                SignalRClient.__logger.warning(
                    "\n".join((
                        "Connecting to SignalR transport failed due to transport handshake " +
                        "exception! Will attempt to establish new connection!",
                        f"Status Code: {e.status_code}",
                        f"Arguments: {e.args}",
                        f"Response Headers: {e.resp_headers}",
                    )),
                )

                if "set-cookie" in e.resp_headers:
                    self.__cookies: List[str] = []

                    for cookie_name, morsel in SimpleCookie(e.resp_headers["set-cookie"]).items():
                        self.__cookies.append(f"{cookie_name}={morsel.value}")

                else:
                    self.__cookies: List[str] = []
                    self.__negotiation_data = None
                    self.__groups_token = None
                    self.__message_id = None
                    self.__negotiate()

                continue

    def __negotiate(self):
        if self.__negotiation_data:
            return

        SignalRClient.__logger.info("Negotiating for new SignalR connection!")
        self.__negotiated_at = int(datetime.utcnow().timestamp() * 1000)

        r = self.__rest_transport.get(
            f"{self.__url}/negotiate",
            params={
                "_": str(self.__negotiated_at),
                "clientProtocol": SignalRClient.__protocol,
                "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                        separators=(",", ":")),
            },
        )
        r.raise_for_status()

        r_json: SignalRNegotiationData = r.json()
        self.__negotiation_data = r_json
        self.__keep_alive_timeout = r_json["KeepAliveTimeout"]
        self.__cookies = [f"{cookie.name}={cookie.value}" for cookie in r.cookies]

    def __ping(self):
        if not self.__negotiation_data:
            return False

        self.__negotiated_at += 1

        try:
            SignalRClient.__logger.info("Pinging SignalR connection with ID " +
                                        f"{self.__negotiation_data['ConnectionId']}!")
            r = self.__rest_transport.get(f"{self.__url}/ping",
                                          params={"_": str(self.__negotiated_at)})
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

                opcode, raw_data = self.__ws_transport.recv_data()
                opcode: int
                raw_data: bytes
                json_data: SignalRData = loads(raw_data)
                id = self.__negotiation_data["ConnectionId"]

                if len(json_data) == 0:
                    SignalRClient.__logger.info("KeepAlive packet received at " +
                                                str(datetime.utcnow()) +
                                                f" from SignalR connection with ID {id}!")

                else:
                    SignalRClient.__logger.info("Received message from SignalR connection with " +
                                                f"ID {id}!")

                if "C" in json_data:
                    self.__message_id = json_data["C"]

                if "G" in json_data:
                    self.__groups_token = json_data["G"]

                return opcode, json_data

            except WebSocketTimeoutException:
                continue

    def __start(self):
        if not self.__negotiation_data:
            return False

        self.__negotiated_at += 1
        connection_token = self.__negotiation_data["ConnectionToken"]
        connection_id = self.__negotiation_data["ConnectionId"]
        SignalRClient.__logger.info(f"Started SignalR connection with ID {connection_id}!")
        r = self.__rest_transport.get(f"{self.__url}/start",
                                      params={"transport": "webSockets",
                                              "clientProtocol": SignalRClient.__protocol,
                                              "connectionToken": connection_token,
                                              "connectionData": dumps([{"name": hub} for hub
                                                                       in self.__hubs],
                                                                      separators=(",", ":")),
                                              "_": str(self.__negotiated_at)})
        r.raise_for_status()
        response: str = r.json()["Response"]
        return response == "started"

    def close(self):
        if self.connected:
            self.__close()

        self.__abort()

    @property
    def connected(self):
        return self.__ws_transport.connected

    @property
    def hubs(self):
        return self.__hubs

    def invoke(self, hub: str, method: str, *args: JSONValueDataType):
        assert hub in self.__hubs
        data: SignalRInvokation = {"H": hub, "M": method, "A": [arg for arg in args]}
        data |= {"I": self.__command_id}
        self.__send(dumps(data, separators=(",", ":")))
        self.__command_id += 1

    def open(self):
        if not self.__negotiation_data:
            self.__negotiate()

        if not self.connected:
            self.__connect()

        self.__start()

        return self
