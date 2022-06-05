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

from argparse import ArgumentParser
from datetime import datetime
from json import dumps
from pathlib import Path

from exfolt import SRLiveClient, TimingType


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("log_file", type=Path)
    args = parser.parse_args()
    log_path: Path = args.log_file

    with log_path.open(mode="a") as log_stream:
        try:
            with SRLiveClient(
                "https://livetiming.formula1.com/signalr",
                TimingType.Hub.STREAMING,
                TimingType.Topic.ARCHIVE_STATUS,
                TimingType.Topic.AUDIO_STREAMS,
                TimingType.Topic.CAR_DATA_Z,
                TimingType.Topic.CHAMPIONSHIP_PREDICTION,
                TimingType.Topic.CONTENT_STREAMS,
                TimingType.Topic.CURRENT_TYRES,
                TimingType.Topic.DRIVER_LIST,
                TimingType.Topic.EXTRAPOLATED_CLOCK,
                TimingType.Topic.HEARTBEAT,
                TimingType.Topic.LAP_COUNT,
                TimingType.Topic.POSITION_Z,
                TimingType.Topic.RACE_CONTROL_MESSAGES,
                TimingType.Topic.SESSION_DATA,
                TimingType.Topic.SESSION_INFO,
                TimingType.Topic.SESSION_STATUS,
                TimingType.Topic.TEAM_RADIO,
                TimingType.Topic.TIMING_APP_DATA,
                TimingType.Topic.TIMING_DATA,
                TimingType.Topic.TIMING_STATS,
                TimingType.Topic.TOP_THREE,
                TimingType.Topic.TRACK_STATUS,
                TimingType.Topic.WEATHER_DATA,
            ) as exfolt:
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
