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
from typing import Dict, List, Literal, Union

from ._type import FlagStatus, TrackStatus
from ._model import DiscordModel


def track_status_str(status: TrackStatus):
    if status == TrackStatus.ALL_CLEAR:
        return "All Clear"

    elif status == TrackStatus.YELLOW:
        return "Yellow"

    elif status == TrackStatus.GREEN:
        return "Green"

    elif status == TrackStatus.SC_DEPLOYED:
        return "Safety Car Deployed"

    elif status == TrackStatus.RED:
        return "Red"

    elif status == TrackStatus.VSC_DEPLOYED:
        return "Virtual Safety Car Deployed"

    elif status == TrackStatus.VSC_ENDING:
        return "Virtual Safety Car Ending"

    else:
        return "Unknown"


RaceControlMessageData = Dict[str, Union[str, int]]


def race_control_message_embed(
    msg_data: Dict[
        Literal["Messages"],
        Dict[str, RaceControlMessageData] | List[RaceControlMessageData],
    ],
    msg_dt: str,
):
    if isinstance(msg_data["Messages"], list):
        msg_data = msg_data["Messages"][0]

    else:
        msg_data = list(msg_data["Messages"].values())[0]

    if msg_data["Category"] == "Flag":
        flag_status: FlagStatus = msg_data["Flag"]

        if flag_status == FlagStatus.BLUE:
            color = 0x0000FF  # Blue

        elif flag_status == FlagStatus.CHEQUERED:
            color = 0x000000  # Black

        elif flag_status == FlagStatus.CLEAR:
            color = 0xFFFFFF  # White

        elif flag_status == FlagStatus.GREEN:
            color = 0x00FF00  # Green

        elif flag_status == FlagStatus.YELLOW:
            color = 0xFFFF00  # Yellow

        elif flag_status == FlagStatus.DOUBLE_YELLOW:
            color = 0xFFA500  # Orange

        elif flag_status == FlagStatus.RED:
            color = 0xFF0000  # Red

        else:
            raise ValueError(f"Unexpected flag status '{flag_status}'!")

    else:
        color = 0XA6EF1F  # Light Green

    fields = [
        DiscordModel.Embed.Field("Message", msg_data["Message"]),
        DiscordModel.Embed.Field("Category", msg_data["Category"]),
    ]

    if "Flag" in msg_data:
        fields.append(DiscordModel.Embed.Field("Flag", msg_data["Flag"]))

    if "Scope" in msg_data:
        fields.append(DiscordModel.Embed.Field("Scope", msg_data["Scope"]))

    if "RacingNumber" in msg_data:
        fields.append(
            DiscordModel.Embed.Field(
                "Driver Number",
                msg_data["RacingNumber"],
            ),
        )

    if "Sector" in msg_data:
        fields.append(
            DiscordModel.Embed.Field(
                "Track Sector",
                msg_data["Sector"],
            ),
        )

    if "Lap" in msg_data:
        fields.append(
            DiscordModel.Embed.Field(
                "Lap Number",
                str(msg_data["Lap"]),
            ),
        )

    if "Status" in msg_data and msg_data["Category"] == "Drs":
        fields.append(
            DiscordModel.Embed.Field(
                "DRS Status",
                msg_data["Status"],
            ),
        )

    return DiscordModel.Embed(
        title="Race Control Message",
        fields=fields,
        color=color,
        timestamp=dateutil.parser.parse(msg_dt),
    )
