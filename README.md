# Last War Survival: First Lady Bot

## Setup

Follow these instructions to install all the dependencies

https://medium.com/@dhadiprasetyo/android-app-automation-complete-guide-with-python-3-appium-2-and-android-emulator-for-beginner-a2f53ca60e58

Then install Last War on the virtual device, and either create an account and level it up to 16, or log into an account which is already level 16 or more.

This application relies heavily on coordinates, and has only been tested on the Pixel 8 virtual device. Other devices will likely cause errors due to different resolutions.

Install pm2 which is used for process managment to ensure the bot always restarts if an exception is thrown (server restart, zeroed, some other bug).

```sh
npm install -g pm2
```

(Optional) Install redis-stack https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/ which is used for metrics and can also be used as a configuration source to be managed externally.

## Config

See `game-bot/config.example.yaml` for example. Make changes to this file and rename to `config.yaml`.

## Run

Start Android virtual device, then run the following from the root directory of this project.

```sh
pm2 start
```

## Disclaimer

- Your account(s) may be banned for using this so use at your own risk.
