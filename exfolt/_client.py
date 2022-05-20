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
from enum import IntEnum
from random import randint
from typing import Any, Dict, List, Literal
from urllib.parse import quote, urlencode

from requests import ConnectionError, HTTPError, Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)

from ._model import (
    DriverData,
    InitialWeatherData,
    WeatherDataChange,
)


WeatherDataEntry = Dict[
    Literal[
        "AirTemp",
        "TrackTemp",
        "Humidity",
        "Pressure",
        "Rainfall",
        "WindDirection",
        "WindSpeed",
    ],
    str,
]


class WeatherTracker:
    class NotifyReason(IntEnum):
        POSITIVE = 1
        NEGATIVE = 2

    def __init__(
        self,
        at_notify_interval: int = 60,
        at_threshold_delta: float = 0.5,
        at_threshold_interval: int = 5,
        tt_notify_interval: int = 60,
        tt_threshold_delta: float = 0.5,
        tt_threshold_interval: int = 5,
        hu_notify_interval: int = 60,
        hu_threshold_delta: float = 5,
        hu_threshold_interval: int = 5,
        pa_notify_interval: int = 60,
        pa_threshold_delta: float = 0.5,
        pa_threshold_interval: int = 5,
        wd_notify_interval: int = 60,
        ws_notify_interval: int = 60,
        ws_threshold_delta: float = 0.5,
        ws_threshold_interval: int = 5,
    ) -> None:
        self.__at_notify_interval = at_notify_interval
        self.__at_threshold_delta = at_threshold_delta
        self.__at_threshold_interval = at_threshold_interval
        self.__at_data_history: List[float] = []
        self.__last_at_notify_at: datetime | None = None
        self.__last_at_notify_reason: WeatherTracker.NotifyReason | None = None
        self.__tt_notify_interval = tt_notify_interval
        self.__tt_threshold_delta = tt_threshold_delta
        self.__tt_threshold_interval = tt_threshold_interval
        self.__tt_data_history: List[float] = []
        self.__last_tt_notify_at: datetime | None = None
        self.__last_tt_notify_reason: WeatherTracker.NotifyReason | None = None
        self.__hu_notify_interval = hu_notify_interval
        self.__hu_threshold_delta = hu_threshold_delta
        self.__hu_threshold_interval = hu_threshold_interval
        self.__hu_data_history: List[float] = []
        self.__last_hu_notify_at: datetime | None = None
        self.__last_hu_notify_reason: WeatherTracker.NotifyReason | None = None
        self.__pa_notify_interval = pa_notify_interval
        self.__pa_threshold_delta = pa_threshold_delta
        self.__pa_threshold_interval = pa_threshold_interval
        self.__pa_data_history: List[float] = []
        self.__last_pa_notify_at: datetime | None = None
        self.__last_pa_notify_reason: WeatherTracker.NotifyReason | None = None
        self.__rf_data_history: List[int] = []
        self.__wd_notify_interval = wd_notify_interval
        self.__wd_data_history: List[int] = []
        self.__last_wd_notify_at: datetime | None = None
        self.__ws_notify_interval = ws_notify_interval
        self.__ws_threshold_delta = ws_threshold_delta
        self.__ws_threshold_interval = ws_threshold_interval
        self.__ws_data_history: List[float] = []
        self.__last_ws_notify_at: datetime | None = None
        self.__last_ws_notify_reason: WeatherTracker.NotifyReason | None = None

    def update_data(self, data: WeatherDataEntry):
        self.__at_data_history.append(float(data["AirTemp"]))
        self.__tt_data_history.append(float(data["TrackTemp"]))
        self.__hu_data_history.append(float(data["Humidity"]))
        self.__pa_data_history.append(float(data["Pressure"]))
        self.__rf_data_history.append(int(data["Rainfall"]))
        self.__wd_data_history.append(int(data["WindDirection"]))
        self.__ws_data_history.append(float(data["WindSpeed"]))

    def notify_changes(self):
        if len(self.__at_data_history) == 1:
            return InitialWeatherData(
                self.__at_data_history[0],
                self.__tt_data_history[0],
                self.__hu_data_history[0],
                self.__pa_data_history[0],
                bool(self.__rf_data_history[0]),
                self.__wd_data_history[0],
                self.__ws_data_history[0],
            )

        else:
            changes = []

            at_interval = min(
                self.__at_threshold_interval,
                len(self.__at_data_history),
            )

            at_history = self.__at_data_history[-at_interval:]

            if at_history[-1] - at_history[0] > 0:
                if at_history[-1] - at_history[0] > self.__at_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_at_notify_at and
                        self.__last_at_notify_reason
                    ):
                        if (
                            self.__last_at_notify_reason ==
                            WeatherTracker.NotifyReason.POSITIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_at_notify_at
                            ).total_seconds() < self.__at_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(at_history[-1] - at_history[0], 1)
                        changes.append({
                            "AirTemp": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{change}",
                                "New": f"{at_history[-1]}",
                                "Previous": f"{at_history[0]}",
                            }
                        })

            elif at_history[0] - at_history[-1] > 0:
                if at_history[0] - at_history[-1] > self.__at_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_at_notify_at and
                        self.__last_at_notify_reason
                    ):
                        if (
                            self.__last_at_notify_reason ==
                            WeatherTracker.NotifyReason.NEGATIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_at_notify_at
                            ).total_seconds() < self.__at_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(at_history[-1] - at_history[0], 1)
                        changes.append({
                            "AirTemp": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{change}",
                                "New": f"{at_history[-1]}",
                                "Previous": f"{at_history[0]}",
                            }
                        })

            tt_interval = min(
                self.__tt_threshold_interval,
                len(self.__tt_data_history),
            )

            tt_history = self.__tt_data_history[-tt_interval:]

            if tt_history[-1] - tt_history[0] > 0:
                if tt_history[-1] - tt_history[0] > self.__tt_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_tt_notify_at and
                        self.__last_tt_notify_reason
                    ):
                        if (
                            self.__last_tt_notify_reason ==
                            WeatherTracker.NotifyReason.POSITIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_tt_notify_at
                            ).total_seconds() < self.__tt_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(tt_history[-1] - tt_history[0], 1)
                        changes.append({
                            "TrackTemp": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{change}",
                                "New": f"{tt_history[-1]}",
                                "Previous": f"{tt_history[0]}",
                            }
                        })

            elif tt_history[0] - tt_history[-1] > 0:
                if tt_history[0] - tt_history[-1] > self.__tt_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_tt_notify_at and
                        self.__last_tt_notify_reason
                    ):
                        if (
                            self.__last_at_notify_reason ==
                            WeatherTracker.NotifyReason.NEGATIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_tt_notify_at
                            ).total_seconds() < self.__tt_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(tt_history[-1] - tt_history[0], 1)
                        changes.append({
                            "TrackTemp": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{change}",
                                "New": f"{tt_history[-1]}",
                                "Previous": f"{tt_history[0]}",
                            }
                        })

            hu_interval = min(
                self.__hu_threshold_interval,
                len(self.__hu_data_history),
            )

            hu_history = self.__hu_data_history[-hu_interval:]

            if hu_history[-1] - hu_history[0] > 0:
                if hu_history[-1] - hu_history[0] > self.__hu_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_hu_notify_at and
                        self.__last_hu_notify_reason
                    ):
                        if (
                            self.__last_hu_notify_reason ==
                            WeatherTracker.NotifyReason.POSITIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_hu_notify_at
                            ).total_seconds() < self.__hu_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(hu_history[-1] - hu_history[0], 1)
                        changes.append({
                            "Humidity": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{change}",
                                "New": f"{hu_history[-1]}",
                                "Previous": f"{hu_history[0]}",
                            }
                        })

            elif hu_history[0] - hu_history[-1] > 0:
                if hu_history[0] - hu_history[-1] > self.__hu_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_hu_notify_at and
                        self.__last_hu_notify_reason
                    ):
                        if (
                            self.__last_at_notify_reason ==
                            WeatherTracker.NotifyReason.NEGATIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_hu_notify_at
                            ).total_seconds() < self.__hu_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(hu_history[-1] - hu_history[0], 1)
                        changes.append({
                            "Humidity": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{change}",
                                "New": f"{hu_history[-1]}",
                                "Previous": f"{hu_history[0]}",
                            }
                        })

            pa_interval = min(
                self.__pa_threshold_interval,
                len(self.__pa_data_history),
            )

            pa_history = self.__pa_data_history[-pa_interval:]

            if pa_history[-1] - pa_history[0] > 0:
                if pa_history[-1] - pa_history[0] > self.__pa_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_pa_notify_at and
                        self.__last_pa_notify_reason
                    ):
                        if (
                            self.__last_pa_notify_reason ==
                            WeatherTracker.NotifyReason.POSITIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_pa_notify_at
                            ).total_seconds() < self.__pa_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(pa_history[-1] - pa_history[0], 1)
                        changes.append({
                            "Pressure": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{change}",
                                "New": f"{pa_history[-1]}",
                                "Previous": f"{pa_history[0]}",
                            }
                        })

            elif pa_history[0] - pa_history[-1] > 0:
                if pa_history[0] - pa_history[-1] > self.__pa_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_pa_notify_at and
                        self.__last_pa_notify_reason
                    ):
                        if (
                            self.__last_at_notify_reason ==
                            WeatherTracker.NotifyReason.NEGATIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_pa_notify_at
                            ).total_seconds() < self.__pa_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(pa_history[-1] - pa_history[0], 1)
                        changes.append({
                            "Pressure": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{change}",
                                "New": f"{pa_history[-1]}",
                                "Previous": f"{pa_history[0]}",
                            }
                        })

            rf_history = self.__rf_data_history[-2:]

            if rf_history[0] != rf_history[1]:
                changes.append({
                    "Rainfall": {
                        "Change": (
                            "Wet"
                            if bool(rf_history[1])
                            else "Dry"
                        ),
                    }
                })

            wd_history = self.__wd_data_history[-2:]

            if wd_history[0] != wd_history[1]:
                notify_change = True

                if self.__last_wd_notify_at:
                    if (
                        datetime.now() -
                        self.__last_wd_notify_at
                    ).total_seconds() < self.__wd_notify_interval:
                        notify_change = False

                if notify_change:
                    changes.append({
                        "WindDirection": {
                            "New": f"{wd_history[-1]}",
                            "Previous": f"{wd_history[0]}",
                        }
                    })

            ws_interval = min(
                self.__ws_threshold_interval,
                len(self.__ws_data_history),
            )

            ws_history = self.__ws_data_history[-ws_interval:]

            if ws_history[-1] - ws_history[0] > 0:
                if ws_history[-1] - ws_history[0] > self.__ws_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_ws_notify_at and
                        self.__last_ws_notify_reason
                    ):
                        if (
                            self.__last_ws_notify_reason ==
                            WeatherTracker.NotifyReason.POSITIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_ws_notify_at
                            ).total_seconds() < self.__ws_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(ws_history[-1] - ws_history[0], 1)
                        changes.append({
                            "WindSpeed": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{change}",
                                "New": f"{ws_history[-1]}",
                                "Previous": f"{ws_history[0]}",
                            }
                        })

            elif ws_history[0] - ws_history[-1] > 0:
                if ws_history[0] - ws_history[-1] > self.__ws_threshold_delta:
                    notify_change = True

                    if (
                        self.__last_ws_notify_at and
                        self.__last_ws_notify_reason
                    ):
                        if (
                            self.__last_at_notify_reason ==
                            WeatherTracker.NotifyReason.NEGATIVE
                        ):
                            if (
                                datetime.now() -
                                self.__last_ws_notify_at
                            ).total_seconds() < self.__ws_notify_interval:
                                notify_change = False

                    if notify_change:
                        change = round(ws_history[-1] - ws_history[0], 1)
                        changes.append({
                            "WindSpeed": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{change}",
                                "New": f"{ws_history[-1]}",
                                "Previous": f"{ws_history[0]}",
                            }
                        })

            changes_list = []

            if len(changes) > 0:
                for change in changes:
                    if "AirTemp" in change.keys():
                        change = change["AirTemp"]
                        self.__last_at_notify_at = datetime.now()
                        self.__last_at_notify_reason = change["Reason"]

                        changes_list.append(
                            WeatherDataChange(
                                "Air Temperature Change Information",
                                change=change["Change"],
                                new=change["New"],
                                previous=change["Previous"],
                            )
                        )

                    elif "TrackTemp" in change.keys():
                        change = change["TrackTemp"]
                        self.__last_tt_notify_at = datetime.now()
                        self.__last_tt_notify_reason = change["Reason"]

                        changes_list.append(
                            WeatherDataChange(
                                "Track Temperature Change Information",
                                change=change["Change"],
                                new=change["New"],
                                previous=change["Previous"],
                            )
                        )

                    elif "Humidity" in change.keys():
                        change = change["Humidity"]
                        self.__last_hu_notify_at = datetime.now()
                        self.__last_hu_notify_reason = change["Reason"]

                        changes_list.append(
                            WeatherDataChange(
                                "Humidity Change Information",
                                change=change["Change"],
                                new=change["New"],
                                previous=change["Previous"],
                            )
                        )

                    elif "Pressure" in change.keys():
                        change = change["Pressure"]
                        self.__last_pa_notify_at = datetime.now()
                        self.__last_pa_notify_reason = change["Reason"]

                        changes_list.append(
                            WeatherDataChange(
                                "Pressure Change Information",
                                change=change["Change"],
                                new=change["New"],
                                previous=change["Previous"],
                            )
                        )

                    elif "Rainfall" in change.keys():
                        change = change["Rainfall"]
                        changes_list.append(
                            WeatherDataChange(
                                "Track Status Change Information",
                                change=change["Change"],
                            )
                        )

                    elif "WindDirection" in change.keys():
                        change = change["WindDirection"]
                        self.__last_wd_notify_at = datetime.now()

                        changes_list.append(
                            WeatherDataChange(
                                "Wind Direction Change Information",
                                new=change["New"],
                                previous=change["Previous"],
                            )
                        )

                    elif "WindSpeed" in change.keys():
                        change = change["WindSpeed"]
                        self.__last_ws_notify_at = datetime.now()
                        self.__last_ws_notify_reason = change["Reason"]

                        changes_list.append(
                            WeatherDataChange(
                                "Wind Speed Change Information",
                                change=change["Change"],
                                new=change["New"],
                                previous=change["Previous"],
                            )
                        )

            return changes_list


