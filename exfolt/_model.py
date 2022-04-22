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
        return f"Snowflake(value={self.__value}, timestamp={self.timestamp}" +\
            f", internal_process_id={self.internal_process_id}, " +\
            f"internal_worker_id={self.internal_worker_id}, " +\
            f"increment={self.increment})"

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

        def __repr__(self) -> str:
            return f"DiscordModel.AllowedMention(parse={self.parse}, " + \
                f"roles={self.roles}, users={self.users}, " + \
                f"replied_user={self.replied_user})"

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

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Footer(text={self.text}, " + \
                    f"icon_url={self.icon_url}, " + \
                    f"proxy_icon_url={self.proxy_icon_url})"

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

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Image(url={self.url}, " + \
                    f"proxy_url={self.proxy_url}, height={self.height}, " + \
                    f"width={self.width})"

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

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Thumbnail(url={self.url}, " + \
                    f"proxy_url={self.proxy_url}, height={self.height}, " + \
                    f"width={self.width})"

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

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Video(url={self.url}, " + \
                    f"proxy_url={self.proxy_url}, height={self.height}, " + \
                    f"width={self.width})"

        class Provider:
            def __init__(
                self,
                name: str | None = None,
                url: str | None = None,
            ) -> None:
                self.name = name
                self.url = url

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Provider(name={self.name}, " + \
                    f"url={self.url})"

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

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Author(name={self.name}, " + \
                    f"url={self.url}, icon_url={self.icon_url}, " + \
                    f"proxy_icon_url={self.proxy_icon_url})"

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

            def __repr__(self) -> str:
                return f"DiscordModel.Embed.Field(name={self.name}, " + \
                    f"value={self.value}, inline={self.inline})"

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

        def __repr__(self) -> str:
            return f"DiscordModel.Embed(title={self.title}, " + \
                f"type={self.type}, description={self.description}, " + \
                f"url={self.url}, timestamp={self.timestamp}, " + \
                f"color={self.color}, footer={self.footer}, " + \
                f"image={self.image}, thumbnail={self.thumbnail}, " + \
                f"video={self.video}, provider={self.provider}, " + \
                f"author={self.author}, fields={self.fields})"

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

        def __repr__(self) -> str:
            return f"DiscordModel.Emoji(id={self.id}, name={self.name}, " + \
                f"roles={self.roles}, user={self.user}, " + \
                f"require_colons={self.require_colons}, " + \
                f"managed={self.managed}, animated={self.animated}, " + \
                f"available={self.available})"

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

        def __repr__(self) -> str:
            return "DiscordModel.MessageReference(message_id=" + \
                f"{self.message_id}, channel_id={self.channel_id}, " + \
                f"guild_id={self.guild_id}, " + \
                f"fail_if_not_exists={self.fail_if_not_exists})"

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

        def __repr__(self) -> str:
            return "DiscordModel.ActionRowComponent(" + \
                f"type={self.type}, " + \
                f"components={self.components}" + \
                ")"

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

        def __repr__(self) -> str:
            return "DiscordModel.ButtonComponent(" + \
                f"type={self.type}, " + \
                f"style={self.style}, " + \
                f"label={self.label}, " + \
                f"emoji={self.emoji}, " + \
                f"custom_id={self.custom_id}, " + \
                f"url={self.url}, " + \
                f"disabled={self.disabled}" + \
                ")"

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

            def __repr__(self) -> str:
                return "DiscordModel.SelectMenuComponent.Option(" + \
                    f"label={self.label}, " + \
                    f"value={self.value}, " + \
                    f"description={self.description}, " + \
                    f"emoji={self.emoji}, " + \
                    f"default={self.default}" + \
                    ")"

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

        def __repr__(self) -> str:
            return "DiscordModel.SelectMenuComponent(" + \
                f"type={self.type}, " + \
                f"custom_id={self.custom_id}, " + \
                f"options={self.options}, " + \
                f"placeholder={self.placeholder}, " + \
                f"min_values={self.min_values}, " + \
                f"max_values={self.max_values}, " + \
                f"disabled={self.disabled}" + \
                ")"

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

        def __repr__(self) -> str:
            return "DiscordModel.TextInputComponent(" + \
                f"type={self.type}, " + \
                f"custom_id={self.custom_id}, " + \
                f"style={self.style}, " + \
                f"label={self.label}, " + \
                f"min_length={self.min_length}, " + \
                f"max_length={self.max_length}, " + \
                f"required={self.required}, " + \
                f"value={self.value}, " + \
                f"placeholder={self.placeholder}" + \
                ")"

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

        def __repr__(self) -> str:
            return "DiscordModel.User(" + \
                f"id={self.id}, " + \
                f"username={self.username}, " + \
                f"discriminator={self.discriminator}, " + \
                f"avatar={self.avatar}, " + \
                f"bot={self.bot}, " + \
                f"system={self.system}, " + \
                f"mfa_enabled={self.mfa_enabled}, " + \
                f"banner={self.banner}, " + \
                f"accent_color={self.accent_color}, " + \
                f"locale={self.locale}, " + \
                f"verified={self.verified}, " + \
                f"email={self.email}, " + \
                f"flags={self.flags}, " + \
                f"premium_type={self.premium_type}, " + \
                f"public_flags={self.public_flags})"
