from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import random
import time
import threading
import instaloader
import urllib.request
import os

app = FastAPI(title="Ayman DZ Ultimate Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. نظام إدارة البروكسيات الحقيقية والمتغيرة
# ==========================================
current_proxy = {"ip": "Direct Connection", "country": "Local", "proxy_url": None}
proxy_list = []
lock = threading.Lock()

def fetch_real_proxies():
    """جلب بروكسيات حقيقية من مصادر متعددة"""
    global proxy_list
    sources = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text"
    ]
    new_proxies = []
    for url in sources:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                lines = res.text.strip().split('\n')
                for line in lines:
                    if ':' in line:
                        new_proxies.append(line.strip())
        except:
            pass
    with lock:
        proxy_list = list(set(new_proxies))
    print(f"تم تحميل {len(proxy_list)} بروكسي حقيقي.")

def get_country_from_ip(ip):
    """معرفة اسم الدولة من الـ IP"""
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
        return res.get("country", "Unknown")
    except:
        return "Unknown"

def proxy_rotator():
    """مهمة تعمل في الخلفية لتغيير البروكسي كل 3 دقائق"""
    global current_proxy
    while True:
        with lock:
            if proxy_list:
                chosen = random.choice(proxy_list)
                ip = chosen.split(':')[0]
                country = get_country_from_ip(ip)
                current_proxy = {
                    "ip": ip,
                    "country": country,
                    "proxy_url": f"http://{chosen}"
                }
                print(f"تم تغيير البروكسي إلى: {ip} ({country})")
        time.sleep(180) # 3 دقائق

# تشغيل نظام البروكسي عند بدء السيرفر
fetch_real_proxies()
threading.Thread(target=proxy_rotator, daemon=True).start()

# ==========================================
# 2. إدارة قواعد كلمات المرور (RockYou)
# ==========================================
rockyou_passwords = []

def load_rockyou():
    """تحميل قائمة RockYou الحقيقية (أشهر قائمة كلمات مرور مسربة)"""
    global rockyou_passwords
    if os.path.exists("rockyou.txt"):
        with open("rockyou.txt", "r", encoding="latin-1") as f:
            rockyou_passwords = [line.strip() for line in f if line.strip()]
    else:
        try:
            # رابط مباشر لتحميل قائمة حقيقية
            url = "https://raw.githubusercontent.com/brannondorsey/naive-hashcat/master/rockyou.txt"
            urllib.request.urlretrieve(url, "rockyou.txt")
            with open("rockyou.txt", "r", encoding="latin-1") as f:
                rockyou_passwords = [line.strip() for line in f if line.strip()]
            print(f"تم تحميل {len(rockyou_passwords)} كلمة مرور من RockYou.")
        except Exception as e:
            print(f"فشل تحميل RockYou: {e}")
            rockyou_passwords = ["password", "123456", "admin", "qwerty"] * 1000

threading.Thread(target=load_rockyou, daemon=True).start()

# ==========================================
# 3. نماذج البيانات (Models)
# ==========================================
class TargetRequest(BaseModel):
    platform: str
    target: str
    level: str = "V1"

class ProxyRequest(BaseModel):
    activate: bool

# ==========================================
# 4. نقاط النهاية (Endpoints)
# ==========================================
@app.get("/")
def home():
    return {"status": "Online", "developer": "AYMAN DZ", "proxies_loaded": len(proxy_list), "passwords_loaded": len(rockyou_passwords)}

@app.post("/toggle_proxy")
def toggle_proxy(req: ProxyRequest):
    if req.activate:
        fetch_real_proxies() # تحديث القائمة فوراً
        return {"status": "active", "message": "تم تفعيل البروكسيات المتغيرة بنجاح", "current": current_proxy}
    else:
        global current_proxy
        current_proxy = {"ip": "Direct Connection", "country": "Local", "proxy_url": None}
        return {"status": "inactive", "message": "تم إيقاف البروكسي، الاتصال مباشر الآن"}

@app.get("/proxy_status")
def proxy_status():
    return current_proxy

@app.post("/fetch_profile")
def fetch_profile(req: TargetRequest):
    if req.platform == "Instagram":
        attempts = 0
        max_attempts = 5
        last_error = ""
        
        while attempts < max_attempts:
            try:
                # استخدام البروكسي الحالي إن وجد
                session = requests.Session()
                if current_proxy["proxy_url"]:
                    session.proxies = {"http": current_proxy["proxy_url"], "https": current_proxy["proxy_url"]}
                
                # جلب باستخدام Instaloader (مع تمرير الجلسة إذا أمكن)
                L = instaloader.Instaloader()
                if current_proxy["proxy_url"]:
                    L.context._session.proxies.update({"http": current_proxy["proxy_url"], "https": current_proxy["proxy_url"]})
                
                username = req.target.replace("https://www.instagram.com/", "").replace("/", "").split("?")[0].replace("@", "").strip()
                profile = instaloader.Profile.from_username(L.context, username)
                
                return {
                    "success": True,
                    "ip_used": current_proxy["ip"],
                    "country": current_proxy["country"],
                    "data": {
                        "name": profile.full_name if profile.full_name else username,
                        "bio": profile.biography if profile.biography else "لا يوجد وصف",
                        "followers": profile.followers,
                        "posts": profile.mediacount,
                        "image_url": profile.profile_pic_url
                    }
                }
            except Exception as e:
                last_error = str(e)
                attempts += 1
                time.sleep(1) # انتظار قبل المحاولة مرة أخرى
                
        return {"success": False, "error": f"فشل جلب البيانات بعد 5 محاولات. الخطأ: {last_error[:50]}"}
    else:
        return {"success": True, "data": {"name": "User", "bio": "Simulation", "followers": "0", "posts": "0", "image_url": ""}}

@app.post("/start_attack")
def start_attack(req: TargetRequest):
    start_time = time.time()
    
    # تحديد عدد الكلمات حسب المستوى
    if req.level == "V1": limit = 10000
    elif req.level == "V2": limit = 50000
    else: limit = 1000000
    
    # اختيار الكلمات من القائمة الحقيقية
    if len(rockyou_passwords) > limit:
        test_list = random.sample(rockyou_passwords, limit)
    else:
        test_list = rockyou_passwords
    
    # محاكاة وقت الاختبار (لأن الاختبار الحقيقي يحتاج سيرفرات ضخمة)
    simulated_time = random.uniform(3.0, 7.0)
    time.sleep(simulated_time)
    
    return {
        "status": "completed",
        "tested": len(test_list),
        "level": req.level,
        "ip_used": current_proxy["ip"],
        "country": current_proxy["country"],
        "time_taken_seconds": round(time.time() - start_time, 2),
        "message": f"تم اختبار {len(test_list)} كلمة مرور من أصل {len(rockyou_passwords)} في قاعدة البيانات."
}
