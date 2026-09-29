import os
import json
import uuid
import re
import asyncio
from datetime import datetime, date
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ForceReply
)

# Credentials
API_ID = int(os.getenv("API_ID", "31526501"))
API_HASH = os.getenv("API_HASH", "cf2792e0bcbdb620a31dd65a43f88c8a")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8959668914:AAFAE8hLkeUZy6yu8Xa24pl-Bo-pakl4clc")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8775300748"))

app = Client("starlink_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "vouchers.json"
file_lock = asyncio.Lock()
active_transactions = {}

# Json Handling with Lock for Concurrency Safety
def load_data_sync():
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
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_data.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_data

async def load_data():
    async with file_lock:
        return load_data_sync()

async def save_data(data):
    async with file_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

# 👑 Full Button Admin Panel Keyboard Setup
def get_admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎟️ Code များကြည့်ရန်", callback_data="btn_list_vouchers"),
            InlineKeyboardButton("➕ Code ထည့်ရန်", callback_data="btn_add_help")
        ],
        [
            InlineKeyboardButton("👥 User စာရင်း", callback_data="btn_list_users"),
            InlineKeyboardButton("📊 ဒီနေ့အခြေအနေ", callback_data="btn_today_stats")
        ],
        [
            InlineKeyboardButton("📜 Time Logs", callback_data="btn_time_logs"),
            InlineKeyboardButton("🛠️ Maintenance Mode", callback_data="btn_maintenance_toggle")
        ],
        [
            InlineKeyboardButton("📢 Broadcast ပို့ရန်", callback_data="btn_ask_broadcast"),
            InlineKeyboardButton("📩 သီးသန့်စာပို့ရန်", callback_data="btn_ask_direct_msg")
        ],
        [
            InlineKeyboardButton("🚫 User Ban မည်", callback_data="btn_ask_ban"),
            InlineKeyboardButton("✅ Ban ဖြည်မည်", callback_data="btn_ask_unban")
        ],
        [
            InlineKeyboardButton("⚙️ Limit ပြောင်းရန်", callback_data="btn_ask_limit"),
            InlineKeyboardButton("🔍 ရှာဖွေရန်", callback_data="btn_ask_search")
        ],
        [
            InlineKeyboardButton("💾 Backup ရယူရန်", callback_data="btn_get_backup")
        ]
    ])

# Admin Command Handler
@app.on_message(filters.command(["admin", "သခင်ကြီး", "အဒ်မင်"]) & filters.user(ADMIN_ID))
async def admin_panel_cmd(client, message: Message):
    text = "👑 **မင်္ဂလာပါ ဆရာကျော်လူ။ Admin Panel -**\n\nအောက်ပါ ခလုတ်များကို နှိပ်၍ စနစ်ကို စီမံခန့်ခွဲနိုင်ပါသည်။"
    await message.reply_text(text, reply_markup=get_admin_panel_keyboard())

# Bulk Add Logic
async def process_bulk_add(message: Message, raw_text: str):
    lines_text = re.sub(r"^/ထည့်ရန်\s*", "", raw_text).strip()
    if not lines_text:
        await message.reply_text("⚠️ Code များကို ရိုက်ကူး/Paste လုပ်၍ ပြန်ပို့ပေးပါဆရာ။")
        return

    lines = lines_text.split("\n")
    data = await load_data()
    vouchers = data.get("vouchers", [])
    
    added_count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue

        code_match = re.search(r'\b(\d{6,12})\b', line)
        if code_match:
            code = code_match.group(1).strip()
            code_pos = line.find(code)
            duration_part = line[code_pos + len(code):].strip()
            
            cleaned_duration = re.sub(r'[\uD83C-\uDBFF\uDC00-\uDFFF\:\,]', ' ', duration_part)
            cleaned_duration = " ".join(cleaned_duration.split()).strip()
            time_left = cleaned_duration if cleaned_duration else "24 Hours"
        else:
            continue

        if code and time_left:
            if not any(v['code'] == code for v in vouchers):
                vouchers.append({"code": code, "time": time_left})
                added_count += 1

    if added_count > 0:
        data["vouchers"] = vouchers
        await save_data(data)
        await message.reply_text(f"✅ **Voucher Code ({added_count}) ခုကို စနစ်ထဲသို့ ထည့်သွင်းပြီးပါပြီ!**")
        try:
            await message.delete()
        except Exception:
            pass
    else:
        await message.reply_text("⚠️ Code ထည့်သွင်း၍ မရပါ။ Format စစ်ဆေးပေးပါဆရာ။")

