#!/bin/bash
# bb-browser 开机自启脚本 — 启动 Chrome 实例 + daemon
# 由 launchd 运行，仅在登录时启动一次

set -e

BB_BROWSER="/Users/icemouce/.npm-global/bin/bb-browser"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="$HOME/.bb-browser/browser/user-data"
CDP_PORT=9222

# 1. 检查是否已有 bb-browser Chrome 实例
if ! pgrep -f "bb-browser/browser/user-data.*remote-debugging-port=$CDP_PORT" > /dev/null 2>&1; then
    echo "[bb-browser] Starting Chrome instance..."
    "$CHROME" \
        --remote-debugging-port=$CDP_PORT \
        --user-data-dir="$USER_DATA_DIR" \
        --no-first-run \
        --no-default-browser-check \
        --disable-sync \
        --disable-background-networking \
        --disable-component-update \
        --disable-features=Translate,MediaRouter \
        --disable-session-crashed-bubble \
        --hide-crash-restore-bubble \
        --use-mock-keychain \
        about:blank &
    sleep 3
fi

# 2. 启动 bb-browser daemon（只启动一次）
"$BB_BROWSER" daemon start 2>&1

echo "[bb-browser] Daemon started"
