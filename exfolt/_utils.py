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

from ._type import FlagStatus, TimingDataStatus, TrackStatus
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

    description = None

    if msg_data["Category"] == "Flag":
        flag_status: FlagStatus = msg_data["Flag"]

        if flag_status == FlagStatus.BLUE:
            color = 0x0000FF  # Blue
            description = "<:blue:964569378999898143>"

        elif flag_status == FlagStatus.CHEQUERED:
            color = 0x000000  # Black
            description = "<:chequered:964569378769235990>"

        elif flag_status == FlagStatus.CLEAR:
            color = 0xFFFFFF  # White
            description = "<:green:964569379205414932>"

        elif flag_status == FlagStatus.GREEN:
            description = "<:green:964569379205414932>"
            color = 0x00FF00  # Green

        elif flag_status == FlagStatus.YELLOW:
            description = "<:yellow:964569379037671484>"
            color = 0xFFFF00  # Yellow

        elif flag_status == FlagStatus.DOUBLE_YELLOW:
            description = "".join((
                "<:yellow:964569379037671484>",
                "<:yellow:964569379037671484>",
            ))
            color = 0xFFA500  # Orange

        elif flag_status == FlagStatus.RED:
            description = "<:red:964569379234779136>"
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
        description=description,
        fields=fields,
        color=color,
        timestamp=dateutil.parser.parse(msg_dt),
    )


TimingData = Dict[
    Literal["Lines"],
    Dict[
        str,
        Dict[
            Literal["Sectors"],
            Dict[
                str,
                Dict[
                    Literal["Segments"],
                    Dict[
                        str,
                        Dict[
                            Literal["Status"],
                            int,
                        ],
                    ],
                ],
            ],
        ],
    ],
]


def timing_data_embed(
    msg_data: TimingData,
    msg_dt: str,
):
    if "Lines" in msg_data and len(msg_data["Lines"]) == 1:
        for drv_num, drv_data in msg_data["Lines"].items():
            if "Sectors" in drv_data and len(drv_data["Sectors"]) == 1:
                for sector_num, sector_data in drv_data["Sectors"].items():
                    if (
                        "Segments" in sector_data and
                        len(sector_data["Segments"]) == 1
                    ):
                        for (
                            segment_num,
                            segment_data,
                        ) in sector_data["Segments"].items():
                            if (
                                "Status" in segment_data and
                                segment_data["Status"] in [
                                    TimingDataStatus.PURPLE,
                                    TimingDataStatus.STOPPED,
                                    TimingDataStatus.PITTED,
                                    TimingDataStatus.PIT_ISSUE,
                                ]
                            ):
                                color = None

                                if segment_data["Status"] == \
                                        TimingDataStatus.PURPLE:
                                    color = 0xA020F0

                                elif segment_data["Status"] in [
                                    TimingDataStatus.STOPPED,
                                    TimingDataStatus.PIT_ISSUE,
                                ]:
                                    color = 0xFFFF00

                                return DiscordModel.Embed(
                                    title="Timing Data",
                                    fields=[
                                        DiscordModel.Embed.Field(
                                            "Driver",
                                            drv_num,
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Sector",
                                            str(int(sector_num) + 1),
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Segment",
                                            str(int(segment_num) + 1),
                                        ),
                                        DiscordModel.Embed.Field(
                                            "Status",
                                            (
                                                "Purple"
                                                if segment_data["Status"] ==
                                                TimingDataStatus.PURPLE
                                                else "Pitted"
                                                if segment_data["Status"] ==
                                                TimingDataStatus.PITTED
                                                else "Pit issues"
                                                if segment_data["Status"] ==
                                                TimingDataStatus.PIT_ISSUE
                                                else "Stopped"
                                            )
                                        ),
                                    ],
                                    color=color,
                                    timestamp=dateutil.parser.parse(msg_dt),
                                )


SessionInfoData = Dict[str, str | Dict[str, str | Dict[str, str]]]


