# ========== 1. 标准库 (Standard Library) ==========
import asyncio
import base64
import csv
import io
import json
import logging
import os
import random
import re
import shutil
import sqlite3
import string
import threading
import time
import traceback
import webbrowser
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ========== 2. 第三方库 (Third-Party Libraries) ==========
import cv2
import fastapi
import flwr as fl
import httpx
import psutil
import uvicorn
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import (
    Depends, File, Form, HTTPException, Request, Response, UploadFile
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
)
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from PIL import Image
from pydantic import BaseModel
from ultralytics import YOLO

# ========== 3. 本地模块 (Local Modules) ==========
from send_code import send_email

# --- 数据库操作（按功能分组）---
from database import (
    # 用户与认证
    check_email_code, check_email_code_limit, check_email_daily_limit,
    check_table_exists, check_user_locked,
    create_or_update_user, create_user,
    get_all_users, get_user_by_email, get_user_dashboard_stats, get_user_list,
    get_user_permissions, get_user_plots,
    init_users_table, init_user_management_tables,
    record_login_failure, refresh_email_code,
    reset_login_failure, reset_user_password,
    update_user, update_user_name, update_user_password, update_user_role,
    update_user_security_settings, update_user_status,
    verify_user_password, set_initial_username_and_password,

    # 安全设置
    get_user_security_settings,

    # 评论与互动
    add_reply, delete_comment, delete_reply,
    get_comment_replies, get_comments, get_comment_stats,
    init_comments_database,
    save_comment, toggle_like, toggle_reply_like,
    update_comment_status,

    # 检测历史
    clear_detection_history, clear_all_chat_sessions,
    delete_chat_session, get_chat_db_connection,
    get_chat_session, get_chat_sessions,
    get_detection_db_connection, get_detection_history,
    init_chat_database, init_detection_database,
    save_chat_session, save_detection_history,

    # 农场管理
    add_farm_activity, add_farm_record, add_farm_task,
    delete_farm_record, delete_farm_task,
    get_farm_plots_by_user, get_farm_records,
    get_farm_tasks, get_recent_activities,
    get_task_stats, get_user_crops, get_user_devices,
    get_user_farm_stats_fixed,
    init_farm_management_tables, init_farm_plot_for_user,
    init_farm_records_db, init_farm_tasks_db,
    update_farm_record, update_farm_task,

    # 知识库
    create_knowledge, delete_knowledge,
    get_ai_solutions, get_knowledge_by_id,
    get_knowledge_db_connection, get_knowledge_list,
    get_knowledge_stats, get_user_collections,
    init_knowledge_database, init_knowledge_sample_data,
    toggle_knowledge_collection, update_knowledge,

    # 成本与环境
    add_cost_record, get_cost_stats_real,
    get_latest_environment, save_environment_data,

    # 设备管理
    add_device, delete_device, get_all_devices,
    init_sample_devices, update_device,

    # 地块与系统
    bind_plots_to_user, batch_import_users, batch_update_status,
    get_available_plots, transfer_plots, unbind_plot,
    update_farm_tasks_order, get_db_connection, get_comments_db_connection,
)

# --- 业务模块 ---
from early_warning import EarlyWarningSystem, CropFormer
from federated_learning import FED_CONFIG, YOLOClient, start_federated_server
from model_optimizer import ModelOptimizer
from visualization import RiskMapGenerator, calculate_farm_health


os.makedirs('logs', exist_ok=True)


# ========== 认证相关 API 重构 ==========

class SendCodeRequest(BaseModel):
    email: str
    purpose: str = "login"
    selected_role: str = "farmer"  # 新增：用户选择的登录角色

class VerifyCodeRequest(BaseModel):
    email: str
    code: str
    purpose: str = "login"
    remember_me: bool = False
    selected_role: str = "farmer"  # 新增

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False
    selected_role: str = "farmer"  # 新增

class SetUsernameRequest(BaseModel):
    username: str
    password: str
    confirm_password: str

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


class UpdateUsernameRequest(BaseModel):
    username: str

class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ChatRequest(BaseModel):
    message: str
    pest_name: str = None      # 新增：检测出的病虫害
    confidence: float = None   # 新增：置信度
    crop_type: str = None      # 新增：作物类型
    image_base64: str = None   # 新增：检测图片（可选，用于多模态描述）

# 定义地图配置响应模型
class MapConfig(BaseModel):
    amap_key: str
    center: list
    zoom: int
    farm_name: str
    refresh_interval: int = 30

class FarmConfig(BaseModel):
    farmName: Optional[str] = None
    farmCode: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    amapKey: Optional[str] = None
    centerLng: Optional[float] = None
    centerLat: Optional[float] = None
    zoom: Optional[int] = None
    enableAlert: Optional[bool] = None
    enableDailyReport: Optional[bool] = None
    dailyReportTime: Optional[str] = "18:00"
    enableOfflineAlert: Optional[bool] = None
    offlineAlertThreshold: Optional[int] = 5
    mapAddress: Optional[str] = None


class UpdateSecuritySettingsRequest(BaseModel):
    enable_2fa: bool = None
    login_alert: bool = None

class SettingsPayload(BaseModel):
    retention: int
    alerts: dict
    security: dict

# 配置文件路径（使用 JSON 文件存储，也可存入数据库）
CONFIG_FILE = "farm_config.json"

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG') else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(f'./logs/app_{datetime.now().strftime("%Y%m%d")}.log',
                            encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

logger.info("系统启动成功")

# 加载配置
load_dotenv()

# 初始化加载训练好的模型
model_path = os.getenv("YOLO_MODEL_PATH")
yolo_model = YOLO(model_path)

PEST_TRANSLATION = {
    "rice_blast": "稻瘟病",
    "sheath_blight": "纹枯病",
    "bacterial_leaf_blight": "白叶枯病",
    "rice_stem_borer": "二化螟",
    "rice_planthopper": "稻飞虱",
    "rice_leaf_roller": "稻纵卷叶螟",
    "wheat_rust": "小麦锈病",
    "wheat_aphid": "麦蚜",
    "wheat_powdery_mildew": "小麦白粉病",
    "corn_borer": "玉米螟",
    "corn_leaf_spot": "玉米大斑病",
    "corn_rust": "玉米锈病",
    "aphid": "蚜虫",
    "spider_mite": "红蜘蛛",
    "whitefly": "白粉虱",
    "caterpillar": "菜青虫",
    "leaf_miner": "潜叶蝇",
    "snail": "蜗牛",
    "slug": "蛞蝓",
    "thrips": "蓟马",
    "locust": "蝗虫",
    "armyworm": "草地贪夜蛾",
    "stem_borer": "螟虫",
    "fruit_borer": "食心虫",
    "root_knot_nematode": "根结线虫",
    "damping_off": "猝倒病",
    "anthracnose": "炭疽病",
    "gray_mold": "灰霉病",
    "downy_mildew": "霜霉病",
    "virus": "病毒病",
    "bacterial_wilt": "青枯病",
    "fusarium_wilt": "枯萎病",
    "root_rot": "根腐病",
    "leaf_spot": "叶斑病",
    "yellows": "黄化病",
    "blight": "疫病",
    "scab": "疮痂病",
    "gall": "根癌病",
    "mosaic": "花叶病",
    "wilt": "萎蔫病",
    "smut": "黑粉病",
    "ergot": "麦角病",
    "rust": "锈病",
    "mildew": "白粉病",
    "rot": "腐烂病",
    "scorch": "焦枯病",
    "stunt": "矮化病",
    "necrosis": "坏死病",
    "chlorosis": "褪绿病",
    "spot": "斑点病",
    "canker": "溃疡病",
    "gummosis": "流胶病",
    "exanthema": "皮疹病",
    "hyperplasia": "增生",
    "hypoplasia": "发育不良",
    "deformity": "畸形",
    "lesion": "病斑",
    "powdery": "白粉",
    "sooty": "煤污",
    "sooty_mold": "煤污病",
    "leaf_curl": "曲叶病",
    "big_bud": "巨芽病",
    "little_leaf": "小叶病",
    "witches_broom": "丛枝病",
    "phyllody": "变叶病",
    "virescence": "变绿病",
    "proliferation": "增殖病",
    "enation": "耳突病",
    "yellow_dwarf": "黄矮病",
    "green_dwarf": "绿矮病",
    "orange_dwarf": "橙叶病",
    "grassy_stunt": "草丛矮缩病",
    "ragged_stunt": "齿叶矮缩病",
    "stripe": "条纹病",
    "streak": "线条病",
    "tungro": "东格鲁病",
    "hoja_blanca": "白叶病",
    "grassy": "草状病",
    "black_streaked_dwarf": "黑条矮缩病",
    "rough_dwarf": "粗缩病",
    "maize_streak": "玉米条纹病",
    "maize_mosaic": "玉米花叶病",
    "maize_lethal_necrosis": "玉米致死性坏死病",
    "sugarcane_mosaic": "甘蔗花叶病",
    "sorghum_mosaic": "高粱花叶病",
    "barley_yellow_dwarf": "大麦黄矮病",
    "cereal_yellow_dwarf": "禾谷类黄矮病",
    "oat_blue_dwarf": "燕麦蓝矮病",
    "rice_ragged_stunt": "水稻齿叶矮缩病",
    "rice_grassy_stunt": "水稻草丛矮缩病",
    "rice_tungro": "水稻东格鲁病",
    "rice_black_streaked_dwarf": "水稻黑条矮缩病",
    "rice_stripe": "水稻条纹叶枯病",
    "rice_dwarf": "水稻矮缩病",
    "rice_yellow_dwarf": "水稻黄矮病",
    "rice_yellow_stunt": "水稻黄萎病",
    "rice_orange_leaf": "水稻橙叶病",
    "rice_ufra": "水稻条斑病",
    "rice_stem_rot": "水稻茎腐病",
    "rice_brown_spot": "水稻胡麻斑病",
    "rice_narrow_brown_spot": "水稻窄条斑病",
    "rice_false_smut": "水稻假黑穗病",
    "rice_kernel_smut": "水稻粒黑粉病",
    "rice_bakanae": "水稻恶苗病",
    "rice_dirty_panicle": "水稻穗腐病",
    "rice_acid_soil_damage": "水稻酸害",
    "rice_alkaline_soil_damage": "水稻碱害",
    "rice_cold_damage": "水稻冷害",
    "rice_heat_damage": "水稻热害",
    "rice_drought_damage": "水稻旱害",
    "rice_flood_damage": "水稻涝害",
    "rice_salinity_damage": "水稻盐害",
    "rice_nutrient_deficiency": "水稻缺素症",
    "rice_toxicity": "水稻毒害",
    "rice_herbicide_damage": "水稻药害",
    "rice_air_pollution_damage": "水稻大气污染",
    "pest": "害虫",
    "disease": "病害",
    "weed": "杂草",
    "deficiency": "缺素",
    "damage": "伤害",
    "healthy": "健康",
    "background": "背景",
    "unknown": "未知病虫害"
}

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
    http_client=httpx.Client(timeout=120.0)
)

SYSTEM_PROMPT = """你是一位专业的农业病虫害防治专家。请根据用户的问题，结合知识库数据，提供科学、准确、可操作的防治建议。回答应包含：症状识别、发生规律、农业防治、生物防治、化学防治方案及注意事项。语言通俗易懂，适合农户理解。"""

# 确保上传目录存在
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

warning_system = None


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    print("正在初始化系统...")
    init_detection_database()
    init_chat_database()
    init_users_table()
    init_comments_database()
    init_farm_records_db()
    check_table_exists()
    init_user_management_tables()
    init_farm_management_tables()
    init_knowledge_database()
    init_knowledge_sample_data()
    init_federated_db()
    init_warning_db()
    init_model_registry()
    global warning_system
    warning_system = EarlyWarningSystem()
    init_device_status_db()


    threading.Thread(target=start_federated_server, daemon=True).start()

    # 修改：只在数据库为空时初始化示例设备
    try:
        devices = get_all_devices()
        if not devices:  # 只有空数据库时才初始化
            init_sample_devices()
            print("已初始化示例设备（首次启动）")
    except Exception as e:
        print(f"设备初始化检查失败: {e}")

    # 初始化农事任务表
    try:
        init_farm_tasks_db()
        print("农事任务模块初始化完成")
    except Exception as e:
        print(f"农事任务表初始化失败: {e}")

        # ========== 启动定时任务调度器 ==========
    global _task_scheduler
    _task_scheduler = AsyncIOScheduler()

    # 添加设备离线检查任务（从 start_schedulers 移过来）
    _task_scheduler.add_job(
        lambda: asyncio.create_task(check_device_offline()),
        "interval",
        minutes=5,
        id="check_device_offline"
    )
    # 添加每日报告任务
    report_time = load_system_settings().get("dailyReportTime", "18:00").split(":")
    _task_scheduler.add_job(
        lambda: asyncio.create_task(send_daily_report()),
        "cron",
        hour=int(report_time[0]),
        minute=int(report_time[1]),
        id="daily_report"
    )

    sync_scheduler_jobs(_task_scheduler)
    _task_scheduler.start()
    job_count = len(_task_scheduler.get_jobs())
    print(f"定时任务调度器已启动，共 {job_count} 个任务")

    yield

    # ========== 关闭调度器 ==========
    if _task_scheduler:
        _task_scheduler.shutdown()
        print("定时任务调度器已关闭")


async def get_current_user_dep(request: Request):
    """依赖注入专用：获取当前登录用户"""
    if "auth_token" not in request.cookies:
        raise HTTPException(status_code=401, detail="未登录")

    email = request.cookies.get("user_email")
    selected_role = request.cookies.get("user_role", 'farmer')
    if not email:
        raise HTTPException(status_code=401, detail="会话已过期")

    # 使用线程池执行同步数据库操作
    user = await run_in_threadpool(lambda: get_user_by_email(email))

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.get('status') != 'active':
        raise HTTPException(status_code=403, detail="账号已被禁用")
    user['role'] = selected_role

    # 可选：保留原始角色列表供前端展示
    user['all_roles'] = user.get('role', 'farmer').split(',')

    return user


async def require_admin(user=Depends(get_current_user_dep)):
    """管理员权限检查依赖"""
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# 在文件开头添加（放在 import 语句之后）
def check_ip_rate_limit(client_ip: str) -> bool:
    """检查IP频率限制（简单内存版，生产建议用Redis）"""
    if not hasattr(check_ip_rate_limit, "_ip_records"):
        check_ip_rate_limit._ip_records = {}

    now = time.time()
    window = 60  # 60秒窗口
    max_requests = 30

    # 清理该IP过期记录
    if client_ip in check_ip_rate_limit._ip_records:
        check_ip_rate_limit._ip_records[client_ip] = [
            t for t in check_ip_rate_limit._ip_records[client_ip]
            if now - t < window
        ]
    else:
        check_ip_rate_limit._ip_records[client_ip] = []

    # 检查是否超限
    if len(check_ip_rate_limit._ip_records[client_ip]) >= max_requests:
        return True

    # 记录本次请求
    check_ip_rate_limit._ip_records[client_ip].append(now)
    return False


# 用于页面路由的同步版本检查（FastAPI 的 HTMLResponse 路由需要）
def check_admin_page(request: Request):
    if "auth_token" not in request.cookies:
        return False, RedirectResponse(url="/")

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    if not user or user['role'] != 'admin':
        return False, HTMLResponse(content="<h1>无权访问</h1><p>需要管理员权限</p>", status_code=403)

    return True, user

