from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException
from database.connection import connect
from shared.utils import now
from .auth import validate_init_data

router = APIRouter(prefix="/api")

def current_user(x_telegram_init_data: str | None):
    tg = validate_init_data(x_telegram_init_data or "")
    if not tg or not tg.get("id"):
        raise HTTPException(status_code=401, detail="Telegram Mini App authentication required")
    tg_id = int(tg["id"])
    c = connect()
    try:
        stamp = now()
        c.execute("""INSERT INTO users(tg_id,username,first_name,last_seen,created_at,updated_at)
                     VALUES(?,?,?,?,?,?)
                     ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, last_seen=excluded.last_seen, updated_at=excluded.updated_at""",
                  (tg_id, tg.get("username"), tg.get("first_name"), stamp, stamp, stamp))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return row
    finally:
        c.close()

def public_user(row):
    if not row:
        return None
    return {
        "tg_id": row["tg_id"],
        "username": row["username"],
        "first_name": row["first_name"],
        "name": row["name"],
        "city": row["city"],
        "province": row["province"],
        "bio": row["bio"],
        "interests": [x.strip() for x in (row["interests"] or "").replace("،", ",").split(",") if x.strip()],
        "verified": bool(row["verified"]),
        "location_verified": bool(row["location_verified"]),
        "points": row["points"] or 0,
        "level": row["level"] or 1,
        "last_seen": row["last_seen"],
    }

@router.get("/me")
def me(x_telegram_init_data: str | None = Header(default=None)):
    return {"user": public_user(current_user(x_telegram_init_data))}

@router.get("/events")
def events(x_telegram_init_data: str | None = Header(default=None)):
    current_user(x_telegram_init_data)
    c = connect()
    try:
        rows = c.execute("""SELECT e.id,e.title,e.description,e.event_type,e.event_date,e.location,e.city,e.capacity,e.gender_rule,e.status,
                                  u.name creator_name
                           FROM events e LEFT JOIN users u ON u.id=e.creator_id
                           WHERE e.status='PUBLISHED' ORDER BY e.event_date ASC, e.id DESC LIMIT 50""").fetchall()
        return {"events": [dict(r) for r in rows]}
    finally:
        c.close()

@router.get("/matches")
def matches(x_telegram_init_data: str | None = Header(default=None)):
    row = current_user(x_telegram_init_data)
    uid = row["tg_id"]
    c = connect()
    try:
        rows = c.execute("""SELECT CASE WHEN m.user1_id=? THEN m.user2_id ELSE m.user1_id END tg_id
                           FROM matches m WHERE m.status='ACTIVE' AND (m.user1_id=? OR m.user2_id=?)
                           ORDER BY m.updated_at DESC LIMIT 50""", (uid,uid,uid)).fetchall()
        ids = [r["tg_id"] for r in rows]
        if not ids:
            return {"matches": []}
        q = ",".join("?" for _ in ids)
        users = c.execute(f"SELECT tg_id,name,first_name,city,bio,interests,verified,last_seen FROM users WHERE tg_id IN ({q}) AND blocked=0", ids).fetchall()
        return {"matches": [dict(r) for r in users]}
    finally:
        c.close()

@router.get("/discover")
def discover(x_telegram_init_data: str | None = Header(default=None)):
    row = current_user(x_telegram_init_data)
    uid = row["tg_id"]
    c = connect()
    try:
        rows = c.execute("""SELECT u.tg_id,u.name,u.first_name,u.city,u.bio,u.interests,u.verified,u.location_verified,u.last_seen
                           FROM users u
                           WHERE u.tg_id<>? AND u.blocked=0 AND u.verified=1 AND u.location_verified=1
                           AND NOT EXISTS (SELECT 1 FROM blocks b WHERE (b.blocker_id=? AND b.blocked_id=u.tg_id) OR (b.blocker_id=u.tg_id AND b.blocked_id=u.tg_id))
                           AND NOT EXISTS (SELECT 1 FROM interactions i WHERE i.from_id=? AND i.to_id=u.tg_id)
                           ORDER BY u.last_seen DESC, u.id DESC LIMIT 30""", (uid,uid,uid)).fetchall()
        return {"users": [dict(r) for r in rows]}
    finally:
        c.close()
