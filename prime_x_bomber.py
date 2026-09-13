import asyncio, json, os, time, logging, random, string, threading, io
from datetime import datetime
from copy import deepcopy
from collections import defaultdict

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ChatMemberUpdated,
    FSInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

_DB_LOCK = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("PrimeBomber")

# ========== PREMIUM EMOJI IDs ==========
EMOJI_FIRE = "5289722755871162900"
EMOJI_STAR = "5372849966689566579"
EMOJI_ROCKET = "5359664288241829619"
EMOJI_CROWN = "6237927637906364256"
EMOJI_SHIELD = "6235476345451716705"
EMOJI_MONEY = "6244678063775289843"
EMOJI_PHONE = "6239930832128056797"
EMOJI_CHECK = "4958689671950369798"
EMOJI_CROSS = "4958900559139570572"
EMOJI_WARNING = "4958526153955476488"
EMOJI_LOCK = "4956719506027185156"
EMOJI_GIFT = "5084613633418199991"
EMOJI_BELL = "5098265504796115765"
EMOJI_GEAR = "5116414868357907335"
EMOJI_VIDEO = "5372849966689566579"

FIRE_EFFECT_ID = "5104841245755180586"

# ========== LEAKED FIREBASE BLACKLIST ==========
LEAKED_FB_BLACKLIST = [
    "tinnm88-b7db5", "tinmm88-b7db5", "e9turnament1", "raaz-5287d", "raav-5287d",
    "apkpure-6eb6a", "e14turnament2", "e5turnament2", "e3turnament11",
    "bossuun", "jsjsjdj-7f0d1", "rahul-54fe9", "runjun-master-panel",
    "gsjjshdbs", "apkdriod-f6fb9", "fir-1fa16", "fir-27c9e",
    "newspreding", "privatesok-59944", "risho-d4c66", "singhaana-6f199",
    "dogla-de225", "ravi-23776", "vibe-d238e", "painislv", "rahais",
    "hdjdjdj-a73f2", "hello-aae5a", "upandar-bb51e", "pehla-panel-green",
    "chfjfj-c2857", "sb-rex-11", "wait-5fead", "strange-2e4aa",
    "customer-1b7ca", "sudhir-suexs-seox", "kali-1b217", "dharmesh-panel",
    "shilpa-e712a", "miyakhalifa-143d5", "hwllob-1a740", "ramm-bac59",
    "maxbhai-b8d3a", "rajakk-80ecd", "jannu-c03ea", "loddysingh-6d511",
    "dhumm-90a53", "sala-a92c9", "project-f2fd6", "rajabhaya",
    "vdgsh-623ed", "rmx3511uuj", "customer03support", "chudgy-1cdca",
    "dusman-abf8b", "jonisins-52271", "sonic-d5c1a", "ashu-415kumar",
    "anvith6-9450e", "kumaru-6eec1",
]

def is_leaked_fb(url: str) -> bool:
    if not url: return False
    u = url.lower()
    return any(kw.lower() in u for kw in LEAKED_FB_BLACKLIST)

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(text: str) -> str:
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def btn(text, callback_data, emoji_id=None, fallback_emoji="", style=None):
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    kw = {"text": label, "callback_data": callback_data}
    if emoji_id: kw["icon_custom_emoji_id"] = emoji_id
    if style in ["primary", "success", "danger"]: kw["style"] = style
    return InlineKeyboardButton(**kw)

def btn_url(text, url, emoji_id=None, fallback_emoji="", style=None):
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    kw = {"text": label, "url": url}
    if emoji_id: kw["icon_custom_emoji_id"] = emoji_id
    if style in ["primary", "success", "danger"]: kw["style"] = style
    return InlineKeyboardButton(**kw)

# ========== REPLY KEYBOARDS ==========
def user_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Start Blast"), KeyboardButton(text="📹 Videos")],
            [KeyboardButton(text="💰 Credits"), KeyboardButton(text="🛑 Stop Blast")],
            [KeyboardButton(text="🎁 Redeem"), KeyboardButton(text="👥 Refer")],
            [KeyboardButton(text="📊 Stats"), KeyboardButton(text="ℹ️ Info")],
            [KeyboardButton(text="💸 Transfer Credits")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Send SMS"), KeyboardButton(text="👥 Users")],
            [KeyboardButton(text="📊 Stats"), KeyboardButton(text="📹 Videos")],
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="🚫 Ban User")],
            [KeyboardButton(text="✅ Unban User"), KeyboardButton(text="🔙 Panel")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def owner_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Send SMS"), KeyboardButton(text="🔥 Firebase")],
            [KeyboardButton(text="👥 Users"), KeyboardButton(text="📊 Stats")],
            [KeyboardButton(text="🛡 Admins"), KeyboardButton(text="👑 Owners")],
            [KeyboardButton(text="💰 Add Credits"), KeyboardButton(text="💸 Deduct Credits")],
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="📹 Videos")],
            [KeyboardButton(text="🎁 Redeem Codes"), KeyboardButton(text="📜 Activity")],
            [KeyboardButton(text="🔒 Protect Number"), KeyboardButton(text="🔗 Force Join")],
            [KeyboardButton(text="🔙 Panel"), KeyboardButton(text="🔄 Refresh")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def main_reply_keyboard(uid, d):
    if is_owner(uid, d): return owner_reply_keyboard()
    if is_admin(uid, d): return admin_reply_keyboard()
    return user_reply_keyboard()

# ========== CONFIG ==========
MAIN_OWNER = 6833492658
SUPER_ADMIN_NAME = "Shadow hex!!!"
SUPER_ADMIN_LINK = "https://t.me/Shadowhex"
SUPER_ADMINS = [6833492658, 8785590284]
DEFAULT_ADMINS = [8785590284]

BOT_TOKEN = "8558781775:AAHTCzGMW-wQG34VpYgtV_5zBmfc-ms2sLc"
LOG_CHANNEL_ID = -1003962383714

_DATA_FILE = "blast_data.json"
_VERSION = "v3.3-PRIME"
_PROGRESS_UPDATE_INTERVAL = 1.0
_BACKGROUND_SCAN_INTERVAL = 60.0

SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

async def send_fire_effect_private(bot, chat_id):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🔥", "message_effect_id": FIRE_EFFECT_ID}
            async with session.post(url, json=payload, timeout=5) as resp:
                res = await resp.json()
                if res.get("ok"):
                    mid = res["result"]["message_id"]
                    await asyncio.sleep(2)
                    d = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                    await session.post(d, json={"chat_id": chat_id, "message_id": mid})
    except Exception as e:
        log.warning(f"Fire Effect: {e}")

async def send_channel_log(bot, text):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error(f"Channel log: {e}")

async def background_backup_sender(bot):
    log.info("Backup Task STARTED")
    while True:
        await asyncio.sleep(3600)
        try:
            if os.path.exists(_DATA_FILE):
                cap = (f"📦 <b>AUTO BACKUP</b>\n📅 <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                       f"📂 <code>{_DATA_FILE}</code>")
                await bot.send_document(LOG_CHANNEL_ID, FSInputFile(_DATA_FILE), caption=cap, parse_mode="HTML")
                log.info("Backup sent")
        except Exception as e:
            log.error(f"Backup fail: {e}")

class UserSession:
    __slots__ = ['uid','cancelled','sent','failed','task','start_time','lock','number','target_uid','blast_data']
    def __init__(self, uid):
        self.uid = uid; self.cancelled = False; self.sent = 0; self.failed = 0
        self.task = None; self.start_time = time.time(); self.lock = asyncio.Lock()
        self.number = None; self.target_uid = None; self.blast_data = None

USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
DEVICE_HEALTH_LOG = []
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS = {}

class S(StatesGroup):
    send_number = State(); send_message = State(); send_speed = State(); send_count = State()
    owner_send_number = State(); owner_send_message = State(); owner_send_speed = State(); owner_send_count = State()
    admin_send_number = State(); admin_send_message = State(); admin_send_speed = State(); admin_send_count = State()
    redeem_code = State()
    add_firebase = State(); add_firebase_file = State()
    add_owner = State(); add_admin = State()
    ban_user = State(); unban_user = State(); broadcast = State()
    fj_add_channel = State(); fj_add_link = State()
    add_plan_name = State(); add_plan_price = State(); add_plan_credits = State(); add_plan_link = State()
    add_credits_uid = State(); add_credits_amount = State()
    deduct_credits_uid = State(); deduct_credits_amount = State()
    gen_redeem_credits = State(); gen_redeem_uses = State()
    set_ref_credits = State()
    protect_number = State(); track_number = State()
    transfer_credits_uid = State(); transfer_credits_amount = State()
    add_all_credits_amount = State(); deduct_all_credits_amount = State()
    add_video = State()

def _default_data():
    return {
        "owners": [MAIN_OWNER],
        "admins": list(DEFAULT_ADMINS),
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "premium": {"ref_credits": 3},
        "force_join": {"enabled": False, "channels": []},
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {"ref_credits": 3, "max_owners": 6},
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": {},
        "videos": []
    }

def load():
    with _DB_LOCK:
        if os.path.exists(_DATA_FILE):
            try:
                with open(_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                default = _default_data()
                for k, v in default.items():
                    if k not in data: data[k] = v
                if MAIN_OWNER not in data.get("owners", []):
                    data["owners"].insert(0, MAIN_OWNER)
                for did in DEFAULT_ADMINS:
                    if did not in data.get("admins", []):
                        data.setdefault("admins", []).append(did)
                for uid_str, u in data.get("users", {}).items():
                    u.setdefault("credits", 0)
                    u.setdefault("sms_history", [])
                    u.setdefault("manual_added_credits", 0)
                if "firebases" in data and data["firebases"]:
                    before = len(data["firebases"])
                    cleaned = [fb for fb in data["firebases"] if not is_leaked_fb(fb.get("url",""))]
                    if before - len(cleaned) > 0:
                        data["firebases"] = cleaned
                        log.warning(f"[CLEANUP] Removed {before-len(cleaned)} leaked FB")
                        try:
                            with open(_DATA_FILE, "w", encoding="utf-8") as fw:
                                json.dump(data, fw, indent=2, ensure_ascii=False)
                        except: pass
                global PROTECTED_NUMBERS
                PROTECTED_NUMBERS = data.get("protected_numbers", {})
                return data
            except Exception as e:
                log.error(f"Load error: {e}")
        d = _default_data(); save(d); return d

def save(d):
    with _DB_LOCK:
        d["protected_numbers"] = PROTECTED_NUMBERS
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)

def reg_user(uid, name, d):
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {"name": name, "uses": 0, "credits": 0, "manual_added_credits": 0,
                         "joined_at": int(time.time()), "refer_code": None,
                         "referred_by": None, "sms_history": []}
        return True
    return False

def log_activity(d, action, uid, details=""):
    d.setdefault("activity_log", []).append({"timestamp": int(time.time()), "uid": uid, "action": action, "details": details})
    if len(d["activity_log"]) > 1000: d["activity_log"] = d["activity_log"][-1000:]

def is_main_owner(uid): return uid == MAIN_OWNER
def is_owner(uid, d): return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS
def is_admin(uid, d): return is_owner(uid, d) or uid in d.get("admins", [])
def is_banned(uid, d): return uid in d.get("banned", [])

def can_use(uid, d):
    if is_banned(uid, d): return False
    if is_admin(uid, d): return True
    if d.get("free_mode"): return True
    if uid in d.get("approved", []): return True
    return False

def role_tag(uid, d):
    if is_main_owner(uid): return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d): return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []): return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if uid in d.get("approved", []): return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"): return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"

def get_user_credits(uid, d): return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid, amount, d, is_manual=False):
    k = str(uid)
    if k not in d.get("users", {}): d["users"][k] = {"credits": 0, "manual_added_credits": 0}
    d["users"][k].setdefault("manual_added_credits", 0)
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amount
    if is_manual: d["users"][k]["manual_added_credits"] += amount

def deduct_credits(uid, amount, d):
    k = str(uid)
    if k in d.get("users", {}):
        c = d["users"][k].get("credits", 0)
        if c >= amount:
            d["users"][k]["credits"] = c - amount
            return True
    return False

def generate_user_refer_code(uid, d):
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not any(u.get("refer_code") == code for u in d.get("users", {}).values()): break
    if k in d.get("users", {}): d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid, code, d):
    ref_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            ref_uid = int(uid_str); break
    if not ref_uid: return False, f"{em(EMOJI_CROSS, '❌')} ɪɴᴠᴀʟɪᴅ ʀᴇғᴇʀʀᴀʟ ᴄᴏᴅᴇ!", None
    if ref_uid == new_uid: return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴘɴᴀ ᴄᴏᴅᴇ ᴋʜᴜᴅ ᴜsᴇ ɴᴀʜɪɴ!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴀᴘ ᴘᴇʜʟᴇ sᴇ ʀᴇғᴇʀ ʜᴏ ᴄʜᴜᴋᴇ ʜᴀɪɴ!", None
    rc = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, rc, d)
    add_credits(ref_uid, rc, d)
    d["users"][str(new_uid)]["referred_by"] = ref_uid
    save(d)
    return True, f"{em(EMOJI_GIFT, '🎉')} ᴡᴇʟᴄᴏᴍE! ᴀᴀᴘᴋᴏ {rc} ᴄʀᴇᴅɪᴛs ᴍɪʟᴇ!", ref_uid

