import os
import json
import uuid
import re
from datetime import datetime, date
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Credentials
API_ID = 31526501
API_HASH = "cf2792e0bcbdb620a31dd65a43f88c8a"
BOT_TOKEN = "8959668914:AAFAE8hLkeUZy6yu8Xa24pl-Bo-pakl4clc"

app = Client("starlink_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
            InlineKeyboardButton("🎟️ Code အားလုံးကြည့်ရန်", callback_data="btn_list_vouchers"),
            InlineKeyboardButton("➕ Code သစ်ထည့်ရန်", callback_data="btn_add_help")
        ],
        [
            InlineKeyboardButton("👥 User စာရင်းကြည့်ရန်", callback_data="btn_list_users"),
            InlineKeyboardButton("📊 ဒီနေ့အခြေအနေ", callback_data="btn_today_stats")
        ],
        [
            InlineKeyboardButton("📜 Time Logs ကြည့်ရန်", callback_data="btn_time_logs"),
            InlineKeyboardButton("🛠️ Maintenance Mode", callback_data="btn_maintenance_toggle")
        ],
        [
            InlineKeyboardButton("⚙️ အကန့်အသတ် ပြောင်းရန်", callback_data="btn_limit_help"),
            InlineKeyboardButton("💾 Backup ရယူရန်", callback_data="btn_get_backup")
        ]
    ])

# Admin Command Center / Admin Panel
@app.on_message(filters.command(["admin", "သခင်ကြီး", "အဒ်မင်"]))
async def admin_panel_cmd(client, message: Message):
    text = "👑 **မင်္ဂလာပါ ဆရာကျော်လူ။ Admin Panel Command များ ခလုတ် -**\n\nအောက်ပါ ခလုတ်များမှတစ်ဆင့် စနစ်ကို လွယ်ကူစွာ ထိန်းချုပ်နိုင်ပါသည်။"
    await message.reply_text(text, reply_markup=get_admin_panel_keyboard())

# 1. /ထည့်ရန် - Admin Bulk Add Code
# Unicode Telegram commands are handled with regex instead of filters.command().
ADD_COMMAND_RE = re.compile(r"^/ထည့်ရန်(?:@\w+)?(?:\s|\n|$)(.*)$", re.DOTALL)

async def add_vouchers_from_text(client, message: Message, raw_text: str):
    """Parse and save one or more voucher lines.

    Accepted format per line:
        CODE 24နာရီ
        CODE 3ရက်
    """
    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    if not lines:
        await message.reply_text(
            "⚠️ Code မတွေ့ပါ။ Format ကို ဒီလိုပို့ပါ -\n\n"
            "`STL-1122 24နာရီ`\n"
            "`STL-3344 3ရက်`"
        )
        return False

    data = load_data()
    vouchers = data.get("vouchers", [])
    existing_codes = {str(v.get("code", "")) for v in vouchers}

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

        vouchers.append({"code": code, "time": time_left})
        existing_codes.add(code)
        added_count += 1

    if added_count:
        data["vouchers"] = vouchers
        save_data(data)

    result = [f"✅ Voucher Code **{added_count}** ခု ထည့်ပြီးပါပြီ။"]
    if duplicate_count:
        result.append(f"♻️ ထပ်နေသော Code: **{duplicate_count}** ခု")
    if invalid_count:
        result.append(f"⚠️ Format မမှန်သော Line: **{invalid_count}** ခု")

    await message.reply_text("\n".join(result))
    return added_count > 0

@app.on_message(filters.regex(ADD_COMMAND_RE))
async def handle_bulk_add(client, message: Message):
    chat_id = message.chat.id
    match = ADD_COMMAND_RE.match(message.text or "")
    payload = match.group(1).strip() if match else ""

    if not payload:
        pending_add_chats.add(chat_id)
        await message.reply_text(
            "➕ **Code ထည့်ရန် အဆင်သင့်ပါပြီ။**\n\n"
            "Code များကို နောက် message တစ်ခုထဲမှာ တစ်ကြောင်းစီ ပို့ပါ။\n\n"
            "ဥပမာ -\n"
            "`STL-1122 24နာရီ`\n"
            "`STL-3344 3ရက်`"
        )
        return

    pending_add_chats.discard(chat_id)
    await add_vouchers_from_text(client, message, payload)

