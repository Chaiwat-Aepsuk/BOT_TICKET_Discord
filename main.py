# =====================================================================
#  Heaven Ticket Shop Bot — โค้ดหลัก
#
#  ⚠️ ถ้าแค่ต้องการเปลี่ยนข้อความ รูป สี สินค้า หรือ ID ห้อง
#     ให้แก้ที่ไฟล์ shop_settings.py ไม่ต้องแก้ไฟล์นี้
#  📖 คู่มือการใช้งานและการปรับแต่ง: ดูไฟล์ คู่มือ_Heaven_Ticket.md
#
#  สารบัญ (กด Ctrl+F แล้วพิมพ์ชื่อในวงเล็บเพื่อกระโดดไปหา)
#  1. ตรวจค่าในไฟล์ตั้งค่า ......... (check_shop_settings, check_products)
#  2. ฟอร์มที่ลูกค้ากรอก .......... (SupportRequestModal, ProductOrderModal)
#  3. ฟังก์ชันช่วยของ Ticket ....... (is_ticket_closed, run_ticket_action,
#                                   get_ticket_owner_id, find_open_ticket)
#  4. สรุปงานหลังปิด Ticket ....... (TicketSummaryModal)
#  5. ปุ่มหลังสรุป: เปิดอีกครั้ง/ลบ .. (DeleteTicketView, DeleteTicketConfirmView,
#                                   CancelDeleteView)
#  6. ปุ่มหลังปิด: สรุปข้อมูล ....... (ClosedTicketView)
#  7. ยืนยันปิด Ticket ............ (CloseConfirmView)
#  8. ปุ่มในห้อง Ticket ........... (TicketControlView = Close + Claim,
#                                   ReopenedTicketView = Close หลังเปิดอีกครั้ง)
#  9. สร้างห้อง Ticket ............ (OrderConfirmView)
#  10. ปุ่มบนหน้าร้าน ............. (ProductButton, SupportButton, ShopPanelView)
#  11. เริ่มบอท และคำสั่ง / ......... (ShopBot, /ping, /panel)
#
#  วงจรของ Ticket หนึ่งห้อง:
#  ลูกค้ากดปุ่มหน้าร้าน → กรอกฟอร์ม → ตรวจสอบ → ยืนยัน → สร้างห้อง Ticket
#  → แอดมิน Claim → Close (ย้ายไปหมวดปิด) → สรุปข้อมูล (ส่ง Log + DM)
#  → เปิดอีกครั้ง (วนกลับไป Close) หรือ ลบ (นับถอยหลัง 10 วิ แล้วลบห้อง)
#
#  ข้อมูลของ Ticket ไม่มีฐานข้อมูล เก็บอยู่ในห้อง Discord เอง:
#  - สถานะเปิด/ปิด = ห้องอยู่หมวดไหน (หมวดเปิดของแต่ละปุ่ม / CLOSED_CATEGORY_ID)
#  - เจ้าของ/ปุ่มที่เลือก/ผู้รับผิดชอบ = Topic ของห้อง "👤 @ลูกค้า · 📦 nitro · 🙋 @แอดมิน"
#    (ดูรายละเอียดที่ build_ticket_topic)
# =====================================================================

import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import asyncio
import re

import shop_settings as settings

# Token ของบอทอ่านจากไฟล์ .env (บรรทัด DISCORD_TOKEN=...)
# ห้ามใส่ Token ลงในโค้ดหรือส่งไฟล์ .env ให้คนอื่น
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ID หมวด Log Support เดิม (ไม่ได้ถูกใช้ในโค้ด)
LOG_SUPPORT_CATEGORY_ID = 1558546401921728522

if not TOKEN:
    raise RuntimeError("ไม่พบ DISCORD_TOKEN ในไฟล์ .env")


# หัวข้อนี้ห้ามเปลี่ยน เพราะขั้นตอนสรุปใช้ค้นหารายละเอียดคำสั่งซื้อในห้อง Ticket
ORDER_DETAILS_TITLE = "🧾 รายละเอียดคำสั่งซื้อ"


# =====================================================================
#  1. ตรวจค่าใน shop_settings.py ก่อนบอทเริ่มทำงาน
#  ถ้าค่าผิด บอทจะไม่เริ่ม และแสดงรายการค่าที่ผิดทั้งหมดใน Terminal
#
#  ถ้าเพิ่มค่าใหม่ใน shop_settings.py ให้เพิ่มชื่อค่าในรายการด้านล่างด้วย:
#  - ข้อความ → SETTING_TEXT_LIMITS (และ SETTING_REQUIRED_TEXTS ถ้าห้ามว่าง)
#  - ID      → SETTING_IDS
#  - ลิงก์รูป → SETTING_IMAGE_URLS
#  - สี      → SETTING_COLORS
#  - อีโมจิ   → SETTING_EMOJIS
# =====================================================================

# (ชื่อค่า, ความยาวสูงสุดที่ Discord รับได้)
SETTING_TEXT_LIMITS = [
    ("PANEL_TITLE", 256),
    ("PANEL_DESCRIPTION", 4096),
    ("PANEL_FOOTER", 2048),
    ("BUTTON_SUPPORT_LABEL", 80),
    ("SUPPORT_FORM_TITLE", 45),
    ("SUPPORT_TOPIC_QUESTION", 45),
    ("SUPPORT_TOPIC_PLACEHOLDER", 150),
    ("SUPPORT_DETAILS_QUESTION", 45),
    ("SUPPORT_DETAILS_EXAMPLE", 100),
    ("SUPPORT_FIELD_TOPIC", 200),
    ("SUPPORT_FIELD_DETAILS", 200),
    ("SUPPORT_REVIEW_TITLE", 256),
    ("SUPPORT_WELCOME_TEXT", 4096),
    ("ORDER_FIELD_PRODUCT", 200),
    ("REVIEW_MESSAGE", 2000),
    ("WELCOME_TITLE", 256),
    ("WELCOME_FOOTER", 2048),
    ("ORDER_NOTICE_TEXT", 2000),
    ("ORDER_DETAILS_GREETING", 3000),
    ("TICKET_SUMMARY_TITLE", 256),
    ("SUMMARY_TITLE", 256),
    ("SUMMARY_SECTION_TITLE", 256),
    ("SUMMARY_FOOTER", 2048),
]

# ข้อความที่เว้นว่างไม่ได้
SETTING_REQUIRED_TEXTS = {
    "BUTTON_SUPPORT_LABEL",
    "ORDER_FIELD_PRODUCT", "SUMMARY_SECTION_TITLE",
    "SUPPORT_FORM_TITLE", "SUPPORT_TOPIC_QUESTION", "SUPPORT_DETAILS_QUESTION",
    "SUPPORT_FIELD_TOPIC", "SUPPORT_FIELD_DETAILS",
}

SETTING_IDS = [
    "GUILD_ID", "TICKET_CATEGORY_ID", "CLOSED_CATEGORY_ID",
    "SUPPORT_ROLE_ID", "LOG_CHANNEL_ID",
]

SETTING_IMAGE_URLS = [
    "PANEL_IMAGE_URL", "WELCOME_THUMBNAIL_URL", "WELCOME_IMAGE_URL",
    "SUPPORT_WELCOME_IMAGE_URL", "SUPPORT_WELCOME_THUMBNAIL_URL",
]

SETTING_COLORS = [
    "PANEL_COLOR", "REVIEW_COLOR", "WELCOME_COLOR",
    "ORDER_DETAILS_COLOR", "SUMMARY_COLOR",
]

SETTING_EMOJIS = [
    "BUTTON_SUPPORT_EMOJI",
]

# สีปุ่มที่ใช้ได้ในรายการสินค้า
BUTTON_COLORS = {
    "blue": discord.ButtonStyle.primary,
    "green": discord.ButtonStyle.success,
    "red": discord.ButtonStyle.danger,
    "grey": discord.ButtonStyle.secondary,
}

# ค่าในแต่ละสินค้า: (ชื่อ, ความยาวสูงสุด, บังคับใส่หรือไม่)
PRODUCT_TEXT_FIELDS = [
    ("id", 40, True),
    ("name", 200, True),
    ("channel_name", 20, False),
    ("button_label", 80, True),
    ("button_emoji", 100, False),
    ("button_color", 10, True),
    ("form_title", 45, True),
    ("review_title", 256, False),
    ("welcome_text", 4096, False),
    ("welcome_image_url", 2000, False),
    ("welcome_thumbnail_url", 2000, False),
]
PRODUCT_KEYS = (
    {name for name, _, _ in PRODUCT_TEXT_FIELDS} | {"questions", "category_id"}
)

QUESTION_TEXT_FIELDS = [
    ("question", 45, True),
    ("example", 100, False),
    ("field_name", 200, True),
]
QUESTION_BOOL_FIELDS = ["long", "required"]
QUESTION_KEYS = (
    {name for name, _, _ in QUESTION_TEXT_FIELDS} | set(QUESTION_BOOL_FIELDS)
)

# สินค้าที่ผ่านการตรวจแล้ว เรียงตามลำดับในไฟล์ตั้งค่า {id: สินค้า}
PRODUCTS_BY_ID = {}