async def send_random_video(bot, chat_id, caption=""):
    d = load(); videos = d.get("videos", [])
    if videos:
        try: await bot.send_video(chat_id, video=random.choice(videos), caption=caption, parse_mode="HTML")
        except Exception as e: log.error(f"Video: {e}")

def kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows])

def speed_kb(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("ғᴀsᴛ", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", "danger"),
         btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", "primary"),
         btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", "success")],
        [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌", "danger")]
    ])

def progress_bar(cur, tot, w=20):
    if tot <= 0: return "░" * w
    f = min(w, int(w * cur / tot))
    return "█" * f + "░" * (w - f)

def progress_text(sent, failed, total, credits=None, speed_label="⚡ MEDIUM"):
    bar = progress_bar(sent + failed, total)
    pct = int(((sent + failed) / total) * 100) if total > 0 else 0
    lines = [
        f"{em(EMOJI_WARNING, '⏳')} <b>{sc('sending sms...')}</b>\n",
        f"{bar} <b>{pct}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ: <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ: <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss: <b>{sent + failed}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ: <b>{speed_label}</b>\n",
    ]
    if credits is not None: lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs ʟᴇғᴛ: <b>{credits}</b>")
    lines.append(f"\n<i>{em(EMOJI_WARNING, '🛑')} sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀʏᴇɪɴ ᴀɢᴀʀ ʙᴇᴇᴄʜ ᴍᴇɪɴ ʀᴏᴋɴᴀ ʜᴏ.</i>")
    return "\n".join(lines)

def stop_send_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑", "danger")]])

def mask_number(n):
    if len(n) <= 4: return n
    return n[:2] + "******" + n[-4:]

def get_scan_status():
    global SCAN_STATUS, CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS
    if SCANNING_IN_PROGRESS: return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."
    if not CACHED_DEVICES: return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"
    c = len(CACHED_DEVICES); t = time.time() - LAST_SCAN_TIME
    if t < 60: return f"{em(EMOJI_CHECK, '🟢')} {c} ᴅᴇᴠɪᴄᴇs"
    elif t < 300: return f"{em(EMOJI_WARNING, '🟡')} {c} ᴅᴇᴠɪᴄᴇs ({int(t/60)}ᴍ ᴏʟᴅ)"
    return f"{em(EMOJI_CROSS, '🔴')} {c} ᴅᴇᴠɪᴄᴇs ({int(t/60)}ᴍ ᴏʟᴅ)"

async def background_firebase_scanner(bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS, DEVICE_HEALTH_LOG
    log.info("Background Scanner STARTED")
    first = False
    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(5); continue
            SCANNING_IN_PROGRESS = True
        SCAN_STATUS = f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ ғɪʀᴇʙᴀsᴇ ᴀᴘɪs..."
        st = time.time()
        try:
            d = load(); fbs = d.get("firebases", [])
            if not fbs:
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴅʙs"
                CACHED_DEVICES = []
                async with SCAN_LOCK: SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL); continue
            devices = await get_all_online_devices(d)
            dur = time.time() - st
            CACHED_DEVICES = devices
            for fb in fbs:
                fb_online = sum(1 for dv in devices if dv["fb_id"] == fb["id"])
                FB_DEVICE_COUNTS[fb["id"]] = {"label": fb.get("label", fb["url"][:30]),
                                               "online": fb_online, "last_update": int(time.time())}
            LAST_SCAN_TIME = time.time()
            DEVICE_HEALTH_LOG.append({"timestamp": int(time.time()), "devices_found": len(devices),
                                       "dbs_scanned": len(fbs), "duration_sec": round(dur, 2),
                                       "status": "healthy" if devices else "no_devices"})
            if len(DEVICE_HEALTH_LOG) > 100: DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-100:]
            if devices:
                SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴅᴇᴠɪᴄᴇs | {fmt_time(int(time.time()))}"
                log.info(f"[SCAN] {len(devices)} online | {len(fbs)} DBs")
                cur_ids = {fb["id"] for fb in fbs}
                for st_id in [k for k in FB_DEVICE_COUNTS if k not in cur_ids]: FB_DEVICE_COUNTS.pop(st_id, None)
                if not first:
                    try:
                        await bot.send_message(MAIN_OWNER,
                            f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('prime bomber active!')}</b>\n\n"
                            f"{em(EMOJI_PHONE, '📱')} ᴅᴇᴠɪᴄᴇs: <b>{len(devices)}</b>\n"
                            f"{em(EMOJI_FIRE, '🔥')} ᴅʙs: <b>{len(fbs)}</b>\n"
                            f"{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ-sᴄᴀɴ: <b>1 ᴍɪɴ</b>", parse_mode="HTML")
                    except: pass
                    first = True
            else:
                SCAN_STATUS = f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs | {fmt_time(int(time.time()))}"
        except Exception as e:
            SCAN_STATUS = f"{em(EMOJI_CROSS, '❌')} ᴇʀʀᴏʀ: {str(e)[:30]}"
            log.error(f"[SCAN] {e}")
        finally:
            async with SCAN_LOCK: SCANNING_IN_PROGRESS = False
        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

def get_cached_devices(): return CACHED_DEVICES

async def fb_get(base_url, path):
    url = base_url.rstrip("/") + path
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt: return {}
                    return json.loads(txt)
    except Exception as e: log.warning(f"fb_get {url}: {e}")
    return {}

async def fb_put(base_url, path, payload):
    url = base_url.rstrip("/") + path
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    if 200 <= r.status < 300: return True
        except Exception as e: log.warning(f"fb_put {attempt+1}: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))
    return False

def device_is_online(dd):
    return any([dd.get("isOnline"), dd.get("online"), dd.get("connected"),
                dd.get("status") in ("online", "active", True, 1)])

async def get_all_online_devices(d):
    fbs = d.get("firebases", [])
    if not fbs: return []
    results = []
    cur_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in cur_ids]
    sem = asyncio.Semaphore(15)

    async def fetch_one(fb):
        url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200: return
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt: return
                    dev_ids = json.loads(txt)
                    if not isinstance(dev_ids, dict): return

                    async def fetch_dev(dev_id):
                        try:
                            u = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                            async with sem:
                                async with s.get(u, timeout=aiohttp.ClientTimeout(total=8)) as r2:
                                    if r2.status == 200:
                                        t2 = (await r2.text()).strip()
                                        if t2 == "null" or not t2: return None
                                        dd = json.loads(t2)
                                        if isinstance(dd, dict) and device_is_online(dd):
                                            name = dd.get("deviceName") or dd.get("name") or dev_id[:16]
                                            return {"fb_id": fb["id"], "fb_url": fb["url"],
                                                    "fb_label": fb.get("label", fb["url"][:30]),
                                                    "dev_id": dev_id, "dev_name": name,
                                                    "sims": dd.get("sims", [])}
                        except Exception as e: log.warning(f"Dev {dev_id}: {e}")
                        return None

                    ids = list(dev_ids.keys())
                    for i in range(0, len(ids), 20):
                        batch = ids[i:i+20]
                        res = await asyncio.gather(*[fetch_dev(d_) for d_ in batch])
                        for x in res:
                            if x: results.append(x)
        except Exception as e: log.warning(f"fb_shallow {fb['url']}: {e}")

    await asyncio.gather(*[fetch_one(fb) for fb in fbs])
    return results

async def send_sms_via_device(fb_url, dev_id, sim_slot, to, message):
    return await fb_put(fb_url, f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {"from": sim_slot, "to": to.strip(), "message": message.strip(),
         "isSended": False, "timestamp": int(time.time())})

async def check_membership(bot, uid, channel_id):
    try:
        chat_id = int(str(channel_id).strip())
        m = await bot.get_chat_member(chat_id, uid)
        return m.status in ("member", "administrator", "creator")
    except Exception as e:
        log.error(f"FJ {channel_id}: {e}"); return False

async def user_joined_all(bot, uid, d):
    if is_owner(uid, d): return True, []
    fj = d.get("force_join", {})
    if not fj.get("enabled", False): return True, []
    missing = []
    for ch in fj.get("channels", []):
        if ch.get("required", True) and not await check_membership(bot, uid, ch["id"]):
            missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing):
    lines = [f"{em(EMOJI_CROSS, '⛔')} <b>{sc('bot use karne ke liye pehle join karein!')}</b>\n\n",
             f"{em(EMOJI_BELL, '👇')} ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:"]
    for ch in missing: lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join karne ke baad /start karein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing):
    rows = [[btn_url(f"ᴊᴏɪɴ {ch.get('title', 'Channel')}", ch["link"], EMOJI_BELL, "🔔", "success")] for ch in missing]
    rows.append([btn("ʀᴇғʀᴇsʜ", "fj:check", EMOJI_GEAR, "🔄", "primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fmt_time(ts): return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def fmt_duration(s):
    if s < 60: return f"{s}s"
    return f"{s // 60}m {s % 60}s"

def owner_panel_text(d):
    fbs = d.get("firebases", []); owners = d.get("owners", []); admins = d.get("admins", [])
    users = d.get("users", {}); stats = d.get("stats", {}); videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ"
    fj = d.get("force_join", {})
    fj_s = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    fb_lines = []
    for i, (fid, fd) in enumerate(list(FB_DEVICE_COUNTS.items())):
        if i >= 5:
            fb_lines.append(f"  {em(EMOJI_STAR, '➕')} +{len(FB_DEVICE_COUNTS)-5} more...")
            break
        age = int(time.time() - fd.get("last_update", 0))
        st = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {st} {fd['label'][:20]}: {fd['online']} ᴏɴʟɪɴᴇ")
    fb_sum = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"
    return (
        f"{em(EMOJI_CROWN, '👑')} <b>{sc('prime x bomber — owner panel')}</b>\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍɪɴs : <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_STAR, '👥')} ᴜsᴇʀs : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} sᴇɴᴛ : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ : <b>{active}</b>\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴍᴏᴅᴇ : {mode}\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ : {fj_s}\n"
        f"{em(EMOJI_MONEY, '💳')} ᴘʟᴀɴs : <b>{len(d.get('pricing', {}).get('plans', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} ᴘᴇʀ ғɪʀᴇʙᴀsᴇ:\n{fb_sum}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {get_scan_status()}\n━━━━━━━━━━━━━━━━━━"
    )

def admin_panel_text(d):
    users = d.get("users", {}); stats = d.get("stats", {}); banned = d.get("banned", [])
    videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ"
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    fb_lines = []
    for i, (fid, fd) in enumerate(list(FB_DEVICE_COUNTS.items())):
        if i >= 5:
            fb_lines.append(f"  {em(EMOJI_STAR, '➕')} +{len(FB_DEVICE_COUNTS)-5} more...")
            break
        age = int(time.time() - fd.get("last_update", 0))
        st = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {st} {fd['label'][:20]}: {fd['online']} ᴏɴʟɪɴᴇ")
    fb_sum = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"
    return (
        f"{em(EMOJI_SHIELD, '🛡')} <b>{sc('prime x bomber — admin panel')}</b>\n\n━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '👥')} ᴜsᴇʀs : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CROSS, '🚫')} ʙᴀɴɴᴇᴅ : <b>{len(banned)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} sᴇɴᴛ : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ : <b>{active}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴅʙs : <b>{len(d.get('firebases', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} ᴘᴇʀ ғɪʀᴇʙᴀsᴇ:\n{fb_sum}\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴍᴏᴅᴇ : {mode}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {get_scan_status()}\n━━━━━━━━━━━━━━━━━━"
    )

def user_home_text(uid, d):
    ud = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    return (
        f"{em(EMOJI_PHONE, '📱')} <b>{sc('prime x bomber')} {_VERSION}</b>\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"{em(EMOJI_STAR, '👤')} ʀᴏʟᴇ : {role_tag(uid, d)}\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{ud.get('credits', 0)}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs : <b>{ud.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {get_scan_status()}\n\n"
        f"ᴛᴀᴘ <b>{sc('start blast')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )

def owner_kb(d):
    mode_btn = (f"🔴 {sc('disable free mode')}", "owner:free:off") if d.get("free_mode") else (f"🟢 {sc('enable free mode')}", "owner:free:on")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤"), btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥")],
        [btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹"), btn("ᴍᴀɴᴀɢᴇ sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑")],
        [btn("ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡"), btn("ᴠɪᴇᴡ ᴜsᴇʀs", "owner:users:list", EMOJI_STAR, "👥")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "owner:ban", EMOJI_CROSS, "🚫"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "owner:unban:menu", EMOJI_CHECK, "✅")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "owner:broadcast", EMOJI_BELL, "📢"), btn("ᴀᴘɪ sᴛᴀᴛs", "owner:stats", EMOJI_STAR, "📊")],
        [btn("ᴀᴄᴛɪᴠɪᴛɪ ʟᴏɢ", "owner:activity", EMOJI_GEAR, "📜"), btn("ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs", "owner:pricing:menu", EMOJI_MONEY, "💳")],
        [btn("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs", "owner:redeem:menu", EMOJI_GIFT, "🎁"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💰"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "💰"), btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗")],
        [btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️"), btn("sᴍs ʜɪsᴛᴏʀʏ", "owner:sms_history", EMOJI_STAR, "📋")],
        [btn("ᴇxᴘᴏʀᴛ sᴄʀɪᴘᴛ", "owner:export_script", EMOJI_GEAR, "📤"), btn("ᴘʀᴏᴛᴇᴄᴛ ɴᴜᴍʙᴇʀ", "owner:protect", EMOJI_LOCK, "🔒")],
        [btn("ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐"), btn("ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ", "owner:track", EMOJI_STAR, "📊")],
        [InlineKeyboardButton(text=mode_btn[0], callback_data=mode_btn[1])],
        [btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄")],
    ])

def admin_kb(d):
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "📤", "success"), btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", "primary")],
        [btn("ᴠɪᴇᴡ ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥", "primary"), btn("ᴀᴘɪ sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊", "primary")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "admin:ban", EMOJI_CROSS, "🚫", "danger"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "admin:unban:menu", EMOJI_CHECK, "✅", "success")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢", "primary")],
        [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄", "primary")],
    ])

