# eXF1LT
Python unofficial F1 live timing client.

## Package Installation Guide
### Requires
* Python 3.9+
* pip package manager

### Install from source
```console
pip install .
```

## Usage Examples
* `eXF1LT discord-bot --bot-token <BOT-TOKEN> --channel-id <TEXT-CHANNEL-ID> --webhook-id <WEBHOOK-ID> --webhook-token <WEBHOOK-TOKEN>` - Post supported messages to Discord channel(s)
* `eXF1LT message-logger <OUT-LOG-FILE-PATH>` - Logs all messages to a local file

## Special Thanks
* [theOehrly](https://github.com/theOehrly) and their work on [Fast-F1](https://github.com/theOehrly/Fast-F1) package. Some documented aspect of live timing has been used in this project.
* [recursiveGecko](https://github.com/recursiveGecko) helping me figure out the decompression of CarData.z and Position.z datas & client connection issue related to GCLB cookie.

## Disclaimer / Notice
pyeXF1LT is an unofficial software and is not associated in anyway with Formula 1 or any of its companies.

## Licensing
This project is licensed under OSI Approved [GNU AGPLv3 **ONLY**](./COPYING).
