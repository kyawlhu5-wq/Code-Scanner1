import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Credentials
API_ID = 31526501
API_HASH = "cf2792e0bcbdb620a31dd65a43f88c8a"
BOT_TOKEN = "8959668914:AAFAE8hLkeUZy6yu8Xa24pl-Bo-pakl4clc"

app = Client("starlink_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DATA_FILE = "vouchers.json"

def load_vouchers():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_vouchers(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ၁။ Note ထဲက Copy ကူးပြီး Paste လုပ်လိုက်သည့် Message များကို အလိုအလျောက် ဖတ်ရှုခြင်း
@app.on_message(filters.text & ~filters.command(["start", "clear"]))
async def handle_bulk_add(client, message: Message):
    lines = message.text.strip().split("\n")
    added_items = []
    vouchers = load_vouchers()

    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2:
            code = parts[0]
            time_left = " ".join(parts[1:])
            vouchers.append({"code": code, "time": time_left})
            added_items.append(f"• `{code}` ({time_left})")

    if added_items:
        save_vouchers(vouchers)
        response_text = "✅ **အောက်ပါ Voucher Code များ စနစ်ထဲ သို့ ထည့်သွင်းပြီးပါပြီ -**\n\n" + "\n".join(added_items)
        await message.reply_text(response_text)
    else:
        await message.reply_text("⚠️ စာသားပုံစံ မမှန်ပါ။\nဥပမာ - `STL-1122-3344 24နာရီ` ပုံစံအတိုင်း ပို့ပေးပါဆရာ။")

# ၂။ /start Command (User များ စာရင်း ကြည့်ရန်)
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Voucher Code များနှင့် သက်တမ်း ကြည့်မည်", callback_data="view_codes")]
    ])
    await message.reply_text(
        "👋 **Starlink Voucher Store မှ ကြိုဆိုပါတယ်!**\n\n"
        "လက်ရှိ ရရှိနိုင်သော Voucher Code များနှင့် သက်တမ်းကို ကြည့်ရန် အောက်ပါ ခလုတ်ကို နှိပ်ပါ -",
        reply_markup=buttons
    )

# ၃။ ခလုတ်နှိပ်ပါက ထည့်ထားသမျှ Code များကို အများသူငာ ကြည့်ရှုနိုင်ခြင်း
@app.on_callback_query(filters.regex("view_codes"))
async def handle_view_codes(client, callback_query: CallbackQuery):
    vouchers = load_vouchers()
    
    if not vouchers:
        await callback_query.message.edit_text(
            "❌ **လောလောဆယ် Voucher Code များ မရှိသေးပါ။**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh ပြုလုပ်မည်", callback_data="view_codes")]])
        )
        return
    
    text = "📋 **အသုံးပြုနိုင်သော Starlink Voucher Codes များ -**\n\n"
    for idx, item in enumerate(vouchers, 1):
        text += f"{idx}. Code: `{item['code']}`\n   ⏳ သက်တမ်း: **{item['time']}**\n\n"
    
    next_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh ပြုလုပ်မည်", callback_data="view_codes")]
    ])
    
    await callback_query.message.edit_text(text, reply_markup=next_button)

# ၄။ Code စာရင်းအားလုံး ပြန်ဖျက်ချင်ပါက သုံးရန် Command (/clear)
@app.on_message(filters.command("clear"))
async def clear_cmd(client, message: Message):
    save_vouchers([])
    await message.reply_text("🗑️ Voucher Code စာရင်း အားလုံးကို ရှင်းလင်းလိုက်ပါပြီ။")

if __name__ == "__main__":
    app.run()
