# pyeXF1LT - Unofficial F1 live timing clients
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
from enum import Enum

from exfolt import F1Client, DiscordClient, DiscordModel, DiscordType


class __TrackStatus(str, Enum):
    ALL_CLEAR = "1"
    YELLOW = "2"
    GREEN = "3"
    SC_DEPLOYED = "4"
    RED = "5"
    VSC_DEPLOYED = "6"
    VSC_ENDING = "7"


def __track_status_str(status: __TrackStatus):
    if status == __TrackStatus.ALL_CLEAR:
        return "All Clear"

    elif status == __TrackStatus.YELLOW:
        return "Yellow"

    elif status == __TrackStatus.GREEN:
        return "Green"

    elif status == __TrackStatus.SC_DEPLOYED:
        return "Safety Car Deployed"

    elif status == __TrackStatus.RED:
        return "Red"

    elif status == __TrackStatus.VSC_DEPLOYED:
        return "Virtual Safety Car Deployed"

    elif status == __TrackStatus.VSC_ENDING:
        return "Virtual Safety Car Ending"

    else:
        return "Unknown"


if __name__ == "__main__":
    if "DISCORD_WEBHOOK_ID" not in os.environ:
        raise RuntimeError("No Discord webhook ID specified!")

    if "DISCORD_WEBHOOK_TOKEN" not in os.environ:
        raise RuntimeError("No Discord webhook token specified!")

    def discord_webhook_message(**args):
        return DiscordClient.post_webhook_message(
            os.environ["DISCORD_WEBHOOK_ID"],
            os.environ["DISCORD_WEBHOOK_TOKEN"],
            **args,
        )

    discord_webhook_message(
        embeds=[
            DiscordModel.Embed(
                title="Live Timing Bot Started",
                url="https://github.com/eXhumer/pyeXF1LT",
                timestamp=datetime.now(tz=timezone.utc),
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
                        if type(msg_data[1]["Messages"]) == list:
                            rc_data = msg_data[1]["Messages"][0]

                        else:
                            rc_data = list(msg_data[1]["Messages"].values())[0]

                        discord_webhook_message(
                            embeds=[
                                DiscordModel.Embed(
                                    title="Race Control Message",
                                    description=rc_data["Message"],
                                    type=DiscordType.Embed.RICH,
                                    timestamp=dateutil.parser.parse(
                                        msg_data[2],
                                    ),
                                    footer=DiscordModel.Embed.Footer(
                                        f"Category: {rc_data['Category']}",
                                    ),
                                ),
                            ],
                        )

                    elif msg_data[0] == "SessionInfo":
                        sc_info = msg_data[1]

                        discord_webhook_message(
                            embeds=[
                                DiscordModel.Embed(
                                    title="Session Information",
                                    description="\n".join((
                                        "Official Name: " +
                                        sc_info['Meeting']['OfficialName'],
                                        "Location: " +
                                        sc_info['Meeting']['Location'],
                                        "Country: " +
                                        sc_info['Meeting']['Country']['Name'],
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
                        weather_data = msg_data[1]

                        discord_webhook_message(
                            embeds=[
                                DiscordModel.Embed(
                                    title="Weather Information",
                                    description="\n".join((
                                        "Air Temperature: " +
                                        weather_data['AirTemp'],
                                        "Track Temperature: " +
                                        weather_data['TrackTemp'],
                                        "Humidity: " +
                                        weather_data['Humidity'],
                                        "Pressure: " +
                                        weather_data['Pressure'],
                                        "Rainfall: " +
                                        weather_data['Rainfall'],
                                        "Wind Direction: " +
                                        weather_data['WindDirection'],
                                        "Wind Speed: " +
                                        weather_data['WindSpeed'],
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
                        status_str = __track_status_str(track_status['Status'])

                        discord_webhook_message(
                            embeds=[
                                DiscordModel.Embed(
                                    title="Track Status",
                                    description="\n".join((
                                        "Status: " +
                                        track_status['Status'] +
                                        f"({status_str})",
                                        "Message: " +
                                        track_status['Message'],
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

                            discord_webhook_message(
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

                        discord_webhook_message(
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
        discord_webhook_message(
            embeds=[
                DiscordModel.Embed(
                    title="Live Timing Bot Stopped",
                    url="https://github.com/eXhumer/pyeXF1LT",
                    timestamp=datetime.now(tz=timezone.utc),
                ),
            ],
        )
