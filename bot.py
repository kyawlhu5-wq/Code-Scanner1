import os
import json
import uuid
import re
from datetime import datetime, date
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Credentials
API_ID = YOUR_API_ID
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

app = Client(
    "starlink_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

DATA_FILE = "vouchers.json"

# Chat IDs waiting for the next message to contain voucher codes
pending_add_chats = set()


# Helper Functions for Data Storage
def load_data():
    default_data = {
        "vouchers": [],
        "sent_messages": {},
        "user_limits": {},
        "users": {},
        "broadcasts": {},
        "detailed_logs": [],
        "banned_users": [],
        "daily_limit": 2,
        "maintenance": False
    }

    if not os.path.exists(DATA_FILE):
        return default_data

    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)

            for k, v in default_data.items():
                if k not in data:
                    data[k] = v

            return data

        except Exception:
            return default_data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎟️ Code အားလုံးကြည့်ရန်",
                callback_data="btn_list_vouchers"
            ),
            InlineKeyboardButton(
                "➕ Code သစ်ထည့်ရန်",
                callback_data="btn_add_help"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 User စာရင်းကြည့်ရန်",
                callback_data="btn_list_users"
            ),
            InlineKeyboardButton(
                "📊 ဒီနေ့အခြေအနေ",
                callback_data="btn_today_stats"
            )
        ],
        [
            InlineKeyboardButton(
                "📜 Time Logs ကြည့်ရန်",
                callback_data="btn_time_logs"
            ),
            InlineKeyboardButton(
                "🛠️ Maintenance Mode",
                callback_data="btn_maintenance_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                "⚙️ အကန့်အသတ် ပြောင်းရန်",
                callback_data="btn_limit_help"
            ),
            InlineKeyboardButton(
                "💾 Backup ရယူရန်",
                callback_data="btn_get_backup"
            )
        ]
    ])


# Admin Command Center / Admin Panel
@app.on_message(
    filters.command(["admin", "သခင်ကြီး", "အဒ်မင်"])
)
async def admin_panel_cmd(client, message: Message):

    text = (
        "👑 **မင်္ဂလာပါ ဆရာကျော်လူ။ "
        "Admin Panel Command များ ခလုတ် -**\n\n"
        "အောက်ပါ ခလုတ်များမှတစ်ဆင့် "
        "စနစ်ကို လွယ်ကူစွာ ထိန်းချုပ်နိုင်ပါသည်။"
    )

    await message.reply_text(
        text,
        reply_markup=get_admin_panel_keyboard()
    )


# ============================================================
# 1. ADD VOUCHERS
# ============================================================

# Unicode Telegram command ကို regex နဲ့ဖမ်းမယ်
ADD_COMMAND_RE = re.compile(
    r"^/ထည့်ရန်(?:@\w+)?(?:\s|\n|$)(.*)$",
    re.DOTALL
)


async def add_vouchers_from_text(
    client,
    message: Message,
    raw_text: str
):
    """
    Accepted format:

    STL-1122 24နာရီ
    STL-3344 3ရက်
    STL-5566 7ရက်
    """

    lines = [
        line.strip()
        for line in raw_text.strip().splitlines()
        if line.strip()
    ]

    if not lines:
        await message.reply_text(
            "⚠️ Code မတွေ့ပါ။ Format ကို ဒီလိုပို့ပါ -\n\n"
            "`STL-1122 24နာရီ`\n"
            "`STL-3344 3ရက်`"
        )
        return False

    data = load_data()
    vouchers = data.get("vouchers", [])

    existing_codes = {
        str(v.get("code", ""))
        for v in vouchers
    }

    added_count = 0
    duplicate_count = 0
    invalid_count = 0

    for line in lines:

        parts = line.split(maxsplit=1)

        if len(parts) < 2:
            invalid_count += 1
            continue

        code = parts[0].strip()
        time_left = parts[1].strip()

        if not code or not time_left:
            invalid_count += 1
            continue

        if code in existing_codes:
            duplicate_count += 1
            continue

        vouchers.append({
            "code": code,
            "time": time_left
        })

        existing_codes.add(code)
        added_count += 1

    if added_count > 0:
        data["vouchers"] = vouchers
        save_data(data)

    result = [
        f"✅ Voucher Code **{added_count}** ခု ထည့်ပြီးပါပြီ။"
    ]

    if duplicate_count > 0:
        result.append(
            f"♻️ ထပ်နေသော Code: **{duplicate_count}** ခု"
        )

    if invalid_count > 0:
        result.append(
            f"⚠️ Format မမှန်သော Line: **{invalid_count}** ခု"
        )

    await message.reply_text(
        "\n".join(result)
    )

    return added_count > 0


