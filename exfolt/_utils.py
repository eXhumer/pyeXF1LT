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
from typing import Dict, List, Literal, Union

from ._model import (
    ExtrapolatedData,
    RaceControlMessageData,
    SessionData,
    SessionInfoData,
    TimingData,
    TrackStatusData,
)
from ._type import TimingDataStatus


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
        for k, v in rate_data.items():
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


SessionInfoDataDict = Dict[str, str | Dict[str, str | Dict[str, str]]]


def session_info_parser(msg_data: SessionInfoDataDict):
    return SessionInfoData(
        msg_data["Meeting"]["OfficialName"],
        msg_data["Meeting"]["Name"],
        msg_data["Meeting"]["Location"],
        msg_data["Meeting"]["Country"]["Name"],
        msg_data["Meeting"]["Circuit"]["ShortName"],
        msg_data["Name"],
        msg_data["StartDate"],
        msg_data["EndDate"],
        msg_data["GmtOffset"],
    )


TrackStatusDataDict = Dict[Literal["Status", "Message"], str]


def track_status_parser(msg_data: TrackStatusDataDict):
    return TrackStatusData(msg_data["Status"], msg_data["Message"])


SessionDataDict = Dict[
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


def session_data_parser(msg_data: SessionDataDict):
    if (
        "Series" in msg_data and
        isinstance(msg_data["Series"], list) and
        "StatusSeries" in msg_data and
        isinstance(msg_data["StatusSeries"], list)
    ):
        return SessionData(
            track_status=msg_data["StatusSeries"][0]["TrackStatus"],
        )

    elif "Series" in msg_data:
        assert not isinstance(msg_data["Series"], list)

        for series_data in msg_data["Series"].values():
            if "Lap" in series_data:
                return SessionData(lap=series_data["Lap"])

            elif "QualifyingPart" in series_data:
                return SessionData(
                    qualifying_part=series_data["QualifyingPart"],
                )

    elif "StatusSeries" in msg_data:
        assert not isinstance(msg_data["StatusSeries"], list)

        for status_series_data in msg_data["StatusSeries"].values():
            if "TrackStatus" in status_series_data:
                return SessionData(
                    track_status=status_series_data["TrackStatus"],
                )

            elif "SessionStatus" in status_series_data:
                return SessionData(
                    session_status=status_series_data["SessionStatus"],
                )

    assert False


def extrapolated_clock_parser(msg_data: Dict[str, str | bool]):
    return ExtrapolatedData(
        msg_data["Remaining"],
        extrapolating=(
            msg_data["Extrapolating"]
            if "Extrapolating" in msg_data
            else None
        )
    )


RaceControlMessageDataDict = Dict[str, Union[str, int]]


def race_control_message_data_parser(
    msg_data: Dict[
        Literal["Messages"],
        Dict[str, RaceControlMessageDataDict] |
        List[RaceControlMessageDataDict],
    ],
):
    if isinstance(msg_data["Messages"], list):
        msg_data = msg_data["Messages"][0]

    else:
        msg_data = list(msg_data["Messages"].values())[0]

    return RaceControlMessageData(
        msg_data["Category"],
        msg_data["Message"],
        flag=(
            msg_data["Flag"]
            if "Flag" in msg_data
            else None
        ),
        scope=(
            msg_data["Scope"]
            if "Scope" in msg_data
            else None
        ),
        driver_data=msg_data["RacingNumber"],
        sector=(
            msg_data["Sector"]
            if "Sector" in msg_data
            else None
        ),
        lap=(
            msg_data["Lap"]
            if "Lap" in msg_data
            else None
        ),
        drs_status=(
            msg_data["Status"]
            if "Status" in msg_data
            else None
        ),
    )


TimingDataDict = Dict[
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


def timing_data_parser(msg_data: TimingDataDict):
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
                                return TimingData(
                                    drv_num,
                                    int(sector_num) + 1,
                                    int(segment_num) + 1,
                                    segment_data["Status"],
                                )
