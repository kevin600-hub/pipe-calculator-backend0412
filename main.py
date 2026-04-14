import math
import os
import json
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
import stripe

app = FastAPI()

# --- 1. 跨域配置 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 初始化 Firebase (保持原样) ---
db = None
try:
    secret_path = "/etc/secrets/serviceAccountKey.json"
    if os.path.exists(secret_path):
        cred = credentials.Certificate(secret_path)
        print(f"✅ 找到 Secret File: {secret_path}")
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
        print("ℹ️ 使用本地 serviceAccountKey.json")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase 初始化成功")
except Exception as e:
    print(f"❌ Firebase 初始化失败详情: {str(e)}")
    traceback.print_exc()

# --- 3. Stripe 配置 ---
stripe.api_key = os.getenv("STRIPE_API_KEY") 
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://pipe-calc-frontend0412.vercel.app")

@app.get("/")
def home():
    return {"message": "管道计算器后端已准备就绪", "firebase_status": "ready" if db else "failed"}

# --- 接口 A: 创建支付跳转链接 (仅修正了 stripe.checkout.Session.create) ---
@app.post("/create-checkout-session")
async def create_checkout():
    try:
        print(f"DEBUG: 收到支付请求, FRONTEND_URL={FRONTEND_URL}")
        
        if not stripe.api_key:
            print("❌ 错误: STRIPE_API_KEY 环境变量为空！")
            raise Exception("Stripe API Key is missing")

        # 1. 调用 Stripe (修正为新版语法：Session 首字母大写)
        print("DEBUG: 正在调用 Stripe API...")
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': '管道流速单次计算服务'},
                    'unit_amount': 500,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{FRONTEND_URL}/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/",
        )
        print(f"✅ Stripe Session 创建成功: {session.id}")

        # 2. 写入 Firebase
        if db:
            print("DEBUG: 正在写入 Firebase...")
            db.collection("orders").document(session.id).set({
                "status": "pending",
                "created_at": firestore.SERVER_TIMESTAMP
            })
            print("✅ Firebase 预记录成功")
        else:
            print("❌ 错误: Firebase 数据库未连接")
            raise Exception("Firebase database not initialized")
        
        return {"url": session.url}

    except Exception as e:
        print(f"🔥 [致命报错] 接口 /create-checkout-session 崩溃:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 接口 B: 核心计算逻辑 (保持原样) ---
@app.get("/calculate")
def calculate_flow(session_id: str, q_m3h: float, d_mm: float):
    if not db:
        raise HTTPException(status_code=500, detail="Database not ready")
    
    order_ref = db.collection("orders").document(session_id)
    order = order_ref.get()

    if not order.exists:
        raise HTTPException(status_code=403, detail="无效的支付 ID")
    
    order_data = order.to_dict()
    if order_data.get("status") != "paid":
        raise HTTPException(status_code=402, detail="该订单尚未支付成功")

    try:
        area = math.pi * ((d_mm / 2000) ** 2)
        velocity = q_m3h / (area * 3600)
        return {"result": round(velocity, 3), "unit": "m/s", "status": "success"}
    except Exception as e:
        return {"error": str(e)}

# --- 接口 D: Webhook (保持原样) ---
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            db.collection("orders").document(session.id).update({
                "status": "paid",
                "paid_at": firestore.SERVER_TIMESTAMP
            })
        return {"status": "success"}
    except Exception as e:
        print(f"⚠️ Webhook Error: {str(e)}")
        return {"error": str(e)}