def check_products(problems):
    products = getattr(settings, "PRODUCTS", None)

    if not isinstance(products, list):
        problems.append("ไม่พบรายการสินค้า PRODUCTS หรือรูปแบบไม่ถูกต้อง (ต้องอยู่ใน [ ... ])")
        return

    # หน้าร้านมีปุ่มได้ไม่เกิน 25 ปุ่ม (เผื่อปุ่มสอบถาม/แจ้งปัญหา 1 ปุ่ม)
    if len(products) > 24:
        problems.append(f"สินค้ามี {len(products)} รายการ เกินขีดจำกัด 24 รายการ")

    for index, product in enumerate(products, start=1):
        where = f"สินค้าลำดับที่ {index}"

        if not isinstance(product, dict):
            problems.append(f"{where}: รูปแบบไม่ถูกต้อง (ต้องอยู่ใน {{ ... }})")
            continue

        if isinstance(product.get("id"), str) and product["id"].strip():
            where = f"สินค้า \"{product['id'].strip()}\""

        for key in product:
            if key not in PRODUCT_KEYS:
                problems.append(f"{where}: ไม่รู้จักค่า \"{key}\" (พิมพ์ชื่อผิดหรือไม่?)")

        clean = {}

        for key, limit, required in PRODUCT_TEXT_FIELDS:
            value = product.get(key, "")

            if not isinstance(value, str):
                problems.append(f"{where}: \"{key}\" ต้องเป็นข้อความในเครื่องหมาย \"...\"")
                continue

            value = value.strip()
            clean[key] = value

            if required and not value:
                problems.append(f"{where}: ต้องใส่ \"{key}\"")
            elif len(value) > limit:
                problems.append(
                    f"{where}: \"{key}\" ยาว {len(value)} ตัวอักษร เกินที่ Discord รับได้ ({limit})"
                )

        product_id = clean.get("id", "")

        if product_id and (
            not product_id.isascii()
            or not all(c.isalnum() or c == "_" for c in product_id)
            or product_id != product_id.lower()
        ):
            problems.append(f"{where}: \"id\" ใช้ได้เฉพาะ a-z, 0-9 และ _")
        elif product_id in PRODUCTS_BY_ID:
            problems.append(f"{where}: \"id\" ซ้ำกับสินค้าอื่น")

        # อีโมจิต้องเป็นตัวอีโมจิจริง เช่น "💜" หรืออีโมจิของเซิร์ฟเวอร์ "<:ชื่อ:ID>"
        emoji = clean.get("button_emoji", "")

        if emoji and emoji.isascii() and not emoji.startswith("<"):
            problems.append(f"{where}: \"button_emoji\" ต้องเป็นอีโมจิ เช่น \"💜\" หรือเว้นว่าง \"\"")

        if clean.get("button_color") and clean["button_color"] not in BUTTON_COLORS:
            problems.append(f"{where}: \"button_color\" ต้องเป็น blue, green, red หรือ grey")

        for key in ("welcome_image_url", "welcome_thumbnail_url"):
            if clean.get(key) and not clean[key].startswith(("https://", "http://")):
                problems.append(f"{where}: \"{key}\" ต้องขึ้นต้นด้วย https:// หรือเว้นว่าง \"\"")

        # หมวดของห้อง Ticket สินค้านี้ (0 หรือไม่ใส่ = ใช้หมวดหลัก TICKET_CATEGORY_ID)
        category_id = product.get("category_id", 0)

        if not is_valid_category_setting(category_id):
            problems.append(f"{where}: \"category_id\" ต้องเป็น ID ตัวเลข หรือ 0 (ไม่ต้องมี \"...\")")
            category_id = 0
        elif category_id and category_id == getattr(settings, "CLOSED_CATEGORY_ID", None):
            problems.append(f"{where}: \"category_id\" ต้องไม่ใช่หมวดของ Ticket ที่ปิดแล้ว")

        clean["category_id"] = category_id

        # ชื่อนำหน้าห้อง (ไม่ใส่ = ใช้ id สินค้า) และข้อความใน Topic ของห้อง
        clean["channel_name"] = clean.get("channel_name") or product_id
        clean["topic_tag"] = f"📦 {product_id}"

        questions = product.get("questions")

        if not isinstance(questions, list) or not 1 <= len(questions) <= 5:
            problems.append(f"{where}: \"questions\" ต้องมีคำถาม 1-5 ข้อ (ข้อจำกัดของฟอร์ม Discord)")
            questions = []

        clean["questions"] = []
        field_names = {settings.ORDER_FIELD_PRODUCT}

        for q_index, question in enumerate(questions, start=1):
            q_where = f"{where} คำถามข้อ {q_index}"

            if not isinstance(question, dict):
                problems.append(f"{q_where}: รูปแบบไม่ถูกต้อง (ต้องอยู่ใน {{ ... }})")
                continue

            for key in question:
                if key not in QUESTION_KEYS:
                    problems.append(f"{q_where}: ไม่รู้จักค่า \"{key}\" (พิมพ์ชื่อผิดหรือไม่?)")

            clean_question = {}

            for key, limit, required in QUESTION_TEXT_FIELDS:
                value = question.get(key, "")

                if not isinstance(value, str):
                    problems.append(f"{q_where}: \"{key}\" ต้องเป็นข้อความในเครื่องหมาย \"...\"")
                    continue

                value = value.strip()
                clean_question[key] = value

                if required and not value:
                    problems.append(f"{q_where}: ต้องใส่ \"{key}\"")
                elif len(value) > limit:
                    problems.append(
                        f"{q_where}: \"{key}\" ยาว {len(value)} ตัวอักษร เกินที่ Discord รับได้ ({limit})"
                    )

            for key in QUESTION_BOOL_FIELDS:
                value = question.get(key, key == "required")

                if not isinstance(value, bool):
                    problems.append(f"{q_where}: \"{key}\" ต้องเป็น True หรือ False")
                    value = False

                clean_question[key] = value

            # หัวข้อคำตอบห้ามซ้ำกัน ไม่เช่นนั้นคำตอบจะทับกันในรายละเอียดคำสั่งซื้อ
            field_name = clean_question.get("field_name", "")

            if field_name in field_names:
                problems.append(f"{q_where}: \"field_name\" ซ้ำกับหัวข้ออื่นในสินค้านี้")

            field_names.add(field_name)
            clean["questions"].append(clean_question)

        if product_id:
            PRODUCTS_BY_ID[product_id] = clean


def check_support_topics(problems):
    # ตัวเลือกในเมนูเลือกเรื่องของฟอร์มสอบถาม / แจ้งปัญหา
    topics = getattr(settings, "SUPPORT_TOPICS", None)

    if not isinstance(topics, list) or not topics:
        problems.append("SUPPORT_TOPICS ต้องมีตัวเลือกอย่างน้อย 1 ตัว (อยู่ใน [ ... ])")
        return

    if len(topics) > 25:
        problems.append(f"SUPPORT_TOPICS มี {len(topics)} ตัวเลือก เกินขีดจำกัด 25 ตัวเลือก")

    clean_topics = []

    for index, topic in enumerate(topics, start=1):
        # รองรับทั้งแบบ {"name": ..., "channel_name": ...} และแบบข้อความอย่างเดียว
        if isinstance(topic, dict):
            for key in topic:
                if key not in ("name", "channel_name"):
                    problems.append(
                        f"SUPPORT_TOPICS ตัวเลือกที่ {index}: ไม่รู้จักค่า \"{key}\" (พิมพ์ชื่อผิดหรือไม่?)"
                    )

            name = topic.get("name")
            channel_name = topic.get("channel_name", "")
        else:
            name = topic
            channel_name = ""

        if not isinstance(name, str) or not name.strip():
            problems.append(f"SUPPORT_TOPICS ตัวเลือกที่ {index} ต้องมี \"name\" เป็นข้อความที่ไม่ว่าง")
            continue

        if not isinstance(channel_name, str):
            problems.append(f"SUPPORT_TOPICS ตัวเลือกที่ {index}: \"channel_name\" ต้องเป็นข้อความ")
            channel_name = ""

        name = name.strip()
        channel_name = channel_name.strip()

        if len(name) > 100:
            problems.append(
                f"SUPPORT_TOPICS ตัวเลือกที่ {index} ยาว {len(name)} ตัวอักษร เกินที่ Discord รับได้ (100)"
            )

        if len(channel_name) > 20:
            problems.append(
                f"SUPPORT_TOPICS ตัวเลือกที่ {index}: \"channel_name\" ยาวเกิน 20 ตัวอักษร"
            )

        if any(existing["name"] == name for existing in clean_topics):
            problems.append(f"SUPPORT_TOPICS ตัวเลือก \"{name}\" ซ้ำกัน")

        clean_topics.append({
            "name": name,
            # ไม่ใส่ channel_name = ใช้ชื่อเรื่องแทน (ตัดให้สั้น)
            "channel_name": channel_name or name[:20],
        })

    settings.SUPPORT_TOPICS = clean_topics

    # หมวดของห้อง Ticket สอบถาม (0 = ใช้หมวดหลัก TICKET_CATEGORY_ID)
    support_category_id = getattr(settings, "SUPPORT_CATEGORY_ID", None)

    if not is_valid_category_setting(support_category_id):
        problems.append("SUPPORT_CATEGORY_ID ต้องเป็น ID ตัวเลข หรือ 0 (ถ้าไม่มีบรรทัดนี้ ให้เพิ่ม SUPPORT_CATEGORY_ID = 0)")
        settings.SUPPORT_CATEGORY_ID = 0
    elif support_category_id and support_category_id == getattr(settings, "CLOSED_CATEGORY_ID", None):
        problems.append("SUPPORT_CATEGORY_ID ต้องไม่ใช่หมวดของ Ticket ที่ปิดแล้ว")


def is_valid_category_setting(value):
    # ID หมวดในไฟล์ตั้งค่า: ตัวเลขบวก หรือ 0 = ใช้หมวดหลัก
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_shop_settings():
    problems = []

    def read(name, expected_type):
        if not hasattr(settings, name):
            problems.append(f"ไม่พบค่า {name} (อาจเผลอลบบรรทัดนี้)")
            return None

        value = getattr(settings, name)

        if not isinstance(value, expected_type) or isinstance(value, bool):
            problems.append(f"{name} ต้องเป็น{'ข้อความ' if expected_type is str else 'ตัวเลข'}")
            return None

        return value

    for name, limit in SETTING_TEXT_LIMITS:
        value = read(name, str)

        if value is None:
            continue

        # ตัดบรรทัดว่างหัว-ท้ายที่เกิดจากการเขียน """ ... """
        value = value.strip()
        setattr(settings, name, value)

        if name in SETTING_REQUIRED_TEXTS and not value:
            problems.append(f"{name} เว้นว่างไม่ได้")

        if len(value) > limit:
            problems.append(
                f"{name} ยาว {len(value)} ตัวอักษร เกินที่ Discord รับได้ ({limit})"
            )

    for name in SETTING_IDS:
        value = read(name, int)

        if value is not None and value <= 0:
            problems.append(f"{name} ต้องเป็น ID ตัวเลขที่ถูกต้อง")

    for name in SETTING_IMAGE_URLS:
        value = read(name, str)

        if value is None:
            continue

        value = value.strip()
        setattr(settings, name, value)

        if value and not value.startswith(("https://", "http://")):
            problems.append(f"{name} ต้องเป็นลิงก์ที่ขึ้นต้นด้วย https:// หรือเว้นว่าง \"\"")

    for name in SETTING_COLORS:
        value = getattr(settings, name, None)

        # รับสีได้ทั้งแบบ 0xFF46C8 และ "#FF46C8" (แปลงเป็นตัวเลขให้)
        if isinstance(value, str):
            hex_text = value.strip().removeprefix("#")

            try:
                if len(hex_text) != 6:
                    raise ValueError
                setattr(settings, name, int(hex_text, 16))
            except ValueError:
                problems.append(f"{name} ต้องเป็นสีแบบ \"#RRGGBB\" หรือ 0xRRGGBB เช่น \"#FF46C8\"")
            continue

        value = read(name, int)

        if value is not None and not 0 <= value <= 0xFFFFFF:
            problems.append(f"{name} ต้องเป็นสีแบบ \"#RRGGBB\" หรือ 0xRRGGBB เช่น \"#FF46C8\"")

    for name in SETTING_EMOJIS:
        value = read(name, str)

        if value is not None:
            setattr(settings, name, value.strip())

    if isinstance(getattr(settings, "ORDER_FIELD_PRODUCT", None), str):
        check_products(problems)

    check_support_topics(problems)

    if (
        getattr(settings, "SUPPORT_FIELD_TOPIC", None)
        == getattr(settings, "SUPPORT_FIELD_DETAILS", None)
    ):
        problems.append("SUPPORT_FIELD_TOPIC กับ SUPPORT_FIELD_DETAILS ต้องไม่ซ้ำกัน")

    if problems:
        raise RuntimeError(
            "ค่าใน shop_settings.py ไม่ถูกต้อง กรุณาแก้ไขแล้วรีสตาร์ตบอท:\n- "
            + "\n- ".join(problems)
        )


