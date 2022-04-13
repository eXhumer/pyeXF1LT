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
* [examples/bot.py](./examples/bot.py) - Retrieves all the messages supported and sends them to a Discord channel via Discord bot
* [examples/bot_webhook.py](./examples/bot_webhook.py) - Retrieves all the messages supported and sends them to a Discord channel via Discord webhook system
* [examples/message_logger.py](./examples/message_logger.py) - Retrieves all the messages supported and logs them to a local file

## Special Thanks
* [theOehrly](https://github.com/theOehrly) and their work on [Fast-F1](https://github.com/theOehrly/Fast-F1) package. Some documented aspect of live timing has been used in this project.
* [recursiveGecko](https://github.com/recursiveGecko) helping me figure out the decompression of CarData.z and Position.z datas.

## Disclaimer / Notice
pyeXF1LT is an unofficial software and is not associated in anyway with Formula 1 or any of its companies.

## Licensing
This project is licensed under OSI Approved [GNU GPLv3 **ONLY**](./LICENSE.md).
