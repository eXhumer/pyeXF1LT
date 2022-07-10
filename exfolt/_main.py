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

import json
from argparse import ArgumentParser, Namespace
from datetime import datetime, timezone
from logging import (
    DEBUG,
    FileHandler,
    Formatter,
    getLogger,
    INFO,
    StreamHandler,
)
from os import environ
from pathlib import Path
from pkg_resources import require
from queue import Queue
from sys import stdout
from typing import Dict, List, Optional

from dotenv import dotenv_values

from ._client import (
    AudioStreamData,
    ExtrapolatedClockData,
    F1LiveClient,
    RaceControlMessageData,
    SessionInfoData,
    TeamRadioData,
    TimingAppData,
    TimingClient,
    TimingStatsData,
    TimingType,
    TrackStatusData,
)
from ._utils import datetime_string_parser


__version__ = require(__package__)[0].version


try:
    from exdc import DiscordClient, DiscordModel, DiscordType
    exdc_available = True

    def __discord_methods(discord_env: Dict[str, str]):
        BLACK_FLAG_EMOJI = discord_env["BLACK_FLAG_EMOJI"]
        BLACK_ORANGE_FLAG_EMOJI = discord_env["BLACK_ORANGE_FLAG_EMOJI"]
        BLACK_WHITE_FLAG_EMOJI = discord_env["BLACK_WHITE_FLAG_EMOJI"]
        BLUE_FLAG_EMOJI = discord_env["BLUE_FLAG_EMOJI"]
        BOT_TOKEN = discord_env["BOT_TOKEN"] if "BOT_TOKEN" in discord_env else None
        CHANNEL_ID = discord_env["CHANNEL_ID"] if "CHANNEL_ID" in discord_env else None
        CHEQUERED_FLAG_EMOJI = discord_env["CHEQUERED_FLAG_EMOJI"]
        GREEN_FLAG_EMOJI = discord_env["GREEN_FLAG_EMOJI"]
        HARD_TYRE_EMOJI = discord_env["HARD_TYRE_EMOJI"]
        INTER_TYRE_EMOJI = discord_env["INTER_TYRE_EMOJI"]
        MEDIUM_TYRE_EMOJI = discord_env["MEDIUM_TYRE_EMOJI"]
        RED_FLAG_EMOJI = discord_env["RED_FLAG_EMOJI"]
        SAFETY_CAR_EMOJI = discord_env["SAFETY_CAR_EMOJI"]
        SOFT_TYRE_EMOJI = discord_env["SOFT_TYRE_EMOJI"]
        UNKNOWN_TYRE_EMOJI = discord_env["UNKNOWN_TYRE_EMOJI"]
        VIRTUAL_SAFETY_CAR_EMOJI = discord_env["VIRTUAL_SAFETY_CAR_EMOJI"]
        WEBHOOK_ID = discord_env["WEBHOOK_ID"] if "WEBHOOK_ID" in discord_env else None
        WEBHOOK_TOKEN = discord_env["WEBHOOK_TOKEN"] if "WEBHOOK_TOKEN" in discord_env else None
        WET_TYRE_EMOJI = discord_env["WET_TYRE_EMOJI"]
        YELLOW_FLAG_EMOJI = discord_env["YELLOW_FLAG_EMOJI"]

        def __audio_stream_embed(
            audio_stream: AudioStreamData,
            timing_client: TimingClient,
            timestamp: datetime,
        ):
            archive_url = (
                "https://livetiming.formula1.com/static/" +
                timing_client.session_info.path + audio_stream.path
            )

            return DiscordModel.Embed(
                title="Audio Stream",
                color=0x00FFFF,
                fields=[
                    DiscordModel.Embed.Field("Name", audio_stream.name),
                    DiscordModel.Embed.Field("Language", audio_stream.language),
                    DiscordModel.Embed.Field("Archive Link", f"[Link]({archive_url})"),
                    DiscordModel.Embed.Field("Live Link", f"[Link]({audio_stream.uri})"),
                ],
                timestamp=timestamp,
            )

        def __bot_start_message():
            return {
                "embeds": [
                    DiscordModel.Embed(title="Live Timing Bot Started",
                                       timestamp=datetime.utcnow()),
                ],
                "components": [
                    DiscordModel.ActionRowComponent([
                        DiscordModel.ButtonComponent(
                            DiscordType.ButtonStyle.LINK,
                            label="Source Code",
                            url="https://github.com/eXhumer/pyeXF1LT",
                        )
                    ])
                ],
            }

        def __bot_stop_message():
            return {
                "embeds": [
                    DiscordModel.Embed(title="Live Timing Bot Stopped",
                                       timestamp=datetime.utcnow()),
                ],
                "components": [
                    DiscordModel.ActionRowComponent([
                        DiscordModel.ButtonComponent(
                            DiscordType.ButtonStyle.LINK,
                            label="Source Code",
                            url="https://github.com/eXhumer/pyeXF1LT",
                        )
                    ])
                ],
            }

        def __discord_message(**args):
            if BOT_TOKEN and CHANNEL_ID:
                Authorization = DiscordClient.BotAuthorization
                DiscordClient(Authorization(BOT_TOKEN)).post_message(CHANNEL_ID, **args)

            if WEBHOOK_TOKEN and WEBHOOK_ID:
                DiscordClient.post_webhook_message(WEBHOOK_ID, WEBHOOK_TOKEN, **args)

        def __extrapolated_clock_embed(clock_data: ExtrapolatedClockData, timestamp: datetime):
            return DiscordModel.Embed(
                title="Extrapolated Clock",
                fields=[
                    DiscordModel.Embed.Field("Remaining", clock_data.remaining),
                    DiscordModel.Embed.Field("Extrapolating", str(clock_data.extrapolating)),
                ],
                timestamp=timestamp,
            )

        def __race_control_message_embed(
            rcm_msg: RaceControlMessageData,
            timing_client: TimingClient,
            timestamp: datetime,
        ):
            fields = [
                DiscordModel.Embed.Field("Message", rcm_msg.message),
                DiscordModel.Embed.Field("Category", rcm_msg.category),
            ]

            if rcm_msg.racing_number is not None:
                if rcm_msg.racing_number in timing_client.drivers:
                    driver_data = timing_client.drivers[rcm_msg.racing_number]
                    author = DiscordModel.Embed.Author(str(driver_data),
                                                       icon_url=driver_data.headshot_url)

                else:
                    author = None
                    fields.append(DiscordModel.Embed.Field("Racing Number", rcm_msg.racing_number))

            else:
                author = None

            if rcm_msg.flag == TimingType.FlagStatus.BLACK:
                color = 0x000000
                description = BLACK_FLAG_EMOJI

            elif rcm_msg.flag == TimingType.FlagStatus.BLACK_AND_ORANGE:
                color = 0xFFA500
                description = BLACK_ORANGE_FLAG_EMOJI

            elif rcm_msg.flag == TimingType.FlagStatus.BLACK_AND_WHITE:
                color = 0xFFA500
                description = BLACK_WHITE_FLAG_EMOJI

            elif rcm_msg.flag == TimingType.FlagStatus.BLUE:
                color = 0x0000FF
                description = BLUE_FLAG_EMOJI

            elif rcm_msg.flag in (TimingType.FlagStatus.CHEQUERED, TimingType.FlagStatus.CLEAR):
                color = 0xFFFFFF

                if rcm_msg.flag == TimingType.FlagStatus.CLEAR:
                    description = GREEN_FLAG_EMOJI

                else:
                    description = CHEQUERED_FLAG_EMOJI

            elif rcm_msg.flag == TimingType.FlagStatus.GREEN:
                color = 0x00FF00
                description = GREEN_FLAG_EMOJI

            elif rcm_msg.flag == TimingType.FlagStatus.YELLOW:
                color = 0xFFFF00
                description = YELLOW_FLAG_EMOJI

            elif rcm_msg.flag == TimingType.FlagStatus.DOUBLE_YELLOW:
                color = 0xFFA500
                description = "".join((YELLOW_FLAG_EMOJI, YELLOW_FLAG_EMOJI))

            elif rcm_msg.flag == TimingType.FlagStatus.RED:
                color = 0xFF0000
                description = RED_FLAG_EMOJI

            else:
                color = 0XA6EF1F
                description = None

            if rcm_msg.status is not None:
                if rcm_msg.category == "Drs":
                    fields.append(DiscordModel.Embed.Field("DRS Status", rcm_msg.status))

                elif rcm_msg.category == "SafetyCar":
                    fields.append(DiscordModel.Embed.Field("Safety Car Status", rcm_msg.status))

                else:
                    fields.append(DiscordModel.Embed.Field("Status", rcm_msg.status))

            if rcm_msg.flag is not None:
                fields.append(DiscordModel.Embed.Field("Flag", rcm_msg.flag))

            if rcm_msg.lap is not None:
                fields.append(DiscordModel.Embed.Field("Lap", rcm_msg.lap))

            if rcm_msg.scope is not None:
                fields.append(DiscordModel.Embed.Field("Scope", rcm_msg.scope))

            if rcm_msg.sector is not None:
                fields.append(DiscordModel.Embed.Field("Sector", rcm_msg.sector))

            return DiscordModel.Embed(title="Race Control Message", author=author, color=color,
                                      description=description, fields=fields, timestamp=timestamp)

        def __session_info_embed(session_info: SessionInfoData, timestamp: datetime):
            return DiscordModel.Embed(
                title="Session Information",
                fields=[
                    DiscordModel.Embed.Field("Official Name",
                                             session_info.meeting["OfficialName"]),
                    DiscordModel.Embed.Field("Meeting Name", session_info.meeting["Name"]),
                    DiscordModel.Embed.Field("Location", session_info.meeting["Location"]),
                    DiscordModel.Embed.Field("Country", session_info.meeting["Country"]["Name"]),
                    DiscordModel.Embed.Field("Circuit",
                                             session_info.meeting["Circuit"]["ShortName"]),
                    DiscordModel.Embed.Field("Session Name", session_info.name),
                    DiscordModel.Embed.Field("Start Date", session_info.start_date),
                    DiscordModel.Embed.Field("End Date", session_info.end_date),
                    DiscordModel.Embed.Field("GMT Offset", session_info.gmt_offset),
                ],
                timestamp=timestamp,
                color=0xFFFFFF,
            )

        def __session_status_embed(status: TimingType.SessionStatus, timestamp: datetime):
            return DiscordModel.Embed(title="Session Status", description=status,
                                      timestamp=timestamp)

        def __team_radio_embed(
            team_radio: TeamRadioData,
            timing_client: TimingClient,
            timestamp: datetime,
        ):
            driver_data = timing_client.drivers.get(team_radio.racing_number, None)
            session_info = timing_client.session_info

            if driver_data:
                author = DiscordModel.Embed.Author(str(driver_data),
                                                   icon_url=driver_data.headshot_url)
                fields = None

            else:
                author = None
                fields = [DiscordModel.Embed.Field("Racing Number", team_radio.racing_number)]

            return DiscordModel.Embed(
                title="Team Radio",
                author=author,
                fields=fields,
                url=(
                    "https://livetiming.formula1.com/static/" + session_info.path +
                    team_radio.path
                ),
                timestamp=timestamp,
            )

        def __timing_app_data_stint_embed(
            stint: TimingAppData.Stint,
            timestamp: datetime,
            racing_number: Optional[str] = None,
            timing_client: Optional[TimingClient] = None,
        ):
            compound = (
                WET_TYRE_EMOJI if stint.compound == TimingType.TyreCompound.WET
                else INTER_TYRE_EMOJI if stint.compound == TimingType.TyreCompound.INTERMEDIATE
                else SOFT_TYRE_EMOJI if stint.compound == TimingType.TyreCompound.SOFT
                else MEDIUM_TYRE_EMOJI if stint.compound == TimingType.TyreCompound.MEDIUM
                else HARD_TYRE_EMOJI if stint.compound == TimingType.TyreCompound.HARD
                else UNKNOWN_TYRE_EMOJI
            )

            fields = [
                DiscordModel.Embed.Field("Compound", compound, inline=True,),
                DiscordModel.Embed.Field("New", str(stint.new), inline=True),
                DiscordModel.Embed.Field("Tyre Changed", str(not stint.tyre_not_changed),
                                         inline=True),
                DiscordModel.Embed.Field("Start Laps", str(stint.start_laps), inline=True),
                DiscordModel.Embed.Field("Total Laps", str(stint.total_laps), inline=True),
            ]

            if racing_number:
                if timing_client:
                    driver_data = timing_client.drivers[racing_number]
                    author = DiscordModel.Embed.Author(str(driver_data),
                                                       icon_url=driver_data.headshot_url)

                else:
                    fields.append(DiscordModel.Embed.Field("Racing Number", racing_number))
                    author = None

            else:
                author = None

            return DiscordModel.Embed(
                title="Pit Stop Information",
                author=author,
                fields=fields,
                timestamp=timestamp,
            )

        def __track_status_embed(track_status: TrackStatusData, timestamp: datetime):
            return DiscordModel.Embed(
                title="Track Status",
                fields=[
                    DiscordModel.Embed.Field(
                        "Status",
                        track_status.status_string,
                    ),
                    DiscordModel.Embed.Field(
                        "Message",
                        track_status.message,
                    ),
                ],
                description=(
                    GREEN_FLAG_EMOJI if track_status.status in [
                        TimingType.TrackStatus.ALL_CLEAR,
                        TimingType.TrackStatus.GREEN,
                        TimingType.TrackStatus.VSC_ENDING,
                    ]
                    else YELLOW_FLAG_EMOJI if track_status.status == TimingType.TrackStatus.YELLOW
                    else SAFETY_CAR_EMOJI if track_status.status ==
                    TimingType.TrackStatus.SC_DEPLOYED
                    else VIRTUAL_SAFETY_CAR_EMOJI
                    if track_status.status == TimingType.TrackStatus.VSC_DEPLOYED
                    else RED_FLAG_EMOJI if track_status.status == TimingType.TrackStatus.RED
                    else None
                ),
                color=(
                    0x00FF00 if track_status.status in [
                        TimingType.TrackStatus.ALL_CLEAR,
                        TimingType.TrackStatus.GREEN,
                        TimingType.TrackStatus.VSC_ENDING,
                    ]
                    else 0xFFFF00 if track_status.status in [
                        TimingType.TrackStatus.YELLOW,
                        TimingType.TrackStatus.SC_DEPLOYED,
                        TimingType.TrackStatus.VSC_DEPLOYED,
                    ]
                    else 0xFF0000 if track_status.status == TimingType.TrackStatus.RED
                    else None
                ),
                timestamp=timestamp,
            )

        return (
            __audio_stream_embed,
            __bot_start_message,
            __bot_stop_message,
            __discord_message,
            __extrapolated_clock_embed,
            __race_control_message_embed,
            __session_info_embed,
            __session_status_embed,
            __team_radio_embed,
            __timing_app_data_stint_embed,
            __track_status_embed,
        )

    def __load_discord_envs(env_path: Path):
        discord_env: Dict[str, str] = {}

        if env_path.is_file():
            for k, v in dotenv_values(dotenv_path=env_path).items():
                if v is not None and len(v) > 0:
                    discord_env |= {k: v}

        for k, v in environ.items():
            if k.startswith("DISCORD_") and len(v) > 0:
                discord_env |= {k[8:]: v}

        assert all([
            item in discord_env.keys() for item in (
                "BLACK_FLAG_EMOJI", "BLACK_ORANGE_FLAG_EMOJI", "BLACK_WHITE_FLAG_EMOJI",
                "BLUE_FLAG_EMOJI", "CHEQUERED_FLAG_EMOJI", "GREEN_FLAG_EMOJI", "HARD_TYRE_EMOJI",
                "INTER_TYRE_EMOJI", "MEDIUM_TYRE_EMOJI", "RED_FLAG_EMOJI", "SAFETY_CAR_EMOJI",
                "SOFT_TYRE_EMOJI", "UNKNOWN_TYRE_EMOJI", "VIRTUAL_SAFETY_CAR_EMOJI",
                "WET_TYRE_EMOJI", "YELLOW_FLAG_EMOJI",
            )
        ]), "Required Discord emoji(s) missing!"

        assert (
            "BOT_TOKEN" in discord_env.keys() and "CHANNEL_ID" in discord_env.keys()
        ) or (
            "WEBHOOK_TOKEN" in discord_env.keys() and "WEBHOOK_ID" in discord_env.keys()
        ), "Missing required credentials for Discord messaging!"

        return discord_env