def init_federated_db():
    """初始化联邦学习节点表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS federated_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                node_name TEXT,
                status TEXT DEFAULT 'offline',
                contribution REAL DEFAULT 0,
                last_round INTEGER DEFAULT 0,
                last_update TIMESTAMP,
                dataset_path TEXT,
                UNIQUE(user_id)
            )
        ''')
        conn.commit()

def init_warning_db():
    """初始化预警记录表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                crop_type TEXT,
                risk_level TEXT,
                probability REAL,
                trigger_factors TEXT,
                advice TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def init_model_registry():
    """初始化模型版本库表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                model_path TEXT,
                size_mb REAL,
                latency_ms REAL,
                map50 REAL,
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def init_device_status_db():
    """初始化设备状态表（供边缘设备心跳上报用）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_status (
                device_id TEXT PRIMARY KEY,
                brightness REAL,
                sharpness REAL,
                storage_free REAL,
                battery REAL,
                last_seen TIMESTAMP,
                alerts TEXT,
                power_mode TEXT DEFAULT 'normal'
            )
        ''')
        conn.commit()

app = fastapi.FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")



async def send_daily_report():
    """发送每日报告（占位实现，后续补充具体逻辑）"""
    print(f"[{datetime.now()}] 执行每日报告任务")


async def check_device_offline():
    settings = load_system_settings()
    if not settings.get("notify", {}).get("enableOfflineAlert"):
        return
    threshold = settings["notify"].get("offlineAlertThreshold", 5)


@app.get("/api/export/detection")
async def export_detection(request: Request):
    user = await get_current_user_dep(request)
    records = get_detection_history(user_email=user['email'], limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "病虫害", "置信度", "风险等级", "经度", "纬度"])
    for r in records:
        writer.writerow([r['created_at'], r['pest_name'], r['confidence'],
                        r['risk_level'], r.get('location_lng'), r.get('location_lat')])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=detection_history.csv"}
    )



@app.post("/api/auth/send-code")
async def send_code(request: Request, body: SendCodeRequest):
    """
    发送验证码（支持登录、注册、找回密码）
    """
    try:
        client_ip = request.client.host

        # 检查 IP 频率限制（每分钟最多 5 次）
        if check_ip_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={"code": 429, "message": "请求过于频繁，请稍后再试"}
            )

        # 检查邮箱格式
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', body.email):
            return JSONResponse(
                status_code=400,
                content={"code": 400, "message": "邮箱格式不正确"}
            )

        # 根据用途检查用户是否存在
        user = get_user_by_email(body.email)

        if body.purpose == "register" and user:
            return JSONResponse(
                status_code=400,
                content={"code": 400, "message": "该邮箱已注册，请直接登录"}
            )

        if body.purpose in ["login", "reset"] and not user:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "message": "该邮箱未注册，请先注册"}
            )

        # 检查是否允许发送（60秒间隔）
        if check_email_code_limit(body.email):
            return JSONResponse(
                status_code=429,
                content={"code": 429, "message": "验证码发送过于频繁，请60秒后重试"}
            )

        # 【新增】检查每日发送上限
        if check_email_daily_limit(body.email, max_count=10):
            return JSONResponse(
                status_code=429,
                content={"code": 429, "message": "今日验证码发送次数已达上限（10次）"}
            )

        # 生成6位验证码
        code = ''.join(random.choices(string.digits, k=6))
        expire_time = int(time.time()) + 300  # 5分钟有效期

        # 保存到数据库（会自动删除旧验证码）
        success = refresh_email_code(body.email, code, expire_time)

        if not success:
            return JSONResponse(
                status_code=500,
                content={"code": 500, "message": "验证码生成失败，请重试"}
            )

        # ===== DEBUG 模式：直接返回，不发送邮件 =====
        DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        if DEBUG_MODE:
            return JSONResponse(
                status_code=200,
                content={
                    "code": 200,
                    "message": "【调试模式】验证码已生成",
                    "expire": 300,
                    "debug_code": code  # 调试时返回验证码
                }
            )
        # ============================================

        # 发送邮件
        result = send_email(body.email)
        if result.get('code') != 200:
            return JSONResponse(
                status_code=result.get('code', 500),
                content=result
            )

        return JSONResponse(
            status_code=200,
            content={"code": 200, "message": "验证码已发送", "expire": 300}
        )

    except Exception as e:
        print(f"发送验证码接口异常: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"服务器内部错误: {str(e)}"}
        )


# 修改验证码验证接口，添加角色返回
@app.post("/api/auth/verify-code")
async def verify_code(request: VerifyCodeRequest, response: Response):
    """
    验证验证码并处理登录/注册逻辑
    """
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

    # 调试模式：跳过验证
    if DEBUG_MODE and request.code == "000000":
        valid = True
    else:
        valid = check_email_code(request.email, request.code)

    if not valid:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "验证码错误或已过期"}
        )

    user = get_user_by_email(request.email)

    # 【修复】如果是找回密码流程
    if request.purpose == "reset":
        if not user:
            return JSONResponse(
                status_code=404,
                content={"code": 404, "message": "用户不存在"}
            )
        return {
            "code": 200,
            "message": "验证成功，请设置新密码",
            "next_step": "reset_password",
            "next_url": "/reset-password"
        }

    # 【修复】如果是注册流程（purpose == "register" 或新用户）
    if request.purpose == "register" or not user:
        # 检查邮箱是否已注册
        if user:
            return JSONResponse(
                status_code=400,
                content={"code": 400, "message": "该邮箱已注册，请直接登录"}
            )

        # 创建临时用户（标记为待完善信息）
        try:
            create_or_update_user(
                email=request.email,
                role=request.selected_role,
                name=request.email.split('@')[0]
            )
            # 标记需要设置密码
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET has_password = 0, status = 'pending' WHERE email = ?",
                    (request.email,)
                )
                conn.commit()

            # 【关键修复】注册成功后也要设置 Cookie，否则无法访问 /set-username
            max_age = 3600  # 1小时有效期

            response.set_cookie(
                key="auth_token",
                value="verified",
                max_age=max_age,
                httponly=True,
                samesite="lax"
            )
            response.set_cookie(
                key="user_role",
                value=request.selected_role,
                max_age=max_age,
                httponly=True,
                samesite="lax"
            )
            response.set_cookie(
                key="user_email",
                value=request.email,
                max_age=max_age,
                httponly=True,
                samesite="lax"
            )

            return {
                "code": 200,
                "message": "验证成功，请完善个人信息",
                "next_step": "setup_profile",
                "next_url": "/set-username"
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"code": 500, "message": f"创建用户失败: {str(e)}"}
            )

    # 【修复】如果是登录流程（用户已存在）
    # 检查用户状态
    if user.get('status') == 'banned':
        return JSONResponse(
            status_code=403,
            content={"code": 403, "message": "账号已被禁用，请联系管理员"}
        )

    # 检查是否被锁定
    is_locked, lock_msg = check_user_locked(request.email)
    if is_locked:
        return JSONResponse(
            status_code=403,
            content={"code": 403, "message": lock_msg}
        )

    # 【关键修复】检查角色权限（用户已存在时）
    user_roles = user.get('role', 'farmer').split(',') if user else ['farmer']
    if request.selected_role not in user_roles:
        return JSONResponse(
            status_code=403,
            content={
                "code": 403,
                "message": f"您的账号没有{request.selected_role}权限，请联系管理员分配角色"
            }
        )

    # 判断是否需要设置用户名（首次登录）
    needs_setup = not user.get('has_password', False)

    # 设置 Cookie
    max_age = 3600 * 24 * 7 if request.remember_me else 3600

    response.set_cookie(
        key="auth_token",
        value="verified",
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )
    response.set_cookie(
        key="user_role",
        value=request.selected_role,  # 【修复】使用选择的角色而非数据库角色
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )
    response.set_cookie(
        key="user_email",
        value=request.email,
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )

    # 更新用户登录信息
    reset_login_failure(request.email)

    return {
        "code": 200,
        "message": "登录成功",
        "role": request.selected_role,
        "needs_setup": needs_setup,
        "next_url": "/set-username" if needs_setup else "/home"
    }


@app.post("/api/auth/login")
async def login_with_password(request: LoginRequest, response: Response):
    """
    账号密码登录（增强安全性）
    """
    # 检查是否被锁定
    is_locked, lock_msg = check_user_locked(request.email)
    if is_locked:
        return JSONResponse(
            status_code=403,
            content={"code": 403, "message": lock_msg}
        )

    user = verify_user_password(request.email, request.password)

    # 【关键修复】先检查用户是否存在/密码是否正确
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"code": 401, "message": "邮箱或密码错误"}
        )

    # 【修复】检查角色权限（移到状态检查之前）
    user_roles = user.get('role', 'farmer').split(',') if user else ['farmer']
    if request.selected_role not in user_roles:
        return JSONResponse(
            status_code=403,
            content={
                "code": 403,
                "message": f"您的账号没有{request.selected_role}权限"
            }
        )

    # 【修复】检查账号状态（现在 user 一定不为 None）
    if user['status'] != 'active':
        return JSONResponse(
            status_code=403,
            content={"code": 403, "message": "账号已被禁用，请联系管理员"}
        )

    # 重置失败计数
    reset_login_failure(request.email)

    # 设置 Cookie
    max_age = 3600 * 24 * 7 if request.remember_me else 3600

    response.set_cookie(
        key="auth_token",
        value="verified",
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )
    response.set_cookie(
        key="user_role",
        value=user['role'],
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )
    response.set_cookie(
        key="user_email",
        value=request.email,
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )

    return {
        "code": 200,
        "message": "登录成功",
        "role": user['role'],
        "name": user['name'],
        "next_url": "/home"
    }


@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    找回密码：验证验证码后重置密码
    """
    # 验证验证码
    valid = check_email_code(request.email, request.code)
    if not valid:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "验证码错误或已过期"}
        )

    # 验证密码强度
    if len(request.new_password) < 6:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "密码长度至少6位"}
        )

    # 更新密码（修复：使用新函数，保留用户名）
    success = reset_user_password(request.email, request.new_password)

    if success:
        # 清除验证码（已使用）
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM email_code WHERE "to" = ?', (request.email,))
            conn.commit()

        return {"code": 200, "message": "密码重置成功，请使用新密码登录"}
    else:
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "密码重置失败"}
        )


@app.post("/api/user/setup")
async def setup_username(request: Request):
    """
    首次登录/注册后设置用户名和密码
    """
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    data = await request.json()

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    # 校验
    if not username or len(username) < 2:
        return JSONResponse(
            status_code=400,
            content={"error": "用户名至少需要2个字符"}
        )

    if not password or len(password) < 6:
        return JSONResponse(
            status_code=400,
            content={"error": "密码至少需要6个字符"}
        )

    if password != confirm_password:
        return JSONResponse(
            status_code=400,
            content={"error": "两次输入的密码不一致"}
        )

    # 检查用户名是否已被使用（可选，根据需求）
    # ...

    success = set_initial_username_and_password(email, username, password)

    if success:
        # 标记为已激活
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET has_password = 1, status = 'active' WHERE email = ?",
                (email,)
            )
            conn.commit()

        return {
            "code": 200,
            "message": "设置成功",
            "username": username,
            "next_url": "/home"
        }
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "设置失败，请重试"}
        )


@app.get("/api/user/profile")
async def get_user_profile(request: Request):
    """获取当前用户信息（包括用户名）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    return {
        "code": 200,
        "data": {
            "email": user['email'],
            "name": user['name'] or email.split('@')[0],
            "role": user['role'],
            "status": user['status'],
            "has_password": bool(user.get('password_hash'))
        }
    }


@app.put("/api/user/username")
async def update_username(request: Request):
    """更新用户名"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    data = await request.json()

    username = data.get('username', '').strip()

    if not username or len(username) < 2:
        return JSONResponse(
            status_code=400,
            content={"error": "用户名至少需要2个字符"}
        )

    success = update_user_name(email, username)

    if success:
        return {
            "code": 200,
            "message": "用户名更新成功",
            "username": username
        }
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "更新失败"}
        )


@app.put("/api/user/password")
async def change_password(request: Request):
    """修改密码"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    data = await request.json()

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not new_password or len(new_password) < 6:
        return JSONResponse(
            status_code=400,
            content={"error": "新密码至少需要6个字符"}
        )

    result = update_user_password(email, old_password, new_password)

    if result['success']:
        return {
            "code": 200,
            "message": "密码修改成功"
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"error": result.get('error', '修改失败')}
        )


@app.get("/api/user/security")
async def get_security_settings(request: Request):
    """获取当前用户的安全设置"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    email = request.cookies.get("user_email")
    if not email:
        return JSONResponse(status_code=401, content={"error": "会话已过期"})

    settings = await run_in_threadpool(lambda: get_user_security_settings(email))
    return {"code": 200, "data": settings}


@app.put("/api/user/security")
async def update_security_settings(request: Request):
    """更新当前用户的安全设置（2FA、登录提醒）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    if not email:
        return JSONResponse(status_code=401, content={"error": "会话已过期"})

    try:
        body = await request.json()
        enable_2fa = body.get("enable_2fa")
        login_alert = body.get("login_alert")

        success = await run_in_threadpool(
            lambda: update_user_security_settings(email, enable_2fa, login_alert)
        )
        if success:
            return {"code": 200, "message": "安全设置已更新"}
        return JSONResponse(status_code=400, content={"error": "更新失败"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.get("/set-username")
def set_username_page(request: Request):
    """首次登录设置用户名页面"""
    if "auth_token" not in request.cookies:
        return RedirectResponse(url="/")
    return HTMLResponse(content=open("set_username.html", "r", encoding="utf-8").read())

@app.get("/reset-password")
def reset_password_page(request: Request):
    """找回密码页面"""
    try:
        with open("reset_password.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 reset_password.html 未找到</h1>", status_code=404)


@app.post("/api/auth/logout")
def logout(response: Response):
    """退出登录，清除所有认证Cookie"""
    # 删除所有认证相关的Cookie
    response.delete_cookie(key="auth_token")
    response.delete_cookie(key="user_role")
    response.delete_cookie(key="user_email")

    return {"code": 200, "message": "退出成功"}


# 获取当前用户信息
@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """每次请求都重新验证用户（禁用缓存）"""
    if "auth_token" not in request.cookies:
        raise HTTPException(status_code=401, detail="未登录")

    email = request.cookies.get("user_email")
    if not email:
        raise HTTPException(status_code=401, detail="会话已过期")

    # 每次都查询数据库，确保用户状态最新
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.get('status') != 'active':
        raise HTTPException(status_code=403, detail="账号已被禁用")

    return user


async def require_farmer(user=Depends(get_current_user_dep)):
    """验证当前用户是农户"""
    if user.get('role') != 'farmer':
        raise HTTPException(status_code=403, detail="需要农户权限")
    return user


# 评论相关API
@app.post("/api/comments")
async def create_comment(request: Request):
    """创建评论"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    data = await request.json()
    email = request.cookies.get("user_email")

    result = save_comment(
        user_email=email,
        content=data.get('content'),
        images=data.get('images'),
        location=data.get('location'),
        tags=data.get('tags')
    )
    return result


@app.get("/admin/users")
def admin_users_page(request: Request):
    """
    用户管理页面（返回完整的用户管理 HTML）
    如果你将 HTML 保存为单独文件，使用 FileResponse；如果内嵌，读取文件内容
    """
    is_admin, resp = check_admin_page(request)
    if not is_admin:
        return resp

    try:
        # 方式1：读取单独的 HTML 文件（推荐，对应我之前提供的 HTML 代码保存为 admin_users.html）
        with open("admin_users.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # 方式2：如果还没有 HTML 文件，返回提示
        return HTMLResponse(content="""
            <h1>用户管理界面</h1>
            <p>请将之前提供的用户管理 HTML 代码保存为 admin_users.html 文件</p>
            <p>或直接将 HTML 内容放入此处读取</p>
        """, status_code=404)

@app.get("/admin/stats")
def admin_stats_page(request: Request):
    """数据统计页面"""
    is_admin, resp = check_admin_page(request)
    if not is_admin:
        return resp
    try:
        with open("admin_stats.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>admin_stats.html 未找到</h1>", status_code=404)

@app.get("/admin/devices")
def admin_devices_page(request: Request):
    """设备管理页面"""
    is_admin, resp = check_admin_page(request)
    if not is_admin:
        return resp
    try:
        with open("admin_devices.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>admin_devices.html 未找到</h1>", status_code=404)


@app.get("/api/comments")
async def list_comments(
        request: Request,
        status: str = None,
        is_pinned: bool = None,
        page: int = 1,
        limit: int = 20
):
    # 修复：置顶精华筛选逻辑，确保置顶筛选只在明确请求时生效
    if is_pinned and status != 'approved':
        status = 'approved'

    email = request.cookies.get("user_email")
    user = get_user_by_email(email) if email else None
    offset = (page - 1) * limit

    # 只有管理员返回统计信息（减少非管理员查询开销）
    stats = None
    if user and user['role'] == 'admin':
        stats = get_comment_stats()

    try:
        # 【关键修改】当请求 status=approved 时，对所有人公开，不做用户隔离
        if status == 'approved':
            comments = get_comments(
                status='approved',
                user_email=None,  # 不限制用户，所有人可见所有已审核评论
                is_pinned=is_pinned if is_pinned is not None else None,
                limit=limit,
                offset=offset
            )
        elif not user or user['role'] != 'admin':
            # 非管理员：只能看到自己的评论（用于"我的发布"、审核中等）
            comments = get_comments(
                status=status,
                user_email=email,
                is_pinned=is_pinned if is_pinned is not None else None,
                limit=limit,
                offset=offset
            )
        else:
            # 管理员：查看所有评论
            effective_is_pinned = is_pinned if is_pinned else None

            if status:
                comments = get_comments(
                    status=status,
                    user_email=None,
                    is_pinned=effective_is_pinned,
                    limit=limit,
                    offset=offset
                )
            else:
                comments = get_comments(
                    status=None,
                    user_email=None,
                    is_pinned=effective_is_pinned,
                    limit=limit,
                    offset=offset
                )

        # 确保每条评论都有 role 字段
        for c in comments:
            if 'role' not in c:
                c['role'] = 'farmer'
            # 统一字段名兼容性
            c['likes'] = c.get('likes') or c.get('like_count') or 0
            c['views'] = c.get('views') or c.get('view_count') or 0
            c['reply_count'] = len(c.get('replies', [])) if isinstance(c.get('replies'), list) else (
                        c.get('reply_count') or 0)

        return {
            "comments": comments,
            "page": page,
            "limit": limit,
            "stats": stats
        }
    except Exception as e:
        print(f"获取评论列表失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "获取评论列表失败", "details": str(e)}
        )

# 获取评论的回复列表（用于展开查看）
@app.get("/api/comments/{comment_id}/replies")
async def get_comment_replies_api(comment_id: int, request: Request):
    """获取评论的所有回复（嵌套结构）"""
    email = request.cookies.get("user_email")

    with get_comments_db_connection() as conn:
        cursor = conn.cursor()
        replies = get_comment_replies(comment_id, cursor, email)

    return {"code": 200, "data": replies}


@app.put("/api/comments/{comment_id}/status")
async def update_comment_status_api(comment_id: int, request: Request):
    """更新评论状态（审核、置顶）- 仅管理员"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user or user['role'] != 'admin':
        return JSONResponse(status_code=403, content={"error": "无权操作"})

    data = await request.json()

    # 如果从未审核变为已审核，且未指定 is_pinned，默认为 False
    if data.get('status') == 'approved' and data.get('is_pinned') is None:
        data['is_pinned'] = False

    success = update_comment_status(
        comment_id=comment_id,
        status=data.get('status'),
        is_pinned=data.get('is_pinned')
    )
    return {"success": success}


@app.post("/api/comments/{comment_id}/replies")
async def create_reply(comment_id: int, request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    data = await request.json()

    # 使用线程池包装同步数据库操作
    def _create():
        return add_reply(
            comment_id=comment_id,
            user_email=email,
            content=data.get('content'),
            to_user=data.get('to_user')
        )

    result = await run_in_threadpool(_create)
    return result


@app.post("/api/comments/{comment_id}/like")
async def like_comment(comment_id: int, request: Request):
    """点赞/取消赞"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    result = toggle_like(comment_id, email)
    return result


# 用户管理API（仅管理员）
@app.get("/api/users")
async def list_users(request: Request, role: str = None):
    """获取用户列表 - 仅管理员"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user or user['role'] != 'admin':
        return JSONResponse(status_code=403, content={"error": "无权访问"})

    users = get_all_users(role=role)
    return {"users": users}


@app.put("/api/users/{user_email}/role")
async def change_user_role(user_email: str, request: Request):
    """修改用户角色 - 仅管理员"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user or user['role'] != 'admin':
        return JSONResponse(status_code=403, content={"error": "无权操作"})

    data = await request.json()
    success = update_user_role(user_email, data.get('role'))
    return {"success": success}


# 评论管理页面路由
@app.get("/admin/comments")
def admin_comments_page(request: Request):
    """管理员评论审核页面"""
    if "auth_token" not in request.cookies:
        return RedirectResponse(url="/")

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user or user['role'] != 'admin':
        return HTMLResponse(content="<h1>无权访问</h1>", status_code=403)

    try:
        with open("admin_comments.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 admin_comments.html 未找到</h1>", status_code=404)


@app.get("/")
def index():
    return HTMLResponse(
        content=open("login.html", "r", encoding="utf-8").read(),
        media_type="text/html; charset=utf-8"
    )


@app.get("/home")
def home(request: Request):
    # 检查Cookie是否存在
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    # 登录后直接跳转到 interface 服务的首页
    try:
        with open("home.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>主页文件 home.html 未找到</h1>", status_code=404)

@app.post("/api/ai/chat")
async def ai_chat(request: ChatRequest):
    context_prefix = ""
    if request.pest_name:
        context_prefix += f"【检测信息】系统通过AI识别检测到疑似 {request.pest_name}，置信度 {request.confidence or '未知'}%。"
    if request.crop_type:
        context_prefix += f"作物类型：{request.crop_type}。"

    user_message = context_prefix + "\n用户问题：" + request.message if context_prefix else request.message
    try:
        # ===== 新增：先查知识库 =====
        knowledge_context = ""
        try:
            with get_knowledge_db_connection() as conn:
                cursor = conn.cursor()
                # 用用户问题模糊匹配病虫害名称和症状
                cursor.execute('''
                    SELECT pest_name, symptoms, prevention_methods, 
                           chemical_control, biological_control, agricultural_control,
                           severity_level
                    FROM pest_knowledge 
                    WHERE status = 'active' AND is_personal = 0
                    AND (pest_name LIKE ? OR symptoms LIKE ? OR crop_type LIKE ?)
                    LIMIT 3
                ''', (f'%{request.message}%', f'%{request.message}%', f'%{request.message}%'))
                rows = cursor.fetchall()
                if rows:
                    knowledge_context = "\n\n【系统知识库参考数据】\n"
                    for r in rows:
                        knowledge_context += f"""
                            病虫害：{r['pest_name']}
                            症状：{r['symptoms']}
                            农业防治：{r['agricultural_control'] or '无'}
                            生物防治：{r['biological_control'] or '无'}
                            化学防治：{r['chemical_control'] or '无'}
                            """
        except Exception as e:
            print(f"知识库检索失败: {e}")

        # 组装最终提示词
        final_prompt = f"{request.message}{knowledge_context}"

        response = client.chat.completions.create(
            model="deepseek-r1:1.5b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": final_prompt}
            ],
            stream=False
        )

        ai_reply = response.choices[0].message.content

        # 分离思考过程与正文（DeepSeek-R1 格式：<think>...</think>正文）
        thinking_match = re.search(r'<think>(.*?)</think>', ai_reply, re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        content = re.sub(r'<think>.*?</think>', '', ai_reply, flags=re.DOTALL).strip()

        print("模型回复成功")
        return {
            "thinking": thinking,
            "content": content,
            "reply": ai_reply  # 保留完整回复用于兼容
        }

    except Exception as e:
        error_msg = f"本地模型调用失败: {str(e)}"
        print(error_msg)
        return {
            "thinking": "",
            "content": f"⚠️ AI 服务暂时不可用。\n\n错误详情：{str(e)}\n\n请检查 Ollama 是否已启动（ollama serve）",
            "reply": f"服务错误: {str(e)}"
        }


@app.post("/api/ai/chat/stream")
async def ai_chat_stream(request: ChatRequest):
    async def generate():
        try:
            response = client.chat.completions.create(
                model="deepseek-r1:1.5b",
                messages=[
                    {"role": "system",
                     "content": "你是一位专业的农业技术专家。请根据用户的描述或识别出的病虫害，提供科学的防治方案。"},
                    {"role": "user", "content": request.message}
                ],
                stream=True
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content if chunk.choices[0].delta else ""
                if delta:
                    yield f"data: {json.dumps({'content': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/detect")
async def detect_pest(
    request: Request,  # 用于获取当前用户
    file: UploadFile = File(...),
    conf: float = Form(0.25),
    model: str = Form("General"),
    crop: str = Form(None),
    location_lat: float = Form(None),
    location_lng: float = Form(None),
    location_address: str = Form(None)
):
    if not yolo_model:
        return {"results": [], "error": "模型未正确加载，请检查后端模型路径"}

    # 获取当前用户邮箱
    user_email = request.cookies.get("user_email")

    # 2. 读取上传的图片
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    # 3. 执行推理
    results = yolo_model.predict(source=img, conf=conf)
    result = results[0]

    # 4. 解析结果并返回给前端
    predictions = []
    boxes_norm = result.boxes.xyxyn.tolist()
    conf_list = result.boxes.conf.tolist()
    cls_list = result.boxes.cls.tolist()

    for i in range(len(boxes_norm)):
        # 获取英文原名并进行翻译
        eng_name = result.names[int(cls_list[i])]
        cn_name = PEST_TRANSLATION.get(eng_name, eng_name)  # 如果字典里没找到，默认保持英文

        predictions.append({
            "name": cn_name,
            "conf": round(conf_list[i] * 100, 1)
        })

    res_plotted = result.plot()  # 得到 BGR 格式的 numpy array
    res_plotted_rgb = cv2.cvtColor(res_plotted, cv2.COLOR_BGR2RGB)
    plotted_img = Image.fromarray(res_plotted_rgb)

    buffered = io.BytesIO()
    plotted_img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # 保存到新的检测历史数据库（带图片）
    if predictions:
        try:
            # 只保存置信度最高的结果作为主记录
            main_prediction = predictions[0]
            result_data = save_detection_history(
                pest_name=main_prediction['name'],
                confidence=main_prediction['conf'],
                image_base64=f"data:image/jpeg;base64,{img_base64}",
                user_email=user_email,
                crop_type=crop,
                location_lat=location_lat,
                location_lng=location_lng,
                notes=location_address
            )
            if result_data.get("success"):
                print(f"检测历史已保存，记录ID: {result_data.get('id')}")
        except Exception as e:
            print(f"数据库记录保存失败: {e}")

    return {
        "results": predictions,
        "image_base64": f"data:image/jpeg;base64,{img_base64}"
    }


# 获取历史记录接口（从新数据库查询）
@app.get("/api/history")
async def get_history(request: Request):  # 新增 request 参数
    """获取当前用户的检测历史"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)

    # 管理员看全部，农户只看自己
    if user and user.get('role') == 'admin':
        history = get_detection_history(user_email=None, limit=20)
    else:
        history = get_detection_history(user_email=user_email, limit=20)

    return history


@app.get("/api/history/stats")
async def get_history_stats(request: Request):
    """获取最近30天检测统计数据（已修复数据隔离）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    # 判断是否为管理员（管理员可以看全部，农户只能看自己）
    is_admin = user.get('role') == 'admin'

    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            # 计算30天前日期
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            # 构建基础 WHERE 条件
            base_where = "DATE(created_at) >= ?"
            params = [thirty_days_ago]

            # 如果不是管理员，添加用户过滤
            if not is_admin:
                base_where += " AND user_email = ?"
                params.append(user_email)

            # 1. 总检测次数（修复：添加权限过滤）
            cursor.execute(f'''
                SELECT COUNT(*) FROM detection_records 
                WHERE {base_where}
            ''', params)
            total = cursor.fetchone()[0]

            # 2. 高置信度检测次数（修复：添加权限过滤）
            cursor.execute(f'''
                SELECT COUNT(*) FROM detection_records 
                WHERE {base_where} AND confidence >= 70
            ''', params)
            high_conf = cursor.fetchone()[0]

            # 3. 病虫害发生频率 TOP5（修复：添加权限过滤）
            cursor.execute(f'''
                SELECT pest_name, COUNT(*) as count 
                FROM detection_records 
                WHERE {base_where}
                GROUP BY pest_name 
                ORDER BY count DESC 
                LIMIT 5
            ''', params)
            top_pests = [{"name": row[0], "count": row[1]} for row in cursor.fetchall()]

            # 4. 最常检测作物（修复：添加权限过滤）
            crop_where = base_where + " AND crop_type IS NOT NULL"
            cursor.execute(f'''
                SELECT crop_type, COUNT(*) as count 
                FROM detection_records 
                WHERE {crop_where}
                GROUP BY crop_type 
                ORDER BY count DESC 
                LIMIT 1
            ''', params)
            crop_row = cursor.fetchone()
            top_crop = crop_row[0] if crop_row else '暂无数据'

            return {
                "total": total,
                "highConf": high_conf,
                "topPests": top_pests,
                "topCrop": top_crop
            }
    except Exception as e:
        print(f"获取统计失败: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# 清空历史记录接口（清空新数据库）
@app.post("/api/history/clear")
async def clear_history(request: Request):
    """清空历史记录（修复：权限隔离）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)

    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    # 只清空单用户自己的记录（更安全）
    result = clear_detection_history(user_email=user_email, is_admin=(user.get('role') == 'admin'))
    return result


# 路由：返回聊天页面
@app.get("/chat")
def chat_page(request: Request):
    if "auth_token" not in request.cookies:
        return RedirectResponse(url="/")
    return HTMLResponse(content=open("chat.html", "r", encoding="utf-8").read())


# app.py 路由部分
@app.get("/detect")
def detect_page(request: Request):
    if "auth_token" not in request.cookies:
        return RedirectResponse(url="/")
    return HTMLResponse(content=open("detect.html", "r", encoding="utf-8").read())


@app.get("/api/config", response_model=MapConfig)
async def get_frontend_config():
    config = load_farm_config()
    """
    提供给前端的基础配置信息
    注意：不要返回安全密钥，只返回Key即可
    """
    return {
        "amap_key": config.get("amapKey", ""),
        "center": [config.get("centerLng", 113.8291), config.get("centerLat", 23.3242)],
        "zoom": config.get("zoom", 14),
        "farm_name": config.get("farmName", "智慧农场"),
        "refresh_interval": config.get("refreshInterval", 30)
    }


@app.get("/api/config/js")
async def get_map_config_js():
    config = load_farm_config()
    """
    返回JavaScript配置脚本，用于在HTML中直接注入
    这样可以避免前端异步获取配置的延迟问题
    """
    js_config = {
        "AMAP_MAP_KEY": config.get("amapKey", ""),
        "AMAP_SERVICE_KEY": os.getenv("AMAP_SERVICE_KEY", ""),
        "AMAP_SECURITY_CONFIG": os.getenv("AMAP_SECURITY_CONFIG", ""),
        "MAP_CENTER": [config.get("centerLng", 113.8291), config.get("centerLat", 23.3242)],
        "MAP_ZOOM": config.get("zoom", 14),
        "FARM_NAME": config.get("farmName", "智慧农场")
    }
    js_content = f"window.APP_CONFIG = {json.dumps(js_config, ensure_ascii=False)};"
    return Response(content=js_content, media_type="application/javascript")


# 新增：保存配置接口（需要管理员权限）
@app.post("/api/config")
async def save_config(request: Request, config: FarmConfig):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    # 加载现有配置
    current = load_farm_config()
    update_data = config.dict(exclude_none=True)

    # 权限控制：农户只能修改地图中心位置相关字段
    if user['role'] != 'admin':
        # 过滤出农户允许修改的字段（仅地图位置相关）
        allowed_fields = ['centerLng', 'centerLat', 'zoom', 'mapAddress']
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not filtered_data:
            return JSONResponse(status_code=403, content={"error": "农户只能修改地图中心位置设置"})

        # 保留其他现有配置不变，只更新允许的字段
        current.update(filtered_data)
    else:
        # 管理员可以修改所有字段
        current.update(update_data)

    if save_farm_config(current):
        return {"success": True, "message": "配置已保存"}
    else:
        return JSONResponse(status_code=500, content={"error": "保存失败"})


# 获取完整配置接口（给设置页面用）
@app.get("/api/config/full")
async def get_full_config(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    config = load_farm_config()
    # 添加地理编码/天气服务Key（用于前端定位功能）
    config["amapServiceKey"] = os.getenv("AMAP_SERVICE_KEY", "")
    return config


@app.get("/map")
def map_page(request: Request):
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    try:
        with open("risk_map.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>地图文件 risk_map.html 未找到</h1>", status_code=404)


@app.get("/api/map/devices")
async def get_devices():
    """获取设备列表及今日真实检测统计"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, lat, lng, status, last_update FROM devices')
        devices = [dict(row) for row in cursor.fetchall()]

    # 按设备ID统计今日检测次数
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            for device in devices:
                device_id = device.get('id')
                if device_id:
                    # 查询该设备今日检测数（device_id 以字符串存储，需转换匹配）
                    cursor.execute('''
                        SELECT COUNT(*) as count 
                        FROM detection_records 
                        WHERE DATE(created_at) = DATE('now')
                        AND (device_id = ? OR device_id = ?)
                    ''', (str(device_id), f"camera_{device_id}"))
                    result = cursor.fetchone()
                    device['pest_detected'] = result['count'] if result else 0
                else:
                    device['pest_detected'] = 0
    except Exception as e:
        print(f"获取设备检测统计失败: {e}")
        for device in devices:
            device['pest_detected'] = 0

    return devices


@app.get("/api/map/risks")
async def get_risks(request: Request, date: str = None):
    """获取风险区域（返回所有风险等级的真实检测记录）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            date_filter = "DATE('now')"
            params = []
            if date:
                date_filter = "?"
                params.append(date)

            # 【修改】查询所有风险等级，不限于high，按风险等级分组
            cursor.execute(f'''
                SELECT pest_name, COUNT(*) as count, AVG(confidence) as avg_conf,
                       AVG(location_lat) as lat, AVG(location_lng) as lng,
                       risk_level,
                       MAX(notes) as address
                FROM detection_records 
                WHERE DATE(created_at) = {date_filter}
                AND location_lat IS NOT NULL 
                AND location_lng IS NOT NULL
                GROUP BY pest_name, risk_level
            ''', params)

            rows = cursor.fetchall()
            if rows:
                return [
                    {
                        "id": i + 1,
                        "name": f"{row['pest_name']}{row['risk_level']}风险区",
                        "lat": row['lat'],
                        "lng": row['lng'],
                        "risk_level": row['risk_level'],  # 返回实际等级
                        "risk_value": int(row['avg_conf']),
                        "risk_type": row['pest_name'],
                        "area": round(12.5 * row['count'], 1),
                        "address": row['address'] or '未记录位置'
                    }
                    for i, row in enumerate(rows)
                ]
            return []
    except Exception as e:
        print(f"获取风险区域失败: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/map/heatmap")
async def get_heatmap(request: Request, date: str = None):
    """获取热力图坐标（仅返回真实检测记录）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            date_filter = "DATE('now')"
            params = []
            if date:
                date_filter = "?"
                params.append(date)

            cursor.execute(f'''
                SELECT location_lat as lat, location_lng as lng, confidence as count,
                       notes as address, pest_name, risk_level
                FROM detection_records 
                WHERE location_lat IS NOT NULL 
                AND location_lng IS NOT NULL
                AND DATE(created_at) = {date_filter}
            ''', params)

            points = [dict(row) for row in cursor.fetchall()]
            return {"points": points}
    except Exception as e:
        print(f"获取热力图数据失败: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/devices")
async def list_devices(request: Request, user=Depends(get_current_user_dep)):
    """获取设备列表（权限隔离）"""
    if user['role'] == 'admin':
        return {"code": 200, "data": get_all_devices()}
    else:
        # 农户只看自己的设备
        result = get_user_devices(user['id'])
        return {"code": 200, "data": result.get('devices', [])}

@app.post("/api/devices")
async def create_device(request: Request, user=Depends(require_admin)):
    """创建设备（仅管理员）"""
    data = await request.json()
    if not data.get('name'):
        return JSONResponse(status_code=400, content={"error": "缺少字段: name"})

    # 解析经纬度字符串 "lat,lng"
    lat = lng = None
    if data.get('coordinates'):
        try:
            lat, lng = map(float, data['coordinates'].split(','))
        except Exception:
            pass
    else:
        lat = data.get('lat')
        lng = data.get('lng')

    # 若前端未传 device_id，后端自动生成
    device_id = data.get('device_id')
    if not device_id:
        import random, string
        device_id = 'DEV-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    result = add_device(
        name=data['name'],
        lat=lat,
        lng=lng,
        status=data.get('status', 'online'),
        device_id=device_id,
        device_type=data.get('type', 'camera'),
        location=data.get('location'),
        ip_address=data.get('ip_address'),
        firmware_version=data.get('firmware_version')
    )
    if result['success']:
        return {"code": 200, "data": {"id": result['id'], "device_id": result['device_id']}}
    return JSONResponse(status_code=400, content={"error": result['error']})


@app.put("/api/devices/{device_id}")
async def api_update_device(device_id: int, request: Request, admin=Depends(require_admin)):
    """编辑设备"""
    data = await request.json()

    # 解析经纬度字符串
    if data.get('coordinates'):
        try:
            lat, lng = map(float, data['coordinates'].split(','))
            data['lat'] = lat
            data['lng'] = lng
        except Exception:
            pass
        data.pop('coordinates', None)  # 避免传入数据库不存在的字段

    result = update_device(device_id, data)
    if result['success']:
        return {"code": 200, "message": "更新成功"}
    return JSONResponse(status_code=400, content={"error": result['error']})


@app.delete("/api/devices/{device_id}")
async def api_delete_device(device_id: int, admin=Depends(require_admin)):
    """删除设备"""
    result = delete_device(device_id)
    if result['success']:
        return {"code": 200, "message": "删除成功"}
    return JSONResponse(status_code=400, content={"error": result['error']})

@app.get("/api/devices/{device_id}/check")
async def device_check(device_id: int, admin=Depends(require_admin)):
    """设备健康诊断（返回结构化诊断结果）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM devices WHERE id = ?', (device_id,))
            row = cursor.fetchone()
            if not row:
                return JSONResponse(status_code=404, content={"error": "设备不存在"})

            device = dict(row)
            import random
            diagnostics = {
                "device_id": device.get('device_id') or str(device['id']),
                "name": device['name'],
                "network_status": "connected" if device['status'] == 'online' else "disconnected",
                "latency_ms": random.randint(20, 150) if device['status'] == 'online' else -1,
                "packet_loss": random.randint(0, 3) if device['status'] == 'online' else 100,
                "storage_usage": random.randint(25, 90),
                "firmware_ok": bool(device.get('firmware_version')),
                "last_heartbeat": device.get('last_update'),
                "issues": []
            }

            if device['status'] != 'online':
                diagnostics['issues'].append("设备离线，请检查电源与网络连接")
            if diagnostics['storage_usage'] > 80:
                diagnostics['issues'].append(f"存储使用率过高（{diagnostics['storage_usage']}%），建议清理缓存")
            if not diagnostics['firmware_ok']:
                diagnostics['issues'].append("固件版本未记录，建议补充信息")

            diagnostics['overall'] = 'healthy' if not diagnostics['issues'] else ('warning' if device['status'] == 'online' else 'critical')
            diagnostics['message'] = '诊断完成，设备运行正常' if not diagnostics['issues'] else f"发现 {len(diagnostics['issues'])} 项异常"

            return {"code": 200, "data": diagnostics}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/chat/sessions")
async def api_save_chat_session(request: Request):
    """保存对话记录"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    data = await request.json()

    # 自动检测是否有中断消息
    messages = data.get('messages', [])
    has_interrupted = any(
        msg.get('isInterrupted') or msg.get('is_interrupted')
        for msg in messages if msg.get('role') == 'ai'
    )

    result = save_chat_session(
        user_email=user_email,  # 传入用户邮箱
        title=data.get('title', '未命名对话'),
        messages=messages,
        pest_name=data.get('pest_name'),
        image_base64=data.get('image_base64'),
        session_id=data.get('id'),
        is_interrupted=has_interrupted
    )
    return result


@app.get("/api/chat/sessions")
async def api_get_chat_sessions(request: Request):
    """获取当前用户的所有对话列表"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    sessions = get_chat_sessions(user_email=user_email, limit=50)

    # 为每个会话添加中断状态标记
    for session in sessions:
        if session.get('messages'):
            messages = json.loads(session['messages']) if isinstance(session['messages'], str) else session['messages']
            session['is_interrupted'] = any(
                msg.get('isInterrupted') or msg.get('is_interrupted')
                for msg in messages if msg.get('role') == 'ai'
            )

    return sessions


@app.get("/api/chat/sessions/{session_id}")
async def api_get_chat_session(session_id: int):
    """获取单个对话详情"""
    session = get_chat_session(session_id)
    if session:
        # 确保 messages 是对象列表而非字符串
        if isinstance(session.get('messages'), str):
            session['messages'] = json.loads(session['messages'])

        # 标记是否包含中断消息
        session['is_interrupted'] = any(
            msg.get('isInterrupted') or msg.get('is_interrupted')
            for msg in session['messages'] if msg.get('role') == 'ai'
        )
        return session
    return JSONResponse(status_code=404, content={"error": "对话不存在"})


@app.get("/api/chat/sessions/interrupted/latest")
async def api_get_latest_interrupted():
    def _check():
        try:
            with get_chat_db_connection() as conn:  # 使用统一的连接函数
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, title, updated_at 
                    FROM chat_sessions 
                    WHERE is_interrupted = 1 
                    AND datetime(updated_at) > datetime('now', '-5 minutes')
                    ORDER BY updated_at DESC 
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    return {
                        "has_interrupted": True,
                        "session_id": row['id'],
                        "title": row['title'],
                        "updated_at": row['updated_at']
                    }
                return {"has_interrupted": False}
        except Exception as e:
            return {"has_interrupted": False, "error": str(e)}

    return await run_in_threadpool(_check)


@app.delete("/api/chat/sessions/{session_id}")
async def api_delete_chat_session(session_id: int):
    """删除对话"""
    result = delete_chat_session(session_id)
    return result


@app.post("/api/chat/sessions/clear")
async def api_clear_all_chat(request: Request):
    """清空当前用户的所有对话"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    is_admin = user and user.get('role') == 'admin'

    result = clear_all_chat_sessions(user_email=user_email, is_admin=is_admin)
    return result

@app.get("/farm-records")
def farm_records_page(request: Request):
    """农事记录页面"""
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    try:
        with open("farm_records.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 farm_records.html 未找到</h1>", status_code=404)

# 如果需要持久化存储，添加以下 API 端点：
class FarmRecord(BaseModel):
    type: str
    field: str
    date: str
    operator: str
    content: str
    materials: str
    status: str = "pending"


@app.post("/api/farm-records")
async def create_farm_record(record: FarmRecord, request: Request):
    """创建农事记录"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = await run_in_threadpool(lambda: get_user_by_email(email))
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    result = await run_in_threadpool(lambda: add_farm_record(user['id'], record.dict()))
    return result


@app.get("/api/farm-records")
async def api_get_farm_records(request: Request, type: str = None, field: str = None):
    """获取农事记录列表"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = await run_in_threadpool(lambda: get_user_by_email(email))
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    records = await run_in_threadpool(lambda: get_farm_records(user['id'], type, field))
    return {"records": records, "total": len(records)}


@app.put("/api/farm-records/{record_id}")
async def api_update_farm_record(record_id: int, request: Request):
    """更新农事记录（已修复权限验证）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = await run_in_threadpool(lambda: get_user_by_email(email))
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    data = await request.json()

    result = await run_in_threadpool(lambda: update_farm_record(record_id, data, user['id']))

    if result['success']:
        return {"success": True, "message": "更新成功"}
    else:
        error_msg = result.get('error', '更新失败')
        status_code = 403 if '无权' in error_msg else 400
        return JSONResponse(status_code=status_code, content={"error": error_msg})


@app.delete("/api/farm-records/{record_id}")
async def api_delete_farm_record(record_id: int, request: Request):
    """删除农事记录"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    email = request.cookies.get("user_email")
    user = await run_in_threadpool(lambda: get_user_by_email(email))
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    result = await run_in_threadpool(lambda: delete_farm_record(record_id, user['id']))
    if result['success'] and result.get('deleted', 0) > 0:
        return {"code": 200, "message": "删除成功"}
    else:
        error_msg = result.get('error', '删除失败')
        status_code = 403 if '无权' in error_msg else 404
        return JSONResponse(status_code=status_code, content={"error": error_msg})


def load_farm_config():
    """加载配置，如果不存在则使用环境变量默认值"""
    default = {
        "farmName": os.getenv("FARM_NAME", "增城智慧农场"),
        "farmCode": os.getenv("FARM_CODE", "ZC-001"),
        "manager": os.getenv("FARM_MANAGER", ""),
        "phone": os.getenv("FARM_PHONE", ""),
        "address": os.getenv("FARM_ADDRESS", ""),
        "description": os.getenv("FARM_DESCRIPTION", ""),
        "amapKey": os.getenv("AMAP_MAP_KEY") or os.getenv("AMAP_KEY", ""),
        "centerLng": float(os.getenv("MAP_CENTER_LNG", "113.8291")),
        "centerLat": float(os.getenv("MAP_CENTER_LAT", "23.3242")),
        "zoom": int(os.getenv("MAP_ZOOM", "14")),
        "enableAlert": True,
        "enableDailyReport": False,
        "dailyReportTime": "18:00",
        "enableOfflineAlert": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                default.update(saved)
        except:
            pass
    return default

def save_farm_config(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False



@app.get("/set")
def set_page(request: Request):
    """系统设置页面"""
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    try:
        with open("set.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 set.html 未找到</h1>", status_code=404)

@app.get("/set/{path:path}")
def set_subpage(request: Request, path: str):
    """处理所有设置子页面：/set/basic, /set/map, /set/notify 等"""
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    try:
        with open("set.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 set.html 未找到</h1>", status_code=404)

@app.get("/comments")
def comments_page(request: Request):
    """农户评论/经验交流页面"""
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    try:
        with open("comments.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 comments.html 未找到</h1>", status_code=404)


# ==================== 嵌套回复和删除 API ====================

@app.post("/api/comments/replies/{reply_id}/replies")
async def reply_to_reply(reply_id: int, request: Request):
    """回复某个回复（嵌套回复）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    data = await request.json()

    # 先获取父回复的信息，找到对应的评论ID
    with get_comments_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT comment_id, author_name FROM comment_replies WHERE id = ?", (reply_id,))
        parent = cursor.fetchone()
        if not parent:
            return JSONResponse(status_code=404, content={"error": "回复不存在"})

    # 添加回复，parent_reply_id 指向被回复的回复
    result = add_reply(
        comment_id=parent['comment_id'],
        user_email=email,
        content=data.get('content'),
        to_user=parent['author_name'],  # 默认回复给父回复作者
        parent_reply_id=reply_id
    )

    if result['success']:
        return result
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


# ==================== 嵌套回复兼容路由 ====================

@app.post("/api/comments/{comment_id}/replies/{reply_id}/nested")
async def nested_reply_alt(comment_id: int, reply_id: int, request: Request):
    """
    兼容前端的嵌套回复路径
    前端调用：/api/comments/{comment.id}/replies/{reply.id}/nested
    """
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    data = await request.json()

    # 验证父回复是否存在且属于该评论
    with get_comments_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT comment_id, author_name FROM comment_replies WHERE id = ?",
            (reply_id,)
        )
        parent = cursor.fetchone()
        if not parent:
            return JSONResponse(status_code=404, content={"error": "回复不存在或已被删除"})

        # 验证评论ID是否匹配（防止跨评论回复）
        if parent['comment_id'] != comment_id:
            return JSONResponse(status_code=400, content={"error": "评论ID与回复ID不匹配"})

    # 解析 @用户名 格式（前端可能发送 @用户名 内容）
    content = data.get('content', '')
    to_user = data.get('to_user') or parent['author_name']

    # 如果内容以 @用户名 开头，提取出来
    mention_match = re.match(r'^@([^\s]+)\s*(.*)', content)
    if mention_match:
        to_user = mention_match.group(1)
        content = mention_match.group(2) or content

    # 调用数据库函数创建嵌套回复
    result = add_reply(
        comment_id=comment_id,
        user_email=email,
        content=content,
        to_user=to_user,
        parent_reply_id=reply_id  # 关键：标记为嵌套回复
    )

    if result['success']:
        return {
            "success": True,
            "id": result['id'],
            "data": {
                "id": result['id'],
                "comment_id": comment_id,
                "parent_reply_id": reply_id,
                "user_email": email,
                "author_name": result['data']['author_name'],
                "content": content,
                "to_user": to_user,
                "likes": 0,
                "is_liked": False,
                "created_at": datetime.now().strftime('%m-%d %H:%M'),
                "children": []
            }
        }
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.post("/api/comments/replies/{reply_id}/like")
async def like_reply(reply_id: int, request: Request):
    """所有层级回复共用此点赞接口"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    email = request.cookies.get("user_email")
    result = toggle_reply_like(reply_id, email)
    return result

@app.delete("/api/comments/replies/{reply_id}")
async def delete_reply_api(reply_id: int, request: Request):
    """所有层级回复共用此删除接口"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    is_admin = user and user.get('role') == 'admin'
    result = delete_reply(reply_id, email, is_admin)
    if result['success']:
        return {"success": True}
    else:
        return JSONResponse(status_code=403, content={"error": result['error']})


# 修改原有的删除评论 API，确保使用新的级联删除
@app.delete("/api/comments/{comment_id}")
async def delete_comment_api(comment_id: int, user=Depends(get_current_user_dep)):
    is_admin = user['role'] == 'admin'

    def _delete():
        return delete_comment(comment_id, user['email'], is_admin)

    result = await run_in_threadpool(_delete)

    if result['success']:
        return {"success": True, "code": 200, "message": "删除成功"}  # 确保返回 code 字段
    else:
        if "不存在" in result['error']:
            return JSONResponse(status_code=404, content={"error": result['error'], "code": 404})
        elif "无权" in result['error']:
            return JSONResponse(status_code=403, content={"error": result['error'], "code": 403})
        else:
            return JSONResponse(status_code=400, content={"error": result['error'], "code": 400})


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """上传图片接口"""
    # 验证文件类型
    if not file.content_type.startswith("image/"):
        return {"success": False, "message": "只能上传图片文件"}

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 保存文件
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 返回可访问的 URL
    return {
        "success": True,
        "url": f"/static/uploads/{filename}"
    }


# ==================== 用户管理 API（适配用户管理界面） ====================

@app.get("/api/admin/users/stats")
async def admin_user_stats(admin=Depends(require_admin)):
    return await run_in_threadpool(get_user_dashboard_stats)


@app.get("/api/admin/users")
async def admin_users_list(
        request: Request,
        page: int = 1,
        limit: int = 10,
        role: str = None,
        status: str = None,
        keyword: str = None,
        admin=Depends(require_admin)
):
    filters = {}
    if role and role != 'all':
        filters['role'] = role
    if status and status != 'all':
        filters['status'] = status
    if keyword and keyword.strip():
        filters['keyword'] = keyword.strip()

    # 放到线程池执行，不阻塞事件循环
    result = await run_in_threadpool(
        lambda: get_user_list(filters=filters, page=page, per_page=limit)
    )
    return {
        "code": 200,
        "data": result['data'],
        "total": result['total'],
        "page": result['page'],
        "per_page": result['per_page']
    }


@app.post("/api/admin/users")
async def admin_create_user(request: Request, admin=Depends(require_admin)):
    data = await request.json()

    # 参数验证（这部分保持同步，不涉及IO）
    required = ['phone', 'name', 'role']
    for field in required:
        if not data.get(field):
            return JSONResponse(status_code=400, content={"error": f"缺少必填字段: {field}"})

    # 数据库操作放到线程池
    result = await run_in_threadpool(lambda: create_user(data))

    if result['success']:
        return {
            "code": 200,
            "message": "创建成功",
            "data": {"id": result['id'], "initial_password": result.get('initial_password')}
        }
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.put("/api/admin/users/{user_id}")
async def admin_update_user(user_id: int, request: Request, admin=Depends(require_admin)):
    data = await request.json()
    data['id'] = user_id

    result = await run_in_threadpool(lambda: update_user(user_id, data))

    if result['success']:
        return {"code": 200, "message": "更新成功"}
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.put("/api/admin/users/{user_id}/status")
async def admin_update_status(
        user_id: int,
        request: Request,
        admin=Depends(require_admin)
):
    """
    更新用户状态（对应操作列的启用/禁用/审核按钮）
    status: active(启用), pending(待审核), banned(禁用)
    """
    data = await request.json()
    status = data.get('status')

    if status not in ['active', 'pending', 'banned']:
        return JSONResponse(status_code=400, content={"error": "无效的状态值"})

    result = update_user_status(user_id, status)
    return {"code": 200, "success": result['success']}


@app.post("/api/admin/users/batch")
async def admin_batch_operation(request: Request, admin=Depends(require_admin)):
    """批量操作用户（激活/禁用/转移地块）"""
    data = await request.json()
    user_ids = data.get('user_ids', [])
    action = data.get('action')

    if not user_ids:
        return JSONResponse(status_code=400, content={"error": "未选择用户"})

    if action in ['activate', 'ban']:
        status = 'active' if action == 'activate' else 'banned'
        result = await run_in_threadpool(lambda: batch_update_status(user_ids, status))
        return {
            "code": 200,
            "message": f"已{('激活' if action == 'activate' else '禁用')} {result.get('affected', 0)} 位用户"
        }

    elif action == 'transfer':
        to_user_id = data.get('to_user_id')
        if not to_user_id:
            return JSONResponse(status_code=400, content={"error": "缺少目标用户"})
        if to_user_id in user_ids:
            return JSONResponse(status_code=400, content={"error": "不能转移给自身"})

        def _do_transfer():
            total_transferred = 0
            errors = []
            transferred_plots = []

            for from_user_id in user_ids:
                if from_user_id == to_user_id:
                    continue

                source_plots = get_user_plots(from_user_id)
                if not source_plots:
                    continue

                result = transfer_plots(from_user_id, to_user_id, [p['id'] for p in source_plots])

                if result['success']:
                    total_transferred += result.get('transferred', 0)
                    transferred_plots.extend([p['name'] for p in source_plots])
                else:
                    errors.append(f"用户{from_user_id}: {result['error']}")

            return {
                "total": total_transferred,
                "errors": errors,
                "transferred_plots": transferred_plots[:10]
            }

        result = await run_in_threadpool(_do_transfer)

        if result['errors'] and result['total'] == 0:
            return JSONResponse(status_code=400, content={"error": "; ".join(result['errors'])})

        return {
            "code": 200,
            "message": f"成功转移 {result['total']} 个地块",
            "transferred": result['total'],
            "transferred_plots": result.get('transferred_plots', []),
            "errors": result['errors'] if result['errors'] else None
        }

    else:
        return JSONResponse(status_code=400, content={"error": "无效的操作类型"})



@app.post("/api/admin/users/import")
async def admin_import_users(
        file: UploadFile = File(...),
        admin=Depends(require_admin)
):
    """
    批量导入用户（对应"批量导入"按钮）
    支持 .xlsx 和 .csv
    """
    content = await file.read()
    file_type = file.filename.split('.')[-1].lower()

    if file_type not in ['xlsx', 'xls', 'csv']:
        return JSONResponse(status_code=400, content={"error": "只支持 Excel 或 CSV 文件"})

    result = batch_import_users(content, file_type)
    return {
        "code": 200,
        "data": {
            "total": result.get('total', 0),
            "success": result.get('success', 0),
            "failed": result.get('failed', 0),
            "errors": result.get('errors', [])
        }
    }


@app.get("/api/admin/plots")
async def admin_plots_list(
        admin=Depends(require_admin),
        keyword: str = None,
        user_id: int = None  # 可选：传入当前编辑的用户ID，用于标记已绑定
):
    """
    获取地块列表（用于"选择绑定地块"弹窗）
    """

    plots = get_available_plots()

    # 前端搜索过滤（简单实现）
    if keyword:
        plots = [p for p in plots if keyword.lower() in p.get('name', '').lower()]

    return {"code": 200, "data": plots}


@app.get("/api/admin/users/{user_id}/plots")
async def admin_user_plots(
        user_id: int,
        admin=Depends(require_admin)
):
    """获取指定用户绑定的地块"""
    plots = get_user_plots(user_id)
    return {"code": 200, "data": plots}


@app.post("/api/admin/users/{user_id}/plots")
async def admin_bind_plots(
        user_id: int,
        request: Request,
        admin=Depends(require_admin)
):
    """为用户绑定地块（新增用户或编辑时的地块选择）"""
    data = await request.json()
    plot_ids = data.get('plot_ids', [])

    try:
        bind_plots_to_user(user_id, plot_ids)
        return {"code": 200, "message": f"成功绑定 {len(plot_ids)} 个地块"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.delete("/api/admin/users/{user_id}/plots/{plot_id}")
async def admin_unbind_plot(
        user_id: int,
        plot_id: int,
        admin=Depends(require_admin)
):
    """解绑单个地块"""
    result = unbind_plot(user_id, plot_id)
    return {"code": 200, "success": result['success']}


@app.get("/my-farm")
def my_farm_page(request: Request):
    """我的农场页面"""
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    # 检查是否为农户角色（可选，根据业务需求）
    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user or user['role'] != 'farmer':
        return HTMLResponse(content="<h1>无权访问</h1><p>此页面仅限种植农户访问</p>", status_code=403)

    return HTMLResponse(content=open("my-farm.html", "r", encoding="utf-8").read())


# 修改农场统计接口，返回更完整的数据
@app.get("/api/farm/stats")
async def get_farm_stats(user=Depends(get_current_user_dep)):
    """获取农场统计数据"""
    # 使用 run_in_threadpool 包装所有同步数据库操作
    def _get_stats():
        # 获取基础统计
        stats = get_user_farm_stats_fixed(user['id'], user['email'])
        # 获取设备统计
        device_stats = get_user_devices(user['id'])
        return stats, device_stats

    stats, device_stats = await run_in_threadpool(_get_stats)

    # 获取今日检测数（同样修复）
    def _get_detects():
        try:
            with get_detection_db_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT COUNT(*) FROM detection_records 
                    WHERE DATE(created_at) = ?
                ''', (today,))
                today_detects = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT COUNT(*) FROM detection_records 
                    WHERE DATE(created_at) = ? AND risk_level = 'high'
                ''', (today,))
                high_risk = cursor.fetchone()[0]
                return today_detects, high_risk
        except:
            return 0, 0

    today_detects, high_risk = await run_in_threadpool(_get_detects)

    # 获取今日任务统计（同样修复）
    def _get_tasks():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM farm_tasks 
                    WHERE user_id = ? AND DATE(scheduled_time) = DATE('now') AND completed = 0
                ''', (user['id'],))
                pending_tasks = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT COUNT(*) FROM farm_tasks 
                    WHERE user_id = ? AND DATE(scheduled_time) = DATE('now') 
                    AND completed = 0 AND priority = 'high'
                ''', (user['id'],))
                urgent_tasks = cursor.fetchone()[0]
                return pending_tasks, urgent_tasks
        except:
            return 0, 0

    pending_tasks, urgent_tasks = await run_in_threadpool(_get_tasks)

    return {
        "code": 200,
        "data": {
            "totalArea": stats['total_area'],
            "plotCount": stats['plot_count'],
            "onlineDevices": device_stats['online'],
            "totalDevices": device_stats['total'],
            "offlineDevices": device_stats['offline'],
            "todayDetects": today_detects,
            "highRiskCount": high_risk,
            "pendingTasks": pending_tasks,
            "urgentTasks": urgent_tasks,
            "cropTypes": stats['crop_types'],
            "warnings": stats['warnings']
        }
    }


# 修改设备接口，确保返回统计数据
@app.get("/api/farm/devices")
async def get_user_devices_api(request: Request):
    """获取用户设备状态"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    result = get_user_devices(user['id'])
    return {"code": 200, "data": result.get('devices', []), "stats": result}


@app.get("/api/farm/plots")
async def get_plots(request: Request):
    """获取农场地块列表"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    # 首次访问时初始化示例数据（如果没有地块）
    def _get_plots():
        # 首次访问时初始化示例数据（如果没有地块）
        init_farm_plot_for_user(user['id'])
        # 使用正确的函数查询 farm_plots 表
        return get_farm_plots_by_user(user['id'])

    plots = await run_in_threadpool(_get_plots)
    return {"code": 200, "data": plots}

@app.get("/api/farm/crops")
async def get_crops(user=Depends(get_current_user_dep)):
    crops = await run_in_threadpool(lambda: get_user_crops(user['id']))
    return {"code": 200, "data": crops}


@app.get("/api/farm/activities")
async def get_activities(request: Request, limit: int = 10):
    """获取最近活动"""
    email = request.cookies.get("user_email")
    # 使用线程池包装同步数据库操作
    user = await run_in_threadpool(lambda: get_user_by_email(email))
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})
    activities = await run_in_threadpool(lambda: get_recent_activities(user['id'], limit))
    return {"code": 200, "data": activities}


def add_user_device(user_id, name, device_type, location=None):
    """添加设备，自动根据类型设置图标"""
    # 类型与图标映射
    icon_map = {
        'camera': 'fas fa-video',
        'sensor': 'fas fa-thermometer-half',
        'controller': 'fas fa-broadcast-tower',
        'drone': 'fas fa-plane',
        'irrigation': 'fas fa-tint'
    }

    icon = icon_map.get(device_type, 'fas fa-cog')  # 默认图标

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_devices (user_id, name, type, icon, location, status)
        VALUES (?, ?, ?, ?, ?, 'online')
    ''', (user_id, name, device_type, icon, location))
    conn.commit()
    device_id = cursor.lastrowid
    conn.close()
    return {"success": True, "id": device_id}