@app.on_message(filters.regex(ADD_COMMAND_RE))
async def handle_bulk_add(client, message: Message):

    chat_id = message.chat.id

    match = ADD_COMMAND_RE.match(
        message.text or ""
    )

    payload = (
        match.group(1).strip()
        if match
        else ""
    )

    # /ထည့်ရန် ပဲပို့ထားရင်
    # နောက် message မှာ Code စောင့်မယ်
    if not payload:

        pending_add_chats.add(chat_id)

        await message.reply_text(
            "➕ **Code ထည့်ရန် အဆင်သင့်ပါပြီ။**\n\n"
            "Code များကို နောက် message တစ်ခုထဲမှာ "
            "တစ်ကြောင်းစီ ပို့ပါ။\n\n"
            "ဥပမာ -\n"
            "`STL-1122 24နာရီ`\n"
            "`STL-3344 3ရက်`"
        )

        return

    pending_add_chats.discard(chat_id)

    await add_vouchers_from_text(
        client,
        message,
        payload
    )


# Button နှိပ်ပြီးနောက်
# နောက် message မှာ Code တိုက်ရိုက်ပို့လို့ရမယ်
@app.on_message(
    filters.text & ~filters.regex(r"^/")
)
async def handle_pending_bulk_add(
    client,
    message: Message
):

    chat_id = message.chat.id

    if chat_id not in pending_add_chats:
        return

    pending_add_chats.discard(chat_id)

    await add_vouchers_from_text(
        client,
        message,
        message.text or ""
    )


# ============================================================
# VOUCHER DASHBOARD
# ============================================================

async def send_vouchers_dashboard(
    client,
    chat_id,
    message_id=None
):

    data = load_data()
    vouchers = data.get("vouchers", [])

    if not vouchers:

        msg_text = (
            "❌ **လက်ရှိ စနစ်ထဲတွင် "
            "Voucher Code များ မရှိသေးပါ။**"
        )

        if message_id:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=msg_text
            )
        else:
            await client.send_message(
                chat_id=chat_id,
                text=msg_text
            )

        return

    text = (
        "⚙️ **ADMIN DASHBOARD - "
        "လက်ရှိ ရှိနေသော Code များ**\n\n"
    )

    buttons = []

    for idx, item in enumerate(vouchers, 1):

        text += (
            f"{idx}. Code: `{item['code']}` | "
            f"သက်တမ်း: **{item['time']}**\n"
        )

        buttons.append([
            InlineKeyboardButton(
                f"❌ ဖျက်မည်: {item['code']}",
                callback_data=f"adm_del_{item['code']}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🗑️ Code အားလုံးကို ဖျက်မည်",
            callback_data="adm_del_all"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Admin Panel သို့ ပြန်သွားရန်",
            callback_data="btn_admin_home"
        )
    ])

    markup = InlineKeyboardMarkup(buttons)

    if message_id:

        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup
        )

    else:

        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup
        )


# ============================================================
# 3. USERS
# ============================================================

@app.on_message(filters.command("အသုံးပြုသူများ"))
async def list_users(client, message: Message):

    await send_users_list(
        client,
        message.chat.id
    )


async def send_users_list(
    client,
    chat_id,
    message_id=None
):

    data = load_data()
    users = data.get("users", {})

    if not users:

        msg_text = (
            "❌ **လက်ရှိတွင် စနစ်ထဲ၌ "
            "အသုံးပြုသူ မရှိသေးပါ။**"
        )

        if message_id:

            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=msg_text
            )

        else:

            await client.send_message(
                chat_id=chat_id,
                text=msg_text
            )

        return

    text = (
        f"👥 **လက်ရှိ စနစ်ထဲရှိ အသုံးပြုသူများ "
        f"(စုစုပေါင်း: {len(users)} ဦး) -**\n\n"
    )

    for idx, (uid, uinfo) in enumerate(
        users.items(),
        1
    ):

        name = uinfo.get(
            "name",
            "Unknown"
        )

        username = (
            f"@{uinfo.get('username')}"
            if uinfo.get("username")
            else "No Username"
        )

        text += (
            f"{idx}. **{name}** "
            f"({username}) | `ID: {uid}`\n"
        )

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Admin Panel သို့ ပြန်သွားရန်",
                callback_data="btn_admin_home"
            )
        ]
    ])

    if message_id:

        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=btn
        )

    else:

        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=btn
        )


# ============================================================
# 4. TODAY STATS
# ============================================================

