from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_tables():
    db.table("users").upsert({"id": 0, "joined_at": "2024-01-01", "blocked": False, "referral_id": None}).execute()
    db.table("users").delete().eq("id", 0).execute()
    print("Supabase connected")

def get_user(telegram_id):
    r = db.table("users").select("*").eq("id", telegram_id).execute()
    return r.data[0] if r.data else None

def add_user(telegram_id, username=None, referral_id=None):
    if get_user(telegram_id): return
    db.table("users").insert({
        "id": telegram_id,
        "username": username,
        "referral_id": referral_id
    }).execute()
    if referral_id:
        db.table("users").select("*").eq("id", referral_id).execute()
        db.rpc("increment_referrals", {"ref_user_id": referral_id}).execute()

def block_user(telegram_id):
    db.table("users").update({"blocked": True}).eq("id", telegram_id).execute()

def unblock_user(telegram_id):
    db.table("users").update({"blocked": False}).eq("id", telegram_id).execute()

def get_stats():
    users = db.table("users").select("*").execute()
    total = len(users.data)
    blocked = len([u for u in users.data if u.get("blocked")])
    movies = db.table("movies").select("id").execute()
    studios = db.table("studios").select("id").execute()
    return total, blocked, len(movies.data), len(studios.data)

def add_movie(title, description, file_id, studio_id):
    r = db.table("movies").insert({
        "title": title,
        "description": description,
        "file_id": file_id,
        "studio_id": studio_id
    }).execute()
    return r.data[0]["id"] if r.data else None

def get_movie(movie_id):
    r = db.table("movies").select("*").eq("id", movie_id).execute()
    return r.data[0] if r.data else None

def get_movies_by_studio(studio_id):
    r = db.table("movies").select("*").eq("studio_id", studio_id).order("id", desc=True).limit(50).execute()
    return r.data

def get_all_studios():
    r = db.table("studios").select("*").order("name").execute()
    return r.data

def add_studio(name):
    r = db.table("studios").insert({"name": name}).execute()
    return r.data[0]["id"] if r.data else None

def delete_studio(studio_id):
    db.table("studios").delete().eq("id", studio_id).execute()