check_shop_settings()


# =====================================================================
#  2. ฟอร์มที่ลูกค้ากรอก (หน้าต่างที่เด้งขึ้นมาหลังกดปุ่มหน้าร้าน)
#  ข้อความในฟอร์มทั้งหมดตั้งใน shop_settings.py
#  หลังกรอก → ส่งหน้าตรวจสอบ (เห็นเฉพาะลูกค้า) พร้อมปุ่มยืนยัน (OrderConfirmView)
# =====================================================================

# ข้อมูลห้อง Ticket สอบถาม / แจ้งปัญหา ใช้รูปแบบเดียวกับสินค้า
# เพื่อใช้ขั้นตอนยืนยันและสร้างห้อง (OrderConfirmView) ชุดเดียวกัน
SUPPORT_TICKET = {
    "welcome_text": settings.SUPPORT_WELCOME_TEXT,
    "welcome_image_url": settings.SUPPORT_WELCOME_IMAGE_URL,
    "welcome_thumbnail_url": settings.SUPPORT_WELCOME_THUMBNAIL_URL,
    "category_id": settings.SUPPORT_CATEGORY_ID,
    # "channel_name" และ "topic_tag" ใส่ตามเรื่องที่ลูกค้าเลือก (ดู on_submit ด้านล่าง)
}

# เครื่องหมายใน Topic ของห้อง Ticket สอบถาม เช่น "💬 สอบถามสินค้า"
SUPPORT_TOPIC_TAG = "💬"


class SupportRequestModal(discord.ui.Modal):
    # ฟอร์มสอบถาม / แจ้งปัญหา: ช่องที่ 1 เลือกเรื่อง, ช่องที่ 2 รายละเอียด (ไม่บังคับ)
    def __init__(self):
        super().__init__(title=settings.SUPPORT_FORM_TITLE)

        self.topic_select = discord.ui.Select(
            placeholder=settings.SUPPORT_TOPIC_PLACEHOLDER or None,
            options=[
                discord.SelectOption(label=topic["name"], value=str(index))
                for index, topic in enumerate(settings.SUPPORT_TOPICS)
            ],
            min_values=1,
            max_values=1,
            required=True
        )
        self.add_item(discord.ui.Label(
            text=settings.SUPPORT_TOPIC_QUESTION,
            component=self.topic_select
        ))

        self.details_input = discord.ui.TextInput(
            placeholder=settings.SUPPORT_DETAILS_EXAMPLE or None,
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000
        )
        self.add_item(discord.ui.Label(
            text=settings.SUPPORT_DETAILS_QUESTION,
            component=self.details_input
        ))

    async def on_submit(self, interaction: discord.Interaction):
        topic = settings.SUPPORT_TOPICS[int(self.topic_select.values[0])]
        details = str(self.details_input.value).strip() or "-"

        answers = {
            settings.SUPPORT_FIELD_TOPIC: topic["name"],
            settings.SUPPORT_FIELD_DETAILS: details
        }

        # ชื่อห้องและ Topic ของห้องขึ้นกับเรื่องที่ลูกค้าเลือก
        ticket_info = dict(
            SUPPORT_TICKET,
            channel_name=topic["channel_name"],
            topic_tag=f"{SUPPORT_TOPIC_TAG} {topic['name']}"
        )

        embed = discord.Embed(
            title=settings.SUPPORT_REVIEW_TITLE or None,
            color=settings.REVIEW_COLOR
        )

        add_answer_fields(embed, answers)

        await interaction.response.send_message(
            settings.REVIEW_MESSAGE or None,
            embed=embed,
            view=OrderConfirmView(
                answers=answers,
                owner_id=interaction.user.id,
                product=ticket_info
            ),
            ephemeral=True
        )


class ProductOrderModal(discord.ui.Modal):
    # ฟอร์มสั่งซื้อของสินค้าหนึ่งรายการ สร้างจากคำถามใน shop_settings.py
    def __init__(self, product):
        super().__init__(title=product["form_title"])
        self.product = product
        self.inputs = []

        for question in product["questions"]:
            text_input = discord.ui.TextInput(
                label=question["question"],
                placeholder=question["example"] or None,
                style=(
                    discord.TextStyle.paragraph
                    if question["long"]
                    else discord.TextStyle.short
                ),
                required=question["required"],
                max_length=1000 if question["long"] else 100
            )
            self.inputs.append((question, text_input))
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        # ไม่จำกัดรูปแบบคำตอบ ลูกค้าพิมพ์ได้อิสระ
        answers = {
            settings.ORDER_FIELD_PRODUCT: self.product["name"]
        }

        for question, text_input in self.inputs:
            answers[question["field_name"]] = (
                str(text_input.value).strip() or "-"
            )

        embed = discord.Embed(
            title=self.product["review_title"] or None,
            color=settings.REVIEW_COLOR
        )

        add_answer_fields(embed, answers)

        await interaction.response.send_message(
            settings.REVIEW_MESSAGE or None,
            embed=embed,
            view=OrderConfirmView(
                answers=answers,
                owner_id=interaction.user.id,
                product=self.product
            ),
            ephemeral=True
        )



# =====================================================================
#  3. ฟังก์ชันช่วยของระบบ Ticket (ใช้ร่วมกันหลายปุ่ม)
# =====================================================================

# ขีดจำกัดของ Discord: Embed หนึ่งอันยาวรวมได้ไม่เกิน 6000 ตัวอักษร
# (เผื่อไว้ 100 ตัวอักษรสำหรับข้อความท้าย/ส่วนอื่น)
EMBED_TOTAL_LIMIT = 6000 - 100


def shorten(text, limit):
    # ตัดข้อความให้ไม่เกิน limit ตัวอักษร และบอกว่าถูกตัด
    # ใช้ป้องกันการส่งไม่สำเร็จเมื่อข้อความยาวเกินที่ Discord รับได้
    if len(text) <= limit:
        return text

    marker = "… (ข้อความยาวเกิน แสดงไม่ครบ)"
    return text[:max(0, limit - len(marker))] + marker


def add_answer_fields(embed, answers, name_prefix="", new_lines=False):
    # ใส่คำตอบของลูกค้าลงใน Embed ทีละช่อง ในกรอบ ``` ```
    # ปกติแสดงครบทุกตัวอักษร จะตัดเฉพาะเมื่อยาวเกินขีดจำกัดของ Discord
    # (ช่องละไม่เกิน 1024 ตัวอักษร และทั้ง Embed ไม่เกิน 6000)
    fence = "```\n{}\n```" if new_lines else "```{}```"
    fence_length = len(fence) - 2
    remaining = EMBED_TOTAL_LIMIT - len(embed)
    items = list(answers.items())

    for index, (question, answer) in enumerate(items):
        name = shorten(f"{name_prefix}{question}", 256)
        # แบ่งพื้นที่ที่เหลือให้ช่องที่ยังไม่ได้ใส่เท่า ๆ กัน
        share = (remaining - len(name)) // (len(items) - index)
        value_limit = max(10, min(1024, share) - fence_length)
        value = fence.format(shorten(answer, value_limit))

        embed.add_field(name=name, value=value, inline=False)
        remaining -= len(name) + len(value)


def is_ticket_closed(channel):
    # ใช้หมวดของห้องบอกสถานะ แทนการแก้ Topic/ชื่อห้อง
    # เพราะ Discord ให้แก้ชื่อ/Topic ได้แค่ประมาณ 2 ครั้งต่อ 10 นาทีต่อห้อง
    return channel.category_id == settings.CLOSED_CATEGORY_ID


# ห้อง Ticket ที่กำลังมีแอดมินดำเนินการอยู่ (Claim / ปิด / เปิดอีกครั้ง / สรุป / ลบ)
busy_ticket_channels = set()


async def run_ticket_action(interaction, action, *args):
    # ป้องกันแอดมินหลายคนกดปุ่มที่แก้ไขห้องเดียวกันพร้อมกัน
    # ถ้ามีคนทำอยู่ คนที่กดตามมาจะได้รับข้อความให้รอ
    channel_id = interaction.channel_id

    if channel_id in busy_ticket_channels:
        await interaction.response.send_message(
            "⏳ มีแอดมินกำลังดำเนินการกับ Ticket นี้อยู่ กรุณารอสักครู่แล้วลองใหม่",
            ephemeral=True
        )
        return

    busy_ticket_channels.add(channel_id)

    try:
        await action(*args)
    finally:
        busy_ticket_channels.discard(channel_id)


# ---------- Topic ของห้อง Ticket ----------
# บอทเก็บข้อมูลของ Ticket ไว้ใน Topic (ข้อความใต้ชื่อห้อง) และแอดมินอ่านได้ด้วย
# แบบปัจจุบัน:  "👤 @ลูกค้า · 📦 nitro"           (ห้องสั่งซื้อ: 📦 ตามด้วย id สินค้า)
#               "👤 @ลูกค้า · 💬 สอบถามสินค้า"    (ห้องสอบถาม: 💬 ตามด้วยเรื่องที่เลือก)
#               หลัง Claim ต่อท้าย " · 🙋 @แอดมิน"
# แบบเดิม (Ticket ที่สร้างก่อนเปลี่ยนรูปแบบ ยังอ่านได้):
#               "Ticket owner ID: 123 | Claimed by ID: 456"
# Topic ถูกเขียนตอนสร้างห้อง และแก้อีกครั้งเดียวตอน Claim (Discord จำกัดการแก้ Topic)

