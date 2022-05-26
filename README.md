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
* [examples/discord_bot.py](./examples/discord_bot.py) - Post supported received messages as Discord embed messages
* [examples/twitter_bot.py](./examples/twitter_bot.py) - Post supported received messages as Twitter tweets
* [examples/message_logger.py](./examples/message_logger.py) - Logs all messages to a local file

## Special Thanks
* [theOehrly](https://github.com/theOehrly) and their work on [Fast-F1](https://github.com/theOehrly/Fast-F1) package. Some documented aspect of live timing has been used in this project.
* [recursiveGecko](https://github.com/recursiveGecko) helping me figure out the decompression of CarData.z and Position.z datas.

## Disclaimer / Notice
pyeXF1LT is an unofficial software and is not associated in anyway with Formula 1 or any of its companies.

## Licensing
This project is licensed under OSI Approved [GNU AGPLv3 **ONLY**](./LICENSE.md).