class F1Client:
    """F1 Live Timing Client"""
    __ping_interval = timedelta(minutes=5)
    __client_protocol = "1.5"

    def __init__(
        self,
        base_url: str = "https://livetiming.formula1.com",
        signalr_endpoint: str = "signalr",
        reconnect: bool = True,
    ) -> None:
        signalr_url = f"{base_url}/{signalr_endpoint}"
        self.___base_url = base_url
        self.__signalr_rest_url = signalr_url
        self.__signalr_wss_url = signalr_url.replace("https://", "wss://")
        self.__rest_session = Session()
        self.__ws = WebSocket(skip_utf8_validation=True)
        self.__connection_token: str | None = None
        self.__message_id: str | None = None
        self.__groups_token: str | None = None
        self.__connected_at: datetime | None = None
        self.__negotiate_at: int | None = None
        self.__last_ping_at: datetime | None = None
        self.__old_data: Any | None = None
        self.__reconnect = reconnect
        self.__driver_data = {}

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

            except (ConnectionError, HTTPError):
                print("Connection error while closing active connection!")

        if self.__ws.connected:
            self.__ws.send(
                json.dumps(
                    {
                        "H": "streaming",
                        "M": "Unsubscribe",
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

            if "DriverList" in self.__old_data:
                for drv_num, drv_data in self.__old_data["DriverList"].items():
                    if drv_num == "_kf":
                        continue

                    self.__driver_data.update({
                        drv_num: DriverData(
                            drv_num,
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
                    })

            self.__start()

    def __negotiate(self):
        self.__negotiate_at = int(datetime.now().timestamp() * 1000)

        res = self.__rest_session.get(
            "/".join((
                self.__signalr_rest_url,
                "negotiate",
            )) + "?" + urlencode(
                {
                    "_": str(self.__negotiate_at),
                    "clientProtocol": F1Client.__client_protocol,
                    "connectionData": [{"name": "streaming"}],
                },
                quote_via=quote,
            ),
        )
        res.raise_for_status()
        res_json = res.json()
        self.__connection_token: str = res_json["ConnectionToken"]
        self.__ws.settimeout(2)

    def __ping(self) -> str | None:
        assert self.__negotiate_at
        self.__negotiate_at += 1

        try:
            res = self.__rest_session.get(
                "/".join((
                    self.__signalr_rest_url,
                    "ping",
                )) + "?" + urlencode({
                    "_": str(self.__negotiate_at)
                }),
            )
            res.raise_for_status()
            return res.json()["Response"]

        except (ConnectionError, HTTPError):
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

                if (
                    "M" in json_data and
                    len(json_data["M"]) == 1 and
                    json_data["M"][0]["A"][0] == "DriverList"
                ):
                    for drv_num, drv_data in json_data["M"][0]["A"][1].items():
                        if type(drv_data) == dict:
                            if "Line" in drv_data and len(drv_data) == 1:
                                continue

                            else:
                                self.__driver_data.update({
                                    drv_num: DriverData(
                                        drv_num,
                                        broadcast_name=drv_data[
                                            "BroadcastName"
                                        ],
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
                                })

                return opcode, json_data

            except WebSocketTimeoutException:
                continue

    def __start(self) -> str:
        assert self.__connection_token and self.__negotiate_at
        self.__negotiate_at += 1

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
                    "_": str(self.__negotiate_at),
                },
                quote_via=quote,
            ),
        )
        res.raise_for_status()
        return res.json()["Response"]

    def driver_data(self, number: str) -> DriverData | None:
        if number not in self.__driver_data:
            return

        return self.__driver_data[number]

    def message(self):
        assert self.__ws.connected

        opcode, json_data = self.__recv()
        return json_data

    def streaming_status(self) -> str:
        res = self.__rest_session.get(
            "/".join((
                self.___base_url,
                "static",
                "StreamingStatus.json",
            )),
        )
        res.raise_for_status()
        res_json = json.loads(res.content.decode("utf-8-sig"))
        streaming_status = res_json["Status"]
        return streaming_status

    def get_archived_session_page(
        self,
        year: int,
        event_name: str,
        event_date: str,
        session_date: str,
        session_name: str,
        page: str,
        json_stream: bool = False,
    ):
        return self.__rest_session.get(
            "/".join((
                self.___base_url,
                "static",
                str(year),
                f"{event_date}_{event_name.replace(' ', '_')}",
                f"{session_date}_{session_name.replace(' ', '_')}",
                f"{page}.jsonStream" if json_stream else f"{page}.json",
            )),
        )
