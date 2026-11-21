#!/bin/bash
# Собирает DiktovkaMac.app рядом с этим скриптом (поверх venv и DiktovkaMac.py).
# Лаунчер компилируется из launcher.c: bash-скриптом .app не запускается —
# Gatekeeper требует настоящий бинарник, подписанный хотя бы ad-hoc.
set -e
cd "$(dirname "$0")"

APP="DiktovkaMac.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

clang -O2 -o "$APP/Contents/MacOS/DiktovkaMac" launcher.c
chmod +x "$APP/Contents/MacOS/DiktovkaMac"
cp AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>DiktovkaMac</string>
    <key>CFBundleDisplayName</key>
    <string>DiktovkaMac</string>
    <key>CFBundleIdentifier</key>
    <string>com.diktovkamac.app</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>DiktovkaMac</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>DiktovkaMac распознаёт вашу речь локально – запись никуда не отправляется.</string>
</dict>
</plist>
EOF

# ad-hoc подпись: без неё Gatekeeper молча не запускает приложение
codesign --force --deep --sign - "$APP"

echo "Собрано: $APP (запуск: open $APP)"
