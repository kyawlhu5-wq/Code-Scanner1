import os
import json
from datetime import date
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Credentials
API_ID = 31526501
API_HASH = "cf2792e0bcbdb620a31dd65a43f88c8a"
BOT_TOKEN = "8959668914:AAFAE8hLkeUZy6yu8Xa24pl-Bo-pakl4clc"

app = Client("starlink_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "vouchers.json"

# Daily Limit Setting
DAILY_LIMIT = 2

# Helper Functions for Data Storage
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"vouchers": [], "sent_messages": {}, "user_limits": {}, "users": {}}
    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
            if "user_limits" not in data:
                data["user_limits"] = {}
            if "users" not in data:
                data["users"] = {}
            return data
        except Exception:
            return {"vouchers": [], "sent_messages": {}, "user_limits": {}, "users": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 1. Admin Bulk Add Code via /add Command
@app.on_message(filters.command("add"))
async def handle_bulk_add(client, message: Message):
    raw_text = message.text.replace("/add", "", 1).strip()
    
    if not raw_text:
        await message.reply_text("⚠️ `/add` ၏ အောက်တွင် Code များကို Paste လုပ်၍ ပို့ပေးပါ ဆရာကျော်လူ။\n\nဥပမာ -\n`/add`\n`STL-1122 24နာရီ`\n`STL-3344 3ရက်`")
        return

    lines = raw_text.split("\n")
    data = load_data()
    vouchers = data.get("vouchers", [])
    
    added_count = 0
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2:
            code = parts[0]
            time_left = " ".join(parts[1:])
            if not any(v['code'] == code for v in vouchers):
                vouchers.append({"code": code, "time": time_left})
                added_count += 1

    if added_count > 0:
        data["vouchers"] = vouchers
        save_data(data)
        
        await message.reply_text(f"✅ **Voucher Code ({added_count}) ခုကို စနစ်ထဲသို့ ထည့်သွင်းပြီးပါပြီ!**")
        try:
            await message.delete()
        except Exception:
            pass
    else:
        await message.reply_text("⚠️ `/add` ၏ အောက်တွင် Code များကို Paste လုပ်၍ ပို့ပေးပါ ဆရာကျော်လူ။\n\nဥပမာ -\n`/add`\n`STL-1122 24နာရီ` ပုံစံအတိုင်း ပို့ပေးပါဆရာ။")

# 2. Admin Dashboard Command (/admin)
@app.on_message(filters.command("admin"))
async def admin_dashboard(client, message: Message):
    data = load_data()
    vouchers = data.get("vouchers", [])
    
    if not vouchers:
        await message.reply_text("❌ **လက်ရှိ စနစ်ထဲတွင် Voucher Code များ မရှိသေးပါ။**")
        return
    
    text = "⚙️ **ADMIN DASHBOARD - လက်ရှိ ရှိနေသော Code များ**\n\n"
    buttons = []
    
    for idx, item in enumerate(vouchers, 1):
        text += f"{idx}. Code: `{item['code']}` | သက်တမ်း: **{item['time']}**\n"
        buttons.append([InlineKeyboardButton(f"❌ ဖျက်မည်: {item['code']}", callback_data=f"adm_del_{item['code']}")])
    
    buttons.append([InlineKeyboardButton("🗑️ Code အားလုံးကို ဖျက်မည်", callback_data="adm_del_all")])
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# 3. View Users Command (/users) - Admin Only
@app.on_message(filters.command("users"))
async def list_users(client, message: Message):
    data = load_data()
    users = data.get("users", {})
    
    if not users:
        await message.reply_text("❌ **လက်ရှိတွင် စနစ်ထဲ၌ အသုံးပြုသူ (User) မရှိသေးပါ။**")
        return
    
    text = f"👥 **လက်ရှိ စနစ်ထဲရှိ အသုံးပြုသူများ (စုစုပေါင်း: {len(users)} ဦး) -**\n\n"
    for idx, (uid, uinfo) in enumerate(users.items(), 1):
        name = uinfo.get("name", "Unknown")
        username = f"@{uinfo.get('username')}" if uinfo.get("username") else "No Username"
        text += f"{idx}. **{name}** ({username}) | `ID: {uid}`\n"
    
    await message.reply_text(text)

# 4. Broadcast Command (/broadcast) - Send Message to All Users
@app.on_message(filters.command("broadcast"))
async def broadcast_message(client, message: Message):
    broadcast_text = message.text.replace("/broadcast", "", 1).strip()
    
    if not broadcast_text:
        await message.reply_text("⚠️ `/broadcast` ၏ အောက်တွင် အားလုံးဆီ ပို့ချင်သော စာသားကို ရိုက်ပေးပါ ဆရာကျော်လူ။\n\nဥပမာ -\n`/broadcast`\n`မနက်ဖြန် Code ဖြည့်ပေးပါမည်။`")
        return
    
    data = load_data()
    users = data.get("users", {})
    
    if not users:
        await message.reply_text("❌ စာပို့ရန် User များ မရှိသေးပါ။")
        return
    
    success_count = 0
    fail_count = 0
    
    sending_msg = await message.reply_text("⏳ **User များဆီသို့ စာပို့နေပါသည်။ ခဏစောင့်ပါ...**")
    
    for uid in users.keys():
        try:
            await client.send_message(chat_id=int(uid), text=broadcast_text)
            success_count += 1
        except Exception:
            fail_count += 1
            
    await sending_msg.edit_text(
        f"📢 **Broadcast ပို့ဆောင်မှု ပြီးစီးပါပြီ!**\n\n"
        f"✅ အောင်မြင်စွာ ပို့ပြီး: **{success_count}** ဦး\n"
        f"❌ ပို့မရသူ (Bot မသုံးတော့သူ): **{fail_count}** ဦး"
    )

# 5. Pin Message Command (/pin) - Reply to any message and type /pin
@app.on_message(filters.command("pin"))
async def pin_message_cmd(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("⚠️ Pin ထောက်ချင်သော Message ကို Reply ပြန်ပြီး `/pin` ဟု ရိုက်ပေးပါ ဆရာကျော်လူ။")
        return
    
    try:
        await message.reply_to_message.pin()
        await message.reply_text("📌 **Message ကို အောင်မြင်စွာ Pin ထောက်လိုက်ပါပြီ!**")
    except Exception as e:
        await message.reply_text(f"❌ **Pin ထောက်၍ မရပါ (Bot တွင် Pin Message Permission ရှိမရှိ စစ်ဆေးပါ) -** {e}")

# 6. User Command (/start)
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    data = load_data()
    users = data.get("users", {})
    
    # Save User Info automatically
    user_id = str(message.from_user.id)
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

# 7. Handle Code Distribution for Users (With Daily 2-Times Limit)
@app.on_callback_query(filters.regex(r"^get_(\d+)$"))
async def handle_user_get_codes(client, callback_query: CallbackQuery):
    user_id = str(callback_query.from_user.id)
    today_str = str(date.today())
    
    data = load_data()
    user_limits = data.get("user_limits", {})
    
    # User Daily Limit Check
    user_record = user_limits.get(user_id, {})
    if user_record.get("date") == today_str:
        used_count = user_record.get("count", 0)
    else:
        used_count = 0
        
    if used_count >= DAILY_LIMIT:
        await callback_query.answer("⚠️ မင်း ဒီနေ့အတွက် ၂ ကြိမ်ယူပြီးပါပြီ! မနက်ဖြန်မှ ထပ်ယူပေးပါနော်။", show_alert=True)
        return

    count = int(callback_query.data.split("_")[1])
    vouchers = data.get("vouchers", [])
    sent_messages = data.get("sent_messages", {})
    
    if len(vouchers) < count:
        await callback_query.answer(f"⚠️ အခုလောလောဆယ်တော့ စနစ်ထဲမှာ Voucher Code ({count}) ခု မရှိသေးဘူးနော် ကိုယ့်ဆရာ။", show_alert=True)
        return
    
    selected_vouchers = vouchers[:count]
    
    text = f"📋 **သင်ယူထားသော Starlink Voucher Code ({count}) ခု -**\n\n"
    code_list = []
    for item in selected_vouchers:
        text += f"🔑 Code: `{item['code']}`\n⏳ သက်တမ်း: **{item['time']}**\n\n"
        code_list.append(item['code'])
    
    text += "⚠️ **အသုံးပြုပြီးပါက ချက်ချင်းပဲ အောက်ပါ ခလုတ်ကို နှိပ်၍ code ကိုစာရင်းမှ ဖျက်ပေးပါရန်။**"
    
    codes_key = ",".join(code_list)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ သုံးပြီးပါပြီ (ဖျက်မည်)", callback_data=f"usr_del_{codes_key}")]
    ])
    
    sent_msg = await callback_query.message.reply_text(text, reply_markup=buttons)
    await callback_query.answer()
    
    # Update Daily Limit
    user_limits[user_id] = {
        "date": today_str,
        "count": used_count + 1
    }
    data["user_limits"] = user_limits
    
    chat_id = sent_msg.chat.id
    msg_id = sent_msg.id
    
    for c in code_list:
        if c not in sent_messages:
            sent_messages[c] = []
        sent_messages[c].append({"chat_id": chat_id, "msg_id": msg_id})
    
    data["sent_messages"] = sent_messages
    save_data(data)

# 8. User Mark as Used / Delete Action
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

# 9. Admin Delete Action (Synchronized Global Deletion)
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
        await callback_query.message.edit_text("🗑️ **Voucher Code အားလုံးကို အပြီးတိုင် ဖျက်လိုက်ပါပြီ။**")
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
        
        if not vouchers:
            await callback_query.message.edit_text("❌ **လက်ရှိ စနစ်ထဲတွင် Voucher Code များ မရှိတော့ပါ။**")
        else:
            text = "⚙️ **ADMIN DASHBOARD - လက်ရှိ ရှိနေသော Code များ**\n\n"
            buttons = []
            for idx, item in enumerate(vouchers, 1):
                text += f"{idx}. Code: `{item['code']}` | သက်တမ်း: **{item['time']}**\n"
                buttons.append([InlineKeyboardButton(f"❌ ဖျက်မည်: {item['code']}", callback_data=f"adm_del_{item['code']}")])
            buttons.append([InlineKeyboardButton("🗑️ Code အားလုံးကို ဖျက်မည်", callback_data="adm_del_all")])
            await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

if __name__ == "__main__":
    app.run()
