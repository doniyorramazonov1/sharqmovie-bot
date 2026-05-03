import random
import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

db: Client = None

def get_db():
    global db
    if db is None:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
    return db

def init_db():
    print("Supabase connected!")

def generate_code():
    conn = get_db()
    while True:
        code = str(random.randint(100, 9999))
        result = conn.table("movies").select("id").eq("movie_code", code).execute()
        if not result.data:
            return code

def get_user(telegram_id):
    conn = get_db()
    result = conn.table("users").select("*").eq("id", telegram_id).execute()
    return result.data[0] if result.data else None

def add_user(telegram_id, username=None, referral_id=None):
    if get_user(telegram_id): return
    conn = get_db()
    conn.table("users").insert({
        "id": telegram_id,
        "username": username,
        "referral_id": referral_id,
        "referrals_count": 0,
        "blocked": False
    }).execute()
    if referral_id:
        conn.rpc("increment_referrals", {"ref_user_id": referral_id}).execute()

def get_stats():
    conn = get_db()
    total = len(conn.table("users").select("id").execute().data)
    blocked = len(conn.table("users").select("id").eq("blocked", True).execute().data)
    movies = len(conn.table("movies").select("id").execute().data)
    studios = len(conn.table("studios").select("id").execute().data)
    return total, blocked, movies, studios

def add_movie(title, description, file_id, studio_id):
    code = generate_code()
    conn = get_db()
    result = conn.table("movies").insert({
        "title": title,
        "description": description,
        "file_id": file_id,
        "studio_id": studio_id,
        "movie_code": code
    }).execute()
    if result.data:
        return result.data[0]["id"], code
    return None, code

def get_movie(movie_id=None, code=None):
    conn = get_db()
    if code:
        result = conn.table("movies").select("*").eq("movie_code", code).execute()
    else:
        result = conn.table("movies").select("*").eq("id", movie_id).execute()
    return result.data[0] if result.data else None

def search_movie(query):
    from difflib import SequenceMatcher
    conn = get_db()
    result = conn.table("movies").select("*").order("id", desc=True).execute()
    all_movies = result.data
    
    results = []
    for m in all_movies:
        title = m.get('title', '').lower()
        code = m.get('movie_code', '') or ''
        desc = m.get('description', '').lower() if m.get('description') else ''
        
        # Exact code match
        if query.lower() == code:
            results.append((1.0, m))
            continue
        
        # Word-level matching
        title_words = title.replace('-', ' ').replace('_', ' ').replace('.', ' ').split()
        query_words = query.lower().replace('-', ' ').replace('_', ' ').replace('.', ' ').split()
        
        best_score = 0
        for qw in query_words:
            if qw in title:
                best_score = max(best_score, 0.8)
            for tw in title_words:
                score = SequenceMatcher(None, qw, tw).ratio()
                best_score = max(best_score, score)
        
        # Check description
        if query.lower() in desc:
            best_score = max(best_score, 0.5)
        
        if best_score >= 0.55:
            results.append((best_score, m))
    
    results.sort(key=lambda x: (-x[0], -x[1]['id']))
    return [r[1] for r in results[:15]]

def get_movies_by_studio(studio_id):
    conn = get_db()
    result = conn.table("movies").select("*").eq("studio_id", studio_id).order("id", desc=True).execute()
    return result.data

def get_all_studios():
    conn = get_db()
    result = conn.table("studios").select("*").order("name").execute()
    return result.data

def add_studio(name):
    try:
        conn = get_db()
        result = conn.table("studios").insert({"name": name}).execute()
        if result.data:
            return result.data[0]["id"]
        return None
    except:
        return None

def delete_studio(studio_id):
    conn = get_db()
    conn.table("movies").delete().eq("studio_id", studio_id).execute()
    conn.table("studios").delete().eq("id", studio_id).execute()

def add_ad(text, link=None, channel_id=None):
    conn = get_db()
    result = conn.table("ads").insert({
        "text": text,
        "link": link,
        "channel_id": channel_id,
        "is_active": True
    }).execute()
    if result.data:
        return result.data[0]["id"]
    return None

def delete_ad(ad_id):
    conn = get_db()
    conn.table("ads").delete().eq("id", ad_id).execute()

def get_active_ads():
    import random as rand
    conn = get_db()
    result = conn.table("ads").select("*").eq("is_active", True).execute()
    ads = result.data
    rand.shuffle(ads)
    return ads[:2]

def get_all_ads():
    conn = get_db()
    result = conn.table("ads").select("*").order("id", desc=True).execute()
    return result.data

def log_ad_view(ad_id, user_id):
    conn = get_db()
    conn.table("ad_stats").insert({
        "ad_id": ad_id,
        "user_id": user_id
    }).execute()

def get_ad_stats():
    conn = get_db()
    result = conn.table("ads").select("*").execute()
    return result.data

def update_ad_click(ad_id):
    conn = get_db()
    result = conn.table("ad_stats").select("id").eq("ad_id", ad_id).eq("clicked", False).order("id", desc=True).limit(1).execute()
    if result.data:
        conn.table("ad_stats").update({"clicked": True}).eq("id", result.data[0]["id"]).execute()

def add_series(title, season, episode, file_id, description=""):
    conn = get_db()
    result = conn.table("series").insert({
        "title": title,
        "season": season,
        "episode": episode,
        "file_id": file_id,
        "description": description
    }).execute()
    if result.data:
        return result.data[0]["id"]
    return None

def get_series(title=None):
    conn = get_db()
    if title:
        result = conn.table("series").select("*").eq("title", title).order("season").order("episode").execute()
    else:
        result = conn.table("series").select("title").order("title").execute()
        # Get unique titles
        titles = []
        seen = set()
        for s in result.data:
            if s['title'] not in seen:
                seen.add(s['title'])
                titles.append(s)
        return titles
    return result.data

def get_series_episode(title, season, episode):
    conn = get_db()
    result = conn.table("series").select("*").eq("title", title).eq("season", season).eq("episode", episode).execute()
    return result.data[0] if result.data else None

def get_series_seasons(title):
    conn = get_db()
    result = conn.table("series").select("season").eq("title", title).order("season").execute()
    seasons = list(set([s['season'] for s in result.data]))
    seasons.sort()
    return seasons

def get_series_episodes(title, season):
    conn = get_db()
    result = conn.table("series").select("*").eq("title", title).eq("season", season).order("episode").execute()
    return result.data

def delete_series(series_id):
    conn = get_db()
    conn.table("series").delete().eq("id", series_id).execute()

def get_series_count():
    conn = get_db()
    result = conn.table("series").select("title").execute()
    return len(set([s['title'] for s in result.data]))
