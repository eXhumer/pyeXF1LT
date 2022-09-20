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

from argparse import ArgumentParser, Namespace
from logging import DEBUG, FileHandler, Formatter, getLogger, INFO, StreamHandler
from pathlib import Path
from typing import List
from pkg_resources import require

from ._client import F1ArchiveClient, F1LiveClient, F1LiveTimingClient
from ._type import StreamingTopic

try:
    exdc_available = True

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


def __message_logger(log_path: Path):
    file_handler = FileHandler(str(log_path.resolve()), mode="w")
    file_handler.setFormatter(Formatter("%(message)s"))
    logger = getLogger("message_logger")
    logger.addHandler(file_handler)
    logger.setLevel(INFO)
    return logger


def __parse_topics(args: Namespace):
    topics: List[StreamingTopic] = []

    if args.archive_status:
        topics.append(StreamingTopic.ARCHIVE_STATUS)

    if args.audio_streams:
        topics.append(StreamingTopic.AUDIO_STREAMS)

    if args.content_streams:
        topics.append(StreamingTopic.CONTENT_STREAMS)

    if args.current_tyres:
        topics.append(StreamingTopic.CURRENT_TYRES)

    if args.driver_list:
        topics.append(StreamingTopic.DRIVER_LIST)

    if args.driver_score:
        topics.append(StreamingTopic.DRIVER_SCORE)

    if args.extrapolated_clock:
        topics.append(StreamingTopic.EXTRAPOLATED_CLOCK)

    if args.lap_count:
        topics.append(StreamingTopic.LAP_COUNT)

    if args.lap_series:
        topics.append(StreamingTopic.LAP_SERIES)

    if args.pit_lane_time_collection:
        topics.append(StreamingTopic.PIT_LANE_TIME_COLLECTION)

    if args.race_control_messages:
        topics.append(StreamingTopic.RACE_CONTROL_MESSAGES)

    if args.session_data:
        topics.append(StreamingTopic.SESSION_DATA)

    if args.session_info:
        topics.append(StreamingTopic.SESSION_INFO)

    if args.session_status:
        topics.append(StreamingTopic.SESSION_STATUS)

    if args.team_radio:
        topics.append(StreamingTopic.TEAM_RADIO)

    if args.timing_app_data:
        topics.append(StreamingTopic.TIMING_APP_DATA)

    if args.timing_data:
        topics.append(StreamingTopic.TIMING_DATA)

    if args.timing_stats:
        topics.append(StreamingTopic.TIMING_STATS)

    if args.track_status:
        topics.append(StreamingTopic.TRACK_STATUS)

    if args.weather_data:
        topics.append(StreamingTopic.WEATHER_DATA)

    return topics


def __program_args():
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
    topics_parser.add_argument("--content-streams", action="store_true")
    topics_parser.add_argument("--current-tyres", action="store_true")
    topics_parser.add_argument("--driver-list", action="store_true")
    topics_parser.add_argument("--driver-score", action="store_true")
    topics_parser.add_argument("--extrapolated-clock", action="store_true")
    topics_parser.add_argument("--lap-count", action="store_true")
    topics_parser.add_argument("--lap-series", action="store_true")
    topics_parser.add_argument("--pit-lane-time-collection", action="store_true")
    topics_parser.add_argument("--race-control-messages", action="store_true")
    topics_parser.add_argument("--session-data", action="store_true")
    topics_parser.add_argument("--session-info", action="store_true")
    topics_parser.add_argument("--session-status", action="store_true")
    topics_parser.add_argument("--team-radio", action="store_true")
    topics_parser.add_argument("--timing-app-data", action="store_true")
    topics_parser.add_argument("--timing-data", action="store_true")
    topics_parser.add_argument("--timing-stats", action="store_true")
    topics_parser.add_argument("--track-status", action="store_true")
    topics_parser.add_argument("--weather-data", action="store_true")

    action_subparser = parser.add_subparsers(dest="action", title="actions", metavar="action",
                                             description="list of supported command line actions")

    archive_message_log_parser = action_subparser.add_parser(
        "archived-message-logger", help="log archived session messages to file",
        description="log archived session messages to file")
    archive_message_log_parser.add_argument(
        "archived_message_log_path", type=Path, help="file path to store logged messaged in")
    session_info_group = archive_message_log_parser.add_mutually_exclusive_group(required=True)
    session_info_group.add_argument("--by-path", help="retrieve archived session by path",
                                    type=str, dest="archive_path")
    session_info_group.add_argument(
        "--by-session-info", nargs=3, dest="archive_session_info", type=int,
        metavar=("YEAR", "MEETING_NUMBER", "SESSION_NUMBER"),
        help="retrieve archived session by year, meeting and session numbers")
    session_info_group.add_argument("--last-session", action="store_true",
                                    dest="archive_last_session",
                                    help="retrieve last archived session")

    live_message_log_parser = action_subparser.add_parser(
        "live-message-logger", help="log live session messages to file",
        description="log live session messages to file")
    live_message_log_parser.add_argument(
        "live_message_log_path", type=Path, help="file path to store logged messaged in")

    if exdc_available:
        live_discord_bot_parser = action_subparser.add_parser(
            "live-discord-bot", help="output incoming messages as Discord messages",
            description="output incoming messages as Discord messages")
        live_discord_bot_parser.add_argument(
            "--env-path", "-e", type=Path, default=Path.home().joinpath(".exfolt_discord_env"),
            help="file to load Discord environment variables from")

    return parser.parse_args()


def __program_logger(args: Namespace):
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

    if args.action == "archived-message-logger":
        message_logger = __message_logger(args.archived_message_log_path)
        logger.info("F1 Live Timing archived feed logger started!")

        if args.archive_path:
            logger.info(f"Retrieving archived feed by path ({args.archive_path})!")
            archive_client = F1ArchiveClient(args.archive_path, *topics)

        elif args.archive_session_info:
            logger.info("Retrieving archived feed by session information (Year: " +
                        f"{args.archive_session_info[0]}, Meeting: " +
                        f"{args.archive_session_info[1]}, Session: " +
                        f"{args.archive_session_info[2]})!")
            archive_client = F1ArchiveClient.get_by_session_info(*args.archive_session_info,
                                                                 *topics)

        elif args.archive_last_session:
            logger.info("Retrieving last archived feed!")
            archive_client = F1ArchiveClient.get_last_session(*topics)

        else:
            assert False, "Unreachable as one of the above condition is required!"

        for message in archive_client:
            logger.info("Logged session feed message!")
            message_logger.info([*message])

        logger.info("F1 Live Timing archived feed logger stopped!")

    if args.action == "live-message-logger":
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
                            message_logger.info(invokation["A"])

        except KeyboardInterrupt:
            logger.info("F1 Live Timing streaming feed logger stopped!")

    if exdc_available and args.action == "live-discord-bot":
        if live_streaming_status == "Offline":
            logger.warning("F1 Live Timing API Streaming Status: Offline!")

        try:
            with F1LiveTimingClient(*topics) as lt_client:
                logger.info("F1 Live Timing streaming feed Discord bot started!")

                for invokations in lt_client:
                    for invokation in invokations:
                        pass

        except KeyboardInterrupt:
            logger.info("F1 Live Timing streaming feed Discord bot stopped!")
