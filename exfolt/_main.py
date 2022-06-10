from argparse import ArgumentParser
from datetime import datetime, timezone
from json import dumps
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
from queue import Queue
from sys import stdout
from typing import List

from ._client import (
    AudioStreamData,
    ExtrapolatedClockData,
    F1LiveClient,
    RaceControlMessageData,
    SessionInfoData,
    TeamRadioData,
    TimingClient,
    TimingType,
    TrackStatusData,
)
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
    message_logger_parser.add_argument("--compact-output", action="store_true")

    if exdc_available:
        discord_bot_parser = subparsers.add_parser("discord-bot")
        discord_bot_parser.add_argument("--bot-token")
        discord_bot_parser.add_argument("--channel-id", type=Snowflake)
        discord_bot_parser.add_argument("--webhook-token")
        discord_bot_parser.add_argument("--webhook-id", type=Snowflake)
        discord_bot_parser.add_argument("--purple-segments", action="store_true")
        discord_bot_parser.add_argument("--disable-start-message", action="store_true")
        discord_bot_parser.add_argument("--disable-stop-message", action="store_true")

    args = parser.parse_args()

    if args.action == "message-logger":
        main_logger = getLogger("exfolt.message_logger")

    elif args.action == "discord-bot":
        main_logger = getLogger("exfolt.discord_bot")

    else:
        assert False

    main_logger.setLevel(DEBUG)
    live_client_logger = getLogger("exfolt.SRLiveClient")
    timing_client_logger = getLogger("exfolt.TimingClient")
    out_format = Formatter("[%(asctime)s][%(name)s][%(levelname)s]\t%(message)s")

    out_stream = StreamHandler(stdout)
    out_stream.setLevel(DEBUG)
    out_stream.setFormatter(out_format)

    timing_client_logger.addHandler(out_stream)
    live_client_logger.addHandler(out_stream)
    main_logger.addHandler(out_stream)

    if args.action == "message-logger":
        log_path: Path = args.log_file
        file_stream = FileHandler(log_path.resolve(), mode="a")
        file_stream.setLevel(INFO)
        file_stream.setFormatter(Formatter("%(message)s"))
        main_logger.addHandler(file_stream)

        try:
            with F1LiveClient() as live_client:
                for _, message in live_client:
                    if len(message) == 0:
                        main_logger.debug(f"keepalive packet received at {datetime.now()}!")
                        continue

                    if "M" in message and len(message["M"]) > 0:
                        main_logger.debug(f"Message received at {datetime.now()}!")
                        live_msg_data = message["M"][0]["A"]
                        dump_opts = {}

                        if args.compact_output:
                            dump_opts.update(separators=(',', ':'))

                        else:
                            dump_opts.update(indent=4, sort_keys=True)

                        main_logger.info(dumps(live_msg_data, **dump_opts))

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
                    Authorization = DiscordClient.BotAuthorization
                    return DiscordClient(Authorization(bot_token)).post_message(channel_id, **args)

                if webhook_token and webhook_id:
                    return DiscordClient.post_webhook_message(webhook_id,
                                                              webhook_token,
                                                              **args)

                assert False

            if not args.disable_start_message:
                discord_message(
                    embeds=[
                        DiscordModel.Embed(title="Live Timing Bot Started",
                                           timestamp=datetime.now(tz=timezone.utc)),
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

            timing_client = TimingClient()
            embed_queue: Queue[DiscordModel.Embed] = Queue()

            try:
                with F1LiveClient() as live_client:
                    for _, message in live_client:
                        if len(message) == 0:
                            main_logger.debug("keepalive packet received!")
                            continue

                        if "R" in message:
                            timing_client.process_old_data(message["R"])

                        if "M" in message and len(message["M"]) > 0:
                            main_logger.debug(f"Message received at {datetime.now()}!")
                            live_msg_data = message["M"][0]["A"]
                            timing_client.process_data(*live_msg_data)

                        for (topic, timing_item, timestamp) in timing_client:
                            if (
                                topic == TimingType.Topic.AUDIO_STREAMS and
                                isinstance(timing_item, AudioStreamData)
                            ):
                                embed_queue.put(
                                    DiscordModel.Embed(
                                        title="New Audio Stream Detected!",
                                        url=(
                                            "https://livetiming.formula1.com/static/" +
                                            timing_client.session_info.path +
                                            timing_item.path
                                        ),
                                        color=0x00FFFF,
                                        fields=[
                                            DiscordModel.Embed.Field("Name", timing_item.name),
                                            DiscordModel.Embed.Field("Language",
                                                                     timing_item.language),
                                        ],
                                        timestamp=datetime_string_parser(timestamp),
                                    ),
                                )

                            elif (
                                topic == TimingType.Topic.EXTRAPOLATED_CLOCK and
                                isinstance(timing_item, ExtrapolatedClockData)
                            ):
                                embed_queue.put(
                                    DiscordModel.Embed(
                                        title="Session Extrapolated Clock",
                                        fields=[
                                            DiscordModel.Embed.Field(
                                                "Remaining",
                                                timing_item.remaining,
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Extrapolating",
                                                str(timing_item.extrapolating),
                                            ),
                                        ],
                                        timestamp=datetime_string_parser(timestamp),
                                    ),
                                )

                            elif (
                                topic == TimingType.Topic.RACE_CONTROL_MESSAGES and
                                isinstance(timing_item, RaceControlMessageData)
                            ):
                                if timing_item.racing_number is not None:
                                    driver_data = timing_client.drivers[
                                        timing_item.racing_number
                                    ]

                                    author = DiscordModel.Embed.Author(
                                        str(driver_data),
                                        icon_url=driver_data.headshot_url,
                                    )

                                else:
                                    author = None

                                if timing_item.flag == TimingType.FlagStatus.BLACK:
                                    color = 0x000000
                                    description = "<:black:964569379264147556>"

                                elif timing_item.flag == TimingType.FlagStatus.BLACK_AND_ORANGE:
                                    color = 0xFFA500
                                    description = "<:blackorange:968388147148914688>"

                                elif timing_item.flag == TimingType.FlagStatus.BLACK_AND_ORANGE:
                                    color = 0xFFA500
                                    description = "<:blackwhite:968388147123728405>"

                                elif timing_item.flag == TimingType.FlagStatus.BLUE:
                                    color = 0x0000FF
                                    description = "<:blue:964569378999898143>"

                                elif timing_item.flag in (
                                    TimingType.FlagStatus.CHEQUERED,
                                    TimingType.FlagStatus.CLEAR,
                                ):
                                    color = 0xFFFFFF

                                    if timing_item.flag == TimingType.FlagStatus.CLEAR:
                                        description = "<:green:964569379205414932>"

                                    else:
                                        description = "<:chequered:964569378769235990>"

                                elif timing_item.flag == TimingType.FlagStatus.GREEN:
                                    color = 0x00FF00
                                    description = "<:green:964569379205414932>"

                                elif timing_item.flag == TimingType.FlagStatus.YELLOW:
                                    color = 0xFFFF00
                                    description = "<:yellow:964569379037671484>"

                                elif timing_item.flag == TimingType.FlagStatus.DOUBLE_YELLOW:
                                    color = 0xFFA500
                                    description = "".join((
                                        "<:yellow:964569379037671484>",
                                        "<:yellow:964569379037671484>",
                                    ))

                                elif timing_item.flag == TimingType.FlagStatus.RED:
                                    color = 0xFF0000
                                    description = "<:red:964569379234779136>"

                                else:
                                    color = 0XA6EF1F
                                    description = None

                                fields = [
                                    DiscordModel.Embed.Field("Message", timing_item.message),
                                    DiscordModel.Embed.Field("Category", timing_item.category),
                                ]

                                if timing_item.drs_status is not None:
                                    fields.append(
                                        DiscordModel.Embed.Field("DRS Status",
                                                                 timing_item.drs_status),
                                    )

                                if timing_item.flag is not None:
                                    fields.append(
                                        DiscordModel.Embed.Field("Flag", timing_item.flag),
                                    )

                                if timing_item.lap is not None:
                                    fields.append(
                                        DiscordModel.Embed.Field("Lap", timing_item.lap),
                                    )

                                if timing_item.scope is not None:
                                    fields.append(
                                        DiscordModel.Embed.Field("Scope", timing_item.scope),
                                    )

                                if timing_item.sector is not None:
                                    fields.append(
                                        DiscordModel.Embed.Field("Sector", timing_item.sector),
                                    )

                                embed_queue.put(
                                    DiscordModel.Embed(
                                        title="Race Control Message",
                                        author=author,
                                        color=color,
                                        description=description,
                                        fields=fields,
                                        timestamp=datetime_string_parser(timestamp),
                                    ),
                                )

                            elif (
                                topic == TimingType.Topic.SESSION_INFO and
                                isinstance(timing_item, SessionInfoData)
                            ):
                                embed_queue.put(
                                    DiscordModel.Embed(
                                        title="Session Information",
                                        fields=[
                                            DiscordModel.Embed.Field(
                                                "Official Name",
                                                timing_item.meeting["OfficialName"],
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Name",
                                                timing_item.meeting["Name"],
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Location",
                                                timing_item.meeting["Location"],
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Country",
                                                timing_item.meeting["Country"]["Name"],
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Circuit",
                                                timing_item.meeting["Circuit"]["ShortName"],
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
                                        timestamp=datetime_string_parser(timestamp),
                                        color=0xFFFFFF,
                                    ),
                                )

                            elif (
                                topic == TimingType.Topic.TEAM_RADIO and
                                isinstance(timing_item, TeamRadioData)
                            ):
                                driver_data = timing_client.drivers[timing_item.racing_number]

                                embed_queue.put(
                                    DiscordModel.Embed(
                                        title="New Team Radio Received!",
                                        author=DiscordModel.Embed.Author(
                                            str(driver_data),
                                            icon_url=driver_data.headshot_url,
                                        ),
                                        url=(
                                            "https://livetiming.formula1.com/static/" +
                                            timing_client.session_info.path +
                                            timing_item.path
                                        ),
                                        timestamp=datetime_string_parser(timestamp),
                                    ),
                                )

                            elif (
                                topic == TimingType.Topic.TRACK_STATUS and
                                isinstance(timing_item, TrackStatusData)
                            ):
                                embed_queue.put(
                                    DiscordModel.Embed(
                                        title="Track Status Changed!",
                                        fields=[
                                            DiscordModel.Embed.Field(
                                                "Status",
                                                timing_item.status_string,
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Message",
                                                timing_item.message,
                                            ),
                                        ],
                                        description=(
                                            "<:green:964569379205414932>"
                                            if timing_item.status in [
                                                TimingType.TrackStatus.ALL_CLEAR,
                                                TimingType.TrackStatus.GREEN,
                                                TimingType.TrackStatus.VSC_ENDING,
                                            ]
                                            else "<:yellow:964569379037671484>"
                                            if timing_item.status ==
                                            TimingType.TrackStatus.YELLOW
                                            else "<:sc:964569379163496538>"
                                            if timing_item.status ==
                                            TimingType.TrackStatus.SC_DEPLOYED
                                            else "<:vsc:964569379352244284>"
                                            if timing_item.status ==
                                            TimingType.TrackStatus.VSC_DEPLOYED
                                            else "<:red:964569379234779136>"
                                            if timing_item.status ==
                                            TimingType.TrackStatus.RED
                                            else None
                                        ),
                                        color=(
                                            0x00FF00
                                            if timing_item.status in [
                                                TimingType.TrackStatus.ALL_CLEAR,
                                                TimingType.TrackStatus.GREEN,
                                                TimingType.TrackStatus.VSC_ENDING,
                                            ]
                                            else 0xFFFF00
                                            if timing_item.status in [
                                                TimingType.TrackStatus.YELLOW,
                                                TimingType.TrackStatus.SC_DEPLOYED,
                                                TimingType.TrackStatus.VSC_DEPLOYED,
                                            ]
                                            else 0xFF0000
                                            if timing_item.status ==
                                            TimingType.TrackStatus.RED
                                            else None
                                        ),
                                        timestamp=datetime_string_parser(timestamp),
                                    ),
                                )

                        while embed_queue.qsize() > 0:
                            embeds: List[DiscordModel.Embed] = []

                            while embed_queue.qsize() > 0 and len(embeds) < 10:
                                embeds.append(embed_queue.get())

                            discord_message(embeds=embeds)

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
