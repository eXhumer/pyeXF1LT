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

from argparse import ArgumentParser
from datetime import datetime, timezone
from os import environ
from queue import Queue

from exdc import (
    DiscordClient,
    DiscordModel,
    DiscordType,
    Snowflake,
)
from exfolt import (
    F1Client,
    FlagStatus,
    RateLimiter,
    TimingDataStatus,
    TrackStatus,
    WeatherDataChange,
    WeatherTracker,
    datetime_string_parser,
    extrapolated_clock_parser,
    race_control_message_data_parser,
    session_data_parser,
    session_info_parser,
    timing_data_parser,
    track_status_parser,
)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--bot-token")
    parser.add_argument("--channel-id", type=Snowflake)
    parser.add_argument("--webhook-token")
    parser.add_argument("--webhook-id", type=Snowflake)
    parser.add_argument("--purple-segments", action="store_true")
    parser.add_argument("--disable-start-message", action="store_true")
    parser.add_argument("--disable-stop-message", action="store_true")
    args = parser.parse_args()

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

    if (
        bot_token and channel_id
    ) or (
        webhook_token and webhook_id
    ):
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

            else:
                assert False

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

        try:
            tracker = WeatherTracker()
            rate_limiter = RateLimiter()
            msg_q = Queue()

            with F1Client() as exfolt:
                for msg in exfolt:
                    print(
                        "Message Received at " +
                        str(datetime.now(tz=timezone.utc)) +
                        "!"
                    )

                    if "C" in msg:
                        msg_data = msg["M"][0]["A"]

                        if msg_data[0] == "RaceControlMessages":
                            rcm_data = race_control_message_data_parser(
                                msg_data[1],
                            )

                            color = 0XA6EF1F
                            description = None
                            fields = [
                                DiscordModel.Embed.Field(
                                    "Message",
                                    rcm_data.message,
                                ),
                                DiscordModel.Embed.Field(
                                    "Category",
                                    rcm_data.category,
                                ),
                            ]

                            if rcm_data.drs_status:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "DRS Status",
                                        rcm_data.drs_status,
                                    )
                                )

                            if rcm_data.flag:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Flag",
                                        rcm_data.flag,
                                    )
                                )

                                if rcm_data.flag == FlagStatus.BLUE:
                                    color = 0x0000FF  # Blue
                                    description = "<:blue:964569378999898143>"

                                elif rcm_data.flag == FlagStatus.BLACK:
                                    color = 0x000000  # Black
                                    description = "<:black:964569379264147556>"

                                elif rcm_data.flag == \
                                        FlagStatus.BLACK_AND_ORANGE:
                                    color = 0xFFA500  # Orange
                                    description = \
                                        "<:blackorange:968388147148914688>"

                                elif rcm_data.flag == \
                                        FlagStatus.BLACK_AND_WHITE:
                                    color = 0xFFA500  # Orange
                                    description = \
                                        "<:blackwhite:968388147123728405>"

                                elif rcm_data.flag in [
                                    FlagStatus.CLEAR, FlagStatus.CHEQUERED,
                                ]:
                                    color = 0xFFFFFF  # White

                                    if rcm_data.flag == FlagStatus.CLEAR:
                                        description = \
                                            "<:green:964569379205414932>"

                                    else:
                                        description = \
                                            "<:chequered:964569378769235990>"

                                elif rcm_data.flag == FlagStatus.GREEN:
                                    description = "<:green:964569379205414932>"
                                    color = 0x00FF00  # Green

                                elif rcm_data.flag == FlagStatus.YELLOW:
                                    description = \
                                        "<:yellow:964569379037671484>"
                                    color = 0xFFFF00  # Yellow

                                elif rcm_data.flag == FlagStatus.DOUBLE_YELLOW:
                                    description = "".join((
                                        "<:yellow:964569379037671484>",
                                        "<:yellow:964569379037671484>",
                                    ))
                                    color = 0xFFA500  # Orange

                                elif rcm_data.flag == FlagStatus.RED:
                                    description = "<:red:964569379234779136>"
                                    color = 0xFF0000  # Red

                                else:
                                    raise ValueError(
                                        "Unexpected flag status '" +
                                        f"{rcm_data.flag}'!"
                                    )

                            if rcm_data.lap:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Lap",
                                        rcm_data.lap,
                                    )
                                )

                            if rcm_data.scope:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Scope",
                                        rcm_data.scope,
                                    )
                                )

                            if rcm_data.sector:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Sector",
                                        rcm_data.sector,
                                    )
                                )

                            if rcm_data.racing_number:
                                driver_data = exfolt.driver_data(
                                    rcm_data.racing_number,
                                )
                                author = DiscordModel.Embed.Author(
                                    str(driver_data),
                                    icon_url=driver_data.headshot_url,
                                )

                            else:
                                author = None

                            embed = DiscordModel.Embed(
                                title="Race Control Message",
                                author=author,
                                color=color,
                                description=description,
                                fields=fields,
                                timestamp=datetime_string_parser(msg_data[2]),
                            )

                            msg_q.put(embed)

                        elif msg_data[0] == "TimingData":
                            timing_data = timing_data_parser(msg_data[1])

                            if timing_data:
                                if (
                                    timing_data.segment_status ==
                                    TimingDataStatus.PURPLE and
                                    not args.purple_segments
                                ):
                                    continue

                                if timing_data.segment_status in [
                                    TimingDataStatus.PURPLE,
                                    TimingDataStatus.STOPPED,
                                    TimingDataStatus.PITTED,
                                    TimingDataStatus.PIT_ISSUE,
                                ]:
                                    if timing_data.segment_status == \
                                            TimingDataStatus.PURPLE:
                                        color = 0xA020F0

                                    elif timing_data.segment_status in [
                                        TimingDataStatus.STOPPED,
                                        TimingDataStatus.PIT_ISSUE,
                                    ]:
                                        color = 0xFFFF00

                                    else:
                                        color = None

                                    if timing_data.racing_number:
                                        driver_data = exfolt.driver_data(
                                            timing_data.racing_number,
                                        )
                                        author = DiscordModel.Embed.Author(
                                            str(driver_data),
                                            icon_url=driver_data.headshot_url,
                                        )

                                    else:
                                        author = None

                                    embed = DiscordModel.Embed(
                                        title="Timing Data",
                                        author=author,
                                        fields=[
                                            DiscordModel.Embed.Field(
                                                "Sector",
                                                timing_data.sector_number,
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Segment",
                                                timing_data.segment_number,
                                            ),
                                            DiscordModel.Embed.Field(
                                                "Status",
                                                (
                                                    "Purple"
                                                    if timing_data.
                                                    segment_status
                                                    == TimingDataStatus.PURPLE
                                                    else "Pitted"
                                                    if timing_data.
                                                    segment_status
                                                    == TimingDataStatus.PITTED
                                                    else "Pit issues"
                                                    if timing_data.
                                                    segment_status
                                                    ==
                                                    TimingDataStatus.PIT_ISSUE
                                                    else "Stopped"
                                                ),
                                            ),
                                        ],
                                        color=color,
                                        timestamp=datetime_string_parser(
                                            msg_data[2],
                                        ),
                                    )

                                    msg_q.put(embed)

                        elif msg_data[0] == "SessionInfo":
                            session_data = session_info_parser(msg_data[1])

                            embed = DiscordModel.Embed(
                                title="Session Information",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Official Name",
                                        session_data.official_name,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Name",
                                        session_data.name,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Location",
                                        session_data.location,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Country",
                                        session_data.country,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Circuit",
                                        session_data.circuit,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Type",
                                        session_data.type,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Start Date",
                                        session_data.start_date,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "End Date",
                                        session_data.end_date,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "GMT Offset",
                                        session_data.gmt_offset,
                                    ),
                                ],
                                timestamp=datetime_string_parser(msg_data[2]),
                                color=0xFFFFFF,
                            )

                            msg_q.put(embed)

                        elif msg_data[0] == "TrackStatus":
                            track_status = track_status_parser(msg_data[1])

                            embed = DiscordModel.Embed(
                                title="Track Status",
                                fields=[
                                    DiscordModel.Embed.Field(
                                        "Status",
                                        track_status.status,
                                    ),
                                    DiscordModel.Embed.Field(
                                        "Message",
                                        track_status.message,
                                    ),
                                ],
                                description=(
                                    "<:green:964569379205414932>"
                                    if track_status.status in [
                                        TrackStatus.ALL_CLEAR,
                                        TrackStatus.GREEN,
                                        TrackStatus.VSC_ENDING,
                                    ]
                                    else "<:yellow:964569379037671484>"
                                    if track_status.status
                                    in TrackStatus.YELLOW
                                    else "<:sc:964569379163496538>"
                                    if track_status.status
                                    in TrackStatus.SC_DEPLOYED
                                    else "<:vsc:964569379352244284>"
                                    if track_status.status
                                    in TrackStatus.VSC_DEPLOYED
                                    else "<:red:964569379234779136>"
                                    if track_status.status
                                    in TrackStatus.RED
                                    else None
                                ),
                                color=(
                                    0x00FF00
                                    if track_status.status in [
                                        TrackStatus.ALL_CLEAR,
                                        TrackStatus.GREEN,
                                        TrackStatus.VSC_ENDING,
                                    ]
                                    else 0xFFFF00
                                    if track_status.status in [
                                        TrackStatus.YELLOW,
                                        TrackStatus.SC_DEPLOYED,
                                        TrackStatus.VSC_DEPLOYED,
                                    ]
                                    else 0xFF0000
                                    if track_status.status == TrackStatus.RED
                                    else None
                                ),
                                timestamp=datetime_string_parser(msg_data[2]),
                            )

                            msg_q.put(embed)

                        elif msg_data[0] == "SessionData":
                            session_data = session_data_parser(msg_data[1])

                            fields = []

                            if session_data.track_status:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Track Status",
                                        session_data.track_status,
                                    ),
                                )

                            if session_data.lap:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Lap",
                                        session_data.lap,
                                    ),
                                )

                            if session_data.qualifying_part:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Qualifying Part",
                                        session_data.qualifying_part,
                                    ),
                                )

                            if session_data.session_status:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Session Status",
                                        session_data.session_status,
                                    ),
                                )

                            embed = DiscordModel.Embed(
                                title="Session Data",
                                fields=fields,
                                timestamp=datetime_string_parser(msg_data[2]),
                            )

                            msg_q.put(embed)

                        elif msg_data[0] == "ExtrapolatedClock":
                            clock_data = extrapolated_clock_parser(msg_data[1])

                            fields = [
                                DiscordModel.Embed.Field(
                                    "Remaining",
                                    clock_data.remaining,
                                ),
                            ]

                            if clock_data.extrapolating is not None:
                                fields.append(
                                    DiscordModel.Embed.Field(
                                        "Extrapolating",
                                        str(clock_data.extrapolating),
                                    )
                                )

                            embed = DiscordModel.Embed(
                                title="Extrapolated Clock",
                                fields=fields,
                                timestamp=datetime_string_parser(msg_data[2]),
                            )

                            msg_q.put(embed)

                        elif msg_data[0] == "WeatherData":
                            tracker.update_data(msg_data[1])
                            changes = tracker.notify_changes()

                            if type(changes) == list:
                                for change in changes:
                                    change: WeatherDataChange

                                    fields = []

                                    if change.change:
                                        fields.append(
                                            DiscordModel.Embed.Field(
                                                "Change",
                                                f"{change.change}"
                                            )
                                        )

                                    if change.new:
                                        fields.append(
                                            DiscordModel.Embed.Field(
                                                "New",
                                                f"{change.new}"
                                            )
                                        )

                                    if change.previous:
                                        fields.append(
                                            DiscordModel.Embed.Field(
                                                "Previous",
                                                f"{change.previous}"
                                            )
                                        )

                                    embed = DiscordModel.Embed(
                                        title=change.title,
                                        timestamp=datetime.now(
                                            tz=timezone.utc,
                                        ),
                                        fields=fields,
                                    )

                                    msg_q.put(embed)

                            else:
                                ts = "Wet" if changes.rainfall else "Dry"
                                embed = DiscordModel.Embed(
                                    title="Initial Weather Information",
                                    fields=[
                                        DiscordModel.Embed.Field(
                                            "Air Temperature (Celsius)",
                                            f"{changes.airtemp}",
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Track Temperature (Celsius)",
                                            f"{changes.tracktemp}",
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Humidity (%)",
                                            f"{changes.humidity}",
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Pressure (mbar)",
                                            f"{changes.pressure}",
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Track Status (Wet / Dry)",
                                            ts,
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Wind Direction (Degree)",
                                            f"{changes.winddirection}",
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Wind Speed",
                                            f"{changes.windspeed}",
                                        ),
                                    ],
                                    timestamp=datetime.now(tz=timezone.utc),
                                )
                                msg_q.put(embed)

                        else:
                            print(msg_data)

                    if not msg_q.empty():
                        if rate_limiter.remaining is not None:
                            assert rate_limiter.reset and rate_limiter.limit

                            if (
                                rate_limiter.remaining == 0
                            ) and (
                                rate_limiter.reset >
                                datetime.utcnow().replace(timezone.utc)
                            ):  # Rate Limited
                                print(
                                    "\n".join((
                                        "Rate Limited!",
                                        f"Limit: {rate_limiter.limit}",
                                        f"Remaining: {rate_limiter.remaining}",
                                        f"Reset: {rate_limiter.reset}",
                                    ))
                                )
                                continue

                        embeds = []

                        for _ in range(min(len(msg_q), 10)):
                            embeds.append(msg_q.get())

                        res = discord_message(embeds=embeds)
                        rate_limiter.update_limit(**res.headers)

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
