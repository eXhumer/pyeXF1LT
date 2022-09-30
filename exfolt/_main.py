# eXF1LT - Unofficial F1 live timing client
# Copyright (C) 2022  eXhumer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 of the
# License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations
from argparse import ArgumentParser
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from json import loads
from logging import DEBUG, FileHandler, Formatter, getLogger, INFO, StreamHandler
from os import environ
from pathlib import Path
from queue import Queue
from pkg_resources import require
from typing import Callable, List, NotRequired, Tuple, TypedDict

from dotenv import dotenv_values
from requests import Response

from ._client import F1ArchiveClient, F1LiveClient, F1LiveTimingClient
from ._type import ArchiveStatus, AudioStream, ContentStream, StreamingTopic
from ._utils import decompress_zlib_data, datetime_parser

try:
    from exdc import DiscordBotAuthorization, DiscordClient
    from exdc.type import Embed, EmbedField

    exdc_available = True

    def __archive_status_embed(status: ArchiveStatus, timestamp: datetime):
        return Embed(
            title="Archive Status",
            fields=[EmbedField("Status", status["Status"])],
            timestamp=timestamp,
        )

    def __audio_stream_embed(stream: AudioStream, session_path: str, timestamp: datetime):
        archive_url = f"{F1ArchiveClient.static_url}/{session_path}{stream['Path']}"

        return Embed(
            title="Audio Stream",
            fields=[
                EmbedField("Name", stream["Name"]),
                EmbedField("Language", stream["Language"]),
                EmbedField("Archive Link", archive_url),
                EmbedField("Live Link", stream["Uri"]),
            ],
            timestamp=timestamp,
        )

    def __content_stream_embed(stream: ContentStream, session_path: str, timestamp: datetime):
        if "Path" in stream:
            assert session_path is not None
            archive_url = f"{F1ArchiveClient.static_url}/{session_path}{stream['Path']}"

        else:
            archive_url = None

        fields = [
            EmbedField("Type", stream["Type"]),
            EmbedField("Name", stream["Name"]),
            EmbedField("Language", stream["Language"]),
            EmbedField("Live Link", stream["Uri"]),
        ]

        if archive_url is not None:
            fields.append(EmbedField("Archive Link", archive_url))

        return Embed(
            title="Content Stream",
            fields=fields,
            timestamp=timestamp,
        )

    def __discord_env(env_path: Path):
        if env_path.is_file():
            env = dotenv_values(dotenv_path=env_path)
            assert "BLACK_FLAG_EMOJI" in env
            assert "BLACK_ORANGE_FLAG_EMOJI" in env
            assert "BLACK_WHITE_FLAG_EMOJI" in env
            assert "BLUE_FLAG_EMOJI" in env
            assert "CHEQUERED_FLAG_EMOJI" in env
            assert "GREEN_FLAG_EMOJI" in env
            assert "HARD_TYRE_EMOJI" in env
            assert "INTER_TYRE_EMOJI" in env
            assert "MEDIUM_TYRE_EMOJI" in env
            assert "RED_FLAG_EMOJI" in env
            assert "SAFETY_CAR_EMOJI" in env
            assert "SOFT_TYRE_EMOJI" in env
            assert "UNKNOWN_TYRE_EMOJI" in env
            assert "VIRTUAL_SAFETY_CAR_EMOJI" in env
            assert "WET_TYRE_EMOJI" in env
            assert "YELLOW_FLAG_EMOJI" in env

            assert ("BOT_TOKEN" in environ and "CHANNEL_ID" in environ) or \
                ("WEBHOOK_ID" in environ and "WEBHOOK_TOKEN" in environ), \
                "Missing required messaging ID/token!"

            discord_env: __DiscordEnv = {
                "BLACK_FLAG_EMOJI": env["BLACK_FLAG_EMOJI"],
                "BLACK_ORANGE_FLAG_EMOJI": env["BLACK_ORANGE_FLAG_EMOJI"],
                "BLACK_WHITE_FLAG_EMOJI": env["BLACK_WHITE_FLAG_EMOJI"],
                "BLUE_FLAG_EMOJI": env["BLUE_FLAG_EMOJI"],
                "CHEQUERED_FLAG_EMOJI": env["CHEQUERED_FLAG_EMOJI"],
                "GREEN_FLAG_EMOJI": env["GREEN_FLAG_EMOJI"],
                "HARD_TYRE_EMOJI": env["HARD_TYRE_EMOJI"],
                "INTER_TYRE_EMOJI": env["INTER_TYRE_EMOJI"],
                "MEDIUM_TYRE_EMOJI": env["MEDIUM_TYRE_EMOJI"],
                "RED_FLAG_EMOJI": env["RED_FLAG_EMOJI"],
                "SAFETY_CAR_EMOJI": env["SAFETY_CAR_EMOJI"],
                "SOFT_TYRE_EMOJI": env["SOFT_TYRE_EMOJI"],
                "UNKNOWN_TYRE_EMOJI": env["UNKNOWN_TYRE_EMOJI"],
                "VIRTUAL_SAFETY_CAR_EMOJI": env["VIRTUAL_SAFETY_CAR_EMOJI"],
                "WET_TYRE_EMOJI": env["WET_TYRE_EMOJI"],
                "YELLOW_FLAG_EMOJI": env["YELLOW_FLAG_EMOJI"],
            }

            if "BOT_TOKEN" in env and "CHANNEL_ID" in env:
                discord_env |= {
                    "BOT_TOKEN": env["BOT_TOKEN"],
                    "CHANNEL_ID": env["CHANNEL_ID"],
                }

            if "WEBHOOK_TOKEN" in env and "WEBHOOK_ID" in env:
                discord_env |= {
                    "WEBHOOK_ID": env["WEBHOOK_ID"],
                    "WEBHOOK_TOKEN": env["WEBHOOK_TOKEN"],
                }

        else:
            assert "EXFOLT_BLACK_FLAG_EMOJI" in environ
            assert "EXFOLT_BLACK_ORANGE_FLAG_EMOJI" in environ
            assert "EXFOLT_BLACK_WHITE_FLAG_EMOJI" in environ
            assert "EXFOLT_BLUE_FLAG_EMOJI" in environ
            assert "EXFOLT_CHEQUERED_FLAG_EMOJI" in environ
            assert "EXFOLT_GREEN_FLAG_EMOJI" in environ
            assert "EXFOLT_HARD_TYRE_EMOJI" in environ
            assert "EXFOLT_INTER_TYRE_EMOJI" in environ
            assert "EXFOLT_MEDIUM_TYRE_EMOJI" in environ
            assert "EXFOLT_RED_FLAG_EMOJI" in environ
            assert "EXFOLT_SAFETY_CAR_EMOJI" in environ
            assert "EXFOLT_SOFT_TYRE_EMOJI" in environ
            assert "EXFOLT_UNKNOWN_TYRE_EMOJI" in environ
            assert "EXFOLT_VIRTUAL_SAFETY_CAR_EMOJI" in environ
            assert "EXFOLT_WET_TYRE_EMOJI" in environ
            assert "EXFOLT_YELLOW_FLAG_EMOJI" in environ

            assert ("EXFOLT_BOT_TOKEN" in environ and "EXFOLT_CHANNEL_ID" in environ) or \
                ("EXFOLT_WEBHOOK_ID" in environ and "EXFOLT_WEBHOOK_TOKEN" in environ), \
                "Missing required messaging ID/token!"

            discord_env: __DiscordEnv = {
                "BLACK_FLAG_EMOJI": environ["EXFOLT_BLACK_FLAG_EMOJI"],
                "BLACK_ORANGE_FLAG_EMOJI": environ["EXFOLT_BLACK_ORANGE_FLAG_EMOJI"],
                "BLACK_WHITE_FLAG_EMOJI": environ["EXFOLT_BLACK_WHITE_FLAG_EMOJI"],
                "BLUE_FLAG_EMOJI": environ["EXFOLT_BLUE_FLAG_EMOJI"],
                "CHEQUERED_FLAG_EMOJI": environ["EXFOLT_CHEQUERED_FLAG_EMOJI"],
                "GREEN_FLAG_EMOJI": environ["EXFOLT_GREEN_FLAG_EMOJI"],
                "HARD_TYRE_EMOJI": environ["EXFOLT_HARD_TYRE_EMOJI"],
                "INTER_TYRE_EMOJI": environ["EXFOLT_INTER_TYRE_EMOJI"],
                "MEDIUM_TYRE_EMOJI": environ["EXFOLT_MEDIUM_TYRE_EMOJI"],
                "RED_FLAG_EMOJI": environ["EXFOLT_RED_FLAG_EMOJI"],
                "SAFETY_CAR_EMOJI": environ["EXFOLT_SAFETY_CAR_EMOJI"],
                "SOFT_TYRE_EMOJI": environ["EXFOLT_SOFT_TYRE_EMOJI"],
                "UNKNOWN_TYRE_EMOJI": environ["EXFOLT_UNKNOWN_TYRE_EMOJI"],
                "VIRTUAL_SAFETY_CAR_EMOJI": environ["EXFOLT_VIRTUAL_SAFETY_CAR_EMOJI"],
                "WET_TYRE_EMOJI": environ["EXFOLT_WET_TYRE_EMOJI"],
                "YELLOW_FLAG_EMOJI": environ["EXFOLT_YELLOW_FLAG_EMOJI"],
            }

            if "EXFOLT_BOT_TOKEN" in environ and "EXFOLT_CHANNEL_ID" in environ:
                discord_env |= {
                    "BOT_TOKEN": environ["EXFOLT_BOT_TOKEN"],
                    "CHANNEL_ID": environ["EXFOLT_CHANNEL_ID"],
                }

            if "EXFOLT_WEBHOOK_TOKEN" in environ and "EXFOLT_WEBHOOK_ID" in environ:
                discord_env |= {
                    "WEBHOOK_ID": environ["EXFOLT_WEBHOOK_ID"],
                    "WEBHOOK_TOKEN": environ["EXFOLT_WEBHOOK_TOKEN"],
                }

        return discord_env

    def __message_embeds(env: __DiscordEnv, embeds: List[Embed]):
        if "WEBHOOK_ID" in env and "WEBHOOK_TOKEN" in env:
            webhook = DiscordClient.post_webhook_message(env["WEBHOOK_ID"], env["WEBHOOK_TOKEN"],
                                                         embeds=embeds)

        else:
            webhook = None

        if "BOT_TOKEN" in env and "CHANNEL_ID" in env:
            channel = DiscordClient(DiscordBotAuthorization(env["BOT_TOKEN"])).\
                post_message(env["CHANNEL_ID"], embeds=embeds)

        else:
            channel = None

        return webhook, channel

