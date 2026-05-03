from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from config import BOT_TOKEN, ADMIN_IDS, REQUIRED_CHANNEL, PRIVATE_CHANNEL, PUBLIC_CHANNEL
import database as db
import keyboards as kb

router = Router()
admin_states = {}

def is_admin(uid):
    return uid in ADMIN_IDS

async def check_subscription(uid, bot):
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, uid)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

@router.message(CommandStart())
async def cmd_start(msg: Message):
    args = msg.text.split()
    referral_id = None
    movie_id = None
    for a in args[1:]:
        if a.startswith("ref_"):
            try: referral_id = int(a[4:])
            except: pass
        elif a.startswith("movie_"):
            try: movie_id = int(a[6:])
            except: pass

    db.add_user(msg.from_user.id, msg.from_user.username, referral_id)

    if movie_id:
        movie = db.get_movie(movie_id)
        if movie and movie["file_id"]:
            cap = f"🎬 {movie['title']}\n\n{movie.get('description', '')}"
            await msg.bot.send_video(msg.from_user.id, movie["file_id"], caption=cap)
            return

    if not await check_subscription(msg.from_user.id, msg.bot):
        await msg.answer("🔒 Botni ishlatish uchun kanalga a'zo bo'ling:", reply_markup=kb.sub_keyboard(REQUIRED_CHANNEL))
        return

    await msg.answer("🎬 Sharq Movie\n\nFilmlarni ko'rish uchun menudan foydalaning:", reply_markup=kb.MENU)

@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    await msg.answer("🔐 Admin panel", reply_markup=kb.ADMIN)

@router.message(F.text == "🎬 Kinolar")
async def all_movies(msg: Message):
    await msg.answer("🎬 Barcha kinolar")
    await msg.answer("Hozircha kinolar yo'q" if not db.get_all_studios() else "Studiyalardan tanlang:", reply_markup=kb.MENU)

@router.message(F.text == "🏢 Studiyalar")
async def list_studios(msg: Message):
    studios = db.get_all_studios()
    if not studios:
        await msg.answer("🏢 Studiyalar yo'q", reply_markup=kb.MENU)
        return
    await msg.answer("🏢 Studiyalar:", reply_markup=kb.studios_keyboard(studios))

@router.message(F.text == "📞 Aloqa")
async def contact(msg: Message):
    await msg.answer("📞 Aloqa: @sharqtech_admin", reply_markup=kb.MENU)

@router.callback_query(F.data == "check_sub")
async def check_sub_cb(cb: CallbackQuery):
    if await check_subscription(cb.from_user.id, cb.bot):
        await cb.answer("✅ A'zo bo'ldingiz!")
        await cb.message.edit_text("✅ Xush kelibsiz!")
        await cb.message.answer("🎬 Sharq Movie", reply_markup=kb.MENU)
    else:
        await cb.answer("A'zo bo'lmagansiz!", show_alert=True)

@router.callback_query(F.data.startswith("studio_"))
async def studio_movies_cb(cb: CallbackQuery):
    sid = int(cb.data[7:])
    movies = db.get_movies_by_studio(sid)
    if not movies:
        await cb.answer("Bu studiyada kino yo'q", show_alert=True)
        return
    await cb.message.edit_text("🎬 Kinolar:", reply_markup=kb.movies_keyboard(movies))

@router.callback_query(F.data.startswith("movie_"))
async def movie_info_cb(cb: CallbackQuery):
    mid = int(cb.data[6:])
    movie = db.get_movie(mid)
    if not movie:
        await cb.answer("Kino topilmadi", show_alert=True)
        return
    text = f"🎬 {movie['title']}\n\n{movie.get('description', '')}"
    await cb.message.edit_text(text, reply_markup=kb.watch_keyboard(mid))

@router.callback_query(F.data.startswith("watch_"))
async def watch_cb(cb: CallbackQuery):
    mid = int(cb.data[6:])
    movie = db.get_movie(mid)
    if movie and movie["file_id"]:
        cap = f"🎬 {movie['title']}\n\n{movie.get('description', '')}"
        await cb.bot.send_video(cb.from_user.id, movie["file_id"], caption=cap)
        await cb.answer("✅ Video yuborildi")
    else:
        await cb.answer("❌ Video topilmadi", show_alert=True)

@router.callback_query(F.data == "back_main")
async def back_main_cb(cb: CallbackQuery):
    await cb.message.edit_text("🏠 Asosiy menyu", reply_markup=kb.MENU)

@router.callback_query(F.data == "back_admin")
async def back_admin_cb(cb: CallbackQuery):
    await cb.message.edit_text("🔐 Admin panel", reply_markup=kb.ADMIN)

