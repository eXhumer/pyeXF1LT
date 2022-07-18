from datetime import datetime, timedelta
from json import dumps, loads
from logging import getLogger
from random import randint
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

from requests import ConnectionError, HTTPError, Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)


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
        self.__command_id = 0
        self.__connection_data = connection_data
        self.__cookies: List[str] = []
        self.__groups_token: Optional[str] = None
        self.__id: Optional[str] = None
        self.__last_ping_at: Optional[datetime] = None
        self.__message_id: Optional[str] = None
        self.__negotiated_at: Optional[int] = None
        self.__reconnect = reconnect
        self.__rest_transport = Session()
        self.__token: Optional[str] = None
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
                                                str(datetime.utcnow()) +
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