TOPIC_SEPARATOR = " · "
PRODUCT_TOPIC_TAG = "📦"
OWNER_TOPIC_PATTERN = re.compile(r"^👤 <@!?(\d+)>")
CLAIM_TOPIC_PATTERN = re.compile(r"🙋 <@!?\d+>")
LEGACY_OWNER_PREFIX = "Ticket owner ID:"
LEGACY_CLAIM_TEXT = "| Claimed by ID:"


def build_ticket_topic(owner_id, topic_tag):
    # Topic ตอนสร้างห้อง เช่น "👤 <@123> · 📦 nitro" (<@123> แสดงเป็นชื่อลูกค้า)
    return f"👤 <@{owner_id}>{TOPIC_SEPARATOR}{topic_tag}"


def build_claimed_topic(topic, admin_id):
    # Topic หลัง Claim (คงรูปแบบเดิมไว้ถ้าเป็น Ticket เก่า)
    if topic.startswith(LEGACY_OWNER_PREFIX):
        return f"{topic} {LEGACY_CLAIM_TEXT} {admin_id}"

    return f"{topic}{TOPIC_SEPARATOR}🙋 <@{admin_id}>"


def is_ticket_claimed(channel):
    topic = channel.topic or ""
    return LEGACY_CLAIM_TEXT in topic or bool(CLAIM_TOPIC_PATTERN.search(topic))


def get_ticket_owner_id(channel):
    # อ่าน ID เจ้าของ Ticket จาก Topic (รองรับทั้งแบบใหม่และแบบเดิม)
    # คืนค่า None ถ้าห้องนี้ไม่ใช่ Ticket ของระบบ
    topic = channel.topic or ""

    match = OWNER_TOPIC_PATTERN.match(topic)

    if match:
        return int(match.group(1))

    if not topic.startswith(LEGACY_OWNER_PREFIX):
        return None

    try:
        return int(topic[len(LEGACY_OWNER_PREFIX):].split("|", 1)[0].strip())
    except ValueError:
        return None


def get_ticket_open_category_id(channel):
    # หมวดที่ห้องนี้ต้องอยู่ตอน "เปิด" ตามปุ่มที่ลูกค้าเลือก (ใช้ตอนเปิด Ticket อีกครั้ง)
    # ถ้าอ่านไม่ได้ (เช่น Ticket เก่า หรือสินค้าถูกลบจากไฟล์ตั้งค่า) ใช้หมวดหลัก
    parts = (channel.topic or "").split(TOPIC_SEPARATOR)

    for part in parts[1:]:
        if part.startswith(PRODUCT_TOPIC_TAG):
            product = PRODUCTS_BY_ID.get(part[len(PRODUCT_TOPIC_TAG):].strip())

            if product is not None:
                return product["category_id"] or settings.TICKET_CATEGORY_ID

        elif part.startswith(SUPPORT_TOPIC_TAG):
            return settings.SUPPORT_CATEGORY_ID or settings.TICKET_CATEGORY_ID

    return settings.TICKET_CATEGORY_ID


def get_open_category_ids():
    # หมวดทั้งหมดที่ใช้เก็บ Ticket ที่เปิดอยู่ (หมวดหลัก + หมวดของแต่ละสินค้า + หมวดสอบถาม)
    category_ids = {
        settings.TICKET_CATEGORY_ID,
        settings.SUPPORT_CATEGORY_ID or settings.TICKET_CATEGORY_ID,
    }

    for product in PRODUCTS_BY_ID.values():
        if product["category_id"]:
            category_ids.add(product["category_id"])

    return category_ids


def make_channel_name(prefix, user):
    # ชื่อห้อง Ticket: <ชื่อสั้นของปุ่ม/เรื่อง>-<ชื่อลูกค้าแบบสั้น> เช่น nitro-heaven
    # ชื่อลูกค้าใช้ username (a-z, 0-9) ตัดให้ไม่เกิน 12 ตัวอักษร
    customer = "".join(
        c if c.isascii() and c.isalnum() else "-"
        for c in user.name.lower()
    ).strip("-")[:12].strip("-") or "customer"

    # Discord ไม่รับช่องว่างในชื่อห้อง จึงเปลี่ยนเป็น -
    prefix = "-".join(prefix.lower().split()) or "ticket"

    return f"{prefix}-{customer}"[:100]


def find_open_ticket(guild, user_id):
    # หา Ticket ที่ยังเปิดอยู่ของลูกค้าคนนี้ (ดูทุกหมวดของ Ticket ที่เปิดใช้งาน)
    # Ticket ที่ปิดแล้วอยู่ในหมวด CLOSED จึงไม่นับ
    for category_id in get_open_category_ids():
        category = guild.get_channel(category_id)

        if not isinstance(category, discord.CategoryChannel):
            continue

        for channel in category.text_channels:
            if get_ticket_owner_id(channel) == user_id:
                return channel

    return None


# ลูกค้าที่กำลังสร้าง Ticket อยู่ ป้องกันกดยืนยันจากหลายฟอร์มพร้อมกัน
creating_ticket_users = set()

# รอบการสรุปที่ส่ง DM ให้ลูกค้าสำเร็จแล้ว (ID ของข้อความที่มีปุ่ม "สรุปข้อมูล")
# ป้องกันลูกค้าได้ DM ซ้ำ เมื่อแอดมินกดสรุปใหม่เพราะส่ง Log ไม่สำเร็จ
# (เก็บในหน่วยความจำ ล้างเมื่อรีสตาร์ตบอท)
dm_sent_rounds = set()


# =====================================================================
#  4. สรุปงานหลังปิด Ticket (แอดมินกดปุ่ม "สรุปข้อมูล")
#  ขั้นตอน: บันทึกสรุปในห้อง → ดึงรายละเอียดคำสั่งซื้อจากห้อง
#          → ส่งเข้าห้อง Log + ส่ง DM ลูกค้า → แสดงปุ่ม เปิดอีกครั้ง / ลบ
# =====================================================================

async def send_summary_to_log(guild, summary_embed):
    # ส่งสรุปเข้าห้อง Log (ห้องตั้งที่ LOG_CHANNEL_ID ใน shop_settings.py)
    if guild is None:
        raise ValueError("ไม่พบเซิร์ฟเวอร์")

    log_channel = guild.get_channel(settings.LOG_CHANNEL_ID)

    if not isinstance(log_channel, discord.TextChannel):
        raise ValueError(
            "ไม่พบห้อง Log Support กรุณาตรวจสอบการตั้งค่าห้อง Log"
        )

    await log_channel.send(
        embed=summary_embed,
        allowed_mentions=discord.AllowedMentions.none()
    )


