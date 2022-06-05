from argparse import ArgumentParser
from datetime import datetime, timezone
from json import dumps
from logging import (
    FileHandler,
    Formatter,
    getLogger,
    INFO,
    StreamHandler,
)
from os import environ
from pathlib import Path
from sys import stdout

from ._client import F1LiveClient, SessionInfoData, TimingClient, TimingType
from ._utils import datetime_string_parser


try:
    from exdc import DiscordClient, DiscordModel, DiscordType, Snowflake
    exdc_available = True

except ImportError:
    exdc_available = False


def console_main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")

    message_logger_parser = subparsers.add_parser("message-logger")
    message_logger_parser.add_argument("log_file", type=Path)

    if exdc_available:
        discord_bot_parser = subparsers.add_parser("discord-bot")
        discord_bot_parser.add_argument("--bot-token")
        discord_bot_parser.add_argument("--channel-id", type=Snowflake)
        discord_bot_parser.add_argument("--webhook-token")
        discord_bot_parser.add_argument("--webhook-id", type=Snowflake)
        discord_bot_parser.add_argument("--purple-segments",
                                        action="store_true")
        discord_bot_parser.add_argument("--disable-start-message",
                                        action="store_true")
        discord_bot_parser.add_argument("--disable-stop-message",
                                        action="store_true")

    args = parser.parse_args()
    logger = getLogger(args.action)
    live_logger = getLogger("exfolt.SRLiveClient")
    timing_logger = getLogger("exfolt.TimingClient")
    logger.setLevel(INFO)
    out_format = Formatter(
        "[%(asctime)s][%(name)s][%(levelname)s]\t%(message)s",
        # "%d-%m-%Y %H:%M:%S",
    )

    out_stream = StreamHandler(stdout)
    out_stream.setLevel(INFO)
    out_stream.setFormatter(out_format)

    timing_logger.addHandler(out_stream)
    live_logger.addHandler(out_stream)
    logger.addHandler(out_stream)

    if args.action == "message-logger":
        log_path: Path = args.log_file
        file_stream = FileHandler(log_path.resolve(), mode="a")
        file_stream.setLevel(INFO)
        file_stream.setFormatter(out_format)

        timing_logger.addHandler(file_stream)
        live_logger.addHandler(file_stream)
        logger.addHandler(file_stream)

        try:
            with F1LiveClient() as exfolt_live_client:
                for live_msg in exfolt_live_client:
                    if len(live_msg[1]) == 0:
                        logger.info("keepalive packet received!")
                        continue

                    if "M" in live_msg[1] and len(live_msg[1]["M"]) > 0:
                        logger.info(f"Message received at {datetime.now()}!")
                        live_msg_data = live_msg[1]["M"][0]["A"]
                        logger.info(dumps(live_msg_data, indent=4))

        except KeyboardInterrupt:
            pass

    elif exdc_available and args.action == "discord-bot":
        bot_token = args.bot_token
        channel_id = str(args.channel_id) if args.channel_id else None
        webhook_token = args.webhook_token
        webhook_id = str(args.webhook_id) if args.webhook_id else None

        if not bot_token and "DISCORD_BOT_TOKEN" in environ:
            bot_token = environ["DISCORD_BOT_TOKEN"]

        if not channel_id and "DISCORD_CHANNEL_ID" in environ:
            channel_id = environ["DISCORD_CHANNEL_ID"]

        if not webhook_token and "DISCORD_WEBHOOK_TOKEN" in environ:
            webhook_token = environ["DISCORD_WEBHOOK_TOKEN"]

        if not webhook_id and "DISCORD_WEBHOOK_ID" in environ:
            webhook_id = environ["DISCORD_WEBHOOK_ID"]

        if (bot_token and channel_id) or (webhook_token and webhook_id):
            def discord_message(**args):
                if bot_token and channel_id:
                    return DiscordClient(
                        DiscordClient.BotAuthorization(bot_token),
                    ).post_message(
                        channel_id,
                        **args,
                    )

                if webhook_token and webhook_id:
                    return DiscordClient.post_webhook_message(
                        webhook_id,
                        webhook_token,
                        **args,
                    )

            if not args.disable_start_message:
                discord_message(
                    embeds=[
                        DiscordModel.Embed(
                            title="Live Timing Bot Started",
                            timestamp=datetime.now(tz=timezone.utc),
                        ),
                    ],
                    components=[
                        DiscordModel.ActionRowComponent([
                            DiscordModel.ButtonComponent(
                                DiscordType.ButtonStyle.LINK,
                                label="Source Code",
                                url="https://github.com/eXhumer/pyeXF1LT",
                            )
                        ])
                    ],
                )

            exfolt_timing_client = TimingClient()

            try:
                with F1LiveClient() as exfolt_live_client:
                    for live_msg in exfolt_live_client:
                        if len(live_msg[1]) == 0:
                            logger.info("keepalive packet received!")
                            continue

                        if "R" in live_msg[1]:
                            exfolt_timing_client.process_old_data(
                                live_msg[1]["R"],
                            )

                        if "M" in live_msg[1] and len(live_msg[1]["M"]) > 0:
                            logger.info("Message received at " +
                                        f"{datetime.now()}!")
                            live_msg_data = live_msg[1]["M"][0]["A"]
                            exfolt_timing_client.process_data(*live_msg_data)

                        for (
                            topic,
                            timing_item,
                            timestamp,
                        ) in exfolt_timing_client:
                            if (
                                topic == TimingType.Topic.SESSION_INFO and
                                isinstance(timing_item, SessionInfoData)
                            ):
                                discord_message(
                                    embeds=[
                                        DiscordModel.Embed(
                                            title="Session Information",
                                            fields=[
                                                DiscordModel.Embed.Field(
                                                    "Official Name",
                                                    timing_item.meeting[
                                                        "OfficialName"
                                                    ],
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "Name",
                                                    timing_item.meeting[
                                                        "Name"
                                                    ],
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "Location",
                                                    timing_item.meeting[
                                                        "Location"
                                                    ],
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "Country",
                                                    timing_item.meeting[
                                                        "Country"
                                                    ]["Name"],
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "Circuit",
                                                    timing_item.meeting[
                                                        "Circuit"
                                                    ]["ShortName"],
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "Type",
                                                    timing_item.type,
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "Start Date",
                                                    timing_item.start_date,
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "End Date",
                                                    timing_item.end_date,
                                                ),
                                                DiscordModel.Embed.Field(
                                                    "GMT Offset",
                                                    timing_item.gmt_offset,
                                                ),
                                            ],
                                            timestamp=datetime_string_parser(
                                                timestamp,
                                            ),
                                            color=0xFFFFFF,
                                        ),
                                    ],
                                )

            except KeyboardInterrupt:
                if not args.disable_stop_message:
                    discord_message(
                        embeds=[
                            DiscordModel.Embed(
                                title="Live Timing Bot Stopped",
                                timestamp=datetime.now(tz=timezone.utc),
                            ),
                        ],
                        components=[
                            DiscordModel.ActionRowComponent([
                                DiscordModel.ButtonComponent(
                                    DiscordType.ButtonStyle.LINK,
                                    label="Source Code",
                                    url="https://github.com/eXhumer/pyeXF1LT",
                                )
                            ])
                        ],
                    )
