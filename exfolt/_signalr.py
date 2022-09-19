from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from json import dumps, loads
from logging import getLogger
from random import randint
from typing import Any, List, TypedDict
from urllib.parse import quote, urlencode

from requests import ConnectionError, HTTPError, Session
from websocket import WebSocket, WebSocketBadStatusException, WebSocketConnectionClosedException, \
    WebSocketTimeoutException


class SignalRNegotiationData(TypedDict):
    """SignalR negotiation data"""

    ConnectionId: str
    ConnectionToken: str


class SignalRInvokation(TypedDict):
    """SignalR hub method invokation data"""

    H: str
    M: str
    A: List[Any]


class SignalRData(TypedDict, total=False):
    C: str
    G: str
    I: int
    M: List[SignalRInvokation]
    R: Any
    S: int


class SignalRClient:
    """
    SignalR client to communicate with SignalR server.

    Currently only supports webSocket transport. Mainly created for use as F1 live timing client
    (F1LiveClient).
    """

    __client_protocol = "1.5"
    __logger = getLogger("eXF1LT.SignalRClient")
    __ping_interval = timedelta(minutes=5)

    def __init__(self, url: str, *hubs: str, reconnect: bool = True):
        self.__command_id = 0
        self.__cookies: List[str] = []
        self.__groups_token: str | None = None
        self.__hubs = hubs
        self.__id: str | None = None
        self.__last_ping_at: datetime | None = None
        self.__message_id: str | None = None
        self.__negotiated_at: int | None = None
        self.__reconnect = reconnect
        self.__rest_transport = Session()
        self.__token: str | None = None
        self.__transport = WebSocket(skip_utf8_validation=True)
        self.__transport_type = "webSockets"
        self.__url = url

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
            f"hubs={self.__hubs}",
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
                    "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                            separators=(",", ":")),
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
                                "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                                        separators=(",", ":")),
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
                    self.__cookies = []

                    for cookie_name, morsel in SimpleCookie(e.resp_headers["set-cookie"]).items():
                        self.__cookies.append(f"{cookie_name}={morsel.value}")

                else:
                    self.__cookies = []
                    self.__token = None
                    self.__groups_token = None
                    self.__message_id = None
                    self.__negotiate()

                continue

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
                "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                        separators=(",", ":")),
            },
        )
        r.raise_for_status()

        r_json: SignalRNegotiationData = r.json()
        self.__token = r_json["ConnectionToken"]
        self.__id = r_json["ConnectionId"]
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
                json_data: SignalRData = loads(raw_data)

                if len(json_data) == 0:
                    SignalRClient.__logger.info("KeepAlive packet received at " +
                                                str(datetime.utcnow()) +
                                                f" from SignalR connection with ID {self.__id}!")

                else:
                    SignalRClient.__logger.info("Received message from SignalR connection with " +
                                                f"ID {self.__id}!")

                if "C" in json_data:
                    self.__message_id = json_data["C"]

                if "G" in json_data:
                    self.__groups_token = json_data["G"]

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
                "connectionData": dumps([{"name": hub} for hub in self.__hubs],
                                        separators=(",", ":")),
                "_": str(self.__negotiated_at),
            },
        )
        r.raise_for_status()
        response: str = r.json()["Response"]
        return response == "started"

    def close(self):
        if self.connected:
            self.__close()

        self.__abort()

    @property
    def connected(self):
        return self.__transport.connected

    @property
    def hubs(self):
        return self.__hubs

    def invoke(self, hub: str, method: str, *args):
        assert hub in self.__hubs
        data: SignalRInvokation = {"H": hub, "M": method, "A": args}
        data |= {"I": self.__command_id}
        self.__transport.send(dumps(data, separators=(",", ":")))
        self.__command_id += 1

    def open(self):
        if not self.__token:
            self.__negotiate()

        if not self.connected:
            self.__connect()

        self.__start()

        return self
