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

import dateutil.parser
import os
from datetime import datetime, timezone

from exfolt import (
    DiscordClient,
    DiscordModel,
    DiscordType,
    F1Client,
    race_control_message_embed,
    track_status_str,
)


if __name__ == "__main__":
    if "DISCORD_BOT_TOKEN" not in os.environ:
        raise RuntimeError("No Discord bot token specified!")

    if "DISCORD_CHANNEL_ID" not in os.environ:
        raise RuntimeError("No Discord channel specified!")

    discord = DiscordClient(
        DiscordClient.BotAuthorization(os.environ["DISCORD_BOT_TOKEN"]),
    )

    def discord_message(**args):
        return discord.post_message(
            os.environ["DISCORD_CHANNEL_ID"],
            **args
        )

    discord_message(
        embeds=[
            DiscordModel.Embed(
                title="Live Timing Bot Started",
                url="https://github.com/eXhumer/pyeXF1LT",
                timestamp=datetime.now(tz=timezone.utc),
                author=DiscordModel.Embed.Author("eXhumer"),
            ),
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
                                race_control_message_embed(msg_data),
                            ],
                        )

                    elif msg_data[0] == "SessionInfo":
                        sc_info = msg_data[1]

                        discord_message(
                            embeds=[
                                DiscordModel.Embed(
                                    title="Session Information",
                                    description="\n".join((
                                        "Official Name: " +
                                        sc_info["Meeting"]["OfficialName"],
                                        "Location: " +
                                        sc_info["Meeting"]["Location"],
                                        "Country: " +
                                        sc_info["Meeting"]["Country"]["Name"],
                                        f"Type: {sc_info['Type']}",
                                    )),
                                    type=DiscordType.Embed.RICH,
                                    timestamp=dateutil.parser.parse(
                                        msg_data[2],
                                    ),
                                ),
                            ],
                        )

                    elif msg_data[0] == "WeatherData":
                        pass
                        weather_data = msg_data[1]

                        discord_message(
                            embeds=[
                                DiscordModel.Embed(
                                    title="Weather Information",
                                    description="\n".join((
                                        "Air Temperature: " +
                                        weather_data["AirTemp"],
                                        "Track Temperature: " +
                                        weather_data["TrackTemp"],
                                        "Humidity: " +
                                        weather_data["Humidity"],
                                        "Pressure: " +
                                        weather_data["Pressure"],
                                        "Rainfall: " +
                                        weather_data["Rainfall"],
                                        "Wind Direction: " +
                                        weather_data["WindDirection"],
                                        "Wind Speed: " +
                                        weather_data["WindSpeed"],
                                    )),
                                    type=DiscordType.Embed.RICH,
                                    timestamp=dateutil.parser.parse(
                                        msg_data[2],
                                    ),
                                ),
                            ],
                        )

                    elif msg_data[0] == "TrackStatus":
                        track_status = msg_data[1]
                        status_str = track_status_str(track_status["Status"])

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
                                series_status = msg_data[1]["StatusSeries"][0]

                            else:
                                series_status = list(
                                    msg_data[1]["StatusSeries"].values())[0]

                            discord_message(
                                embeds=[
                                    DiscordModel.Embed(
                                        title="Session Data",
                                        description="\n".join((
                                            ("Track Status: " +
                                             series_status["TrackStatus"])
                                            if "TrackStatus" in series_status
                                            else (
                                                "Session Status: " +
                                                series_status["SessionStatus"]
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
                        embed_desc = f"Remaining: {clock_data['Remaining']}"

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
                        pass

                    else:
                        print(msg_data)

    except KeyboardInterrupt:
        discord_message(
            embeds=[
                DiscordModel.Embed(
                    title="Live Timing Bot Stopped",
                    url="https://github.com/eXhumer/pyeXF1LT",
                    timestamp=datetime.now(tz=timezone.utc),
                ),
            ],
        )