def session_info_embed(
    msg_data: SessionInfoData,
    msg_dt: str,
):
    return DiscordModel.Embed(
        title="Session Information",
        fields=[
            DiscordModel.Embed.Field(
                "Official Name",
                msg_data["Meeting"]["OfficialName"],
            ),
            DiscordModel.Embed.Field(
                "Name",
                msg_data["Meeting"]["Name"],
            ),
            DiscordModel.Embed.Field(
                "Location",
                msg_data["Meeting"]["Location"],
            ),
            DiscordModel.Embed.Field(
                "Country",
                msg_data["Meeting"]["Country"]["Name"],
            ),
            DiscordModel.Embed.Field(
                "Circuit",
                msg_data["Meeting"]["Circuit"]["ShortName"],
            ),
            DiscordModel.Embed.Field(
                "Type",
                msg_data["Name"],
            ),
            DiscordModel.Embed.Field(
                "Start Date",
                msg_data["StartDate"],
            ),
            DiscordModel.Embed.Field(
                "End Date",
                msg_data["EndDate"],
            ),
            DiscordModel.Embed.Field(
                "GMT Offset",
                msg_data["GmtOffset"],
            ),
        ],
        timestamp=dateutil.parser.parse(msg_dt),
        color=0xFFFFFF,
    )


TrackStatusData = Dict[Literal["Status", "Message"], str]


def track_status_embed(
    msg_data: TrackStatusData,
    msg_dt: str,
):
    return DiscordModel.Embed(
        title="Track Status",
        fields=[
            DiscordModel.Embed.Field(
                "Status",
                (
                    track_status_str(msg_data["Status"]) +
                    f" ({msg_data['Status']})"
                ),
            ),
            DiscordModel.Embed.Field("Message", msg_data["Message"]),
        ],
        description=(
            "<:green:964569379205414932>"
            if msg_data["Status"] in [
                TrackStatus.ALL_CLEAR,
                TrackStatus.GREEN,
                TrackStatus.VSC_ENDING,
            ]
            else "<:yellow:964569379037671484>"
            if msg_data["Status"] in TrackStatus.YELLOW
            else "<:sc:964569379163496538>"
            if msg_data["Status"] in TrackStatus.SC_DEPLOYED
            else "<:vsc:964569379352244284>"
            if msg_data["Status"] in TrackStatus.VSC_DEPLOYED
            else "<:red:964569379234779136>"
            if msg_data["Status"] in TrackStatus.RED
            else None
        ),
        timestamp=dateutil.parser.parse(msg_dt),
    )


SessionData = Dict[
    Literal["Series", "StatusSeries"],
    List[
        Dict[
            str,
            str,
        ]
    ] | Dict[
        str,
        Dict[
            str,
            str | int,
        ],
    ],
]


def session_data_embed(
    msg_data: SessionData,
    msg_dt: str,
):
    fields = []

    if (
        "Series" in msg_data and
        isinstance(msg_data["Series"], list) and
        "StatusSeries" in msg_data and
        isinstance(msg_data["StatusSeries"], list)
    ):
        fields.append(
            DiscordModel.Embed.Field(
                "Track Status",
                msg_data["StatusSeries"][0]["TrackStatus"],
            ),
        )

    elif "Series" in msg_data:
        assert not isinstance(msg_data["Series"], list)

        for series_data in msg_data["Series"].values():
            if "Lap" in series_data:
                fields.append(
                    DiscordModel.Embed.Field(
                        "Lap Count",
                        str(series_data["Lap"]),
                    ),
                )

            elif "QualifyingPart" in series_data:
                fields.append(
                    DiscordModel.Embed.Field(
                        "Qualifying Part",
                        str(series_data["QualifyingPart"]),
                    ),
                )

    elif "StatusSeries" in msg_data:
        assert not isinstance(msg_data["StatusSeries"], list)

        for status_series_data in msg_data["StatusSeries"].values():
            if "TrackStatus" in status_series_data:
                fields.append(
                    DiscordModel.Embed.Field(
                        "Track Status",
                        status_series_data["TrackStatus"],
                    ),
                )

            elif "SessionStatus" in status_series_data:
                fields.append(
                    DiscordModel.Embed.Field(
                        "Session Status",
                        status_series_data["SessionStatus"],
                    ),
                )

    assert len(fields) > 0

    return DiscordModel.Embed(
        title="Session Data",
        fields=fields,
        timestamp=dateutil.parser.parse(msg_dt),
    )


def extrapolated_clock_embed(
    msg_data: Dict[str, str | bool],
    msg_dt: str,
):
    fields = [
        DiscordModel.Embed.Field(
            "Remaining",
            msg_data["Remaining"],
        ),
    ]

    if "Extrapolating" in msg_data:
        fields.append(
            DiscordModel.Embed.Field(
                "Extrapolating",
                str(msg_data["Extrapolating"]),
            ),
        )

    return DiscordModel.Embed(
        title="Extrapolated Clock",
        fields=fields,
        timestamp=dateutil.parser.parse(msg_dt),
    )