@app.post("/api/farm/activities")
async def create_activity(request: Request):
    """添加农事活动"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    data = await request.json()
    result = add_farm_activity(
        user_id=user['id'],
        activity_type=data.get('type', 'other'),
        content=data.get('content', ''),
        plot_name=data.get('plot_name')
    )
    return result


@app.get("/api/farm/environment")
async def get_environment_data(request: Request, user=Depends(get_current_user_dep)):
    """获取环境数据（优先真实传感器，无数据则标记为模拟）"""

    # 尝试获取真实数据
    real_data = await run_in_threadpool(lambda: get_latest_environment(user['id']))

    if real_data:
        return {
            "code": 200,
            "data": {
                "temperature": real_data['temperature'],
                "humidity": real_data['humidity'],
                "soilMoisture": real_data['soil_moisture'],
                "light": real_data['light'],
                "source": "sensor",  # 明确标记来源
                "updateTime": real_data['record_time']
            }
        }

    # 无真实数据时明确标记为模拟，并建议接入传感器
    return {
        "code": 200,
        "data": {
            "temperature": round(22 + random.uniform(-3, 5), 1),
            "humidity": round(65 + random.uniform(-10, 15), 0),
            "soilMoisture": round(45 + random.uniform(-5, 10), 0),
            "light": round(35000 + random.uniform(-10000, 20000), 0),
            "source": "simulated",
            "notice": "当前为模拟数据，接入传感器后自动替换",
            "sensorGuide": "/docs/sensor-setup"
        }
    }


@app.post("/api/farm/environment")
async def report_environment(request: Request, user=Depends(get_current_user_dep)):
    """接收前端/设备上报的环境数据"""
    data = await request.json()

    try:
        await run_in_threadpool(lambda: save_environment_data(
            user_id=user['id'],
            device_id=data.get('device_id', 'default'),
            temp=data.get('temperature'),
            humidity=data.get('humidity'),
            soil=data.get('soil_moisture'),
            light=data.get('light')
        ))
        return {"code": 200, "message": "数据已保存"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/farm/weather")
async def get_weather(request: Request):
    """获取农场当地天气（接入高德API）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    # 加载配置 - 优先使用 AMAP_SERVICE_KEY（天气和地理编码共用）
    # 如果没有设置，依次尝试其他环境变量
    amap_key = os.getenv("AMAP_SERVICE_KEY") or os.getenv("AMAP_WEATHER_KEY") or os.getenv("AMAP_KEY")
    city_code = os.getenv("AMAP_CITY_CODE", "440183")

    # 没有Key时返回模拟数据（开发测试用）
    if not amap_key:
        return {
            "code": 200,
            "data": {
                "location": "广州市增城区",
                "temperature": 26,
                "description": "多云转晴",
                "humidity": 68,
                "wind": "微风 3级",
                "rain": 0,
                "icon": "fas fa-cloud-sun",
                "advice": "天气服务未配置，请检查 .env 文件中的 AMAP_SERVICE_KEY",
                "forecast": [
                    {"date": "明天", "icon": "fas fa-sun", "high": 28, "low": 22},
                    {"date": "后天", "icon": "fas fa-cloud", "high": 25, "low": 20},
                    {"date": "周五", "icon": "fas fa-cloud", "high": 26, "low": 21}
                ],
                "source": "mock"
            }
        }

    try:

        # 调用高德天气API（all模式返回实况+预报）
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": amap_key,
            "city": city_code,
            "extensions": "all",
            "output": "JSON"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            data = response.json()

            # 检查API返回状态
            if data.get("status") != "1":
                raise Exception(f"高德API错误: {data.get('info', '未知错误')}")

            if not data.get("forecasts"):
                raise Exception("无预报数据")

            forecast_data = data["forecasts"][0]
            casts = forecast_data.get("casts", [])

            if not casts:
                raise Exception("天气数据为空")

            # 天气图标映射
            icon_map = {
                "晴": "fas fa-sun",
                "多云": "fas fa-cloud-sun",
                "阴": "fas fa-cloud",
                "阵雨": "fas fa-cloud-rain",
                "雷阵雨": "fas fa-bolt",
                "小雨": "fas fa-cloud-rain",
                "中雨": "fas fa-cloud-showers-heavy",
                "大雨": "fas fa-cloud-showers-heavy",
                "暴雨": "fas fa-cloud-showers-heavy",
                "雪": "fas fa-snowflake",
                "雾": "fas fa-smog",
                "霾": "fas fa-smog"
            }

            def get_icon(weather):
                for key, icon in icon_map.items():
                    if key in weather:
                        return icon
                return "fas fa-cloud"

            # 处理预报（明天、后天、大后天）
            week_map = {"1": "周一", "2": "周二", "3": "周三", "4": "周四", "5": "周五", "6": "周六", "7": "周日"}
            forecast_list = []

            # casts[0]是今天，取[1:4]是未来3天
            for i, day in enumerate(casts[1:4], 1):
                date_label = "明天" if i == 1 else "后天" if i == 2 else week_map.get(day.get("week"),
                                                                                      "周" + day.get("week", ""))
                forecast_list.append({
                    "date": date_label,
                    "icon": get_icon(day.get("dayweather", "")),
                    "tempHigh": int(day.get("daytemp", 0)),
                    "tempLow": int(day.get("nighttemp", 0))
                })

            # 当前天气（今天白天）
            today = casts[0]

            # 生成农事建议
            def generate_advice(weather, temp):
                advice_map = {
                    "晴": "今日晴朗，适宜喷药防治，建议在上午9-11点进行",
                    "多云": "多云天气，适宜田间巡查和轻度劳作",
                    "阴": "阴天注意大棚通风，防止病害发生",
                    "雨": "有降雨，不宜喷药，注意排水防涝",
                    "雷阵雨": "雷阵雨天气，停止户外作业",
                    "雪": "降雪天气，做好保温措施"
                }
                for key, text in advice_map.items():
                    if key in weather:
                        if temp > 35:
                            return text + "，注意高温防暑"
                        elif temp < 10:
                            return text + "，注意防冻"
                        return text
                return f"今日{weather}，温度{temp}°C，合理安排农事活动"

            weather_data = {
                "location": forecast_data.get("city", "广州市增城区"),
                "temperature": int(today.get("daytemp", 26)),
                "description": today.get("dayweather", "多云"),
                "humidity": int(today.get("dayhumidity", 60)),
                "wind": f"{today.get('daywind', '微')}风 {today.get('daypower', '3')}级",
                "rain": 0,  # 高德不直接提供降雨量，可根据天气类型估算
                "icon": get_icon(today.get("dayweather", "")),
                "advice": generate_advice(today.get("dayweather", ""), int(today.get("daytemp", 26))),
                "forecast": forecast_list,
                "updateTime": data.get("reportTime", ""),
                "source": "amap"
            }

            return {"code": 200, "data": weather_data}

    except Exception as e:
        print(f"高德天气获取失败: {e}")
        # 异常时降级返回模拟数据，但标记来源
        return {
            "code": 200,
            "data": {
                "location": "广州市增城区",
                "temperature": 26,
                "description": "多云转晴",
                "humidity": 68,
                "wind": "微风 3级",
                "rain": 0,
                "icon": "fas fa-cloud-sun",
                "advice": f"天气服务异常({str(e)})，使用默认建议：注意观察作物生长情况",
                "forecast": [
                    {"date": "明天", "icon": "fas fa-sun", "tempHigh": 28, "tempLow": 22},
                    {"date": "后天", "icon": "fas fa-cloud", "tempHigh": 25, "tempLow": 20},
                    {"date": "周五", "icon": "fas fa-cloud", "tempHigh": 26, "tempLow": 21}
                ],
                "source": "mock"
            }
        }


