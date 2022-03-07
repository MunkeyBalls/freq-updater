# freq-updater
Updater for freqtrade strategies and configuration

Create a copy of, or rename config_example.json to config.json.

Modify the config.json to include the repositories, bots you want to auto update.

Run the script every x mins to check if there has been an update, for example using crontab:
```
2-59/5 * * * * /usr/bin/python3 "/opt/appdata/freqtrade/strats/autoupdater/autoupdate.py"
```