except ImportError:
    exdc_available = False


def __message_logger(args: Namespace):
    file_stream = FileHandler(args.log_file, mode="w")
    file_stream.setFormatter(Formatter("%(message)s\n"))
    logger = getLogger("message_logger")
    logger.addHandler(file_stream)
    file_stream.setLevel(INFO)
    logger.setLevel(INFO)
    return logger


def __program_args():
    parser = ArgumentParser(
        prog="eXF1LT",
        description="unofficial F1 live timing client",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"{parser.prog} {__version__}",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="verbose logging output",
    )
    parser.add_argument(
        "--license",
        "-L",
        action="store_true",
        help="display project license",
    )
    topics_parser = parser.add_argument_group(
        title="F1 live timing SignalR streaming topics",
    )
    topics_parser.add_argument(
        "--archive-status",
        action="store_true",
        help="ArchiveStatus support",
    )
    topics_parser.add_argument(
        "--audio-streams",
        action="store_true",
        help="AudioStreams support",
    )
    topics_parser.add_argument(
        "--car-data",
        action="store_true",
        help="CarData.z support",
    )
    topics_parser.add_argument(
        "--championship-prediction",
        action="store_true",
        help="ChampionshipPrediction support",
    )
    topics_parser.add_argument(
        "--content-streams",
        action="store_true",
        help="ContentStreams support",
    )
    topics_parser.add_argument(
        "--current-tyres",
        action="store_true",
        help="CurrentTyres support",
    )
    topics_parser.add_argument(
        "--driver-list",
        action="store_true",
        help="DriverList support",
    )
    topics_parser.add_argument(
        "--extrapolated-clock",
        action="store_true",
        help="ExtrapolatedClock support",
    )
    topics_parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Heartbeat support",
    )
    topics_parser.add_argument(
        "--lap-count",
        action="store_true",
        help="LapCount support",
    )
    topics_parser.add_argument(
        "--position",
        action="store_true",
        help="Position.z support",
    )
    topics_parser.add_argument(
        "--race-control-messages",
        action="store_true",
        help="RaceControlMessages support",
    )
    topics_parser.add_argument(
        "--session-data",
        action="store_true",
        help="SessionData support",
    )
    topics_parser.add_argument(
        "--session-info",
        action="store_true",
        help="SessionInfo support",
    )
    topics_parser.add_argument(
        "--session-status",
        action="store_true",
        help="SessionStatus support",
    )
    topics_parser.add_argument(
        "--team-radio",
        action="store_true",
        help="TeamRadio support",
    )
    topics_parser.add_argument(
        "--timing-app-data",
        action="store_true",
        help="TimingAppData support",
    )
    topics_parser.add_argument(
        "--timing-data",
        action="store_true",
        help="TimingData support",
    )
    topics_parser.add_argument(
        "--timing-stats",
        action="store_true",
        help="TimingStats support",
    )
    topics_parser.add_argument(
        "--top-three",
        action="store_true",
        help="TopThree support",
    )
    topics_parser.add_argument(
        "--track-status",
        action="store_true",
        help="TrackStatus support",
    )
    topics_parser.add_argument(
        "--weather-data",
        action="store_true",
        help="WeatherData support",
    )
    action_subparser = parser.add_subparsers(
        dest="action",
        title="actions",
        description="list of supported command line actions",
        metavar="supported actions",
    )
    live_message_log_parser = action_subparser.add_parser(
        "message-logger",
        help="log incoming messages to file",
        description="log incoming messages to file",
    )
    live_message_log_parser.add_argument(
        "log_file",
        type=Path,
        help="file path to store logged messaged in",
    )

    if exdc_available:
        live_discord_bot_parser = action_subparser.add_parser(
            "discord-bot",
            help="run Discord bot output incoming messages as Discord messages",
            description="run Discord bot to output incoming messages as Discord messages",
        )
        live_discord_bot_parser.add_argument(
            "--env-path",
            type=Path,
            dest="discord_env_path",
            default=Path("discord.env"),
            help="Discord environment file path",
        )
        live_discord_bot_parser.add_argument(
            "--start-message",
            action="store_true",
            help="show start Discord message on startup",
        )
        live_discord_bot_parser.add_argument(
            "--stop-message",
            action="store_true",
            help="show stop Discord message on exit",
        )
        live_discord_bot_parser.add_argument(
            "--replay-audio-streams-message",
            action="store_true",
            help="replay AudioStreams data",
        )
        live_discord_bot_parser.add_argument(
            "--replay-session-info-message",
            action="store_true",
            help="replay SessionInfo data",
        )
        live_discord_bot_parser.add_argument(
            "--skip-replay-data",
            action="store_true",
            help="skip replay data",
        )
        live_discord_bot_parser.add_argument(
            "--log-to-file",
            dest="log_path",
            type=Path,
            help="log to local file",
        )
        live_discord_bot_parser.add_argument(
            "--no-console-log",
            action="store_true",
            help="disable logging to console",
        )

    return parser.parse_args(), parser.prog


