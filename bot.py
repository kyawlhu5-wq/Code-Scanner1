@app.on_message(filters.document & filters.private)
async def handle_document_add(client, message: Message):
    # Admin စစ်ဆေးရန် (လိုအပ်ပါက Admin ID စစ်ပါ)
    if not message.document.file_name.endswith(('.txt', '.json')):
        return
    
    status_msg = await message.reply_text("⏳ **ဖိုင်ထဲမှ Code များကို ခဏအတွင်း စနစ်ထဲသို့ ထည့်သွင်းနေပါသည်...**")
    
    # ဖိုင်ကို Download ဆွဲမည်
    file_path = await message.download()
    
    data = load_data()
    vouchers = data.get("vouchers", [])
    added_count = 0
    
    # TXT ဖိုင်ဖြစ်ပါက line တစ်ကြောင်းချင်း ရိုးရိုးရှင်းရှင်း ဖတ်မည် (Regex မသုံးဘဲ Fast Split)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Space (သို့) Tab နဲ့ ပိုင်းခြားထားပါက ပထမစာလုံးကို Code၊ ဒုတိယစာလုံးကို Duration ဟု ယူမည်
            parts = line.split(maxsplit=1)
            code = parts[0].strip()
            duration = parts[1].strip() if len(parts) > 1 else "24 Hours"
            
            # စနစ်ထဲ တန်းထည့်မည်
            vouchers.append({"code": code, "time": duration})
            added_count += 1

    data["vouchers"] = vouchers
    save_data(data)
    
    # ဒေါင်းလုဒ်ဆွဲထားသော ယာယီဖိုင်ကို ဖျက်မည်
    if os.path.exists(file_path):
        os.remove(file_path)
        
    await status_msg.edit_text(f"✅ **ဖိုင်ထဲမှ Voucher Code ({added_count}) ခုကို စက္ကန့်ပိုင်းအတွင်း အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ!**")
