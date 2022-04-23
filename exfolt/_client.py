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

import dateutil.parser
import json
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from random import randint
from typing import Any, Dict, List, Literal, Union
from urllib.parse import quote, urlencode

from requests import ConnectionError, Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)

from ._model import DiscordModel
from ._type import FlagStatus, TimingDataStatus


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

            rf_history = self.__rf_data_history[-2:]

            if rf_history[0] != rf_history[1]:
                ts = "Dry" if rf_history[1] == 0 else "Wet"

                changes.append({
                    "Rainfall": {
                        "Change": ts,
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
                    if "AirTemp" in change.keys():
                        change = change["AirTemp"]
                        self.__last_at_notify_at = datetime.now()
                        self.__last_at_notify_reason = change["Reason"]

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

                    elif "TrackTemp" in change.keys():
                        change = change["TrackTemp"]
                        self.__last_tt_notify_at = datetime.now()
                        self.__last_tt_notify_reason = change["Reason"]

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

                    elif "Humidity" in change.keys():
                        change = change["Humidity"]
                        self.__last_hu_notify_at = datetime.now()
                        self.__last_hu_notify_reason = change["Reason"]

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

                    elif "Pressure" in change.keys():
                        change = change["Pressure"]
                        self.__last_pa_notify_at = datetime.now()
                        self.__last_pa_notify_reason = change["Reason"]

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

                    elif "Rainfall" in change.keys():
                        change = change["Rainfall"]
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

                    elif "WindDirection" in change.keys():
                        change = change["WindDirection"]
                        self.__last_wd_notify_at = datetime.now()

                        embeds.append(
                            DiscordModel.Embed(
                                title="Wind Direction Change Information",
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

                    elif "WindSpeed" in change.keys():
                        change = change["WindSpeed"]
                        self.__last_ws_notify_at = datetime.now()
                        self.__last_ws_notify_reason = change["Reason"]

                        embeds.append(
                            DiscordModel.Embed(
                                title="Wind Speed Change Information",
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


TimingData = Dict[
    Literal["Lines"],
    Dict[
        str,
        Dict[
            Literal["Sectors"],
            Dict[
                str,
                Dict[
                    Literal["Segments"],
                    Dict[
                        str,
                        Dict[
                            Literal["Status"],
                            int,
                        ],
                    ],
                ],
            ],
        ],
    ],
]


RaceControlMessageData = Dict[str, Union[str, int]]


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

            if "DriverList" in self.__old_data:
                self.__driver_data.update(
                    self.__old_data["DriverList"],
                )

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
                                self.__driver_data.update({drv_num: drv_data})

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

    def __driver_string(self, number: str) -> str:
        if number not in self.__driver_data:
            return number

        fn = self.__driver_data[number]["FirstName"]
        ln = self.__driver_data[number]["LastName"]
        return f"{fn} {ln} ({number})"

    def __driver_headshot_url(self, number: str) -> str | None:
        if number not in self.__driver_data:
            return

        return (
            self.__driver_data[number]["HeadshotUrl"]
            if "HeadshotUrl" in self.__driver_data[number]
            else None
        )

    def timing_data_embed(
        self,
        msg_data: TimingData,
        msg_dt: str,
    ):
        if "Lines" in msg_data and len(msg_data["Lines"]) == 1:
            for drv_num, drv_data in msg_data["Lines"].items():
                if "Sectors" in drv_data and len(drv_data["Sectors"]) == 1:
                    for sector_num, sector_data in drv_data["Sectors"].items():
                        if (
                            "Segments" in sector_data and
                            len(sector_data["Segments"]) == 1
                        ):
                            for (
                                segment_num,
                                segment_data,
                            ) in sector_data["Segments"].items():
                                if (
                                    "Status" in segment_data and
                                    segment_data["Status"] in [
                                        TimingDataStatus.PURPLE,
                                        TimingDataStatus.STOPPED,
                                        TimingDataStatus.PITTED,
                                        TimingDataStatus.PIT_ISSUE,
                                    ]
                                ):
                                    color = None

                                    if segment_data["Status"] == \
                                            TimingDataStatus.PURPLE:
                                        color = 0xA020F0

                                    elif segment_data["Status"] in [
                                        TimingDataStatus.STOPPED,
                                        TimingDataStatus.PIT_ISSUE,
                                    ]:
                                        color = 0xFFFF00

                                    drv_hs_url = \
                                        self.__driver_headshot_url(drv_num)

                                    return DiscordModel.Embed(
                                        title="Timing Data",
                                        author=DiscordModel.Embed.Author(
                                            self.__driver_string(drv_num),
                                            icon_url=drv_hs_url,
                                        ),
                                        fields=[
                                            DiscordModel.Embed.Field(
                                                "Sector",
                                                str(int(sector_num) + 1),
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Segment",
                                                str(int(segment_num) + 1),
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Status",
                                                (
                                                    "Purple"
                                                    if segment_data["Status"]
                                                    == TimingDataStatus.PURPLE
                                                    else "Pitted"
                                                    if segment_data["Status"]
                                                    == TimingDataStatus.PITTED
                                                    else "Pit issues"
                                                    if segment_data["Status"]
                                                    ==
                                                    TimingDataStatus.PIT_ISSUE
                                                    else "Stopped"
                                                )
                                            ),
                                        ],
                                        color=color,
                                        timestamp=dateutil.parser.parse(
                                            msg_dt,
                                        ),
                                    )

    def race_control_message_embed(
        self,
        msg_data: Dict[
            Literal["Messages"],
            Dict[str, RaceControlMessageData] | List[RaceControlMessageData],
        ],
        msg_dt: str,
    ):
        if isinstance(msg_data["Messages"], list):
            msg_data = msg_data["Messages"][0]

        else:
            msg_data = list(msg_data["Messages"].values())[0]

        description = None

        if msg_data["Category"] == "Flag":
            flag_status: FlagStatus = msg_data["Flag"]

            if flag_status == FlagStatus.BLUE:
                color = 0x0000FF  # Blue
                description = "<:blue:964569378999898143>"

            elif flag_status == FlagStatus.CHEQUERED:
                color = 0x000000  # Black
                description = "<:chequered:964569378769235990>"

            elif flag_status == FlagStatus.CLEAR:
                color = 0xFFFFFF  # White
                description = "<:green:964569379205414932>"

            elif flag_status == FlagStatus.GREEN:
                description = "<:green:964569379205414932>"
                color = 0x00FF00  # Green

            elif flag_status == FlagStatus.YELLOW:
                description = "<:yellow:964569379037671484>"
                color = 0xFFFF00  # Yellow

            elif flag_status == FlagStatus.DOUBLE_YELLOW:
                description = "".join((
                    "<:yellow:964569379037671484>",
                    "<:yellow:964569379037671484>",
                ))
                color = 0xFFA500  # Orange

            elif flag_status == FlagStatus.RED:
                description = "<:red:964569379234779136>"
                color = 0xFF0000  # Red

            else:
                raise ValueError(f"Unexpected flag status '{flag_status}'!")

        else:
            color = 0XA6EF1F  # Light Green

        fields = [
            DiscordModel.Embed.Field("Message", msg_data["Message"]),
            DiscordModel.Embed.Field("Category", msg_data["Category"]),
        ]

        if "Flag" in msg_data:
            fields.append(DiscordModel.Embed.Field("Flag", msg_data["Flag"]))

        if "Scope" in msg_data:
            fields.append(DiscordModel.Embed.Field("Scope", msg_data["Scope"]))

        if "RacingNumber" in msg_data:
            author = DiscordModel.Embed.Author(
                self.__driver_string(msg_data["RacingNumber"]),
                icon_url=self.__driver_headshot_url(msg_data["RacingNumber"]),
            )

        else:
            author = None

        if "Sector" in msg_data:
            fields.append(
                DiscordModel.Embed.Field(
                    "Track Sector",
                    msg_data["Sector"],
                ),
            )

        if "Lap" in msg_data:
            fields.append(
                DiscordModel.Embed.Field(
                    "Lap Number",
                    str(msg_data["Lap"]),
                ),
            )

        if "Status" in msg_data and msg_data["Category"] == "Drs":
            fields.append(
                DiscordModel.Embed.Field(
                    "DRS Status",
                    msg_data["Status"],
                ),
            )

        return DiscordModel.Embed(
            title="Race Control Message",
            author=author,
            description=description,
            fields=fields,
            color=color,
            timestamp=dateutil.parser.parse(msg_dt),
        )
