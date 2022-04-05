# pyeXF1LT - Unofficial F1 live timing clients
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
from asyncio import TimeoutError
from datetime import datetime, timedelta
from pathlib import Path
from random import randint
from typing import Any, Dict, List
from urllib.parse import quote, urlencode

from aiohttp import ClientSession, ClientWebSocketResponse
from requests import Session
from websocket import (
    WebSocket,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)

from ._model import DiscordModel


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
        while True:
            if not self.__ws.connected and self.__reconnect:
                self.__connect()

            if self.__ws.connected:
                try:
                    return self.message()

                except WebSocketConnectionClosedException:
                    if not self.__reconnect:
                        raise

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


class DiscordClient:
    """Discord client
    """
    __rest_api_url = "https://discord.com/api"
    __rest_api_version = 9

    class BotAuthorization:
        def __init__(self, bot_token: str) -> None:
            self.__token = bot_token

        def __str__(self) -> str:
            return f"Bot {self.__token}"

    def __init__(
        self,
        authorization: BotAuthorization,
        session: Session | None = None,
    ):
        if session is None:
            session = Session()

        self.__authorization = authorization
        self.__session = session

    def post_message(
        self,
        channel_id: str,
        content: str | None = None,
        tts: bool | None = None,
        embeds: List[DiscordModel.Embed] | None = None,
        allowed_mentions: DiscordModel.AllowedMention | None = None,
        message_reference: DiscordModel.MessageReference | None = None,
        sticker_ids: List[str] | None = None,
        flags: int | None = None,
        files: List[Path] | None = None,
    ):
        assert content or embeds or sticker_ids or files

        json_data = {}

        if tts is not None:
            json_data.update(tts=tts)

        if content:
            json_data.update(content=content)

        if embeds:
            json_data.update(embeds=[])

            for embed in embeds:
                embed_data = {}

                if embed.title:
                    embed_data.update(title=embed.title)

                if embed.type:
                    embed_data.update(type=embed.type)

                if embed.description:
                    embed_data.update(description=embed.description)

                if embed.url:
                    embed_data.update(url=embed.url)

                if embed.timestamp:
                    embed_data.update(
                        timestamp=embed.timestamp.isoformat(),
                    )

                if embed.color:
                    embed_data.update(color=embed.color)

                if embed.footer:
                    embed_footer_data = {"text": embed.footer.text}

                    if embed.footer.icon_url:
                        embed_footer_data.update(
                            icon_url=embed.footer.icon_url,
                        )

                    if embed.footer.proxy_icon_url:
                        embed_footer_data.update(
                            proxy_icon_url=embed.footer.proxy_icon_url,
                        )

                    embed_data.update(footer=embed_footer_data)

                if embed.image:
                    embed_image_data = {"url": embed.image.url}

                    if embed.image.proxy_url:
                        embed_image_data.update(
                            proxy_url=embed.image.proxy_url,
                        )

                    if embed.image.height:
                        embed_image_data.update(height=embed.image.height)

                    if embed.image.width:
                        embed_image_data.update(width=embed.image.width)

                    embed_data.update(image=embed_image_data)

                if embed.thumbnail:
                    embed_thumbnail_data = {"url": embed.thumbnail.url}

                    if embed.thumbnail.proxy_url:
                        embed_thumbnail_data.update(
                            proxy_url=embed.thumbnail.proxy_url,
                        )

                    if embed.thumbnail.height:
                        embed_thumbnail_data.update(
                            height=embed.thumbnail.height,
                        )

                    if embed.image.width:
                        embed_thumbnail_data.update(
                            width=embed.thumbnail.width,
                        )

                    embed_data.update(thumbnail=embed_thumbnail_data)

                if embed.video:
                    embed_video_data = {"url": embed.video.url}

                    if embed.video.proxy_url:
                        embed_video_data.update(
                            proxy_url=embed.video.proxy_url,
                        )

                    if embed.video.height:
                        embed_video_data.update(height=embed.video.height)

                    if embed.video.width:
                        embed_video_data.update(width=embed.video.width)

                    embed_data.update(video=embed_video_data)

                if embed.provider:
                    embed_provider_data = {}

                    if embed.provider.name:
                        embed_provider_data.update(name=embed.provider.name)

                    if embed.provider.url:
                        embed_provider_data.update(url=embed.provider.url)

                    embed_data.update(provider=embed_provider_data)

                if embed.author:
                    embed_author_data = {"name": embed.author.name}

                    if embed.author.url:
                        embed_author_data.update(url=embed.author.url)

                    if embed.author.icon_url:
                        embed_author_data.update(
                            icon_url=embed.author.icon_url,
                        )

                    if embed.author.proxy_icon_url:
                        embed_author_data.update(
                            proxy_icon_url=embed.author.proxy_icon_url,
                        )

                    embed_data.update(author=embed_author_data)

                if embed.fields:
                    fields = []

                    for embed_field in embed.fields:
                        embed_field_data = {
                            "name": embed_field.name,
                            "value": embed_field.value,
                        }

                        if embed_field.inline is not None:
                            embed_field_data.update(inline=embed_field.inline)

                        fields.append(embed_field_data)

                    embed_data.update(fields=fields)

                json_data["embeds"].append(embed_data)

        if sticker_ids:
            json_data.update(sticker_ids=sticker_ids)

        if allowed_mentions:
            allowed_mentions_data = {
                "parse": allowed_mentions.parse,
                "roles": allowed_mentions.roles,
                "users": allowed_mentions.users,
                "replied_user": allowed_mentions.replied_user,
            }

            json_data.update(allowed_mentions=allowed_mentions_data)

        if message_reference:
            message_reference_data = {}

            if message_reference.message_id:
                message_reference_data.update(
                    message_id=message_reference.message_id,
                )

            if message_reference.channel_id:
                message_reference_data.update(
                    channel_id=message_reference.channel_id,
                )

            if message_reference.guild_id:
                message_reference_data.update(
                    guild_id=message_reference.guild_id,
                )

            if message_reference.fail_if_not_exists:
                message_reference_data.update(
                    fail_if_not_exists=message_reference.fail_if_not_exists,
                )

            json_data.update(message_reference=message_reference_data)

        if flags is not None:
            json_data.update(flags=flags)

        res = self.__post(
            f"channels/{channel_id}/messages",
            json=json_data,
        )
        res.raise_for_status()

        return res

    def __get(self, uri: str, **kwargs):
        while uri.startswith("/"):
            uri = uri[1:]

        if "headers" in kwargs:
            if "Authorization" not in kwargs["headers"]:
                kwargs["headers"]["Authorization"] = str(self.__authorization)

        else:
            kwargs.update({
                "headers": {"Authorization": str(self.__authorization)}
            })

        return self.__session.get(
            "/".join((
                DiscordClient.__rest_api_url,
                f"v{DiscordClient.__rest_api_version}",
                uri,
            )),
            **kwargs,
        )

    def __post(self, uri: str, **kwargs):
        while uri.startswith("/"):
            uri = uri[1:]

        if "headers" in kwargs:
            if "Authorization" not in kwargs["headers"]:
                kwargs["headers"]["Authorization"] = str(self.__authorization)

        else:
            kwargs.update({
                "headers": {"Authorization": str(self.__authorization)}
            })

        return self.__session.post(
            "/".join((
                DiscordClient.__rest_api_url,
                f"v{DiscordClient.__rest_api_version}",
                uri,
            )),
            **kwargs,
        )

    def __patch(self, uri: str, **kwargs):
        while uri.startswith("/"):
            uri = uri[1:]

        if "headers" in kwargs:
            if "Authorization" not in kwargs["headers"]:
                kwargs["headers"]["Authorization"] = str(self.__authorization)

        else:
            kwargs.update({
                "headers": {"Authorization": str(self.__authorization)}
            })

        return self.__session.patch(
            "/".join((
                DiscordClient.__rest_api_url,
                f"v{DiscordClient.__rest_api_version}",
                uri,
            )),
            **kwargs,
        )

    def __put(self, uri: str, **kwargs):
        while uri.startswith("/"):
            uri = uri[1:]

        if "headers" in kwargs:
            if "Authorization" not in kwargs["headers"]:
                kwargs["headers"]["Authorization"] = str(self.__authorization)

        else:
            kwargs.update({
                "headers": {"Authorization": str(self.__authorization)}
            })

        return self.__session.put(
            "/".join((
                DiscordClient.__rest_api_url,
                f"v{DiscordClient.__rest_api_version}",
                uri,
            )),
            **kwargs,
        )

    def __delete(self, uri: str, **kwargs):
        while uri.startswith("/"):
            uri = uri[1:]

        if "headers" in kwargs:
            if "Authorization" not in kwargs["headers"]:
                kwargs["headers"]["Authorization"] = str(self.__authorization)

        else:
            kwargs.update({
                "headers": {"Authorization": str(self.__authorization)}
            })

        return self.__session.delete(
            "/".join((
                DiscordClient.__rest_api_url,
                f"v{DiscordClient.__rest_api_version}",
                uri,
            )),
            **kwargs,
        )