# After /ထည့်ရန်, accept the next normal text message as the voucher list.
@app.on_message(filters.text & ~filters.regex(r"^/"))
async def handle_pending_bulk_add(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in pending_add_chats:
        return

    pending_add_chats.discard(chat_id)
    await add_vouchers_from_text(client, message, message.text or "")

# Helper to show vouchers dashboard
async def send_vouchers_dashboard(client, chat_id, message_id=None):
    data = load_data()
    vouchers = data.get("vouchers", [])
    
    if not vouchers:
        msg_text = "❌ **လက်ရှိ စနစ်ထဲတွင် Voucher Code များ မရှိသေးပါ။**"
        if message_id:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text)
        else:
            await client.send_message(chat_id=chat_id, text=msg_text)
        return
    
    text = "⚙️ **ADMIN DASHBOARD - လက်ရှိ ရှိနေသော Code များ**\n\n"
    buttons = []
    for idx, item in enumerate(vouchers, 1):
        text += f"{idx}. Code: `{item['code']}` | သက်တမ်း: **{item['time']}**\n"
        buttons.append([InlineKeyboardButton(f"❌ ဖျက်မည်: {item['code']}", callback_data=f"adm_del_{item['code']}")])
    
    buttons.append([InlineKeyboardButton("🗑️ Code အားလုံးကို ဖျက်မည်", callback_data="adm_del_all")])
    buttons.append([InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")])
    
    markup = InlineKeyboardMarkup(buttons)
    if message_id:
        await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=markup)

# 3. /အသုံးပြုသူများ - View Users
@app.on_message(filters.command("အသုံးပြုသူများ"))
async def list_users(client, message: Message):
    await send_users_list(client, message.chat.id)

async def send_users_list(client, chat_id, message_id=None):
    data = load_data()
    users = data.get("users", {})
    if not users:
        msg_text = "❌ **လက်ရှိတွင် စနစ်ထဲ၌ အသုံးပြုသူ မရှိသေးပါ။**"
        if message_id:
            await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg_text)
        else:
            await client.send_message(chat_id=chat_id, text=msg_text)
        return
    
    text = f"👥 **လက်ရှိ စနစ်ထဲရှိ အသုံးပြုသူများ (စုစုပေါင်း: {len(users)} ဦး) -**\n\n"
    for idx, (uid, uinfo) in enumerate(users.items(), 1):
        name = uinfo.get("name", "Unknown")
        username = f"@{uinfo.get('username')}" if uinfo.get("username") else "No Username"
        text += f"{idx}. **{name}** ({username}) | `ID: {uid}`\n"
    
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])
    if message_id:
        await client.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=btn)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=btn)

# 4. /အခြေအနေ - Today Stats
@app.on_message(filters.command("အခြေအနေ"))
async def daily_stats(client, message: Message):
    await send_daily_stats(client, message.chat.id)

async def send_daily_stats(client, chat_id, message_id=None):
    data = load_data()
    user_limits = data.get("user_limits", {})
    users = data.get("users", {})
    today_str = str(date.today())
    limit = data.get("daily_limit", 2)
    
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
            
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])
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

# 5. /ထုတ်ယူသည့်အချိန် - Detailed Logs
@app.on_message(filters.command("ထုတ်ယူသည့်အချိန်"))
async def detailed_logs_cmd(client, message: Message):
    await send_time_logs(client, message.chat.id)

async def send_time_logs(client, chat_id, message_id=None):
    data = load_data()
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

