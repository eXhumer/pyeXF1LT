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
