import math
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
import stripe

app = FastAPI()

# --- 1. 跨域配置 (允许前端 Vercel 访问) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 部署时建议改为你的 Vercel 域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 初始化 Firebase (确保 serviceAccountKey.json 在同级目录) ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase 初始化成功")
except Exception as e:
    print(f"❌ Firebase 初始化失败: {e}")

# --- 3. Stripe 配置 (目前先留空，后续填入) ---
# 从 Render 的环境变量中读取密钥
stripe.api_key = os.getenv("STRIPE_API_KEY") 
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
# 设置你的 Vercel 前端地址 (注意：结尾不要带斜杠)
# 这样设置：优先读取环境变量，如果没有配置则使用你的 Vercel 生产地址
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://pipe-calc-frontend0412.vercel.app")


@app.get("/")
def home():
    return {"message": "管道计算器后端已准备就绪"}

# --- 接口 A: 创建支付跳转链接 ---
@app.post("/create-checkout-session")
async def create_checkout():
    try:
        # 创建 Stripe 支付会话
        session = stripe.checkout.sessions.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': '管道流速单次计算服务'},
                    'unit_amount': 500, # 5.00 美金
                },
                'quantity': 1,
            }],
            mode='payment',
            # 支付成功后，带上 session_id 返回前端结果页
            success_url=f"{FRONTEND_URL}/result?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/",
        )
        
        # 在 Firebase 中预记录这笔交易
        db.collection("orders").document(session.id).set({
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 接口 B: 核心计算逻辑 (带支付校验) ---
@app.get("/calculate")
def calculate_flow(session_id: str, q_m3h: float, d_mm: float):
    """
    前端支付成功后，带上 session_id 请求此接口进行计算
    """
    # 1. 从 Firebase 检查支付状态
    order_ref = db.collection("orders").document(session_id)
    order = order_ref.get()

    if not order.exists:
        raise HTTPException(status_code=403, detail="无效的支付 ID")
    
    order_data = order.to_dict()
    if order_data.get("status") != "paid":
        # 如果你还没配置 Webhook，为了测试，可以临时注释掉下面这行
        raise HTTPException(status_code=402, detail="该订单尚未支付成功")

    # 2. 核心计算公式 (Q = A * v)
    try:
        # A = π * (d/2000)^2 (mm转m并求圆面积)
        area = math.pi * ((d_mm / 2000) ** 2)
        # v = Q / (A * 3600) (流量转为秒速)
        velocity = q_m3h / (area * 3600)
        
        return {
            "result": round(velocity, 3),
            "unit": "m/s",
            "status": "success"
        }
    except ZeroDivisionError:
        return {"error": "管径不能为0"}
    except Exception as e:
        return {"error": str(e)}

# --- 接口 C (NEW): Firebase 测试接口 ---
@app.get("/test-firebase")
async def test_firebase():
    """
    测试接口：写入测试数据到 Firebase，验证连接成功
    访问这个接口后，你应该能在 Firebase 后台看到测试数据
    """
    try:
        # 写入一条测试数据到 Firebase
        test_doc = {
            "test_name": "管道计算器后端测试",
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "connected",
            "message": "✅ Firebase 连接成功！这是来自后端的测试数据",
            "backend_url": "Render Deploy",
            "test_time": "2026-04-13"
        }
        
        # 写入到 Firebase 的 'test' 集合
        db.collection("test").document("connection_test").set(test_doc)
        
        return {
            "status": "success",
            "message": "✅ 测试数据已写入 Firebase",
            "collection": "test",
            "document": "connection_test",
            "data": test_doc
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "message": "❌ Firebase 连接失败"
        }

# --- 接口 D: Stripe Webhook (由 Stripe 自动调用) ---
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return {"error": "Invalid signature"}

    # 当收到支付成功的信号时，更新 Firebase 里的状态
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        db.collection("orders").document(session.id).update({
            "status": "paid",
            "paid_at": firestore.SERVER_TIMESTAMP
        })
    
    return {"status": "success"}
