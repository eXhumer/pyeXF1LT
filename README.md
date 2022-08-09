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

### Install from PyPI
```console
pip install exfolt
```

### Install from PyPI with Discord integration
```console
pip install exfolt[discord]
```

### Install from PyPI with Twitter integration
```console
pip install exfolt[twitter]
```

Upon package installation, `eXF1LT` executable will be available in your Python environment to use this library as a standalone program. Discord messaging action will be unavailable from executable unless [eXDC](https://github.com/eXhumer/pyeXDC) is installed. Use `eXF1LT --help` to view available executable functions.

## Discord environment variables
Discord environment variables can be specified via external file with `--env-path` formatted like [this](./discord.env.example), by creating a `discord.env` file in current console directory, or it can also be specified in OS environment. **OS environment requires all variable names to be prefixed with `DISCORD_`**. A combination of `WEBHOOK_ID` and `WEBHOOK_TOKEN` or `BOT_TOKEN` and `CHANNEL_ID` will be required to use the Discord bot functionality. By default, the `discord.env.example` file uses a emojis from a privately hosted Discord server, but it can easily be changed as well via environment file or OS environment as well.

## Twitter environment variables
Twitter environment variables can be specified via external file with `--env-path` formatted like [this](./twitter.env.example), by creating a `twitter.env` file in current console directory, or it can also be specified in OS environment. **OS environment requires all variable names to be prefixed with `TWITTER_`**. `OAUTH_CONSUMER_KEY`, `OAUTH_CONSUMER_SECRET`, `OAUTH_TOKEN` & `OAUTH_TOKEN_SECRET` will be required to use Twitter bot functionality.

## Disclaimer / Notice
eXF1LT is an unofficial software and is not associated in anyway with Formula 1 or any of its companies.

## Special Thanks
* [theOehrly](https://github.com/theOehrly) and their work on [Fast-F1](https://github.com/theOehrly/Fast-F1) package. Some documented aspect of live timing has been used in this project.
* [recursiveGecko](https://github.com/recursiveGecko) helping me figure out the decompression of CarData.z and Position.z datas & client connection issue related to GCLB cookie.

## Licensing
This project is licensed under OSI Approved [GNU AGPLv3 **ONLY**](./COPYING).