class TicketSummaryModal(discord.ui.Modal):
    # ฟอร์มให้แอดมินพิมพ์สรุปผลการดำเนินงาน (ใช้ได้เฉพาะ Role Support)
    def __init__(self, channel, owner_id):
        super().__init__(title="สรุปผลการดำเนินงาน")
        self.ticket_channel = channel
        self.owner_id = owner_id

        self.summary = discord.ui.TextInput(
            label="สรุปผลการดำเนินงาน",
            placeholder="ระบุสิ่งที่ดำเนินการและผลลัพธ์ของคำสั่งซื้อ",
            style=discord.TextStyle.paragraph,
            required=True,
            # Discord รับข้อความในช่องของ Embed ได้ไม่เกิน 1024 ตัวอักษร
            # (สรุปนี้ถูกใส่เป็นช่องหนึ่งใน Embed ที่ส่ง DM และ Log)
            max_length=1000
        )
        self.add_item(self.summary)

    async def on_submit(self, interaction: discord.Interaction):
        # ป้องกันแอดมินหลายคนส่งสรุปพร้อมกัน
        await run_ticket_action(interaction, self.submit_summary, interaction)

    async def submit_summary(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ เฉพาะแอดมิน Support เท่านั้นที่สรุปข้อมูลได้",
                ephemeral=True
            )
            return

        channel = self.ticket_channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ ไม่พบห้อง Ticket",
                ephemeral=True
            )
            return

        if not is_ticket_closed(channel):
            await interaction.response.send_message(
                "❌ สามารถสรุปได้เฉพาะ Ticket ที่ปิดแล้ว",
                ephemeral=True
            )
            return

        summary_text = self.summary.value.strip()

        if not summary_text:
            await interaction.response.send_message(
                "❌ กรุณากรอกสรุปข้อมูล",
                ephemeral=True
            )
            return
        
        # ตอบรับ Modal ทันที ป้องกัน Discord หมดเวลารอ
        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        # ป้องกันสรุปซ้ำ: ถ้าปุ่ม "สรุปข้อมูล" ของรอบนี้ถูกเอาออกแล้ว
        # แปลว่ามีแอดมินคนอื่นสรุปรอบนี้ไปแล้ว
        if interaction.message is not None:
            try:
                latest_message = await channel.fetch_message(
                    interaction.message.id
                )
                already_summarized = not latest_message.components
            except discord.NotFound:
                already_summarized = True
            except discord.HTTPException:
                already_summarized = False

            if already_summarized:
                await interaction.followup.send(
                    "⚠️ Ticket รอบนี้ถูกสรุปไปแล้ว",
                    ephemeral=True
                )
                return

        summary_embed = discord.Embed(
            title=settings.TICKET_SUMMARY_TITLE or None,
            description=summary_text,
            color=settings.SUMMARY_COLOR
        )
        summary_embed.add_field(
            name="ลูกค้า ID",
            value=str(self.owner_id),
            inline=True
        )
        summary_embed.add_field(
            name="โดย",
            value=interaction.user.mention,
            inline=True
        )
        now = datetime.now(
            timezone(timedelta(hours=7))
        )

        date_text = (
            f"{now.day}/{now.month}/{now.year} "
            f"{now.strftime('%H:%M')}"
        )

        summary_embed.add_field(
            name="วันที่และเวลา",
            value=date_text,
            inline=False
        )

        # บันทึกสรุปลงใน Ticket ก่อน
        await channel.send(
            embed=summary_embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

        # ดึงรายละเอียดคำสั่งซื้อจาก Embed เดิมในห้อง Ticket
        order_details = "ไม่พบรายละเอียดคำสั่งซื้อเดิม"

        try:
            async for message in channel.history(limit=100, oldest_first=True):
                if message.author != interaction.client.user:
                    continue

                for original_embed in message.embeds:
                    if original_embed.title == ORDER_DETAILS_TITLE:
                        details = []

                        for field in original_embed.fields:
                            details.append(
                                f"**{field.name}**\n{field.value.strip()}"
                            )

                        if details:
                            order_details = "\n".join(details)

                        break

                if order_details != "ไม่พบรายละเอียดคำสั่งซื้อเดิม":
                    break

        except (discord.Forbidden, discord.HTTPException) as error:
            print(f"ดึงรายละเอียดคำสั่งซื้อไม่สำเร็จ: {error}")

        # สร้าง Embed รายละเอียดคำสั่งซื้อและสรุปผล (ใช้ทั้ง DM และ Log)
        dm_embed = discord.Embed(
            title=settings.SUMMARY_TITLE or None,
            color=settings.SUMMARY_COLOR
        )

        dm_embed.add_field(
            name=settings.SUMMARY_SECTION_TITLE,
            value=summary_text,
            inline=False
        )

        dm_embed.add_field(
            name="📅 วันที่และเวลา",
            value=date_text,
            inline=False
        )

        dm_embed.add_field(
            name="👤 ลูกค้า",
            value=f"<@{self.owner_id}>",
            inline=True
        )

        dm_embed.add_field(
            name="🛠️ แอดมินผู้สรุป",
            value=interaction.user.mention,
            inline=True
        )

        if settings.SUMMARY_FOOTER:
            dm_embed.set_footer(
                text=settings.SUMMARY_FOOTER
            )

        # ใส่รายละเอียดคำสั่งซื้อเป็นอย่างสุดท้าย และตัดให้พอดีพื้นที่ที่เหลือ
        # (คำอธิบาย Embed ได้ไม่เกิน 4096 ตัวอักษร และทั้ง Embed ไม่เกิน 6000)
        dm_embed.description = shorten(
            order_details,
            min(4096, EMBED_TOTAL_LIMIT - len(dm_embed))
        )

        # ส่ง Embed รายละเอียดคำสั่งซื้อและสรุปผลไปยัง Log
        log_success = False

        try:
            await send_summary_to_log(
                interaction.guild,
                dm_embed
            )
            log_success = True

        except (ValueError, discord.Forbidden, discord.HTTPException) as error:
            print(f"ส่ง Log Support ไม่สำเร็จ: {error}")

        # ส่ง Embed เดียวกันไปยัง DM ของลูกค้า
        dm_success = False

        # รอบการสรุป = ข้อความที่มีปุ่ม "สรุปข้อมูล" ที่แอดมินกด
        # ถ้ารอบนี้เคยส่ง DM สำเร็จแล้ว (เช่น ส่ง Log ไม่สำเร็จแล้วกดสรุปใหม่)
        # จะไม่ส่ง DM ซ้ำให้ลูกค้า
        summary_round = (
            interaction.message.id
            if interaction.message is not None
            else None
        )
        dm_already_sent = summary_round in dm_sent_rounds

        if not dm_already_sent:
            try:
                customer = interaction.client.get_user(self.owner_id)

                if customer is None:
                    customer = await interaction.client.fetch_user(self.owner_id)

                await customer.send(
                    embed=dm_embed,
                    allowed_mentions=discord.AllowedMentions.none()
                )

                dm_success = True

                if summary_round is not None:
                    dm_sent_rounds.add(summary_round)

            except discord.Forbidden:
                dm_success = False

            except discord.HTTPException as error:
                print(f"ส่งสรุป DM ไม่สำเร็จ: {error}")
                dm_success = False

        if log_success:
            # ปิดปุ่ม "สรุปข้อมูล" ของรอบนี้ ป้องกันการสรุปซ้ำ
            if interaction.message is not None:
                try:
                    await interaction.message.edit(view=None)
                except discord.HTTPException:
                    pass

            await channel.send(

                "📦 **สรุป Ticket เรียบร้อยแล้ว**\n",
                view=DeleteTicketView()
            )
        # แจ้งผลให้แอดมิน (เห็นคนเดียว)
        result_lines = ["✅ บันทึกสรุปใน Ticket แล้ว"]

        if dm_already_sent:
            result_lines.append("ℹ️ รอบนี้ส่ง DM ให้ลูกค้าไปแล้ว จึงไม่ส่งซ้ำ")
        elif dm_success:
            result_lines.append("✅ ส่ง DM ให้ลูกค้าสำเร็จ")
        else:
            result_lines.append(
                "⚠️ ส่ง DM ให้ลูกค้าไม่สำเร็จ (ลูกค้าอาจปิดรับ DM)"
            )

        if log_success:
            result_lines.append("✅ ส่งสรุปไปยัง Log Support สำเร็จ")
        else:
            result_lines.append(
                "❌ ส่ง Log Support ไม่สำเร็จ กรุณาตรวจสอบ Terminal "
                "แล้วกด \"สรุปข้อมูล\" ใหม่"
            )

        result_text = "\n".join(result_lines)

        await interaction.followup.send(
            result_text,
            ephemeral=True
        )


# =====================================================================
#  5. ปุ่มหลังสรุปงาน: "เปิด Ticket อีกครั้ง" / "ลบ Ticket"
#  ลบ → ถามยืนยัน (DeleteTicketConfirmView) → นับถอยหลัง 10 วิ (CancelDeleteView)
#  ระหว่างนับถอยหลังกด "ยกเลิกการลบ" ได้ แล้วจะได้ปุ่มชุดนี้กลับมาใหม่
# =====================================================================

class DeleteTicketView(discord.ui.View):
    # ไม่รับข้อมูลห้องตอนสร้าง เพื่อให้ลงทะเบียนเป็นปุ่มถาวรได้
    # (ปุ่มยังใช้งานได้หลังรีสตาร์ตบอท) ห้องจะอ่านจาก interaction.channel แทน
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="เปิด Ticket อีกครั้ง",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="heaven:reopen_ticket"
    )
    
    async def reopen_ticket(self, interaction, button):
        # ป้องกันแอดมินหลายคนกดเปิดอีกครั้งพร้อมกัน
        await run_ticket_action(interaction, self.do_reopen_ticket, interaction)

    async def do_reopen_ticket(self, interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = (
            interaction.guild.get_role(settings.SUPPORT_ROLE_ID)
            if interaction.guild else None
        )

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ เฉพาะทีม Support เท่านั้นที่เปิด Ticket ได้",
                ephemeral=True
            )
            return

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ ไม่พบห้อง Ticket",
                ephemeral=True
            )
            return

        if not is_ticket_closed(channel):
            await interaction.response.send_message(
                "⚠️ Ticket นี้ไม่ได้อยู่ในสถานะปิด",
                ephemeral=True
            )
            return

        # อ่าน ID เจ้าของ Ticket จาก Topic
        owner_id = get_ticket_owner_id(channel)

        if owner_id is None:
            await interaction.response.send_message(
                "❌ อ่านข้อมูลเจ้าของ Ticket ไม่สำเร็จ",
                ephemeral=True
            )
            return

        # ย้ายกลับหมวดของปุ่มที่ลูกค้าเลือกตอนเปิด Ticket (เช่น Support2)
        open_category = interaction.guild.get_channel(
            get_ticket_open_category_id(channel)
        )

        if not isinstance(open_category, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ ไม่พบ Category Ticket ที่เปิดใช้งาน",
                ephemeral=True
            )
            return

        # ตรวจว่าลูกค้ามี Ticket อื่นที่เปิดอยู่หรือไม่ (ตรวจก่อนย้ายห้องนี้กลับ
        # ห้องนี้จึงยังอยู่หมวด CLOSED และไม่ถูกนับ) อนุญาตให้เปิดได้ แต่จะเตือนแอดมิน
        other_open_ticket = find_open_ticket(interaction.guild, owner_id)

        # ตอบ Discord ทันที ป้องกันปุ่มหมดเวลา 3 วินาทีระหว่างแก้ไขห้อง
        await interaction.response.defer()

        # ตรวจสอบว่ามีเจ้าของ Ticket อยู่ในเซิร์ฟเวอร์
        try:
            owner = await interaction.guild.fetch_member(owner_id)
        except discord.NotFound:
            await interaction.followup.send(
                "❌ ไม่พบลูกค้าในเซิร์ฟเวอร์ จึงไม่สามารถเปิด Ticket ได้",
                ephemeral=True
            )
            return
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"❌ ตรวจสอบบัญชีลูกค้าไม่สำเร็จ: {error}",
                ephemeral=True
            )
            return

        # ย้ายกลับ Category เดิมและซิงก์ Permission กับหมวดหมู่
        # ไม่แก้ชื่อห้องและ Topic เพื่อไม่ให้ติด Rate Limit
        try:
            await channel.edit(
                category=open_category,
                sync_permissions=True,
                reason=f"Ticket reopened by {interaction.user}"
            )

            # คืนสิทธิ์ให้ลูกค้าดูและส่งข้อความได้
            await channel.set_permissions(
                owner,
                overwrite=discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True,
                    send_messages_in_threads=True,
                    add_reactions=True
                ),
                reason=f"Ticket reopened by {interaction.user}"
            )

            await channel.send(
                f"🔓 Ticket ถูกเปิดอีกครั้งโดย {interaction.user.mention}\n"
                f"ยินดีต้อนรับกลับครับ {owner.mention} สามารถพิมพ์ข้อความได้แล้ว",
                allowed_mentions=discord.AllowedMentions.none()
            )

            # ปิดปุ่มเปิด/ลบชุดเดิม
            for item in self.children:
                item.disabled = True

            await interaction.edit_original_response(
                content="✅ เปิด Ticket กลับมาแล้ว ลูกค้าสามารถพิมพ์ได้อีกครั้ง",
                view=self
            )

            # ส่งปุ่มควบคุม Ticket ชุดใหม่
            await channel.send(
                "🔓 **Ticket เปิดใช้งานแล้ว**\n"
                "แอดมินสามารถปิด Ticket ได้จากปุ่มด้านล่าง",
                view=ReopenedTicketView()
            )

            # เตือนแอดมินเฉพาะคนที่กด ถ้าลูกค้ามี Ticket อื่นเปิดอยู่ด้วย
            if other_open_ticket is not None:
                await interaction.followup.send(
                    "⚠️ **แจ้งเตือน:** ลูกค้ารายนี้มี Ticket อื่นที่เปิดอยู่แล้ว: "
                    f"{other_open_ticket.mention}\n"
                    "ตอนนี้ลูกค้ามี Ticket เปิดอยู่ 2 ห้อง "
                    "กรุณาตรวจสอบและปิดห้องที่ไม่ใช้งาน",
                    ephemeral=True
                )


        except discord.Forbidden:
            await interaction.followup.send(
                "❌ บอทไม่มีสิทธิ์จัดการห้องหรือ Permission",
                ephemeral=True
            )
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"❌ เปิด Ticket ไม่สำเร็จ: {error}",
                ephemeral=True
            )
    @discord.ui.button(
        label="ลบ Ticket",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="heaven:delete_ticket"
    )
    async def delete_ticket(self, interaction, button):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = (
            interaction.guild.get_role(settings.SUPPORT_ROLE_ID)
            if interaction.guild else None
        )

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ เฉพาะทีม Support เท่านั้นที่ลบ Ticket ได้",
                ephemeral=True
            )
            return

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ ไม่พบห้อง Ticket",
                ephemeral=True
            )
            return

        if not is_ticket_closed(channel):
            await interaction.response.send_message(
                "❌ ลบได้เฉพาะ Ticket ที่ปิดแล้ว",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ คุณกำลังจะลบ Ticket นี้\n"
            "ยืนยันหรือยกเลิกได้จากปุ่มด้านล่าง",
            view=DeleteTicketConfirmView(channel, interaction.message),
            ephemeral=True
        )



