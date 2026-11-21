#!/bin/bash
# Собирает Diktovka.app рядом с этим скриптом (поверх venv и diktovka_mac.py).
set -e
cd "$(dirname "$0")"

APP="Diktovka.app"
mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/MacOS/Diktovka" <<'EOF'
#!/bin/bash
# Запускает «Диктовку» из её виртуального окружения Python.
BASE="$(cd "$(dirname "$0")/../../.." && pwd)"
exec "$BASE/venv/bin/python" "$BASE/diktovka_mac.py" >> "$BASE/diktovka.log" 2>&1
EOF
chmod +x "$APP/Contents/MacOS/Diktovka"

cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Diktovka</string>
    <key>CFBundleDisplayName</key>
    <string>Диктовка</string>
    <key>CFBundleIdentifier</key>
    <string>com.diktovka.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>Diktovka</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Диктовка распознаёт вашу речь локально – запись никуда не отправляется.</string>
</dict>
</plist>
EOF

echo "Собрано: $APP (запуск: open $APP)"
