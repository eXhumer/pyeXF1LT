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

from argparse import ArgumentParser
from datetime import datetime
from json import dumps
from pathlib import Path

from exfolt import F1Client


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("log_file", type=Path)
    args = parser.parse_args()
    log_path: Path = args.log_file

    with log_path.open(mode="a") as log_stream:
        try:
            with F1Client() as exfolt:
                for msg in exfolt:
                    print(f"Message Received at {datetime.now()}!")

                    if "C" in msg:
                        msg_data = msg["M"][0]["A"]

                        if msg_data[0] != "Heartbeat":
                            log_stream.write(
                                (dumps(msg_data, indent=4) + "\n")
                            )

        except KeyboardInterrupt:
            pass
