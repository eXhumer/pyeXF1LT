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

from datetime import datetime, timezone


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
    assert date.count("-") == 2, f"Unexpected date string format {dt_str}!"
    assert time.count(":") == 2, f"Unexpected date string format {dt_str}!"

    [year, month, day] = date.split("-")
    [hour, minute, second] = time.split(":")

    if "." in dt_str:
        [second, microsecond] = second.split(".")

    else:
        microsecond = "0"

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