@router.message(F.text == "📊 Statistika")
async def admin_stats(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    total, blocked, movies, studios = db.get_stats()
    await msg.answer(f"📊 Statistika\n\n👥 Jami: {total}\n🚫 Bloklangan: {blocked}\n🎬 Kinolar: {movies}\n🏢 Studiyalar: {studios}", reply_markup=kb.ADMIN)

@router.message(F.text == "🎬 Kino qo'shish")
async def admin_add_movie_start(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    admin_states[msg.from_user.id] = {"step": "video"}
    await msg.answer("📹 Video yuboring:")

@router.message(F.video)
async def handle_video(msg: Message):
    uid = msg.from_user.id
    if uid not in admin_states or admin_states[uid].get("step") != "video":
        if not is_admin(uid):
            return
        admin_states[uid] = {"step": "video"}
    fid = msg.video.file_id
    admin_states[uid]["file_id"] = fid
    await msg.answer("📝 Nomi:")
    admin_states[uid]["step"] = "title"

@router.message(lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("step") == "title")
async def handle_title(msg: Message):
    admin_states[msg.from_user.id]["title"] = msg.text
    await msg.answer("📝 Tavsifi (yoki - o'tkazish):")
    admin_states[msg.from_user.id]["step"] = "desc"

@router.message(lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("step") == "desc")
async def handle_desc(msg: Message):
    admin_states[msg.from_user.id]["description"] = msg.text if msg.text != "-" else ""
    studios = db.get_all_studios()
    if not studios:
        await msg.answer("🏢 Avval studio qo'shing", reply_markup=kb.ADMIN)
        del admin_states[msg.from_user.id]
        return
    text = "🏢 Studiya tanlang:\n"
    for i, s in enumerate(studios):
        text += f"{i+1}. {s['name']}\n"
    text += "\nRaqam yozing:"
    await msg.answer(text)
    admin_states[msg.from_user.id]["step"] = "studio"

@router.message(lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("step") == "studio")
async def handle_studio(msg: Message):
    try:
        idx = int(msg.text) - 1
        studios = db.get_all_studios()
        s = studios[idx]
        fid = admin_states[msg.from_user.id]["file_id"]
        await msg.bot.forward_message(PRIVATE_CHANNEL, msg.chat.id, msg.message_id - 3)
        movie_id = db.add_movie(
            admin_states[msg.from_user.id]["title"],
            admin_states[msg.from_user.id]["description"],
            fid,
            s["id"]
        )
        await msg.answer(f"✅ Qo'shildi!\n\n🎬 {admin_states[msg.from_user.id]['title']}\n🆔 ID: {movie_id}", reply_markup=kb.ADMIN)
    except:
        await msg.answer("❌ Noto'g'ri raqam")
        return
    del admin_states[msg.from_user.id]

@router.message(F.text == "🏢 Studio qo'shish")
async def admin_add_studio_start(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    admin_states[msg.from_user.id] = {"step": "studio_name"}
    await msg.answer("🏢 Studiya nomi:")

@router.message(lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("step") == "studio_name")
async def handle_studio_name(msg: Message):
    sid = db.add_studio(msg.text)
    await msg.answer(f"✅ {msg.text} qo'shildi! ID: {sid}", reply_markup=kb.ADMIN)
    del admin_states[msg.from_user.id]

@router.message(F.text == "🗑 Studio o'chirish")
async def admin_del_studio(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    studios = db.get_all_studios()
    if not studios:
        await msg.answer("🏢 Studiyalar yo'q", reply_markup=kb.ADMIN)
        return
    await msg.answer("O'chirish uchun tanlang:", reply_markup=kb.delete_studio_keyboard(studios))

@router.callback_query(F.data.startswith("del_studio_"))
async def delete_studio_cb(cb: CallbackQuery):
    sid = int(cb.data[11:])
    db.delete_studio(sid)
    await cb.message.edit_text("✅ O'chirildi", reply_markup=kb.ADMIN)

@router.message(F.text == "📢 Reklama yuborish")
async def admin_broadcast(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    admin_states[msg.from_user.id] = {"step": "broadcast"}
    await msg.answer("📣 Reklama matnini yuboring:")

@router.message(lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("step") == "broadcast")
async def handle_broadcast(msg: Message):
    await msg.answer("📤 Yuborilmoqda...")
    users = db.db.table("users").select("*").execute()
    sent = 0
    for u in users.data:
        try:
            await msg.bot.send_message(u["id"], msg.text)
            sent += 1
        except: pass
    await msg.answer(f"✅ Yuborildi! Jami: {sent}", reply_markup=kb.ADMIN)
    del admin_states[msg.from_user.id]

@router.message(F.text == "📣 Kanalga post")
async def admin_post(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    admin_states[msg.from_user.id] = {"step": "post"}
    await msg.answer("📣 Post matnini yuboring:")

@router.message(lambda m: m.from_user.id in admin_states and admin_states[m.from_user.id].get("step") == "post")
async def handle_post(msg: Message):
    if not PUBLIC_CHANNEL:
        await msg.answer("❌ Public channel sozlanmagan")
        return
    kb_post = kb.post_watch_keyboard(msg.bot.me.username, 0)
    try:
        await msg.bot.send_message(PUBLIC_CHANNEL, msg.text, reply_markup=kb_post)
        await msg.answer("✅ Kanalga yuborildi!", reply_markup=kb.ADMIN)
    except Exception as e:
        await msg.answer(f"❌ {e}")
    del admin_states[msg.from_user.id]

@router.message(F.text == "⬅️ Orqaga")
async def back(msg: Message):
    if is_admin(msg.from_user.id) and msg.from_user.id in admin_states:
        del admin_states[msg.from_user.id]
    await msg.answer("🏠 Asosiy menyu", reply_markup=kb.MENU)
