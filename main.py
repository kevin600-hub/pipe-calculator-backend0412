# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import math

app = FastAPI()

# 允许前端 Vercel 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # MVP阶段先允许所有，部署时再改
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "管道计算器后端已启动"}

@app.get("/calculate")
def calculate_flow(q_m3h: float = None, d_mm: float = None, v_ms: float = None):
    """
    计算逻辑：Q = A * v
    Q (m3/h), d (mm), v (m/s)
    """
    # 示例：已知流量Q和管径d，求流速v
    if q_m3h and d_mm and v_ms is None:
        # A = π * (d/2000)^2  (将mm转为m，再求面积)
        area = math.pi * ((d_mm / 2000) ** 2)
        # v = Q / (A * 3600)  (将m3/h转为m3/s)
        velocity = q_m3h / (area * 3600)
        return {"result": round(velocity, 3), "unit": "m/s", "type": "velocity"}
    
    # 这里以后可以扩展：已知v和d求Q，或者已知Q和v求d
    return {"error": "参数不足"}
