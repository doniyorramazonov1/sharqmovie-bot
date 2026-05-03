from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, KeyboardButton, InlineKeyboardButton

MENU = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎬 Kinolar")],
    [KeyboardButton(text="🏢 Studiyalar")],
    [KeyboardButton(text="📞 Aloqa")]
], resize_keyboard=True)

ADMIN = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🎬 Kino qo'shish")],
    [KeyboardButton(text="📺 Serial qo'shish"), KeyboardButton(text="📋 Seriallar ro'yxati")],
    [KeyboardButton(text="🏢 Studio qo'shish"), KeyboardButton(text="🗑 Studio o'chirish")],
    [KeyboardButton(text="➕ Reklama qo'shish"), KeyboardButton(text="📋 Reklamalar ro'yxati")],
    [KeyboardButton(text="📢 Reklama yuborish"), KeyboardButton(text="📣 Kanalga post")],
    [KeyboardButton(text="⬅️ Orqaga")]
], resize_keyboard=True)

def sub_keyboard(link):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ A'zo bo'lish", url=link)],
        [InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_sub")]
    ])

def studios_keyboard(studios):
    kb = []
    for s in studios:
        kb.append([InlineKeyboardButton(text=s["name"], callback_data=f"studio_{s['id']}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def delete_studio_keyboard(studios):
    kb = []
    for s in studios:
        kb.append([InlineKeyboardButton(text=f"❌ {s['name']}", callback_data=f"del_studio_{s['id']}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def post_watch_keyboard(bot_username, movie_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Tomosha qilish", url=f"https://t.me/{bot_username}?start=movie_{movie_id}")]
    ])