# 📥 Interactive ForceReply Listener for Admin Button Actions
@app.on_message(filters.reply & filters.private & filters.user(ADMIN_ID))
async def handle_admin_replies(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user.is_self:
        return

    prompt_text = message.reply_to_message.text or ""
    input_text = message.text or ""

    # 1. Bulk Add Codes
    if "ထည့်သွင်းလိုသော Code များကို အောက်တွင် Paste လုပ်၍ တိုက်ရိုက် ပို့ပေးပါဆရာ" in prompt_text:
        await process_bulk_add(message, input_text)

    # 2. Daily Limit Change
    elif "တစ်နေ့တာ ထုတ်ယူခွင့် အကန့်အသတ် သစ်ကို ရိုက်ထည့်ပေးပါဆရာ" in prompt_text:
        if input_text.isdigit():
            new_limit = int(input_text)
            data = await load_data()
            data["daily_limit"] = new_limit
            await save_data(data)
            await message.reply_text(f"⚙️ **User များ၏ တစ်နေ့တာ အကန့်အသတ်ကို ({new_limit}) ကြိမ်သို့ ပြောင်းလဲပြီးပါပြီ!**")
        else:
            await message.reply_text("⚠️ ဂဏန်း (Number) သာ ရိုက်ထည့်ပေးပါဆရာ။")

    # 3. Ban User
    elif "Ban မည့် User ID ကို ရိုက်ထည့်ပေးပါဆရာ" in prompt_text:
        target_id = input_text.strip()
        data = await load_data()
        banned = data.get("banned_users", [])
        if target_id not in banned:
            banned.append(target_id)
            data["banned_users"] = banned
            await save_data(data)
            await message.reply_text(f"🚫 **User ID (`{target_id}`) ကို ပိတ် (Ban) လိုက်ပါပြီ!**")
        else:
            await message.reply_text("⚠️ အဆိုပါ User မှာ Banned စာရင်းထဲတွင် ရှိပြီးသားဖြစ်ပါသည်။")

    # 4. Unban User
    elif "Ban ဖြည်ပေးမည့် User ID ကို ရိုက်ထည့်ပေးပါဆရာ" in prompt_text:
        target_id = input_text.strip()
        data = await load_data()
        banned = data.get("banned_users", [])
        if target_id in banned:
            banned.remove(target_id)
            data["banned_users"] = banned
            await save_data(data)
            await message.reply_text(f"✅ **User ID (`{target_id}`) ကို Ban ဖြည်ပေးလိုက်ပါပြီ!**")
        else:
            await message.reply_text("⚠️ အဆိုပါ User မှာ Banned စာရင်းထဲတွင် မရှိပါ။")

    # 5. Broadcast Message
    elif "User များအားလုံးထံ ကြေညာလိုသော စာသားကို ပို့ပေးပါဆရာ" in prompt_text:
        broadcast_text = input_text.strip()
        data = await load_data()
        users = data.get("users", {})
        broadcasts = data.get("broadcasts", {})

        if not users:
            await message.reply_text("❌ စာပို့ရန် User မရှိသေးပါ။")
            return

        bc_id = str(uuid.uuid4())[:8]
        sent_list = []
        success, fail = 0, 0
        sending_msg = await message.reply_text("⏳ **ကြေညာစာ စတင် ပို့ဆောင်နေပါသည်...**")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ စာကို ပြန်ဖျက်မည် (Admin Only)", callback_data=f"del_bc_{bc_id}")]])

        for uid in users.keys():
            try:
                sent = await client.send_message(chat_id=int(uid), text=broadcast_text, reply_markup=btn)
                sent_list.append({"chat_id": int(uid), "msg_id": sent.id})
                success += 1
            except Exception:
                fail += 1

        admin_sent = await message.reply_text(f"📢 **Broadcast Message:**\n\n{broadcast_text}", reply_markup=btn)
        sent_list.append({"chat_id": admin_sent.chat.id, "msg_id": admin_sent.id})
        
        broadcasts[bc_id] = sent_list
        data["broadcasts"] = broadcasts
        await save_data(data)

        await sending_msg.edit_text(
            f"📢 **Broadcast ပို့ပြီးပါပြီ!**\n\n✅ အောင်မြင်: **{success}** | ❌ ပို့မရ: **{fail}**\n🆔 Broadcast ID: `{bc_id}`"
        )

    # 6. Direct Message
    elif "သီးသန့်စာပို့ရန် အောက်ပါ ပုံစံအတိုင်း ရိုက်ပေးပါဆရာ" in prompt_text:
        parts = input_text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("⚠️ ပုံစံ မမှန်ပါ။ `<User_ID> <စာသား>` ဟု ရိုက်ပေးပါ။")
            return
        target_id, msg_content = parts[0].strip(), parts[1].strip()
        try:
            await client.send_message(chat_id=int(target_id), text=f"📩 **Admin ထံမှ သီးသန့်စာ -**\n\n{msg_content}")
            await message.reply_text("✅ စာကို အောင်မြင်စွာ ပို့လိုက်ပါပြီဆရာ။")
        except Exception as e:
            await message.reply_text(f"❌ စာပို့၍ မရပါ - {e}")

    # 7. Search
    elif "ရှာဖွေလိုသော Code သို့မဟုတ် User ID / Name ကို ရိုက်ပေးပါဆရာ" in prompt_text:
        query = input_text.strip()
        data = await load_data()
        results = []
        for v in data.get("vouchers", []):
            if query in v["code"]:
                results.append(f"🎟️ **Voucher:** Code: `{v['code']}` | သက်တမ်း: {v['time']}")
        for uid, uinfo in data.get("users", {}).items():
            if query in uid or query.lower() in uinfo.get("name", "").lower() or query.lower() in uinfo.get("username", "").lower():
                results.append(f"👤 **User:** {uinfo.get('name')} (@{uinfo.get('username')}) | ID: `{uid}`")

        if results:
            await message.reply_text(f"🔍 **ရှာဖွေမှု ရလဒ်များ ({query}) -**\n\n" + "\n".join(results))
        else:
            await message.reply_text(f"❌ **{query}** နှင့် ပတ်သက်သော အချက်အလက် ရှာမတွေ့ပါ။")

# 🎛️ Admin Panel Button Callbacks
@app.on_callback_query(filters.regex(r"^btn_") & filters.user(ADMIN_ID))
async def handle_admin_buttons(client, callback_query: CallbackQuery):
    data_code = callback_query.data
    chat_id = callback_query.message.chat.id
    msg_id = callback_query.message.id

    if data_code == "btn_admin_home":
        text = "👑 **မင်္ဂလာပါ ဆရာကျော်လူ။ Admin Panel -**\n\nအောက်ပါ ခလုတ်များကို နှိပ်၍ စနစ်ကို စီမံခန့်ခွဲနိုင်ပါသည်။"
        await callback_query.message.edit_text(text, reply_markup=get_admin_panel_keyboard())

    elif data_code == "btn_list_vouchers":
        await send_vouchers_dashboard(client, chat_id, msg_id)

    elif data_code == "btn_add_help":
        await callback_query.message.reply_text(
            "➕ **ထည့်သွင်းလိုသော Code များကို အောက်တွင် Paste လုပ်၍ တိုက်ရိုက် ပို့ပေးပါဆရာ -**",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_list_users":
        await send_users_list(client, chat_id, msg_id)

    elif data_code == "btn_today_stats":
        await send_daily_stats(client, chat_id, msg_id)

    elif data_code == "btn_time_logs":
        await send_time_logs(client, chat_id, msg_id)

    elif data_code == "btn_maintenance_toggle":
        data = await load_data()
        data["maintenance"] = not data.get("maintenance", False)
        await save_data(data)
        status = "ဖွင့်လိုက်ပါပြီ (ON)" if data["maintenance"] else "ပိတ်လိုက်ပါပြီ (OFF)"
        await callback_query.answer(f"🛠️ Maintenance Mode ကို {status}", show_alert=True)
        await callback_query.message.edit_text(f"⚙️ Maintenance Mode Status: **{status}**", reply_markup=get_admin_panel_keyboard())

    elif data_code == "btn_ask_broadcast":
        await callback_query.message.reply_text(
            "📢 **User များအားလုံးထံ ကြေညာလိုသော စာသားကို ပို့ပေးပါဆရာ -**",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_ask_direct_msg":
        await callback_query.message.reply_text(
            "📩 **သီးသန့်စာပို့ရန် အောက်ပါ ပုံစံအတိုင်း ရိုက်ပေးပါဆရာ -**\n\n`<User_ID> <ပို့လိုသောစာသား>`",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_ask_ban":
        await callback_query.message.reply_text(
            "🚫 **Ban မည့် User ID ကို ရိုက်ထည့်ပေးပါဆရာ -**",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_ask_unban":
        await callback_query.message.reply_text(
            "✅ **Ban ဖြည်ပေးမည့် User ID ကို ရိုက်ထည့်ပေးပါဆရာ -**",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_ask_limit":
        await callback_query.message.reply_text(
            "⚙️ **တစ်နေ့တာ ထုတ်ယူခွင့် အကန့်အသတ် သစ်ကို ရိုက်ထည့်ပေးပါဆရာ -**\n\n*(ဥပမာ- 3)*",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_ask_search":
        await callback_query.message.reply_text(
            "🔍 **ရှာဖွေလိုသော Code သို့မဟုတ် User ID / Name ကို ရိုက်ပေးပါဆရာ -**",
            reply_markup=ForceReply(selective=True)
        )
        await callback_query.answer()

    elif data_code == "btn_get_backup":
        if os.path.exists(DATA_FILE):
            await client.send_document(chat_id=chat_id, document=DATA_FILE, caption="📥 **စနစ်၏ Backup Data File ဖြစ်ပါသည်ဆရာ။**")
            await callback_query.answer("✅ Backup File ပို့ပေးလိုက်ပါပြီ။")
        else:
            await callback_query.answer("❌ Backup File မရှိသေးပါ။", show_alert=True)

# Helper Functions
async def send_vouchers_dashboard(client, chat_id, message_id=None):
    data = await load_data()
    vouchers = data.get("vouchers", [])
    btn_home = InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")

    if not vouchers:
        msg_text = "❌ **လက်ရှိ စနစ်ထဲတွင် Voucher Code များ မရှိသေးပါ။**"
        markup = InlineKeyboardMarkup([[btn_home]])
        if message_id:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text, reply_markup=markup)
        else:
            await client.send_message(chat_id=chat_id, text=msg_text, reply_markup=markup)
        return

    text = "⚙️ **ADMIN DASHBOARD - လက်ရှိ ရှိနေသော Code များ**\n\n"
    buttons = []
    for idx, item in enumerate(vouchers, 1):
        text += f"{idx}. Code: `{item['code']}` | သက်တမ်း: **{item['time']}**\n"
        buttons.append([InlineKeyboardButton(f"❌ ဖျက်မည်: {item['code']}", callback_data=f"adm_del_{item['code']}")])

    buttons.append([InlineKeyboardButton("🗑️ Code အားလုံးကို ဖျက်မည်", callback_data="adm_del_all")])
    buttons.append([btn_home])

    markup = InlineKeyboardMarkup(buttons)
    if message_id:
        await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=markup)

async def send_users_list(client, chat_id, message_id=None):
    data = await load_data()
    users = data.get("users", {})
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])

    if not users:
        msg_text = "❌ **လက်ရှိတွင် စနစ်ထဲ၌ အသုံးပြုသူ မရှိသေးပါ။**"
        if message_id:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text, reply_markup=btn)
        else:
            await client.send_message(chat_id=chat_id, text=msg_text, reply_markup=btn)
        return

    text = f"👥 **လက်ရှိ စနစ်ထဲရှိ အသုံးပြုသူများ (စုစုပေါင်း: {len(users)} ဦး) -**\n\n"
    for idx, (uid, uinfo) in enumerate(users.items(), 1):
        name = uinfo.get("name", "Unknown")
        username = f"@{uinfo.get('username')}" if uinfo.get("username") else "No Username"
        text += f"{idx}. **{name}** ({username}) | `ID: {uid}`\n"

    if message_id:
        await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=btn)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=btn)