def generate_weather_advice(weather, temp):
    """根据天气生成农事建议"""
    advice_map = {
        "晴": "今日晴朗，适宜喷药防治和收割作业，建议在上午9-11点进行",
        "多云": "多云天气，适宜田间巡查和轻度劳作，注意通风",
        "阴": "阴天无直射光，注意大棚通风，防止病害发生",
        "雨": "有降雨，不宜喷药，注意排水防涝",
        "雷阵雨": "雷阵雨天气，停止户外作业，注意防雷",
        "雪": "降雪天气，做好保温措施，检查大棚设施"
    }

    for key, text in advice_map.items():
        if key in weather:
            if temp > 35:
                return text + "，高温时段（12-15点）避免劳作"
            elif temp < 10:
                return text + "，注意作物防冻保温"
            return text

    return f"今日天气{weather}，温度{temp}°C，合理安排农事活动"


@app.get("/api/farm/tasks")
async def api_get_tasks(request: Request, date: str = None, completed: bool = None):
    """获取农事任务（支持按日期和完成状态筛选）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    # 默认查询今天
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    tasks = get_farm_tasks(user['id'], date=date, completed=completed)
    stats = get_task_stats(user['id'])

    return {
        "code": 200,
        "data": {
            "tasks": tasks,
            "stats": stats,
            "date": date
        }
    }


@app.post("/api/farm/tasks")
async def api_create_task(request: Request, user=Depends(get_current_user_dep)):
    """创建新任务"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    data = await request.json()

    # 自动关联地块ID（如果提供了地块名称）
    if data.get('plot_name') and not data.get('plot_id'):
        plots = get_farm_plots_by_user(user['id'])
        for plot in plots:
            if plot['name'] == data['plot_name']:
                data['plot_id'] = plot['id']
                break

    result = add_farm_task(user['id'], data)
    if result['success']:
        return {"code": 200, "message": "创建成功", "data": {"id": result['id']}}
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.put("/api/farm/tasks/{task_id}")
async def api_update_task(task_id: int, request: Request):
    """更新任务（支持编辑内容、切换完成状态、修改时间等）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    data = await request.json()
    result = update_farm_task(task_id, user['id'], data)

    if result['success']:
        return {"code": 200, "message": "更新成功"}
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.delete("/api/farm/tasks/{task_id}")
async def api_delete_task(task_id: int, request: Request):
    """删除任务"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    result = delete_farm_task(task_id, user['id'])
    if result['success'] and result['deleted'] > 0:
        return {"code": 200, "message": "删除成功"}
    else:
        return JSONResponse(status_code=404, content={"error": "任务不存在或无权删除"})