except ImportError:
    exdc_available = False

__logo__ = """
     _______  __   __  _______  ____  ___    _______
    |       ||  |_|  ||       ||    ||   |  |       |
    |    ___||       ||    ___| |   ||   |  |_     _|
    |   |___ |       ||   |___  |   ||   |    |   |
    |    ___| |     | |    ___| |   ||   |___ |   |
    |   |___ |   _   ||   |     |   ||       ||   |
    |_______||__| |__||___|     |___||_______||___|
"""
__license__ = """
    eXF1LT - Unofficial F1 live timing client
    Copyright (C) 2022  eXhumer

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, version 3 of the
    License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
__project_url__ = "https://github.com/eXhumer/pyeXF1LT"
__version__ = require(__package__)[0].version


class __DiscordEnv(TypedDict):
    BLACK_FLAG_EMOJI: str
    BLACK_ORANGE_FLAG_EMOJI: str
    BLACK_WHITE_FLAG_EMOJI: str
    BLUE_FLAG_EMOJI: str
    BOT_TOKEN: NotRequired[str]
    CHANNEL_ID: NotRequired[str]
    CHEQUERED_FLAG_EMOJI: str
    GREEN_FLAG_EMOJI: str
    HARD_TYRE_EMOJI: str
    INTER_TYRE_EMOJI: str
    MEDIUM_TYRE_EMOJI: str
    RED_FLAG_EMOJI: str
    SAFETY_CAR_EMOJI: str
    SOFT_TYRE_EMOJI: str
    UNKNOWN_TYRE_EMOJI: str
    VIRTUAL_SAFETY_CAR_EMOJI: str
    WEBHOOK_ID: NotRequired[str]
    WEBHOOK_TOKEN: NotRequired[str]
    WET_TYRE_EMOJI: str
    YELLOW_FLAG_EMOJI: str


class _ProgramAction(StrEnum):
    ARCHIVED_MESSAGE_LOGGER = "archived-message-logger"
    LIST_ARCHIVED_MEETINGS = "list-archived-meetings"
    LIST_ARCHIVED_SESSIONS = "list-archived-sessions"
    LIST_ARCHIVED_TOPICS = "list-archived-topics"
    LIVE_DISCORD_BOT = "live-discord-bot"
    LIVE_MESSAGE_LOGGER = "live-message-logger"


class __ProgramNamespace:
    action: _ProgramAction
    archive_last_session: bool
    archive_path: str
    archive_session_info: List[str]
    archive_status: bool
    archived_message_log_path: Path
    audio_streams: bool
    car_data: bool
    championship_prediction: bool
    content_streams: bool
    current_tyres: bool
    discord_env_path: Path
    driver_list: bool
    driver_race_info: bool
    driver_score: bool
    extrapolated_clock: bool
    heartbeat: bool
    lap_count: bool
    lap_series: bool
    license: bool
    list_archived_meetings_year: int
    list_archived_sessions_meeting: int
    list_archived_sessions_year: int
    list_archived_topics_meeting: int
    list_archived_topics_session: int
    list_archived_topics_year: int
    live_b64_zlib_decode: bool
    live_message_log_path: Path
    log_console: bool
    log_level: int
    log_path: Path
    pit_lane_time_collection: bool
    position: bool
    race_control_messages: bool
    session_data: bool
    session_info: bool
    session_status: bool
    sp_feed: bool
    team_radio: bool
    timing_app_data: bool
    timing_data_f1: bool
    timing_data: bool
    timing_stats: bool
    tla_rcm: bool
    top_three: bool
    track_status: bool
    tyre_stint_series: bool
    weather_data: bool
    weather_data_series: bool


def __message_logger(log_path: Path):
    file_handler = FileHandler(str(log_path.resolve()), mode="w")
    file_handler.setFormatter(Formatter("%(message)s"))
    logger = getLogger("message_logger")
    logger.addHandler(file_handler)
    logger.setLevel(INFO)
    return logger


def __parse_topics(args: __ProgramNamespace):
    topics: List[StreamingTopic] = []

    if args.archive_status:
        topics.append(StreamingTopic.ARCHIVE_STATUS)

    if args.audio_streams:
        topics.append(StreamingTopic.AUDIO_STREAMS)

    if args.car_data:
        topics.append(StreamingTopic.CAR_DATA_Z)

    if args.championship_prediction:
        topics.append(StreamingTopic.CHAMPIONSHIP_PREDICTION)

    if args.content_streams:
        topics.append(StreamingTopic.CONTENT_STREAMS)

    if args.current_tyres:
        topics.append(StreamingTopic.CURRENT_TYRES)

    if args.driver_list:
        topics.append(StreamingTopic.DRIVER_LIST)

    if args.driver_race_info:
        topics.append(StreamingTopic.DRIVER_RACE_INFO)

    if args.driver_score:
        topics.append(StreamingTopic.DRIVER_SCORE)

    if args.extrapolated_clock:
        topics.append(StreamingTopic.EXTRAPOLATED_CLOCK)

    if args.heartbeat:
        topics.append(StreamingTopic.HEARTBEAT)

    if args.lap_count:
        topics.append(StreamingTopic.LAP_COUNT)

    if args.lap_series:
        topics.append(StreamingTopic.LAP_SERIES)

    if args.pit_lane_time_collection:
        topics.append(StreamingTopic.PIT_LANE_TIME_COLLECTION)

    if args.position:
        topics.append(StreamingTopic.POSITION_Z)

    if args.race_control_messages:
        topics.append(StreamingTopic.RACE_CONTROL_MESSAGES)

    if args.session_data:
        topics.append(StreamingTopic.SESSION_DATA)

    if args.session_info:
        topics.append(StreamingTopic.SESSION_INFO)

    if args.session_status:
        topics.append(StreamingTopic.SESSION_STATUS)

    if args.sp_feed:
        topics.append(StreamingTopic.SP_FEED)

    if args.team_radio:
        topics.append(StreamingTopic.TEAM_RADIO)

    if args.timing_app_data:
        topics.append(StreamingTopic.TIMING_APP_DATA)

    if args.timing_data:
        topics.append(StreamingTopic.TIMING_DATA)

    if args.timing_data_f1:
        topics.append(StreamingTopic.TIMING_DATA_F1)

    if args.timing_stats:
        topics.append(StreamingTopic.TIMING_STATS)

    if args.tla_rcm:
        topics.append(StreamingTopic.TLA_RCM)

    if args.top_three:
        topics.append(StreamingTopic.TOP_THREE)

    if args.track_status:
        topics.append(StreamingTopic.TRACK_STATUS)

    if args.tyre_stint_series:
        topics.append(StreamingTopic.TYRE_STINT_SERIES)

    if args.weather_data:
        topics.append(StreamingTopic.WEATHER_DATA)

    if args.weather_data_series:
        topics.append(StreamingTopic.WEATHER_DATA_SERIES)

    return topics


def __program_args() -> __ProgramNamespace:
    parser = ArgumentParser(prog="eXF1LT", description="unofficial F1 live timing client")

    parser.add_argument("--license", "-L", action="store_true", help="prints the project license")
    parser.add_argument("--version", "-V", action="version",
                        version=f"{parser.prog} {__version__}")

    log_parser = parser.add_argument_group(title="logging options")
    log_parser.add_argument("-v", dest="log_level", action="count", help="log level", default=0)
    log_parser.add_argument("--no-console-log", dest="log_console", action="store_false",
                            help="disable stdout logging")
    log_parser.add_argument("--log-to-file", dest="log_path", type=Path, help="log file path")

    topics_parser = parser.add_argument_group(title="streaming topics")
    topics_parser.add_argument("--archive-status", action="store_true")
    topics_parser.add_argument("--audio-streams", action="store_true")
    topics_parser.add_argument("--car-data", action="store_true")
    topics_parser.add_argument("--championship-prediction", action="store_true")
    topics_parser.add_argument("--content-streams", action="store_true")
    topics_parser.add_argument("--current-tyres", action="store_true")
    topics_parser.add_argument("--driver-list", action="store_true")
    topics_parser.add_argument("--driver-race-info", action="store_true")
    topics_parser.add_argument("--driver-score", action="store_true")
    topics_parser.add_argument("--extrapolated-clock", action="store_true")
    topics_parser.add_argument("--heartbeat", action="store_true")
    topics_parser.add_argument("--lap-count", action="store_true")
    topics_parser.add_argument("--lap-series", action="store_true")
    topics_parser.add_argument("--pit-lane-time-collection", action="store_true")
    topics_parser.add_argument("--position", action="store_true")
    topics_parser.add_argument("--race-control-messages", action="store_true")
    topics_parser.add_argument("--session-data", action="store_true")
    topics_parser.add_argument("--session-info", action="store_true")
    topics_parser.add_argument("--session-status", action="store_true")
    topics_parser.add_argument("--sp-feed", action="store_true")
    topics_parser.add_argument("--team-radio", action="store_true")
    topics_parser.add_argument("--timing-app-data", action="store_true")
    topics_parser.add_argument("--timing-data", action="store_true")
    topics_parser.add_argument("--timing-data-f1", action="store_true")
    topics_parser.add_argument("--timing-stats", action="store_true")
    topics_parser.add_argument("--tla-rcm", action="store_true")
    topics_parser.add_argument("--top-three", action="store_true")
    topics_parser.add_argument("--track-status", action="store_true")
    topics_parser.add_argument("--tyre-stint-series", action="store_true")
    topics_parser.add_argument("--weather-data", action="store_true")
    topics_parser.add_argument("--weather-data-series", action="store_true")

    action_subparser = parser.add_subparsers(dest="action", title="actions", metavar="action",
                                             description="list of supported command line actions")

    archive_message_log_parser = action_subparser.add_parser(
        "archived-message-logger", help="log archived session messages to file",
        description="log archived session messages to file")
    archive_message_log_parser.add_argument(
        "archived_message_log_path", type=Path, help="file path to store logged messaged in")
    archive_message_log_parser.add_argument("--disable-b64-zlib-decode", action="store_false",
                                            dest="archived_b64_zlib_decode",
                                            help="disables decoding of base64/zlib encoded data")
    session_info_group = archive_message_log_parser.add_mutually_exclusive_group(required=True)
    session_info_group.add_argument("--by-path", help="retrieve archived session by path",
                                    type=str, dest="archive_path")
    session_info_group.add_argument(
        "--by-session-info", nargs=3, dest="archive_session_info", type=int,
        metavar=("YEAR", "MEETING", "SESSION"),
        help="retrieve archived session by year, meeting and session")
    session_info_group.add_argument("--last-session", action="store_true",
                                    dest="archive_last_session",
                                    help="retrieve last archived session")

    list_archived_meetings_parser = action_subparser.add_parser(
        "list-archived-meetings", help="display all the meetings from year index",
        description="display all the meetings from a year index")
    list_archived_meetings_parser.add_argument("list_archived_meetings_year", type=int)

    list_archived_sessions_parser = action_subparser.add_parser(
        "list-archived-sessions", help="display all the sessions from meeting index",
        description="display all the meetings from a year index")
    list_archived_sessions_parser.add_argument("list_archived_sessions_year", type=int)
    list_archived_sessions_parser.add_argument("list_archived_sessions_meeting", type=int)

    list_archived_topics_parser = action_subparser.add_parser(
        "list-archived-topics", help="display all the topics from session index",
        description="display all the topics from session index")
    list_archived_topics_parser.add_argument("list_archived_topics_year", type=int)
    list_archived_topics_parser.add_argument("list_archived_topics_meeting", type=int)
    list_archived_topics_parser.add_argument("list_archived_topics_session", type=int)

    live_message_log_parser = action_subparser.add_parser(
        "live-message-logger", help="log live session messages to file",
        description="log live session messages to file")
    live_message_log_parser.add_argument(
        "live_message_log_path", type=Path, help="file path to store logged messaged in")
    live_message_log_parser.add_argument(
        "--disable-b64-zlib-decode", action="store_false", dest="live_b64_zlib_decode",
        help="disables decoding of base64/zlib encoded data")

    if exdc_available:
        live_discord_bot_parser = action_subparser.add_parser(
            "live-discord-bot", help="output incoming messages as Discord messages",
            description="output incoming messages as Discord messages")
        live_discord_bot_parser.add_argument(
            "--env-path", "-e", type=Path, default=Path.home().joinpath(".exfolt_discord_env"),
            dest="discord_env_path", help="file to load Discord environment variables from")

    return parser.parse_args()


def __program_logger(args: __ProgramNamespace):
    formatter = Formatter("[%(asctime)s][%(name)s][%(levelname)s]\t%(message)s")
    logger = getLogger("eXF1LT")

    if args.log_level == 0:
        logger.setLevel(INFO)

    else:
        logger.setLevel(DEBUG)

    if args.log_console:
        console_handler = StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if args.log_path:
        file_handler = FileHandler(str(args.log_path.resolve()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def __program_main():
    print(__logo__)
    args = __program_args()
    logger = __program_logger(args)
    topics = __parse_topics(args)
    live_streaming_status = F1LiveClient.streaming_status()

    if args.license:
        logger.info("Printing project license")
        print(__license__)

    if args.action == _ProgramAction.ARCHIVED_MESSAGE_LOGGER:
        message_logger = __message_logger(args.archived_message_log_path)
        logger.info("F1 Live Timing archived feed logger started!")

        if args.archive_path:
            logger.info(f"Retrieving archived feed by path ({args.archive_path})!")
            archive_client = F1ArchiveClient(args.archive_path, *topics)

        elif args.archive_session_info:
            year = int(args.archive_session_info[0])
            meeting = args.archive_session_info[1]
            session = args.archive_session_info[2]

            logger.info(f"Retrieving archived feed by session information (Year: {year}, " +
                        f"Meeting: {meeting}, Session: {session})!")
            archive_client = F1ArchiveClient.get_by_session_info(year, meeting, session, *topics)

        elif args.archive_last_session:
            logger.info("Retrieving last archived session messages!")
            archive_client = F1ArchiveClient.get_last_session(*topics)

        else:
            assert False, "Unreachable as one of the above condition is required!"

        logger.info("Logging all archived session messages!")

        with archive_client:
            for message in archive_client:
                if message[0] in [StreamingTopic.CAR_DATA_Z, StreamingTopic.POSITION_Z] and \
                        args.archived_b64_zlib_decode:
                    message_logger.info([message[0],
                                        loads(decompress_zlib_data(message[1])), message[2]])

                else:
                    message_logger.info([*message])

        logger.info("F1 Live Timing archived feed logger stopped!")

    if args.action == _ProgramAction.LIST_ARCHIVED_MEETINGS:
        year = args.list_archived_meetings_year
        meetings = F1ArchiveClient.year_index(year)["Meetings"]

        logger.info(f"Season {year}")

        for i, meeting_index in enumerate(meetings):
            if i == len(meetings) - 1:
                logger.info(f"└ {i + 1} - {meeting_index['Name']}")

            else:
                logger.info(f"├ {i + 1} - {meeting_index['Name']}")

    if args.action == _ProgramAction.LIST_ARCHIVED_SESSIONS:
        year = args.list_archived_sessions_year
        meeting = args.list_archived_sessions_meeting
        meeting_index = F1ArchiveClient.meeting_index(year, meeting)[1]

        logger.info(f"{meeting_index['Name']} ({year})")

        for i, session_index in enumerate(meeting_index["Sessions"]):
            if i == len(meeting_index["Sessions"]) - 1:
                logger.info(f"└ {i + 1} - {session_index['Name']}")

            else:
                logger.info(f"├ {i + 1} - {session_index['Name']}")

    if args.action == _ProgramAction.LIST_ARCHIVED_TOPICS:
        year = args.list_archived_topics_year
        meeting = args.list_archived_topics_meeting
        session = args.list_archived_topics_session

        year_index, meeting_index, session_index = \
            F1ArchiveClient.session_index(year, meeting, session)

        if "Path" in meeting_index:
            path = meeting_index["Path"]

        else:
            meeting_sessions = meeting_index["Sessions"]
            meeting_date = meeting_sessions[-1]["StartDate"].split("T")[0]
            meeting_name = meeting_index["Name"]
            session_date = session_index["StartDate"].split("T")[0]
            session_name = session_index["Name"]

            path = "/".join([
                str(year),
                f"{meeting_date} {meeting_name}",
                f"{session_date} {session_name}",
                "",
            ]).replace(" ", "_")

        archive_client = F1ArchiveClient(path)
        topics_index = archive_client.topics_index

        logger.info(f"{meeting_index['Name']} ({year}) - {session_index['Name']}")
        total_feeds = len(topics_index["Feeds"])

        for i, topic in enumerate(sorted(topics_index["Feeds"])):
            if i == total_feeds - 1:
                logger.info(f"└ {topic}")

            else:
                logger.info(f"├ {topic}")

    if args.action == _ProgramAction.LIVE_MESSAGE_LOGGER:
        if live_streaming_status == "Offline":
            logger.warning("F1 Live Timing API Streaming Status: Offline!")

        message_logger = __message_logger(args.live_message_log_path)

        try:
            with F1LiveClient(*topics) as live_client:
                logger.info("F1 Live Timing streaming feed logger started!")

                for _, message in live_client:
                    if len(message) == 0:
                        continue

                    if "R" in message:
                        logger.info("Logged return value from 'streaming' hub!")
                        message_logger.info(message["R"])

                    if "M" in message and len(message["M"]) != 0:
                        for invokation in message["M"]:
                            assert invokation["H"] == "streaming" and invokation["M"] == "feed"
                            logger.info("Logged 'feed' invokation arguments from 'streaming' hub!")

                            if invokation["A"][0] in [
                                StreamingTopic.CAR_DATA_Z,
                                StreamingTopic.POSITION_Z,
                            ] and args.live_b64_zlib_decode:
                                message_logger.info([
                                    invokation["A"][0],
                                    loads(decompress_zlib_data(invokation["A"][1])),
                                    invokation["A"][2]])

                            else:
                                message_logger.info(invokation["A"])

        except KeyboardInterrupt:
            logger.info("F1 Live Timing streaming feed logger stopped!")

    if exdc_available and args.action == _ProgramAction.LIVE_DISCORD_BOT:
        if live_streaming_status == "Offline":
            logger.warning("F1 Live Timing API Streaming Status: Offline!")

        discord_env = __discord_env(args.discord_env_path)
        embed_queue: Queue[Embed] = Queue()
        message_embeds: Callable[[List[Embed]], Tuple[Response | None, Response | None]] = \
            lambda embeds: __message_embeds(discord_env, embeds)

        try:
            with F1LiveTimingClient(*topics) as lt_client:
                logger.info("F1 Live Timing streaming feed Discord bot started!")

                for feeds in lt_client:
                    for topic, change, timestamp in feeds:
                        if topic == StreamingTopic.ARCHIVE_STATUS:
                            embed_queue.put(
                                __archive_status_embed(change, datetime_parser(timestamp)))

                        elif topic == StreamingTopic.AUDIO_STREAMS:
                            if isinstance(change["Streams"], Mapping):
                                for key in change["Streams"].keys():
                                    embed_queue.put(
                                        __audio_stream_embed(
                                            lt_client.timing_client.audio_streams[int(key)],
                                            lt_client.timing_client.session_info["Path"],
                                            datetime_parser(timestamp),
                                        ),
                                    )

                            else:
                                for stream in change["Streams"]:
                                    embed_queue.put(
                                        __audio_stream_embed(
                                            stream,
                                            lt_client.timing_client.session_info["Path"],
                                            datetime_parser(timestamp),
                                        ),
                                    )

                        elif topic == StreamingTopic.CONTENT_STREAMS:
                            if isinstance(change["Streams"], Mapping):
                                for key in change["Streams"].keys():
                                    embed_queue.put(
                                        __content_stream_embed(
                                            lt_client.timing_client.content_streams[int(key)],
                                            lt_client.timing_client.session_info["Path"],
                                            datetime_parser(timestamp),
                                        ),
                                    )

                            else:
                                for stream in change["Streams"]:
                                    embed_queue.put(
                                        __content_stream_embed(
                                            stream,
                                            lt_client.timing_client.session_info["Path"],
                                            datetime_parser(timestamp),
                                        ),
                                    )

                    if embed_queue.qsize() > 0:
                        embeds: List[Embed] = []

                        while len(embeds) < 10 and embed_queue.qsize() > 0:
                            embeds.append(embed_queue.get())

                        message_embeds(embeds)

        except KeyboardInterrupt:
            logger.info("F1 Live Timing streaming feed Discord bot stopped!")
