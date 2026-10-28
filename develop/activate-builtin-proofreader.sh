#!/bin/bash
# Run as the logged-in user, after installing the built-in Squirrel package.
set -euo pipefail
APP="${1:-/Library/Input Methods/Squirrel.app}"
DATA="$APP/Contents/SharedSupport/proofreader"
HELPER="$APP/Contents/Resources/LiurChecker/LiurChecker"
CLIENT="$APP/Contents/Helpers/liur_proofread_client"
RIME="$HOME/Library/Rime"
AGENT="$HOME/Library/LaunchAgents/org.rime-liur.proofreader.plist"
LABEL="gui/$(id -u)/org.rime-liur.proofreader"
[ "$(id -u)" -ne 0 ] || { echo '請使用登入帳號執行，不要使用 sudo。' >&2; exit 1; }
[ "$APP" = '/Library/Input Methods/Squirrel.app' ] || { echo '遷移只適用已安裝的正式位置。' >&2; exit 1; }
/usr/bin/codesign --verify --deep --strict "$APP"
/usr/bin/env -i HOME="$HOME" PATH=/usr/bin:/bin "$HELPER" --model-dir "$DATA/model" --rime-dir "$DATA" --self-test
BACKUP="$RIME/backups/builtin-migration-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$BACKUP"
for name in lua/liur_proofreader.lua proofreader/liur_proofread_client; do
    if [ -e "$RIME/$name" ] || [ -L "$RIME/$name" ]; then
        mkdir -p "$BACKUP/$(dirname "$name")"
        cp -pP "$RIME/$name" "$BACKUP/$name"
    fi
done
if [ -f "$AGENT" ]; then cp -p "$AGENT" "$BACKUP/launch-agent.plist"; fi
WAS_RUNNING=0
if /bin/launchctl print "$LABEL" >/dev/null 2>&1; then WAS_RUNNING=1; fi
rollback() {
    status=$?
    trap - EXIT
    if [ "$status" -ne 0 ]; then
        for name in lua/liur_proofreader.lua proofreader/liur_proofread_client; do
            rm -f "$RIME/$name"
            if [ -e "$BACKUP/$name" ] || [ -L "$BACKUP/$name" ]; then cp -pP "$BACKUP/$name" "$RIME/$name"; fi
        done
        if [ -f "$BACKUP/launch-agent.plist" ]; then cp -p "$BACKUP/launch-agent.plist" "$AGENT"; fi
        if [ "$WAS_RUNNING" -eq 1 ]; then /bin/launchctl bootstrap "gui/$(id -u)" "$AGENT" || true; fi
        /usr/bin/open "$APP"
        echo "遷移失敗，原設定已還原：$BACKUP" >&2
    fi
    exit "$status"
}
trap rollback EXIT
"$APP/Contents/MacOS/Squirrel" --quit
for attempt in {1..50}; do
    if ! /usr/bin/pgrep -f '^/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel$' >/dev/null; then break; fi
    /bin/sleep 0.1
done
if /usr/bin/pgrep -f '^/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel$' >/dev/null; then
    echo '鼠鬚管仍在結束中，請稍後重試遷移。' >&2
    exit 1
fi
if [ "$WAS_RUNNING" -eq 1 ]; then /bin/launchctl bootout "$LABEL"; fi
rm -f "$AGENT"
mkdir -p "$RIME/lua" "$RIME/proofreader"
cp "$DATA/liur_proofreader.lua" "$RIME/lua/liur_proofreader.lua.new"
mv "$RIME/lua/liur_proofreader.lua.new" "$RIME/lua/liur_proofreader.lua"
rm -f "$RIME/proofreader/liur_proofread_client"
ln -s "$CLIENT" "$RIME/proofreader/liur_proofread_client"
/usr/bin/open "$APP"
ready=0
for attempt in {1..60}; do
    result=$("$CLIENT" "$RIME/proofreader/run/builtin.sock" 備 住)
    if [ "$result" = $'註\t備註' ]; then ready=1; break; fi
    /bin/sleep 0.2
done
[ "$ready" -eq 1 ] || { echo '內建服務未就緒。' >&2; exit 1; }
"$APP/Contents/MacOS/Squirrel" --reload
trap - EXIT
echo "已切換到鼠鬚管內建校錯，舊服務已停止。備份：$BACKUP"
