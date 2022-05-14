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

from datetime import datetime, timezone
from typing import Dict, List, Literal

from ._type import TrackStatus
from ._model import DiscordModel


class RateLimiter:
    def __init__(self) -> None:
        self.__limit: int | None = None
        self.__remaining: int | None = None
        self.__reset: int | None = None

    @property
    def limit(self):
        return self.__limit

    @property
    def remaining(self):
        return self.__remaining

    @property
    def reset(self):
        if not self.__reset:
            return

        return datetime.fromtimestamp(
            self.__reset
        ).replace(tzinfo=timezone.utc)

    def update_limit(self, **rate_data: str):
        for k, v in rate_data:
            if k.lower() == "x-rate-limit-limit":
                self.__limit = int(v)

            elif k.lower() == "x-rate-limit-remaining":
                self.__remaining = int(v)

            elif k.lower() == "x-rate-limit-reset":
                self.__reset = int(v)


def datetime_string_parser(dt_str: str):
    assert (
        "Z" in dt_str and
        dt_str.count("Z") == 1 and
        dt_str.endswith("Z") and
        "T" in dt_str and
        dt_str.count("T") == 1
    ), "\n".join((
        "Unexpected datetime string format!",
        f"Received datetime string: {dt_str}",
    ))

    [date, time] = dt_str.replace("Z", "").split("T")
    assert date.count("-") == 2, "Unexpected date string format!"
    assert (
        time.count(":") == 2 and
        time.count(".") == 1
    ), "Unexpected date string format!"

    [year, month, day] = date.split("-")
    [hour, minute, second] = time.split(":")
    [second, microsecond] = second.split(".")

    if len(microsecond) > 6:
        microsecond = microsecond[:6]
    else:
        microsecond += "0" * (6 - len(microsecond))

    return datetime(
        int(year),
        int(month),
        int(day),
        hour=int(hour),
        minute=int(minute),
        second=int(second),
        microsecond=int(microsecond),
        tzinfo=timezone.utc,
    )


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
        timestamp=datetime_string_parser(msg_dt),
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
        color=(
            0x00FF00
            if msg_data["Status"] in [
                TrackStatus.ALL_CLEAR,
                TrackStatus.GREEN,
                TrackStatus.VSC_ENDING,
            ]
            else 0xFFFF00
            if msg_data["Status"] in [
                TrackStatus.YELLOW,
                TrackStatus.SC_DEPLOYED,
                TrackStatus.VSC_DEPLOYED,
            ]
            else 0xFF0000
            if msg_data["Status"] == TrackStatus.RED
            else None
        ),
        timestamp=datetime_string_parser(msg_dt),
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
        timestamp=datetime_string_parser(msg_dt),
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
        timestamp=datetime_string_parser(msg_dt),
    )
