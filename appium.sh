#!/usr/bin/env bash
cd "$(dirname "$0")"

export ANDROID_HOME=$HOME/Library/Android/sdk 
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/emulator

echo "Starting appium..."
appium --address 127.0.0.1 --port 4723