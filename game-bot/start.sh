#!/usr/bin/env bash
cd "$(dirname "$0")"

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/emulator

function cleanup {
  adb shell am force-stop com.fun.lastwar.gp || true
}

cleanup
trap cleanup EXIT
python3 first-lady.py
