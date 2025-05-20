import logging
import asyncio
from itertools import islice
from collections import deque

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from AxTask import run_robot_task_to
from AxRobot import RobotManager
from config import config

# ─── CONFIG ────────────────────────────────────────
TELEGRAM_TOKEN = config["telegram_bot_token"]
ROBOT_ID       = "89824116043628m"
robot_manager  = RobotManager(config["token"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── YOUR POIS ──────────────────────────────────────
POI_LIST = [
  {"name": "4D_Robot",            "coordinate": [  4.734035126432445,   -0.33602792868236975], "yaw": 179,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "AMR",                 "coordinate": [ 13.071532590060997,     5.23239284916599], "yaw":  92,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Board room",          "coordinate": [ 19.126824654165375,  -23.160599592984   ], "yaw":  90,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "CBS",                 "coordinate": [ 43.105000000000004,   33.84            ], "yaw":  84,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Cafeteria",           "coordinate": [ -0.605,              -25.485           ], "yaw": 118,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Car Parking(General)", "coordinate": [ 83.53073612369144,    0.0728256561899343], "yaw": 180,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Charging Station",    "coordinate": [  0.028294880667081166,   0.39899799464162183], "yaw": 266,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Charging startion 2", "coordinate": [ 56.8003459398907,   -26.283367735026687], "yaw": 358,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Entrance",            "coordinate": [ 73.12213900291908,   -21.365519944396283], "yaw": 179,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Finance",             "coordinate": [ 24.6425,             -23.527500000000003], "yaw":  91,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Founder Lounge",      "coordinate": [ 33.3525,             -23.015           ], "yaw":  92,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Founders Parking",    "coordinate": [ 82.07673440807639,   -31.450637353032107], "yaw":  92,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "HR Cabin",            "coordinate": [ 53.17259864582943,   -23.01558585419571 ], "yaw":  87,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Ideation",            "coordinate": [  8.2425,             -31.067500000000003], "yaw": 85.37,  "areaId": "67f77a224666c3f79fda5459"},
  {"name": "MB_ROBOT",            "coordinate": [ 32.1,                -6.892500000000001], "yaw":  89,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Main gate",           "coordinate": [107.65222863852841,  -11.346648091858924], "yaw": 192.83, "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Mat Bank",            "coordinate": [ -4.875,               38.56            ], "yaw": 273,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "NPD",                 "coordinate": [  8.47,              -22.525000000000002], "yaw":  91,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Pannel area",         "coordinate": [ 25.53,               31.66            ], "yaw": 185,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Play area",           "coordinate": [  3.76,              -18.44           ], "yaw":  89,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Project",             "coordinate": [ 47.03094220957382,  -22.410705935982378], "yaw":  90,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Reception",           "coordinate": [ 62.205043738356906, -22.5966745423629  ], "yaw": 91.18,  "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Rolling conveyor",    "coordinate": [ 39.61,               -2.0375          ], "yaw":   5,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Shutter",             "coordinate": [ 64.09747092618545,    1.935674457058667], "yaw": 180,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Testing area",        "coordinate": [ 40.44579003561921,    5.71749286962131 ], "yaw":  90,    "areaId": "67f77a224666c3f79fda5459"},
  {"name": "Training hall",       "coordinate": [ 12.255743409355091, -22.738723420161477], "yaw": 90.98,  "areaId": "67f77a224666c3f79fda5459"},
  {"name": "VR",                  "coordinate": [ 41.7875,             -22.5275         ], "yaw":  89,    "areaId": "67f77a224666c3f79fda5459"},
]
POI_MAP = {poi["name"]: poi for poi in POI_LIST}

# ─── QUEUE STATE ────────────────────────────────────
task_queue = deque()
_worker_running = False

# ─── HELPERS ────────────────────────────────────────
def chunked(iterable, n):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            return
        yield chunk

async def async_get_state():
    return await asyncio.to_thread(robot_manager.getRobotState, ROBOT_ID)

async def robot_reached(poi, tol=0.5):
    """Poll until robot is within tol meters of poi."""
    while True:
        success, data = await async_get_state()
        if success and data.get("robotId")==ROBOT_ID:
            x, y = data.get("x"), data.get("y")
            if x is not None and y is not None:
                dx = x - poi["coordinate"][0]
                dy = y - poi["coordinate"][1]
                if (dx*dx+dy*dy)**0.5 <= tol:
                    return True
        await asyncio.sleep(2)

# ─── QUEUE PROCESSOR ─────────────────────────────────
async def _process_queue(context: ContextTypes.DEFAULT_TYPE):
    global _worker_running
    if _worker_running:
        return
    _worker_running = True

    while task_queue:
        poi, chat_id = task_queue.popleft()
        name = poi["name"]

        # 1) dispatch CSP task
        await context.bot.send_message(chat_id,
            f"🚀 Dispatching robot to *{name}*…", parse_mode="Markdown"
        )
        success, result = await asyncio.to_thread(run_robot_task_to, poi)
        if not success:
            await context.bot.send_message(chat_id,
                f"❌ Failed to send *{name}*: {result}", parse_mode="Markdown"
            )
            continue

        # 2) wait for physical arrival
        await context.bot.send_message(chat_id,
            "⏳ Waiting to arrive…", parse_mode="Markdown"
        )
        await robot_reached(poi)

        # 3) confirm completion
        await context.bot.send_message(chat_id,
            f"✅ Arrived at *{name}*! Task ID: `{result}`", parse_mode="Markdown"
        )

    _worker_running = False

# ─── /start HANDLER ─────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cols = 3
    keyboard = [
        [InlineKeyboardButton(p["name"], callback_data=p["name"])
         for p in row]
        for row in chunked(POI_LIST, cols)
    ]
    await update.message.reply_text(
        "📍 Tap to queue destinations:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── POI BUTTON CALLBACK ────────────────────────────
async def on_poi_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    poi_name = query.data
    poi = POI_MAP.get(poi_name)
    chat_id = query.message.chat.id

    if not poi:
        await context.bot.send_message(chat_id, f"❌ Unknown POI: {poi_name}")
        return

    task_queue.append((poi, chat_id))
    pos = len(task_queue)
    await context.bot.send_message(chat_id,
        f"📌 Queued *{poi_name}* at position {pos}", parse_mode="Markdown"
    )

    # kick off processor if idle
    await _process_queue(context)

# ─── BOT SETUP & RUN ───────────────────────────────
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_poi_selected))

    logger.info("🤖 Bot starting with true serial queue…")
    app.run_polling()

if __name__ == "__main__":
    main()
