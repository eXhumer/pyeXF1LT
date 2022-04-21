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
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from random import randint
from typing import Any, Dict, List, Literal
from urllib.parse import quote, urlencode

from requests import ConnectionError, Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)

from ._model import DiscordModel


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
        hu_threshold_delta: float = 0.5,
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

    def notify_change_embed(self):
        if len(self.__at_data_history) == 1:
            ts = "Dry" if self.__rf_data_history[0] == 0 else "Wet"

            return [
                DiscordModel.Embed(
                    title="Initial Weather Information",
                    fields=[
                        DiscordModel.Embed.Field(
                            "Air Temperature (Celsius)",
                            f"{self.__at_data_history[0]}",
                        ),
                        DiscordModel.Embed.Field(
                            "Track Temperature (Celsius)",
                            f"{self.__tt_data_history[0]}",
                        ),
                        DiscordModel.Embed.Field(
                            "Humidity (%)",
                            f"{self.__hu_data_history[0]}",
                        ),
                        DiscordModel.Embed.Field(
                            "Pressure (mbar)",
                            f"{self.__pa_data_history[0]}",
                        ),
                        DiscordModel.Embed.Field(
                            "Track Status (Wet / Dry)",
                            ts,
                        ),
                        DiscordModel.Embed.Field(
                            "Wind Direction (Degree)",
                            f"{self.__wd_data_history[0]}",
                        ),
                        DiscordModel.Embed.Field(
                            "Wind Speed",
                            f"{self.__ws_data_history[0]}",
                        ),
                    ],
                    timestamp=datetime.now(tz=timezone.utc),
                )
            ]

        else:
            changes = []

            at_interval = min(
                self.__at_threshold_interval,
                len(self.__at_data_history),
            )

            at_history = self.__at_data_history[-at_interval:0]

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
                        changes.append({
                            "AirTemp": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{at_history[-1] - at_history[0]}",
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
                        changes.append({
                            "AirTemp": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{at_history[-1] - at_history[0]}",
                                "New": f"{at_history[-1]}",
                                "Previous": f"{at_history[0]}",
                            }
                        })

            tt_interval = min(
                self.__tt_threshold_interval,
                len(self.__tt_data_history),
            )

            tt_history = self.__tt_data_history[-tt_interval:0]

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
                        changes.append({
                            "TrackTemp": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{tt_history[-1] - tt_history[0]}",
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
                        changes.append({
                            "TrackTemp": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{tt_history[-1] - tt_history[0]}",
                                "New": f"{tt_history[-1]}",
                                "Previous": f"{tt_history[0]}",
                            }
                        })

            hu_interval = min(
                self.__hu_threshold_interval,
                len(self.__hu_data_history),
            )

            hu_history = self.__hu_data_history[-hu_interval:0]

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
                        changes.append({
                            "Humidity": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{hu_history[-1] - hu_history[0]}",
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
                        changes.append({
                            "Humidity": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{hu_history[-1] - hu_history[0]}",
                                "New": f"{hu_history[-1]}",
                                "Previous": f"{hu_history[0]}",
                            }
                        })

            pa_interval = min(
                self.__pa_threshold_interval,
                len(self.__pa_data_history),
            )

            pa_history = self.__pa_data_history[-pa_interval:0]

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
                        changes.append({
                            "Pressure": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{pa_history[-1] - pa_history[0]}",
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
                        changes.append({
                            "Pressure": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{pa_history[-1] - pa_history[0]}",
                                "New": f"{pa_history[-1]}",
                                "Previous": f"{pa_history[0]}",
                            }
                        })

            rf_history = self.__rf_data_history[-2:0]

            if rf_history[0] != rf_history[1]:
                ts = "Dry" if rf_history[1] == 0 else "Wet"

                changes.append({
                    "Rainfall": {
                        "Change": ts,
                    }
                })

            wd_history = self.__wd_data_history[-2:0]

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

            ws_history = self.__ws_data_history[-ws_interval:0]

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
                        changes.append({
                            "WindSpeed": {
                                "Reason": WeatherTracker.NotifyReason.POSITIVE,
                                "Change": f"{ws_history[-1] - ws_history[0]}",
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
                        changes.append({
                            "WindSpeed": {
                                "Reason": WeatherTracker.NotifyReason.NEGATIVE,
                                "Change": f"{ws_history[-1] - ws_history[0]}",
                                "New": f"{ws_history[-1]}",
                                "Previous": f"{ws_history[0]}",
                            }
                        })

            embeds = []

            if len(changes) > 0:
                for change in changes:
                    if change.key() == "AirTemp":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Air Temperature Change Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Change",
                                        f"{change['Change']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "New",
                                        f"{change['New']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Previous",
                                        f"{change['Previous']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

                    elif change.key() == "TrackTemp":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Track Temperature Change Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Change",
                                        f"{change['Change']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "New",
                                        f"{change['New']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Previous",
                                        f"{change['Previous']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

                    elif change.key() == "Humidity":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Humidity Change Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Change",
                                        f"{change['Change']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "New",
                                        f"{change['New']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Previous",
                                        f"{change['Previous']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

                    elif change.key() == "Pressure":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Pressure Change Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Change",
                                        f"{change['Change']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "New",
                                        f"{change['New']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Previous",
                                        f"{change['Previous']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

                    elif change.key() == "Rainfall":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Track Status Change Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Change",
                                        f"{change['Change']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

                    elif change.key() == "WindDirection":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Wind Direction Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "New",
                                        f"{change['New']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Previous",
                                        f"{change['Previous']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

                    elif change.key() == "WindSpeed":
                        embeds.append(
                            DiscordModel.Embed(
                                title="Wind Speed Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Change",
                                        f"{change['Change']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "New",
                                        f"{change['New']}"
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Previous",
                                        f"{change['Previous']}"
                                    ),
                                ],
                                timestamp=datetime.now(tz=timezone.utc),
                            )
                        )

            return embeds if len(embeds) > 0 else None


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
        self.__negotiate_at: int | None = None
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
        self.__ws.settimeout(20)

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
