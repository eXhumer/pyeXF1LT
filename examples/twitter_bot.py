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

from exfolt import F1Client, race_control_message_data_parser
from extc import OAuth2Client, OAuth2Scope


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("client_id")
    parser.add_argument("--client-secret")
    parser.add_argument("--access-token")
    parser.add_argument("--refresh-token")
    parser.add_argument(
        "--redirect-uri",
        default="http://localhost:65012/auth_callback",
    )
    args = parser.parse_args()

    if args.access_token or args.refresh_token:
        extc = OAuth2Client(
            args.client_id,
            access_token=args.access_token,
            refresh_token=args.refresh_token,
            client_secret=args.client_secret,
        )

    else:
        extc = OAuth2Client.new_user_authorization(
            args.client_id,
            args.redirect_uri,
            [
                OAuth2Scope.TWEET_READ,
                OAuth2Scope.TWEET_WRITE,
                OAuth2Scope.OFFLINE_ACCESS,
                OAuth2Scope.USERS_READ,
            ],
            client_secret=args.client_secret,
        )
        print("New Twitter User Token")
        print("----------------------")
        print(f"Access Token: {extc.access_token}")
        print(f"Refresh Token: {extc.refresh_token}")

    with F1Client() as exfolt:
        for msg in exfolt:
            if "C" in msg:
                msg_data = msg["M"][0]["A"]

                if msg_data[0] == "RaceControlMessages":
                    rcm_data = race_control_message_data_parser(
                        msg_data[1],
                    )

                    extc.post(
                        "2/tweets",
                        json={"text": rcm_data.message},
                    )
