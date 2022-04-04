from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List

from ._type import DiscordType


class Snowflake:
    def __init__(self, value: int | str) -> None:
        assert int(value) <= (1 << 64) - 1, "Value too big!"
        self.__value = int(value)

    def __str__(self):
        return str(self.__value)

    def __repr__(self) -> str:
        return "Snowflake(value={self.__value}, )"

    @property
    def __discord_epoch_timestamp_ms(self):
        return self.__value >> 22

    @property
    def __epoch_timestamp_ms(self):
        return self.__discord_epoch_timestamp_ms + 0x14AA2CAB000

    @property
    def timestamp(self):
        return datetime.fromtimestamp(self.__epoch_timestamp_ms / 1000)

    @property
    def internal_worker_id(self):
        return (self.__value & 0x3E0000) >> 17

    @property
    def internal_process_id(self):
        return (self.__value & 0x1F000) >> 12

    @property
    def increment(self):
        return self.__value & 0xFFF


class DiscordModel:
    class AllowedMention:
        def __init__(
            self,
            parse: List[DiscordType.AllowedMention],
            roles: List[str],
            users: List[str],
            replied_user: bool,
        ) -> None:
            self.parse = parse
            self.roles = roles
            self.users = users
            self.replied_user = replied_user

    class Embed:
        class Footer:
            def __init__(
                self,
                text: str,
                icon_url: str | None = None,
                proxy_icon_url: str | None = None,
            ) -> None:
                self.text = text
                self.icon_url = icon_url
                self.proxy_icon_url = proxy_icon_url

        class Image:
            def __init__(
                self,
                url: str,
                proxy_url: str | None = None,
                height: int | None = None,
                width: int | None = None,
            ) -> None:
                self.url = url
                self.proxy_url = proxy_url
                self.height = height
                self.width = width

        class Thumbnail:
            def __init__(
                self,
                url: str,
                proxy_url: str | None = None,
                height: int | None = None,
                width: int | None = None,
            ) -> None:
                self.url = url
                self.proxy_url = proxy_url
                self.height = height
                self.width = width

        class Video:
            def __init__(
                self,
                url: str,
                proxy_url: str | None = None,
                height: int | None = None,
                width: int | None = None,
            ) -> None:
                self.url = url
                self.proxy_url = proxy_url
                self.height = height
                self.width = width

        class Provider:
            def __init__(
                self,
                name: str | None = None,
                url: str | None = None,
            ) -> None:
                self.name = name
                self.url = url

        class Author:
            def __init__(
                self,
                name: str,
                url: str | None = None,
                icon_url: str | None = None,
                proxy_icon_url: str | None = None,
            ) -> None:
                self.name = name
                self.url = url
                self.icon_url = icon_url
                self.proxy_icon_url = proxy_icon_url

        class Field:
            def __init__(
                self,
                name: str,
                value: str,
                inline: bool | None = None,
            ) -> None:
                self.name = name
                self.value = value
                self.inline = inline

        def __init__(
            self,
            title: str | None = None,
            type: DiscordType.Embed | None = None,
            description: str | None = None,
            url: str | None = None,
            timestamp: datetime | None = None,
            color: int | None = None,
            footer: DiscordModel.Embed.Footer | None = None,
            image: DiscordModel.Embed.Image | Path | None = None,
            thumbnail: DiscordModel.Embed.Thumbnail | Path | None = None,
            video: DiscordModel.Embed.Video | Path | None = None,
            provider: DiscordModel.Embed.Provider | None = None,
            author: DiscordModel.Embed.Author | None = None,
            fields: List[DiscordModel.Embed.Field] | None = None,
        ) -> None:
            self.title = title
            self.type = type
            self.description = description
            self.url = url
            self.timestamp = timestamp
            self.color = color
            self.footer = footer
            self.image = image
            self.thumbnail = thumbnail
            self.video = video
            self.provider = provider
            self.author = author
            self.fields = fields

    class MessageReference:
        def __init__(
            self,
            message_id: str | None = None,
            channel_id: str | None = None,
            guild_id: str | None = None,
            fail_if_not_exists: bool | None = None,
        ) -> None:
            self.message_id = message_id
            self.channel_id = channel_id
            self.guild_id = guild_id
            self.fail_if_not_exists = fail_if_not_exists
