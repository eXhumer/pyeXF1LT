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

import argparse
import dateutil.parser
import os
from datetime import datetime, timezone

from exfolt import (
    DiscordClient,
    DiscordModel,
    DiscordType,
    F1Client,
    Snowflake,
    race_control_message_embed,
    timing_data_embed,
    track_status_str,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot-token")
    parser.add_argument("--channel-id", type=Snowflake)
    parser.add_argument("--webhook-token")
    parser.add_argument("--webhook-id", type=Snowflake)
    args = parser.parse_args()

    bot_token = args.bot_token
    channel_id = str(args.channel_id) if args.channel_id else None
    webhook_token = args.webhook_token
    webhook_id = str(args.webhook_id) if args.webhook_id else None

    if not bot_token and "DISCORD_BOT_TOKEN" in os.environ:
        bot_token = os.environ["DISCORD_BOT_TOKEN"]

    if not channel_id and "DISCORD_CHANNEL_ID" in os.environ:
        channel_id = os.environ["DISCORD_CHANNEL_ID"]

    if not webhook_token and "DISCORD_WEBHOOK_TOKEN" in os.environ:
        webhook_token = os.environ["DISCORD_WEBHOOK_TOKEN"]

    if not webhook_id and "DISCORD_WEBHOOK_ID" in os.environ:
        webhook_id = os.environ["DISCORD_WEBHOOK_ID"]

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

            else:
                return DiscordClient.post_webhook_message(
                    webhook_id,
                    webhook_token,
                    **args,
                )

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
            with F1Client() as exfolt:
                for msg in exfolt:
                    print(f"Message Received at {datetime.now()}!")

                    if "C" in msg:
                        msg_data = msg["M"][0]["A"]

                        if msg_data[0] == "RaceControlMessages":
                            discord_message(
                                embeds=[
                                    race_control_message_embed(
                                        msg_data[1],
                                        msg_data[2],
                                    ),
                                ],
                            )

                        elif msg_data[0] == "TimingData":
                            embed = timing_data_embed(
                                msg_data[1],
                                msg_data[2],
                            )

                            if embed:
                                discord_message(embeds=[embed])

                        elif msg_data[0] == "SessionInfo":
                            print(msg_data)
                            # sc_info = msg_data[1]

                            # discord_message(
                            #     embeds=[
                            #         DiscordModel.Embed(
                            #             title="Session Information",
                            #             description="\n".join((
                            #                 "Official Name: " +
                            #                 sc_info["Meeting"]["OfficialName"],
                            #                 "Location: " +
                            #                 sc_info["Meeting"]["Location"],
                            #                 "Country: " +
                            #                 sc_info["Meeting"]["Country"]["Name"],
                            #                 f"Type: {sc_info['Type']}",
                            #             )),
                            #             type=DiscordType.Embed.RICH,
                            #             timestamp=dateutil.parser.parse(
                            #                 msg_data[2],
                            #             ),
                            #         ),
                            #     ],
                            # )

                        elif msg_data[0] == "WeatherData":
                            print(msg_data)
                            # weather_data = msg_data[1]

                            # discord_message(
                            #     embeds=[
                            #         DiscordModel.Embed(
                            #             title="Weather Information",
                            #             description="\n".join((
                            #                 "Air Temperature: " +
                            #                 weather_data["AirTemp"],
                            #                 "Track Temperature: " +
                            #                 weather_data["TrackTemp"],
                            #                 "Humidity: " +
                            #                 weather_data["Humidity"],
                            #                 "Pressure: " +
                            #                 weather_data["Pressure"],
                            #                 "Rainfall: " +
                            #                 weather_data["Rainfall"],
                            #                 "Wind Direction: " +
                            #                 weather_data["WindDirection"],
                            #                 "Wind Speed: " +
                            #                 weather_data["WindSpeed"],
                            #             )),
                            #             type=DiscordType.Embed.RICH,
                            #             timestamp=dateutil.parser.parse(
                            #                 msg_data[2],
                            #             ),
                            #         ),
                            #     ],
                            # )

                        elif msg_data[0] == "TrackStatus":
                            track_status = msg_data[1]
                            status_str = track_status_str(
                                track_status["Status"],
                            )

                            discord_message(
                                embeds=[
                                    DiscordModel.Embed(
                                        title="Track Status",
                                        description="\n".join((
                                            "Status: " +
                                            track_status["Status"] +
                                            f"({status_str})",
                                            "Message: " +
                                            track_status["Message"],
                                        )),
                                        type=DiscordType.Embed.RICH,
                                        timestamp=dateutil.parser.parse(
                                            msg_data[2],
                                        ),
                                    ),
                                ],
                            )

                        elif msg_data[0] == "SessionData":
                            if "StatusSeries" in msg_data[1]:
                                if type(msg_data[1]["StatusSeries"]) == list:
                                    series_status = msg_data[1][
                                        "StatusSeries"
                                    ][0]

                                else:
                                    series_status = list(
                                        msg_data[1][
                                            "StatusSeries"
                                        ].values())[0]

                                discord_message(
                                    embeds=[
                                        DiscordModel.Embed(
                                            title="Session Data",
                                            description="\n".join((
                                                ("Track Status: " +
                                                 series_status["TrackStatus"])
                                                if "TrackStatus"
                                                in series_status
                                                else (
                                                    "Session Status: " +
                                                    series_status[
                                                        "SessionStatus"
                                                    ]
                                                ),
                                            )),
                                            type=DiscordType.Embed.RICH,
                                            timestamp=dateutil.parser.parse(
                                                msg_data[2],
                                            ),
                                        ),
                                    ],
                                )

                        elif msg_data[0] == "ExtrapolatedClock":
                            clock_data = msg_data[1]
                            embed_desc = "Remaining: " + \
                                clock_data["Remaining"]

                            if "Extrapolating" in clock_data:
                                embed_desc += "".join((
                                    "\nExtrapolating: ",
                                    clock_data["Extrapolating"],
                                ))

                            discord_message(
                                embeds=[
                                    DiscordModel.Embed(
                                        title="Extrapolated Clock",
                                        description=embed_desc,
                                        type=DiscordType.Embed.RICH,
                                        timestamp=dateutil.parser.parse(
                                            msg_data[2],
                                        ),
                                    ),
                                ],
                            )

                        elif msg_data[0] == "Heartbeat":
                            print(msg_data)

                        else:
                            print(msg_data)

        except KeyboardInterrupt:
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