class DeleteTicketConfirmView(discord.ui.View):
    # ข้อความถามยืนยันก่อนลบ (เห็นเฉพาะแอดมินที่กด) หมดเวลาใน 60 วินาที
    def __init__(self, channel, panel_message=None):
        super().__init__(timeout=60)
        self.ticket_channel = channel
        # ข้อความที่มีปุ่ม เปิด Ticket อีกครั้ง / ลบ Ticket
        self.panel_message = panel_message
        self.cancelled = False
        self.started = False

    async def interaction_check(self, interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            ) 
            return False

        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if support_role is None or support_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ เฉพาะทีม Support เท่านั้นที่ใช้ปุ่มนี้ได้",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="ยืนยันลบ",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def confirm_delete(self, interaction, button):
        # ป้องกันแอดมินหลายคนยืนยันลบพร้อมกัน (ล็อกไว้ตลอดช่วงนับถอยหลัง)
        await run_ticket_action(interaction, self.do_confirm_delete, interaction)

    async def do_confirm_delete(self, interaction):
        if self.started:
            await interaction.response.send_message(
                "กำลังดำเนินการอยู่ครับ",
                ephemeral=True
            )
            return

        self.started = True

        channel = self.ticket_channel

        # ต้องเป็น Ticket ที่ปิดแล้วเท่านั้น
        if not is_ticket_closed(channel):
            await interaction.response.send_message(
                "❌ ห้องนี้ไม่ใช่ Ticket ที่ปิดแล้ว",
                ephemeral=True
            )
            self.started = False
            return

        # สร้างข้อความนับถอยหลัง พร้อมปุ่มยกเลิก
        cancel_view = CancelDeleteView(channel, self.panel_message)

        await interaction.response.edit_message(
            content="🗑️ ยืนยันแล้ว กำลังเตรียมลบ Ticket...",
            view=None
        )

        countdown_message = await channel.send(
            "⚠️ **Ticket จะถูกลบใน 10 วินาที**\n"
            "กดปุ่มด้านล่างหากต้องการยกเลิก",
            view=cancel_view
        )

        for seconds_left in range(10, 0, -1):
            if cancel_view.cancelled:
                return

            try:
                await countdown_message.edit(
                    content=f"⚠️ **Ticket จะถูกลบใน {seconds_left} วินาที**",
                    view=cancel_view
                )
            except discord.HTTPException:
                pass

            await asyncio.sleep(1)

        if cancel_view.cancelled:
            return

        # ตรวจสอบว่าห้องยังอยู่ และยังเป็น Ticket ปิดแล้ว
        try:
            current_channel = channel.guild.get_channel(channel.id)

            if current_channel is None:
                return

            if not is_ticket_closed(current_channel):
                await channel.send(
                    "❌ ยกเลิกการลบ เพราะสถานะ Ticket เปลี่ยนไปแล้ว"
                )
                return

            await channel.delete(
                reason=f"Ticket deletion confirmed by {interaction.user}"
            )

        except discord.NotFound:
            pass
        except discord.Forbidden:
            print("ลบ Ticket ไม่สำเร็จ: บอทไม่มีสิทธิ์ Manage Channels")
        except discord.HTTPException as error:
            print(f"ลบ Ticket ไม่สำเร็จ: {error}")

    @discord.ui.button(
        label="ยกเลิก",
        emoji="❌",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_confirm(self, interaction, button):
        self.cancelled = True
        self.stop()

        await interaction.response.edit_message(
            content="ยกเลิกการลบ Ticket แล้วครับ",
            view=None
        )


class CancelDeleteView(discord.ui.View):
    # ปุ่ม "ยกเลิกการลบ" ที่แสดงระหว่างนับถอยหลัง 10 วินาที
    def __init__(self, channel, panel_message=None):
        super().__init__(timeout=15)
        self.ticket_channel = channel
        self.panel_message = panel_message
        self.cancelled = False

    @discord.ui.button(
        label="ยกเลิกการลบ",
        emoji="🛑",
        style=discord.ButtonStyle.danger
    )
    async def cancel_delete(self, interaction, button):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if support_role is None or support_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ เฉพาะทีม Support เท่านั้นที่ยกเลิกได้",
                ephemeral=True
            )
            return

        self.cancelled = True
        self.stop()

        await interaction.response.edit_message(
            content="✅ ยกเลิกการลบ Ticket แล้ว ห้องนี้จะไม่ถูกลบ",
            view=None
        )

        # ปิดปุ่มชุดเดิมที่อยู่ด้านบน แล้วส่งปุ่มชุดใหม่ไว้ล่างสุด
        # เพื่อให้วนลูป เปิดอีกครั้ง / ลบ ต่อได้
        if self.panel_message is not None:
            try:
                await self.panel_message.edit(view=None)
            except discord.HTTPException:
                pass

        await self.ticket_channel.send(
            "📦 **Ticket ยังอยู่ในสถานะปิด**\n"
            "เลือกเปิด Ticket อีกครั้ง หรือลบ Ticket ได้จากปุ่มด้านล่าง",
            view=DeleteTicketView()
        )

    async def on_timeout(self):
        # หากปุ่มหมดเวลา จะไม่สามารถกดยกเลิกผ่านปุ่มนี้ได้อีก
        for item in self.children:
            item.disabled = True


# =====================================================================
#  6. ปุ่มหลังปิด Ticket: "สรุปข้อมูล" (เปิดฟอร์ม TicketSummaryModal)
# =====================================================================

class ClosedTicketView(discord.ui.View):
    # ไม่รับ owner_id ตอนสร้าง เพื่อให้ลงทะเบียนเป็นปุ่มถาวรได้
    # เจ้าของ Ticket จะอ่านจาก Topic ของห้องแทน
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="สรุปข้อมูล",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="heaven:ticket_summary"
    )
    async def summary_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ เฉพาะแอดมิน Support เท่านั้นที่ใช้ปุ่มนี้ได้",
                ephemeral=True
            )
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ ไม่พบห้อง Ticket",
                ephemeral=True
            )
            return

        if not is_ticket_closed(interaction.channel):
            await interaction.response.send_message(
                "❌ Ticket นี้ยังไม่ได้ปิด",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(interaction.channel)

        if owner_id is None:
            await interaction.response.send_message(
                "❌ ไม่สามารถอ่าน ID เจ้าของ Ticket ได้",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TicketSummaryModal(
                interaction.channel,
                owner_id
            )
        )


# =====================================================================
#  7. ยืนยันปิด Ticket
#  ปิด = ล็อกไม่ให้ลูกค้าพิมพ์ + ย้ายห้องไปหมวด CLOSED + เอาปุ่ม Close/Claim เดิมออก
#        + ส่งปุ่ม "สรุปข้อมูล"
#  (ไม่เปลี่ยนชื่อห้อง/Topic เพราะ Discord จำกัดการแก้ 2 ครั้งต่อ 10 นาที)
# =====================================================================

class CloseConfirmView(discord.ui.View):
    # ข้อความถามยืนยันปิด (เห็นเฉพาะแอดมินที่กด) หมดเวลาใน 120 วินาที
    def __init__(self, ticket_channel, owner_id):
        super().__init__(timeout=120)
        self.ticket_channel = ticket_channel
        self.owner_id = owner_id

    @discord.ui.button(
        label="ยืนยันปิด Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger
    )
    async def confirm_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # ป้องกันแอดมินหลายคนยืนยันปิดพร้อมกัน
        await run_ticket_action(interaction, self.do_confirm_close, interaction)

    async def do_confirm_close(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        # ตรวจสอบ Role แอดมิน
        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ คุณไม่มีสิทธิ์ปิด Ticket นี้",
                ephemeral=True
            )
            return

        channel = self.ticket_channel

        # ป้องกันการใช้ปุ่มผิดห้อง
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "ไม่พบห้อง Ticket",
                ephemeral=True
            )
            return

        # อ่านเจ้าของ Ticket จาก Topic
        if get_ticket_owner_id(channel) != self.owner_id:
            await interaction.response.send_message(
                "❌ ไม่สามารถยืนยันเจ้าของ Ticket ได้",
                ephemeral=True
            )
            return

        # ป้องกันการกดยืนยันซ้ำ
        self.stop()

        # ตอบ Discord ทันที และแสดงสถานะ "กำลังคิด" ให้แอดมินเห็น
        await interaction.response.defer(ephemeral=True, thinking=True)

        # ตรวจสอบสถานะล่าสุดก่อนปิด
        if is_ticket_closed(channel):
            await interaction.followup.send(
                "⚠️ Ticket นี้ถูกปิดไปแล้วครับ",
                ephemeral=True
            )
            return

        # ล็อกสิทธิ์เจ้าของ Ticket ไม่ให้ส่งข้อความ
        owner = interaction.guild.get_member(self.owner_id)

        if owner is None:
            try:
                owner = await interaction.guild.fetch_member(self.owner_id)
            except discord.NotFound:
                owner = None

        if owner is None:
            await interaction.followup.send(
                "❌ ไม่พบเจ้าของ Ticket จึงไม่สามารถล็อกสิทธิ์ได้",
                ephemeral=True
            )
            return

        # ตรวจสอบ Category ปลายทาง
        closed_category = interaction.guild.get_channel(
            settings.CLOSED_CATEGORY_ID
        )

        if not isinstance(closed_category, discord.CategoryChannel):
            await interaction.followup.send(
                "❌ ไม่พบ Category CLOSED TICKETS กรุณาตรวจสอบ ID",
                ephemeral=True
            )
            return

        try:
            await channel.set_permissions(
                owner,
                overwrite=discord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=False,
                    send_messages_in_threads=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    add_reactions=False
                ),
                reason=f"Ticket closed by {interaction.user}"
            )

            # ย้าย Ticket ไปหมวด CLOSED TICKETS (หมวดนี้คือสถานะปิด)
            # ไม่แก้ชื่อห้องและ Topic เพื่อไม่ให้ติด Rate Limit
            await channel.edit(
                category=closed_category,
                reason=f"Ticket closed by {interaction.user}"
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ บอทไม่มีสิทธิ์จัดการห้องหรือ Permission",
                ephemeral=True
            )
            return
        except discord.HTTPException as error:
            print(f"ปิด Ticket ไม่สำเร็จ: {error}")
            await interaction.followup.send(
                f"❌ ปิด Ticket ไม่สำเร็จ: {error}",
                ephemeral=True
            )
            return

        # ปิดเฉพาะปุ่มควบคุม Ticket ที่มีอยู่เดิม
        async for message in channel.history(limit=50):
            if message.author != interaction.client.user or not message.components:
                continue

            # ปิดเฉพาะข้อความที่มีปุ่ม Close Ticket (ทั้งชุดแรกและชุดเปิดใหม่) หรือ Claim
            has_ticket_controls = any(
                getattr(component, "custom_id", None)
                in (
                    "heaven:close_ticket",
                    "heaven:claim_ticket",
                    "heaven:reopened_close_ticket"
                )
                for row in message.components
                for component in row.children
            )

            if has_ticket_controls:
                await message.edit(view=None)

        # แจ้งว่าปิด Ticket แล้ว

        await channel.send(
            f"🔒 Ticket ถูกปิดโดย {interaction.user.mention}\n"
            "ห้องนี้ถูกล็อกไม่ให้ลูกค้าส่งข้อความเพิ่มเติม"
        )

        await channel.send(
            view=ClosedTicketView()
        )

        await interaction.followup.send(
            "✅ ปิด Ticket เรียบร้อยแล้ว",
            ephemeral=True
        )


    @discord.ui.button(
        label="ยกเลิก",
        emoji="↩️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="ยกเลิกการปิด Ticket แล้ว",
            view=None
        )
        self.stop()