async def send_daily_stats(client, chat_id, message_id=None):
    data = await load_data()
    user_limits = data.get("user_limits", {})
    users = data.get("users", {})
    today_str = str(date.today())
    limit = data.get("daily_limit", 2)
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])

    today_records = []
    for uid, urec in user_limits.items():
        if urec.get("date") == today_str:
            uinfo = users.get(uid, {})
            name = uinfo.get("name", "Unknown")
            username = f"@{uinfo.get('username')}" if uinfo.get("username") else "No Username"
            today_records.append({
                "name": name,
                "username": username,
                "count": urec.get("count", 0),
                "total_codes": urec.get("total_codes", 0),
                "codes": urec.get("history", [])
            })

    if not today_records:
        msg_text = "📊 **ဒီနေ့အတွက် User များ Code ထုတ်ယူထားခြင်း မရှိသေးပါ။**"
        if message_id:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text, reply_markup=btn)
        else:
            await client.send_message(chat_id=chat_id, text=msg_text, reply_markup=btn)
        return

    text = f"📊 **ဒီနေ့ ({today_str}) User များ Code ထုတ်ယူမှု အနှစ်ချုပ် -**\n\n"
    for idx, rec in enumerate(today_records, 1):
        codes_str = ", ".join([f"`{c}`" for c in rec["codes"]]) if rec["codes"] else "မရှိပါ"
        text += f"{idx}. **{rec['name']}** ({rec['username']})\n"
        text += f"   • ထုတ်ယူမှု: **{rec['count']}/{limit} ကြိမ်**\n"
        text += f"   • စုစုပေါင်း: **{rec['total_codes']} ခု**\n"
        text += f"   • ယူထားသော Code များ: {codes_str}\n\n"

    if message_id:
        await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=btn)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=btn)

