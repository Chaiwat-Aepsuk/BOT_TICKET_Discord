#!/usr/bin/env bash
# ติดตั้ง / อัปเดต Heaven Ticket Bot บน Ubuntu ให้รันตลอดเวลาด้วย systemd
# วิธีใช้ (จากในโฟลเดอร์บอท):  sudo bash deploy/setup.sh
# รันซ้ำได้ทุกครั้ง เช่น หลังอัปโหลดโค้ดใหม่ หรือแก้ requirements.txt
set -euo pipefail

SERVICE=heaven-ticket-bot
BOT_USER=heavenbot
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ กรุณารันด้วย sudo: sudo bash deploy/setup.sh"
    exit 1
fi
for file in main.py shop_settings.py requirements.txt .env; do
    if [ ! -f "$APP_DIR/$file" ]; then
        echo "❌ ไม่พบไฟล์ $file ใน $APP_DIR กรุณาอัปโหลดให้ครบก่อน"
        exit 1
    fi
done

echo "▶ 1/5 ติดตั้ง Python"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip > /dev/null

echo "▶ 2/5 สร้างผู้ใช้ $BOT_USER สำหรับรันบอท (ไม่ใช้ root เพื่อความปลอดภัย)"
if ! id -u "$BOT_USER" > /dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$BOT_USER"
fi

echo "▶ 3/5 ติดตั้งไลบรารีของบอท"
# .venv ที่อัปโหลดมาจาก Windows ใช้บน Linux ไม่ได้ ลบทิ้งแล้วสร้างใหม่
if [ -d "$APP_DIR/.venv/Scripts" ]; then
    rm -rf "$APP_DIR/.venv"
fi
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "▶ 4/5 ตั้งสิทธิ์ไฟล์"
chown -R "$BOT_USER:$BOT_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"   # Token อ่านได้เฉพาะบอท
if ! runuser -u "$BOT_USER" -- test -r "$APP_DIR/main.py"; then
    echo "❌ ผู้ใช้ $BOT_USER เข้าโฟลเดอร์ $APP_DIR ไม่ได้ (เช่น อยู่ใน /root)"
    echo "   ย้ายโฟลเดอร์บอทไปที่ /opt/heaven-ticket-bot แล้วรันใหม่"
    exit 1
fi

echo "▶ 5/5 ติดตั้งและเปิดบอท"
sed -e "s|__APP_DIR__|$APP_DIR|g" -e "s|__BOT_USER__|$BOT_USER|g" \
    "$APP_DIR/deploy/$SERVICE.service" > "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable -q "$SERVICE"
systemctl restart "$SERVICE"

sleep 5
if systemctl is-active -q "$SERVICE"; then
    echo "✅ บอทกำลังทำงาน ดูข้อความล่าสุดได้ด้วย: sudo journalctl -u $SERVICE -n 30"
else
    echo "❌ บอทเปิดไม่สำเร็จ ข้อความ Error ล่าสุด:"
    journalctl -u "$SERVICE" -n 30 --no-pager
    exit 1
fi
