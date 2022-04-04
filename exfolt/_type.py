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

from enum import Enum, IntEnum


class DiscordType:
    class AllowedMention(str, Enum):
        ROLES = "roles"
        USERS = "users"
        EVERYONE = "everyone"

    class Embed(str, Enum):
        RICH = "rich"
        IMAGE = "image"
        VIDEO = "video"
        GIFV = "gifv"
        ARTICLE = "article"
        LINK = "link"

    class MessageFlag(IntEnum):
        CROSSPOSTED = 1 << 0
        IS_CROSSPOST = 1 << 1
        SUPPRESS_EMBEDS = 1 << 2
        SOURCE_MESSAGE_DELETED = 1 << 3
        URGENT = 1 << 4
        HAS_THREAD = 1 << 5
        EPHEMERAL = 1 << 6
        LOADING = 1 << 7
        FAILED_TO_MENTION_SOME_ROLES_IN_THREAD = 1 << 8
