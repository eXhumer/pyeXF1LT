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

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Dict, List

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

    class Emoji:
        def __init__(
            self,
            id: str | None = None,
            name: str | None = None,
            roles: List[str] | None = None,
            user: DiscordModel.User | None = None,
            require_colons: bool | None = None,
            managed: bool | None = None,
            animated: bool | None = None,
            available: bool | None = None,
        ):
            self.id = id
            self.name = name
            self.roles = roles
            self.user = user
            self.require_colons = require_colons
            self.managed = managed
            self.animated = animated
            self.available = available

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

    class ActionRowComponent:
        def __init__(
            self,
            components: List[
                DiscordModel.ButtonComponent |
                DiscordModel.SelectMenuComponent |
                DiscordModel.TextInputComponent,
            ],
        ):
            self.type = DiscordType.Component.ACTION_ROW
            self.components = components

    class ButtonComponent:
        def __init__(
            self,
            style: DiscordType.ButtonStyle,
            label: str | None = None,
            emoji: Dict[str, bool | str] | None = None,
            custom_id: str | None = None,
            url: str | None = None,
            disabled: bool | None = None,
        ):
            self.type = DiscordType.Component.BUTTON
            self.style = style
            self.label = label
            self.emoji = emoji
            self.custom_id = custom_id
            self.url = url
            self.disabled = disabled

    class SelectMenuComponent:
        class Option:
            def __init__(
                self,
                label: str,
                value: str,
                description: str | None = None,
                emoji: Dict[str, bool | str] | None = None,
                default: bool | None = None,
            ) -> None:
                self.label = label
                self.value = value
                self.description = description
                self.emoji = emoji
                self.default = default

        def __init__(
            self,
            custom_id: str,
            options: List[DiscordModel.SelectMenuComponent.Option],
            placeholder: str | None = None,
            min_values: int | None = None,
            max_values: int | None = None,
            disabled: bool | None = None,
        ) -> None:
            self.type = DiscordType.Component.SELECT_MENU
            self.custom_id = custom_id
            self.options = options
            self.placeholder = placeholder
            self.min_values = min_values
            self.max_values = max_values
            self.disabled = disabled

    class TextInputComponent:
        def __init__(
            self,
            custom_id: str,
            style: DiscordType.TextInputStyle,
            label: str,
            min_length: int | None = None,
            max_length: int | None = None,
            required: bool | None = None,
            value: str | None = None,
            placeholder: str | None = None,
        ) -> None:
            self.type = DiscordType.Component.TEXT_INPUT
            self.custom_id = custom_id
            self.style = style
            self.label = label
            self.min_length = min_length
            self.max_length = max_length
            self.required = required
            self.value = value
            self.placeholder = placeholder

    class User:
        def __init__(
            self,
            id: str,
            username: str,
            discriminator: str,
            avatar: str | None = None,
            bot: bool | None = None,
            system: bool | None = None,
            mfa_enabled: bool | None = None,
            banner: str | None = None,
            accent_color: int | None = None,
            locale: str | None = None,
            verified: bool | None = None,
            email: str | None = None,
            flags: int | None = None,
            premium_type: int | None = None,
            public_flags: int | None = None,

        ) -> None:
            self.id = id
            self.username = username
            self.discriminator = discriminator
            self.avatar = avatar
            self.bot = bot
            self.system = system
            self.mfa_enabled = mfa_enabled
            self.banner = banner
            self.accent_color = accent_color
            self.locale = locale
            self.verified = verified
            self.email = email
            self.flags = flags
            self.premium_type = premium_type
            self.public_flags = public_flags