async def send_time_logs(client, chat_id, message_id=None):
    data = await load_data()
    logs = data.get("detailed_logs", [])
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])

    if not logs:
        msg_text = "📜 **ထုတ်ယူထားသော Time Logs မရှိသေးပါ။**"
        if message_id:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text, reply_markup=btn)
        else:
            await client.send_message(chat_id=chat_id, text=msg_text, reply_markup=btn)
        return

    recent_logs = logs[-15:]
    recent_logs.reverse()
    text = f"📜 **အသေးစိတ် Code ထုတ်ယူမှု Time Logs (နောက်ဆုံး {len(recent_logs)} ခု) -**\n\n"
    for idx, log in enumerate(recent_logs, 1):
        name = log.get("name", "Unknown")
        username = f"@{log.get('username')}" if log.get("username") else "No Username"
        user_id = log.get("user_id", "Unknown")
        timestamp = log.get("timestamp", "")
        codes = log.get("codes", [])
        codes_str = ", ".join([f"`{c}`" for c in codes])

        text += f"{idx}. 🕒 **{timestamp}**\n"
        text += f"   👤 User: **{name}** ({username}) | `ID: {user_id}`\n"
        text += f"   🔑 Codes ({len(codes)}ခု): {codes_str}\n\n"

    if message_id:
        await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=btn)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=btn)

