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
from mimetypes import guess_type
from pathlib import Path
from random import randint
from typing import Any, Dict, List
from urllib.parse import quote, urlencode

from requests import ConnectionError, Session
from requests_toolbelt import MultipartEncoder
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

    @staticmethod
    def __random_attachment_id():
        return randint(0, 0x7fffffffffffffff)

    @staticmethod
    def __button_component_data(
        component: DiscordModel.ButtonComponent,
    ):
        data = {
            "type": component.type,
            "style": component.style,
        }

        if component.label:
            data.update(label=component.label)

        if component.emoji:
            data.update(emoji=component.emoji)

        if component.custom_id:
            data.update(custom_id=component.custom_id)

        if component.url:
            data.update(url=component.url)

        if component.disabled:
            data.update(disabled=component.disabled)

        print(data)
        return data

    @staticmethod
    def __select_menu_component_data(
        component: DiscordModel.SelectMenuComponent,
    ):
        data = {
            "type": component.type,
            "custom_id": component.custom_id,
            "options": component.options,
        }

        if component.placeholder:
            data.update(placeholder=component.placeholder)

        if component.min_values:
            data.update(min_values=component.min_values)

        if component.min_values:
            data.update(min_values=component.min_values)

        if component.disabled:
            data.update(disabled=component.disabled)

        return data

    @staticmethod
    def __text_input_component_data(
        component: DiscordModel.TextInputComponent,
    ):
        data = {
            "type": component.type,
            "custom_id": component.custom_id,
            "style": component.style,
            "label": component.label,
        }

        if component.min_length:
            data.update(min_length=component.min_length)

        if component.max_length:
            data.update(max_length=component.max_length)

        if component.required:
            data.update(required=component.required)

        if component.value:
            data.update(value=component.value)

        if component.placeholder:
            data.update(placeholder=component.placeholder)

        return data

    def post_message(
        self,
        channel_id: str,
        content: str | None = None,
        tts: bool | None = None,
        embeds: List[DiscordModel.Embed] | None = None,
        allowed_mentions: DiscordModel.AllowedMention | None = None,
        message_reference: DiscordModel.MessageReference | None = None,
        components: List[DiscordModel.ActionRowComponent] | None = None,
        sticker_ids: List[str] | None = None,
        flags: int | None = None,
        files: List[Path] | None = None,
    ):
        assert content or embeds or sticker_ids or files

        files_data = []
        payload_json_data = {}

        if tts is not None:
            payload_json_data.update(tts=tts)

        if files:
            for file in files:
                attachment_id = DiscordClient.__random_attachment_id()
                files_data.append({
                    "id": attachment_id,
                    "stream": file.open(mode="rb"),
                    "filename": str(attachment_id) + file.suffix,
                    "content_type": guess_type(
                        str(attachment_id) +
                        file.suffix
                    )[0],
                })

        if content:
            payload_json_data.update(content=content)

        if embeds:
            payload_json_data.update(embeds=[])

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
                    if isinstance(embed.image, DiscordModel.Embed.Image):
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

                    else:
                        attachment_id = DiscordClient.__random_attachment_id()
                        files_data.append({
                            "id": attachment_id,
                            "stream": embed.image.open(mode="rb"),
                            "filename": (
                                str(attachment_id) +
                                embed.image.suffix
                            ),
                            "content_type": guess_type(
                                str(attachment_id) +
                                embed.image.suffix
                            ),
                        })
                        embed_data.update(
                            image={
                                "url": f"attachment://{str(attachment_id)}" +
                                       embed.image.suffix,
                            },
                        )

                if embed.thumbnail:
                    if isinstance(
                        embed.thumbnail,
                        DiscordModel.Embed.Thumbnail,
                    ):
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

                    else:
                        attachment_id = DiscordClient.__random_attachment_id()
                        files_data.append({
                            "id": attachment_id,
                            "stream": embed.thumbnail.open(mode="rb"),
                            "filename": (
                                str(attachment_id) +
                                embed.thumbnail.suffix
                            ),
                            "content_type": guess_type(
                                str(attachment_id) +
                                embed.thumbnail.suffix
                            ),
                        })
                        embed_data.update(
                            thumbnail={
                                "url": f"attachment://{str(attachment_id)}" +
                                       embed.thumbnail.suffix,
                            },
                        )

                if embed.video:
                    if isinstance(embed.video, DiscordModel.Embed.Video):
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

                    else:
                        attachment_id = DiscordClient.__random_attachment_id()
                        files_data.append({
                            "id": attachment_id,
                            "stream": embed.video.open(mode="rb"),
                            "filename": (
                                str(attachment_id) +
                                embed.video.suffix
                            ),
                            "content_type": guess_type(
                                str(attachment_id) +
                                embed.video.suffix
                            ),
                        })
                        embed_data.update(
                            video={
                                "url": f"attachment://{str(attachment_id)}" +
                                       embed.video.suffix,
                            },
                        )

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

                payload_json_data["embeds"].append(embed_data)

        if sticker_ids:
            payload_json_data.update(sticker_ids=sticker_ids)

        if allowed_mentions:
            allowed_mentions_data = {
                "parse": allowed_mentions.parse,
                "roles": allowed_mentions.roles,
                "users": allowed_mentions.users,
                "replied_user": allowed_mentions.replied_user,
            }

            payload_json_data.update(allowed_mentions=allowed_mentions_data)

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

            payload_json_data.update(message_reference=message_reference_data)

        if components:
            components_data = []

            for component in components:
                action_comps_data = []

                for action_component in component.components:
                    if isinstance(
                        action_component,
                        DiscordModel.ButtonComponent,
                    ):
                        action_comps_data.append(
                            DiscordClient.__button_component_data(
                                action_component,
                            ),
                        )

                    elif isinstance(
                        action_component,
                        DiscordModel.SelectMenuComponent,
                    ):
                        action_comps_data.append(
                            DiscordClient.__select_menu_component_data(
                                action_component,
                            ),
                        )

                    elif isinstance(
                        action_component,
                        DiscordModel.TextInputComponent,
                    ):
                        action_comps_data.append(
                            DiscordClient.__text_input_component_data(
                                action_component,
                            ),
                        )

                    else:
                        assert False

            payload_json_data.update(components=components_data)

        if flags is not None:
            payload_json_data.update(flags=flags)

        if len(files_data) > 0:
            files_dict = {}
            payload_json_data.update(attachments=[])

            for file_data in files_data:
                files_dict.update({
                    f"files[{file_data['id']}]": (
                        file_data["filename"],
                        file_data["stream"],
                        file_data["content_type"],
                    )
                })
                payload_json_data["attachments"].append({
                    "id": file_data["id"],
                    "filename": file_data["filename"],
                })

            mp_encoder = MultipartEncoder(
                fields={
                    "payload_json": (
                        None,
                        json.dumps(payload_json_data, separators=(',', ':')),
                        "application/json",
                    ),
                    **files_dict,
                }
            )

            res = self.__post(
                f"channels/{channel_id}/messages",
                data=mp_encoder,
                headers={"Content-Type": mp_encoder.content_type},
            )

        else:
            res = self.__post(
                f"channels/{channel_id}/messages",
                json=payload_json_data,
            )

        res.raise_for_status()
        return res

    @staticmethod
    def post_webhook_message(
        webhook_id: str,
        webhook_token: str,
        content: str | None = None,
        username: str | None = None,
        avatar_url: str | None = None,
        tts: bool | None = None,
        embeds: List[DiscordModel.Embed] | None = None,
        allowed_mentions: DiscordModel.AllowedMention | None = None,
        components: List[DiscordModel.ActionRowComponent] | None = None,
        flags: int | None = None,
        files: List[Path] | None = None,
    ):
        assert content or embeds or files
        session = Session()

        files_data = []
        payload_json_data = {}

        if tts is not None:
            payload_json_data.update(tts=tts)

        if files:
            for file in files:
                attachment_id = DiscordClient.__random_attachment_id()
                files_data.append({
                    "id": attachment_id,
                    "stream": file.open(mode="rb"),
                    "filename": str(attachment_id) + file.suffix,
                    "content_type": guess_type(
                        str(attachment_id) +
                        file.suffix
                    )[0],
                })

        if content:
            payload_json_data.update(content=content)

        if username:
            payload_json_data.update(username=username)

        if avatar_url:
            payload_json_data.update(avatar_url=avatar_url)

        if embeds:
            payload_json_data.update(embeds=[])

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
                    if isinstance(embed.image, DiscordModel.Embed.Image):
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

                    else:
                        attachment_id = DiscordClient.__random_attachment_id()
                        files_data.append({
                            "id": attachment_id,
                            "stream": embed.image.open(mode="rb"),
                            "filename": (
                                str(attachment_id) +
                                embed.image.suffix
                            ),
                            "content_type": guess_type(
                                str(attachment_id) +
                                embed.image.suffix
                            ),
                        })
                        embed_data.update(
                            image={
                                "url": f"attachment://{str(attachment_id)}" +
                                       embed.image.suffix,
                            },
                        )

                if embed.thumbnail:
                    if isinstance(
                        embed.thumbnail,
                        DiscordModel.Embed.Thumbnail,
                    ):
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

                    else:
                        attachment_id = DiscordClient.__random_attachment_id()
                        files_data.append({
                            "id": attachment_id,
                            "stream": embed.thumbnail.open(mode="rb"),
                            "filename": (
                                str(attachment_id) +
                                embed.thumbnail.suffix
                            ),
                            "content_type": guess_type(
                                str(attachment_id) +
                                embed.thumbnail.suffix
                            ),
                        })
                        embed_data.update(
                            thumbnail={
                                "url": f"attachment://{str(attachment_id)}" +
                                       embed.thumbnail.suffix,
                            },
                        )

                if embed.video:
                    if isinstance(embed.video, DiscordModel.Embed.Video):
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

                    else:
                        attachment_id = DiscordClient.__random_attachment_id()
                        files_data.append({
                            "id": attachment_id,
                            "stream": embed.video.open(mode="rb"),
                            "filename": (
                                str(attachment_id) +
                                embed.video.suffix
                            ),
                            "content_type": guess_type(
                                str(attachment_id) +
                                embed.video.suffix
                            ),
                        })
                        embed_data.update(
                            video={
                                "url": f"attachment://{str(attachment_id)}" +
                                       embed.video.suffix,
                            },
                        )

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

                payload_json_data["embeds"].append(embed_data)

        if allowed_mentions:
            allowed_mentions_data = {
                "parse": allowed_mentions.parse,
                "roles": allowed_mentions.roles,
                "users": allowed_mentions.users,
                "replied_user": allowed_mentions.replied_user,
            }

            payload_json_data.update(allowed_mentions=allowed_mentions_data)

        if components:
            components_data = []

            for component in components:
                action_comps_data = []

                for action_component in component.components:
                    if isinstance(
                        action_component,
                        DiscordModel.ButtonComponent,
                    ):
                        action_comps_data.append(
                            DiscordClient.__button_component_data(
                                action_component,
                            ),
                        )

                    elif isinstance(
                        action_component,
                        DiscordModel.SelectMenuComponent,
                    ):
                        action_comps_data.append(
                            DiscordClient.__select_menu_component_data(
                                action_component,
                            ),
                        )

                    elif isinstance(
                        action_component,
                        DiscordModel.TextInputComponent,
                    ):
                        action_comps_data.append(
                            DiscordClient.__text_input_component_data(
                                action_component,
                            ),
                        )

                    else:
                        assert False

            payload_json_data.update(components=components_data)

        if flags is not None:
            payload_json_data.update(flags=flags)

        if len(files_data) > 0:
            files_dict = {}
            payload_json_data.update(attachments=[])

            for file_data in files_data:
                files_dict.update({
                    f"files[{file_data['id']}]": (
                        file_data["filename"],
                        file_data["stream"],
                        file_data["content_type"],
                    )
                })
                payload_json_data["attachments"].append({
                    "id": file_data["id"],
                    "filename": file_data["filename"],
                })

            mp_encoder = MultipartEncoder(
                fields={
                    "payload_json": (
                        None,
                        json.dumps(payload_json_data, separators=(',', ':')),
                        "application/json",
                    ),
                    **files_dict,
                }
            )

            res = session.post(
                "/".join((
                    DiscordClient.__rest_api_url,
                    f"v{DiscordClient.__rest_api_version}",
                    "webhooks",
                    webhook_id,
                    webhook_token,
                )),
                data=mp_encoder,
                headers={"Content-Type": mp_encoder.content_type},
            )

        else:
            res = session.post(
                "/".join((
                    DiscordClient.__rest_api_url,
                    f"v{DiscordClient.__rest_api_version}",
                    "webhooks",
                    webhook_id,
                    webhook_token,
                )),
                json=payload_json_data,
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