# =====================================================================
#  8. ปุ่มในห้อง Ticket
#  TicketControlView  = ปุ่มแรกของห้อง: Close Ticket + Claim
#  ReopenedTicketView = หลังเปิดอีกครั้ง: Close Ticket อย่างเดียว (ไม่มี Claim ซ้ำ)
#  ทุกปุ่มใช้ได้เฉพาะคนที่มี Role Support (SUPPORT_ROLE_ID)
# =====================================================================

class ReopenedTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="heaven:reopened_close_ticket"
    )
    async def close_reopened_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # เรียกขั้นตอนยืนยันปิด Ticket แบบเดียวกับปุ่มเดิม
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "คำสั่งนี้ใช้ได้เฉพาะในห้อง Ticket",
                ephemeral=True
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = (
            interaction.guild.get_role(settings.SUPPORT_ROLE_ID)
            if interaction.guild else None
        )

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ เฉพาะทีม Support เท่านั้นที่ปิด Ticket ได้",
                ephemeral=True
            )
            return

        channel = interaction.channel

        if is_ticket_closed(channel):
            await interaction.response.send_message(
                "⚠️ Ticket นี้ถูกปิดไปแล้วครับ",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(channel)

        if owner_id is None:
            await interaction.response.send_message(
                "❌ ห้องนี้ไม่ใช่ Ticket ที่ระบบรู้จัก",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "คุณแน่ใจหรือไม่ว่าต้องการปิด Ticket นี้?",
            view=CloseConfirmView(channel, owner_id),
            ephemeral=True
        )


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="heaven:close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "คำสั่งนี้ใช้ได้เฉพาะในห้อง Ticket",
                ephemeral=True
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "เมนูเฉพาะ Admin เท่านั้น!!",
                ephemeral=True
            )
            return

        # ตรวจสอบว่า Ticket ถูกปิดไปแล้วหรือยัง
        if is_ticket_closed(interaction.channel):
            await interaction.response.send_message(
                "⚠️ Ticket นี้ถูกปิดไปแล้วครับ",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(interaction.channel)

        if owner_id is None:
            await interaction.response.send_message(
                "❌ ห้องนี้ไม่ใช่ Ticket ที่ระบบรู้จัก",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "คุณแน่ใจหรือไม่ว่าต้องการปิด Ticket นี้?",
            view=CloseConfirmView(
                interaction.channel,
                owner_id
            ),
            ephemeral=True
        )
    
    @discord.ui.button(
        label="Claim",
        emoji="🙋",
        style=discord.ButtonStyle.success,
        custom_id="heaven:claim_ticket"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # ป้องกันแอดมินหลายคนกด Claim พร้อมกัน
        await run_ticket_action(
            interaction, self.do_claim_ticket, interaction, button
        )

    async def do_claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "ไม่สามารถตรวจสอบสิทธิ์ได้",
                ephemeral=True
            )
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "คำสั่งนี้ใช้ได้เฉพาะในห้อง Ticket",
                ephemeral=True
            )
            return

        # ตรวจสอบ Role ที่ได้รับอนุญาต
        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        ) if interaction.guild else None

        if (
            support_role is None
            or support_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ เฉพาะแอดมินที่มี Role Support เท่านั้นที่ Claim ได้",
                ephemeral=True
            )
            return

        channel = interaction.channel
        topic = channel.topic or ""

        # ตรวจสอบว่าเป็น Ticket ของระบบ
        if get_ticket_owner_id(channel) is None:
            await interaction.response.send_message(
                "❌ ห้องนี้ไม่ใช่ Ticket ที่ระบบรู้จัก",
                ephemeral=True
            )
            return

        # ตรวจสอบว่าเคยมีคน Claim แล้วหรือยัง
        if is_ticket_claimed(channel):
            await interaction.response.send_message(
                "⚠️ Ticket นี้มีผู้รับผิดชอบแล้ว",
                ephemeral=True
            )
            return

        # บันทึกผู้รับผิดชอบต่อท้าย Topic เดิม เช่น "... · 🙋 @แอดมิน"
        new_topic = build_claimed_topic(topic, interaction.user.id)

        try:
            await channel.edit(
                topic=new_topic,
                reason=f"Ticket claimed by {interaction.user}"
            )

            # เปลี่ยนปุ่มให้เห็นว่าใครรับเคสนี้แล้ว
            button.label = f"Claimed: {interaction.user.display_name}"
            button.disabled = True

            await interaction.response.edit_message(view=self)

            await interaction.followup.send(
                f"✅ คุณรับผิดชอบ Ticket นี้แล้ว: {channel.mention}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Bot ไม่มีสิทธิ์แก้ไขห้อง Ticket",
                ephemeral=True
            )

        except discord.HTTPException as error:
            print(f"Claim ticket error: {error}")
            await interaction.response.send_message(
                "❌ Claim Ticket ไม่สำเร็จ กรุณาตรวจสอบ Terminal",
                ephemeral=True
            )


# =====================================================================
#  9. สร้างห้อง Ticket (หลังลูกค้ากด "ยืนยันข้อมูล" ในหน้าตรวจสอบ)
#  ห้องใหม่ชื่อ <channel_name ของปุ่ม/เรื่อง>-<ชื่อลูกค้า> เช่น nitro-heaven
#  อยู่ในหมวด "category_id" ของสินค้า / SUPPORT_CATEGORY_ID (0 = หมวดหลัก TICKET_CATEGORY_ID)
#  เห็นได้เฉพาะลูกค้าคนนั้น + Role Support
#  ข้อความในห้อง: 1) Embed ต้อนรับ + ปุ่ม Close/Claim  2) ข้อความคั่น
#                3) รายละเอียดคำสั่งซื้อ (คำตอบจากฟอร์ม)
# =====================================================================