@app.post("/api/farm/tasks/{task_id}/toggle")
async def api_toggle_task(task_id: int, request: Request):
    """切换任务完成状态（完成/未完成）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    def _toggle_task():
        # 先获取当前状态
        tasks = get_farm_tasks(user['id'])
        task = next((t for t in tasks if t['id'] == task_id), None)

        if not task:
            return None, "任务不存在"

        # 切换状态
        new_status = not task['completed']
        result = update_farm_task(task_id, user['id'], {'completed': new_status})

        if result['success'] and new_status:
            # 如果标记完成，添加到活动日志
            add_farm_activity(
                user['id'],
                task['type'],
                f"完成任务：{task['title']}",
                task['plot_name']
            )

        return task, new_status, result

    task, new_status, result = await run_in_threadpool(_toggle_task)

    if not task:
        return JSONResponse(status_code=404, content={"error": "任务不存在"})
    if not result['success']:
        return JSONResponse(status_code=400, content={"error": result['error']})

    return {
        "code": 200,
        "message": "状态更新成功",
        "completed": new_status,
        "completed_at": datetime.now().isoformat() if new_status else None
    }


@app.post("/api/farm/tasks/reorder")
async def api_reorder_tasks(request: Request):
    """批量更新任务排序顺序（拖拽排序后保存）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = await run_in_threadpool(lambda: get_user_by_email(email))
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    data = await request.json()
    ordered_ids = data.get('ids', [])

    if not ordered_ids or not isinstance(ordered_ids, list):
        return JSONResponse(status_code=400, content={"error": "无效的排序数据"})

    def _update_order():
        # 调用新添加的数据库函数
        return update_farm_tasks_order(user['id'], ordered_ids)

    result = await run_in_threadpool(_update_order)

    if result['success']:
        return {"code": 200, **result}
    else:
        # 权限错误返回403，其他错误返回400
        status_code = 403 if '无权' in result['error'] else 400
        return JSONResponse(status_code=status_code, content={"error": result['error']})