# 6. /ကြေညာ - Broadcast
@app.on_message(filters.command("ကြေညာ"))
async def broadcast_message(client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("⚠️ `/ကြေညာ` ၏ အောက်တွင် စာသား ရိုက်ပေးပါ ဆရာကျော်လူ။\n\nဥပမာ -\n`/ကြေညာ မနက်ဖြန် Code ဖြည့်ပေးပါမည်။`")
        return
    
    broadcast_text = parts[1].strip()
    data = load_data()
    users = data.get("users", {})
    broadcasts = data.get("broadcasts", {})
    
    if not users:
        await message.reply_text("❌ စာပို့ရန် User များ မရှိသေးပါ။")
        return
    
    bc_id = str(uuid.uuid4())[:8]
    sent_list = []
    success_count = 0
    fail_count = 0
    
    sending_msg = await message.reply_text("⏳ **ခဏစောင့်ပါ သခင်ကြီး...**")
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ စာကို ပြန်ဖျက်မည် (Admin Only)", callback_data=f"del_bc_{bc_id}")]])
    
    for uid in users.keys():
        try:
            sent = await client.send_message(chat_id=int(uid), text=broadcast_text, reply_markup=btn)
            sent_list.append({"chat_id": int(uid), "msg_id": sent.id})
            success_count += 1
        except Exception:
            fail_count += 1
            
    admin_sent = await message.reply_text(f"📢 **Broadcast Message:**\n\n{broadcast_text}", reply_markup=btn)
    sent_list.append({"chat_id": admin_sent.chat.id, "msg_id": admin_sent.id})
    
    broadcasts[bc_id] = sent_list
    data["broadcasts"] = broadcasts
    save_data(data)
    
    await sending_msg.edit_text(
        f"📢 **Broadcast ပို့ဆောင်မှု ပြီးစီးပါပြီ!**\n\n"
        f"✅ အောင်မြင်စွာ ပို့ပြီး: **{success_count}** ဦး\n"
        f"❌ ပို့မရသူ: **{fail_count}** ဦး\n"
        f"🆔 Broadcast ID: `{bc_id}`"
    )

# 7. /သီးသန့်စာပို့ရန် - Direct Send Message
@app.on_message(filters.command("သီးသန့်စာပို့ရန်"))
async def send_direct_msg(client, message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("⚠️ `/သီးသန့်စာပို့ရန် <User_ID> <စာသား>` ပုံစံဖြင့် ပို့ပေးပါဆရာ။\n\nဥပမာ - `/သီးသန့်စာပို့ရန် 12345678 မင်္ဂလာပါ`")
        return
    target_id = parts[1].strip()
    msg_to_send = parts[2].strip()
    try:
        await client.send_message(chat_id=int(target_id), text=f"📩 **Admin ထံမှ သီးသန့်စာ -**\n\n{msg_to_send}")
        await message.reply_text("✅ စာကို အောင်မြင်စွာ ပို့လိုက်ပါပြီဆရာ။")
    except Exception as e:
        await message.reply_text(f"❌ စာပို့၍ မရပါ - {e}")

# 8. /ဘန်းမယ် - Ban User
@app.on_message(filters.command("ဘန်းမယ်"))
async def ban_user_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("⚠️ `/ဘန်းမယ် <User_ID>` ပုံစံဖြင့် ရိုက်ပေးပါဆရာ။\n\nဥပမာ - `/ဘန်းမယ် 12345678`")
        return
    target_id = parts[1].strip()
    data = load_data()
    banned = data.get("banned_users", [])
    if target_id not in banned:
        banned.append(target_id)
        data["banned_users"] = banned
        save_data(data)
        await message.reply_text(f"🚫 **User ID (`{target_id}`) ကို အကောင့် ပိတ်လိုက်ပါပြီ!**")
    else:
        await message.reply_text("⚠️ အဆိုပါ User ကို ပိတ်ပြီးသား ဖြစ်ပါသည်။")

# 9. /ဘန်းတာဖြည်မယ် - Unban User
@app.on_message(filters.command("ဘန်းတာဖြည်မယ်"))
async def unban_user_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("⚠️ `/ဘန်းတာဖြည်မယ် <User_ID>` ပုံစံဖြင့် ရိုက်ပေးပါဆရာ။\n\nဥပမာ - `/ဘန်းတာဖြည်မယ် 12345678`")
        return
    target_id = parts[1].strip()
    data = load_data()
    banned = data.get("banned_users", [])
    if target_id in banned:
        banned.remove(target_id)
        data["banned_users"] = banned
        save_data(data)
        await message.reply_text(f"✅ **User ID (`{target_id}`) ကို အကောင့် ပြန်ဖွင့်ပေးလိုက်ပါပြီ!**")
    else:
        await message.reply_text("⚠️ အဆိုပါ User မှာ ပိတ်ထားသော စာရင်းတွင် မရှိပါ။")

# 10. /အကန့်အသတ် - Set Daily Limit
@app.on_message(filters.command("အကန့်အသတ်"))
async def set_limit_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply_text("⚠️ `/အကန့်အသတ် <အရေအတွက်>` ရိုက်ပေးပါဆရာ။\n\nဥပမာ - `/အကန့်အသတ် 3`")
        return
    new_limit = int(parts[1])
    data = load_data()
    data["daily_limit"] = new_limit
    save_data(data)
    await message.reply_text(f"⚙️ **User များ၏ တစ်နေ့တာ ထုတ်ယူခွင့် အကန့်အသတ်ကို ({new_limit}) ကြိမ်သို့ ပြောင်းလဲလိုက်ပါပြီ!**")

# 11. /ဖမ်းမယ် - Search Code or User
@app.on_message(filters.command("ဖမ်းမယ်"))
async def search_cmd(client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("⚠️ `/ဖမ်းမယ် <Code သို့မဟုတ် User_ID>` ရိုက်ရှာပေးပါဆရာ။")
        return
    query = parts[1].strip()
    data = load_data()
    
    results = []
    for v in data.get("vouchers", []):
        if query in v["code"]:
            results.append(f"🎟️ **Voucher:** Code: `{v['code']}` | သက်တမ်း: {v['time']}")
    for uid, uinfo in data.get("users", {}).items():
        if query in uid or query.lower() in uinfo.get("name", "").lower() or query.lower() in uinfo.get("username", "").lower():
            results.append(f"👤 **User:** {uinfo.get('name')} (@{uinfo.get('username')}) | ID: `{uid}`")
            
    if results:
        text = f"🔍 **ရှာဖွေမှု ရလဒ်များ ({query}) -**\n\n" + "\n".join(results)
        await message.reply_text(text)
    else:
        await message.reply_text(f"❌ **{query}** နှင့် ပတ်သက်သော အချက်အလက် ရှာမတွေ့ပါ။")

# 12. /ခနbotရပ်မယ် - Maintenance Mode
@app.on_message(filters.command("ခနbotရပ်မယ်"))
async def maintenance_cmd(client, message: Message):
    parts = message.text.split()
    data = load_data()
    if len(parts) < 2:
        status = "ဖွင့်ထားသည် (ON)" if data.get("maintenance") else "ပိတ်ထားသည် (OFF)"
        await message.reply_text(f"🛠️ **လက်ရှိ ပြင်ဆင်ရေး Maintenance Mode Status:** {status}\n\nပြောင်းရန် - `/ခနbotရပ်မယ် ဖွင့်` သို့မဟုတ် `/ခနbotရပ်မယ် ပိတ်` ရိုက်ပါ။")
        return
    arg = parts[1].strip()
    if arg in ["ဖွင့်", "on"]:
        data["maintenance"] = True
        save_data(data)
        await message.reply_text("🛠️ **Maintenance Mode ကို ဖွင့်လိုက်ပါပြီ (User များ Code ယူ၍ မရတော့ပါ)။**")
    elif arg in ["ပိတ်", "off"]:
        data["maintenance"] = False
        save_data(data)
        await message.reply_text("✅ **Maintenance Mode ကို ပိတ်လိုက်ပါပြီ (User များ ပုံမှန် ယူနိုင်ပါပြီ)။**")

# 13. /backup - Backup File Download
@app.on_message(filters.command("backup"))
async def backup_data_cmd(client, message: Message):
    if os.path.exists(DATA_FILE):
        await message.reply_document(document=DATA_FILE, caption="📥 **စနစ်၏ Backup Data File ဖြစ်ပါတယ်ဆရာကျော်လူ။**")
    else:
        await message.reply_text("❌ Backup လုပ်ရန် Data File မရှိသေးပါ။")

# 14. /pin - Pin Message
@app.on_message(filters.command("pin"))
async def pin_message_cmd(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("⚠️ Pin ထောက်ချင်သော Message ကို Reply ပြန်ပြီး `/pin` ဟု ရိုက်ပေးပါဆရာ။")
        return
    try:
        await message.reply_to_message.pin()
        await message.reply_text("📌 **Message ကို အောင်မြင်စွာ Pin ထောက်လိုက်ပါပြီ!**")
    except Exception as e:
        await message.reply_text(f"❌ Pin ထောက်၍ မရပါ - {e}")

# Admin Panel Button Clicks Callback
@app.on_callback_query(filters.regex(r"^btn_"))
async def handle_admin_buttons(client, callback_query: CallbackQuery):
    data_code = callback_query.data
    chat_id = callback_query.message.chat.id
    msg_id = callback_query.message.id
    
    if data_code == "btn_admin_home":
        text = "👑 **မင်္ဂလာပါ ဆရာကျော်လူ။ Admin Panel Command များ ခလုတ် -**\n\nအောက်ပါ ခလုတ်များမှတစ်ဆင့် စနစ်ကို လွယ်ကူစွာ ထိန်းချုပ်နိုင်ပါသည်။"
        await callback_query.message.edit_text(text, reply_markup=get_admin_panel_keyboard())
    elif data_code == "btn_list_vouchers":
        await send_vouchers_dashboard(client, chat_id, msg_id)
    elif data_code == "btn_add_help":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])
        pending_add_chats.add(chat_id)
        await callback_query.message.edit_text("➕ **Code များ အစုလိုက် ထည့်ရန် -**\n\nအောက်က Code များကို နောက် message တစ်ခုထဲမှာ တစ်ကြောင်းစီ ပို့ပါ။\n\n`STL-1122 24နာရီ`\n`STL-3344 3ရက်`\n\nသို့မဟုတ် `/ထည့်ရန်` ကို အရင်ပို့ပြီး နောက် message မှာ Code များပို့နိုင်ပါတယ်။", reply_markup=btn)
    elif data_code == "btn_list_users":
        await send_users_list(client, chat_id, msg_id)
    elif data_code == "btn_today_stats":
        await send_daily_stats(client, chat_id, msg_id)
    elif data_code == "btn_time_logs":
        await send_time_logs(client, chat_id, msg_id)
    elif data_code == "btn_maintenance_toggle":
        data = load_data()
        data["maintenance"] = not data.get("maintenance", False)
        save_data(data)
        status = "ဖွင့်လိုက်ပါပြီ (ON)" if data["maintenance"] else "ပိတ်လိုက်ပါပြီ (OFF)"
        await callback_query.answer(f"🛠️ Maintenance Mode ကို {status}", show_alert=True)
        await callback_query.message.edit_text(f"⚙️ Maintenance Mode Status: **{status}**", reply_markup=get_admin_panel_keyboard())
    elif data_code == "btn_limit_help":
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel သို့ ပြန်သွားရန်", callback_data="btn_admin_home")]])
        await callback_query.message.edit_text("⚙️ **တစ်နေ့တာ ထုတ်ယူခွင့် အကန့်အသတ် ပြောင်းရန် -**\n\n`/အကန့်အသတ် 3` ဟု ရိုက်ပေးပါ။", reply_markup=btn)
    elif data_code == "btn_get_backup":
        if os.path.exists(DATA_FILE):
            await client.send_document(chat_id=chat_id, document=DATA_FILE, caption="📥 **စနစ်၏ Backup Data File ဖြစ်ပါတယ်ဆရာကျော်လူ။**")
            await callback_query.answer("✅ Backup File ပို့ပေးလိုက်ပါပြီဆရာ။")
        else:
            await callback_query.answer("❌ Backup File မရှိသေးပါ။", show_alert=True)

# Delete Broadcast Callback
@app.on_callback_query(filters.regex(r"^del_bc_"))
async def handle_delete_broadcast(client, callback_query: CallbackQuery):
    bc_id = callback_query.data.replace("del_bc_", "")
    data = load_data()
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
    save_data(data)
    await callback_query.answer(f"✅ User များဆီမှ မက်ဆေ့ခ်ျ ({del_count}) ခုကို ပြန်ဖျက်လိုက်ပါပြီ!", show_alert=True)

# User Command: /start Only
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    user_id = str(message.from_user.id)
    data = load_data()
    
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
    save_data(data)
    
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

# Handle User Get Code
@app.on_callback_query(filters.regex(r"^get_(\d+)$"))
async def handle_user_get_codes(client, callback_query: CallbackQuery):
    user_id = str(callback_query.from_user.id)
    data = load_data()
    
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
    sent_messages = data.get("sent_messages", {})
    
    if len(vouchers) < count:
        await callback_query.answer(f"⚠️ အခုလောလောဆယ် စနစ်ထဲမှာ Voucher Code ({count}) ခု မရှိသေးပါဘူးဆရာ။", show_alert=True)
        return
    
    selected_vouchers = vouchers[:count]
    text = f"📋 **သင်ယူထားသော Starlink Voucher Code ({count}) ခု -**\n\n"
    code_list = []
    for item in selected_vouchers:
        text += f"🔑 Code: `{item['code']}`\n⏳ သက်တမ်း: **{item['time']}**\n\n"
        code_list.append(item['code'])
    
    text += "⚠️ **အသုံးပြုပြီးပါက ချက်ချင်းပဲ အောက်ပါ ခလုတ်ကို နှိပ်၍ code ကိုစာရင်းမှ ဖျက်ပေးပါရန်။**"
    codes_key = ",".join(code_list)
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✅ သုံးပြီးပါပြီ (ဖျက်မည်)", callback_data=f"usr_del_{codes_key}")]])
    
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
    
    chat_id = sent_msg.chat.id
    msg_id = sent_msg.id
    for c in code_list:
        if c not in sent_messages:
            sent_messages[c] = []
        sent_messages[c].append({"chat_id": chat_id, "msg_id": msg_id})
    
    data["sent_messages"] = sent_messages
    save_data(data)

# User Mark as Used
@app.on_callback_query(filters.regex(r"^usr_del_"))
async def handle_user_delete(client, callback_query: CallbackQuery):
    codes_str = callback_query.data.replace("usr_del_", "")
    codes_to_del = codes_str.split(",")
    data = load_data()
    vouchers = data.get("vouchers", [])
    
    vouchers = [v for v in vouchers if v['code'] not in codes_to_del]
    data["vouchers"] = vouchers
    save_data(data)
    
    try:
        await callback_query.message.delete()
    except Exception:
        pass
    await callback_query.answer("✅ Code များကို သုံးပြီးကြောင်း မှတ်သားပြီး ဖျက်လိုက်ပါပြီ။", show_alert=True)

# Admin Delete Action
@app.on_callback_query(filters.regex(r"^adm_del_"))
async def handle_admin_delete(client, callback_query: CallbackQuery):
    action = callback_query.data.replace("adm_del_", "")
    data = load_data()
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
        save_data(data)
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
        save_data(data)
        
        await callback_query.answer(f"✅ Code ({target_code}) ကို ဖျက်လိုက်ပါပြီ။", show_alert=True)
        await send_vouchers_dashboard(client, callback_query.message.chat.id, callback_query.message.id)

if __name__ == "__main__":
    app.run()