class OrderConfirmView(discord.ui.View):
    # ใช้ทั้งการสั่งซื้อสินค้าและการสอบถาม (product = ข้อมูลสินค้า หรือ SUPPORT_TICKET)
    def __init__(self, answers, owner_id, product):
        super().__init__(timeout=300)
        self.answers = answers
        self.owner_id = owner_id
        self.product = product
        self.started = False

    @discord.ui.button(
        label="ยืนยันข้อมูล",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # ป้องกันคนอื่นเรียกใช้ View นี้
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ คำสั่งซื้อนี้ไม่ใช่ของคุณ",
                ephemeral=True
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์",
                ephemeral=True
            )
            return

        # ค้นหาหมวดของปุ่มที่ลูกค้าเลือก (0 = หมวดหลัก)
        category = interaction.guild.get_channel(
            self.product["category_id"] or settings.TICKET_CATEGORY_ID
        )

        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "❌ ไม่พบ Category Ticket กรุณาตรวจสอบ ID",
                ephemeral=True
            )
            return

        # สร้างสิทธิ์ของห้อง
        overwrites = {
            interaction.guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            interaction.user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        # อนุญาตให้ Role Support เข้าห้องได้
        support_role = interaction.guild.get_role(
            settings.SUPPORT_ROLE_ID
        )

        if support_role is None:
            await interaction.response.send_message(
                "❌ ไม่พบ Role Support กรุณาตรวจสอบ ID",
                ephemeral=True
            )
            return

        overwrites[support_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True
        )

        # ป้องกันลูกค้ากดยืนยันซ้ำจนได้ห้อง Ticket หลายห้อง
        if self.started or interaction.user.id in creating_ticket_users:
            await interaction.response.send_message(
                "⏳ กำลังสร้าง Ticket อยู่ครับ",
                ephemeral=True
            )
            return

        # จำกัดลูกค้า 1 คนต่อ 1 Ticket ที่เปิดอยู่
        existing_ticket = find_open_ticket(
            interaction.guild,
            interaction.user.id
        )

        if existing_ticket is not None:
            await interaction.response.send_message(
                f"⚠️ คุณมี Ticket ที่เปิดอยู่แล้ว: {existing_ticket.mention}\n"
                "กรุณาติดต่อแอดมินในห้องเดิมครับ",
                ephemeral=True
            )
            return

        self.started = True
        creating_ticket_users.add(interaction.user.id)

        # ตอบ Interaction ก่อนเริ่มสร้างห้อง
        await interaction.response.defer(ephemeral=True)

        try:
            # ชื่อห้อง เช่น nitro-heaven / Topic เช่น "👤 @ลูกค้า · 📦 nitro"
            channel = await interaction.guild.create_text_channel(
                name=make_channel_name(
                    self.product["channel_name"],
                    interaction.user
                ),
                category=category,
                overwrites=overwrites,
                topic=build_ticket_topic(
                    interaction.user.id,
                    self.product["topic_tag"]
                )
            )

            # ส่งข้อมูลคำสั่งซื้อเข้า Ticket

            # ส่วนที่ 1: Embed ต้อนรับในห้อง Ticket
            welcome_embed = discord.Embed(
                title=settings.WELCOME_TITLE or None,
                description=self.product["welcome_text"] or None,
                color=settings.WELCOME_COLOR
            )

            # รูปของสินค้านี้ ถ้าไม่ได้ตั้งไว้ใช้รูปกลางของร้าน (เว้นว่างทั้งคู่ = ไม่แสดง)
            thumbnail_url = (
                self.product["welcome_thumbnail_url"]
                or settings.WELCOME_THUMBNAIL_URL
            )
            image_url = (
                self.product["welcome_image_url"]
                or settings.WELCOME_IMAGE_URL
            )

            if thumbnail_url:
                welcome_embed.set_thumbnail(url=thumbnail_url)

            if image_url:
                welcome_embed.set_image(url=image_url)

            if settings.WELCOME_FOOTER:
                welcome_embed.set_footer(
                    text=settings.WELCOME_FOOTER
                )

            await channel.send(
                content=f"{interaction.user.mention} {support_role.mention}",
                embed=welcome_embed,
                view=TicketControlView()
            )

            # ส่วนที่ 2: ข้อความเน้นตรงกลาง (เว้นว่างในไฟล์ตั้งค่า = ไม่ส่ง)
            if settings.ORDER_NOTICE_TEXT:
                await channel.send(settings.ORDER_NOTICE_TEXT)

            # ส่วนที่ 3: รายละเอียดที่ลูกค้ากรอก
            order_embed = discord.Embed(
                title=ORDER_DETAILS_TITLE,
                description=settings.ORDER_DETAILS_GREETING.replace(
                    "{customer}",
                    interaction.user.mention
                ) or None,
                color=settings.ORDER_DETAILS_COLOR
            )

            add_answer_fields(
                order_embed,
                self.answers,
                name_prefix="📦 ",
                new_lines=True
            )

            await channel.send(embed=order_embed)


            await interaction.edit_original_response(
    content=f"✅ สร้าง Ticket สำเร็จแล้ว: {channel.mention}",
    embed=None,
    view=None
)

            self.stop()

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot ไม่มีสิทธิ์สร้างห้องหรือกำหนด Permission",
                ephemeral=True
            )

        except discord.HTTPException as error:
            print(f"Ticket creation error: {error}")
            await interaction.followup.send(
                "❌ สร้าง Ticket ไม่สำเร็จ กรุณาตรวจสอบ Terminal",
                ephemeral=True
            )

        finally:
            creating_ticket_users.discard(interaction.user.id)

    @discord.ui.button(
        label="ยกเลิก",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ คำสั่งซื้อนี้ไม่ใช่ของคุณ",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "ยกเลิกคำสั่งซื้อแล้วครับ",
            ephemeral=True
        )

        self.stop()



# =====================================================================
#  10. ปุ่มบนหน้าร้าน (ข้อความที่ส่งด้วย /panel)
#  ปุ่มสินค้าสร้างจาก PRODUCTS ใน shop_settings.py แล้วตามด้วยปุ่มสอบถามท้ายสุด
# =====================================================================

class ProductButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"heaven:buy_(?P<product_id>[a-z0-9_]+)"
):
    # ปุ่มสินค้าบนหน้าร้าน 1 ปุ่มต่อ 1 สินค้า
    # custom_id = "heaven:buy_<id สินค้า>" ทำให้ปุ่ม Buy Nitro / Buy Premium
    # บนหน้าร้านที่ส่งไปก่อนหน้านี้ยังใช้งานได้ และปุ่มยังทำงานหลังรีสตาร์ตบอท
    def __init__(self, product_id, product=None):
        button = discord.ui.Button(custom_id=f"heaven:buy_{product_id}")

        if product is not None:
            button.label = product["button_label"]
            button.emoji = product["button_emoji"] or None
            button.style = BUTTON_COLORS[product["button_color"]]

        super().__init__(button)
        self.product_id = product_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["product_id"])

    async def callback(self, interaction: discord.Interaction):
        product = PRODUCTS_BY_ID.get(self.product_id)

        # สินค้าถูกลบออกจากไฟล์ตั้งค่าแล้ว แต่ปุ่มยังอยู่บนหน้าร้านเดิม
        if product is None:
            await interaction.response.send_message(
                "❌ สินค้านี้ไม่เปิดให้สั่งซื้อแล้วครับ",
                ephemeral=True
            )
            return

        # ถ้ามี Ticket ที่เปิดอยู่แล้ว ไม่ต้องให้กรอกฟอร์มใหม่
        if interaction.guild is not None:
            existing_ticket = find_open_ticket(
                interaction.guild,
                interaction.user.id
            )

            if existing_ticket is not None:
                await interaction.response.send_message(
                    f"⚠️ คุณมี Ticket ที่เปิดอยู่แล้ว: {existing_ticket.mention}\n"
                    "กรุณาติดต่อแอดมินในห้องเดิมครับ",
                    ephemeral=True
                )
                return

        await interaction.response.send_modal(
            ProductOrderModal(product)
        )


class SupportButton(discord.ui.Button):
    # ปุ่ม "สอบถาม / แจ้งปัญหา" (ข้อความและเมนูตั้งใน shop_settings.py ส่วน 🔴)
    def __init__(self):
        super().__init__(
            label=settings.BUTTON_SUPPORT_LABEL,
            emoji=settings.BUTTON_SUPPORT_EMOJI or None,
            style=discord.ButtonStyle.danger,
            custom_id="heaven:support"
        )

    async def callback(self, interaction: discord.Interaction):
        # กฎ 1 คนต่อ 1 Ticket นับรวมทุกประเภท (ทั้งสั่งซื้อและสอบถาม)
        if interaction.guild is not None:
            existing_ticket = find_open_ticket(
                interaction.guild,
                interaction.user.id
            )

            if existing_ticket is not None:
                await interaction.response.send_message(
                    f"⚠️ คุณมี Ticket ที่เปิดอยู่แล้ว: {existing_ticket.mention}\n"
                    "กรุณาติดต่อแอดมินในห้องเดิมครับ",
                    ephemeral=True
                )
                return

        await interaction.response.send_modal(
            SupportRequestModal()
        )


class ShopPanelView(discord.ui.View):
    def __init__(self):
        # timeout=None ทำให้ View รองรับการทำงานแบบ persistent
        super().__init__(timeout=None)

        # ปุ่มสินค้าตามลำดับใน shop_settings.py แล้วตามด้วยปุ่มสอบถาม/แจ้งปัญหา
        for product_id, product in PRODUCTS_BY_ID.items():
            self.add_item(ProductButton(product_id, product))

        self.add_item(SupportButton())


# =====================================================================
#  11. เริ่มบอท และคำสั่ง / (Slash Commands)
#  /ping  = ทดสอบว่าบอทออนไลน์
#  /panel = ส่งหน้าร้าน (ต้องมีสิทธิ์ Manage Server)
#
#  ⚠️ ถ้าสร้างปุ่มชุดใหม่ที่ต้องใช้ได้หลังรีสตาร์ตบอท
#     ต้องมี custom_id + timeout=None และเพิ่ม self.add_view(...) ใน setup_hook
# =====================================================================

class ShopBot(commands.Bot):
    async def setup_hook(self):
        # ลงทะเบียน View เพื่อให้ปุ่มเดิมทำงานหลังรีสตาร์ต Bot
        self.add_view(ShopPanelView())
        # ปุ่มสินค้าทุกปุ่ม (รวมปุ่มของสินค้าที่ถูกลบจากไฟล์ตั้งค่าแล้ว)
        self.add_dynamic_items(ProductButton)
        self.add_view(TicketControlView())
        self.add_view(ClosedTicketView())
        self.add_view(DeleteTicketView())
        self.add_view(ReopenedTicketView())
        # ลงทะเบียน Slash Commands เฉพาะเซิร์ฟเวอร์ GUILD_ID (ขึ้นทันที ไม่ต้องรอ)
        guild = discord.Object(id=settings.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        # ล้างคำสั่งแบบทุกเซิร์ฟเวอร์ (Global) ที่เคยลงทะเบียนไว้ ไม่ให้คำสั่งขึ้นซ้ำ 2 อัน
        self.tree.clear_commands(guild=None)
        await self.tree.sync()


intents = discord.Intents.default()

bot = ShopBot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Bot Online: {bot.user}")
    print("Heaven Ticket Shop พร้อมใช้งาน")


@bot.tree.command(
    name="ping",
    description="ทดสอบว่า Bot ทำงานอยู่หรือไม่"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Pong! 🟢 Heaven Ticket Shop พร้อมใช้งาน",
        ephemeral=True
    )


@bot.tree.command(
    name="panel",
    description="ส่งหน้าร้าน Ticket Shop"
)
@app_commands.guild_only()
async def panel(interaction: discord.Interaction):
    # จำกัดคำสั่งนี้ให้ผู้มีสิทธิ์ Manage Server ใช้
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ คุณต้องมีสิทธิ์ Manage Server จึงใช้คำสั่งนี้ได้",
            ephemeral=True
        )
        return

    # ข้อความและรูปตั้งค่าได้ใน shop_settings.py
    embed = discord.Embed(
        title=settings.PANEL_TITLE or None,
        description=settings.PANEL_DESCRIPTION or None,
        color=settings.PANEL_COLOR
    )

    if settings.PANEL_FOOTER:
        embed.set_footer(
            text=settings.PANEL_FOOTER
        )

    if settings.PANEL_IMAGE_URL:
        embed.set_image(url=settings.PANEL_IMAGE_URL)

    await interaction.response.send_message(
        "✅ สร้างหน้าร้านเรียบร้อยแล้ว",
        ephemeral=True
    )

    await interaction.channel.send(
        embed=embed,
        view=ShopPanelView()
    )


bot.run(TOKEN)