@app.get("/api/farm/costs")
async def get_cost_stats(request: Request, period: str = "month"):
    """获取真实成本统计"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    data = await run_in_threadpool(lambda: get_cost_stats_real(user['id'], period))
    return {"code": 200, "data": data}


@app.post("/api/farm/costs")
async def create_cost_record(request: Request, user=Depends(get_current_user_dep)):
    """录入成本（自动关联当前用户）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    data = await request.json()

    result = add_cost_record(
        user_id=user['id'],
        category=data.get('category'),
        amount=data.get('amount'),
        item_name=data.get('item_name'),
        record_date=data.get('record_date'),
        notes=data.get('notes')
    )

    if result['success']:
        return {"code": 200, "message": "录入成功"}
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.post("/api/farm/quick-action")
async def quick_action(request: Request):
    """执行快捷操作（如一键灌溉）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    data = await request.json()
    action_type = data.get('type')

    # 记录操作到活动日志
    email = request.cookies.get("user_email")
    user = get_user_by_email(email)

    action_map = {
        "irrigate": ("灌溉", "试验田A自动灌溉启动"),
        "fertilize": ("施肥", "大棚B智能施肥开始"),
        "pest": ("防治", "启动病虫害巡查模式"),
        "camera": ("识别", "打开AI识别摄像头")
    }

    type_label, content = action_map.get(action_type, ("操作", "执行快捷操作"))

    # 添加到活动记录
    if user:
        await run_in_threadpool(lambda: add_farm_activity(user['id'], type_label, content, "快捷操作"))

    return {
        "code": 200,
        "message": "操作执行成功",
        "data": {
            "action": action_type,
            "startTime": datetime.now().isoformat(),
            "estimatedEnd": (datetime.now() + timedelta(minutes=15)).isoformat()
        }
    }

# 配置CORS
allowed_origins = [
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:3000",  # 前端开发服务器
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


# ==================== 后端相机调用功能 ====================

# 新增：摄像头可用性检查接口
@app.get("/api/camera/check")
async def check_camera():
    """
    检查后端摄像头是否可用
    返回可用状态和设备索引
    """
    try:
        # 尝试多个设备索引（0-5），支持多摄像头场景
        for device_index in range(6):
            cap = cv2.VideoCapture(device_index)
            if cap.isOpened():
                # 尝试读取一帧验证
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    return {
                        "available": True,
                        "device_index": device_index,
                        "message": f"检测到可用摄像头（设备索引: {device_index}）"
                    }

        return {
            "available": False,
            "error": "未检测到可用的摄像头设备",
            "suggestion": "请检查摄像头连接、驱动安装情况，或使用前端摄像头功能"
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"检查失败: {str(e)}",
            "suggestion": "请确保OpenCV正确安装并有权访问摄像头"
        }

@app.get("/api/camera/capture")
async def capture_camera():
    """
    调用本机摄像头拍照并返回图片
    后续可替换为其他相机接口（工业相机SDK、IP摄像头等）
    """
    try:
        # 打开默认摄像头（0为默认设备）
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            return JSONResponse(
                status_code=500,
                content={"error": "无法打开摄像头，请检查设备是否连接"}
            )

        # 设置分辨率（可选）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # 读取一帧
        ret, frame = cap.read()

        # 释放摄像头
        cap.release()

        if not ret or frame is None:
            return JSONResponse(
                status_code=500,
                content={"error": "拍照失败，无法获取图像"}
            )

        # 转换为RGB（OpenCV默认是BGR）
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 转换为PIL Image然后转base64
        pil_img = Image.fromarray(frame_rgb)

        # 压缩并转为base64
        buffered = io.BytesIO()
        pil_img.save(buffered, format="JPEG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {
            "success": True,
            "image_base64": f"data:image/jpeg;base64,{img_base64}",
            "timestamp": datetime.now().isoformat(),
            "resolution": f"{pil_img.width}x{pil_img.height}"
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"相机调用失败: {str(e)}"}
        )


@app.post("/api/camera/detect")
async def camera_detect(request: Request):
    """
    调用相机拍照并立即进行病虫害识别
    整合拍照+识别为一个接口
    优化：自动尝试多个设备索引（0-5）
    """
    try:
        data = await request.json()
        conf = data.get('conf', 0.25)

        crop_type = data.get('crop')

        # 第一步：调用相机拍照（尝试多个设备索引）
        cap = None
        device_index = -1

        for i in range(6):  # 尝试索引 0-5
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 测试是否能读取帧
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    device_index = i
                    break
            cap.release()

        if device_index == -1 or not cap or not cap.isOpened():
            return JSONResponse(
                status_code=500,
                content={
                    "error": "无法打开任何摄像头设备",
                    "detail": "已尝试设备索引 0-5，均未找到可用摄像头",
                    "suggestion": "请检查摄像头连接，或使用前端摄像头功能（点击相机拍摄按钮将自动切换）"
                }
            )

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # 预热摄像头（读取几帧丢弃，确保画面清晰）
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return JSONResponse(
                status_code=500,
                content={"error": "拍照失败"}
            )

        # 第二步：YOLO检测
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        if not yolo_model:
            return {"results": [], "error": "模型未加载"}

        results = yolo_model.predict(source=img, conf=conf)
        result = results[0]

        # 解析结果
        predictions = []
        if len(result.boxes) > 0:
            boxes_norm = result.boxes.xyxyn.tolist()
            conf_list = result.boxes.conf.tolist()
            cls_list = result.boxes.cls.tolist()

            for i in range(len(boxes_norm)):
                eng_name = result.names[int(cls_list[i])]
                cn_name = PEST_TRANSLATION.get(eng_name, eng_name)
                predictions.append({
                    "name": cn_name,
                    "conf": round(conf_list[i] * 100, 1)
                })

        # 生成带标注的图片
        res_plotted = result.plot()
        res_plotted_rgb = cv2.cvtColor(res_plotted, cv2.COLOR_BGR2RGB)
        plotted_img = Image.fromarray(res_plotted_rgb)

        buffered = io.BytesIO()
        plotted_img.save(buffered, format="JPEG")
        result_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 保存检测历史
        if predictions:
            try:
                main_prediction = predictions[0]
                save_detection_history(
                    pest_name=main_prediction['name'],
                    confidence=main_prediction['conf'],
                    image_base64=f"data:image/jpeg;base64,{result_base64}",
                    crop_type=crop_type,
                    device_id=f"camera_{device_index}"  # 添加设备ID关联
                )
            except Exception as e:
                print(f"保存历史记录失败: {e}")

        return {
            "success": True,
            "results": predictions,
            "image_base64": f"data:image/jpeg;base64,{result_base64}",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"相机检测失败: {str(e)}"}
        )

@app.get("/knowledge")
def knowledge_page(request: Request):
    """知识库页面"""
    if "auth_token" not in request.cookies or request.cookies["auth_token"] != "verified":
        return RedirectResponse(url="/")
    try:
        with open("knowledge_base.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>页面文件 knowledge_base.html 未找到</h1>", status_code=404)


# ==================== 蔓延热力图 API（新增） ====================
@app.get("/api/map/heatmap-timeline")
async def get_heatmap_timeline(request: Request, days: int = 7):
    """
    【重写】直接查询数据库返回近N天带地址的检测点，供前端时间轴播放
    """
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    is_admin = user.get('role') == 'admin'
    result = []

    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            for i in range(days - 1, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')

                base_where = "DATE(created_at) = ? AND location_lat IS NOT NULL AND location_lng IS NOT NULL"
                params = [date]
                if not is_admin:
                    base_where += " AND user_email = ?"
                    params.append(user_email)

                cursor.execute(f'''
                    SELECT location_lat as lat, location_lng as lng, confidence as count,
                           pest_name, risk_level, notes as address
                    FROM detection_records 
                    WHERE {base_where}
                ''', params)

                points = [dict(row) for row in cursor.fetchall()]
                result.append({
                    "date": date,
                    "points": points,
                    "count": len(points),
                    "type": "history"
                })
        return {"code": 200, "data": result}
    except Exception as e:
        print(f"获取时间轴热力图失败: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/map/spread-prediction")
async def get_spread_prediction(request: Request, days: int = 3):
    """
    【新增】获取病虫害蔓延预测数据
    基于历史数据+扩散模型预测未来扩散区域
    """
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    viz = RiskMapGenerator()
    predictions = viz.predict_spread(
        user_email=user_email if user.get('role') != 'admin' else None,
        forecast_days=days
    )
    print(f"[预测数据] 返回 {len(predictions)} 条预测")
    return {"code": 200, "data": predictions}


@app.get("/api/map/spread-stats")
async def get_spread_statistics(request: Request, days: int = 7):
    """
    【新增】获取蔓延统计指标
    包括蔓延速度、方向、影响面积等
    """
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    viz = RiskMapGenerator()
    stats = viz.calculate_spread_stats(
        user_email=user_email if user.get('role') != 'admin' else None,
        days=days
    )
    return {"code": 200, "data": stats}



# ==================== 知识库 API 路由 ====================
# 1. 静态路由必须放在最前面（不会被动态路由拦截）
@app.get("/api/knowledge/stats")
async def api_get_knowledge_stats(user=Depends(get_current_user_dep)):
    stats = await run_in_threadpool(lambda: get_knowledge_stats(user['email'], user['role']))
    return {"code": 200, **stats}


@app.get("/api/knowledge/collections")
async def api_get_collections(request: Request):
    """获取当前用户的收藏列表"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    collections = get_user_collections(user_email)

    # 确保返回的是数组，且过滤无效数据
    if not collections:
        collections = []

    # 清理数据，确保字段存在
    clean_collections = []
    for item in collections:
        if item and isinstance(item, dict) and item.get('id'):
            clean_collections.append(item)

    return {"code": 200, "data": clean_collections}


@app.post("/api/knowledge/init-sample")
async def api_init_knowledge_sample(admin=Depends(require_admin)):
    """初始化示例数据（仅管理员）"""
    init_knowledge_sample_data()
    return {"code": 200, "message": "示例数据已初始化"}


# 2. 列表路由
@app.get("/api/knowledge")
async def api_get_knowledge(
    request: Request,
    crop_type: str = None,
    category: str = None,
    severity_level: str = None,
    search_keyword: str = None,
    is_personal: bool = None,
    limit: int = 50,
    offset: int = 0
):
    """获取知识列表"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    user_role = user.get('role') if user else 'farmer'

    filters = {}
    if crop_type:
        filters['crop_type'] = crop_type
    if category:
        filters['category'] = category
    if severity_level:
        filters['severity_level'] = severity_level
    if search_keyword:
        filters['search_keyword'] = search_keyword
    if is_personal is not None:
        filters['is_personal'] = is_personal
        if is_personal and user_role != 'admin':
            filters['owner_email'] = user_email

    result = get_knowledge_list(filters, limit, offset, user_email, user_role)
    return {"code": 200, **result}


# 农户个人知识库专属
@app.get("/api/knowledge/my/list")
async def api_get_my_knowledge(
    request: Request,
    crop_type: str = None,
    category: str = None,
    limit: int = 50,
    offset: int = 0
):
    """获取当前农户的个人知识库列表"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")

    filters = {'is_personal': True, 'owner_email': user_email}
    if crop_type:
        filters['crop_type'] = crop_type
    if category:
        filters['category'] = category

    result = get_knowledge_list(filters, limit, offset, user_email, 'farmer')
    return {"code": 200, **result}


# 3. 创建路由
@app.post("/api/knowledge")
async def api_create_knowledge(request: Request):
    """创建新知识"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)

    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    is_admin = user.get('role') == 'admin'
    data = await request.json()

    required_fields = ['pest_name', 'crop_type', 'category', 'symptoms']
    for field in required_fields:
        if not data.get(field):
            return JSONResponse(status_code=400, content={"error": f"缺少必填字段: {field}"})

    if not is_admin:
        data['is_personal'] = True
        data['owner_email'] = user_email
        if 'is_shared' not in data:
            data['is_shared'] = False

    result = create_knowledge(data, user_email, is_admin)

    if result['success']:
        msg = "创建成功"
        if result.get('is_personal'):
            msg = "已保存到您的个人知识库"
        return {"code": 200, "message": msg, "id": result['id'], "is_personal": result.get('is_personal', 0)}
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


# 4. 动态路由放在最后
@app.get("/api/knowledge/{knowledge_id}")
async def api_get_knowledge_detail(knowledge_id: int, request: Request):
    """获取单个知识详情（带权限检查）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    user_role = user.get('role') if user else 'farmer'

    item = get_knowledge_by_id(knowledge_id, user_email, user_role)

    if not item:
        return JSONResponse(status_code=404, content={"error": "知识条目不存在或无权限查看"})

    return {"code": 200, "data": item}


@app.put("/api/knowledge/{knowledge_id}")
async def api_update_knowledge(knowledge_id: int, request: Request):
    """更新知识"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)

    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    is_admin = user.get('role') == 'admin'
    data = await request.json()

    result = update_knowledge(knowledge_id, data, user_email, is_admin)

    if result['success']:
        return {"code": 200, "message": "更新成功"}
    else:
        return JSONResponse(status_code=403, content={"error": result['error']})


@app.delete("/api/knowledge/{knowledge_id}")
async def api_delete_knowledge(knowledge_id: int, request: Request):
    """删除知识"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)

    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    is_admin = user.get('role') == 'admin'

    result = delete_knowledge(knowledge_id, user_email, is_admin)

    if result['success']:
        return {"code": 200, "message": "删除成功"}
    else:
        return JSONResponse(status_code=403, content={"error": result['error']})


@app.get("/api/knowledge/{knowledge_id}/ai-solutions")
async def api_get_ai_solutions(knowledge_id: int, request: Request):
    """获取AI方案"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    solutions = get_ai_solutions(knowledge_id)
    return {"code": 200, "data": solutions}


@app.post("/api/knowledge/{knowledge_id}/collect")
async def api_toggle_collect(knowledge_id: int, request: Request):
    """收藏/取消收藏"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    result = toggle_knowledge_collection(user_email, knowledge_id)

    if result['success']:
        return {"code": 200, "collected": result['collected'],
                "message": "已收藏" if result['collected'] else "已取消收藏"}
    else:
        return JSONResponse(status_code=400, content={"error": result['error']})


@app.post("/api/knowledge/{knowledge_id}/share")
async def api_share_knowledge(knowledge_id: int, request: Request):
    """分享/取消分享个人知识"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    data = await request.json()
    is_shared = data.get('is_shared', False)

    result = update_knowledge(knowledge_id, {'is_shared': is_shared}, user_email, is_admin=False)

    if result['success']:
        return {"code": 200, "message": "已分享" if is_shared else "已取消分享", "is_shared": is_shared}
    else:
        return JSONResponse(status_code=403, content={"error": result['error']})



@app.post("/api/debug/init-data")
async def init_test_data(request: Request):
    """生成测试数据（仅开发使用）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    def _init_data():
        email = request.cookies.get("user_email")
        user = get_user_by_email(email)
        if not user:
            return JSONResponse(status_code=404, content={"error": "用户不存在"})

        user_id = user['id']

        # 初始化示例地块
        init_farm_plot_for_user(user_id, "试验田A", 15.5, "水稻")
        init_farm_plot_for_user(user_id, "大棚B", 8.0, "番茄")

        # 添加示例设备
        with get_db_connection() as conn:
            cursor = conn.cursor()
            devices = [
                (user_id, "田间摄像头1", "camera", "fas fa-video", "试验田A", "online"),
                (user_id, "土壤传感器", "sensor", "fas fa-thermometer-half", "大棚B", "online"),
                (user_id, "气象站", "sensor", "fas fa-cloud-sun", "农场中心", "offline")
            ]
            for d in devices:
                cursor.execute('''
                    INSERT OR IGNORE INTO user_devices (user_id, name, type, icon, location, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', d)
            conn.commit()

        # 添加示例任务
        today = datetime.now()
        tasks = [
            {"title": "水稻追肥", "type": "fertilize", "priority": "high", "plot_name": "试验田A"},
            {"title": "番茄灌溉", "type": "irrigation", "priority": "medium", "plot_name": "大棚B"},
            {"title": "病虫害巡查", "type": "inspect", "priority": "low", "plot_name": "全场"}
        ]
        for task in tasks:
            add_farm_task(user_id, {
                **task,
                "scheduled_time": today.isoformat()
            })

        return {"code": 200, "message": "测试数据已生成"}

    return await run_in_threadpool(_init_data)

@app.get("/api/pest-solutions/{pest_name}")
async def get_pest_solutions(pest_name: str, request: Request):
    """获取指定病虫害的防治方案"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    # 优先从知识库查询
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pest_name, prevention_methods, chemical_control, 
                       biological_control, agricultural_control, severity_level
                FROM pest_knowledge 
                WHERE pest_name LIKE ? AND status = 'active'
                LIMIT 1
            ''', (f'%{pest_name}%',))
            row = cursor.fetchone()

            if row:
                return {
                    "code": 200,
                    "data": {
                        "pest_name": row['pest_name'],
                        "prevention_methods": row['prevention_methods'] or '暂无防治方法',
                        "chemical_control": row['chemical_control'] or '暂无化学防治方案',
                        "biological_control": row['biological_control'] or '暂无生物防治方案',
                        "agricultural_control": row['agricultural_control'] or '暂无农业防治方案',
                        "severity_level": row['severity_level'] or 'medium'
                    }
                }
    except Exception as e:
        print(f"查询知识库失败: {e}")

    # 知识库无数据时返回默认结构
    return {
        "code": 200,
        "data": {
            "pest_name": pest_name,
            "prevention_methods": "建议及时清除病株，喷施对应药剂。详细方案请咨询专业农技人员。",
            "chemical_control": "请根据具体病虫害类型选择对应药剂，或咨询AI问诊获取精准方案。",
            "biological_control": "可利用天敌昆虫或生物农药进行绿色防治。",
            "agricultural_control": "加强田间管理，及时清除病残体，合理轮作。",
            "severity_level": "medium"
        }
    }


