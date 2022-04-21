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

from exfolt import (
    DiscordClient,
    DiscordModel,
    DiscordType,
    F1Client,
    Snowflake,
    WeatherTracker,
    extrapolated_clock_embed,
    race_control_message_embed,
    session_data_embed,
    session_info_embed,
    timing_data_embed,
    track_status_embed,
)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--bot-token")
    parser.add_argument("--channel-id", type=Snowflake)
    parser.add_argument("--webhook-token")
    parser.add_argument("--webhook-id", type=Snowflake)
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
                DiscordClient(
                    DiscordClient.BotAuthorization(bot_token),
                ).post_message(
                    channel_id,
                    **args,
                )

            if webhook_token and webhook_id:
                DiscordClient.post_webhook_message(
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
            tracker = WeatherTracker()

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
                            discord_message(
                                embed=[
                                    session_info_embed(
                                        msg_data[1],
                                        msg_data[2],
                                    ),
                                ],
                            )

                        elif msg_data[0] == "TrackStatus":
                            discord_message(
                                embeds=[
                                    track_status_embed(
                                        msg_data[1],
                                        msg_data[2],
                                    ),
                                ],
                            )

                        elif msg_data[0] == "SessionData":
                            discord_message(
                                embeds=[
                                    session_data_embed(
                                        msg_data[1],
                                        msg_data[2],
                                    ),
                                ],
                            )

                        elif msg_data[0] == "ExtrapolatedClock":
                            discord_message(
                                embeds=[
                                    extrapolated_clock_embed(
                                        msg_data[1],
                                        msg_data[2],
                                    ),
                                ],
                            )

                        elif msg_data[0] == "WeatherData":
                            tracker.update_data(msg_data[1])
                            embeds = tracker.notify_change_embed()

                            if embeds:
                                discord_message(embeds=embeds)

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
