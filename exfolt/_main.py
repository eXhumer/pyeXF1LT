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
from datetime import datetime, timezone
from enum import StrEnum
from json import dumps, loads
from logging import DEBUG, FileHandler, Formatter, getLogger, INFO, StreamHandler
from os import environ
from pathlib import Path
from queue import Empty, Queue
from pkg_resources import require
from typing import List, NotRequired, TypedDict

from dotenv import dotenv_values

from ._client import F1ArchiveClient, F1LiveClient, F1LiveTimingClient
from ._type import ArchiveStatus, AudioStream, ContentStream, Driver, ExtrapolatedClock, \
    FlagStatus, RaceControlMessage, SessionInfo, SessionStatus, StreamingTopic, TeamRadioCapture, \
    TrackStatus, TrackStatusStatus
from ._utils import decompress_zlib_data


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


try:
    from exdc.client import REST as DiscordRESTClient
    from exdc.exception import RESTException
    from exdc.type.channel import Embed, EmbedAuthor, EmbedField
    exdc_available = True

    def __archive_status_embed(status: ArchiveStatus, timestamp: datetime | None = None):
        return Embed(title="Archive Status",
                     fields=[EmbedField(name="Status", value=status["Status"])],
                     timestamp=__timestamp(timestamp=timestamp))

    def __audio_stream_embed(stream: AudioStream, session_path: str | None = None,
                             timestamp: datetime | None = None):

        if session_path:
            archive_url = f"{F1ArchiveClient.static_url}/{session_path}{stream['Path']}"
            archive_embed = EmbedField(name="Archive Link", value=archive_url)

        else:
            archive_embed = EmbedField(name="Archive Path", value=stream["Path"])

        return Embed(title="Audio Stream",
                     fields=[EmbedField(name="Name", value=stream["Name"]),
                             EmbedField(name="Language", value=stream["Language"]),
                             archive_embed, EmbedField(name="Live Link", value=stream["Uri"])],
                     timestamp=__timestamp(timestamp=timestamp))

    def __content_stream_embed(stream: ContentStream, session_path: str | None = None,
                               timestamp: datetime | None = None):
        if "Path" in stream:
            if session_path:
                archive_url = f"{F1ArchiveClient.static_url}/{session_path}{stream['Path']}"
                archive_embed = EmbedField(name="Archive Link", value=archive_url)

            else:
                archive_embed = EmbedField(name="Archive Path", value=stream["Path"])

        else:
            archive_embed = None

        fields = [EmbedField(name="Type", value=stream["Type"]),
                  EmbedField(name="Name", value=stream["Name"]),
                  EmbedField(name="Language", value=stream["Language"]),
                  EmbedField(name="Live Link", value=stream["Uri"])]

        if archive_url is not None:
            fields.append(archive_embed)

        return Embed(title="Content Stream", fields=fields,
                     timestamp=__timestamp(timestamp=timestamp))

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

            assert ("BOT_TOKEN" in env and "CHANNEL_ID" in env) or \
                ("WEBHOOK_ID" in env and "WEBHOOK_TOKEN" in env), \
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

    def __extrapolated_clock_embed(extrapolated_clock: ExtrapolatedClock,
                                   timestamp: datetime | None = None):
        return Embed(title="Extrapolated Clock",
                     fields=[EmbedField(name="Remaining", value=extrapolated_clock["Remaining"]),
                             EmbedField(name="Extrapolating",
                                        value=str(extrapolated_clock["Extrapolating"]))],
                     timestamp=__timestamp(timestamp=timestamp))

    def __message_embeds(env: __DiscordEnv, embeds: List[Embed]):
        if "WEBHOOK_ID" in env and "WEBHOOK_TOKEN" in env:
            try:
                webhook = DiscordRESTClient.post_webhook_message(env["WEBHOOK_ID"],
                                                                env["WEBHOOK_TOKEN"],
                                                                embeds=embeds)

            except RESTException as res_ex:
                print("req_data", res_ex.response.request.read())
                print("res_data", res_ex.response.content)
                raise res_ex

        else:
            webhook = None

        if "BOT_TOKEN" in env and "CHANNEL_ID" in env:
            channel = DiscordRESTClient.with_bot_token(env["BOT_TOKEN"]).\
                post_message(env["CHANNEL_ID"], embeds=embeds)

        else:
            channel = None

        return webhook, channel

    def __race_control_message_embed(rcm_msg: RaceControlMessage,
                                     discord_env: __DiscordEnv,
                                     timestamp: datetime | None = None,
                                     driver: Driver | None = None):
        fields = [
            EmbedField(name="Message", value=rcm_msg["Message"]),
            EmbedField(name="Category", value=rcm_msg["Category"]),
        ]

        if "RacingNumber" in rcm_msg:
            if driver:
                assert rcm_msg["RacingNumber"] == driver["RacingNumber"]
                headshot_url = None

                if "HeadshotUrl" in driver:
                    headshot_url = driver["HeadshotUrl"]

                driver_name = f"{driver['FirstName']} {driver['LastName']} " + \
                    f"({driver['RacingNumber']})"
                author = EmbedAuthor(name=driver_name, icon_url=headshot_url)

            else:
                author = None
                fields.append(EmbedField(name="Racing Number", value=rcm_msg["RacingNumber"]))

        else:
            author = None

        if "Flag" in rcm_msg:
            if rcm_msg["Flag"] == FlagStatus.BLACK:
                color = 0x000000
                description = discord_env["BLACK_FLAG_EMOJI"]

            elif rcm_msg["Flag"] == FlagStatus.BLACK_AND_ORANGE:
                color = 0xFFA500
                description = discord_env["BLACK_ORANGE_FLAG_EMOJI"]

            elif rcm_msg["Flag"] == FlagStatus.BLACK_AND_WHITE:
                color = 0xFFA500
                description = discord_env["BLACK_WHITE_FLAG_EMOJI"]

            elif rcm_msg["Flag"] == FlagStatus.BLUE:
                color = 0x0000FF
                description = discord_env["BLUE_FLAG_EMOJI"]

            elif rcm_msg["Flag"] in (FlagStatus.CHEQUERED, FlagStatus.CLEAR):
                color = 0xFFFFFF

                if rcm_msg["Flag"] == FlagStatus.CLEAR:
                    description = discord_env["GREEN_FLAG_EMOJI"]

                else:
                    description = discord_env["CHEQUERED_FLAG_EMOJI"]

            elif rcm_msg["Flag"] == FlagStatus.GREEN:
                color = 0x00FF00
                description = discord_env["GREEN_FLAG_EMOJI"]

            elif rcm_msg["Flag"] == FlagStatus.YELLOW:
                color = 0xFFFF00
                description = discord_env["YELLOW_FLAG_EMOJI"]

            elif rcm_msg["Flag"] == FlagStatus.DOUBLE_YELLOW:
                color = 0xFFA500
                description = "".join((discord_env["YELLOW_FLAG_EMOJI"],
                                       discord_env["YELLOW_FLAG_EMOJI"]))

            elif rcm_msg["Flag"] == FlagStatus.RED:
                color = 0xFF0000
                description = discord_env["RED_FLAG_EMOJI"]

            else:
                color = 0XA6EF1F
                description = None

            fields.append(EmbedField(name="Flag", value=str(rcm_msg["Flag"])))

        else:
            color = None
            description = None

        if "Status" in rcm_msg:
            if rcm_msg["Category"] == "Drs":
                fields.append(EmbedField(name="DRS Status", value=rcm_msg["Status"]))

            elif rcm_msg["Category"] == "SafetyCar":
                fields.append(EmbedField(name="Safety Car Status", value=rcm_msg["Status"]))

            else:
                fields.append(EmbedField(name="Status", value=rcm_msg["Status"]))

        if "Lap" in rcm_msg:
            fields.append(EmbedField(name="Lap", value=str(rcm_msg["Lap"])))

        if "Mode" in rcm_msg:
            fields.append(EmbedField(name="Mode", value=rcm_msg["Mode"]))

        if "Scope" in rcm_msg:
            fields.append(EmbedField(name="Scope", value=rcm_msg["Scope"]))

        if "Sector" in rcm_msg:
            fields.append(EmbedField(name="Sector", value=str(rcm_msg["Sector"])))

        return Embed(title="Race Control Message", author=author, color=color,
                     description=description, fields=fields,
                     timestamp=__timestamp(timestamp=timestamp))

    def __session_info_embed(session_info: SessionInfo, timestamp: datetime | None = None):
        return Embed(title="Session Information",
                     fields=[EmbedField(name="Official Name",
                                        value=session_info["Meeting"]["OfficialName"]),
                             EmbedField(name="Meeting Name",
                                        value=session_info["Meeting"]["Name"]),
                             EmbedField(name="Location",
                                        value=session_info["Meeting"]["Location"]),
                             EmbedField(name="Country",
                                        value=session_info["Meeting"]["Country"]["Name"]),
                             EmbedField(name="Circuit",
                                        value=session_info["Meeting"]["Circuit"]["ShortName"]),
                             EmbedField(name="Session Name", value=session_info["Name"]),
                             EmbedField(name="Start Date", value=session_info["StartDate"]),
                             EmbedField(name="End Date", value=session_info["EndDate"]),
                             EmbedField(name="GMT Offset", value=session_info["GmtOffset"])],
                     timestamp=__timestamp(timestamp=timestamp),
                     color=0xFFFFFF)

    def __session_status_embed(status: SessionStatus, timestamp: datetime | None = None):
        return Embed(title="Session Status", description=str(status["Status"]),
                     timestamp=__timestamp(timestamp=timestamp))

    def __team_radio_embed(team_radio: TeamRadioCapture, timestamp: datetime | None = None,
                           driver: Driver | None = None, session_path: str | None = None):
        if driver:
            if "HeadshotUrl" in driver:
                headshot_url = driver["HeadshotUrl"]

            else:
                headshot_url = None

            driver_name = f"{driver['FirstName']} {driver['LastName']} " + \
                f"({driver['RacingNumber']})"
            author = EmbedAuthor(name=driver_name, icon_url=headshot_url)
            fields = None

        else:
            author = None
            fields = [EmbedField(name="Racing Number", value=team_radio["RacingNumber"])]

        if session_path:
            url = (
                "https://livetiming.formula1.com/static/" + session_path +
                team_radio["Path"]
            )

        else:
            fields.append(EmbedField(name="Path", value=team_radio["Path"]))
            url = None

        return Embed(title="Team Radio", author=author, fields=fields, url=url,
                     timestamp=__timestamp(timestamp=timestamp))

    def __timestamp(timestamp: datetime | None = None):
        return timestamp.astimezone(timezone.utc).isoformat() if timestamp else None

    def __track_status_embed(track_status: TrackStatus, discord_env: __DiscordEnv,
                             timestamp: datetime | None = None):
        return Embed(title="Track Status",
                     fields=[EmbedField(name="Status", value=track_status["Status"]),
                             EmbedField(name="Message", value=track_status["Message"])],
                     description=(discord_env["GREEN_FLAG_EMOJI"] if track_status["Status"] in [
                         TrackStatusStatus.ALL_CLEAR,
                         TrackStatusStatus.GREEN,
                         TrackStatusStatus.VSC_ENDING] else discord_env["YELLOW_FLAG_EMOJI"]
                         if track_status["Status"] == TrackStatusStatus.YELLOW else
                         discord_env["SAFETY_CAR_EMOJI"] if track_status["Status"] ==
                         TrackStatusStatus.SC_DEPLOYED else discord_env["VIRTUAL_SAFETY_CAR_EMOJI"]
                         if track_status["Status"] == TrackStatusStatus.VSC_DEPLOYED else
                         discord_env["RED_FLAG_EMOJI"] if track_status["Status"] ==
                         TrackStatusStatus.RED else None),
                     color=(
                         0x00FF00 if track_status["Status"] in [
                             TrackStatusStatus.ALL_CLEAR,
                             TrackStatusStatus.GREEN,
                             TrackStatusStatus.VSC_ENDING,
                         ]
                         else 0xFFFF00 if track_status["Status"] in [
                             TrackStatusStatus.YELLOW,
                             TrackStatusStatus.SC_DEPLOYED,
                             TrackStatusStatus.VSC_DEPLOYED,
                         ]
                         else 0xFF0000 if track_status["Status"] == TrackStatusStatus.RED
                         else None
                     ),
                     timestamp=__timestamp(timestamp=timestamp))

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
    archive_session_info: List[int]
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
            year, meeting, session = args.archive_session_info

            logger.info(f"Retrieving archived feed by session information (Year: {year}, " +
                        f"Meeting: {meeting}, Session: {session})!")
            archive_client = F1ArchiveClient.get_by_session_info(year, meeting, session, *topics)

        elif args.archive_last_session:
            logger.info("Retrieving last archived session messages!")
            archive_client = F1ArchiveClient.get_last_session(*topics)

        else:
            assert False, "Unreachable as one of the above condition is required!"

        logger.info("Logging all archived session messages!")

        with archive_client:  # Fetches and loads topic data
            for topic, data, timedelta in archive_client:
                if topic in [StreamingTopic.CAR_DATA_Z, StreamingTopic.POSITION_Z] and \
                        args.archived_b64_zlib_decode:
                    message_logger.info(dumps([topic, loads(decompress_zlib_data(data)),
                                               timedelta], separators=(",", ":")))

                else:
                    message_logger.info(dumps([topic, data, timedelta], separators=(",", ":")))

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
                        message_logger.info(dumps(message["R"], separators=(",", ":")))

                    if "M" in message and len(message["M"]) != 0:
                        for invokation in message["M"]:
                            assert invokation["H"] == "streaming" and invokation["M"] == "feed"
                            logger.info("Logged 'feed' invokation arguments from 'streaming' hub!")

                            if invokation["A"][0] in [
                                StreamingTopic.CAR_DATA_Z,
                                StreamingTopic.POSITION_Z,
                            ] and args.live_b64_zlib_decode:
                                message_logger.info(dumps([
                                    invokation["A"][0],
                                    loads(decompress_zlib_data(invokation["A"][1])),
                                    invokation["A"][2]], separators=(",", ":")))

                            else:
                                message_logger.info(dumps(invokation["A"], separators=(",", ":")))

        except KeyboardInterrupt:
            logger.info("F1 Live Timing streaming feed logger stopped!")

    if exdc_available and args.action == _ProgramAction.LIVE_DISCORD_BOT:
        if live_streaming_status == "Offline":
            logger.warning("F1 Live Timing API Streaming Status: Offline!")

        discord_env = __discord_env(args.discord_env_path)
        embed_queue: Queue[Embed] = Queue()

        try:
            with F1LiveTimingClient(*topics) as lt_client:
                logger.info("F1 Live Timing streaming feed Discord bot started!")

                for feeds in lt_client:
                    for topic, change, timestamp in feeds:
                        if topic == StreamingTopic.ARCHIVE_STATUS:
                            assert lt_client.timing_client.archive_status
                            archive_status = lt_client.timing_client.archive_status

                            embed_queue.put(__archive_status_embed(archive_status,
                                                                   timestamp=timestamp))

                        elif topic == StreamingTopic.AUDIO_STREAMS:
                            assert lt_client.timing_client.audio_streams
                            audio_streams = lt_client.timing_client.audio_streams
                            session_info = lt_client.timing_client.session_info
                            session_path = session_info["Path"] if session_info else None

                            if isinstance(change["Streams"], Mapping):
                                for key in change["Streams"].keys():
                                    audio_stream = audio_streams[int(key)]

                                    embed_queue.put(__audio_stream_embed(audio_stream,
                                                                         session_path=session_path,
                                                                         timestamp=timestamp))

                            else:
                                assert isinstance(audio_streams["Streams"], list)

                                for stream in audio_streams["Streams"]:
                                    embed_queue.put(__audio_stream_embed(stream,
                                                                         session_path=session_path,
                                                                         timestamp=timestamp))

                        elif topic == StreamingTopic.CONTENT_STREAMS:
                            assert lt_client.timing_client.content_streams
                            content_streams = lt_client.timing_client.content_streams
                            session_info = lt_client.timing_client.session_info
                            session_path = session_info["Path"] if session_info else None

                            if isinstance(change["Streams"], Mapping):
                                for key in change["Streams"].keys():
                                    content_stream = content_streams[int(key)]

                                    embed_queue.put(__content_stream_embed(
                                        content_stream, session_path=session_path,
                                        timestamp=timestamp))

                            else:
                                assert isinstance(content_streams["Streams"], list)

                                for stream in content_streams["Streams"]:
                                    embed_queue.put(__content_stream_embed(
                                        stream, session_path=session_path, timestamp=timestamp))

                        elif topic == StreamingTopic.DRIVER_LIST:
                            continue

                        elif topic == StreamingTopic.EXTRAPOLATED_CLOCK:
                            assert lt_client.timing_client.extrapolated_clock
                            extrapolated_clock = lt_client.timing_client.extrapolated_clock

                            embed_queue.put(__extrapolated_clock_embed(extrapolated_clock,
                                                                       timestamp=timestamp))

                        elif topic == StreamingTopic.RACE_CONTROL_MESSAGES:
                            assert lt_client.timing_client.race_control_messages
                            driver_list = lt_client.timing_client.driver_list
                            race_control_messages = lt_client.timing_client.race_control_messages
                            messages = change["Messages"]

                            if isinstance(messages, Mapping):
                                for key in messages.keys():
                                    message = race_control_messages["Messages"][int(key)]

                                    if "RacingNumber" in message and driver_list and \
                                            message["RacingNumber"] in driver_list:
                                        driver = driver_list[message["RacingNumber"]]

                                    else:
                                        driver = None

                                    embed_queue.put(__race_control_message_embed(
                                        message, discord_env, timestamp=timestamp, driver=driver))

                            else:
                                assert isinstance(race_control_messages["Messages"], list)

                                for message in race_control_messages["Messages"]:
                                    if "RacingNumber" in message and driver_list and \
                                            message["RacingNumber"] in driver_list:
                                        driver = driver_list[message["RacingNumber"]]

                                    else:
                                        driver = None

                                    embed_queue.put(__race_control_message_embed(
                                        message, discord_env, timestamp=timestamp, driver=driver))

                        elif topic == StreamingTopic.SESSION_INFO:
                            assert lt_client.timing_client.session_info
                            session_info = lt_client.timing_client.session_info

                            embed_queue.put(__session_info_embed(session_info,
                                                                 timestamp=timestamp))

                        elif topic == StreamingTopic.SESSION_STATUS:
                            assert lt_client.timing_client.session_status
                            session_status = lt_client.timing_client.session_status

                            embed_queue.put(__session_status_embed(session_status,
                                                                   timestamp=timestamp))

                        elif topic == StreamingTopic.TEAM_RADIO:
                            assert lt_client.timing_client.team_radio
                            team_radio = lt_client.timing_client.team_radio
                            driver_list = lt_client.timing_client.driver_list
                            session_info = lt_client.timing_client.session_info
                            session_path = session_info["Path"] if session_info else None
                            captures = change["Captures"]

                            if isinstance(captures, Mapping):
                                for key in captures.keys():
                                    capture = team_radio["Captures"][key]

                                    if driver_list and capture["RacingNumber"] in driver_list:
                                        driver = driver_list[capture["RacingNumber"]]

                                    else:
                                        driver = None

                                    embed_queue.put(__team_radio_embed(
                                        capture, timestamp=timestamp, driver=driver,
                                        session_path=session_path))

                            else:
                                assert isinstance(team_radio["Captures"], list)

                                for capture in team_radio["Captures"]:
                                    if driver_list and capture["RacingNumber"] in driver_list:
                                        driver = driver_list[capture["RacingNumber"]]

                                    else:
                                        driver = None

                                    embed_queue.put(__team_radio_embed(
                                        capture, timestamp=timestamp, driver=driver,
                                        session_path=session_path))

                        elif topic == StreamingTopic.TRACK_STATUS:
                            assert lt_client.timing_client.track_status
                            track_status = lt_client.timing_client.track_status

                            embed_queue.put(__track_status_embed(
                                track_status, discord_env, timestamp=timestamp))

                        else:
                            print(topic, change, timestamp)

                    embeds: List[Embed] = []

                    while len(embeds) < 10:
                        try:
                            embeds.append(embed_queue.get(block=False))

                        except Empty:
                            break

                    if len(embeds) > 0:
                        __message_embeds(discord_env, embeds)

        except KeyboardInterrupt:
            logger.info("F1 Live Timing streaming feed Discord bot stopped!")