def user_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴛᴀʀᴛ ʙʟᴀsᴛ", "user:send", EMOJI_ROCKET, "📤", "success")],
        [btn("ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹", "primary"), btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳", "primary")],
        [btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁", "primary"), btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥", "primary")],
        [btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊", "primary"), btn("sᴍs ʜɪsᴛᴏʀʏ", "user:sms_history", EMOJI_STAR, "📜", "primary")],
        [btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰", "success")],
        [btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸", "primary")],
        [btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️", "primary")],
    ])

def videos_menu_kb(d):
    videos = d.get("videos", [])
    rows = [[btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕")],
            [btn("🗑 ʙᴜʟᴋ ᴅᴇʟᴇᴛᴇ ᴀʟʟ", "owner:videos:bulk_del", EMOJI_CROSS, "🗑")]]
    for idx, vid in enumerate(videos, 1):
        rows.append([btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx-1}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fb_menu_kb(d, page=0):
    fbs = d.get("firebases", [])
    per = 8
    total_pages = max(1, (len(fbs) + per - 1) // per)
    page = max(0, min(page, total_pages - 1))
    current = fbs[page*per:(page+1)*per]
    rows = [[btn("ᴀᴅᴅ ғɪʀᴇʙᴀsᴇ", "owner:fb:add", EMOJI_CHECK, "➕"),
             btn("📁 ᴀᴅᴅ ᴠɪᴀ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄")]]
    for fb in current:
        label = fb.get("label", fb["url"].replace("https://", ""))
        if len(label) > 16: label = label[:14] + ".."
        rows.append([btn(label, "noop", EMOJI_FIRE, "🔥"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑")])
    nav = []
    if page > 0: nav.append(btn("◀️ ᴘʀᴇᴠ", f"owner:fb:menu:{page-1}", EMOJI_GEAR, "◀️"))
    if page < total_pages - 1: nav.append(btn("ɴᴇxᴛ ▶️", f"owner:fb:menu:{page+1}", EMOJI_GEAR, "▶️"))
    if nav: rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owners_menu_kb(d):
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6: rows.append([btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕")])
    for oid in owners:
        if oid == MAIN_OWNER: rows.append([btn(f"{oid} (ᴍᴀɪɴ)", "noop", EMOJI_CROWN, "👑")])
        else: rows.append([btn(f"{oid}", "noop", EMOJI_CROWN, "🔱"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d):
    admins = d.get("admins", [])
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕")]]
    for aid in admins:
        rows.append([btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d, prefix):
    banned = d.get("banned", [])
    rows = [[btn(f"{bid}", f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓")] for bid in banned]
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def users_list_kb(d, prefix, page=0):
    users = d.get("users", {})
    items = list(users.items())
    per = 10; start = page * per
    chunk = items[start:start+per]
    approved = d.get("approved", []); banned = d.get("banned", [])
    lines = [f"{em(EMOJI_STAR, '👥')} <b>{sc('users')} ({len(items)} ᴛᴏᴛᴀʟ)</b>\n"]
    for uid_str, udata in chunk:
        u = int(uid_str); name = udata.get("name", "Unknown")
        uses = udata.get("uses", 0); credits = udata.get("credits", 0)
        if u in banned: s = em(EMOJI_CROSS, "🚫")
        elif u in approved: s = em(EMOJI_CHECK, "✅")
        elif is_owner(u, d): s = em(EMOJI_CROWN, "👑")
        elif u in d["admins"]: s = em(EMOJI_SHIELD, "🛡")
        else: s = em(EMOJI_STAR, "👤")
        lines.append(f"{s} <code>{u}</code> — {name[:18]} | 💰{credits} | 📤{uses}")
    rows = []; nav = []
    if page > 0: nav.append(btn("◀️ ᴘʀᴇᴠ", f"{prefix}:users:pg:{page-1}", EMOJI_GEAR, "◀️"))
    if start + per < len(items): nav.append(btn("ɴᴇxᴛ ▶️", f"{prefix}:users:pg:{page+1}", EMOJI_GEAR, "▶️"))
    if nav: rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

def api_stats_text(d):
    stats = d.get("stats", {}); api_use = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [f"{em(EMOJI_STAR, '📊')} <b>{sc('api stats')}</b>\n",
             f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ : <b>{stats.get('total_sent', 0)}</b>",
             f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n━━━━━━━━━━━━━━━━━━"]
    if not api_use: lines.append(f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴜsᴀɢᴇ")
    for fb_id, fs in api_use.items():
        fb = fbs.get(fb_id); label = fb.get("label", fb_id[:20]) if fb else fb_id[:20]
        label = label.replace("<","&lt;").replace(">","&gt;").replace("&","&amp;")
        lines.append(f"{em(EMOJI_FIRE, '🔥')} {label}\n   ✅ {fs.get('sent', 0)} sᴇɴᴛ  ❌ {fs.get('failed', 0)} ғᴀɪʟᴇᴅ")
    return "\n".join(lines)

R = Router()

# ========== /START ==========
@R.message(CommandStart(deep_link=True))
async def cmd_start_deep(msg, state):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))
    name = msg.from_user.full_name or "User"
    uname = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)
    if is_new:
        log_text = (f"🆕 <b>NEW USER</b>\n\n👤 <b>Name:</b> {name}\n🆔 <b>ID:</b> <code>{uid}</code>\n"
                    f"🌐 <b>Username:</b> {uname}\n📅 <code>{fmt_time(int(time.time()))}</code>")
        asyncio.create_task(send_channel_log(msg.bot, log_text))
    args = msg.text.split()
    code = args[1] if len(args) > 1 else ""
    if code.startswith("REF") and not d["users"].get(str(uid), {}).get("referred_by"):
        ok, txt, ref = process_referral(uid, code, d)
        if ok and ref:
            try:
                rn = d["users"].get(str(uid), {}).get("name", "Someone")
                await msg.bot.send_message(ref, f"{em(EMOJI_GIFT, '🎉')} <b>{rn}</b> ne aapka referral use kiya!\n+{d['settings']['ref_credits']} credits!", parse_mode="HTML")
            except: pass
    save(d)
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to Prime x Bomber!\nOwner: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        await msg.answer(f"{em(EMOJI_CROWN, '👑')} <b>Prime x Bomber — Owner Panel</b>\n👇 Use buttons below", reply_markup=owner_reply_keyboard())
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        await msg.answer(f"{em(EMOJI_SHIELD, '🛡')} <b>Prime x Bomber — Admin Panel</b>\n👇 Use buttons below", reply_markup=admin_reply_keyboard())
        return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML"); return
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nOwner se approval lein.", parse_mode="HTML"); return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
    await msg.answer(f"{em(EMOJI_ROCKET, '🚀')} <b>Prime x Bomber</b>\n👇 Use buttons below", reply_markup=user_reply_keyboard())

@R.message(Command("start"))
async def cmd_start(msg, state):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))
    name = msg.from_user.full_name or "User"
    uname = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)
    save(d)
    if is_new:
        log_text = (f"🆕 <b>NEW USER</b>\n\n👤 <b>Name:</b> {name}\n🆔 <b>ID:</b> <code>{uid}</code>\n"
                    f"🌐 <b>Username:</b> {uname}\n📅 <code>{fmt_time(int(time.time()))}</code>")
        asyncio.create_task(send_channel_log(msg.bot, log_text))
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to Prime x Bomber!\nOwner: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        await msg.answer(f"{em(EMOJI_CROWN, '👑')} Owner Panel buttons 👇", reply_markup=owner_reply_keyboard()); return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        await msg.answer(f"{em(EMOJI_SHIELD, '🛡')} Admin Panel buttons 👇", reply_markup=admin_reply_keyboard()); return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML"); return
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>", parse_mode="HTML"); return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
    await msg.answer(f"{em(EMOJI_ROCKET, '🚀')} User buttons 👇", reply_markup=user_reply_keyboard())

# ========== REPLY KEYBOARD HANDLERS ==========
@R.message(F.text == "🚀 Start Blast")
async def rk_start_blast(msg, state):
    await _user_send_start(msg, state)

@R.message(F.text == "📹 Videos")
async def rk_videos(msg, state):
    d = load(); videos = d.get("videos", [])
    if not videos:
        await msg.answer("❌ Abhi koi video available nahi hai!"); return
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!")

@R.message(F.text == "💰 Credits")
async def rk_credits(msg):
    d = load(); await msg.answer(f"💰 Credits: <b>{get_user_credits(msg.from_user.id, d)}</b>", parse_mode="HTML")

@R.message(F.text == "🛑 Stop Blast")
async def rk_stop(msg):
    uid = msg.from_user.id
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(uid)
        if not s or (s.task and s.task.done()):
            await msg.answer("✅ Koi active sending nahi!"); return
        s.cancelled = True
    await msg.answer("🛑 Stop signal bhej diya!")

@R.message(F.text == "🎁 Redeem")
async def rk_redeem(msg, state):
    await state.set_state(S.redeem_code)
    await msg.answer(f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Code</b>\n\nApna code enter karein:",
                     reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

@R.message(F.text == "👥 Refer")
async def rk_refer(msg):
    d = load(); uid = msg.from_user.id
    code = generate_user_refer_code(uid, d); save(d)
    rc = d.get("settings", {}).get("ref_credits", 3)
    me = await msg.bot.get_me()
    await msg.answer(f"{em(EMOJI_STAR, '👥')} <b>Referral</b>\n\n🎁 Code: <code>{code}</code>\n"
                     f"🔗 https://t.me/{me.username}?start={code}\n\nHar referral pe <b>{rc}</b> credits!",
                     parse_mode="HTML")

@R.message(F.text == "📊 Stats")
async def rk_stats(msg):
    d = load(); uid = msg.from_user.id
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"); return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML"); return
    ud = d["users"].get(str(uid), {}); st = d.get("stats", {})
    await msg.answer(f"{em(EMOJI_STAR, '📊')} <b>Your Stats</b>\n\n"
                     f"💰 Credits: <b>{ud.get('credits', 0)}</b>\n📤 Sent: <b>{ud.get('uses', 0)}</b>\n"
                     f"📈 Bot Total: <b>{st.get('total_sent', 0)}</b>", parse_mode="HTML")

@R.message(F.text == "ℹ️ Info")
async def rk_info(msg):
    await msg.answer(f"{em(EMOJI_GEAR, 'ℹ️')} <b>Prime x Bomber {_VERSION}</b>\n\n"
                     f"👤 Owner: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>",
                     parse_mode="HTML", disable_web_page_preview=True)

@R.message(F.text == "💸 Transfer Credits")
async def rk_transfer(msg, state):
    await _user_transfer_start(msg, state)

@R.message(F.text == "🚀 Send SMS")
async def rk_send_sms(msg, state):
    d = load(); uid = msg.from_user.id
    if is_owner(uid, d): await _owner_send_start(msg, state)
    elif is_admin(uid, d): await _admin_send_start(msg, state)

@R.message(F.text == "👥 Users")
async def rk_users(msg):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d): return
    prefix = "owner" if is_owner(uid, d) else "admin"
    text, markup = users_list_kb(d, prefix, 0)
    await msg.answer(text, reply_markup=markup, parse_mode="HTML")

@R.message(F.text == "📢 Broadcast")
async def rk_broadcast(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d): return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    await msg.answer(f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\nMessage type karo:",
                     reply_markup=kb([(f"{sc('cancel')}", back)]), parse_mode="HTML")

@R.message(F.text == "🚫 Ban User")
async def rk_ban(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d): return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(uid, d) else "admin:home"
    await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Ban User</b>\n\nUser ID bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", back)]), parse_mode="HTML")

@R.message(F.text == "✅ Unban User")
async def rk_unban(msg):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d): return
    banned = d.get("banned", [])
    if not banned: await msg.answer("✅ Koi banned nahi!"); return
    prefix = "owner" if is_owner(uid, d) else "admin"
    await msg.answer(f"{em(EMOJI_CHECK, '🔓')} <b>Unban</b>\n\nBanned: <b>{len(banned)}</b>",
                     reply_markup=unban_menu_kb(d, prefix), parse_mode="HTML")

@R.message(F.text == "🔥 Firebase")
async def rk_firebase(msg):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    await msg.answer(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b>",
                     reply_markup=fb_menu_kb(d, 0), parse_mode="HTML")

@R.message(F.text == "🛡 Admins")
async def rk_admins(msg):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    await msg.answer(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>\n\nTotal: <b>{len(d.get('admins', []))}</b>",
                     reply_markup=admins_menu_kb(d), parse_mode="HTML")

@R.message(F.text == "👑 Owners")
async def rk_owners(msg):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    await msg.answer(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>\n\nTotal: <b>{len(d.get('owners', []))}/6</b>",
                     reply_markup=owners_menu_kb(d), parse_mode="HTML")

@R.message(F.text == "💰 Add Credits")
async def rk_add_credits(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    await state.set_state(S.add_credits_uid)
    await msg.answer(f"{em(EMOJI_MONEY, '💰')} <b>Add Credits</b>\n\nUser ID bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(F.text == "💸 Deduct Credits")
async def rk_deduct_credits(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    await state.set_state(S.deduct_credits_uid)
    await msg.answer(f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits</b>\n\nUser ID bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(F.text == "🎁 Redeem Codes")
async def rk_redeem_codes(msg):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    codes = d.get("redeem_codes", {})
    text = f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes</b>\n\nTotal: <b>{len(codes)}</b>\n\n"
    for c, data in list(codes.items())[:10]:
        st = "✅" if data.get("uses_left", 0) > 0 else "❌"
        text += f"<code>{c}</code> — 💰{data['credits']} — {st} ({data.get('uses_left', 0)})\n"
    rows = [[btn("ɢᴇɴᴇʀᴀᴛᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕")],
            [btn("ᴅᴇʟᴇᴛᴇ", "owner:redeem:del", EMOJI_CROSS, "🗑")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]]
    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.message(F.text == "📜 Activity")
async def rk_activity(msg):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    entries = d.get("activity_log", [])[-20:]
    if not entries:
        await msg.answer("📜 Koi activity nahi."); return
    lines = ["📜 <b>Recent Activity</b>\n"]
    for e in reversed(entries):
        lines.append(f"[{fmt_time(e.get('timestamp',0))}] <code>{e.get('uid',0)}</code> — {e.get('action','?')}")
    await msg.answer("\n".join(lines), parse_mode="HTML")

@R.message(F.text == "🔒 Protect Number")
async def rk_protect(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    await state.set_state(S.protect_number)
    await msg.answer(f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\nNumber bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(F.text == "🔗 Force Join")
async def rk_fj(msg):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): return
    fj = d.get("force_join", {}); chs = fj.get("channels", [])
    status = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    text = f"{em(EMOJI_BELL, '🔗')} <b>Force Join</b>\n\nStatus: {status}\nChannels: <b>{len(chs)}</b>\n\n"
    for ch in chs:
        text += f"• {ch.get('title','Channel')} (<code>{ch['id']}</code>)\n"
    rows = [[btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕")],
            [btn("ʀᴇᴍᴏᴠᴇ", "owner:fj:remove", EMOJI_CROSS, "🗑")],
            [InlineKeyboardButton(text=f"🟢 {sc('enable')}" if not fj.get("enabled") else f"🔴 {sc('disable')}", callback_data="owner:fj:toggle")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]]
    await msg.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.message(F.text == "🔙 Panel")
async def rk_panel(msg, state):
    await state.clear()
    d = load(); uid = msg.from_user.id
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.message(F.text == "🔄 Refresh")
async def rk_refresh(msg, state):
    await rk_panel(msg, state)

# ========== INTERNAL HELPERS ==========
async def _user_send_start(msg, state):
    d = load(); uid = msg.from_user.id
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True); return
    if not can_use(uid, d):
        await msg.answer("🚫 Access denied!"); return
    await state.set_state(S.send_number)
    await msg.answer(f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\nNumber bhejo:\n<i>Example: +919876543210</i>",
                     reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

async def _owner_send_start(msg, state):
    await state.set_state(S.owner_send_number)
    await msg.answer(f"{em(EMOJI_CROWN, '👑')} <b>Owner SMS</b>\n\nNumber bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

async def _admin_send_start(msg, state):
    await state.set_state(S.admin_send_number)
    await msg.answer(f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS</b>\n\nNumber bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", "admin:home")]), parse_mode="HTML")

async def _user_transfer_start(msg, state):
    d = load(); uid = msg.from_user.id
    if is_banned(uid, d): await msg.answer("🚫 Banned!"); return
    if not can_use(uid, d): await msg.answer("⛔ Access nahi!"); return
    c = get_user_credits(uid, d)
    if c < 2: await msg.answer("❌ Minimum 2 credits chahiye!"); return
    await state.set_state(S.transfer_credits_uid)
    await msg.answer(f"{em(EMOJI_MONEY, '💸')} <b>Transfer Credits</b>\n\nYour: <b>{c}</b>\n\nTarget User ID bhejo:",
                     reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

# ========== CALLBACKS (SEND FLOWS) ==========
@R.callback_query(F.data == "user:send")
async def user_send_start(cq, state):
    await _user_send_start(cq.message, state)
    try: await cq.message.delete()
    except: pass
    await cq.answer()

@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True); return
    await _owner_send_start(cq.message, state)
    try: await cq.message.delete()
    except: pass
    await cq.answer()

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True); return
    await _admin_send_start(cq.message, state)
    try: await cq.message.delete()
    except: pass
    await cq.answer()

# ========== FSM: SEND NUMBER/MESSAGE/SPEED/COUNT ==========
@R.message(S.send_number)
async def user_got_number(msg, state):
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid. Example: +919876543210"); return
    if n in PROTECTED_NUMBERS:
        await msg.answer(f"{em(EMOJI_LOCK, '🔒')} Ye number protected hai!"); return
    await state.update_data(number=n)
    await state.set_state(S.send_message)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Number: <code>{mask_number(n)}</code>\n\n"
                     f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — Message</b>\n\nType karo:",
                     reply_markup=kb([(f"{sc('cancel')}", "user:cancel")]), parse_mode="HTML")

@R.message(S.send_message)
async def user_got_message(msg, state):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — Speed</b>",
                     reply_markup=speed_kb("user"), parse_mode="HTML")

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed(cq, state):
    d = load(); uid = cq.from_user.id
    smap = {"user:speed:fast": SPEED_FAST, "user:speed:medium": SPEED_MEDIUM, "user:speed:slow": SPEED_SLOW}
    sp = smap.get(cq.data, SPEED_MEDIUM)
    sl = "🚀 FAST" if sp == SPEED_FAST else "⚡ MEDIUM" if sp == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sp)
    await state.set_state(S.send_count)
    devs = get_cached_devices() or await get_all_online_devices(d)
    c = len(devs)
    ci = ""
    if not is_admin(uid, d):
        ci = f"\n💰 Credits: <b>{get_user_credits(uid, d)}</b>\n"
    await cq.message.edit_text(f"{sl} selected!\n\n{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — Count</b>\n\n"
                               f"🔥 APIs: <b>{c}</b>\n📤 Capacity: <b>{c*3}</b>{ci}\n\nKitne SMS?",
                               reply_markup=kb([(f"{sc('cancel')}", "user:cancel")]), parse_mode="HTML")

@R.message(S.send_count)
async def user_count(msg, state):
    d = load(); uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        c = int(msg.text.strip())
        if c < 1: raise ValueError
    except:
        await msg.answer("❌ Sirf number bhejo:"); return
    await state.clear()
    num = fsmd.get("number", ""); m = fsmd.get("message", ""); sp = fsmd.get("send_speed", SPEED_DEFAULT)
    if not is_admin(uid, d):
        cc = get_user_credits(uid, d)
        if cc <= 0:
            await msg.answer("❌ Credits nahi hain! Admin se contact karein."); return
        if c > cc:
            await msg.answer(f"⚠️ Sirf {cc} credits. {cc} bhej raha hoon...")
            c = cc
    devs = get_cached_devices() or await get_all_online_devices(d)
    if not devs:
        await msg.answer("😴 Koi API online nahi!"); return
    await run_sms_blast_with_progress(msg.bot, msg, uid, num, m, c, devs, sp)

@R.message(S.owner_send_number)
async def owner_got_number(msg, state):
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer("❌ Invalid."); return
    await state.update_data(number=n)
    await state.set_state(S.owner_send_message)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Number: <code>{n}</code>\n\nMessage type karo:",
                     reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.owner_send_message)
async def owner_got_message(msg, state):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer("⚡ Speed:", reply_markup=speed_kb("owner"))

@R.callback_query(F.data.in_({"owner:speed:fast","owner:speed:medium","owner:speed:slow"}))
async def owner_speed(cq, state):
    smap = {"owner:speed:fast": SPEED_FAST, "owner:speed:medium": SPEED_MEDIUM, "owner:speed:slow": SPEED_SLOW}
    sp = smap.get(cq.data, SPEED_MEDIUM)
    sl = "🚀 FAST" if sp == SPEED_FAST else "⚡ MEDIUM" if sp == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sp)
    await state.set_state(S.owner_send_count)
    devs = get_cached_devices() or await get_all_online_devices(load())
    c = len(devs)
    await cq.message.edit_text(f"{sl} selected!\n\n🔥 APIs: <b>{c}</b>\n📤 Capacity: <b>{c*3}</b>\n\nKitne SMS?",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.owner_send_count)
async def owner_count(msg, state):
    fsmd = await state.get_data()
    try:
        c = int(msg.text.strip())
        if c < 1: raise ValueError
    except:
        await msg.answer("❌ Sirf number:"); return
    await state.clear()
    num = fsmd.get("number", ""); m = fsmd.get("message", ""); sp = fsmd.get("send_speed", SPEED_DEFAULT)
    devs = get_cached_devices() or await get_all_online_devices(load())
    if not devs: await msg.answer("😴 Koi API nahi!"); return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, num, m, c, devs, sp)

@R.message(S.admin_send_number)
async def admin_got_number(msg, state):
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer("❌ Invalid."); return
    if n in PROTECTED_NUMBERS:
        p = PROTECTED_NUMBERS[n]
        if not is_owner(msg.from_user.id, load()) and msg.from_user.id != p:
            await msg.answer("🔒 Ye number protected hai!"); return
    await state.update_data(number=n)
    await state.set_state(S.admin_send_message)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Number: <code>{mask_number(n)}</code>\n\nMessage:",
                     reply_markup=kb([(f"{sc('cancel')}", "admin:home")]), parse_mode="HTML")

@R.message(S.admin_send_message)
async def admin_got_message(msg, state):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer("⚡ Speed:", reply_markup=speed_kb("admin"))

@R.callback_query(F.data.in_({"admin:speed:fast","admin:speed:medium","admin:speed:slow"}))
async def admin_speed(cq, state):
    smap = {"admin:speed:fast": SPEED_FAST, "admin:speed:medium": SPEED_MEDIUM, "admin:speed:slow": SPEED_SLOW}
    sp = smap.get(cq.data, SPEED_MEDIUM)
    sl = "🚀 FAST" if sp == SPEED_FAST else "⚡ MEDIUM" if sp == SPEED_MEDIUM else "🐢 SLOW"
    await state.update_data(send_speed=sp)
    await state.set_state(S.admin_send_count)
    devs = get_cached_devices() or await get_all_online_devices(load())
    c = len(devs)
    await cq.message.edit_text(f"{sl} selected!\n\n🔥 APIs: <b>{c}</b>\n📤 Capacity: <b>{c*3}</b>\n\nKitne SMS?",
                               reply_markup=kb([(f"{sc('cancel')}", "admin:home")]), parse_mode="HTML")

@R.message(S.admin_send_count)
async def admin_count(msg, state):
    fsmd = await state.get_data()
    try:
        c = int(msg.text.strip())
        if c < 1: raise ValueError
    except:
        await msg.answer("❌ Sirf number:"); return
    await state.clear()
    num = fsmd.get("number", ""); m = fsmd.get("message", ""); sp = fsmd.get("send_speed", SPEED_DEFAULT)
    devs = get_cached_devices() or await get_all_online_devices(load())
    if not devs: await msg.answer("😴 Koi API nahi!"); return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, num, m, c, devs, sp)

# ========== MAIN SMS BLAST ==========
async def run_sms_blast_with_progress(bot, msg, uid, number, message, count, devices, speed=SPEED_DEFAULT):
    await send_random_video(bot, msg.chat.id, caption=f"💣 <b>Prime x Bomber — SMS on {mask_number(number)}!</b>")
    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old = USER_SESSIONS[uid]
            if old.task and not old.task.done():
                await msg.answer("⚠️ Ek sending already chal rahi hai!"); return
            del USER_SESSIONS[uid]
        s = UserSession(uid)
        s.number = number; s.blast_data = load()
        USER_SESSIONS[uid] = s
    is_reg = not is_admin(uid, load()) and not is_owner(uid, load())
    cc = get_user_credits(uid, load()) if is_reg else None
    sl = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"
    try:
        pmsg = await msg.answer(progress_text(0, 0, count, cc, sl), reply_markup=stop_send_kb(), parse_mode="HTML")
    except Exception as e:
        log.error(f"Progress fail: {e}")
        async with SESSIONS_LOCK:
            if uid in USER_SESSIONS: del USER_SESSIONS[uid]
        return
    so = 0; sf = 0; left = count; api_delta = {}; lt = time.time(); st = time.time()

    async def do_send():
        nonlocal so, sf, left, lt
        try:
            for dev in devices:
                if left <= 0: break
                async with s.lock:
                    if s.cancelled: break
                fb_id = dev["fb_id"]; fb_url = dev["fb_url"]; did = dev["dev_id"]; sims = dev["sims"]
                slots = [x.get("simSlotIndex", 0) for x in sims] if sims else [0]
                quota = min(3, left); dsv = 0
                for sim in slots:
                    async with s.lock:
                        if dsv >= quota or left <= 0 or s.cancelled: break
                    ok = await send_sms_via_device(fb_url, did, sim, number, message)
                    async with s.lock:
                        if ok:
                            so += 1; dsv += 1; left -= 1
                            if is_reg:
                                deduct_credits(uid, 1, s.blast_data)
                                s.blast_data["stats"]["total_sent"] = s.blast_data["stats"].get("total_sent", 0) + 1
                                k = str(uid)
                                if k in s.blast_data["users"]:
                                    s.blast_data["users"][k]["uses"] = s.blast_data["users"][k].get("uses", 0) + 1
                                s.blast_data.setdefault("sms_history", {}).setdefault(str(uid), []).append(
                                    {"number": number, "message": message[:100], "timestamp": int(time.time()), "status": "sent"})
                        else:
                            sf += 1; left -= 1
                        api_delta.setdefault(fb_id, {"sent": 0, "failed": 0})
                        api_delta[fb_id]["sent" if ok else "failed"] += 1
                        n = time.time()
                        if (n - lt >= _PROGRESS_UPDATE_INTERVAL or (so + sf) == count or s.cancelled):
                            cl = get_user_credits(uid, load()) if is_reg else None
                            try:
                                await pmsg.edit_text(progress_text(so, sf, count, cl, sl),
                                    reply_markup=stop_send_kb() if not s.cancelled else None, parse_mode="HTML")
                            except TelegramBadRequest: pass
                            lt = n
                    await asyncio.sleep(speed)
        except Exception as e: log.error(f"Send loop {uid}: {e}")
        finally:
            async with s.lock: s.sent = so; s.failed = sf

    task = asyncio.create_task(do_send()); s.task = task
    await task
    wc = s.cancelled
    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS: del USER_SESSIONS[uid]
    if not is_reg:
        df = s.blast_data or load()
        df["stats"]["total_sent"] = df["stats"].get("total_sent", 0) + so
        df["stats"]["total_failed"] = df["stats"].get("total_failed", 0) + sf
        for fid, d_ in api_delta.items():
            df["stats"].setdefault("api_usage", {}).setdefault(fid, {"sent": 0, "failed": 0})
            df["stats"]["api_usage"][fid]["sent"] += d_["sent"]
            df["stats"]["api_usage"][fid]["failed"] += d_["failed"]
        k = str(uid)
        if k in df["users"]: df["users"][k]["uses"] = df["users"][k].get("uses", 0) + so
        df.setdefault("sms_history", {}).setdefault(str(uid), []).append(
            {"number": number, "message": message[:100], "timestamp": int(time.time()), "status": "completed" if not wc else "stopped"})
        save(df)
    else:
        df = s.blast_data or load()
        df["stats"]["total_failed"] = df["stats"].get("total_failed", 0) + sf
        for fid, d_ in api_delta.items():
            df["stats"].setdefault("api_usage", {}).setdefault(fid, {"sent": 0, "failed": 0})
            df["stats"]["api_usage"][fid]["failed"] += d_["failed"]
        save(df)
    dlog = load()
    dur = int(time.time() - st)
    log_activity(dlog, "sms_blast", uid, f"Sent:{so} Fail:{sf} Total:{count} Dur:{fmt_duration(dur)} Stop:{wc}")
    save(dlog)
    try:
        uc = await bot.get_chat(uid)
        un = uc.full_name or "Unknown"
        uu = f"@{uc.username}" if uc.username else "No"
    except: un = "Unknown"; uu = "No"
    cl = (f"🚀 <b>SMS BLAST LOG — PRIME X BOMBER</b>\n\n👤 <b>User:</b> {un}\n🆔 <code>{uid}</code>\n"
          f"🌐 {uu}\n📞 <code>{number}</code>\n💬 <code>{message}</code>\n✅ {so}\n❌ {sf}\n"
          f"📊 {count}\n⏱ {fmt_duration(dur)}\n🛑 {'STOPPED' if wc else 'COMPLETED'}")
    asyncio.create_task(send_channel_log(bot, cl))
    ic = em(EMOJI_CHECK, "✅") if sf == 0 and so > 0 else em(EMOJI_WARNING, "⚠️") if so > 0 else em(EMOJI_CROSS, "❌")
    ct = ""
    if is_reg:
        rem = get_user_credits(uid, load())
        ct = f"\n💰 Used: <b>{so}</b>\n💳 Remaining: <b>{rem}</b>"
    stxt = f"\n🛑 <b>Stopped!</b>" if wc else ""
    if is_owner(uid, load()): bkb = [btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙")]
    elif is_admin(uid, load()): bkb = [btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙")]
    else: bkb = [btn("sᴇɴᴅ ᴀɴᴏᴛʜᴇʀ", "user:send", EMOJI_ROCKET, "📤"), btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠")]
    try:
        await pmsg.edit_text(f"{ic} <b>SMS Blast Result</b>{stxt}\n\n📞 <code>{mask_number(number)}</code>\n"
                             f"💬 <code>{message[:50]}{'...' if len(message)>50 else ''}</code>\n"
                             f"✅ Sent: <b>{so}</b>\n❌ Failed: <b>{sf}</b>\n🔥 APIs: <b>{len(api_delta)}</b>\n"
                             f"⏱ Duration: <b>{fmt_duration(int(time.time()-st))}</b>{ct}",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[bkb]), parse_mode="HTML")
    except Exception as e: log.error(f"Final edit: {e}")

@R.callback_query(F.data == "user:stop_send")
async def user_stop(cq, state):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(uid)
        if not s or (s.task and s.task.done()):
            await cq.answer("✅ Already done!"); return
        s.cancelled = True
    await cq.answer("🛑 Stop signal bheja!", show_alert=True)

# ========== VIDEO ==========
@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Denied!", show_alert=True); return
    v = d.get("videos", [])
    await cq.message.edit_text(f"{em(EMOJI_VIDEO, '📹')} <b>Videos</b>\n\nTotal: <b>{len(v)}</b>",
                               reply_markup=videos_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Denied!", show_alert=True); return
    await state.set_state(S.add_video)
    await cq.message.edit_text("📹 Video bhejo ya URL/FileID:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:videos:menu")]), parse_mode="HTML")

@R.message(S.add_video)
async def owner_videos_add_done(msg, state):
    d = load()
    if not is_admin(msg.from_user.id, d): await state.clear(); return
    vfid = None
    if msg.video: vfid = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video"): vfid = msg.document.file_id
    elif msg.text: vfid = msg.text.strip()
    if not vfid: await msg.answer("❌ Valid video:"); return
    d.setdefault("videos", []).append(vfid); save(d); await state.clear()
    await msg.answer("✅ Video saved!", reply_markup=videos_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    i = int(cq.data.split("owner:videos:del:", 1)[1])
    v = d.get("videos", [])
    if 0 <= i < len(v): v.pop(i); d["videos"] = v; save(d); await cq.answer("🗑 Removed!")
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    d["videos"] = []; save(d)
    await cq.answer("🗑 All videos deleted!", show_alert=True)
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "user:random_video")
async def user_video(cq, state):
    d = load()
    if not d.get("videos", []): await cq.answer("❌ Koi video nahi!", show_alert=True); return
    await cq.answer("📹 Sending...")
    await send_random_video(cq.bot, cq.message.chat.id, f"{em(EMOJI_VIDEO, '📹')} Enjoy!")

# ========== PROTECT / TRACK ==========
@R.callback_query(F.data == "owner:protect")
async def owner_protect(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫 Owner only!", show_alert=True); return
    await state.set_state(S.protect_number)
    await cq.message.edit_text("🔒 <b>Protect Number</b>\n\nNumber bhejo:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.protect_number)
async def owner_protect_done(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): await state.clear(); return
    n = msg.text.strip()
    if not n.replace("+","").replace(" ","").isdigit() or len(n) < 7:
        await msg.answer("❌ Invalid."); return
    PROTECTED_NUMBERS[n] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS; save(d); await state.clear()
    await msg.answer(f"🔒 Protected: <code>{n}</code>\n\nSirf Owner/Admin use kar sakte hain.",
                     reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")
    log_activity(d, "protect_number", uid, f"Protected {n}")

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq, state):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d) and not is_admin(uid, d): await cq.answer("🚫"); return
    p = d.get("protected_numbers", {})
    if not p:
        await cq.message.edit_text("🔐 Koi number protected nahi.",
                                   reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML"); return
    lines = ["🔐 <b>Protected Numbers</b>\n"]
    o = is_owner(uid, d) or is_main_owner(uid)
    for num, pu in p.items():
        dn = num if o else mask_number(num)
        pd = d.get("users", {}).get(str(pu), {})
        lines.append(f"📞 <code>{dn}</code> — 🔒 <code>{pu}</code> ({pd.get('name','?')})")
    rows = []
    if o: rows.append([btn("ʀᴇᴍᴏᴠᴇ", "owner:protected_remove", EMOJI_CROSS, "🗑")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove(cq, state):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d): await cq.answer("🚫"); return
    p = d.get("protected_numbers", {})
    if not p: await cq.answer("❌ Koi nahi!"); return
    rows = [[btn(num, f"owner:protected_del:{num}", EMOJI_CROSS, "🗑")] for num in p]
    rows.append([btn("ʙᴀᴄᴋ", "owner:protected_list", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text("🗑 Remove?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq, state):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d): await cq.answer("🚫"); return
    num = cq.data.split("owner:protected_del:", 1)[1]
    if num in d.get("protected_numbers", {}):
        del d["protected_numbers"][num]; save(d)
        global PROTECTED_NUMBERS
        PROTECTED_NUMBERS = d["protected_numbers"]
        await cq.answer(f"✅ Removed {num}", show_alert=True)
    await owner_protected_list(cq, state)

@R.callback_query(F.data == "owner:track")
async def owner_track(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.track_number)
    await cq.message.edit_text("📊 <b>Track Number</b>\n\nNumber bhejo:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.track_number)
async def owner_track_done(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): await state.clear(); return
    num = msg.text.strip()
    if not num.replace("+","").replace(" ","").isdigit() or len(num) < 7:
        await msg.answer("❌ Invalid."); return
    await state.clear()
    ah = d.get("sms_history", {})
    found = []
    for uid_str, h in ah.items():
        for e in h:
            if e.get("number") == num:
                ud = d.get("users", {}).get(uid_str, {})
                found.append({"uid": int(uid_str), "name": ud.get("name", "?"), "ts": e.get("timestamp", 0)}); break
    if not found:
        await msg.answer(f"📊 <b>Tracker</b>\n\n📞 <code>{num}</code>\n\n❌ Koi nahi bheja.",
                         reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML"); return
    lines = [f"📊 <b>Tracker</b>\n\n📞 <code>{num}</code>\n\n👥 Users:"]
    for e in found: lines.append(f"• <code>{e['uid']}</code> — {e['name'][:20]} — {fmt_time(e['ts'])}")
    await msg.answer("\n".join(lines), reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

# ========== ADD ALL / DEDUCT ALL ==========
@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text("💰 <b>Add Credits to ALL</b>\n\nAmount:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.add_all_credits_amount)
async def owner_add_all_done(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): await state.clear(); return
    try:
        a = int(msg.text.strip())
        if a <= 0: raise ValueError
    except: await msg.answer("❌ Valid number:"); return
    await state.clear()
    users = d.get("users", {})
    if not users: await msg.answer("❌ No users!"); return
    cnt = 0
    for uid_str in users: add_credits(int(uid_str), a, d, is_manual=True); cnt += 1
    save(d)
    n = f"💰 <b>Credits Added!</b>\n\n🎉 +{a} credits!\n💳 Check /start"
    ok = 0
    for uid_str in users:
        try: await msg.bot.send_message(int(uid_str), n, parse_mode="HTML"); ok += 1; await asyncio.sleep(0.05)
        except: pass
    await msg.answer(f"✅ <b>Added to {cnt} users</b>\n💰 {a} each\n📨 Notified: {ok}",
                     reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")
    log_activity(d, "add_all_credits", uid, f"Added {a} to {cnt}")

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text("💰 <b>Deduct/Reset ALL</b>\n\nAmount:\n<i>Manual added safe rahenge</i>",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_confirm(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): await state.clear(); return
    try:
        a = int(msg.text.strip())
        if a < 0: raise ValueError
    except: await msg.answer("❌ Valid:"); return
    await state.update_data(amt=a)
    ck = InlineKeyboardMarkup(inline_keyboard=[[
        btn("✅ YES", "owner:deduct_all_yes", EMOJI_CHECK, "✅"),
        btn("❌ NO", "owner:home", EMOJI_CROSS, "❌")]])
    await msg.answer(f"⚠️ <b>CONFIRM</b>\n\nSabhi users se <b>{a}</b> credits deduct?", reply_markup=ck, parse_mode="HTML")

@R.callback_query(F.data == "owner:deduct_all_yes")
async def owner_deduct_all_yes(cq, state):
    d = load(); uid = cq.from_user.id
    if not is_owner(uid, d): await cq.answer("🚫"); return
    data = await state.get_data(); a = data.get("deduct_all_amount", 0)
    await state.clear()
    users = d.get("users", {})
    if not users: await cq.message.edit_text("❌ No users!"); return
    cnt = 0; td = 0
    owners = d.get("owners", [MAIN_OWNER]); admins = d.get("admins", [])
    for uid_str, ud in users.items():
        u = int(uid_str)
        if u in owners or u in admins: continue
        cur = ud.get("credits", 0); man = ud.get("manual_added_credits", 0)
        pool = max(0, cur - man)
        if pool > 0:
            ded = min(a, pool)
            if ded > 0:
                ud["credits"] = cur - ded; cnt += 1; td += ded
    save(d)
    await cq.message.edit_text(f"✅ <b>Deducted!</b>\n💰 Amount: <b>{a}</b>\n👥 Users: <b>{cnt}</b>\n💳 Total: <b>{td}</b>\n🛡 Manual Safe",
                               reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")
    log_activity(d, "deduct_all_credits", uid, f"Deducted {td} from {cnt}")

# ========== USER TRANSFER ==========
@R.callback_query(F.data == "user:transfer")
async def user_transfer(cq, state):
    await _user_transfer_start(cq.message, state)
    try: await cq.message.delete()
    except: pass
    await cq.answer()

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg, state):
    d = load(); uid = msg.from_user.id
    try: tu = int(msg.text.strip())
    except: await msg.answer("❌ Valid ID:"); return
    if tu == uid: await msg.answer("❌ Self transfer nahi!"); return
    if str(tu) not in d.get("users", {}): await msg.answer("❌ User not found!"); return
    c = get_user_credits(uid, d)
    if c < 2: await msg.answer("❌ Min 2 credits!"); return
    await state.update_data(transfer_target=tu)
    await state.set_state(S.transfer_credits_amount)
    h = c // 2
    await msg.answer(f"💸 <b>Step 2/2</b>\n\n👤 To: <code>{tu}</code>\n💰 Your: <b>{c}</b>\n📤 Max (Half): <b>{h}</b>\n\nAmount:",
                     reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

@R.message(S.transfer_credits_amount)
async def user_transfer_amt(msg, state):
    d = load(); uid = msg.from_user.id
    try:
        a = int(msg.text.strip())
        if a <= 0: raise ValueError
    except: await msg.answer("❌ Valid:"); return
    fsmd = await state.get_data(); tu = fsmd.get("transfer_target")
    c = get_user_credits(uid, d); mx = c // 2
    if a > mx: await msg.answer(f"❌ Max {mx}!"); return
    if not deduct_credits(uid, a, d): await msg.answer("❌ Insufficient!"); return
    add_credits(tu, a, d); save(d); await state.clear()
    try:
        await msg.bot.send_message(tu, f"💸 <b>Credits Received!</b>\n\n👤 From: <code>{uid}</code>\n💰 +{a}\n💳 Balance: <b>{get_user_credits(tu, d)}</b>", parse_mode="HTML")
    except: pass
    await msg.answer(f"✅ <b>Transfer Success!</b>\n\n👤 To: <code>{tu}</code>\n💰 {a}\n💳 Your: <b>{get_user_credits(uid, d)}</b>",
                     reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML")
    log_activity(d, "credit_transfer", uid, f"{a} to {tu}")

# ========== OWNER HOME / FIREBASE / OWNERS / ADMINS ==========
@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq, state):
    await state.clear(); d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫", show_alert=True); return
    try: await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest: pass

@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.clear()
    parts = cq.data.split(":"); page = int(parts[3]) if len(parts) > 3 else 0
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b>",
                               reply_markup=fb_menu_kb(d, page), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase</b>\n\n<i>Label | URL</i>",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]), parse_mode="HTML")

@R.message(S.add_firebase)
async def owner_fb_add_done(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_owner(uid, d): await state.clear(); return
    t = msg.text.strip()
    if "|" in t:
        p = t.split("|", 1); label = p[0].strip(); url = p[1].strip()
    else: url = t; label = url.replace("https://","").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer("❌ URL https:// se start:"); return
    url = url.rstrip("/")
    if is_leaked_fb(url):
        await state.clear()
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} <b>Ye Firebase blocked hai!</b>\nLeaked nahi add hogi.",
                         reply_markup=fb_menu_kb(d), parse_mode="HTML"); return
    fbs = d.get("firebases", [])
    if any(f["url"] == url for f in fbs):
        await state.clear(); await msg.answer("⚠️ Already added!", reply_markup=fb_menu_kb(d)); return
    fbs.append({"id": str(int(time.time())), "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs; save(d); await state.clear()
    await msg.answer(f"✅ <b>Added!</b>\n🏷 {label}\n🔗 <code>{url}</code>", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_file(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text("🔥 <b>Bulk Add via TXT</b>\n\n.txt file bhejo (leaked block honge):",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]), parse_mode="HTML")

@R.message(S.add_firebase_file, F.document)
async def owner_fb_file_done(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    doc = msg.document
    if not doc.file_name.endswith('.txt'):
        await msg.answer("❌ Sirf .txt:"); return
    fi = await msg.bot.get_file(doc.file_id)
    df = await msg.bot.download_file(fi.file_path)
    content = df.read().decode('utf-8', errors='ignore')
    fbs = d.get("firebases", []); ex = {f["url"].rstrip("/") for f in fbs}
    added = 0; skip = 0; block = 0; proc = set()
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if "|" in line:
            p = line.split("|", 1); label = p[0].strip(); url = p[1].strip()
        else: url = line; label = url.replace("https://","").replace("http://","").split(".")[0][:20]
        if not (url.startswith("http://") or url.startswith("https://")): continue
        url = url.rstrip("/")
        if is_leaked_fb(url): block += 1; continue
        if url in ex or url in proc: skip += 1; continue
        proc.add(url); ex.add(url)
        fbs.append({"id": str(int(time.time()*1000)+random.randint(100,999)), "url": url, "label": label, "added_at": int(time.time())})
        added += 1
    d["firebases"] = fbs; save(d); await state.clear()
    await msg.answer(f"✅ <b>TXT Done!</b>\n🔥 Added: <b>{added}</b>\n⚠️ Skipped: <b>{skip}</b>\n🚫 Blocked: <b>{block}</b>\n📊 Total: <b>{len(fbs)}</b>",
                     reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.message(S.add_firebase_file)
async def owner_fb_file_bad(msg): await msg.answer("❌ .txt file bhejo!")

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    parts = cq.data.split(":"); fid = parts[3]; page = int(parts[4]) if len(parts) > 4 else 0
    d["firebases"] = [f for f in d["firebases"] if f["id"] != fid]; save(d)
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [x for x in CACHED_DEVICES if x.get("fb_id") != fid]
    FB_DEVICE_COUNTS.pop(fid, None)
    await cq.answer("🗑 Removed!")
    d = load()
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase</b>\n\nTotal: <b>{len(d['firebases'])}</b>",
                               reply_markup=fb_menu_kb(d, page), parse_mode="HTML")

@R.callback_query(F.data == "owner:stats")
async def owner_stats(cq, state):
    await state.clear(); d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await cq.answer("⏳")
    cur = {f["id"] for f in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [x for x in CACHED_DEVICES if x.get("fb_id") in cur]
    for k in [k for k in FB_DEVICE_COUNTS if k not in cur]: FB_DEVICE_COUNTS.pop(k, None)
    devs = get_cached_devices() or await get_all_online_devices(d)
    st = api_stats_text(d)
    dl = [f"\n{em(EMOJI_CHECK, '🟢')} <b>Devices ({len(devs)})</b>\n"]
    if not devs: dl.append("  😴 None")
    for dv in devs:
        dl.append(f"  📱 <b>{dv['dev_name'][:20]}</b>\n     🔥 {dv['fb_label'][:25]}\n     📶 SIMs: {len(dv['sims']) or 1}")
    full = st + "\n" + "\n".join(dl)
    if len(full) > 4000: full = full[:3990] + "\n<i>...truncated</i>"
    await cq.message.edit_text(full, reply_markup=kb([(f"{sc('refresh')}", "owner:stats"), (f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>\n\nTotal: <b>{len(d.get('owners', []))}/6</b>",
                               reply_markup=owners_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    if len(d.get("owners", [])) >= 6: await cq.answer("❌ Max 6!"); return
    await state.set_state(S.add_owner)
    await cq.message.edit_text("👑 <b>Add Super Admin</b>\n\nChat ID:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:owners:menu")]), parse_mode="HTML")

@R.message(S.add_owner)
async def owner_owners_add_done(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try: nid = int(msg.text.strip())
    except: await msg.answer("❌ Valid ID:"); return
    if is_owner(nid, d): await state.clear(); await msg.answer("⚠️ Already!", reply_markup=owners_menu_kb(d)); return
    if len(d.get("owners", [])) >= 6: await state.clear(); await msg.answer("❌ Max 6!"); return
    d["owners"].append(nid); save(d); await state.clear()
    await msg.answer(f"✅ <b>Super Admin Added!</b>\n<code>{nid}</code>", reply_markup=owners_menu_kb(load()), parse_mode="HTML")
    try: await msg.bot.send_message(nid, "🔱 Aapko Super Admin banaya gaya! /start karein.")
    except: pass

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq, state):
    d = load(); uid = cq.from_user.id
    did = int(cq.data.split("owner:owners:del:", 1)[1])
    if not is_owner(uid, d): await cq.answer("🚫"); return
    if did == MAIN_OWNER or did in SUPER_ADMINS: await cq.answer("❌ Hardcoded!", show_alert=True); return
    if did in d["owners"]: d["owners"].remove(did); save(d); await cq.answer("🗑")
    await cq.message.edit_text(f"👑 <b>Owners</b>\n\nTotal: <b>{len(d['owners'])}/6</b>", reply_markup=owners_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>\n\nTotal: <b>{len(d.get('admins', []))}</b>",
                               reply_markup=admins_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.add_admin)
    await cq.message.edit_text("🛡 <b>Add Admin</b>\n\nUser ID:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:admins:menu")]), parse_mode="HTML")

@R.message(S.add_admin)
async def owner_admins_add_done(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try: nid = int(msg.text.strip())
    except: await msg.answer("❌ Valid ID:"); return
    if nid in d.get("admins", []) or is_owner(nid, d):
        await state.clear(); await msg.answer("⚠️ Already!", reply_markup=admins_menu_kb(d)); return
    d["admins"].append(nid); save(d); await state.clear()
    await msg.answer(f"✅ <b>Admin Added!</b>\n<code>{nid}</code>", reply_markup=admins_menu_kb(load()), parse_mode="HTML")
    try: await msg.bot.send_message(nid, "🛡 Aapko Admin banaya gaya! /start karein.")
    except: pass

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq, state):
    d = load(); uid = cq.from_user.id
    did = int(cq.data.split("owner:admins:del:", 1)[1])
    if not is_owner(uid, d): await cq.answer("🚫"); return
    if did in DEFAULT_ADMINS: await cq.answer("❌ Hardcoded admin!", show_alert=True); return
    if did in d.get("admins", []): d["admins"].remove(did); save(d); await cq.answer("🗑")
    await cq.message.edit_text(f"🛡 <b>Admins</b>\n\nTotal: <b>{len(d['admins'])}</b>", reply_markup=admins_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free(cq, state):
    await state.clear(); d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    d["free_mode"] = (cq.data == "owner:free:on"); save(d); d = load()
    await cq.answer(f"{'🟢 FREE ON' if d['free_mode'] else '🔴 Approval'}", show_alert=True)
    try: await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest: pass

@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users(cq, state):
    d = load(); uid = cq.from_user.id
    prefix = "owner" if is_owner(uid, d) else "admin"
    if not is_admin(uid, d): await cq.answer("🚫"); return
    t, m = users_list_kb(d, prefix, 0)
    await cq.message.edit_text(t, reply_markup=m, parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_pg(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    parts = cq.data.split(":"); prefix = parts[0]; page = int(parts[3])
    t, m = users_list_kb(d, prefix, page)
    await cq.message.edit_text(t, reply_markup=m, parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text("🚫 <b>Ban User</b>\n\nUser ID:", reply_markup=kb([(f"{sc('cancel')}", back)]), parse_mode="HTML")

@R.message(S.ban_user)
async def panel_ban_done(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d): await state.clear(); return
    try: bid = int(msg.text.strip())
    except: await msg.answer("❌ Valid ID:"); return
    if is_owner(bid, d) or is_admin(bid, d):
        await state.clear(); await msg.answer("❌ Admin/Owner ban nahi!"); return
    if bid not in d.get("banned", []): d.setdefault("banned", []).append(bid); save(d)
    await state.clear()
    await msg.answer(f"🚫 <b>Banned!</b>\n<code>{bid}</code>",
                     reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d), parse_mode="HTML")
    try: await msg.bot.send_message(bid, "🚫 Aapko ban kar diya gaya.")
    except: pass

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    b = d.get("banned", [])
    if not b: await cq.answer("✅ No banned!"); return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    await cq.message.edit_text(f"🔓 <b>Unban</b>\n\nBanned: <b>{len(b)}</b>", reply_markup=unban_menu_kb(d, prefix), parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban(cq, state):
    d = load(); uid = cq.from_user.id
    if not is_admin(uid, d): await cq.answer("🚫"); return
    bid = int(cq.data.split(":")[-1])
    if bid in d.get("banned", []): d["banned"].remove(bid); save(d)
    await cq.answer(f"✅ {bid} unbanned!", show_alert=True)
    await cq.message.edit_text(owner_panel_text(d) if is_owner(uid, d) else admin_panel_text(d),
                               reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d), parse_mode="HTML")
    try: await cq.bot.send_message(bid, "✅ Unban! /start karein.")
    except: pass

@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_bc(cq, state):
    d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text("📢 <b>Broadcast</b>\n\nMessage type karo:", reply_markup=kb([(f"{sc('cancel')}", back)]), parse_mode="HTML")

@R.message(S.broadcast)
async def panel_bc_do(msg, state):
    d = load(); uid = msg.from_user.id
    if not is_admin(uid, d): await state.clear(); return
    await state.clear()
    users = d.get("users", {})
    w = await msg.answer(f"📤 Broadcasting to {len(users)}...")
    ok = 0; fl = 0
    for uid_str in users:
        try:
            t = int(uid_str)
            if msg.text: await msg.bot.send_message(t, f"📢 <b>Broadcast</b>\n\n{msg.text}", parse_mode="HTML")
            else: await msg.copy_to(t)
            ok += 1
        except: fl += 1
        await asyncio.sleep(0.05)
    try: await w.delete()
    except: pass
    await msg.answer(f"✅ <b>Broadcast Done!</b>\n✅ {ok}\n❌ {fl}",
                     reply_markup=owner_kb(d) if is_owner(uid, d) else admin_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:export_script")
async def owner_export(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await cq.answer("📤 Exporting...")
    try:
        sp = os.path.abspath(__file__)
        if not os.path.exists(sp):
            sp = _DATA_FILE.replace(".json", ".py")
            if not os.path.exists(sp): sp = "prime_x_bomber.py"
        await cq.message.reply_document(FSInputFile(sp),
            caption=f"📤 <b>Prime x Bomber Script</b> — <i>{_VERSION}</i>", parse_mode="HTML")
    except Exception as e: await cq.answer(f"❌ {str(e)[:40]}", show_alert=True)

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq, state):
    await state.clear(); d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    try: await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest: pass

@R.callback_query(F.data == "admin:stats")
async def admin_stats(cq, state):
    await state.clear(); d = load()
    if not is_admin(cq.from_user.id, d): await cq.answer("🚫"); return
    await cq.answer("⏳")
    cur = {f["id"] for f in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [x for x in CACHED_DEVICES if x.get("fb_id") in cur]
    for k in [k for k in FB_DEVICE_COUNTS if k not in cur]: FB_DEVICE_COUNTS.pop(k, None)
    devs = get_cached_devices() or await get_all_online_devices(d)
    st = api_stats_text(d)
    dl = [f"\n{em(EMOJI_CHECK, '🟢')} <b>Devices ({len(devs)})</b>\n"]
    if not devs: dl.append("  😴 None")
    for dv in devs: dl.append(f"  📱 <b>{dv['dev_name'][:20]}</b> — 🔥 {dv['fb_label'][:20]}")
    full = st + "\n" + "\n".join(dl)
    if len(full) > 4000: full = full[:3990] + "\n<i>...truncated</i>"
    await cq.message.edit_text(full, reply_markup=kb([(f"{sc('refresh')}", "admin:stats"), (f"{sc('back')}", "admin:home")]), parse_mode="HTML")

# ========== FORCE JOIN ==========
@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    fj = d.get("force_join", {}); chs = fj.get("channels", [])
    s = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    t = f"🔗 <b>Force Join</b>\n\nStatus: {s}\nChannels: <b>{len(chs)}</b>\n\n"
    for ch in chs:
        r = "✅" if ch.get("required", True) else "❌"
        t += f"• {ch.get('title','Channel')} (<code>{ch['id']}</code>)\n  {r} | {ch['link']}\n\n"
    rows = [[btn("ᴀᴅᴅ", "owner:fj:add", EMOJI_CHECK, "➕")],
            [btn("ʀᴇᴍᴏᴠᴇ", "owner:fj:remove", EMOJI_CROSS, "🗑")],
            [InlineKeyboardButton(text=f"🟢 {sc('enable')}" if not fj.get("enabled") else f"🔴 {sc('disable')}", callback_data="owner:fj:toggle")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]]
    await cq.message.edit_text(t, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text("🔗 <b>Step 1/2</b>\n\nChannel ID (e.g. -100123):",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:fj:menu")]), parse_mode="HTML")

@R.message(S.fj_add_channel)
async def owner_fj_ch(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try: ch = int(msg.text.strip())
    except: await msg.answer("❌ Valid ID:"); return
    await state.update_data(fj_channel_id=ch)
    await state.set_state(S.fj_add_link)
    await msg.answer("🔗 <b>Step 2/2</b>\n\nInvite link:", reply_markup=kb([(f"{sc('cancel')}", "owner:fj:menu")]), parse_mode="HTML")

@R.message(S.fj_add_link)
async def owner_fj_link(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    link = msg.text.strip()
    if not link.startswith("http"): await msg.answer("❌ https:// se:"); return
    fsmd = await state.get_data(); ch = str(fsmd.get("fj_channel_id"))
    try:
        c = await msg.bot.get_chat(int(ch)); title = c.title or "Channel"
    except: title = "Channel"
    chs = d.setdefault("force_join", {}).setdefault("channels", [])
    chs = [x for x in chs if str(x["id"]) != ch]
    chs.append({"id": ch, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = chs; save(d); await state.clear()
    await msg.answer(f"✅ <b>Added!</b>\n📢 {title}\n🔗 {link}", reply_markup=kb([(f"{sc('back')}", "owner:fj:menu")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_rem(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    chs = d.get("force_join", {}).get("channels", [])
    if not chs: await cq.answer("❌ Koi nahi!"); return
    rows = [[btn(f"{c.get('title','Channel')[:25]}", f"owner:fj:del:{c['id']}", EMOJI_CROSS, "🗑")] for c in chs]
    rows.append([btn("ʙᴀᴄᴋ", "owner:fj:menu", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text("🗑 Remove?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    cid = cq.data.split("owner:fj:del:", 1)[1]
    chs = d.get("force_join", {}).get("channels", [])
    d["force_join"]["channels"] = [c for c in chs if str(c["id"]) != cid]
    save(d); await cq.answer("🗑")
    await owner_fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_tog(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False); save(d)
    await cq.answer(f"FJ {'ENABLED' if fj['enabled'] else 'DISABLED'}!", show_alert=True)
    await owner_fj_menu(cq, state)

# ========== PRICING / REDEEM / CREDITS ==========
@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    plans = d.get("pricing", {}).get("plans", [])
    t = f"💳 <b>Plans</b>\n\nTotal: <b>{len(plans)}</b>\n\n"
    for i, p in enumerate(plans, 1):
        t += f"{i}. <b>{p['name']}</b>\n   💰 {p['price']} {p.get('currency','INR')} = {p['credits']}\n   🔗 {p['payment_link']}\n\n"
    rows = [[btn("ᴀᴅᴅ", "owner:pricing:add", EMOJI_CHECK, "➕")],
            [btn("ʀᴇᴍᴏᴠᴇ", "owner:pricing:remove", EMOJI_CROSS, "🗑")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]]
    await cq.message.edit_text(t, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:add")
async def owner_plan_add(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text("💳 <b>Step 1/4</b>\n\nPlan name:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]), parse_mode="HTML")

@R.message(S.add_plan_name)
async def owner_plan_name(msg, state):
    if not is_owner(msg.from_user.id, load()): await state.clear(); return
    await state.update_data(plan_name=msg.text.strip())
    await state.set_state(S.add_plan_price)
    await msg.answer("💳 <b>Step 2/4</b>\n\nPrice:", reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]), parse_mode="HTML")

@R.message(S.add_plan_price)
async def owner_plan_price(msg, state):
    if not is_owner(msg.from_user.id, load()): await state.clear(); return
    try: p = float(msg.text.strip())
    except: await msg.answer("❌ Valid:"); return
    await state.update_data(plan_price=p)
    await state.set_state(S.add_plan_credits)
    await msg.answer("💳 <b>Step 3/4</b>\n\nCredits:", reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]), parse_mode="HTML")

@R.message(S.add_plan_credits)
async def owner_plan_credits(msg, state):
    if not is_owner(msg.from_user.id, load()): await state.clear(); return
    try: c = int(msg.text.strip())
    except: await msg.answer("❌:"); return
    await state.update_data(plan_credits=c)
    await state.set_state(S.add_plan_link)
    await msg.answer(f"💳 <b>Step 4/4</b>\n\nPayment link:", reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]), parse_mode="HTML")

@R.message(S.add_plan_link)
async def owner_plan_link(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    lk = msg.text.strip()
    if not lk.startswith("http"): await msg.answer("❌ https://:"); return
    fsmd = await state.get_data()
    plan = {"id": str(int(time.time())), "name": fsmd.get("plan_name","Plan"),
            "price": fsmd.get("plan_price", 0), "credits": fsmd.get("plan_credits", 0),
            "currency": "INR", "payment_link": lk}
    d.setdefault("pricing", {}).setdefault("plans", []).append(plan)
    save(d); await state.clear()
    await msg.answer(f"✅ <b>Plan Added!</b>\n📋 {plan['name']}\n💰 {plan['price']} = {plan['credits']}\n🔗 {plan['payment_link']}",
                     reply_markup=kb([(f"{sc('back')}", "owner:pricing:menu")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:remove")
async def owner_plan_rem(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    plans = d.get("pricing", {}).get("plans", [])
    if not plans: await cq.answer("❌ No plans!"); return
    rows = [[btn(f"{p['name'][:25]}", f"owner:pricing:del:{p['id']}", EMOJI_CROSS, "🗑")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "owner:pricing:menu", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text("🗑 Remove?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_plan_del(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    pid = cq.data.split("owner:pricing:del:", 1)[1]
    d["pricing"]["plans"] = [p for p in d.get("pricing", {}).get("plans", []) if p["id"] != pid]
    save(d); await cq.answer("🗑"); await owner_pricing(cq, state)

@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    codes = d.get("redeem_codes", {})
    t = f"🎁 <b>Redeem Codes</b>\n\nTotal: <b>{len(codes)}</b>\n\n"
    for c, data in list(codes.items())[:10]:
        s = "✅" if data.get("uses_left", 0) > 0 else "❌"
        t += f"<code>{c}</code> — 💰{data['credits']} — {s} ({data.get('uses_left',0)})\n"
    rows = [[btn("ɢᴇɴᴇʀᴀᴛᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕")],
            [btn("ᴅᴇʟᴇᴛᴇ", "owner:redeem:del", EMOJI_CROSS, "🗑")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]]
    await cq.message.edit_text(t, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text("🎁 <b>Step 1/2</b>\n\nCredits:",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:redeem:menu")]), parse_mode="HTML")

@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg, state):
    if not is_owner(msg.from_user.id, load()): await state.clear(); return
    try: c = int(msg.text.strip())
    except: await msg.answer("❌:"); return
    await state.update_data(gen_credits=c); await state.set_state(S.gen_redeem_uses)
    await msg.answer("🎁 <b>Step 2/2</b>\n\nMax uses:", reply_markup=kb([(f"{sc('cancel')}", "owner:redeem:menu")]), parse_mode="HTML")

@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try:
        u = int(msg.text.strip())
        if u < 1: raise ValueError
    except: await msg.answer("❌:"); return
    fsmd = await state.get_data(); c = fsmd.get("gen_credits", 10)
    while True:
        code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in d.get("redeem_codes", {}): break
    d.setdefault("redeem_codes", {})[code] = {"credits": c, "uses_left": u, "created_by": msg.from_user.id,
                                               "created_at": int(time.time()), "used_by": []}
    save(d); await state.clear()
    await msg.answer(f"🎉 <b>Code Generated!</b>\n\n🎁 <code>{code}</code>\n💰 {c}\n🔢 {u}",
                     reply_markup=kb([(f"{sc('back')}", "owner:redeem:menu")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    codes = d.get("redeem_codes", {})
    if not codes: await cq.answer("❌ None!"); return
    rows = [[btn(c, f"owner:redeem:deldo:{c}", EMOJI_CROSS, "🗑")] for c in list(codes.keys())[:20]]
    rows.append([btn("ʙᴀᴄᴋ", "owner:redeem:menu", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text("🗑 Delete?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_deldo(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    c = cq.data.split("owner:redeem:deldo:", 1)[1]
    if c in d.get("redeem_codes", {}): del d["redeem_codes"][c]; save(d)
    await cq.answer("🗑"); await owner_redeem(cq, state)

@R.callback_query(F.data == "owner:credits:add")
async def owner_add_credit(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text("💰 <b>Add Credits</b>\n\nUser ID:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.add_credits_uid)
async def owner_add_credit_uid(msg, state):
    if not is_owner(msg.from_user.id, load()): await state.clear(); return
    try: u = int(msg.text.strip())
    except: await msg.answer("❌:"); return
    await state.update_data(credit_uid=u); await state.set_state(S.add_credits_amount)
    await msg.answer("💰 <b>Step 2/2</b>\n\nAmount:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.add_credits_amount)
async def owner_add_credit_amt(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try: a = int(msg.text.strip())
    except: await msg.answer("❌:"); return
    fsmd = await state.get_data(); u = fsmd.get("credit_uid")
    add_credits(u, a, d, is_manual=True); save(d); await state.clear()
    try: await msg.bot.send_message(u, f"💰 <b>Credits Added!</b>\n+{a}\n💳 Balance: <b>{get_user_credits(u, d)}</b>", parse_mode="HTML")
    except: pass
    await msg.answer(f"✅ <b>{a} credits</b> → <code>{u}</code>\n💳 {get_user_credits(u, d)}",
                     reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_ded_credit(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text("💰 <b>Deduct Credits</b>\n\nUser ID:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.deduct_credits_uid)
async def owner_ded_uid(msg, state):
    if not is_owner(msg.from_user.id, load()): await state.clear(); return
    try: u = int(msg.text.strip())
    except: await msg.answer("❌:"); return
    await state.update_data(deduct_uid=u); await state.set_state(S.deduct_credits_amount)
    await msg.answer("💰 <b>Step 2/2</b>\n\nAmount:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.deduct_credits_amount)
async def owner_ded_amt(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try: a = int(msg.text.strip())
    except: await msg.answer("❌:"); return
    fsmd = await state.get_data(); u = fsmd.get("deduct_uid")
    ok = deduct_credits(u, a, d); save(d); await state.clear()
    if ok:
        try: await msg.bot.send_message(u, f"⚠️ <b>Credits Deducted!</b>\n-{a}\n💳 {get_user_credits(u, d)}", parse_mode="HTML")
        except: pass
        await msg.answer(f"✅ <b>-{a}</b> from <code>{u}</code>\n💳 {get_user_credits(u, d)}",
                         reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")
    else:
        await msg.answer(f"❌ Insufficient! User has {get_user_credits(u, d)}",
                         reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    s = d.get("settings", {})
    t = (f"⚙️ <b>Settings</b>\n\n🎁 Referral: <b>{s.get('ref_credits', 3)}</b>\n"
         f"👑 Max Owners: <b>{s.get('max_owners', 6)}</b>")
    rows = [[btn("sᴇᴛ ʀᴇғ ᴄʀᴇᴅɪᴛs", "owner:settings:ref", EMOJI_GIFT, "🎁")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")]]
    await cq.message.edit_text(t, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:settings:ref")
async def owner_set_ref(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text("🎁 <b>Referral Credits</b>\n\nKitne?",
                               reply_markup=kb([(f"{sc('cancel')}", "owner:settings")]), parse_mode="HTML")

@R.message(S.set_ref_credits)
async def owner_set_ref_done(msg, state):
    d = load()
    if not is_owner(msg.from_user.id, d): await state.clear(); return
    try:
        c = int(msg.text.strip())
        if c < 0: raise ValueError
    except: await msg.answer("❌:"); return
    d.setdefault("settings", {})["ref_credits"] = c
    d["premium"]["ref_credits"] = c; save(d); await state.clear()
    await msg.answer(f"✅ <b>Updated!</b> Ab {c} credits/referral.", reply_markup=kb([(f"{sc('back')}", "owner:settings")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:activity")
async def owner_activity(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    e = d.get("activity_log", [])[-20:]
    if not e: t = "📜 <i>No activity.</i>"
    else:
        lines = ["📜 <b>Activity Log</b>\n"]
        for x in reversed(e): lines.append(f"[{fmt_time(x.get('timestamp',0))}] <code>{x.get('uid',0)}</code> — {x.get('action','?')} — {x.get('details','')}")
        t = "\n".join(lines)
    await cq.message.edit_text(t, reply_markup=kb([(f"{sc('refresh')}", "owner:activity"), (f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_hist(cq, state):
    d = load()
    if not is_owner(cq.from_user.id, d): await cq.answer("🚫"); return
    ah = d.get("sms_history", {}); t = sum(len(v) for v in ah.values())
    await cq.message.edit_text(f"📋 <b>Global SMS History</b>\n\nTotal: <b>{t}</b>", reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

# ========== USER HOME / CREDITS / REDEEM / REFER / STATS / PRICING / INFO ==========
@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq, state):
    await state.clear(); d = load(); uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True); return
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"); return
    if is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML"); return
    if not can_use(uid, d):
        await cq.message.edit_text("⛔ Access nahi!"); return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:credits")
async def user_credits(cq, state):
    d = load(); await cq.answer(f"💰 Credits: {get_user_credits(cq.from_user.id, d)}\nOwner: {SUPER_ADMIN_NAME}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem(cq, state):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text("🎁 <b>Redeem Code</b>\n\nCode:", reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

@R.message(S.redeem_code)
async def user_redeem_done(msg, state):
    d = load(); uid = msg.from_user.id
    code = msg.text.strip().upper(); await state.clear()
    codes = d.get("redeem_codes", {})
    if code not in codes:
        await msg.answer("❌ Invalid!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML"); return
    cd = codes[code]
    if cd.get("uses_left", 0) <= 0:
        await msg.answer("❌ Expired!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML"); return
    if uid in cd.get("used_by", []):
        await msg.answer("❌ Already used!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML"); return
    c = cd["credits"]; add_credits(uid, c, d)
    cd["uses_left"] = cd.get("uses_left", 1) - 1
    cd.setdefault("used_by", []).append(uid); save(d)
    await msg.answer(f"🎉 <b>Redeemed!</b>\n💰 +{c}\n💳 {get_user_credits(uid, d)}",
                     reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML")

@R.callback_query(F.data == "user:refer")
async def user_refer(cq, state):
    d = load(); uid = cq.from_user.id
    code = generate_user_refer_code(uid, d); save(d)
    rc = d.get("settings", {}).get("ref_credits", 3)
    me = await cq.bot.get_me()
    await cq.message.edit_text(f"👥 <b>Referral</b>\n\n🎁 Code: <code>{code}</code>\n🔗 https://t.me/{me.username}?start={code}\n\n{rc} credits/referral!",
                               reply_markup=kb([(f"{sc('back')}", "user:home")]), parse_mode="HTML")

@R.callback_query(F.data == "user:stats")
async def user_stats(cq, state):
    d = load(); uid = cq.from_user.id
    ud = d["users"].get(str(uid), {}); st = d.get("stats", {})
    await cq.message.edit_text(f"📊 <b>Your Stats</b>\n\n💰 {ud.get('credits', 0)}\n📤 {ud.get('uses', 0)}\n📅 {fmt_time(ud.get('joined_at', 0))}\n\n📈 Bot Total: {st.get('total_sent', 0)}",
                               reply_markup=kb([(f"{sc('back')}", "user:home")]), parse_mode="HTML")

@R.callback_query(F.data == "user:sms_history")
async def user_sms_hist(cq, state):
    d = load(); uid = cq.from_user.id
    h = d.get("sms_history", {}).get(str(uid), [])[-10:]
    if not h: t = "📜 <i>No history.</i>"
    else:
        lines = ["📜 <b>Your SMS History</b>\n"]
        for i, e in enumerate(reversed(h), 1):
            si = "✅" if e.get("status")=="sent" else "🛑" if e.get("status")=="stopped" else "⏳"
            lines.append(f"{i}. [{fmt_time(e.get('timestamp',0))}] {si} <code>{mask_number(e.get('number','?'))}</code>")
        t = "\n".join(lines)
    await cq.message.edit_text(t, reply_markup=kb([(f"{sc('back')}", "user:home")]), parse_mode="HTML")

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq, state):
    d = load(); plans = d.get("pricing", {}).get("plans", [])
    if not plans: await cq.answer("❌ No plans!", show_alert=True); return
    t = "💰 <b>Buy Credits</b>\n\n"
    for p in plans:
        t += f"📋 <b>{p['name']}</b>\n   💰 {p['price']} {p.get('currency','INR')}\n   🎁 {p['credits']} credits\n\n"
    rows = [[btn_url(f"Buy {sc(p['name'][:20])}", p['payment_link'], EMOJI_MONEY, "💳")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(t, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "user:info")
async def user_info(cq, state):
    await cq.message.edit_text(f"ℹ️ <b>Prime x Bomber {_VERSION}</b>\n\n🤖 Bulk SMS via Firebase\n\n👤 <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>",
                               reply_markup=kb([(f"{sc('back')}", "user:home")]), parse_mode="HTML", disable_web_page_preview=True)

@R.callback_query(F.data == "noop")
async def noop(cq): await cq.answer()

@R.callback_query(F.data == "fj:check")
async def fj_check(cq, state):
    uid = cq.from_user.id; d = load()
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("❌ Abhi bhi join nahi!", show_alert=True)
        try: await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        except: pass
        return
    await cq.answer("✅ Verified!", show_alert=True)
    await send_random_video(cq.bot, cq.message.chat.id, "🚀 Welcome!")
    if is_owner(uid, d): await cq.message.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d): await cq.message.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else: await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.message(Command("logs"))
async def cmd_logs(msg, state):
    await state.clear(); uid = msg.from_user.id; d = load()
    if not is_owner(uid, d): await msg.answer("❌ Owner only!"); return
    log_lines = ["="*60, "  PRIME X BOMBER - LOG EXPORT", f"  By: {uid} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "="*60, ""]
    log_lines.append(f"[VERSION] {_VERSION}")
    log_lines.append(f"[OWNER] {MAIN_OWNER} | {SUPER_ADMIN_NAME}")
    log_lines.append(f"[OWNERS] {d.get('owners', [])}")
    log_lines.append(f"[ADMINS] {d.get('admins', [])}")
    log_lines.append(f"[BANNED] {d.get('banned', [])}")
    log_lines.append(f"[FBS] {len(d.get('firebases', []))}")
    for fb in d.get("firebases", []): log_lines.append(f"  {fb.get('label')} | {fb['url']}")
    log_lines.append(f"[USERS] {len(d.get('users', {}))}")
    for u, ud in d.get("users", {}).items():
        log_lines.append(f"  {u} | {ud.get('name','?')} | C:{ud.get('credits',0)} | U:{ud.get('uses',0)}")
    log_lines.append(f"[STATS] Sent:{d.get('stats',{}).get('total_sent',0)} Failed:{d.get('stats',{}).get('total_failed',0)}")
    log_lines.append(f"[PROTECTED] {len(d.get('protected_numbers',{}))}")
    log_lines.append(f"[CODES] {len(d.get('redeem_codes',{}))}")
    log_lines.append(f"[VIDEOS] {len(d.get('videos',[]))}")
    log_lines.append("="*60)
    text = "\n".join(log_lines)
    from aiogram.types import BufferedInputFile
    fb = io.BytesIO(text.encode("utf-8"))
    await msg.answer_document(document=BufferedInputFile(fb.getvalue(), filename=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
                               caption=f"📜 <b>Logs</b> — {_VERSION}", parse_mode="HTML")

# ========== MAIN (FIXED) ==========
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"@{me.username} — PRIME X BOMBER {_VERSION} started!")

    scanner = asyncio.create_task(background_firebase_scanner(bot))
    backup = asyncio.create_task(background_backup_sender(bot))
    log.info("Background tasks created")

    # ✅ Notification ko background task banao (await mat karo)
    async def notify_owner():
        try:
            await bot.send_message(MAIN_OWNER,
                f"🚀 <b>PRIME X BOMBER {_VERSION} ONLINE!</b>\n@{me.username}\n"
                f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
                f"🔄 <b>Background Scanner:</b> Active\n"
                f"📦 <b>Auto Backup:</b> 1 Hour\n"
                f"⏱ <b>Scan Interval:</b> 1 minute\n"
                f"👥 <b>Per-User Sessions:</b> ENABLED\n"
                f"🚀 <b>Concurrent:</b> 1000+\n"
                f"🔒 <b>Number Protection:</b> ON\n"
                f"🚫 <b>Leaked Firebase Blocker:</b> ACTIVE\n"
                f"⌨️ <b>Reply Keyboards:</b> ENABLED\n"
                f"👤 <b>Owner:</b> {SUPER_ADMIN_NAME}", parse_mode="HTML")
        except Exception as e:
            log.warning(f"Notify: {e}")

    asyncio.create_task(notify_owner())

    # ✅ Polling pehle start karo
    log.info("Starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())