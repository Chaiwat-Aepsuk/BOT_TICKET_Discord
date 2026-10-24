# คู่มือนำ Heaven Ticket Bot ขึ้น VPS (Ubuntu)

เมื่อทำตามคู่มือนี้แล้ว บอทจะรันบน VPS ตลอด 24 ชั่วโมง โดยไม่ต้องเปิดคอมพิวเตอร์ไว้
- บอทเปิดเองเมื่อ VPS รีสตาร์ต
- บอทเปิดใหม่เองใน 10 วินาที ถ้าหยุดเพราะ Error
- บอทรันด้วยผู้ใช้ `heavenbot` ไม่ใช่ root จึงปลอดภัยกว่า

---

## 0. ไฟล์ในโฟลเดอร์ `deploy/`

| ไฟล์ | หน้าที่ |
|---|---|
| `setup.sh` | สคริปต์ติดตั้งและอัปเดตบอท รันคำสั่งเดียวจบ |
| `heaven-ticket-bot.service` | ไฟล์ตั้งค่า systemd สำหรับเปิดบอทค้างไว้ ไม่ต้องแก้เอง |
| `คู่มือ_VPS.md` | คู่มือนี้ |

---

## 1. เช่า VPS

- **ระบบ:** Ubuntu 24.04 หรือ 22.04
- **สเปกขั้นต่ำ:** RAM 1 GB, 1 CPU บอทนี้ใช้ทรัพยากรน้อยมาก
- **เก็บไว้หลังเช่า:** IP ของ VPS และรหัสผ่าน root (หรือไฟล์ SSH key)

## 2. โปรแกรมที่ต้องใช้บนคอมพิวเตอร์

- **WinSCP** (ฟรี) ใช้ลากไฟล์ขึ้น VPS
  - ตอน Login ให้เลือก `SFTP` แล้วใส่ IP, ชื่อผู้ใช้ `root` และรหัสผ่าน
- **Terminal สำหรับพิมพ์คำสั่งบน VPS** เลือกได้ 2 ทาง:
  - เปิด PowerShell แล้วพิมพ์ `ssh root@IP_ของ_VPS`
  - หรือใน WinSCP กดปุ่ม "Open session in PuTTY"

## 3. อัปโหลดไฟล์

1. ใน WinSCP ไปที่ `/opt` แล้วสร้างโฟลเดอร์ชื่อ `heaven-ticket-bot`
2. ลากไฟล์เหล่านี้จากเครื่องเข้าไปในโฟลเดอร์นั้น

**ต้องอัปโหลด:**
```
main.py
shop_settings.py
requirements.txt
.env                ← ไฟล์ Token (WinSCP ซ่อนไฟล์ที่ขึ้นต้นด้วยจุดไว้ กด Ctrl+Alt+H เพื่อแสดง)
deploy/             ← ทั้งโฟลเดอร์
```

**ห้ามอัปโหลด:** `.venv` (ใช้บน Linux ไม่ได้), `.git`, `__pycache__`

> ⚠️ ต้องวางไว้ใน `/opt/heaven-ticket-bot` ห้ามวางใน `/root` เพราะผู้ใช้ของบอทเข้าโฟลเดอร์ `/root` ไม่ได้
> ถ้า Login ด้วยผู้ใช้อื่นที่ไม่ใช่ root ดูหมายเหตุท้ายข้อ 6

## 4. ติดตั้งบอท (ทำครั้งแรกครั้งเดียว)

> 🛑 **ปิดบอทในคอมพิวเตอร์ก่อน**
> ถ้าบอทรันพร้อมกัน 2 ที่ด้วย Token เดียวกัน ปุ่มจะทำงาน 2 ครั้ง และ Ticket จะเปิดซ้ำ

พิมพ์คำสั่งเหล่านี้ใน Terminal ของ VPS ทีละบรรทัด:

```bash
cd /opt/heaven-ticket-bot
sed -i 's/\r$//' deploy/setup.sh      # แก้รูปแบบบรรทัดของไฟล์จาก Windows (ทำไว้กันพลาด)
sudo bash deploy/setup.sh
```

สคริปต์ทำ 5 ขั้นตอนให้เอง:
1. ติดตั้ง Python
2. สร้างผู้ใช้ `heavenbot`
3. ติดตั้งไลบรารีของบอท
4. ล็อกไฟล์ `.env` ให้บอทอ่านได้คนเดียว
5. เปิดบอท

ถ้าขึ้น **✅ บอทกำลังทำงาน** แปลว่าเสร็จแล้ว ลองพิมพ์ `/ping` ใน Discord ได้เลย