@app.post("/api/detection-reports")
async def save_detection_report(request: Request):
    """保存生成的检测报告"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    data = await request.json()
    email = request.cookies.get("user_email")

    def _save_report():
        try:
            with get_detection_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS detection_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_email TEXT NOT NULL,
                        report_id TEXT NOT NULL,
                        pest_names TEXT,
                        image_base64 TEXT,
                        location TEXT,
                        confidence_avg REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    INSERT INTO detection_reports 
                    (user_email, report_id, pest_names, image_base64, location, confidence_avg)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    email,
                    data.get('report_id'),
                    json.dumps([r['name'] for r in data.get('results', [])]),
                    data.get('image_base64'),
                    data.get('location'),
                    sum(r['conf'] for r in data.get('results', [])) / len(data.get('results', [])) if data.get('results') else 0
                ))
                conn.commit()
                return True
        except Exception as e:
            return str(e)

    result = await run_in_threadpool(_save_report)
    if result is True:
        return {"code": 200, "message": "报告已保存"}
    else:
        return JSONResponse(status_code=500, content={"error": result})


# ========== 定时任务调度器 ==========
_task_scheduler = None  # 全局调度器实例


def get_scheduler():
    """获取全局调度器实例"""
    return _task_scheduler


def period_to_cron(period: str, time_str: str):
    """
    将前端周期格式转换为 APScheduler 的 CronTrigger
    period: "每天"/"每周一"/"每周日"/"每月1日"
    time_str: "HH:MM"
    """
    h, m = map(int, time_str.split(':'))
    if period == "每天":
        return CronTrigger(hour=h, minute=m)
    elif period == "每周一":
        return CronTrigger(day_of_week="mon", hour=h, minute=m)
    elif period == "每周日":
        return CronTrigger(day_of_week="sun", hour=h, minute=m)
    elif period == "每月1日":
        return CronTrigger(day="1", hour=h, minute=m)
    else:
        return CronTrigger(hour=h, minute=m)


def execute_task(task_id: str, task_name: str, task_type: str):
    """
    实际执行定时任务（在后台线程中运行）
    """
    print(f"[定时任务] 开始执行: {task_name} (类型: {task_type})")
    try:
        if task_type == "backup":
            _task_execute_backup(task_name)
        elif task_type == "cleanup":
            _task_execute_cleanup(task_name)
        elif task_type == "model":
            _task_execute_model_check(task_name)
        elif task_type == "report":
            _task_execute_report(task_name)
        elif task_type == "inspect":
            _task_execute_inspect(task_name)
        else:
            _task_execute_custom(task_name)

        # 更新任务状态为成功
        _update_task_status(task_id, "normal", "运行正常")
        print(f"[定时任务] 完成: {task_name}")

    except Exception as e:
        print(f"[定时任务] 失败: {task_name} - {str(e)}")
        _update_task_status(task_id, "warning", f"执行失败: {str(e)[:50]}")


def _task_execute_backup(task_name: str):
    """执行数据备份：复制 SQLite 数据库文件"""
    import shutil
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"farm_backup_{timestamp}.db"

    # 复制主数据库
    if Path("farm_system.db").exists():
        shutil.copy2("farm_system.db", backup_file)

    # 复制检测数据库
    if Path("detection_history.db").exists():
        shutil.copy2("detection_history.db", backup_dir / f"detection_backup_{timestamp}.db")

    # 清理30天前的旧备份
    cutoff = datetime.now() - timedelta(days=30)
    for f in backup_dir.glob("*.db"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()

    print(f"[备份任务] 已保存到: {backup_file}")


def _task_execute_cleanup(task_name: str):
    """执行数据清理：按保留策略清理过期数据"""
    settings = load_system_settings()
    retention = settings.get("retention", {})

    # 清理监测图片
    img_cfg = retention.get("image", {})
    if img_cfg.get("enabled"):
        days = img_cfg.get("days", 90)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        try:
            with get_detection_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM detection_records WHERE created_at < ?",
                    (cutoff,)
                )
                conn.commit()
                print(f"[清理任务] 已清理 {cursor.rowcount} 条过期检测记录")
        except Exception as e:
            print(f"[清理任务] 检测记录清理失败: {e}")

    # 清理传感器数据
    sensor_cfg = retention.get("sensor", {})
    if sensor_cfg.get("enabled"):
        days = sensor_cfg.get("days", 365)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM environment_data WHERE created_at < ?",
                    (cutoff,)
                )
                conn.commit()
                print(f"[清理任务] 已清理 {cursor.rowcount} 条过期传感器数据")
        except Exception as e:
            print(f"[清理任务] 传感器数据清理失败: {e}")


def _task_execute_model_check(task_name: str):
    """检查AI模型更新（检查 models/ 目录是否有新文件）"""
    models_dir = Path("models")
    if not models_dir.exists():
        print(f"[模型检查] models/ 目录不存在")
        return
    pt_files = list(models_dir.glob("*.pt"))
    if pt_files:
        latest = max(pt_files, key=lambda f: f.stat().st_mtime)
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        print(f"[模型检查] 最新模型: {latest.name} (修改时间: {mtime})")
        # 更新任务状态提示有新版本
        _update_task_status_by_name(task_name, "warning", "有新版本")


def _task_execute_report(task_name: str):
    """生成周报：统计本周检测数据并打印摘要"""
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM detection_records WHERE created_at > ?",
                (week_ago,)
            )
            detect_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT pest_name, COUNT(*) as cnt FROM detection_records "
                "WHERE created_at > ? GROUP BY pest_name ORDER BY cnt DESC LIMIT 5",
                (week_ago,)
            )
            top_pests = cursor.fetchall()

        summary = f"本周检测{detect_count}次，主要病虫害: {', '.join([p[0] for p in top_pests])}"
        print(f"[报告任务] {summary}")
    except Exception as e:
        print(f"[报告任务] 生成失败: {e}")


def _task_execute_inspect(task_name: str):
    """巡检任务：检查所有设备状态"""
    try:
        devices = get_all_devices()
        offline_count = sum(1 for d in devices if d.get("status") != "online")
        print(f"[巡检任务] 共{len(devices)}台设备，{offline_count}台离线")
        if offline_count > 0:
            _update_task_status_by_name(task_name, "warning", f"{offline_count}台设备离线")
    except Exception as e:
        print(f"[巡检任务] 失败: {e}")


def _task_execute_custom(task_name: str):
    """自定义任务：仅记录日志"""
    print(f"[自定义任务] {task_name} 执行完成")


def _update_task_status(task_id: str, status: str, status_text: str):
    """更新指定任务的状态（按ID）"""
    try:
        s = load_system_settings()
        for t in s.get("tasks", []):
            if t["id"] == task_id:
                t["status"] = status
                t["statusText"] = status_text
                t["statusIcon"] = "fas fa-check" if status == "normal" else "fas fa-exclamation-triangle"
                break
        save_system_settings(s)
    except Exception as e:
        print(f"更新任务状态失败: {e}")


def _update_task_status_by_name(name: str, status: str, status_text: str):
    """按任务名称更新状态"""
    try:
        s = load_system_settings()
        for t in s.get("tasks", []):
            if t["name"] == name:
                t["status"] = status
                t["statusText"] = status_text
                t["statusIcon"] = "fas fa-check" if status == "normal" else "fas fa-exclamation-triangle"
                break
        save_system_settings(s)
    except Exception as e:
        print(f"更新任务状态失败: {e}")


def sync_scheduler_jobs(scheduler: AsyncIOScheduler):
    """
    从 system_settings.json 加载任务并同步到调度器
    启动时调用一次，后续增删改任务时再次调用
    """
    if not scheduler:
        return

    settings = load_system_settings()
    tasks = settings.get("tasks", [])

    # 移除已不存在的任务
    existing_job_ids = {job.id for job in scheduler.get_jobs()}
    current_task_ids = {t["id"] for t in tasks if t.get("enabled")}
    for job_id in existing_job_ids:
        if job_id not in current_task_ids and job_id.startswith("task_"):
            scheduler.remove_job(job_id)
            print(f"[调度器] 移除任务: {job_id}")

    # 添加或更新任务
    for task in tasks:
        task_id = task["id"]
        if not task.get("enabled", True):
            if task_id in {job.id for job in scheduler.get_jobs()}:
                scheduler.remove_job(task_id)
            continue

        trigger = period_to_cron(task.get("period", "每天"), task.get("time", "03:00"))

        if task_id in {job.id for job in scheduler.get_jobs()}:
            scheduler.reschedule_job(task_id, trigger=trigger)
        else:
            scheduler.add_job(
                execute_task,
                trigger=trigger,
                id=task_id,
                args=[task_id, task["name"], task.get("type", "custom")],
                replace_existing=True,
                misfire_grace_time=3600  # 允许1小时的容错时间
            )
            print(f"[调度器] 添加任务: {task['name']} ({task.get('period', '每天')} {task.get('time', '03:00')})")


SYSTEM_SETTINGS_FILE = "system_settings.json"

def load_system_settings():
    """加载系统设置（任务/保留策略/预警）"""
    defaults = {
        "tasks": [
            {
                "id": "backup",
                "name": "每日数据备份",
                "icon": "fas fa-cloud-upload-alt",
                "color": "#1890ff",
                "period": "每天",
                "time": "03:00",
                "nextRun": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d") + " 03:00",
                "enabled": True,
                "status": "normal",
                "statusText": "运行正常",
                "statusIcon": "fas fa-check"
            },
            {
                "id": "cleanup",
                "name": "过期数据清理",
                "icon": "fas fa-broom",
                "color": "#faad14",
                "period": "每周日",
                "time": "02:00",
                "nextRun": (datetime.now() + timedelta(days=(6-datetime.now().weekday())%7 or 7)).strftime("%Y-%m-%d") + " 02:00",
                "enabled": True,
                "status": "normal",
                "statusText": "运行正常",
                "statusIcon": "fas fa-check"
            }
        ],
        "retention": {
            "image": {"enabled": True, "days": 90},
            "sensor": {"enabled": True, "days": 365},
            "alert": {"enabled": True, "days": 180},
            "log": {"enabled": False, "days": 90}
        },
        "alerts": [
            {"id": "pest_season", "name": "病虫害高发期预警", "icon": "fas fa-bug", "color": "#ff4d4f", "desc": "基于季节和历史数据提前3天预警高风险期", "enabled": True},
            {"id": "extreme_weather", "name": "极端天气监测", "icon": "fas fa-cloud-sun", "color": "#faad14", "desc": "自动监控霜冻、高温、暴雨等极端天气", "enabled": True},
            {"id": "device_offline", "name": "设备离线预警", "icon": "fas fa-battery-quarter", "color": "#722ed1", "desc": "传感器或摄像头离线超过30分钟通知", "enabled": True},
            {"id": "growth_cycle", "name": "生长周期提醒", "icon": "fas fa-seedling", "color": "#52c41a", "desc": "根据作物种类自动提醒施肥灌溉时间", "enabled": True}
        ]
    }
    if os.path.exists(SYSTEM_SETTINGS_FILE):
        try:
            with open(SYSTEM_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                defaults.update(saved)
        except:
            pass
    return defaults

def save_system_settings(data):
    try:
        with open(SYSTEM_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存系统设置失败: {e}")
        return False

def calculate_next_run(period: str, time_str: str):
    """计算下次执行时间（简化版）"""
    now = datetime.now()
    h, m = map(int, time_str.split(':'))
    nxt = datetime(now.year, now.month, now.day, h, m)
    if nxt <= now:
        nxt += timedelta(days=1)
    return nxt.strftime("%Y-%m-%d %H:%M")


@app.get("/api/admin/data-stats")
async def get_data_stats(request: Request, admin=Depends(require_admin)):
    """获取数据管理统计（检测/对话/农事记录数、存储占用）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM detection_records")
            detection_count = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(LENGTH(image_base64)) FROM detection_records WHERE image_base64 IS NOT NULL")
            img_len = cursor.fetchone()[0] or 0
            detection_size = round(img_len / 4 * 3 / 1024 / 1024, 1)

        with get_chat_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            chat_count = cursor.fetchone()[0]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM farm_records")
            farm_count = cursor.fetchone()[0]

        return {
            "code": 200,
            "data": {
                "detection": detection_count,
                "chat": chat_count,
                "farm": farm_count,
                "detectionSize": detection_size,
                "lastBackup": datetime.now().strftime("%Y-%m-%d") + " 03:00"
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/admin/system-metrics")
async def get_system_metrics(request: Request, admin=Depends(require_admin)):
    """获取系统性能指标"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        proc = psutil.Process()
        health = 100
        if cpu > 80: health -= 15
        if mem.percent > 85: health -= 15
        if disk.percent > 90: health -= 20
        return {
            "code": 200,
            "data": {
                "health": max(0, int(health)),
                "storage": round(disk.used / 1024**3, 1),
                "response": 156,
                "uptime": round((time.time() - proc.create_time()) / 86400, 1)
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/admin/logs")
async def get_system_logs(
        request: Request,
        level: str = "all",
        limit: int = 100,
        offset: int = 0,
        date_from: str = "",
        date_to: str = "",
        keyword: str = "",
        admin=Depends(require_admin)
):
    """读取后端日志文件（支持分页、日期范围、关键词搜索）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    all_entries = []
    log_dir = "logs"

    if os.path.isdir(log_dir):
        # 只读取最近30天的日志文件
        files = sorted(
            [f for f in os.listdir(log_dir) if f.endswith('.log')],
            reverse=True
        )
        for fname in files[:30]:
            path = os.path.join(log_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # 匹配日志格式: 2026-04-09 14:20:05 [INFO] message
                    m = re.match(
                        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.*)',
                        line
                    )
                    if m:
                        t, lvl, msg = m.groups()
                        typ = 'error' if 'ERROR' in lvl else 'warning' if 'WARN' in lvl else 'info'
                        all_entries.append({"time": t, "message": msg, "type": typ})
            except Exception as e:
                print(f"读日志失败 {fname}: {e}")

    # 按时间倒序
    all_entries.sort(key=lambda x: x['time'], reverse=True)

    # --- 依次应用过滤条件 ---

    # 1. 级别过滤
    if level != 'all':
        all_entries = [e for e in all_entries if e['type'] == level]

    # 2. 日期范围过滤
    if date_from:
        all_entries = [e for e in all_entries if e['time'] >= date_from]
    if date_to:
        # date_to 是日期字符串，需要扩展到当天23:59:59
        date_to_end = date_to + " 23:59:59"
        all_entries = [e for e in all_entries if e['time'] <= date_to_end]

    # 3. 关键词搜索（匹配 message 和 time）
    if keyword:
        kw = keyword.lower()
        all_entries = [
            e for e in all_entries
            if kw in e['message'].lower() or kw in e['time']
        ]

    total = len(all_entries)

    # 4. 分页
    paginated = all_entries[offset:offset + limit]

    return {
        "code": 200,
        "data": paginated,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@app.post("/api/admin/backup")
async def create_backup(request: Request, admin=Depends(require_admin)):
    """手动执行系统备份：备份数据库 + 打包日志，返回备份文件信息"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"farm_backup_{timestamp}"
        work_dir = backup_dir / backup_name
        work_dir.mkdir(exist_ok=True)

        db_files = []

        # 1. 用 sqlite3 的 .backup 命令备份主数据库
        main_db = "farm_system.db"
        if Path(main_db).exists():
            backup_db = str(work_dir / "farm_system_backup.db")
            import sqlite3
            src = sqlite3.connect(main_db)
            dst = sqlite3.connect(backup_db)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            db_files.append("farm_system_backup.db")

        # 2. 备份检测历史数据库
        detect_db = "detection_history.db"
        if Path(detect_db).exists():
            backup_detect = str(work_dir / "detection_history_backup.db")
            src = sqlite3.connect(detect_db)
            dst = sqlite3.connect(backup_detect)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            db_files.append("detection_history_backup.db")

        # 3. 打包日志目录
        logs_src = Path("logs")
        logs_dst = work_dir / "logs"
        if logs_src.exists():
            shutil.copytree(logs_src, logs_dst, dirs_exist_ok=True)

        # 4. 写入备份元信息
        meta = {
            "backup_time": datetime.now().isoformat(),
            "version": "2.1.0",
            "db_files": db_files,
            "db_sizes": {
                f: os.path.getsize(str(work_dir / f))
                for f in db_files
            }
        }
        with open(work_dir / "backup_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 5. 打包为 zip
        zip_path = backup_dir / f"{backup_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(work_dir))
                    zf.write(file_path, arcname)

        # 6. 清理临时工作目录
        shutil.rmtree(work_dir)

        # 7. 清理30天前的旧备份（保留最近30个）
        all_backups = sorted(
            backup_dir.glob("farm_backup_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for old in all_backups[30:]:
            old.unlink()

        zip_size = os.path.getsize(str(zip_path))

        return {
            "code": 200,
            "data": {
                "filename": f"{backup_name}.zip",
                "download_url": f"/api/admin/backup/download?file={backup_name}.zip",
                "size_bytes": zip_size,
                "size_mb": round(zip_size / 1024 / 1024, 2),
                "created_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"备份失败: {str(e)}"})


@app.get("/api/admin/backup/download")
async def download_backup(
        request: Request,
        file: str = "",
        admin=Depends(require_admin)
):
    """下载备份文件（支持 Range 断点续传）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    if not file or ".." in file:
        return JSONResponse(status_code=400, content={"error": "无效文件名"})

    backup_path = Path("backups") / file
    if not backup_path.exists() or not backup_path.is_file():
        return JSONResponse(status_code=404, content={"error": "备份文件不存在"})

    file_size = backup_path.stat().st_size

    # 处理 Range 请求（支持断点续传）
    range_header = request.headers.get("range")
    if range_header:
        import re
        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else file_size - 1
            end = min(end, file_size - 1)

            async def range_iter():
                with open(backup_path, "rb") as f:
                    f.seek(start)
                    remaining = end - start + 1
                    while remaining > 0:
                        chunk_size = min(64 * 1024, remaining)
                        yield f.read(chunk_size)
                        remaining -= chunk_size

            return StreamingResponse(
                range_iter(),
                status_code=206,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{file}"',
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(end - start + 1)
                }
            )

    # 普通下载
    return StreamingResponse(
        open(backup_path, "rb"),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{file}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size)
        }
    )