@app.on_message(filters.command("အခြေအနေ"))
async def daily_stats(client, message: Message):

    await send_daily_stats(
        client,
        message.chat.id
    )


async def send_daily_stats(
    client,
    chat_id,
    message_id=None
):

    data = load_data()

    user_limits = data.get(
        "user_limits",
        {}
    )

    users = data.get(
        "users",
        {}
    )

    today_str = str(date.today())

    limit = data.get(
        "daily_limit",
        2
    )

    today_records = []

    for uid, urec in user_limits.items():

        if urec.get("date") == today_str:

            uinfo = users.get(
                uid,
                {}
            )

            name = uinfo.get(
                "name",
                "Unknown"
            )

            username = (
                f"@{uinfo.get('username')}"
                if uinfo.get("username")
                else "No Username"
            )

            today_records.append({
                "name": name,
                "username": username,
                "count": urec.get("count", 0),
                "total_codes": urec.get(
                    "total_codes",
                    0
                ),
                "codes": urec.get(
                    "history",
                    []
                )
            })

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Admin Panel သို့ ပြန်သွားရန်",
                callback_data="btn_admin_home"
            )
        ]
    ])

    if not today_records:

        msg_text = (
            "📊 **ဒီနေ့အတွက် User များ "
            "Code ထုတ်ယူထားခြင်း မရှိသေးပါ။**"
        )

        if message_id:

            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=msg_text,
                reply_markup=btn
            )

        else:

            await client.send_message(
                chat_id=chat_id,
                text=msg_text,
                reply_markup=btn
            )

        return

    text = (
        f"📊 **ဒီနေ့ ({today_str}) User များ "
        f"Code ထုတ်ယူမှု အနှစ်ချုပ် -**\n\n"
    )

    for idx, rec in enumerate(
        today_records,
        1
    ):

        codes_str = (
            ", ".join(
                [f"`{c}`" for c in rec["codes"]]
            )
            if rec["codes"]
            else "မရှိပါ"
        )

        text += (
            f"{idx}. **{rec['name']}** "
            f"({rec['username']})\n"
        )

        text += (
            f"   • ထုတ်ယူမှု: "
            f"**{rec['count']}/{limit} ကြိမ်**\n"
        )

        text += (
            f"   • စုစုပေါင်း: "
            f"**{rec['total_codes']} ခု**\n"
        )

        text += (
            f"   • ယူထားသော Code များ: "
            f"{codes_str}\n\n"
        )

    if message_id:

        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=btn
        )

    else:

        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=btn
        )


# ============================================================
# 5. TIME LOGS
# ============================================================

@app.on_message(filters.command("ထုတ်ယူသည့်အချိန်"))
async def detailed_logs_cmd(
    client,
    message: Message
):

    await send_time_logs(
        client,
        message.chat.id
    )


async def send_time_logs(
    client,
    chat_id,
    message_id=None
):

    data = load_data()

    logs = data.get(
        "detailed_logs",
        []
    )

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Admin Panel သို့ ပြန်သွားရန်",
                callback_data="btn_admin_home"
            )
        ]
    ])

    if not logs:

        msg_text = (
            "📜 **ထုတ်ယူထားသော Time Logs "
            "မရှိသေးပါ။**"
        )

        if message_id:

            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=msg_text,
                reply_markup=btn
            )

        else:

            await client.send_message(
                chat_id=chat_id,
                text=msg_text,
                reply_markup=btn
            )

        return

    recent_logs = logs[-15:]
    recent_logs.reverse()

    text = (
        f"📜 **အသေးစိတ် Code ထုတ်ယူမှု "
        f"Time Logs (နောက်ဆုံး "
        f"{len(recent_logs)} ခု) -**\n\n"
    )

    for idx, log in enumerate(
        recent_logs,
        1
    ):

        name = log.get(
            "name",
            "Unknown"
        )

        username = (
            f"@{log.get('username')}"
            if log.get("username")
            else "No Username"
        )

        user_id = log.get(
            "user_id",
            "Unknown"
        )

        timestamp = log.get(
            "timestamp",
            ""
        )

        codes = log.get(
            "codes",
            []
        )

        codes_str = ", ".join(
            [f"`{c}`" for c in codes]
        )

        text += (
            f"{idx}. 🕒 **{timestamp}**\n"
        )

        text += (
            f"   👤 User: **{name}** "
            f"({username}) | `ID: {user_id}`\n"
        )

        text += (
            f"   🔑 Codes ({len(codes)}ခု): "
            f"{codes_str}\n\n"
        )

    if message_id:

        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=btn
        )

    else:

        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=btn
        )