# User Command Handlers
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    user_id = str(message.from_user.id)
    data = await load_data()

    if user_id in data.get("banned_users", []):
        await message.reply_text("🚫 **သင့်အကောင့်မှာ စည်းကမ်းဖောက်ဖျက်မှုကြောင့် ပိတ်ခံထားရပါသည်။**")
        return

    users = data.get("users", {})
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    users[user_id] = {
        "name": full_name,
        "username": message.from_user.username or ""
    }
    data["users"] = users
    await save_data(data)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ 1 Code ယူမည်", callback_data="get_1")],
        [InlineKeyboardButton("🎟️ 2 Codes ယူမည်", callback_data="get_2")],
        [InlineKeyboardButton("🎟️ 3 Codes ယူမည်", callback_data="get_3")]
    ])
    await message.reply_text(
        "👋 **သခင်ကြီးဟာ မင့်တို့ဖို့ အပင်ပန်းခံပေးနေပါတယ်!**\n\n"
        "မင်းတို့ လိုအပ်သလောက်ပဲ Voucher Code အရေအတွက်ကို အောက်ပါ ခလုတ်များမှ ရွေးချယ်ပါ -",
        reply_markup=buttons
    )

@app.on_callback_query(filters.regex(r"^get_(\d+)$"))
async def handle_user_get_codes(client, callback_query: CallbackQuery):
    user_id = str(callback_query.from_user.id)
    data = await load_data()

    if user_id in data.get("banned_users", []):
        await callback_query.answer("🚫 သင့်အကောင့်ကို ပိတ်ထားပါသည်။", show_alert=True)
        return

    if data.get("maintenance", False):
        await callback_query.answer("🛠️ လက်ရှိ စနစ်ပြင်ဆင်နေပါသဖြင့် ခဏတာ ပိတ်ထားပါသည်။", show_alert=True)
        return

    first_name = callback_query.from_user.first_name or ""
    last_name = callback_query.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    username = callback_query.from_user.username or ""

    today_str = str(date.today())
    now_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    limit = data.get("daily_limit", 2)

    user_limits = data.get("user_limits", {})
    detailed_logs = data.get("detailed_logs", [])

    user_record = user_limits.get(user_id, {})
    if user_record.get("date") == today_str:
        used_count = user_record.get("count", 0)
        total_codes = user_record.get("total_codes", 0)
        history = user_record.get("history", [])
    else:
        used_count = 0
        total_codes = 0
        history = []

    if used_count >= limit:
        await callback_query.answer(f"⚠️ မင်း ဒီနေ့အတွက် {limit} ကြိမ်ယူပြီးပါပြီ! မနက်ဖြန်မှ ထပ်ယူပေးပါနော်။", show_alert=True)
        return

    count = int(callback_query.data.split("_")[1])
    vouchers = data.get("vouchers", [])

    if len(vouchers) < count:
        await callback_query.answer(f"⚠️ အခုလောလောဆယ် စနစ်ထဲမှာ Voucher Code ({count}) ခု မရှိသေးပါဘူးဆရာ။", show_alert=True)
        return

    selected_vouchers = vouchers[:count]
    data["vouchers"] = vouchers[count:]

    text = f"📋 **သင်ယူထားသော Starlink Voucher Code ({count}) ခု -**\n\n"
    code_list = []
    for item in selected_vouchers:
        text += f"🔑 Code: `{item['code']}`\n⏳ သက်တမ်း: **{item['time']}**\n\n"
        code_list.append(item['code'])

    text += "⚠️ **အသုံးပြုပြီးပါက ချက်ချင်းပဲ အောက်ပါ ခလုတ်ကို နှိပ်၍ အကြောင်းကြားပေးပါရန်။**"

    tx_id = str(uuid.uuid4())[:8]
    active_transactions[tx_id] = code_list

    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✅ သုံးပြီးပါပြီ (ဖျက်မည်)", callback_data=f"usr_del_{tx_id}")]])

    sent_msg = await callback_query.message.reply_text(text, reply_markup=buttons)
    await callback_query.answer()

    history.extend(code_list)
    user_limits[user_id] = {
        "date": today_str,
        "count": used_count + 1,
        "total_codes": total_codes + count,
        "history": history
    }
    data["user_limits"] = user_limits

    detailed_logs.append({
        "timestamp": now_time_str,
        "user_id": user_id,
        "name": full_name,
        "username": username,
        "codes": code_list
    })
    data["detailed_logs"] = detailed_logs

    sent_messages = data.get("sent_messages", {})
    chat_id = sent_msg.chat.id
    msg_id = sent_msg.id
    for c in code_list:
        if c not in sent_messages:
            sent_messages[c] = []
        sent_messages[c].append({"chat_id": chat_id, "msg_id": msg_id})

    data["sent_messages"] = sent_messages
    await save_data(data)

