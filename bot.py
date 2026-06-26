import os
import re
import logging
import threading
import asyncio
from flask import Flask, request, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ========== KONFİQ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
PORT = int(os.environ.get('PORT', 8080))
APP_URL = os.environ.get('RENDER_EXTERNAL_URL', '')

active_attacks = {}  # {ip: {'chat_id': int, 'active': bool}}

# ========== HÜCUM SƏHİFƏSİ ==========
ATTACK_PAGE = '''<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ryhavean Server</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
        }
        .container {
            text-align: center;
            padding: 3rem;
            border: 3px solid #00ff00;
            border-radius: 15px;
            background: rgba(0,255,0,0.03);
            animation: glow 2s infinite;
            max-width: 800px;
        }
        @keyframes glow {
            0% { box-shadow: 0 0 10px #ff0000; }
            50% { box-shadow: 0 0 40px #ff0000, 0 0 80px #ff0000; }
            100% { box-shadow: 0 0 10px #ff0000; }
        }
        h1 {
            font-size: 3rem;
            color: #ff0000;
            text-shadow: 0 0 20px #ff0000, 0 0 40px #ff0000;
            margin-bottom: 2rem;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .ip { color: #ffff00; font-size: 1.5rem; }
        .status { color: #ff4444; margin: 1rem 0; font-size: 1.2rem; }
        .footer { color: #555; margin-top: 3rem; font-size: 0.8rem; }
        .matrix { opacity: 0.2; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                  background: repeating-linear-gradient(0deg, transparent, transparent 2px, #0f0 2px, #0f0 4px);
                  pointer-events: none; z-index: -1; }
    </style>
</head>
<body>
    <div class="matrix"></div>
    <div class="container">
        <h1>⚠ RYHAVEAN SERVER IS ATTACK! ⚠</h1>
        <p>Target IP: <span class="ip">{{ ip }}</span></p>
        <p class="status">>> SYSTEM COMPROMISED <<</p>
        <p>Bu bağlantı müdaxilə edildi.</p>
        <p>Bütün məlumatlarınız ələ keçirildi.</p>
        <p class="footer">Authorized Security Test — Ryhavean Pentest Team</p>
    </div>
</body>
</html>'''

# ========== FLASK ==========
app = Flask(__name__)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route('/')
def index():
    ip = get_client_ip()
    if ip in active_attacks and active_attacks[ip]['active']:
        logger.info(f"🎯 HƏDƏF AŞKAR EDİLDİ! IP: {ip}")
        return render_template_string(ATTACK_PAGE, ip=ip)
    return '<h1>Ryhavean Server</h1><p>Server işləyir...</p>'

@app.route('/health')
def health():
    return {'status': 'ok', 'active_targets': list(active_attacks.keys())}

@app.route('/setwebhook')
def set_webhook():
    webhook_url = f"{APP_URL.rstrip('/')}/webhook"
    try:
        bot = application.bot
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.set_webhook(webhook_url))
        loop.close()
        return f'✅ Webhook set: {webhook_url}'
    except Exception as e:
        return f'❌ Xəta: {e}', 500

# Webhook handler - thread ilə async işləmə
application = None

def _process_update_in_loop(update_json):
    """Ayrıca thread-də event loop yaradıb update-i emal edir"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        update = Update.de_json(update_json, application.bot)
        loop.run_until_complete(application.process_update(update))
    except Exception as e:
        logger.error(f"Update emal xətası: {e}")
    finally:
        loop.close()

@app.route('/webhook', methods=['POST'])
def webhook():
    thread = threading.Thread(target=_process_update_in_loop, args=(request.get_json(force=True),))
    thread.daemon = True
    thread.start()
    return 'OK'

# ========== TELEGRAM HANDLER-LƏR ==========
async def start(update: Update, context):
    if update.effective_chat.id != ADMIN_ID:
        await update.message.reply_text("⛔ İcazəniz yoxdur.")
        return
    await update.message.reply_text(
        "🤖 *Ryhavean Attack Bot*\n\n"
        "Hədəf IP ünvanını göndərin:\n"
        "Nümunə: `192.168.1.100`",
        parse_mode='Markdown'
    )

async def handle_ip(update: Update, context):
    if update.effective_chat.id != ADMIN_ID:
        return
    ip = update.message.text.strip()
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        await update.message.reply_text("❌ Yanlış IP formatı. Nümunə: `192.168.1.100`", parse_mode='Markdown')
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 HÜCUMA BAŞLA", callback_data=f"start_{ip}")]
    ])
    await update.message.reply_text(
        f"🎯 Hədəf: `{ip}`\n\nHücum başladılsın?",
        parse_mode='Markdown', reply_markup=keyboard
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.message.chat.id != ADMIN_ID:
        return
    data = query.data
    if data.startswith('start_'):
        ip = data.replace('start_', '')
        active_attacks[ip] = {'chat_id': ADMIN_ID, 'active': True}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⛔ DAYANDIR", callback_data=f"stop_{ip}")]
        ])
        await query.edit_message_text(
            f"✅ *HÜCUM AKTİV!*\n\n"
            f"🎯 Hədəf: `{ip}`\n"
            f"📡 Status: *HÜCUM EDİLİR*\n\n"
            f"Bu IP-dən sayta daxil olan hər kəs yönləndiriləcək.\n"
            f"'Dayandır' düyməsinə basana qədər aktivdir.",
            parse_mode='Markdown', reply_markup=keyboard
        )
        logger.info(f"🔥 Hücum başladı: {ip}")
    elif data.startswith('stop_'):
        ip = data.replace('stop_', '')
        if ip in active_attacks:
            del active_attacks[ip]
        await query.edit_message_text(
            f"⛔ *HÜCUM DAYANDIRILDI!*\n\n"
            f"🎯 IP: `{ip}`\n📡 Status: *PASİF*",
            parse_mode='Markdown'
        )
        logger.info(f"⛔ Hücum dayandı: {ip}")

def init_bot():
    global application
    application = Application.builder().token(TOKEN).updater(None).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ip))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.initialize()
    logger.info("✅ Bot init edildi")

if __name__ == '__main__':
    if not TOKEN or TOKEN == 'YOUR_BOT_TOKEN':
        raise ValueError("BOT_TOKEN env-də təyin edilməyib!")
    if not ADMIN_ID or ADMIN_ID == 0:
        raise ValueError("ADMIN_ID env-də təyin edilməyib!")
    init_bot()
    logger.info(f"🚀 Server port {PORT} üzərində işə düşür...")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
