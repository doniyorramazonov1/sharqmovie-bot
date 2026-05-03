from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command
from config import BOT_TOKEN, ADMIN_IDS, REQUIRED_CHANNEL, PRIVATE_CHANNEL, PUBLIC_CHANNEL
import database as db
import keyboards as kb

router = Router()
admin_states = {}

def is_admin(uid):
    return uid in ADMIN_IDS

def build_ad_text():
    ads = db.get_active_ads()
    if not ads:
        return "\n\n📣 Reklama: @sharqtech_admin"
    text = "\n\n📢 Reklamalar:\n"
    for ad in ads:
        text += f"• {ad['text']}\n"
        if ad.get('link'):
            text += f"  🔗 {ad['link']}\n"
    return text

async def send_movie(msg_or_cb, movie, bot):
    if not movie or not movie["file_id"]:
        return
    cap = f"🎬 {movie['title']}\n🆔 Kod: {movie['movie_code']}\n\n{movie.get('description', '')}{build_ad_text()}"
    if hasattr(msg_or_cb, 'answer'):
        await msg_or_cb.answer("🎬 Kino topildi!")
        await msg_or_cb.bot.send_video(msg_or_cb.chat.id, movie["file_id"], caption=cap, protect_content=True)
    else:
        await cb.bot.send_video(cb.from_user.id, movie["file_id"], caption=cap, protect_content=True)
        await cb.answer("🎬 Video yuborildi")

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
    movie_code = None
    for a in args[1:]:
        if a.startswith("ref_"):
            try: referral_id = int(a[4:])
            except: pass
        elif a.startswith("movie_"):
            movie_code = a[6:]
        elif a.isdigit():
            movie_code = a

    db.add_user(msg.from_user.id, msg.from_user.username, referral_id)

    if movie_code:
        movie = db.get_movie(code=movie_code)
        if movie and movie["file_id"]:
            cap = f"🎬 {movie['title']}\n🆔 Kod: {movie['movie_code']}{build_ad_text()}"
            await msg.bot.send_video(msg.from_user.id, movie["file_id"], caption=cap, protect_content=True)
            return
        series_list = db.get_series(movie_code)
        if series_list:
            kb_list = []
            seasons = db.get_series_seasons(movie_code)
            for s in seasons:
                kb_list.append([InlineKeyboardButton(text=f"📁 Mavsum {s}", callback_data=f"series_season_{movie_code}_{s}")])
            kb_list.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
            await msg.answer(f"📺 {movie_code}\n\nMavsum tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))
            return

    if not await check_subscription(msg.from_user.id, msg.bot):
        await msg.answer("🔒 Botni ishlatish uchun kanalga a'zo bo'ling:", reply_markup=kb.sub_keyboard(REQUIRED_CHANNEL))
        return

    await msg.answer("🎬 Sharq Movie\n\n📝 Kino kodini yoki nomini yozing (masalan: 1234 yoki Avatar)", reply_markup=kb.MENU)

@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    await msg.answer("🔐 Admin panel", reply_markup=kb.ADMIN)

@router.message(F.text == "🎬 Kinolar")
async def all_movies(msg: Message):
    await msg.answer("🎬 Barcha kinolar bo'yicha qidirish uchun kod yoki nom yozing:")

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

@router.message()
async def global_search(msg: Message):
    text = msg.text.strip()
    
    if text.startswith('/'):
        return
    
    uid = msg.from_user.id
    
    if is_admin(uid) and uid in admin_states:
        if admin_states[uid].get("step") == "title":
            admin_states[uid]["title"] = text
            await msg.answer("📝 Tavsifi (yoki - o'tkazish):")
            admin_states[uid]["step"] = "desc"
            return
        if admin_states[uid].get("step") == "desc":
            admin_states[uid]["description"] = text if text != "-" else ""
            studios = db.get_all_studios()
            if not studios:
                await msg.answer("🏢 Avval studio qo'shing", reply_markup=kb.ADMIN)
                del admin_states[uid]
                return
            text_msg = "🏢 Studiya tanlang:\n"
            for i, s in enumerate(studios):
                text_msg += f"{i+1}. {s['name']}\n"
            text_msg += "\nRaqam yozing:"
            await msg.answer(text_msg)
            admin_states[uid]["step"] = "studio"
            return
        if admin_states[uid].get("step") == "studio":
            try:
                idx = int(text) - 1
                studios = db.get_all_studios()
                s = studios[idx]
                state = admin_states[uid]
                fid = state["file_id"]
                title = state["title"]
                desc = state["description"]
                if PRIVATE_CHANNEL:
                    try:
                        await msg.bot.forward_message(PRIVATE_CHANNEL, msg.chat.id, msg.message_id - 4)
                    except Exception as e:
                        print(f"Forward xatosi: {e}")
                movie_id, code = db.add_movie(title, desc, fid, s["id"])
                del admin_states[uid]
                await msg.answer(f"✅ Qo'shildi!\n\n🎬 {title}\n🆔 Kod: {code}", reply_markup=kb.ADMIN)
            except ValueError:
                await msg.answer("❌ Faqat raqam yozing")
            except IndexError:
                await msg.answer("❌ Bunday raqamli studio yo'q. Qayta tanlang:")
            except Exception as e:
                await msg.answer(f"❌ Xatolik: {e}\nQaytadan urinib ko'ring yoki /admin bosing")
                if uid in admin_states:
                    del admin_states[uid]
            return
        if admin_states[uid].get("step") == "studio_name":
            sid = db.add_studio(text)
            await msg.answer(f"✅ {text} qo'shildi! ID: {sid}", reply_markup=kb.ADMIN)
            del admin_states[uid]
            return
        if admin_states[uid].get("step") == "broadcast":
            await msg.answer("📤 Yuborilmoqda...")
            users = db.db.execute("SELECT * FROM users").fetchall() if hasattr(db, 'db') else []
            sent = 0
            for u in users:
                try:
                    await msg.bot.send_message(u['id'] if isinstance(u, dict) else u[0], text)
                    sent += 1
                except: pass
            await msg.answer(f"✅ Yuborildi! Jami: {sent}", reply_markup=kb.ADMIN)
            del admin_states[uid]
            return
        if admin_states[uid].get("step") == "post":
            if not PUBLIC_CHANNEL:
                await msg.answer("❌ Public channel sozlanmagan")
                del admin_states[uid]
                return
            kb_post = kb.post_watch_keyboard(msg.bot.me.username, 0)
            try:
                await msg.bot.send_message(PUBLIC_CHANNEL, text, reply_markup=kb_post)
                await msg.answer("✅ Kanalga yuborildi!", reply_markup=kb.ADMIN)
            except Exception as e:
                await msg.answer(f"❌ {e}")
            del admin_states[uid]
            return
        if admin_states[uid].get("step") == "ad_text":
            admin_states[uid]["ad_text"] = text
            await msg.answer("🔗 Link (yoki - o'tkazish):")
            admin_states[uid]["step"] = "ad_link"
            return
        if admin_states[uid].get("step") == "ad_link":
            link = text if text != "-" else None
            db.add_ad(admin_states[uid]["ad_text"], link)
            await msg.answer("✅ Reklama qo'shildi!", reply_markup=kb.ADMIN)
            del admin_states[uid]
            return
        if admin_states[uid].get("step") == "series_title":
            admin_states[uid]["series_title"] = text
            await msg.answer("📁 Mavsum raqami (masalan: 1):")
            admin_states[uid]["step"] = "series_season"
            return
        if admin_states[uid].get("step") == "series_season":
            try:
                admin_states[uid]["series_season"] = int(text)
                await msg.answer("🎬 Qism raqami (masalan: 1):")
                admin_states[uid]["step"] = "series_episode"
            except:
                await msg.answer("❌ Faqat raqam yozing")
            return
        if admin_states[uid].get("step") == "series_episode":
            try:
                admin_states[uid]["series_episode"] = int(text)
                await msg.answer("📹 Video yuboring:")
                admin_states[uid]["step"] = "series_video"
            except:
                await msg.answer("❌ Faqat raqam yozing")
            return
        if admin_states[uid].get("step") == "series_desc":
            db.add_series(
                admin_states[uid]["series_title"],
                admin_states[uid]["series_season"],
                admin_states[uid]["series_episode"],
                admin_states[uid]["file_id"],
                text if text != "-" else ""
            )
            title = admin_states[uid]["series_title"]
            season = admin_states[uid]["series_season"]
            episode = admin_states[uid]["series_episode"] + 1
            admin_states[uid]["series_episode"] = episode
            admin_states[uid]["step"] = "series_video"
            await msg.answer(f"✅ Qo'shildi!\n\n📺 {title}\n📁 Mavsum {season}, {episode-1}-qism\n\n📹 Keyingi qism videosini yuboring (yoki ⬅️ Orqaga):")
            return

    if not await check_subscription(uid, msg.bot):
        await msg.answer("🔒 Botni ishlatish uchun kanalga a'zo bo'ling:", reply_markup=kb.sub_keyboard(REQUIRED_CHANNEL))
        return

    if is_admin(uid):
        if text == "📊 Statistika":
            total, blocked, movies, studios = db.get_stats()
            series_count = db.get_series_count()
            ads = db.get_all_ads()
            ad_count = len(ads)
            await msg.answer(f"📊 Statistika\n\n👥 Jami: {total}\n🚫 Bloklangan: {blocked}\n🎬 Kinolar: {movies}\n📺 Seriallar: {series_count}\n🏢 Studiyalar: {studios}\n📣 Reklamalar: {ad_count}", reply_markup=kb.ADMIN)
            return
        if text == "🎬 Kino qo'shish":
            admin_states[uid] = {"step": "video"}
            await msg.answer("📹 Video yuboring:", reply_markup=kb.ADMIN)
            return
        if text == "📺 Serial qo'shish":
            admin_states[uid] = {"step": "series_title"}
            await msg.answer("📺 Serial nomi:", reply_markup=kb.ADMIN)
            return
        if text == "📋 Seriallar ro'yxati":
            series_list = db.get_series()
            if not series_list:
                await msg.answer("📺 Seriallar yo'q", reply_markup=kb.ADMIN)
                return
            text_msg = "📺 Seriallar:\n\n"
            for s in series_list:
                text_msg += f"• {s['title']}\n"
            text_msg += "\nQo'shish: 📺 Serial qo'shish\nO'chirish: /del_serial ID"
            await msg.answer(text_msg, reply_markup=kb.ADMIN)
            return
        if text == "🏢 Studio qo'shish":
            admin_states[uid] = {"step": "studio_name"}
            await msg.answer("🏢 Studiya nomi:", reply_markup=kb.ADMIN)
            return
        if text == "🗑 Studio o'chirish":
            studios = db.get_all_studios()
            if not studios:
                await msg.answer("🏢 Studiyalar yo'q", reply_markup=kb.ADMIN)
                return
            await msg.answer("O'chirish uchun tanlang:", reply_markup=kb.delete_studio_keyboard(studios))
            return
        if text == "➕ Reklama qo'shish":
            admin_states[uid] = {"step": "ad_text"}
            await msg.answer("📝 Reklama matni:", reply_markup=kb.ADMIN)
            return
        if text == "📋 Reklamalar ro'yxati":
            ads = db.get_all_ads()
            if not ads:
                await msg.answer("📣 Reklamalar yo'q", reply_markup=kb.ADMIN)
                return
            text_msg = "📣 Reklamalar:\n\n"
            for a in ads:
                text_msg += f"🆔 {a['id']}. {a['text']}\n"
                if a.get('link'):
                    text_msg += f"   🔗 {a['link']}\n"
                text_msg += "\n"
            text_msg += "O'chirish: /del_ad ID"
            await msg.answer(text_msg, reply_markup=kb.ADMIN)
            return
        if text == "📢 Reklama yuborish":
            admin_states[uid] = {"step": "broadcast"}
            await msg.answer("📣 Reklama matnini yuboring:", reply_markup=kb.ADMIN)
            return
        if text == "📣 Kanalga post":
            admin_states[uid] = {"step": "post"}
            await msg.answer("📣 Post matnini yuboring:", reply_markup=kb.ADMIN)
            return

    # Check if it's a series name
    series_list = db.get_series(text)
    if series_list:
        if len(series_list) == 1 and 'title' in series_list[0]:
            # It's a single series, show seasons
            title = series_list[0]['title']
            seasons = db.get_series_seasons(title)
            kb_list = []
            for s in seasons:
                kb_list.append([InlineKeyboardButton(text=f"📁 Mavsum {s}", callback_data=f"series_season_{title}_{s}")])
            kb_list.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
            await msg.answer(f"📺 {title}\n\nMavsum tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))
        else:
            kb_list = []
            for s in series_list:
                kb_list.append([InlineKeyboardButton(text=f"📺 {s['title']}", callback_data=f"series_seasons_{s['title']}")])
            kb_list.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
            await msg.answer(f"🔍 Seriallar ({len(series_list)}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))
        return

    movie = db.get_movie(code=text)
    if movie:
        cap = f"🎬 {movie['title']}\n🆔 Kod: {movie['movie_code']}\n\n{movie.get('description', '')}{build_ad_text()}"
        await msg.bot.send_video(msg.chat.id, movie["file_id"], caption=cap, protect_content=True)
        return

    results = db.search_movie(text)
    if results:
        kb_list = []
        for m in results:
            kb_list.append([InlineKeyboardButton(text=f"🎬 {m['title']} (Kod: {m['movie_code']})", callback_data=f"movie_{m['id']}")])
        kb_list.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
        await msg.answer(f"🔍 Natijalar ({len(results)}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))
    else:
        await msg.answer(f"❌ \"{text}\" topilmadi.\n\n📝 Kino kodini yoki nomini yozing:", reply_markup=kb.MENU)

@router.callback_query(F.data == "check_sub")
async def check_sub_cb(cb: CallbackQuery):
    if await check_subscription(cb.from_user.id, cb.bot):
        await cb.answer("✅ A'zo bo'ldingiz!")
        await cb.message.edit_text("✅ Xush kelibsiz!")
        await cb.message.answer("🎬 Sharq Movie\n\n📝 Kino kodini yoki nomini yozing:", reply_markup=kb.MENU)
    else:
        await cb.answer("A'zo bo'lmagansiz!", show_alert=True)

@router.callback_query(F.data.startswith("studio_"))
async def studio_movies_cb(cb: CallbackQuery):
    sid = int(cb.data[7:])
    movies = db.get_movies_by_studio(sid)
    if not movies:
        await cb.answer("Bu studiyada kino yo'q", show_alert=True)
        return
    kb_list = []
    for m in movies:
        kb_list.append([InlineKeyboardButton(text=f"🎬 {m['title']} ({m['movie_code']})", callback_data=f"watch_{m['id']}")])
    kb_list.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
    await cb.message.edit_text("🎬 Kinolar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))

@router.callback_query(F.data.startswith("series_season_"))
async def series_season_cb(cb: CallbackQuery):
    parts = cb.data[14:].rsplit("_", 1)
    title = "_".join(parts[:-1])
    season = int(parts[-1])
    eps = db.get_series_episodes(title, season)
    if not eps:
        await cb.answer("Bu mavsumda qismlar yo'q", show_alert=True)
        return
    kb_list = []
    for e in eps:
        kb_list.append([InlineKeyboardButton(text=f"🎬 {e['episode']}-qism", callback_data=f"watch_series_{e['id']}")])
    kb_list.append([InlineKeyboardButton(text="⬅️ Mavsumlar", callback_data=f"series_seasons_{title}")])
    await cb.message.edit_text(f"📺 {title}\n📁 Mavsum {season}\n\nQism tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))

@router.callback_query(F.data.startswith("series_seasons_"))
async def series_seasons_cb(cb: CallbackQuery):
    title = cb.data[15:]
    seasons = db.get_series_seasons(title)
    kb_list = []
    for s in seasons:
        kb_list.append([InlineKeyboardButton(text=f"📁 Mavsum {s}", callback_data=f"series_season_{title}_{s}")])
    kb_list.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")])
    await cb.message.edit_text(f"📺 {title}\n\nMavsum tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))

@router.callback_query(F.data.startswith("watch_series_"))
async def watch_series_cb(cb: CallbackQuery):
    eid = int(cb.data[13:])
    conn = db.get_conn()
    ep = conn.execute("SELECT * FROM series WHERE id = ?", (eid,)).fetchone()
    conn.close()
    if ep and ep['file_id']:
        cap = f"📺 {ep['title']}\n📁 Mavsum {ep['season']}, {ep['episode']}-qism\n\n{ep.get('description', '')}{build_ad_text()}"
        await cb.bot.send_video(cb.from_user.id, ep['file_id'], caption=cap, protect_content=True)
        await cb.answer("✅ Video yuborildi")
    else:
        await cb.answer("❌ Video topilmadi", show_alert=True)

@router.callback_query(F.data.startswith("movie_"))
async def movie_info_cb(cb: CallbackQuery):
    mid = int(cb.data[6:])
    movie = db.get_movie(movie_id=mid)
    if not movie:
        await cb.answer("Kino topilmadi", show_alert=True)
        return
    db.log_ad_view(0, cb.from_user.id)
    text = f"🎬 {movie['title']}\n🆔 Kod: {movie['movie_code']}\n\n{movie.get('description', '')}{build_ad_text()}"
    kb_watch = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Tomosha qilish", callback_data=f"watch_{mid}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")]
    ])
    await cb.message.edit_text(text, reply_markup=kb_watch)

@router.callback_query(F.data.startswith("watch_"))
async def watch_cb(cb: CallbackQuery):
    mid = int(cb.data[6:])
    movie = db.get_movie(movie_id=mid)
    if movie and movie["file_id"]:
        cap = f"🎬 {movie['title']}\n🆔 Kod: {movie['movie_code']}{build_ad_text()}"
        await cb.bot.send_video(cb.from_user.id, movie["file_id"], caption=cap, protect_content=True)
        await cb.answer("✅ Video yuborildi")
    else:
        await cb.answer("❌ Video topilmadi", show_alert=True)

@router.callback_query(F.data == "back_main")
async def back_main_cb(cb: CallbackQuery):
    await cb.message.edit_text("🏠 Asosiy menyu", reply_markup=kb.MENU)

@router.callback_query(F.data == "back_admin")
async def back_admin_cb(cb: CallbackQuery):
    await cb.message.edit_text("🔐 Admin panel", reply_markup=kb.ADMIN)

@router.message(F.video)
async def handle_video(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        return
    
    # Check if we're in series addition mode
    if uid in admin_states and admin_states[uid].get("step") == "series_video":
        admin_states[uid]["file_id"] = msg.video.file_id
        await msg.answer("📝 Tavsifi (yoki - o'tkazish):")
        admin_states[uid]["step"] = "series_desc"
        return
        
    if uid not in admin_states or admin_states[uid].get("step") != "video":
        admin_states[uid] = {"step": "video"}
    fid = msg.video.file_id
    admin_states[uid]["file_id"] = fid
    await msg.answer("📝 Nomi:")
    admin_states[uid]["step"] = "title"

@router.callback_query(F.data.startswith("del_studio_"))
async def delete_studio_cb(cb: CallbackQuery):
    sid = int(cb.data[11:])
    db.delete_studio(sid)
    await cb.message.edit_text("✅ O'chirildi", reply_markup=kb.ADMIN)

@router.message(Command("del_serial"))
async def admin_del_series(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    try:
        serial_id = int(msg.text.split()[1])
        db.delete_series(serial_id)
        await msg.answer(f"✅ Serial {serial_id} o'chirildi", reply_markup=kb.ADMIN)
    except:
        await msg.answer("❌ /del_serial ID formatida yozing")

@router.message(Command("del_ad"))
async def admin_del_ad(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    try:
        ad_id = int(msg.text.split()[1])
        db.delete_ad(ad_id)
        await msg.answer(f"✅ Reklama {ad_id} o'chirildi", reply_markup=kb.ADMIN)
    except:
        await msg.answer("❌ /del_ad ID formatida yozing")

@router.message(F.text == "⬅️ Orqaga")
async def back(msg: Message):
    if is_admin(msg.from_user.id) and msg.from_user.id in admin_states:
        del admin_states[msg.from_user.id]
    await msg.answer("🏠 Asosiy menyu", reply_markup=kb.MENU)