@app.on_callback_query(filters.regex(r"^usr_del_"))
async def handle_user_delete(client, callback_query: CallbackQuery):
    tx_id = callback_query.data.replace("usr_del_", "")
    active_transactions.pop(tx_id, None)
    try:
        await callback_query.message.delete()
    except Exception:
        pass
    await callback_query.answer("✅ Code များကို သုံးပြီးကြောင်း မှတ်သားပြီး ဖျက်လိုက်ပါပြီ။", show_alert=True)

@app.on_callback_query(filters.regex(r"^del_bc_") & filters.user(ADMIN_ID))
async def handle_delete_broadcast(client, callback_query: CallbackQuery):
    bc_id = callback_query.data.replace("del_bc_", "")
    data = await load_data()
    broadcasts = data.get("broadcasts", {})

    if bc_id not in broadcasts:
        await callback_query.answer("⚠️ အဆိုပါ Message သည် ဖျက်ပြီးဖြစ်သည် သို့မဟုတ် စနစ်တွင် မရှိတော့ပါ။", show_alert=True)
        return

    sent_list = broadcasts[bc_id]
    del_count = 0
    for item in sent_list:
        try:
            await client.delete_messages(chat_id=item["chat_id"], message_ids=item["msg_id"])
            del_count += 1
        except Exception:
            pass

    del broadcasts[bc_id]
    data["broadcasts"] = broadcasts
    await save_data(data)
    await callback_query.answer(f"✅ User များဆီမှ မက်ဆေ့ခ်ျ ({del_count}) ခုကို ပြန်ဖျက်လိုက်ပါပြီ!", show_alert=True)

