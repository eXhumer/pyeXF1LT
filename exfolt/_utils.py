# pyeXF1LT - Unofficial F1 live timing client
# Copyright (C) 2022  eXhumer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 of the
# License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from datetime import datetime, timedelta, timezone


def datetime_parser(datetime_str: str):
    assert (
        "Z" in datetime_str and datetime_str.count("Z") == 1 and datetime_str.endswith("Z") and
        "T" in datetime_str and datetime_str.count("T") == 1
    ), "\n".join((
        "Unexpected datetime string format!",
        f"Received datetime string: {datetime_str}",
    ))

    [date, time] = datetime_str.replace("Z", "").split("T")
    assert date.count("-") == 2, f"Unexpected date string format {datetime_str}!"
    assert time.count(":") == 2, f"Unexpected date string format {datetime_str}!"

    [year, month, day] = date.split("-")
    [hour, minute, second] = time.split(":")

    return datetime(
        int(year),
        int(month),
        int(day),
        hour=int(hour),
        minute=int(minute),
        second=float(second),
        tzinfo=timezone.utc,
    )


def laptime_parser(laptime_str: str):
    [minutes, seconds] = laptime_str.split(":")
    return timedelta(minutes=int(minutes), seconds=round(float(seconds), 3))


def timedelta_parser(delta_str: str):
    assert delta_str.count(":") == 2 and delta_str.count(".") == 1
    [hours, minutes, seconds] = delta_str.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes), seconds=round(float(seconds), 3))
