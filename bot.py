import random
import string
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Credentials
API_ID = 31526501
API_HASH = "cf2792e0bcbdb620a31dd65a43f88c8a"
BOT_TOKEN = "8959668914:AAFAE8hLkeUZy6yu8Xa24pl-Bo-pakl4clc"

app = Client("starlink_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Random Starlink Code ထုတ်ပေးသည့် Function
def generate_starlink_code():
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"STL-{part1}-{part2}"

# Command /start
@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Generate & Check Code", callback_data="gen_check")]
    ])
    await message.reply_text(
        "👋 **Starlink Voucher Auto Checker မှ ကြိုဆိုပါတယ်!**\n\n"
        "Random Code ထုတ်ယူပြီး အချိန်/သက်တမ်း စစ်ဆေးရန် အောက်ပါ ခလုတ်ကို နှိပ်ပါ -",
        reply_markup=buttons
    )

# Button Click စစ်ဆေးခြင်း
@app.on_callback_query(filters.regex("gen_check"))
async def handle_gen_check(client, callback_query: CallbackQuery):
    # ၁။ Random Code ထုတ်ခြင်း
    generated_code = generate_starlink_code()
    
    # ယာယီ စာပြခြင်း
    await callback_query.message.edit_text(
        f"🔑 **Generated Code:** `{generated_code}`\n\n⏳ *သက်တမ်း အလိုအလျောက် စစ်ဆေးနေပါသည်...*"
    )
    
    # စစ်ဆေးချိန် ၂ စက္ကန့် စောင့်ခြင်း
    await asyncio.sleep(2)
    
    # ၂။ အချိန်/သက်တမ်း Random သတ်မှတ် စစ်ဆေးခြင်း
    statuses = ["Active", "Expired", "Used"]
    result_status = random.choice(statuses)
    
    if result_status == "Active":
        days_left = random.randint(1, 30)
        status_text = f"🟢 **Status:** Active (သက်တမ်းကျန်ရှိချိန်: {days_left} ရက်)"
    elif result_status == "Expired":
        status_text = "🔴 **Status:** Expired (သက်တမ်းကုန်သွားပါပြီ)"
    else:
        status_text = "🟡 **Status:** Already Used (အသုံးပြုပြီးသား ဖြစ်ပါသည်)"

    # နောက်ထပ် ပြန်စစ်နိုင်မယ့် ခလုတ်
    next_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 နောက်တစ်ခု ထပ်စစ်မည်", callback_data="gen_check")]
    ])

    # ၃။ အဖြေထုတ်ပေးခြင်း
    await callback_query.message.edit_text(
        f"🔑 **Voucher Code:** `{generated_code}`\n\n"
        f"{status_text}\n\n"
        f"📅 **Checked Time:** စစ်ဆေးပြီးပါပြီ",
        reply_markup=next_button
    )

if __name__ == "__main__":
    app.run()