## 5. คำสั่งที่ใช้บ่อย

| อยากทำอะไร | คำสั่ง |
|---|---|
| ดูว่าบอทยังทำงานอยู่ไหม | `sudo systemctl status heaven-ticket-bot` |
| ดูข้อความล่าสุด 50 บรรทัด | `sudo journalctl -u heaven-ticket-bot -n 50` |
| ดูข้อความแบบสด (กด Ctrl+C เพื่อออก) | `sudo journalctl -u heaven-ticket-bot -f` |
| รีสตาร์ตบอท | `sudo systemctl restart heaven-ticket-bot` |
| หยุดบอท | `sudo systemctl stop heaven-ticket-bot` |
| เปิดบอท | `sudo systemctl start heaven-ticket-bot` |

ข้อความที่บอทแสดงในหน้าต่างดำบน Windows (เช่น `Bot Online: ...` หรือข้อความ Error) จะอยู่ใน `journalctl` แทน

## 6. อัปเดตบอท (หลังแก้โค้ดหรือข้อความ)

1. แก้ไฟล์ในคอมพิวเตอร์ แล้วทดสอบให้ผ่านก่อน
2. ปิดบอทในคอมพิวเตอร์
3. ใช้ WinSCP อัปโหลดไฟล์ที่แก้ทับของเดิม เช่น `shop_settings.py`
4. รีสตาร์ตบอทบน VPS ตามกรณี:
   - **แก้แค่ `main.py` หรือ `shop_settings.py`:**
     ```bash
     sudo systemctl restart heaven-ticket-bot
     ```
   - **แก้ `requirements.txt` หรือไฟล์ใน `deploy/`:** รันสคริปต์ติดตั้งซ้ำ
     ```bash
     cd /opt/heaven-ticket-bot && sed -i 's/\r$//' deploy/setup.sh && sudo bash deploy/setup.sh
     ```
5. ดูข้อความล่าสุดว่ามี `Bot Online` ขึ้น:
   ```bash
   sudo journalctl -u heaven-ticket-bot -n 20
   ```

> **ถ้า VPS ให้ Login ด้วยผู้ใช้อื่นที่ไม่ใช่ root** (เช่น `ubuntu`) WinSCP จะเขียนไฟล์ลง `/opt` ไม่ได้
> 1. อัปโหลดไฟล์ไปไว้ที่ `/home/ubuntu/upload` ก่อน
> 2. คัดลอกเข้าโฟลเดอร์บอท แล้วรันสคริปต์ติดตั้งซ้ำ
>    ```bash
>    sudo mkdir -p /opt/heaven-ticket-bot && sudo cp -r /home/ubuntu/upload/. /opt/heaven-ticket-bot/
>    cd /opt/heaven-ticket-bot && sudo sed -i 's/\r$//' deploy/setup.sh && sudo bash deploy/setup.sh
>    ```

## 7. ความปลอดภัย

- **`.env` มี Token ของบอท:**
  - ห้ามส่งให้ใคร และห้ามแคปหน้าจอ
  - สคริปต์ล็อกไฟล์นี้ให้บอทอ่านได้คนเดียวไว้แล้ว
- **ถ้า Token หลุด:**
  1. ไปที่ Discord Developer Portal → Bot → Reset Token
  2. แก้ `.env` บน VPS
  3. รีสตาร์ตบอท
- **ตั้งรหัสผ่าน root ให้ยาก** หรือใช้ SSH key แทน

## 8. แก้ปัญหา

| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| `❌ ไม่พบไฟล์ ...` | อัปโหลดไฟล์ไม่ครบ หรือไม่ได้ `cd /opt/heaven-ticket-bot` ก่อนรัน |
| `$'\r': command not found` | ลืมรัน `sed -i 's/\r$//' deploy/setup.sh` |
| `ไม่พบ DISCORD_TOKEN` | ไม่ได้อัปโหลด `.env` หรือไฟล์ว่าง |
| `ตั้งค่าใน shop_settings.py ไม่ถูกต้อง` | แก้ตามข้อความ Error แล้วอัปโหลดใหม่ และรีสตาร์ต |
| `LoginFailure` / `Improper token` | Token ใน `.env` ผิดหรือถูก Reset ไปแล้ว |
| ปุ่มทำงาน 2 ครั้ง หรือ Ticket เปิดซ้ำ | บอทยังรันอยู่ในคอมพิวเตอร์ ให้ปิดฝั่งคอมพิวเตอร์ |
| `/panel` ไม่ขึ้น | `GUILD_ID` ใน `shop_settings.py` ผิด หรือรอ Discord สักครู่แล้วกด Ctrl+R |