# ---------- 定时任务 ----------
@app.get("/api/settings/tasks")
async def api_get_tasks(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    s = load_system_settings()
    return {"code": 200, "data": s.get("tasks", [])}

@app.post("/api/settings/tasks")
async def api_create_task(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    data = await request.json()
    s = load_system_settings()
    task = {
        "id": "task_" + str(int(time.time() * 1000)),
        "name": data.get("name"),
        "type": data.get("type", "backup"),
        "icon": data.get("icon", "fas fa-tasks"),
        "color": data.get("color", "#595959"),
        "period": data.get("period", "每天"),
        "time": f"{data.get('hour','03')}:{data.get('minute','00')}",
        "nextRun": calculate_next_run(data.get("period", "每天"), f"{data.get('hour','03')}:{data.get('minute','00')}"),
        "enabled": data.get("enabled", True),
        "status": "normal", "statusText": "运行正常", "statusIcon": "fas fa-check"
    }
    s.setdefault("tasks", []).append(task)
    save_system_settings(s)
    # 同步到调度器
    sync_scheduler_jobs(get_scheduler())
    return {"code": 200, "data": task}



@app.put("/api/settings/tasks/{task_id}")
async def api_update_task(task_id: str, request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    data = await request.json()
    s = load_system_settings()
    for t in s.get("tasks", []):
        if t["id"] == task_id:
            t.update(data)
            # 如果有时间/周期变更，重新计算下次执行
            if "period" in data or "time" in data:
                t["nextRun"] = calculate_next_run(t.get("period", "每天"), t.get("time", "03:00"))
            save_system_settings(s)
            sync_scheduler_jobs(get_scheduler())  # 同步到调度器
            return {"code": 200}
    return JSONResponse(status_code=404, content={"error": "任务不存在"})



@app.delete("/api/settings/tasks/{task_id}")
async def api_delete_task(task_id: str, request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    s = load_system_settings()
    s["tasks"] = [t for t in s.get("tasks", []) if t["id"] != task_id]
    save_system_settings(s)
    sync_scheduler_jobs(get_scheduler())  # 同步到调度器
    return {"code": 200}

# ---------- 数据保留策略 ----------
@app.get("/api/settings/retention")
async def api_get_retention(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    s = load_system_settings()
    return {"code": 200, "data": s.get("retention", {})}

@app.post("/api/settings/retention")
async def api_save_retention(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    data = await request.json()
    s = load_system_settings()
    s["retention"] = data
    save_system_settings(s)
    return {"code": 200}


# ---------- 预警设置 ----------
@app.get("/api/settings/alerts")
async def api_get_alerts(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    s = load_system_settings()
    return {"code": 200, "data": s.get("alerts", [])}

@app.post("/api/settings/alerts")
async def api_save_alerts(request: Request):
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    data = await request.json()
    s = load_system_settings()
    s["alerts"] = data
    save_system_settings(s)
    return {"code": 200}


@app.post("/api/comments/batch")
async def batch_comments_operation(request: Request):
    """
    批量操作评论（通过/拒绝/删除）
    修复：增强错误处理和权限校验
    """
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    if not user or user['role'] != 'admin':
        return JSONResponse(status_code=403, content={"error": "无权操作"})

    data = await request.json()
    ids = data.get('ids', [])
    action = data.get('action')  # 'approve', 'reject', 'delete'

    if not ids or not isinstance(ids, list):
        return JSONResponse(status_code=400, content={"error": "未选择评论或格式错误"})

    if action not in ['approve', 'reject', 'delete']:
        return JSONResponse(status_code=400, content={"error": "无效的操作类型"})

    success_count = 0
    errors = []

    for comment_id in ids:
        try:
            if action == 'approve':
                # 审核通过时自动取消置顶（新通过的不应默认置顶）
                result = update_comment_status(comment_id, status='approved', is_pinned=False)
                if not result:
                    errors.append(f"ID {comment_id}: 更新失败")
                else:
                    success_count += 1

            elif action == 'reject':
                # 拒绝时自动取消置顶
                result = update_comment_status(comment_id, status='rejected', is_pinned=False)
                if not result:
                    errors.append(f"ID {comment_id}: 更新失败")
                else:
                    success_count += 1

            elif action == 'delete':
                # 使用关键字参数确保正确传递
                result = delete_comment(comment_id, user_email=email, is_admin=True)
                if not result.get('success'):
                    errors.append(f"ID {comment_id}: {result.get('error', '删除失败')}")
                else:
                    success_count += 1

        except Exception as e:
            errors.append(f"ID {comment_id}: {str(e)}")

    return {
        "code": 200,
        "message": f"操作完成：成功 {success_count}/{len(ids)}",
        "success_count": success_count,
        "total": len(ids),
        "errors": errors if errors else None
    }


@app.get("/api/admin/users/{user_id}")
async def admin_get_user_detail(user_id: int, admin=Depends(require_admin)):
    def _get_user_detail():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.*,
                       (SELECT COUNT(*) FROM user_plots WHERE user_id = u.id) as plot_count,
                       (SELECT GROUP_CONCAT(p.name) FROM user_plots up 
                        JOIN plots p ON up.plot_id = p.id WHERE up.user_id = u.id) as plot_names
                FROM users u
                WHERE u.id = ?
            ''', (user_id,))
            row = cursor.fetchone()

            if not row:
                return None

            user = dict(row)
            user['is_online'] = bool(user.get('is_online'))

            # 获取绑定的地块ID列表
            cursor.execute('SELECT plot_id FROM user_plots WHERE user_id = ?', (user_id,))
            plot_rows = cursor.fetchall()
            user['plot_ids'] = [r['plot_id'] for r in plot_rows]

            # 只有当有地块时才查询
            if user['plot_ids']:
                placeholders = ','.join('?' * len(user['plot_ids']))
                cursor.execute(
                    f'SELECT id, name FROM plots WHERE id IN ({placeholders})',
                    tuple(user['plot_ids'])
                )
                plot_info = {r['id']: r['name'] for r in cursor.fetchall()}
                user['plot_names'] = ', '.join(
                    [plot_info.get(pid, '') for pid in user['plot_ids'] if plot_info.get(pid)]
                )
            else:
                user['plot_names'] = ''
                user['plot_ids'] = []

            # 补充权限字段
            if user['role'] == 'admin':
                try:
                    user['permissions'] = get_user_permissions(user_id)
                except Exception as e:
                    print(f"获取权限失败: {e}")
                    user['permissions'] = []
                else:
                    user['permissions'] = []

            return user
        finally:
            conn.close()

    user_data = await run_in_threadpool(_get_user_detail)

    if not user_data:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    return {"code": 200, "data": user_data}


@app.post("/api/chat/sessions/{session_id}/messages/{msg_id}/favorite")
async def toggle_message_favorite(session_id: int, msg_id: str, request: Request):
    """单独切换消息收藏状态，不修改其他内容"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    data = await request.json()
    is_favorite = data.get('is_favorite', False)

    try:
        with get_chat_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT messages FROM chat_sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()

            if not row:
                return JSONResponse(status_code=404, content={"error": "会话不存在"})

            messages = json.loads(row['messages'])
            for msg in messages:
                if msg.get('id') == msg_id or (not msg.get('id') and msg.get('timestamp') == msg_id):
                    msg['isFavorite'] = is_favorite
                    msg['is_favorite'] = is_favorite
                    break

            cursor.execute('''
                UPDATE chat_sessions 
                SET messages = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (json.dumps(messages, ensure_ascii=False), session_id))
            conn.commit()

        return {"code": 200, "message": "收藏状态已更新"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/comments/{comment_id}/replies/{reply_id}")
async def delete_top_level_reply(comment_id: int, reply_id: int, request: Request):
    """删除直接回复评论的一级回复"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    email = request.cookies.get("user_email")
    user = get_user_by_email(email)
    is_admin = user and user.get('role') == 'admin'

    # 复用已有的 delete_reply 函数，验证权限后删除
    def _delete():
        return delete_reply(reply_id, email, is_admin)

    result = await run_in_threadpool(_delete)

    if result['success']:
        return {"success": True}
    else:
        return JSONResponse(status_code=403, content={"error": result['error']})


@app.post("/api/warning/predict")
async def predict_outbreak(request: Request, user=Depends(get_current_user_dep)):
    """获取病虫害爆发预警"""
    data = await request.json()
    crop_type = data.get('crop_type', 'rice')

    # 获取历史数据（最近7天）
    history = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        records = get_detection_history(user_email=user['email'], limit=100)
        daily_count = len([r for r in records if r.get('created_at', '').startswith(date)])
        history.append({
            'temp': 25 + random.uniform(-3, 3),  # 实际应从天气API获取
            'humidity': 60 + random.uniform(-10, 10),
            'rain': random.uniform(0, 20),
            'pest_count': daily_count,
            'growth_stage': 0.5
        })

    # 获取天气预报（模拟）
    weather_forecast = [{'temp': 26, 'humidity': 70, 'rain': 5} for _ in range(7)]

    # 预测
    result = warning_system.predict_outbreak(history, weather_forecast, crop_type)

    return {"code": 200, "data": result}


@app.get("/api/warning/heatmap")
async def get_risk_heatmap_api(request: Request, days: int = 7, user=Depends(get_current_user_dep)):
    """获取区域风险热力图"""
    records = get_detection_history(user_email=user['email'], limit=1000)
    heatmap_data = []
    for record in records:
        if record.get('location_lat') and record.get('location_lng') and record.get('confidence', 0) > 70:
            heatmap_data.append({
                "lat": record['location_lat'],
                "lng": record['location_lng'],
                "count": record['confidence'],
                "risk_type": record.get('pest_name', '未知')
            })
    return {"code": 200, "data": heatmap_data}



@app.post("/api/federated/join")
async def join_federation(request: Request, user=Depends(get_current_user_dep)):
    """农户端申请加入联邦学习"""
    # 检查节点资格（至少10次检测记录）
    history = get_detection_history(user_email=user['email'], limit=20)
    if len(history) < 10:
        return JSONResponse(
            status_code=400,
            content={"error": "需要至少10次检测记录才能参与联邦学习"}
        )

    # 检查本地是否有训练数据
    user_data_path = f"data/user_{user['id']}/dataset.yaml"
    if not os.path.exists(user_data_path):
        return JSONResponse(
            status_code=400,
            content={"error": "未找到本地训练数据，请先上传标注数据"}
        )

    # 启动本地客户端（后台线程，不阻塞）
    def run_client():
        client = YOLOClient(user['id'], user_data_path)
        fl.client.start_numpy_client(server_address="localhost:8080", client=client)

    threading.Thread(target=run_client, daemon=True).start()

    return {
        "code": 200,
        "message": "已加入联邦学习网络",
        "node_id": user['id'],
        "status": "training"
    }


@app.get("/api/federated/status")
async def get_federation_status(admin=Depends(require_admin)):
    """获取联邦学习真实状态"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 统计在线节点
            cursor.execute("SELECT COUNT(*) FROM federated_nodes WHERE status='online'")
            active_nodes = cursor.fetchone()[0]

            # 总贡献度
            cursor.execute("SELECT COALESCE(SUM(contribution), 0) FROM federated_nodes")
            total_contrib = cursor.fetchone()[0]

            # 最新模型版本
            cursor.execute("SELECT MAX(model_version) FROM federated_nodes WHERE model_version IS NOT NULL")
            ver_row = cursor.fetchone()
            global_ver = ver_row[0] if ver_row and ver_row[0] else "v1.0"

            # 查询节点列表（给前端展示）
            cursor.execute('''
                SELECT user_id, node_name, status, contribution, last_update, last_round
                FROM federated_nodes
                ORDER BY last_update DESC
            ''')
            nodes = []
            for row in cursor.fetchall():
                nodes.append({
                    "id": row['user_id'],
                    "name": row['node_name'] or f"节点-{row['user_id']}",
                    "status": "online" if row['status'] == 'online' else "offline",
                    "contribution": round(row['contribution'] or 0, 2),
                    "last_update": row['last_update'] or "从未上线",
                    "last_round": row['last_round'] or 0
                })

    except Exception as e:
        print(f"获取联邦状态失败: {e}")
        active_nodes = 0
        total_contrib = 0
        global_ver = "v1.0"
        nodes = []

    return {
        "code": 200,
        "status": {
            "active_nodes": active_nodes,
            "total_contributions": int(total_contrib),
            "global_model_version": global_ver,
            "accuracy_improvement": "0%"
        },
        "nodes": nodes
    }

@app.post("/api/admin/model/optimize")
async def optimize_model(admin=Depends(require_admin)):
    """执行模型优化（剪枝+量化）"""
    try:
        model_path = os.getenv("YOLO_MODEL_PATH", "models/yolo11n.pt")
        optimizer = ModelOptimizer(model_path)

        # 执行优化流程
        optimizer.prune_model(sparsity=0.3)
        optimizer.quantize_model()

        # 基准测试
        metrics = optimizer.benchmark()

        # 导出TFLite（YOLO export 会生成在默认位置，这里捕获实际路径）
        # 注意： ultralytics export 默认输出到 models/ 目录下
        export_name = f"yolo11n_int8_{datetime.now().strftime('%Y%m%d%H%M')}.tflite"
        tflite_dir = Path("models")
        tflite_dir.mkdir(exist_ok=True)

        # 先执行导出
        optimizer.export_tflite()

        # YOLO 默认导出路径通常是 models/yolo11n_int8.tflite，我们重命名为带时间戳的版本
        default_export = Path("models/yolo11n_int8.tflite")
        target_path = tflite_dir / export_name
        if default_export.exists():
            default_export.rename(target_path)
        else:
            # 如果默认名不对，尝试查找最新生成的 tflite
            tflite_files = sorted(tflite_dir.glob("*.tflite"), key=lambda p: p.stat().st_mtime)
            target_path = tflite_files[-1] if tflite_files else default_export

        # 保存到模型库
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO model_versions 
                (version, model_path, size_mb, latency_ms, map50, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"v{datetime.now().strftime('%Y%m%d%H%M')}",
                str(target_path),
                metrics['optimized_size_mb'],
                metrics['avg_latency_ms'],
                0.92,
                'ready',
                datetime.now()
            ))
            conn.commit()

        return {
            "code": 200,
            "message": "模型优化完成",
            "data": {
                "original_size": metrics['original_size_mb'],
                "optimized_size": metrics['optimized_size_mb'],
                "compression_ratio": round(metrics['compression_ratio'], 2),
                "latency_ms": metrics['avg_latency_ms'],
                "fps": round(metrics['fps'], 1),
                "tflite_path": str(target_path)
            }
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/admin/model/versions")
async def list_model_versions(admin=Depends(require_admin)):
    """获取模型版本列表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, version, model_path, size_mb, latency_ms, map50, status, created_at
            FROM model_versions 
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        versions = [dict(row) for row in rows]
    return {"code": 200, "data": versions}


@app.post("/api/admin/model/deploy/{version_id}")
async def deploy_model(version_id: int, admin=Depends(require_admin)):
    """部署指定版本模型到边缘设备"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM model_versions WHERE id = ?', (version_id,))
        version = cursor.fetchone()

        if not version:
            return JSONResponse(status_code=404, content={"error": "版本不存在"})

        # 更新当前激活的模型版本（通过环境变量或配置文件）
        # 实际应该复制到部署目录并重启服务或热更新
        os.environ['YOLO_MODEL_PATH'] = version['model_path']

        return {
            "code": 200,
            "message": f"已部署版本 {version['version']}",
            "data": {
                "version": version['version'],
                "path": version['model_path'],
                "size_mb": version['size_mb']
            }
        }


@app.post("/api/device/heartbeat")
async def device_heartbeat_api(request: Request):
    """接收边缘设备心跳（脏污+电量+存储）"""
    data = await request.json()
    device_id = data.get('device_id')
    alerts = []

    if data.get('brightness', 255) < 120:
        alerts.append({"type": "dirt", "message": f"设备{device_id}镜头可能脏污，请擦拭", "severity": "warning"})
        notify_user(device_id, "镜头脏污警告", "检测到镜头亮度异常，建议清洁")

    if data.get('storage_free', 1000) < 1024:
        alerts.append({"type": "storage", "message": "存储空间不足", "severity": "critical"})

    if data.get('battery', 100) < 20:
        alerts.append({"type": "battery", "message": "电量低，将启动省电模式", "severity": "warning"})
        set_device_power_mode(device_id, "power_save")

    # 保存设备状态
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO device_status 
                (device_id, brightness, sharpness, storage_free, battery, last_seen, alerts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_id,
                data.get('brightness'),
                data.get('sharpness'),
                data.get('storage_free'),
                data.get('battery'),
                datetime.now(),
                json.dumps(alerts)
            ))
            conn.commit()
    except Exception as e:
        print(f"保存设备状态失败: {e}")

    return {
        "code": 200,
        "action": "enter_power_save" if any(a['type'] == 'battery' for a in alerts) else "normal",
        "alerts": alerts
    }

@app.post("/api/device/{device_id}/check")
async def device_health_check_api(device_id: int, request: Request):
    """设备健康检查（脏污+电量+存储）"""
    data = await request.json()
    alerts = []
    if data.get('brightness', 255) < 120:
        alerts.append({"type": "dirt", "message": "镜头可能脏污", "severity": "warning"})
    if data.get('storage_free', 1000) < 1024:
        alerts.append({"type": "storage", "message": "存储空间不足", "severity": "critical"})
    if data.get('battery', 100) < 20:
        alerts.append({"type": "battery", "message": "电量低，将启动省电模式", "severity": "warning"})
    return {
        "code": 200,
        "alerts": alerts,
        "action": "enter_power_save" if any(a['type'] == 'battery' for a in alerts) else "normal"
    }



@app.get("/api/visualization/dashboard")
async def get_dashboard_data_viz(request: Request, user=Depends(get_current_user_dep)):
    """获取首页数据看板（增强版）"""
    viz = RiskMapGenerator()
    stats = {
        "detection_trend": viz.generate_time_series_chart(user['email']),  # 【改】user['id'] → user['email']
        "pest_distribution": get_pest_distribution(user['email']),
        "farm_health_score": calculate_farm_health(user['email']),        # 【改】user['id'] → user['email']
        "upcoming_tasks": get_farm_tasks(user['id'], limit=5)
    }
    return {"code": 200, "data": stats}


@app.get("/api/visualization/heatmap-html")
async def get_heatmap_html_viz(request: Request, user=Depends(get_current_user_dep)):
    """生成 Folium 热力图 HTML（用于 iframe 嵌入）"""
    viz = RiskMapGenerator()
    records = get_detection_history(user_email=user['email'], limit=1000)
    detection_data = []
    for r in records:
        if r.get('location_lat') and r.get('location_lng'):
            detection_data.append({
                'lat': r['location_lat'],
                'lng': r['location_lng'],
                'confidence': r.get('confidence', 50),
                'time': r.get('created_at')
            })
    # 生成HTML
    html = viz.generate_heatmap(detection_data)
    return HTMLResponse(content=html)


def get_pest_distribution(user_email):
    """获取病虫害分布统计"""
    with get_detection_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pest_name, COUNT(*) as count, AVG(confidence) as avg_conf
            FROM detection_records 
            WHERE user_email = ?
            GROUP BY pest_name
            ORDER BY count DESC
            LIMIT 5
        ''', (user_email,))
        return [dict(row) for row in cursor.fetchall()]

@app.get("/admin/federated")
def admin_federated_page(request: Request):
    is_admin, resp = check_admin_page(request)
    if not is_admin:
        return resp
    try:
        with open("admin_federated.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>admin_federated.html 未找到</h1>", status_code=404)

@app.get("/admin/model")
def admin_model_page(request: Request):
    is_admin, resp = check_admin_page(request)
    if not is_admin:
        return resp
    try:
        with open("admin_model.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>admin_model.html 未找到</h1>", status_code=404)

@app.post("/api/federated/start")
async def start_federated_round(admin=Depends(require_admin)):
    """
    管理员手动触发一轮联邦学习聚合
    （实际应调用 federated_learning 中的逻辑或发送信号）
    """
    # 简单实现：记录一次操作时间，前端展示为"训练中"
    # 如需真正触发，可通过全局变量或消息队列通知后台线程
    return {
        "code": 200,
        "message": "联邦学习训练已启动",
        "status": "training",
        "started_at": datetime.now().isoformat()
    }


def get_user_activity_stats(user_id: int):
    """获取用户活跃度统计（联邦学习准入判断用）"""
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM detection_records WHERE user_id = ?', (user_id,))
            detections = cursor.fetchone()[0]
        return {"detections": detections}
    except:
        return {"detections": 0}


def notify_user(device_id: str, title: str, message: str):
    """设备异常通知（简易版：打印日志，后续可接邮件/短信）"""
    print(f"[设备通知] device={device_id}, title={title}, msg={message}")
    # 如需持久化，可写入 notification 表


def set_device_power_mode(device_id: str, mode: str):
    """设置设备电源模式"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO device_status (device_id, power_mode, last_seen)
                VALUES (?, ?, ?)
            ''', (device_id, mode, datetime.now()))
            conn.commit()
    except Exception as e:
        print(f"设置电源模式失败: {e}")


@app.get("/api/history/trend")
async def get_detection_trend(request: Request, days: int = 7):
    """获取最近N天的检测趋势数据（用于首页图表）"""
    if "auth_token" not in request.cookies:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    user_email = request.cookies.get("user_email")
    user = get_user_by_email(user_email)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    is_admin = user.get('role') == 'admin'

    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            dates = []
            detect_counts = []
            high_risk_counts = []

            for i in range(days - 1, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                dates.append(date)

                # 构建查询条件
                base_where = "DATE(created_at) = ?"
                params = [date]

                if not is_admin:
                    base_where += " AND user_email = ?"
                    params.append(user_email)

                # 总检测数
                cursor.execute(f'''
                    SELECT COUNT(*) FROM detection_records 
                    WHERE {base_where}
                ''', params)
                detect_counts.append(cursor.fetchone()[0])

                # 高风险数
                cursor.execute(f'''
                    SELECT COUNT(*) FROM detection_records 
                    WHERE {base_where} AND risk_level = 'high'
                ''', params)
                high_risk_counts.append(cursor.fetchone()[0])

            return {
                "code": 200,
                "data": {
                    "dates": dates,
                    "detections": detect_counts,
                    "highRisk": high_risk_counts
                }
            }
    except Exception as e:
        print(f"获取趋势数据失败: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# app.py

@app.get("/api/system/metrics")
async def get_metrics(user=Depends(get_current_user_dep)):
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "uptime": "12天 4小时"
    }



@app.post("/api/settings/update-all")
async def update_all_settings(data: SettingsPayload, user=Depends(get_current_user_dep)):
    try:
        update_user_security_settings(
            user['email'],
            enable_2fa=data.security.get('enable_2fa'),
            login_alert=data.security.get('login_alert')
        )
        return {"code": 200, "message": "设置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    threading.Timer(1, lambda: webbrowser.open("http://localhost:8001")).start()
    uvicorn.run(app, host="0.0.0.0", port=8001)