@app.on_callback_query(filters.regex(r"^adm_del_") & filters.user(ADMIN_ID))
async def handle_admin_delete(client, callback_query: CallbackQuery):
    action = callback_query.data.replace("adm_del_", "")
    data = await load_data()
    vouchers = data.get("vouchers", [])
    sent_messages = data.get("sent_messages", {})

    if action == "all":
        for code, msg_list in sent_messages.items():
            for m in msg_list:
                try:
                    await client.delete_messages(chat_id=m["chat_id"], message_ids=m["msg_id"])
                except Exception:
                    pass
        data["vouchers"] = []
        data["sent_messages"] = {}
        await save_data(data)
        await callback_query.message.edit_text("🗑️ **Voucher Code အားလုံးကို အပြီးတိုင် ဖျက်လိုက်ပါပြီ။**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]]))
    else:
        target_code = action
        if target_code in sent_messages:
            for m in sent_messages[target_code]:
                try:
                    await client.delete_messages(chat_id=m["chat_id"], message_ids=m["msg_id"])
                except Exception:
                    pass
            del sent_messages[target_code]

        vouchers = [v for v in vouchers if v['code'] != target_code]
        data["vouchers"] = vouchers
        data["sent_messages"] = sent_messages
        await save_data(data)

        await callback_query.answer(f"✅ Code ({target_code}) ကို ဖျက်လိုက်ပါပြီ။", show_alert=True)
        await send_vouchers_dashboard(client, callback_query.message.chat.id, callback_query.message.id)

if __name__ == "__main__":
    app.run()