def __program_license(program_name: str):
    return (
        """
        {program_name} {version}

        {program_name} - Unofficial F1 live timing client
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
    ).format(
        program_name=program_name,
        version=__version__,
    )


def __program_logger(args: Namespace):
    log_formatter = Formatter("[%(asctime)s][%(name)s][%(levelname)s]\t%(message)s")

    if not args.no_console_log:
        out_stream = StreamHandler(stdout)
        out_stream.setFormatter(log_formatter)

    if args.log_path:
        file_stream = FileHandler(args.log_path, mode="w")
        file_stream.setFormatter(log_formatter)

    logger = getLogger("exfolt")

    if not args.no_console_log:
        logger.addHandler(out_stream)

    if args.log_path:
        logger.addHandler(file_stream)

    if args.verbose == 0:
        if not args.no_console_log:
            out_stream.setLevel(INFO)

        if args.log_path:
            file_stream.setLevel(INFO)

        logger.setLevel(INFO)

    else:
        if not args.no_console_log:
            out_stream.setLevel(DEBUG)

        if args.log_path:
            file_stream.setLevel(DEBUG)

        logger.setLevel(DEBUG)

    return logger


def __setup_live_client(args: Namespace):
    topics: List[TimingType.Topic] = []

    if args.archive_status:
        topics.append(TimingType.Topic.ARCHIVE_STATUS)

    if args.audio_streams:
        topics.append(TimingType.Topic.AUDIO_STREAMS)

    if args.car_data:
        topics.append(TimingType.Topic.CAR_DATA_Z)

    if args.championship_prediction:
        topics.append(TimingType.Topic.CHAMPIONSHIP_PREDICTION)

    if args.content_streams:
        topics.append(TimingType.Topic.CONTENT_STREAMS)

    if args.current_tyres:
        topics.append(TimingType.Topic.CURRENT_TYRES)

    if args.driver_list:
        topics.append(TimingType.Topic.DRIVER_LIST)

    if args.extrapolated_clock:
        topics.append(TimingType.Topic.EXTRAPOLATED_CLOCK)

    if args.heartbeat:
        topics.append(TimingType.Topic.HEARTBEAT)

    if args.lap_count:
        topics.append(TimingType.Topic.LAP_COUNT)

    if args.position:
        topics.append(TimingType.Topic.POSITION_Z)

    if args.race_control_messages:
        topics.append(TimingType.Topic.RACE_CONTROL_MESSAGES)

    if args.session_data:
        topics.append(TimingType.Topic.SESSION_DATA)

    if args.session_info:
        topics.append(TimingType.Topic.SESSION_INFO)

    if args.session_status:
        topics.append(TimingType.Topic.SESSION_STATUS)

    if args.team_radio:
        topics.append(TimingType.Topic.TEAM_RADIO)

    if args.timing_app_data:
        topics.append(TimingType.Topic.TIMING_APP_DATA)

    if args.timing_data:
        topics.append(TimingType.Topic.TIMING_DATA)

    if args.timing_stats:
        topics.append(TimingType.Topic.TIMING_STATS)

    if args.top_three:
        topics.append(TimingType.Topic.TOP_THREE)

    if args.track_status:
        topics.append(TimingType.Topic.TRACK_STATUS)

    if args.weather_data:
        topics.append(TimingType.Topic.WEATHER_DATA)

    return F1LiveClient(*topics)


def __program_main():
    args, prog = __program_args()
    logger = __program_logger(args)

    if args.license:
        print(__program_license(prog))

    if args.action == "message-logger":
        message_logger = __message_logger(args)

        try:
            with __setup_live_client(args) as live_client:
                for _, message in live_client:
                    if len(message) == 0:
                        continue

                    if "R" in message:
                        logger.info("Old data packet received at " +
                                    str(datetime.now(tz=timezone.utc)))
                        message_logger.info(json.dumps(message["R"]))

                    if "M" in message and len(message["M"]) > 0:
                        logger.info("New data packet received at " +
                                    str(datetime.now(tz=timezone.utc)))
                        message_logger.info(json.dumps(message["M"][0]["A"]))

        except KeyboardInterrupt:
            pass

    if exdc_available and args.action == "discord-bot":
        (
            audio_stream_embed,
            bot_start_message,
            bot_stop_message,
            discord_message,
            extrapolated_clock_embed,
            race_control_message_embed,
            session_info_embed,
            session_status_embed,
            team_radio_embed,
            timing_app_data_stint_embed,
            track_status_embed,
        ) = __discord_methods(__load_discord_envs(args.discord_env_path))

        if args.start_message:
            discord_message(**bot_start_message())

        timing_client = TimingClient()
        embed_queue: Queue[DiscordModel.Embed] = Queue()

        try:
            with __setup_live_client(args) as live_client:
                for _, message in live_client:
                    if len(message) == 0:
                        continue

                    if "R" in message and not args.skip_replay_data:
                        logger.info("Old data packet received at " +
                                    str(datetime.now(tz=timezone.utc)))
                        timing_client.process_old_data(message["R"])

                        if args.replay_audio_streams_message:
                            for audio_stream in timing_client.audio_streams:
                                embed_queue.put(
                                    audio_stream_embed(
                                        audio_stream,
                                        timing_client,
                                        datetime.utcnow(),
                                    ),
                                )

                        if args.replay_session_info_message:
                            embed_queue.put(
                                session_info_embed(
                                    timing_client.session_info,
                                    datetime.utcnow(),
                                ),
                            )

                    if "M" in message and len(message["M"]) > 0:
                        logger.info("New data packet received at " +
                                    str(datetime.now(tz=timezone.utc)))
                        live_msg_data = message["M"][0]["A"]
                        timing_client.process_data(*live_msg_data)

                    for (topic, timing_item, data, timestamp) in timing_client:
                        if (
                            topic == TimingType.Topic.AUDIO_STREAMS and
                            isinstance(timing_item, AudioStreamData)
                        ):
                            embed_queue.put(
                                audio_stream_embed(
                                    timing_item,
                                    timing_client,
                                    datetime_string_parser(timestamp),
                                ),
                            )

                        elif (
                            topic == TimingType.Topic.EXTRAPOLATED_CLOCK and
                            isinstance(timing_item, ExtrapolatedClockData)
                        ):
                            embed_queue.put(
                                extrapolated_clock_embed(
                                    timing_item,
                                    datetime_string_parser(timestamp),
                                )
                            )

                        elif (
                            topic == TimingType.Topic.RACE_CONTROL_MESSAGES and
                            isinstance(timing_item, RaceControlMessageData)
                        ):
                            embed_queue.put(
                                race_control_message_embed(
                                    timing_item,
                                    timing_client,
                                    datetime_string_parser(timestamp),
                                ),
                            )

                        elif (
                            topic == TimingType.Topic.SESSION_INFO and
                            isinstance(timing_item, SessionInfoData)
                        ):
                            embed_queue.put(
                                session_info_embed(
                                    timing_item,
                                    datetime_string_parser(timestamp),
                                ),
                            )

                        elif (
                            topic == TimingType.Topic.SESSION_STATUS and
                            isinstance(timing_item, TimingType.SessionStatus)
                        ):
                            embed_queue.put(
                                session_status_embed(
                                    timing_item,
                                    datetime_string_parser(timestamp),
                                ),
                            )

                        elif (
                            topic == TimingType.Topic.TEAM_RADIO and
                            isinstance(timing_item, TeamRadioData)
                        ):
                            embed_queue.put(
                                team_radio_embed(
                                    timing_item,
                                    timing_client,
                                    datetime_string_parser(timestamp),
                                ),
                            )

                        elif (
                            topic == TimingType.Topic.TIMING_APP_DATA and
                            isinstance(timing_item, TimingAppData)
                        ):
                            if "Stints" in data:
                                timing_stints = data["Stints"]

                                if isinstance(timing_stints, list):
                                    if len(timing_stints) > 0:
                                        embed_queue.put(
                                            timing_app_data_stint_embed(
                                                timing_item.stints[-1],
                                                datetime_string_parser(timestamp),
                                                racing_number=timing_item.racing_number,
                                                timing_client=timing_client,
                                            ),
                                        )

                                else:
                                    if "Compound" in list(timing_stints.values())[0]:
                                        embed_queue.put(
                                            timing_app_data_stint_embed(
                                                timing_item.stints[-1],
                                                datetime_string_parser(timestamp),
                                                racing_number=timing_item.racing_number,
                                                timing_client=timing_client,
                                            ),
                                        )

                        elif (
                            topic == TimingType.Topic.TIMING_STATS and
                            isinstance(timing_item, dict)
                        ):
                            for racing_number, lines_data in data["Lines"].items():
                                driver_data = timing_client.drivers.get(racing_number, None)
                                timing_stats: TimingStatsData = timing_item[racing_number]

                                if driver_data:
                                    author = DiscordModel.Embed.Author(
                                        str(driver_data),
                                        icon_url=driver_data.headshot_url,
                                    )

                                else:
                                    author = None

                                if (
                                    "PersonalBestLapTime" in lines_data and
                                    "Position" in lines_data["PersonalBestLapTime"] and
                                    lines_data["PersonalBestLapTime"]["Position"] == 1
                                ):
                                    new_fl_time = timing_stats.best_lap_time
                                    assert new_fl_time
                                    minutes = new_fl_time.seconds // 60
                                    seconds = new_fl_time.total_seconds() - (minutes * 60)

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Lap Time",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Lap Time",
                                                    f"{minutes}:{round(seconds, 3)}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSpeeds" in lines_data and
                                    "I1" in lines_data["BestSpeeds"] and
                                    "Position" in lines_data["BestSpeeds"]["I1"] and
                                    lines_data["BestSpeeds"]["I1"]["Position"] == 1
                                ):
                                    new_i2_speed = timing_stats.best_intermediate_1_speed
                                    assert new_i2_speed

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Intermediate 1 Speed",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Speed",
                                                    f"{new_i2_speed}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSpeeds" in lines_data and
                                    "I2" in lines_data["BestSpeeds"] and
                                    "Position" in lines_data["BestSpeeds"]["I2"] and
                                    lines_data["BestSpeeds"]["I2"]["Position"] == 1
                                ):
                                    new_i2_speed = timing_stats.best_intermediate_2_speed
                                    assert new_i2_speed

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Intermediate 2 Speed",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Speed",
                                                    f"{new_i2_speed}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSpeeds" in lines_data and
                                    "FL" in lines_data["BestSpeeds"] and
                                    "Position" in lines_data["BestSpeeds"]["FL"] and
                                    lines_data["BestSpeeds"]["FL"]["Position"] == 1
                                ):
                                    new_fl_speed = timing_stats.best_finish_line_speed
                                    assert new_fl_speed

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Finish Line Speed",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Speed",
                                                    f"{new_fl_speed}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSpeeds" in lines_data and
                                    "ST" in lines_data["BestSpeeds"] and
                                    "Position" in lines_data["BestSpeeds"]["ST"] and
                                    lines_data["BestSpeeds"]["ST"]["Position"] == 1
                                ):
                                    new_st_speed = timing_stats.best_speed_trap_speed
                                    assert new_st_speed

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Speed Trap Speed",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Speed",
                                                    f"{new_st_speed}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSectors" in lines_data and
                                    isinstance(lines_data["BestSectors"], dict) and
                                    "0" in lines_data["BestSectors"] and
                                    "Position" in lines_data["BestSectors"]["0"] and
                                    lines_data["BestSectors"]["0"]["Position"] == 1
                                ):
                                    new_s1_time = timing_stats.best_sector_1
                                    assert new_s1_time

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Sector 1",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Time",
                                                    f"{round(new_s1_time, 3)}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSectors" in lines_data and
                                    isinstance(lines_data["BestSectors"], dict) and
                                    "1" in lines_data["BestSectors"] and
                                    "Position" in lines_data["BestSectors"]["1"] and
                                    lines_data["BestSectors"]["1"]["Position"] == 1
                                ):
                                    new_s2_time = timing_stats.best_sector_2
                                    assert new_s2_time

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Sector 2",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Time",
                                                    f"{round(new_s2_time, 3)}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                                if (
                                    "BestSectors" in lines_data and
                                    isinstance(lines_data["BestSectors"], dict) and
                                    "2" in lines_data["BestSectors"] and
                                    "Position" in lines_data["BestSectors"]["2"] and
                                    lines_data["BestSectors"]["2"]["Position"] == 1
                                ):
                                    new_s3_time = timing_stats.best_sector_3
                                    assert new_s3_time

                                    embed_queue.put(
                                        DiscordModel.Embed(
                                            title="Fastest Sector 3",
                                            author=author,
                                            color=0xA020F0,
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Time",
                                                    f"{round(new_s3_time, 3)}",
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(timestamp),
                                        )
                                    )

                        elif (
                            topic == TimingType.Topic.TRACK_STATUS and
                            isinstance(timing_item, TrackStatusData)
                        ):
                            embed_queue.put(
                                track_status_embed(
                                    timing_item,
                                    datetime_string_parser(timestamp),
                                ),
                            )

                        else:
                            logger.info(timing_item)

                    while embed_queue.qsize() > 0:
                        embeds: List[DiscordModel.Embed] = []

                        while embed_queue.qsize() > 0 and len(embeds) < 10:
                            embeds.append(embed_queue.get())

                        discord_message(embeds=embeds)

        except KeyboardInterrupt:
            if args.stop_message:
                discord_message(**bot_stop_message())
