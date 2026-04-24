import sqlite3
import time
import os
import json
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import bcrypt


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 统一数据库文件路径
DB_PATH = os.path.join(DATA_DIR, 'email.db')
DETECTION_DB_PATH = os.path.join(DATA_DIR, 'detection_history.db')
CHAT_DB_PATH = os.path.join(DATA_DIR, 'chat_history.db')
COMMENTS_DB_PATH = os.path.join(DATA_DIR, 'comments.db')
KNOWLEDGE_DB_PATH = os.path.join(DATA_DIR, 'knowledge_base.db')

# 统一连接配置（WAL模式提升并发性能）
DB_CONFIG = {
    'timeout': 30,
    'check_same_thread': False,
    'isolation_level': None  # 自动提交模式，手动控制事务
}

def get_db_connection():
    """获取主数据库连接（带WAL模式）"""
    conn = sqlite3.connect(DB_PATH, **DB_CONFIG)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # 关键：启用WAL模式
    return conn

def get_detection_db_connection():
    """获取检测历史数据库连接"""
    conn = sqlite3.connect(DETECTION_DB_PATH, **DB_CONFIG)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def get_chat_db_connection():
    """获取对话记录数据库连接"""
    conn = sqlite3.connect(CHAT_DB_PATH, **DB_CONFIG)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def get_comments_db_connection():
    """获取评论数据库连接"""
    conn = sqlite3.connect(COMMENTS_DB_PATH, **DB_CONFIG)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def get_knowledge_db_connection():
    """获取知识库数据库连接"""
    conn = sqlite3.connect(KNOWLEDGE_DB_PATH, **DB_CONFIG)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ==================== 用户名和密码管理 ====================

def update_user_name(email, name):
    """更新用户显示名称（用户名）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET name = ? WHERE email = ?",
                (name, email)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"更新用户名失败: {e}")
        return False


def update_user_password(email, old_password, new_password):
    """更新用户密码（需要验证旧密码）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 验证旧密码
            cursor.execute(
                "SELECT password_hash FROM users WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()

            if not row:
                return {"success": False, "error": "用户不存在"}

            stored_hash = row['password_hash']

            # 如果已设置过密码，验证旧密码
            if stored_hash:
                if not verify_password(old_password, stored_hash):
                    return {"success": False, "error": "原密码错误"}

            # 哈希新密码并保存
            new_hash = hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE email = ?",
                (new_hash, email)
            )
            conn.commit()
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_user_password(account, password):
    """验证用户密码（支持邮箱或用户名登录）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 判断是邮箱还是用户名
            if '@' in account:
                cursor.execute(
                    "SELECT password_hash, name, role, status, email FROM users WHERE email = ?",
                    (account,)
                )
            else:
                cursor.execute(
                    "SELECT password_hash, name, role, status, email FROM users WHERE name = ?",
                    (account,)
                )

            row = cursor.fetchone()
            if not row:
                return None

            stored_hash = row['password_hash']

            # 防御性检查：hash 格式必须正确
            if not stored_hash or not isinstance(stored_hash, str) or not stored_hash.startswith('$2'):
                print(f"用户 {account} 的密码哈希格式无效，需要重新设置密码")
                return None

            if verify_password(password, stored_hash):
                return {
                    "email": row['email'],
                    "name": row['name'],
                    "role": row['role'],
                    "status": row['status']
                }
            return None
    except Exception as e:
        print(f"密码验证失败: {e}")
        return None


def set_initial_username_and_password(email, username, password):
    """首次登录设置用户名和密码"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 哈希密码
            pwd_hash = hash_password(password) if password else None
            cursor.execute(
                "UPDATE users SET name = ?, password_hash = ?, has_password = 1 WHERE email = ?",
                (username, pwd_hash, email)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"设置初始用户名密码失败: {e}")
        return False


def get_user_display_name(email):
    """获取用户显示名称"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, email FROM users WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()
            if row and row['name']:
                return row['name']
            # 如果没有设置用户名，返回邮箱前缀
            return email.split('@')[0] if email else "未命名用户"
    except Exception as e:
        print(f"获取用户名失败: {e}")
        return "未命名用户"

def hash_password(password: str) -> str:
    """哈希密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    if not hashed or not isinstance(hashed, str) or not hashed.startswith('$2'):
        return False
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ==================== 对话记录数据库管理（新增） ====================

def init_chat_database():
    """初始化对话记录数据库（修复：支持用户隔离）"""
    with get_chat_db_connection() as conn:
        cursor = conn.cursor()

        # 创建表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,                     -- 新增：所属用户
                title TEXT NOT NULL,
                pest_name TEXT,
                image_base64 TEXT,
                messages TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_interrupted BOOLEAN DEFAULT 0
            )
        ''')

        # 检查并添加 user_email 字段（兼容旧数据）
        cursor.execute("PRAGMA table_info(chat_sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'user_email' not in columns:
            cursor.execute('ALTER TABLE chat_sessions ADD COLUMN user_email TEXT')
            print("已添加 user_email 字段到 chat_sessions 表")

        # 创建索引（优化查询）
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_sessions(user_email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_updated ON chat_sessions(updated_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_pest ON chat_sessions(pest_name)')
        conn.commit()


def save_chat_session(user_email, title, messages, pest_name=None, image_base64=None, session_id=None, is_interrupted=False):
    """保存对话记录（修复：关联用户）"""
    init_chat_database()
    now = datetime.now().isoformat()
    messages_json = json.dumps(messages, ensure_ascii=False) if isinstance(messages, list) else messages
    try:
        with get_chat_db_connection() as conn:
            cursor = conn.cursor()
            # ... 原有代码 ...

            if session_id:
                # 更新时检查权限：只能更新自己的会话
                cursor.execute('SELECT user_email FROM chat_sessions WHERE id = ?', (session_id,))
                row = cursor.fetchone()
                if row and row['user_email'] and row['user_email'] != user_email:
                    return {"success": False, "error": "无权修改他人对话"}

                cursor.execute('''
                    UPDATE chat_sessions 
                    SET title = ?, pest_name = ?, image_base64 = ?, messages = ?, 
                        updated_at = ?, is_interrupted = ?
                    WHERE id = ?
                ''', (title, pest_name, image_base64, messages_json, now,
                      1 if is_interrupted else 0, session_id))
            else:
                cursor.execute('''
                    INSERT INTO chat_sessions 
                    (user_email, title, pest_name, image_base64, messages, created_at, updated_at, is_interrupted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_email, title, pest_name, image_base64, messages_json, now, now,
                      1 if is_interrupted else 0))
                session_id = cursor.lastrowid

            conn.commit()
            return {"success": True, "id": session_id, "is_interrupted": is_interrupted}
    except Exception as e:
        print(f"保存对话记录失败: {e}")
        return {"success": False, "error": str(e)}


def get_chat_sessions(user_email, limit=50, include_interrupted=None):
    """获取用户的对话列表（修复：用户隔离）"""
    init_chat_database()
    try:
        with get_chat_db_connection() as conn:
            cursor = conn.cursor()

            sql = '''
                SELECT id, title, pest_name, image_base64, created_at, updated_at, is_interrupted 
                FROM chat_sessions 
                WHERE (user_email = ? OR user_email IS NULL)  -- 兼容旧数据
            '''
            params = [user_email]

            if include_interrupted is not None:
                sql += ' AND is_interrupted = ?'
                params.append(1 if include_interrupted else 0)

            sql += ' ORDER BY updated_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            sessions = []
            for row in rows:
                session = dict(row)
                # 布尔值转换
                session['is_interrupted'] = bool(session.get('is_interrupted', 0))

                # 是否是最新的可恢复中断（5分钟内更新且中断）
                if session['is_interrupted']:
                    try:
                        updated = datetime.fromisoformat(session['updated_at'])
                        session['can_resume'] = (datetime.now() - updated).total_seconds() < 300  # 5分钟内
                    except:
                        session['can_resume'] = False
                else:
                    session['can_resume'] = False

                sessions.append(session)

            return sessions
    except Exception as e:
        print(f"获取对话列表失败: {e}")
        return []


def get_chat_session(session_id):
    """获取单个对话详情（包含中断状态解析）"""
    init_chat_database()
    try:
        with get_chat_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                record = dict(row)
                # 解析JSON
                try:
                    if isinstance(record.get('messages'), str):
                        record['messages'] = json.loads(record['messages'])
                except:
                    record['messages'] = []

                # 布尔值转换
                record['is_interrupted'] = bool(record.get('is_interrupted', 0))

                # 检查是否是最近中断的（5分钟内）
                if record['is_interrupted']:
                    try:
                        updated = datetime.fromisoformat(record['updated_at'])
                        record['is_recently_interrupted'] = (datetime.now() - updated).total_seconds() < 300
                    except:
                        record['is_recently_interrupted'] = False
                else:
                    record['is_recently_interrupted'] = False

                return record
            return None
    except Exception as e:
        print(f"获取对话详情失败: {e}")
        return None


def delete_chat_session(session_id):
    """删除对话记录"""
    init_chat_database()
    try:
        with get_chat_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
            conn.commit()
            return {"success": True}
    except Exception as e:
        print(f"删除对话记录失败: {e}")
        return {"success": False, "error": str(e)}


def clear_all_chat_sessions(user_email, is_admin=False):
    """清空用户对话（修复：用户隔离）"""
    init_chat_database()
    try:
        with get_chat_db_connection() as conn:
            cursor = conn.cursor()

            if is_admin and user_email is None:
                # 管理员可以清空所有
                cursor.execute('DELETE FROM chat_sessions')
            else:
                # 普通用户只能清空自己的
                cursor.execute('DELETE FROM chat_sessions WHERE user_email = ? OR user_email IS NULL',
                               (user_email,))

            deleted = cursor.rowcount
            conn.commit()
            return {"success": True, "deleted_count": deleted}
    except Exception as e:
        print(f"清空对话记录失败: {e}")
        return {"success": False, "error": str(e)}


# ==================== 检测历史数据库管理（原有） ====================

def init_detection_database():
    """
    初始化检测历史数据库
    包含表：detection_records（检测记录）、pest_details（病虫害详情）
    """
    with get_detection_db_connection() as conn:
        cursor = conn.cursor()

        # 主表：检测记录
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS detection_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pest_name TEXT NOT NULL,              -- 病虫害名称
                        confidence REAL NOT NULL,              -- 置信度（百分比）
                        image_base64 TEXT,                     -- 检测后标注图片（Base64）
                        original_image_base64 TEXT,            -- 原始上传图片（Base64，可选）
                        device_id TEXT,                        -- 设备ID（如果是边缘设备上传）
                        location_lat REAL,                     -- 检测位置纬度
                        location_lng REAL,                     -- 检测位置经度
                        risk_level TEXT DEFAULT 'low',         -- 风险等级：low/medium/high
                        status TEXT DEFAULT 'active',          -- 状态：active/resolved/ignored
                        notes TEXT,                            -- 用户备注
                        crop_type TEXT,                        -- 新增：作物类型（rice/wheat/corn等）
                        user_email TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

        # 详情表：同一图片中多个病虫害的详细记录
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pest_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                pest_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                bbox_x1 REAL,                          -- 边界框坐标
                bbox_y1 REAL,
                bbox_x2 REAL,
                bbox_y2 REAL,
                FOREIGN KEY (record_id) REFERENCES detection_records(id) ON DELETE CASCADE
            )
        ''')

        # 创建索引以提高查询速度
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON detection_records(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_name ON detection_records(pest_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_level ON detection_records(risk_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_id ON pest_details(record_id)')

        conn.commit()
        print(f"检测历史数据库初始化完成：{DETECTION_DB_PATH}")


def save_detection_history(pest_name, confidence, image_base64, user_email=None, **kwargs):
    """
    保存检测历史记录到专用数据库
    新增：user_email 参数用于关联用户
    """
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            # 根据置信度自动判断风险等级
            if 'risk_level' not in kwargs:
                if confidence >= 75:
                    risk_level = 'high'
                elif confidence >= 50:
                    risk_level = 'medium'
                else:
                    risk_level = 'low'
            else:
                risk_level = kwargs['risk_level']

            # 修改SQL，添加 user_email 字段
            cursor.execute('''
                INSERT INTO detection_records 
                (pest_name, confidence, image_base64, original_image_base64, 
                 device_id, location_lat, location_lng, risk_level, notes, crop_type, user_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pest_name,
                confidence,
                image_base64,
                kwargs.get('original_image_base64'),
                kwargs.get('device_id'),
                kwargs.get('location_lat'),
                kwargs.get('location_lng'),
                risk_level,
                kwargs.get('notes'),
                kwargs.get('crop_type'),
                user_email  # 新增
            ))

            conn.commit()
            return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        print(f"保存检测历史失败: {e}")
        return {"success": False, "error": str(e)}


def get_detection_history(user_email=None, limit=20, risk_level=None, pest_name=None):
    """
    获取检测历史记录
    新增：user_email 参数，为 None 时返回全部（管理员），否则返回该用户的
    """
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM detection_records WHERE 1=1'
            params = []

            # 用户隔离：非管理员只能看自己
            if user_email:
                query += ' AND user_email = ?'
                params.append(user_email)

            if risk_level:
                query += ' AND risk_level = ?'
                params.append(risk_level)

            if pest_name:
                query += ' AND pest_name LIKE ?'
                params.append(f'%{pest_name}%')

            query += ' ORDER BY id DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            records = []
            for row in rows:
                record = dict(row)
                cursor.execute('SELECT * FROM pest_details WHERE record_id = ?', (record['id'],))
                details = [dict(r) for r in cursor.fetchall()]
                record['details'] = details
                records.append(record)

            return records
    except Exception as e:
        print(f"获取检测历史失败: {e}")
        return []


def get_detection_by_id(record_id):
    """根据ID获取单条检测记录详情"""
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM detection_records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            if row:
                record = dict(row)
                cursor.execute('SELECT * FROM pest_details WHERE record_id = ?', (record_id,))
                record['details'] = [dict(r) for r in cursor.fetchall()]
                return record
            return None
    except Exception as e:
        print(f"获取记录详情失败: {e}")
        return None


def update_detection_status(record_id, status, notes=None):
    """更新检测记录状态（如标记为已处理）"""
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE detection_records 
                SET status = ?, notes = COALESCE(?, notes), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, notes, record_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"更新记录状态失败: {e}")
        return False


def clear_detection_history(user_email=None, is_admin=False):
    """清空检测历史（修复：增加用户隔离）"""
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            # 如果不是管理员，只能清空自己的记录
            if not is_admin and user_email:
                cursor.execute('DELETE FROM detection_records WHERE user_email = ?', (user_email,))
                deleted = cursor.rowcount
                conn.commit()
                print(f"已清空用户 {user_email} 的 {deleted} 条检测记录")
            else:
                # 管理员可以清空所有（或传入特定用户邮箱）
                if user_email:
                    cursor.execute('DELETE FROM detection_records WHERE user_email = ?', (user_email,))
                else:
                    cursor.execute('DELETE FROM detection_records')
                deleted = cursor.rowcount
                conn.commit()
                print(f"已清空 {deleted} 条检测记录")

            return {"success": True, "deleted_count": deleted}
    except Exception as e:
        print(f"清空检测历史失败: {e}")
        return {"success": False, "error": str(e)}


def delete_detection_record(record_id):
    """删除单条检测记录"""
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM detection_records WHERE id = ?', (record_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"删除记录失败: {e}")
        return False


def get_detection_stats():
    """获取检测统计信息（用于Dashboard展示）"""
    init_detection_database()
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()

            # 总检测次数
            cursor.execute('SELECT COUNT(*) FROM detection_records')
            total = cursor.fetchone()[0]

            # 各风险等级数量
            cursor.execute('''
                SELECT risk_level, COUNT(*) as count 
                FROM detection_records 
                GROUP BY risk_level
            ''')
            risk_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # 今日检测次数
            cursor.execute('''
                SELECT COUNT(*) FROM detection_records 
                WHERE DATE(created_at) = DATE('now')
            ''')
            today = cursor.fetchone()[0]

            return {
                "total": total,
                "today": today,
                "risk_distribution": risk_stats
            }
    except Exception as e:
        print(f"获取统计信息失败: {e}")
        return {}


# ==================== 原有邮箱验证码功能（保持不变） ====================

def check_table_exists():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="email_code"')
        if cursor.fetchone() is None:
            cursor.execute('''
                CREATE TABLE email_code (
                    "to" TEXT, 
                    "code" TEXT, 
                    "expire_time" INTEGER,
                    "created_at" INTEGER DEFAULT (strftime('%s','now'))
                )
            ''')
            cursor.execute('CREATE INDEX idx_email ON email_code("to")')
            cursor.execute('CREATE INDEX idx_created ON email_code("created_at")')
            conn.commit()


def insert_email_code(to, code, expire_time):
    check_table_exists()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 【关键】先删除该邮箱所有旧验证码，确保只有一个有效码
            cursor.execute('DELETE FROM email_code WHERE "to" = ?', (to,))
            # 插入新验证码
            cursor.execute(
                'INSERT INTO email_code ("to", "code", "expire_time") VALUES (?, ?, ?)',
                (to, code, expire_time)
            )
            conn.commit()
            return "success"
    except Exception as e:
        return str(e)


def check_email_code(to, code):
    now = int(time.time())
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT rowid FROM email_code WHERE "to" = ? AND "code" = ? AND "expire_time" > ?',
                (to, code, now)
            )
            result = cursor.fetchone()
            if result is None:
                return False
            # 【关键】验证成功后不删除，保持有效直到过期或被新码替换
            # 如需限制验证次数，可改为标记已使用而非删除
            # cursor.execute('DELETE FROM email_code WHERE rowid = ?', (result['rowid'],))
            # conn.commit()
            return True
    except Exception as e:
        print(f"验证出错: {e}")
        return False

def check_email_daily_limit(to, max_count=10):
    """每天最多发送 10 次验证码"""
    today = time.strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today_start = int(time.mktime(time.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d')))
        cursor.execute(
            'SELECT COUNT(*) FROM email_code WHERE "to" = ? AND created_at >= ?',
            (to, today_start)
        )
        return cursor.fetchone()[0] >= max_count


def check_email_code_limit(to):
    now = int(time.time())
    one_minute_ago = now - 60
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM email_code WHERE "to" = ? AND "created_at" > ?',
            (to, one_minute_ago)
        )
        count = cursor.fetchone()[0]  # 获取发送次数
        return count >= 30  # 【修改】60秒内超过30次才限制


def clean_expired_codes():
    now = int(time.time())
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM email_code WHERE "expire_time" <= ?', (now,))
            deleted = cursor.rowcount
            conn.commit()
            print(f"清理了 {deleted} 条过期验证码")
            return deleted
    except Exception as e:
        print(f"清理失败: {e}")
        return 0


def init_farm_records_db():
    """初始化农事记录数据库"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS farm_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                field TEXT,
                date TEXT NOT NULL,
                operator TEXT,
                content TEXT,              -- 作业内容
                materials TEXT,
                remark TEXT,               -- 新增：备注字段
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


# 在 database.py 中添加农事记录操作函数
def add_farm_record(user_id, record_data):
    """添加农事记录"""
    init_farm_records_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO farm_records 
                (user_id, type, field, date, operator, content, materials, remark, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                record_data.get('type'),
                record_data.get('field'),
                record_data.get('date'),
                record_data.get('operator'),
                record_data.get('content'),
                record_data.get('materials'),
                record_data.get('remark'),  # 新增
                record_data.get('status', 'pending')
            ))
            conn.commit()
            return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        print(f"添加农事记录失败: {e}")
        return {"success": False, "error": str(e)}


def get_farm_records(user_id, type_filter=None, field_filter=None):
    """获取农事记录列表（仅当前用户）"""
    init_farm_records_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM farm_records WHERE user_id = ?'  # 修改
            params = [user_id]

            if type_filter:
                query += ' AND type = ?'
                params.append(type_filter)
            if field_filter:
                query += ' AND field = ?'
                params.append(field_filter)

            query += ' ORDER BY date DESC, created_at DESC'
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"获取农事记录失败: {e}")
        return []


def delete_farm_record(record_id, user_id):
    """删除农事记录（仅删除自己的记录）"""
    init_farm_records_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 先验证记录是否属于该用户
            cursor.execute('SELECT user_id FROM farm_records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "记录不存在"}
            if row['user_id'] != user_id:
                return {"success": False, "error": "无权删除他人记录"}

            cursor.execute('DELETE FROM farm_records WHERE id = ? AND user_id = ?',
                           (record_id, user_id))
            conn.commit()
            return {"success": True, "deleted": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}


def init_users_table():
    """初始化用户表（增强安全字段）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 创建表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE,
                password_hash TEXT,
                name TEXT,
                role TEXT DEFAULT 'farmer',
                status TEXT DEFAULT 'pending',  -- pending/active/banned/locked
                avatar TEXT,
                max_plots INTEGER DEFAULT 5,
                last_login_ip TEXT,
                last_login_at TEXT,
                is_online INTEGER DEFAULT 0,
                login_count INTEGER DEFAULT 0,
                has_password INTEGER DEFAULT 0,  -- 关键字段：0=首次登录需设置，1=已设置
                failed_login_attempts INTEGER DEFAULT 0,  -- 登录失败次数
                locked_until INTEGER DEFAULT 0,  -- 锁定截止时间戳
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT
            )
        ''')

        # 迁移：添加安全字段（兼容旧数据）
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        security_fields = [
            ('failed_login_attempts', 'INTEGER DEFAULT 0'),
            ('locked_until', 'INTEGER DEFAULT 0'),
        ]

        for field_name, field_type in security_fields:
            if field_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                    print(f"已添加安全字段: {field_name}")
                except Exception as e:
                    print(f"添加字段失败: {e}")

        conn.commit()


def check_user_locked(email):
    """检查用户是否因多次登录失败被锁定"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT failed_login_attempts, locked_until 
                FROM users WHERE email = ?
            ''', (email,))
            row = cursor.fetchone()

            if not row:
                return False, None

            locked_until = row['locked_until'] or 0
            failed_attempts = row['failed_login_attempts'] or 0

            now = int(time.time())

            # 如果还在锁定时间内
            if locked_until > now:
                remaining = locked_until - now
                return True, f"账号已锁定，请 {remaining // 60} 分钟后重试"

            # 如果锁定已过期，重置计数
            if locked_until > 0 and locked_until <= now:
                cursor.execute('''
                    UPDATE users SET failed_login_attempts = 0, locked_until = 0 
                    WHERE email = ?
                ''', (email,))
                conn.commit()

            return False, None

    except Exception as e:
        print(f"检查锁定状态失败: {e}")
        return False, None


# 新增：记录登录失败
def record_login_failure(email):
    """记录登录失败，超过5次锁定30分钟"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT failed_login_attempts FROM users WHERE email = ?
            ''', (email,))
            row = cursor.fetchone()

            if not row:
                return

            attempts = (row['failed_login_attempts'] or 0) + 1

            if attempts >= 5:
                # 锁定30分钟
                locked_until = int(time.time()) + 1800
                cursor.execute('''
                    UPDATE users SET failed_login_attempts = ?, locked_until = ? 
                    WHERE email = ?
                ''', (attempts, locked_until, email))
            else:
                cursor.execute('''
                    UPDATE users SET failed_login_attempts = ? WHERE email = ?
                ''', (attempts, email))

            conn.commit()
            return attempts
    except Exception as e:
        print(f"记录登录失败失败: {e}")


# 新增：重置登录失败计数
def reset_login_failure(email):
    """登录成功后重置失败计数"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET failed_login_attempts = 0, locked_until = 0 
                WHERE email = ?
            ''', (email,))
            conn.commit()
    except Exception as e:
        print(f"重置登录失败计数失败: {e}")


# 新增：验证码管理优化（确保旧验证码在发送新码前保持有效）
def refresh_email_code(to, code, expire_time):
    """刷新验证码（删除旧码，插入新码）"""
    check_table_exists()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 删除该邮箱所有旧验证码
            cursor.execute('DELETE FROM email_code WHERE "to" = ?', (to,))
            # 插入新验证码
            cursor.execute(
                'INSERT INTO email_code ("to", "code", "expire_time") VALUES (?, ?, ?)',
                (to, code, expire_time)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"刷新验证码失败: {e}")
        return False


def get_user_by_email(email):
    """根据邮箱获取用户信息"""
    init_users_table()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return None


def create_or_update_user(email, role='farmer', name=None, phone=None):
    """创建或更新用户"""
    init_users_table()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 确保 role 是字符串
            if isinstance(role, list):
                role = ','.join(role)

            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                    UPDATE users 
                    SET last_login_at = CURRENT_TIMESTAMP, 
                        name = COALESCE(?, name),
                        phone = COALESCE(?, phone)
                    WHERE email = ?
                ''', (name, phone, email))
            else:
                cursor.execute('''
                    INSERT INTO users (email, role, name, phone, last_login_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (email, role, name or email.split('@')[0], phone))

            conn.commit()
            return True
    except Exception as e:
        print(f"创建/更新用户失败: {e}")
        return False


def update_user_role(email, role):
    """更新用户角色（管理员功能）"""
    if role not in ['admin', 'farmer']:
        return False
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE email = ?', (role, email))
            conn.commit()
            return True
    except Exception as e:
        print(f"更新角色失败: {e}")
        return False


def get_all_users(role=None, limit=50):
    """获取用户列表（管理员功能）"""
    init_users_table()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if role:
                cursor.execute('''
                    SELECT * FROM users WHERE role = ? 
                    ORDER BY last_login DESC LIMIT ?
                ''', (role, limit))
            else:
                cursor.execute('SELECT * FROM users ORDER BY last_login DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return []


# ==================== 评论数据库管理 ====================

def get_users_roles(user_ids):
    """批量获取用户角色（跨库查询：comments.db -> email.db）"""
    if not user_ids:
        return {}
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(user_ids))
            cursor.execute(
                f'SELECT id, role FROM users WHERE id IN ({placeholders})',
                list(user_ids)
            )
            return {row['id']: row['role'] for row in cursor.fetchall()}
    except Exception as e:
        print(f"批量获取用户角色失败: {e}")
        return {}

def init_comments_database():
    """初始化评论数据库（支持嵌套回复和回复点赞）"""
    with get_comments_db_connection() as conn:
        cursor = conn.cursor()

        # 1. 评论主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                author_name TEXT,
                content TEXT NOT NULL,
                images TEXT,
                location TEXT,
                tags TEXT,
                status TEXT DEFAULT 'pending',
                is_pinned INTEGER DEFAULT 0,
                pin_order INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 2. 回复表（直接包含完整字段，无需后续迁移）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id INTEGER NOT NULL,
                parent_reply_id INTEGER DEFAULT NULL,
                user_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                author_name TEXT,
                content TEXT NOT NULL,
                to_user TEXT,
                likes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_reply_id) REFERENCES comment_replies(id) ON DELETE CASCADE
            )
        ''')

        # 3. 点赞记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_likes (
                comment_id INTEGER,
                user_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (comment_id, user_email),
                FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
            )
        ''')

        # 4. 回复点赞记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reply_likes (
                reply_id INTEGER,
                user_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (reply_id, user_email),
                FOREIGN KEY (reply_id) REFERENCES comment_replies(id) ON DELETE CASCADE
            )
        ''')

        # 5. 创建索引（确保在表结构完整后执行）
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comment_status ON comments(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comment_pinned ON comments(is_pinned)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_comment_created ON comments(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reply_comment ON comment_replies(comment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reply_parent ON comment_replies(parent_reply_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reply_likes ON reply_likes(reply_id)')

        conn.commit()
        print(f"评论数据库初始化完成：{COMMENTS_DB_PATH}（已支持嵌套回复和回复点赞）")

def get_comment_replies(comment_id, cursor=None, user_email=None):
    """获取指定评论的所有回复（支持嵌套结构）"""
    close_conn = False
    if cursor is None:
        conn = get_comments_db_connection()
        cursor = conn.cursor()
        close_conn = True

    try:
        # 获取所有顶级回复（直接回复评论的）
        cursor.execute(
            """SELECT id, comment_id, parent_reply_id, user_id, user_email, author_name, 
                   content, to_user, likes, created_at
            FROM comment_replies 
            WHERE comment_id = ? AND parent_reply_id IS NULL
            ORDER BY created_at ASC""",
            (comment_id,)
        )

        rows = cursor.fetchall()
        replies = []
        for row in rows:
            reply = dict(row)
            # 格式化时间显示
            if reply.get('created_at'):
                try:
                    dt = datetime.fromisoformat(reply['created_at'])
                    reply['created_at'] = dt.strftime('%m-%d %H:%M')
                except:
                    pass

            # 获取当前用户是否点赞了这个回复
            if user_email:
                cursor.execute(
                    "SELECT 1 FROM reply_likes WHERE reply_id = ? AND user_email = ?",
                    (reply['id'], user_email)
                )
                reply['is_liked'] = cursor.fetchone() is not None
            else:
                reply['is_liked'] = False

            # 递归获取子回复（回复这个回复的）
            reply['nested_replies'] = get_nested_replies(reply['id'], cursor, user_email)
            replies.append(reply)

        return replies

    except Exception as e:
        print(f"获取回复失败: {e}")
        return []
    finally:
        if close_conn:
            conn.close()


def get_nested_replies(parent_reply_id, cursor, user_email=None):
    """递归获取嵌套回复"""
    try:
        cursor.execute(
            """SELECT id, comment_id, parent_reply_id, user_id, user_email, author_name, 
                   content, to_user, likes, created_at
            FROM comment_replies 
            WHERE parent_reply_id = ?
            ORDER BY created_at ASC""",
            (parent_reply_id,)
        )

        rows = cursor.fetchall()
        replies = []
        for row in rows:
            reply = dict(row)
            # 格式化时间
            if reply.get('created_at'):
                try:
                    dt = datetime.fromisoformat(reply['created_at'])
                    reply['created_at'] = dt.strftime('%m-%d %H:%M')
                except:
                    pass

            # 检查当前用户是否点赞
            if user_email:
                cursor.execute(
                    "SELECT 1 FROM reply_likes WHERE reply_id = ? AND user_email = ?",
                    (reply['id'], user_email)
                )
                reply['is_liked'] = cursor.fetchone() is not None
            else:
                reply['is_liked'] = False

            # 继续获取子回复（理论上可以无限嵌套，但前端只展示2层）
            reply['nested_replies'] = get_nested_replies(reply['id'], cursor, user_email)
            replies.append(reply)

        return replies
    except Exception as e:
        print(f"获取嵌套回复失败: {e}")
        return []

def get_comment_by_id(comment_id):
    """根据ID获取评论"""
    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"获取评论失败: {e}")
        return None


def add_reply(comment_id, user_email, content, to_user=None, parent_reply_id=None):
    """添加回复（支持回复的回复）"""
    init_users_table()
    init_comments_database()

    try:
        # 验证评论存在
        comment = get_comment_by_id(comment_id)
        if not comment:
            return {"success": False, "error": "评论不存在或已被删除"}

        # 如果是回复某个回复，验证父回复存在
        if parent_reply_id:
            with get_comments_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM comment_replies WHERE id = ?", (parent_reply_id,))
                if not cursor.fetchone():
                    return {"success": False, "error": "回复的目标不存在"}

        # 获取用户信息
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name FROM users WHERE email = ?', (user_email,))
            user = cursor.fetchone()
            if not user:
                return {"success": False, "error": "用户不存在"}

        with get_comments_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """INSERT INTO comment_replies 
                   (comment_id, parent_reply_id, user_id, user_email, author_name, content, to_user, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (comment_id, parent_reply_id, user['id'], user_email, user['name'], content, to_user, now)
            )
            reply_id = cursor.lastrowid
            conn.commit()

            # 返回完整的回复数据
            return {
                "success": True,
                "id": reply_id,
                "data": {
                    "id": reply_id,
                    "comment_id": comment_id,
                    "parent_reply_id": parent_reply_id,
                    "user_email": user_email,
                    "author_name": user['name'],
                    "content": content,
                    "to_user": to_user,
                    "likes": 0,
                    "is_liked": False,
                    "created_at": datetime.now().strftime('%m-%d %H:%M'),
                    "children": []
                }
            }
    except Exception as e:
        print(f"添加回复失败: {e}")
        return {"success": False, "error": str(e)}


def toggle_reply_like(reply_id, user_email):
    """切换回复点赞状态"""
    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()

            # 检查是否已点赞
            cursor.execute('SELECT 1 FROM reply_likes WHERE reply_id = ? AND user_email = ?',
                           (reply_id, user_email))
            liked = cursor.fetchone()

            if liked:
                # 取消赞
                cursor.execute('DELETE FROM reply_likes WHERE reply_id = ? AND user_email = ?',
                               (reply_id, user_email))
                cursor.execute('UPDATE comment_replies SET likes = likes - 1 WHERE id = ?', (reply_id,))
                conn.commit()
                return {"success": True, "liked": False}
            else:
                # 点赞
                cursor.execute('INSERT INTO reply_likes (reply_id, user_email) VALUES (?, ?)',
                               (reply_id, user_email))
                cursor.execute('UPDATE comment_replies SET likes = likes + 1 WHERE id = ?', (reply_id,))
                conn.commit()
                return {"success": True, "liked": True}
    except Exception as e:
        print(f"回复点赞操作失败: {e}")
        return {"success": False, "error": str(e)}


def delete_reply(reply_id, user_email, is_admin=False):
    """删除回复（仅本人或管理员可删除，级联删除所有子回复）- 带事务回滚"""
    conn = get_comments_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN')

        # 查询回复信息
        cursor.execute('SELECT user_email FROM comment_replies WHERE id = ?', (reply_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return {"success": False, "error": "回复不存在"}

        # 权限检查
        if not is_admin and row['user_email'] != user_email:
            conn.rollback()
            return {"success": False, "error": "无权删除他人回复"}

        # 级联删除该回复的所有子回复和点赞记录
        def delete_nested_replies(parent_id):
            cursor.execute('SELECT id FROM comment_replies WHERE parent_reply_id = ?', (parent_id,))
            children = cursor.fetchall()
            for child in children:
                delete_nested_replies(child['id'])  # 递归删除子回复
                cursor.execute('DELETE FROM reply_likes WHERE reply_id = ?', (child['id'],))
                cursor.execute('DELETE FROM comment_replies WHERE id = ?', (child['id'],))

        # 删除当前回复的子回复
        delete_nested_replies(reply_id)

        # 删除当前回复的点赞
        cursor.execute('DELETE FROM reply_likes WHERE reply_id = ?', (reply_id,))

        # 删除当前回复
        cursor.execute('DELETE FROM comment_replies WHERE id = ?', (reply_id,))

        conn.commit()
        return {"success": True, "message": "回复已删除"}

    except Exception as e:
        conn.rollback()
        print(f"删除回复失败（已回滚）: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def delete_comment(comment_id, user_email, is_admin=False):
    """删除评论（软删除，级联删除所有相关数据）- 带事务回滚"""
    conn = get_comments_db_connection()
    cursor = conn.cursor()

    try:
        # 开始事务（显式控制）
        cursor.execute('BEGIN')

        # 查询评论信息
        cursor.execute('SELECT user_email, is_pinned FROM comments WHERE id = ?', (comment_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return {"success": False, "error": "评论不存在"}

        # 权限检查
        if not is_admin and row['user_email'] != user_email:
            conn.rollback()
            return {"success": False, "error": "无权删除他人评论"}

        # 级联删除：先删子回复的点赞 -> 子回复 -> 评论的点赞 -> 评论
        def delete_nested_replies(parent_id):
            cursor.execute('SELECT id FROM comment_replies WHERE parent_reply_id = ?', (parent_id,))
            children = cursor.fetchall()
            for child in children:
                delete_nested_replies(child['id'])  # 递归删除孙回复
                # 删除回复的点赞
                cursor.execute('DELETE FROM reply_likes WHERE reply_id = ?', (child['id'],))
                # 删除回复
                cursor.execute('DELETE FROM comment_replies WHERE id = ?', (child['id'],))

        # 获取该评论的所有顶级回复
        cursor.execute('SELECT id FROM comment_replies WHERE comment_id = ? AND parent_reply_id IS NULL', (comment_id,))
        top_replies = cursor.fetchall()

        for reply in top_replies:
            delete_nested_replies(reply['id'])
            cursor.execute('DELETE FROM reply_likes WHERE reply_id = ?', (reply['id'],))
            cursor.execute('DELETE FROM comment_replies WHERE id = ?', (reply['id'],))

        # 删除评论的点赞记录
        cursor.execute('DELETE FROM comment_likes WHERE comment_id = ?', (comment_id,))

        # 软删除评论本身（保留数据可恢复）
        cursor.execute('''
            UPDATE comments 
            SET status = 'deleted', updated_at = CURRENT_TIMESTAMP, is_pinned = 0
            WHERE id = ?
        ''', (comment_id,))

        conn.commit()
        return {"success": True, "message": "评论已删除"}

    except Exception as e:
        conn.rollback()  # 关键：异常时回滚所有操作
        print(f"删除评论失败（已回滚）: {e}")
        return {"success": False, "error": f"删除失败: {str(e)}"}
    finally:
        conn.close()  # 确保连接关闭


def toggle_like(comment_id, user_email):
    """切换点赞状态"""
    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()
            # 检查是否已点赞
            cursor.execute('SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_email = ?',
                           (comment_id, user_email))
            liked = cursor.fetchone()

            if liked:
                # 取消赞
                cursor.execute('DELETE FROM comment_likes WHERE comment_id = ? AND user_email = ?',
                               (comment_id, user_email))
                cursor.execute('UPDATE comments SET likes = likes - 1 WHERE id = ?', (comment_id,))
                conn.commit()
                return {"success": True, "liked": False}
            else:
                # 点赞
                cursor.execute('INSERT INTO comment_likes (comment_id, user_email) VALUES (?, ?)',
                               (comment_id, user_email))
                cursor.execute('UPDATE comments SET likes = likes + 1 WHERE id = ?', (comment_id,))
                conn.commit()
                return {"success": True, "liked": True}
    except Exception as e:
        print(f"点赞操作失败: {e}")
        return {"success": False, "error": str(e)}


def get_comment_stats():
    """获取评论统计数据（修复版：包含完整状态统计）"""
    init_comments_database()
    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()

            # 总评论数（排除已删除）
            cursor.execute("SELECT COUNT(*) FROM comments WHERE status != 'deleted'")
            total = cursor.fetchone()[0]

            # 待审核（不需要再检查 != 'deleted'，因为 pending 不可能等于 deleted）
            cursor.execute("SELECT COUNT(*) FROM comments WHERE status = 'pending'")
            pending = cursor.fetchone()[0]

            # 已通过
            cursor.execute("SELECT COUNT(*) FROM comments WHERE status = 'approved'")
            approved = cursor.fetchone()[0]

            # 已拒绝
            cursor.execute("SELECT COUNT(*) FROM comments WHERE status = 'rejected'")
            rejected = cursor.fetchone()[0]

            # 置顶精华
            cursor.execute("SELECT COUNT(*) FROM comments WHERE status = 'approved' AND is_pinned = 1")
            pinned = cursor.fetchone()[0]

            # 今日新增
            cursor.execute("SELECT COUNT(*) FROM comments WHERE DATE(created_at) = DATE('now')")
            today = cursor.fetchone()[0]

            return {
                "total": total or 0,
                "pending": pending or 0,
                "approved": approved or 0,
                "rejected": rejected or 0,
                "pinned": pinned or 0,
                "today": today or 0
            }
    except Exception as e:
        print(f"获取统计失败: {e}")
        return {
            "total": 0, "pending": 0, "approved": 0,
            "rejected": 0, "pinned": 0, "today": 0,
            "error": str(e)
        }

def init_user_management_tables():
    """初始化用户管理所需的所有表（适配管理界面）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 统一使用 TIMESTAMP 类型
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'farmer',
            status TEXT DEFAULT 'pending',
            avatar TEXT,
            max_plots INTEGER DEFAULT 5,
            last_login_ip TEXT,
            last_login_at TIMESTAMP,
            is_online INTEGER DEFAULT 0,
            login_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    print("创建 users 表（TIMESTAMP 格式）")

    # 创建索引（忽略已存在的错误）
    indexes = [
        ('idx_users_phone', 'phone'),
        ('idx_users_role', 'role'),
        ('idx_users_status', 'status'),
        ('idx_users_online', 'is_online')
    ]

    for idx_name, col_name in indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON users({col_name})')
        except sqlite3.OperationalError:
            pass

    # 2. 创建地块表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            crop_type TEXT,
            area REAL,
            lat REAL,
            lng REAL,
            device_id TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. 创建用户-地块关联表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plot_id INTEGER NOT NULL,
            is_default INTEGER DEFAULT 0,
            bind_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plot_id) REFERENCES plots(id) ON DELETE CASCADE,
            UNIQUE(user_id, plot_id)
        )
    ''')

    # 4. 创建权限表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            menu_code TEXT NOT NULL,
            can_view INTEGER DEFAULT 0,
            can_edit INTEGER DEFAULT 0,
            can_delete INTEGER DEFAULT 0,
            UNIQUE(role, menu_code)
        )
    ''')

    # 5. 初始化默认权限数据
    default_perms = [
        ('admin', 'user_manage', 1, 1, 1),
        ('admin', 'plot_manage', 1, 1, 1),
        ('admin', 'comment_audit', 1, 1, 1),
        ('admin', 'system_settings', 1, 1, 1),
        ('admin', 'detection_view', 1, 1, 1),
        ('farmer', 'plot_view', 1, 0, 0),
        ('farmer', 'detection_create', 1, 1, 0),
        ('farmer', 'comment_create', 1, 1, 0),
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO user_permissions (role, menu_code, can_view, can_edit, can_delete)
        VALUES (?, ?, ?, ?, ?)
    ''', default_perms)

    conn.commit()
    conn.close()
    print("用户管理表初始化完成")


def update_user(user_id, update_data):
    """更新用户信息（适配编辑功能）- 带事务回滚"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN')

        allowed_fields = ['name', 'email', 'role', 'status', 'avatar', 'max_plots']
        sets = []
        values = []

        for field in allowed_fields:
            if field in update_data:
                sets.append(f"{field} = ?")
                values.append(update_data[field])

        if not sets:
            conn.rollback()
            return {"success": False, "error": "无有效更新字段"}

        # 添加 updated_at 更新
        sets.append("updated_at = datetime('now')")
        values.append(user_id)

        cursor.execute(f'''
            UPDATE users 
            SET {', '.join(sets)}
            WHERE id = ?
        ''', values)

        # 如果更新了角色，同步更新地块限制
        if 'role' in update_data:
            if update_data['role'] == 'admin':
                cursor.execute("UPDATE users SET max_plots = 0 WHERE id = ?", (user_id,))
            else:
                cursor.execute("UPDATE users SET max_plots = 5 WHERE id = ?", (user_id,))

        if 'permissions' in update_data and update_data.get('role') == 'admin':
            # 先删除旧权限
            cursor.execute("DELETE FROM user_permissions WHERE role = (SELECT role FROM users WHERE id = ?)",
                           (user_id,))
            # 插入新权限
            for perm in update_data['permissions']:
                cursor.execute('''
                            INSERT OR REPLACE INTO user_permissions (role, menu_code, can_view, can_edit, can_delete)
                            VALUES ((SELECT role FROM users WHERE id = ?), ?, 1, 1, 1)
                        ''', (user_id, perm))

        # 如果更新了地块绑定
        if 'plot_ids' in update_data and update_data.get('role') != 'admin':
            # 先解除旧绑定
            cursor.execute("DELETE FROM user_plots WHERE user_id = ?", (user_id,))
            # 重新绑定
            if update_data['plot_ids']:
                for plot_id in update_data['plot_ids'][:5]:  # 最多5个
                    try:
                        cursor.execute('''
                            INSERT INTO user_plots (user_id, plot_id) 
                            VALUES (?, ?)
                        ''', (user_id, plot_id))
                    except sqlite3.IntegrityError:
                        pass

        conn.commit()
        return {"success": True}

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def update_user_status(user_id, status):
    """更新用户状态（active/pending/banned）- 修复：更新 updated_at"""
    if status not in ['active', 'pending', 'banned']:
        return {"success": False, "error": "无效状态"}

    conn = get_db_connection()
    cursor = conn.cursor()
    # 同时更新 updated_at
    cursor.execute(
        "UPDATE users SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, user_id)
    )
    conn.commit()
    conn.close()
    return {"success": True}


def batch_update_status(user_ids, status):
    """批量更新状态（适配底部悬浮批量操作栏）- 修复：更新 updated_at"""
    if status not in ['active', 'banned']:
        return {"success": False, "error": "无效状态"}

    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ','.join(['?' for _ in user_ids])
    # 同时更新 updated_at
    cursor.execute(f'''
        UPDATE users 
        SET status = ?, updated_at = datetime('now')
        WHERE id IN ({placeholders})
    ''', [status] + user_ids)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return {"success": True, "affected": affected}


def get_user_list(filters=None, page=1, per_page=10):
    init_user_management_tables()
    conn = get_db_connection()  # 改为手动获取
    try:
        cursor = conn.cursor()

        where_clauses = ["1=1"]
        params = []

        if filters:
            if filters.get('id'):
                where_clauses.append("u.id = ?")
                params.append(filters['id'])
            if filters.get('role'):
                where_clauses.append("role = ?")
                params.append(filters['role'])
            if filters.get('status'):
                where_clauses.append("status = ?")
                params.append(filters['status'])
            if filters.get('keyword'):
                where_clauses.append("(phone LIKE ? OR name LIKE ?)")
                keyword = f"%{filters['keyword']}%"
                params.extend([keyword, keyword])

        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM users WHERE {' AND '.join(where_clauses)}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # 查询数据（带地块数量统计）
        sql = f'''
                SELECT 
                    u.id, u.phone, u.email, u.name, u.role, u.status, 
                    u.avatar, u.max_plots, u.last_login_ip, u.last_login_at, 
                    u.is_online, u.login_count, u.created_at, u.updated_at,
                    (SELECT COUNT(*) FROM user_plots WHERE user_id = u.id) as plot_count,
                    (SELECT GROUP_CONCAT(p.name) FROM user_plots up 
                     JOIN plots p ON up.plot_id = p.id 
                     WHERE up.user_id = u.id LIMIT 5) as plot_names
                FROM users u
                WHERE {' AND '.join(where_clauses)}
                ORDER BY u.created_at DESC
                LIMIT ? OFFSET ?
            '''
        params.extend([per_page, (page - 1) * per_page])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # 获取关联统计（评论数、识别次数等，用于活跃度）
        users = []
        for row in rows:
            user = dict(row)
            # 转换布尔值
            user['is_online'] = bool(user['is_online'])
            # 添加权限字段（从user_permissions表查询）
            user['permissions'] = get_user_permissions(user['id'])
            user['stats'] = get_user_activity_stats(user['id'])
            users.append(user)

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "data": users
        }
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return {"total": 0, "page": page, "per_page": per_page, "data": []}
    finally:
        conn.close()

def get_user_permissions(user_id):
    """获取用户权限列表"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT menu_code, can_view, can_edit, can_delete 
                FROM user_permissions 
                WHERE role = (SELECT role FROM users WHERE id = ?)
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except:
        return []


def get_user_activity_stats(user_id):
    """获取用户活跃度统计（用于界面展示）"""
    stats = {"comments": 0, "detections": 0, "likes": 0}

    # 评论数（使用你已有的 comments 数据库）
    try:
        conn = get_comments_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM comments WHERE user_id = ?", (user_id,))
        stats['comments'] = cursor.fetchone()[0]
        conn.close()
    except:
        pass

    # 检测识别次数（使用你已有的 detection 数据库）
    try:
        conn = get_detection_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM detection_records WHERE user_id = ?", (user_id,))
        stats['detections'] = cursor.fetchone()[0]
        conn.close()
    except:
        pass

    return stats


def get_user_dashboard_stats():
    """
    获取用户管理看板统计数据
    对应界面：总用户/在线/待审核/已禁用
    """
    init_user_management_tables()
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}

    # 总用户数
    cursor.execute("SELECT COUNT(*) FROM users")
    stats['total'] = cursor.fetchone()[0]

    # 在线用户（最近30分钟有活动）
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE is_online = 1 
        AND last_login_at > datetime('now', '-30 minutes')
    ''')
    stats['online'] = cursor.fetchone()[0]

    # 待审核（pending）
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
    stats['pending'] = cursor.fetchone()[0]

    # 已禁用（banned）
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'banned'")
    stats['banned'] = cursor.fetchone()[0]

    # 角色分布（用于标签页显示数字）
    cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    stats['role_dist'] = dict(cursor.fetchall())

    conn.close()
    return stats


def create_user(user_data):
    """创建新用户（适配"新增用户"按钮）- 带事务回滚"""
    init_user_management_tables()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN')

        # 检查手机号重复
        cursor.execute("SELECT 1 FROM users WHERE phone = ?", (user_data['phone'],))
        if cursor.fetchone():
            conn.rollback()
            return {"success": False, "error": "手机号已存在"}

        # 生成随机初始密码
        import random
        import string
        default_pwd = ''.join(random.choices(string.ascii_uppercase, k=1)) + \
                      ''.join(random.choices(string.ascii_lowercase + string.digits, k=7)) + \
                      '@Agri'

        # 哈希密码（实际生产环境）
        pwd_hash = hash_password(default_pwd)

        cursor.execute('''
            INSERT INTO users (phone, name, email, role, status, password_hash, max_plots, has_password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data['phone'],
            user_data['name'],
            user_data.get('email'),
            user_data.get('role', 'farmer'),
            user_data.get('status', 'pending'),
            pwd_hash,
            5 if user_data.get('role') == 'farmer' else 0,
            1
        ))

        user_id = cursor.lastrowid

        # 绑定地块（如果是农户且提供了plot_ids）
        if user_data.get('role') == 'farmer' and user_data.get('plot_ids'):
            # 检查当前绑定数量
            cursor.execute("SELECT COUNT(*) FROM user_plots WHERE user_id = ?", (user_id,))
            current_count = cursor.fetchone()[0]
            max_plots = 5

            available = max_plots - current_count
            plot_ids = user_data['plot_ids'][:available]

            for plot_id in plot_ids:
                try:
                    cursor.execute('''
                        INSERT INTO user_plots (user_id, plot_id) 
                        VALUES (?, ?)
                    ''', (user_id, plot_id))
                except sqlite3.IntegrityError:
                    pass  # 已存在则跳过

        conn.commit()
        return {
            "success": True,
            "id": user_id,
            "initial_password": default_pwd,
            "message": "创建成功，初始密码已生成"
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def bind_plots_to_user(user_id, plot_ids, cursor=None):
    """
    绑定地块到用户（限制最多5个）- 支持事务上下文
    供 create_user 和 update_user 内部调用
    """
    close_conn = False
    if cursor is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        close_conn = True
        try:
            cursor.execute('BEGIN')
        except:
            pass  # 可能已有事务

    try:
        # 检查当前绑定数量
        cursor.execute("SELECT COUNT(*) FROM user_plots WHERE user_id = ?", (user_id,))
        current_count = cursor.fetchone()[0]
        max_plots = 5

        cursor.execute("SELECT max_plots FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0] is not None:
            max_plots = row[0]

        available = max_plots - current_count
        if len(plot_ids) > available:
            if close_conn:
                conn.rollback()
                conn.close()
            raise Exception(f"超出最大绑定限制，最多还能绑定{available}个地块")

        # 插入新绑定（跳过已存在的）
        inserted = 0
        for plot_id in plot_ids[:available]:
            try:
                cursor.execute('''
                    INSERT INTO user_plots (user_id, plot_id) 
                    VALUES (?, ?)
                ''', (user_id, plot_id))
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # 已存在则跳过

        if close_conn:
            conn.commit()
            conn.close()

        return {"success": True, "inserted": inserted}

    except Exception as e:
        if close_conn:
            try:
                conn.rollback()
            except:
                pass
            conn.close()
        raise e


def get_user_plots(user_id):
    """获取用户绑定的所有地块详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, up.is_default, up.bind_at 
        FROM user_plots up
        JOIN plots p ON up.plot_id = p.id
        WHERE up.user_id = ?
    ''', (user_id,))
    plots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return plots


def unbind_plot(user_id, plot_id):
    """解绑单个地块"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_plots WHERE user_id = ? AND plot_id = ?",
        (user_id, plot_id)
    )
    conn.commit()
    conn.close()
    return {"success": True}


def transfer_plots(from_user_id, to_user_id, plot_ids=None):
    """批量转移地块（带事务回滚）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN')

        if plot_ids is None:
            # 转移所有地块
            cursor.execute(
                "SELECT plot_id FROM user_plots WHERE user_id = ?",
                (from_user_id,)
            )
            plot_ids = [row[0] for row in cursor.fetchall()]

        # 检查目标用户剩余额度
        cursor.execute(
            "SELECT COUNT(*) FROM user_plots WHERE user_id = ?",
            (to_user_id,)
        )
        target_current = cursor.fetchone()[0]

        cursor.execute("SELECT max_plots FROM users WHERE id = ?", (to_user_id,))
        row = cursor.fetchone()
        target_max = row[0] if row else 5

        if target_current + len(plot_ids) > target_max:
            conn.rollback()
            return {"success": False, "error": "目标用户地块配额不足"}

        # 执行转移
        for plot_id in plot_ids:
            cursor.execute('''
                UPDATE user_plots SET user_id = ? 
                WHERE user_id = ? AND plot_id = ?
            ''', (to_user_id, from_user_id, plot_id))

        conn.commit()
        return {"success": True, "transferred": len(plot_ids)}

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


import pandas as pd
from io import BytesIO


def batch_import_users(file_content, file_type='xlsx'):
    """批量导入用户（Excel/CSV）- 优化版带单条回滚"""
    try:
        # 解析文件
        if file_type == 'xlsx':
            df = pd.read_excel(BytesIO(file_content))
        else:
            df = pd.read_csv(BytesIO(file_content))

        required_cols = ['phone', 'name', 'role']
        for col in required_cols:
            if col not in df.columns:
                return {"success": False, "error": f"缺少必要列: {col}"}

        results = {"total": len(df), "success": 0, "failed": 0, "errors": []}

        for idx, row in df.iterrows():
            try:
                user_data = {
                    'phone': str(row['phone']).strip(),
                    'name': str(row['name']).strip(),
                    'role': str(row['role']).strip().lower(),
                    'email': str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None,
                    'status': str(row.get('status', 'pending')).strip(),
                    'plot_ids': []
                }

                # 解析地块ID
                if 'plot_ids' in row and pd.notna(row['plot_ids']):
                    plot_str = str(row['plot_ids'])
                    user_data['plot_ids'] = [int(x.strip()) for x in plot_str.split(',') if x.strip().isdigit()]

                # 单条创建（内部有独立事务）
                result = create_user(user_data)
                if result['success']:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"行{idx + 2}: {result['error']}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"行{idx + 2}: {str(e)}")

        return {"success": True, **results}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_import_template():
    """生成导入模板数据"""
    template_data = {
        'phone': ['13800138001', '13900139002', '13700137003'],
        'name': ['张三', '李四', '王五'],
        'role': ['farmer', 'farmer', 'admin'],
        'email': ['zhang@example.com', '', ''],
        'status': ['active', 'pending', 'active'],
        'plot_ids': ['1,2', '3', '']  # 农户可绑定，管理员留空
    }
    df = pd.DataFrame(template_data)
    return df.to_excel(index=False, engine='openpyxl')

def update_user_online_status(user_id, is_online, ip=None):
    """更新用户在线状态（在登录/心跳时调用）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET is_online = ?, last_login_ip = ?, last_login_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (1 if is_online else 0, ip, user_id))
    conn.commit()
    conn.close()

def check_offline_users(timeout_minutes=30):
    """
    检查超时离线用户（后台任务调用）
    超过30分钟无活动标记为离线
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET is_online = 0 
        WHERE is_online = 1 
        AND last_login_at < datetime('now', ?)
    ''', (f'-{timeout_minutes} minutes',))
    conn.commit()
    conn.close()


# ==================== 地块管理函数（为用户管理界面提供数据） ====================

def get_plots_list(keyword=None, status='active', limit=100):
    """
    获取地块列表（用于用户管理界面的地块选择器）

    Args:
        keyword: 搜索关键词（地块名称）
        status: 地块状态筛选
        limit: 返回数量限制
    """
    init_user_management_tables()  # 确保表存在
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = '''
        SELECT 
            p.*,
            (SELECT COUNT(*) FROM user_plots WHERE plot_id = p.id) as bound_count,
            (SELECT u.name || ' (' || u.phone || ')' 
             FROM user_plots up 
             JOIN users u ON up.user_id = u.id 
             WHERE up.plot_id = p.id 
             LIMIT 1) as bound_to
        FROM plots p
        WHERE p.status = ?
    '''
    params = [status]

    if keyword:
        sql += ' AND p.name LIKE ?'
        params.append(f'%{keyword}%')

    sql += ' ORDER BY p.id DESC LIMIT ?'
    params.append(limit)

    cursor.execute(sql, params)
    plots = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return plots


def get_plot_by_id(plot_id):
    """根据ID获取单个地块详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plots WHERE id = ?', (plot_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_plot(plot_data):
    """
    创建新地块

    plot_data: {
        'name': '地块名称',
        'location': '位置描述',
        'crop_type': '作物类型',
        'area': 面积（亩）,
        'lat': 纬度,
        'lng': 经度,
        'device_id': '设备ID（可选）'
    }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO plots (name, location, crop_type, area, lat, lng, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            plot_data.get('name'),
            plot_data.get('location'),
            plot_data.get('crop_type'),
            plot_data.get('area'),
            plot_data.get('lat'),
            plot_data.get('lng'),
            plot_data.get('device_id')
        ))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def update_plot(plot_id, plot_data):
    """更新地块信息"""
    conn = get_db_connection()
    cursor = conn.cursor()

    allowed_fields = ['name', 'location', 'crop_type', 'area', 'lat', 'lng', 'device_id', 'status']
    sets = []
    values = []

    for field in allowed_fields:
        if field in plot_data:
            sets.append(f"{field} = ?")
            values.append(plot_data[field])

    if not sets:
        return {"success": False, "error": "无有效更新字段"}

    values.append(plot_id)

    try:
        cursor.execute(f'''
            UPDATE plots SET {', '.join(sets)} WHERE id = ?
        ''', values)
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def delete_plot(plot_id):
    """删除地块（仅当未被绑定时可删除）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 检查是否已被绑定
    cursor.execute("SELECT COUNT(*) FROM user_plots WHERE plot_id = ?", (plot_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return {"success": False, "error": "该地块已被用户绑定，无法删除"}

    try:
        cursor.execute("DELETE FROM plots WHERE id = ?", (plot_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_available_plots(user_id=None):
    """
    获取可选的地块列表（排除已被其他用户绑定的，或标记当前用户已绑定的）
    用于前端选择器显示哪些地块可用
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = '''
        SELECT p.*, 
               CASE WHEN up.user_id IS NOT NULL THEN 1 ELSE 0 END as is_bound,
               up.user_id as bound_user_id
        FROM plots p
        LEFT JOIN user_plots up ON p.id = up.plot_id
        WHERE p.status = 'active'
    '''

    cursor.execute(sql)
    rows = cursor.fetchall()

    plots = []
    for row in rows:
        plot = dict(row)
        # 标记可用性：未绑定，或当前用户已绑定
        if plot['bound_user_id'] is None:
            plot['availability'] = 'available'  # 完全可用
        elif user_id and plot['bound_user_id'] == user_id:
            plot['availability'] = 'owned'  # 当前用户已拥有
        else:
            plot['availability'] = 'occupied'  # 被其他用户占用

        plots.append(plot)

    conn.close()
    return plots


def init_farm_management_tables():
    """初始化农场管理相关表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 添加设备表
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT,
                icon TEXT DEFAULT 'fas fa-video',
                location TEXT,
                status TEXT DEFAULT 'offline',
                last_online TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

    # 添加活动表
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS farm_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                type_label TEXT,
                content TEXT NOT NULL,
                plot_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')


    # 地块表 - 统一使用 TIMESTAMP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS farm_plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            area REAL NOT NULL,
            crop TEXT,
            plantDate DATE,
            status TEXT DEFAULT 'growing',
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 统一
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # plots 表（用户管理界面用的）- 如果存在需要重建或使用迁移脚本
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            crop_type TEXT,
            area REAL,
            lat REAL,
            lng REAL,
            device_id TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 统一
        )
    ''')

    # user_plots 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plot_id INTEGER NOT NULL,
            is_default INTEGER DEFAULT 0,
            bind_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 统一
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plot_id) REFERENCES plots(id) ON DELETE CASCADE,
            UNIQUE(user_id, plot_id)
        )
    ''')

    # 其余表保持不变
    conn.commit()
    conn.close()


def add_farm_activity(user_id, activity_type, content, plot_name=None):
    """添加农事活动，自动转换中文标签"""
    type_map = {
        'irrigation': '灌溉',
        'fertilize': '施肥',
        'pest': '病虫害防治',
        'harvest': '收获',
        'sow': '播种',
        'weed': '除草',
        'inspect': '巡查'
    }

    type_label = type_map.get(activity_type, '其他农事')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO farm_activities (user_id, type, type_label, content, plot_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, activity_type, type_label, content, plot_name))
    conn.commit()
    conn.close()
    return {"success": True}


# 在 database.py 中确认这些函数已实现

def get_user_farm_stats_fixed(user_id, user_email=None):
    """修复版：获取用户农场统计"""
    init_farm_management_tables()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 总面积
    cursor.execute("SELECT COALESCE(SUM(area), 0) FROM farm_plots WHERE user_id = ?", (user_id,))
    total_area = cursor.fetchone()[0]

    # 种植作物种类数
    cursor.execute("SELECT COUNT(DISTINCT crop) FROM farm_plots WHERE user_id = ?", (user_id,))
    crop_types = cursor.fetchone()[0]

    # 在线设备数（修复：添加user_id过滤）
    cursor.execute("""
        SELECT COUNT(*) FROM user_devices 
        WHERE user_id = ? AND status = 'online'
    """, (user_id,))
    online_devices = cursor.fetchone()[0]

    # 地块数量
    cursor.execute("SELECT COUNT(*) FROM farm_plots WHERE user_id = ?", (user_id,))
    plot_count = cursor.fetchone()[0]

    # 待处理预警（从农场地块状态为warning的数量计算）
    cursor.execute("""
        SELECT COUNT(*) FROM farm_plots 
        WHERE user_id = ? AND status = 'warning'
    """, (user_id,))
    warnings = cursor.fetchone()[0]

    conn.close()

    return {
        "total_area": float(total_area or 0),
        "plot_count": plot_count or 0,
        "crop_types": crop_types or 0,
        "online_devices": online_devices or 0,
        "warnings": warnings or 0
    }


def get_farm_plots_by_user(user_id):
    """获取用户的农场地块列表"""
    init_farm_management_tables()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, area, crop as crop_type, plantDate as plant_date, 
                       status, location, created_at
                FROM farm_plots 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            plots = []
            for row in rows:
                plot = dict(row)
                # 转换状态显示
                status_map = {
                    'growing': '正常生长',
                    'warning': '异常预警',
                    'harvested': '已收获'
                }
                plot['status_text'] = status_map.get(plot['status'], '正常生长')
                plots.append(plot)
            return plots
    except Exception as e:
        print(f"获取农场地块失败: {e}")
        return []


def get_user_devices(user_id):
    """获取用户设备（确保字段完整）"""
    init_farm_management_tables()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, type, icon, location, status, last_online
                FROM user_devices 
                WHERE user_id = ?
            ''', (user_id,))
            devices = [dict(row) for row in cursor.fetchall()]

            for device in devices:
                device['online'] = device.get('status') == 'online'

            # 计算统计数据
            total = len(devices)
            online = len([d for d in devices if d['online']])

            return {
                "devices": devices,
                "total": total,
                "online": online,
                "offline": total - online
            }
    except Exception as e:
        print(f"获取设备失败: {e}")
        return {"devices": [], "total": 0, "online": 0, "offline": 0}


def get_recent_activities(user_id, limit=10):
    """获取最近活动（修复字段映射）"""
    init_farm_management_tables()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, type, type_label, content, plot_name, created_at 
                FROM farm_activities 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            activities = [dict(row) for row in cursor.fetchall()]

            # 格式化时间
            for act in activities:
                if act.get('created_at'):
                    try:
                        dt = datetime.fromisoformat(act['created_at'])
                        act['time_text'] = dt.strftime('%m-%d %H:%M')
                    except:
                        act['time_text'] = '刚刚'

            return activities
    except Exception as e:
        print(f"获取活动失败: {e}")
        return []


def get_user_crops(user_id):
    """获取用户作物列表（基于地块）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 从地块表中获取作物信息，并模拟进度和健康度
            cursor.execute('''
                SELECT id, name, crop as variety, area, status, 
                       plantDate as plant_date, created_at
                FROM farm_plots 
                WHERE user_id = ? AND crop IS NOT NULL
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            crops = []
            for idx, row in enumerate(rows):
                crop = dict(row)
                # 计算生长进度（基于种植日期）
                if crop.get('plant_date'):
                    try:
                        plant_date = datetime.fromisoformat(crop['plant_date'])
                        days_grown = (datetime.now() - plant_date).days
                        # 模拟90天生长周期
                        crop['progress'] = min(int((days_grown / 90) * 100), 100)
                    except:
                        crop['progress'] = 60  # 默认值
                else:
                    crop['progress'] = 60

                # 健康度（基于状态）
                crop['health'] = 95 if crop['status'] == 'growing' else 70
                crop['stage'] = '生长期' if crop['progress'] < 80 else '成熟期'

                # 新增：计算预计收成日期（种植后90天）
                if crop.get('plant_date'):
                    try:
                        plant_date = datetime.fromisoformat(crop['plant_date'])
                        harvest_date = plant_date + timedelta(days=90)
                        crop['harvestDate'] = harvest_date.strftime('%Y-%m-%d')
                    except:
                        crop['harvestDate'] = '预计90天后'
                else:
                    crop['harvestDate'] = '待定'

                # 新增：生成种植提示
                if crop['health'] >= 90:
                    crop['tip'] = f'健康度{crop["health"]}%，{crop["stage"]}，管理良好请继续保持'
                elif crop['health'] >= 70:
                    crop['tip'] = f'健康度{crop["health"]}%，需关注水肥条件，适时灌溉'
                else:
                    crop['tip'] = f'健康度较低（{crop["health"]}%），建议检查病虫害并及时防治'

                crops.append(crop)


            return crops
    except Exception as e:
        print(f"获取作物失败: {e}")
        return []


def init_farm_plot_for_user(user_id, name="默认地块", area=10.0, crop="玉米"):
    """为用户初始化示例地块（如果没有地块的话）"""
    init_farm_management_tables()
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查是否已有地块
        cursor.execute("SELECT COUNT(*) FROM farm_plots WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO farm_plots (user_id, name, area, crop, plantDate, status, location)
                VALUES (?, ?, ?, ?, date('now'), 'growing', '农场A区')
            ''', (user_id, name, area, crop))
            conn.commit()
    except Exception as e:
        print(f"初始化地块失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def init_farm_tasks_db():
    """初始化农事任务表（支持拖拽排序）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS farm_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            plot_name TEXT,
            plot_id INTEGER,
            scheduled_time TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            notes TEXT,
            reminder_sent INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,          -- 新增：排序权重
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user ON farm_tasks(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_date ON farm_tasks(scheduled_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_completed ON farm_tasks(completed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_sort ON farm_tasks(sort_order)')

    # 【迁移】为旧表添加 sort_order 字段
    try:
        cursor.execute("SELECT sort_order FROM farm_tasks LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE farm_tasks ADD COLUMN sort_order INTEGER DEFAULT 0")
        print("已为 farm_tasks 表添加 sort_order 字段")

    conn.commit()
    conn.close()


def add_farm_task(user_id, task_data):
    """添加农事任务"""
    init_farm_tasks_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO farm_tasks 
                (user_id, title, type, plot_name, plot_id, scheduled_time, priority, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                task_data.get('title'),
                task_data.get('type', 'other'),
                task_data.get('plot_name'),
                task_data.get('plot_id'),
                task_data.get('scheduled_time', datetime.now().isoformat()),
                task_data.get('priority', 'medium'),
                task_data.get('notes')
            ))
            conn.commit()
            return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_farm_tasks(user_id, date=None, completed=None, limit=50):
    """获取农事任务列表（修复：按 sort_order 排序）"""
    init_farm_tasks_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM farm_tasks WHERE user_id = ?'
            params = [user_id]

            if date:
                sql += ' AND DATE(scheduled_time) = DATE(?)'
                params.append(date)
            if completed is not None:
                sql += ' AND completed = ?'
                params.append(1 if completed else 0)

            # 关键修复：按 sort_order 升序，其次按时间排序
            sql += ' ORDER BY completed ASC, sort_order ASC, scheduled_time ASC LIMIT ?'
            params.append(limit)

            cursor.execute(sql, params)
            tasks = [dict(row) for row in cursor.fetchall()]

            # 转换布尔值和优先级文本
            for task in tasks:
                task['completed'] = bool(task['completed'])
                task['priorityText'] = {
                    'high': '紧急',
                    'medium': '普通',
                    'low': '提醒'
                }.get(task['priority'], '普通')

            return tasks
    except Exception as e:
        print(f"获取任务失败: {e}")
        return []


def update_farm_task(task_id, user_id, update_data):
    """更新任务（编辑、完成/取消、修改时间等）"""
    init_farm_tasks_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            allowed_fields = ['title', 'type', 'plot_name', 'scheduled_time',
                              'priority', 'completed', 'notes']
            sets = []
            params = []

            for field in allowed_fields:
                if field in update_data:
                    sets.append(f"{field} = ?")
                    params.append(update_data[field])

            if not sets:
                return {"success": False, "error": "无有效更新字段"}

            # 如果标记完成，记录完成时间
            if 'completed' in update_data and update_data['completed']:
                sets.append("completed_at = datetime('now')")

            sets.append("updated_at = datetime('now')")
            params.extend([task_id, user_id])

            cursor.execute(f'''
                UPDATE farm_tasks 
                SET {', '.join(sets)}
                WHERE id = ? AND user_id = ?
            ''', params)
            conn.commit()
            return {"success": True, "affected": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_farm_task(task_id, user_id):
    """删除任务"""
    init_farm_tasks_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM farm_tasks WHERE id = ? AND user_id = ?',
                           (task_id, user_id))
            conn.commit()
            return {"success": True, "deleted": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_task_stats(user_id, period='today'):
    """获取任务统计"""
    init_farm_tasks_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if period == 'today':
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as high_priority,
                        SUM(CASE WHEN completed = 0 AND scheduled_time < datetime('now') THEN 1 ELSE 0 END) as overdue
                    FROM farm_tasks 
                    WHERE user_id = ? AND DATE(scheduled_time) = DATE('now')
                ''', (user_id,))

            row = cursor.fetchone()
            return {
                "total": row['total'] or 0,
                "completed": row['completed'] or 0,
                "pending": (row['total'] or 0) - (row['completed'] or 0),
                "high_priority": row['high_priority'] or 0,
                "overdue": row['overdue'] or 0,
                "completion_rate": round((row['completed'] or 0) / max(row['total'], 1) * 100, 1)
            }
    except Exception as e:
        return {"total": 0, "completed": 0, "pending": 0}


# ==================== 知识库数据库管理 ====================

def get_knowledge_db_connection():
    """获取知识库数据库连接"""
    conn = sqlite3.connect(KNOWLEDGE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_knowledge_database():
    """初始化知识库数据库（优化版：支持个人知识库）"""
    with get_knowledge_db_connection() as conn:
        cursor = conn.cursor()

        # 1. 病虫害知识库主表（增加个人知识库字段）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pest_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pest_name TEXT NOT NULL,
                english_name TEXT,
                crop_type TEXT NOT NULL,
                category TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                damage_features TEXT,
                morphological_features TEXT,
                occurrence_season TEXT,
                favorable_conditions TEXT,
                distribution_areas TEXT,
                prevention_methods TEXT,
                chemical_control TEXT,
                biological_control TEXT,
                agricultural_control TEXT,
                similar_pests TEXT,
                image_urls TEXT,
                video_url TEXT,
                severity_level TEXT DEFAULT 'medium',
                urgency_level TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'active',
                is_personal INTEGER DEFAULT 0,          -- 新增：0=系统知识，1=个人知识
                owner_email TEXT,                      -- 新增：个人知识所属用户
                is_shared INTEGER DEFAULT 0,           -- 新增：个人知识是否分享给其他农户
                view_count INTEGER DEFAULT 0,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pest_name, crop_type, owner_email)  -- 修改：同一用户的个人知识可重名
            )
        ''')

        # 2. AI防治方案库（保持不变）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_prevention_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pest_id INTEGER NOT NULL,
                pest_name TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                thinking_process TEXT,
                prevention_summary TEXT,
                quality_score INTEGER,
                is_recommended INTEGER DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                created_by TEXT,
                source_detection_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pest_id) REFERENCES pest_knowledge(id) ON DELETE CASCADE
            )
        ''')

        # 3. 用户收藏表（保持不变）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_knowledge_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                pest_id INTEGER NOT NULL,
                collection_type TEXT DEFAULT 'pest',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pest_id) REFERENCES pest_knowledge(id) ON DELETE CASCADE,
                UNIQUE(user_email, pest_id)
            )
        ''')

        # 创建索引（优化查询性能）
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_crop ON pest_knowledge(crop_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_category ON pest_knowledge(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_name ON pest_knowledge(pest_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_personal ON pest_knowledge(is_personal)')  # 新增索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_owner ON pest_knowledge(owner_email)')    # 新增索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_status ON pest_knowledge(status)')

        conn.commit()
        print(f"知识库数据库初始化完成：{KNOWLEDGE_DB_PATH}（已支持个人知识库）")


def get_knowledge_list(filters=None, limit=50, offset=0, user_email=None, user_role=None):
    """
    获取知识列表（优化版：支持农户个人知识库）
    """
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            # 构建查询条件
            where_clauses = ["status = 'active'"]
            params = []

            # 调试输出（如仍有问题可开启）
            # print(f"[DEBUG] user_email: {user_email}, user_role: {user_role}, filters: {filters}")

            # 权限控制：根据查询类型设置不同条件
            if user_role != 'admin':
                if filters and filters.get('is_personal'):
                    # 关键修复：明确查询个人知识时，只查自己的，不查系统知识
                    where_clauses.append('is_personal = 1')
                    where_clauses.append('owner_email = ?')
                    params.append(user_email or '')
                else:
                    # 查询系统知识库或全部：显示系统知识+自己的知识+他人分享的
                    where_clauses.append("""
                        (is_personal = 0 OR owner_email = ? OR (is_personal = 1 AND is_shared = 1))
                    """)
                    params.append(user_email or '')

            # 应用其他筛选条件（作物类型、分类等）
            if filters:
                if filters.get('crop_type'):
                    where_clauses.append('crop_type = ?')
                    params.append(filters['crop_type'])
                if filters.get('category'):
                    where_clauses.append('category = ?')
                    params.append(filters['category'])
                if filters.get('severity_level'):
                    where_clauses.append('severity_level = ?')
                    params.append(filters['severity_level'])
                if filters.get('search_keyword'):
                    where_clauses.append("(pest_name LIKE ? OR symptoms LIKE ? OR english_name LIKE ?)")
                    keyword = f"%{filters['search_keyword']}%"
                    params.extend([keyword, keyword, keyword])

            # 关键修复：确保参数顺序正确
            # SQL 结构：SELECT ... FROM ... LEFT JOIN ... ON ... AND ukc.user_email = ?
            # WHERE ... (params) ... ORDER BY ... LIMIT ? OFFSET ?

            # 收藏查询的参数放在最前面
            collection_email = user_email or ''

            # 构建最终 SQL
            sql = f'''
                SELECT pk.*, 
                       CASE WHEN ukc.id IS NOT NULL THEN 1 ELSE 0 END as is_collected,
                       (SELECT COUNT(*) FROM ai_prevention_knowledge WHERE pest_id = pk.id) as ai_solution_count
                FROM pest_knowledge pk
                LEFT JOIN user_knowledge_collections ukc ON pk.id = ukc.pest_id AND ukc.user_email = ?
                WHERE {' AND '.join(where_clauses)}
                ORDER BY is_personal ASC, created_at DESC LIMIT ? OFFSET ?
            '''

            # 参数顺序：1.收藏邮箱, 2-4.where条件参数, 5.limit, 6.offset
            final_params = [collection_email] + params + [limit, offset]

            # 调试输出（如仍有问题可开启）
            # print(f"[DEBUG] SQL: {sql}")
            # print(f"[DEBUG] Params: {final_params}")

            cursor.execute(sql, final_params)
            rows = cursor.fetchall()

            knowledge_list = []
            for row in rows:
                item = dict(row)
                item['is_collected'] = bool(item.get('is_collected', 0))
                item['has_ai_solution'] = item.get('ai_solution_count', 0) > 0
                item['is_personal'] = bool(item.get('is_personal', 0))
                item['is_shared'] = bool(item.get('is_shared', 0))

                # 解析JSON字段
                if item.get('image_urls'):
                    try:
                        item['image_urls'] = json.loads(item['image_urls'])
                    except:
                        item['image_urls'] = []
                else:
                    item['image_urls'] = []

                knowledge_list.append(item)

            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM pest_knowledge WHERE {' AND '.join(where_clauses)}"
            # 注意：count_sql 不需要收藏查询参数，只需要 where 参数
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            return {"data": knowledge_list, "total": total}
    except Exception as e:
        print(f"获取知识列表失败: {e}")
        import traceback
        traceback.print_exc()
        return {"data": [], "total": 0}


def get_knowledge_by_id(knowledge_id, user_email=None, user_role=None):
    """获取单个病虫害知识详情（增加权限检查）"""
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pk.*,
                       CASE WHEN ukc.id IS NOT NULL THEN 1 ELSE 0 END as is_collected
                FROM pest_knowledge pk
                LEFT JOIN user_knowledge_collections ukc ON pk.id = ukc.pest_id AND ukc.user_email = ?
                WHERE pk.id = ? 
            ''', (user_email or '', knowledge_id))

            row = cursor.fetchone()
            if not row:
                return None

            item = dict(row)
            item['is_collected'] = bool(item.get('is_collected', 0))
            item['is_personal'] = bool(item.get('is_personal', 0))

            # 权限检查：非管理员只能查看系统知识或自己的个人知识
            if user_role != 'admin':
                if item['is_personal'] and item.get('owner_email') != user_email and not item.get('is_shared'):
                    return None  # 无权查看他人的非分享个人知识

            # 解析JSON字段
            if item.get('image_urls'):
                try:
                    item['image_urls'] = json.loads(item['image_urls'])
                except:
                    item['image_urls'] = []
            else:
                item['image_urls'] = []

            if item.get('similar_pests'):
                try:
                    item['similar_pests'] = json.loads(item['similar_pests'])
                except:
                    item['similar_pests'] = []
            else:
                item['similar_pests'] = []

            # 更新浏览量
            cursor.execute('''
                UPDATE pest_knowledge 
                SET view_count = view_count + 1 
                WHERE id = ?
            ''', (knowledge_id,))
            conn.commit()

            return item
    except Exception as e:
        print(f"获取知识详情失败: {e}")
        return None


def create_knowledge(data, created_by, is_admin=False):
    """
    创建知识条目（优化版：支持个人知识库）
    修复：确保 owner_email 统一存储为小写，避免匹配问题
    """
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            # 判断是个人知识还是系统知识
            is_personal = 0 if is_admin else 1
            # 关键修复：确保 owner_email 为小写，去除空格
            owner_email = None if is_admin else (created_by.lower().strip() if created_by else None)

            # 检查重复（系统知识检查全局唯一，个人知识检查用户内唯一）
            if is_admin:
                cursor.execute("SELECT id FROM pest_knowledge WHERE pest_name = ? AND crop_type = ? AND is_personal = 0",
                             (data.get('pest_name'), data.get('crop_type')))
            else:
                cursor.execute("SELECT id FROM pest_knowledge WHERE pest_name = ? AND crop_type = ? AND is_personal = 1 AND LOWER(owner_email) = LOWER(?)",
                             (data.get('pest_name'), data.get('crop_type'), created_by))

            if cursor.fetchone():
                return {"success": False, "error": "该病虫害知识已存在"}

            cursor.execute('''
                INSERT INTO pest_knowledge (
                    pest_name, english_name, crop_type, category, symptoms,
                    damage_features, morphological_features, occurrence_season,
                    favorable_conditions, distribution_areas, prevention_methods,
                    chemical_control, biological_control, agricultural_control,
                    similar_pests, image_urls, severity_level, urgency_level,
                    status, is_personal, owner_email, is_shared, created_by,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (
                data.get('pest_name'), data.get('english_name'), data.get('crop_type'),
                data.get('category'), data.get('symptoms'), data.get('damage_features'),
                data.get('morphological_features'), data.get('occurrence_season'),
                data.get('favorable_conditions'), data.get('distribution_areas'),
                data.get('prevention_methods'), data.get('chemical_control'),
                data.get('biological_control'), data.get('agricultural_control'),
                json.dumps(data.get('similar_pests', []), ensure_ascii=False),
                json.dumps(data.get('image_urls', []), ensure_ascii=False),
                data.get('severity_level', 'medium'), data.get('urgency_level', 'normal'),
                'active', is_personal, owner_email,
                1 if data.get('is_shared') else 0, created_by
            ))

            conn.commit()
            return {"success": True, "id": cursor.lastrowid, "is_personal": is_personal}
    except Exception as e:
        print(f"创建知识条目失败: {e}")
        return {"success": False, "error": str(e)}


def update_knowledge(knowledge_id, data, user_email=None, is_admin=False):
    """
    更新知识条目（增加权限控制）

    权限规则：
    - 管理员可以修改所有知识
    - 农户只能修改自己的个人知识，不能修改系统知识
    """
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            # 先查询现有记录检查权限
            cursor.execute('SELECT is_personal, owner_email FROM pest_knowledge WHERE id = ?', (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "error": "知识条目不存在"}

            record = dict(row)

            # 权限检查
            if not is_admin:
                if record['is_personal'] == 0:
                    return {"success": False, "error": "无权修改系统知识"}
                if record['owner_email'] != user_email:
                    return {"success": False, "error": "只能修改自己的个人知识"}

            # 构建更新字段
            allowed_fields = [
                'pest_name', 'english_name', 'crop_type', 'category', 'symptoms',
                'damage_features', 'morphological_features', 'occurrence_season',
                'favorable_conditions', 'distribution_areas', 'prevention_methods',
                'chemical_control', 'biological_control', 'agricultural_control',
                'similar_pests', 'image_urls', 'severity_level', 'urgency_level',
                'status', 'is_shared'
            ]

            sets = []
            params = []

            for field in allowed_fields:
                if field in data:
                    sets.append(f"{field} = ?")
                    if field in ['similar_pests', 'image_urls']:
                        params.append(json.dumps(data[field], ensure_ascii=False))
                    else:
                        params.append(data[field])

            if not sets:
                return {"success": False, "error": "无有效更新字段"}

            sets.append("updated_at = datetime('now')")
            params.append(knowledge_id)

            cursor.execute(f'''
                UPDATE pest_knowledge 
                SET {', '.join(sets)}
                WHERE id = ?
            ''', params)

            conn.commit()
            return {"success": True}
    except Exception as e:
        print(f"更新知识条目失败: {e}")
        return {"success": False, "error": str(e)}


def delete_knowledge(knowledge_id, user_email=None, is_admin=False):
    """
    删除知识条目（软删除，增加权限控制）

    权限规则：
    - 管理员可以删除所有知识
    - 农户只能删除自己的个人知识
    """
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            # 查询现有记录检查权限
            cursor.execute('SELECT is_personal, owner_email FROM pest_knowledge WHERE id = ?', (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "error": "知识条目不存在"}

            record = dict(row)

            # 权限检查
            if not is_admin:
                if record['is_personal'] == 0:
                    return {"success": False, "error": "无权删除系统知识"}
                if record['owner_email'] != user_email:
                    return {"success": False, "error": "只能删除自己的个人知识"}

            # 软删除
            cursor.execute('''
                UPDATE pest_knowledge 
                SET status = 'deleted', updated_at = datetime('now')
                WHERE id = ?
            ''', (knowledge_id,))
            conn.commit()
            return {"success": True}
    except Exception as e:
        print(f"删除知识条目失败: {e}")
        return {"success": False, "error": str(e)}


def get_knowledge_stats(user_email=None, user_role=None):
    """获取知识库统计数据（区分系统知识和个人知识）- 修复版"""
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # 系统知识统计（所有人可见）
            cursor.execute("SELECT COUNT(*) FROM pest_knowledge WHERE status = 'active' AND is_personal = 0")
            stats['total_system'] = cursor.fetchone()[0] or 0

            # 个人知识统计（仅自己）- 修复：确保 user_email 不为空
            if user_email:
                # 检查用户邮箱是否存在（去除首尾空格，确保大小写匹配）
                cursor.execute("SELECT COUNT(*) FROM pest_knowledge WHERE status = 'active' AND is_personal = 1 AND LOWER(owner_email) = LOWER(?)",
                             (user_email.strip(),))
                stats['total_personal'] = cursor.fetchone()[0] or 0
            else:
                stats['total_personal'] = 0

            # AI方案统计
            cursor.execute("SELECT COUNT(*) FROM ai_prevention_knowledge")
            stats['ai_solutions'] = cursor.fetchone()[0] or 0

            # 高风险统计（仅系统知识，避免个人知识影响全局统计）
            cursor.execute("SELECT COUNT(*) FROM pest_knowledge WHERE severity_level = 'high' AND status = 'active' AND is_personal = 0")
            stats['high_risk'] = cursor.fetchone()[0] or 0

            # 今日浏览（修复：统计所有今日更新的知识，不只是系统知识）
            cursor.execute("SELECT COALESCE(SUM(view_count), 0) FROM pest_knowledge WHERE DATE(updated_at) = DATE('now')")
            stats['today_views'] = cursor.fetchone()[0] or 0

            # 总统计（根据角色）
            if user_role == 'admin':
                stats['total'] = stats['total_system'] + stats['total_personal']
            else:
                # 农户看到系统知识+自己的个人知识
                if user_email:
                    cursor.execute('''
                        SELECT COUNT(*) FROM pest_knowledge 
                        WHERE status = 'active' 
                        AND (is_personal = 0 OR (is_personal = 1 AND LOWER(owner_email) = LOWER(?)))
                    ''', (user_email.strip(),))
                    stats['total'] = cursor.fetchone()[0] or 0
                else:
                    # 未登录或获取不到邮箱时，只显示系统知识
                    stats['total'] = stats['total_system']

            # 调试日志（开发环境可见）
            print(f"[Stats Debug] user_email: {user_email}, system: {stats['total_system']}, personal: {stats['total_personal']}")

            return stats
    except Exception as e:
        print(f"获取统计数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {"total": 0, "total_system": 0, "total_personal": 0,
                "ai_solutions": 0, "high_risk": 0, "today_views": 0}

def get_ai_solutions(pest_id):
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ai_prevention_knowledge 
                WHERE pest_id = ?
                ORDER BY is_recommended DESC, quality_score DESC, created_at DESC
            ''', (pest_id,))

            solutions = []
            for row in cursor.fetchall():
                solution = dict(row)
                solution['is_recommended'] = bool(solution.get('is_recommended', 0))
                solutions.append(solution)
            return solutions
    except Exception as e:
        print(f"获取AI方案失败: {e}")
        return []

def toggle_knowledge_collection(user_email, pest_id):
    init_knowledge_database()
    try:
        # 验证用户是否存在（应用层检查，替代外键约束）
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM users WHERE email = ?', (user_email,))
            if not cursor.fetchone():
                return {"success": False, "error": "用户不存在"}

        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id FROM user_knowledge_collections 
                WHERE user_email = ? AND pest_id = ?
            ''', (user_email, pest_id))

            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                    DELETE FROM user_knowledge_collections 
                    WHERE user_email = ? AND pest_id = ?
                ''', (user_email, pest_id))
                conn.commit()
                return {"success": True, "collected": False}
            else:
                cursor.execute('''
                    INSERT INTO user_knowledge_collections (user_email, pest_id)
                    VALUES (?, ?)
                ''', (user_email, pest_id))
                conn.commit()
                return {"success": True, "collected": True}
    except Exception as e:
        print(f"收藏操作失败: {e}")
        return {"success": False, "error": str(e)}

def get_user_collections(user_email):
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pk.*, ukc.created_at as collected_at
                FROM user_knowledge_collections ukc
                JOIN pest_knowledge pk ON ukc.pest_id = pk.id
                WHERE ukc.user_email = ? AND pk.status = 'active'
                ORDER BY ukc.created_at DESC
            ''', (user_email,))

            collections = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get('image_urls'):
                    try:
                        item['image_urls'] = json.loads(item['image_urls'])
                    except:
                        item['image_urls'] = []
                else:
                    item['image_urls'] = []
                collections.append(item)
            return collections
    except Exception as e:
        print(f"获取收藏列表失败: {e}")
        return []


# ==================== 补充缺失的评论功能函数 ====================

def save_comment(user_email, content, images=None, location=None, tags=None):
    """保存新评论"""
    init_users_table()
    init_comments_database()

    try:
        # 获取用户ID
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name FROM users WHERE email = ?', (user_email,))
            user = cursor.fetchone()
            if not user:
                return {"success": False, "error": "用户不存在"}

            user_id = user['id']
            author_name = user['name'] or user_email.split('@')[0]

        with get_comments_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO comments 
                (user_id, user_email, author_name, content, images, location, tags, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, user_email, author_name, content,
                json.dumps(images) if images else None,
                location, tags, 'pending', now, now
            ))

            comment_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "id": comment_id,
                "data": {
                    "id": comment_id,
                    "user_id": user_id,
                    "user_email": user_email,
                    "author_name": author_name,
                    "content": content,
                    "images": images or [],
                    "location": location,
                    "tags": tags,
                    "status": "pending",
                    "created_at": now,
                    "likes": 0,
                    "views": 0,
                    "replies": []
                }
            }
    except Exception as e:
        print(f"保存评论失败: {e}")
        return {"success": False, "error": str(e)}


def get_comments(status=None, user_email=None, limit=20, offset=0, is_pinned=None):
    """获取评论列表（支持筛选和分页）"""
    init_comments_database()

    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()

            where_clauses = ["1=1"]
            where_clauses.append("c.status != 'deleted'")
            params = []

            if status:
                where_clauses.append("c.status = ?")
                params.append(status)

            if user_email:
                where_clauses.append("c.user_email = ?")
                params.append(user_email)

            if is_pinned is not None:
                where_clauses.append("c.is_pinned = ?")
                params.append(1 if is_pinned else 0)

            # 查询评论
            sql = f'''
                SELECT c.*, 
                       CASE WHEN cl.comment_id IS NOT NULL THEN 1 ELSE 0 END as is_liked
                FROM comments c
                LEFT JOIN comment_likes cl ON c.id = cl.comment_id AND cl.user_email = ?
                WHERE {' AND '.join(where_clauses)}
                ORDER BY c.is_pinned DESC, c.created_at DESC
                LIMIT ? OFFSET ?
            '''
            params = [user_email or ''] + params + [limit, offset]

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # ==================== 新增：批量获取用户角色 ====================
            user_ids = list(set([row['user_id'] for row in rows if row['user_id']]))
            user_roles = get_users_roles(user_ids)
            # ==============================================================

            comments = []
            for row in rows:
                comment = dict(row)

                # ==================== 新增：填充角色字段 ====================
                role = user_roles.get(comment['user_id'], 'farmer')
                # 管理员在评论中也显示为专家身份，或你可以单独加个 'admin' 标签
                comment['role'] = 'expert' if role == 'admin' else role
                # ==========================================================

                # 解析JSON字段
                if comment.get('images'):
                    try:
                        comment['images'] = json.loads(comment['images'])
                    except:
                        comment['images'] = []
                else:
                    comment['images'] = []

                # 获取回复（包含嵌套）
                comment['replies'] = get_comment_replies(comment['id'], cursor, user_email)
                comment['is_liked'] = bool(comment.get('is_liked', 0))
                comments.append(comment)

            return comments
    except Exception as e:
        print(f"获取评论失败: {e}")
        return []


def update_comment_status(comment_id, status=None, is_pinned=None):
    """更新评论状态（审核、置顶）"""
    init_comments_database()

    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()

            sets = []
            params = []

            if status:
                sets.append("status = ?")
                params.append(status)

            if is_pinned is not None:
                sets.append("is_pinned = ?")
                params.append(1 if is_pinned else 0)

            if not sets:
                return False

            params.append(comment_id)

            cursor.execute(f'''
                UPDATE comments 
                SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', params)

            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"更新评论状态失败: {e}")
        return False


def get_comment_by_id(comment_id):
    """根据ID获取评论详情"""
    init_comments_database()
    try:
        with get_comments_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"获取评论详情失败: {e}")
        return None

def init_knowledge_sample_data():
    init_knowledge_database()
    try:
        with get_knowledge_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM pest_knowledge WHERE status = 'active'")
            if cursor.fetchone()[0] > 0:
                return

            sample_data = [
                {
                    "pest_name": "稻瘟病", "english_name": "Rice Blast", "crop_type": "水稻",
                    "category": "病害", "severity_level": "high", "urgency_level": "urgent",
                    "symptoms": "叶片出现梭形或纺锤形病斑，边缘褐色，中央灰白色，两端有褐色坏死线。严重时全株枯死。",
                    "damage_features": "主要危害叶片、茎秆和穗部，导致减产20-50%，严重时可绝收。",
                    "occurrence_season": "苗期至穗期均可发生，分蘖盛期和抽穗期最易感病。",
                    "favorable_conditions": "温度25-28℃，相对湿度90%以上，阴雨连绵天气易大流行。",
                    "chemical_control": "选用三环唑、稻瘟灵、春雷霉素等药剂，在发病初期喷雾防治。",
                    "biological_control": "使用枯草芽孢杆菌、井冈霉素等生物农药防治。",
                    "agricultural_control": "选用抗病品种，合理施肥，避免过量氮肥，浅水灌溉。"
                },
                {
                    "pest_name": "二化螟", "english_name": "Striped Rice Stem Borer", "crop_type": "水稻",
                    "category": "虫害", "severity_level": "high", "urgency_level": "urgent",
                    "symptoms": "幼虫蛀食茎秆，造成枯心苗、白穗和虫伤株。",
                    "damage_features": "一代幼虫造成枯心苗，二代幼虫造成白穗，严重影响产量。",
                    "occurrence_season": "一年发生1-5代，以第一代和第二代危害最重。",
                    "favorable_conditions": "高温高湿有利于发生，分蘖期和孕穗期最易受害。",
                    "chemical_control": "使用氯虫苯甲酰胺、阿维菌素、杀虫双等药剂，在卵孵化高峰期施药。",
                    "biological_control": "释放赤眼蜂防治，保护利用蜘蛛、青蛙等天敌。",
                    "agricultural_control": "齐泥割稻、低茬收割，减少越冬虫源；灌水杀蛹。"
                },
                {
                    "pest_name": "稻飞虱", "english_name": "Rice Planthopper", "crop_type": "水稻",
                    "category": "虫害", "severity_level": "high", "urgency_level": "urgent",
                    "symptoms": "成虫和若虫群集于稻丛下部刺吸汁液，严重时稻株枯萎倒伏，称为'冒穿'。",
                    "damage_features": "直接吸食汁液造成黄熟，传播病毒病，排泄蜜露诱发煤污病。",
                    "occurrence_season": "5-10月均可发生，以8-9月晚稻抽穗期危害最重。",
                    "favorable_conditions": "夏季高温干旱、台风暴雨天气有利于迁入和繁殖。",
                    "chemical_control": "选用吡蚜酮、烯啶虫胺、呋虫胺等高效低毒药剂，注意轮换使用。",
                    "biological_control": "保护蜘蛛、黑肩绿盲蝽等天敌，使用真菌类生物农药。",
                    "agricultural_control": "合理密植，科学管水，避免偏施氮肥，及时晒田。"
                },
                {
                    "pest_name": "纹枯病", "english_name": "Sheath Blight", "crop_type": "水稻",
                    "category": "病害", "severity_level": "medium", "urgency_level": "normal",
                    "symptoms": "叶鞘出现椭圆形暗绿色水渍状病斑，后扩大成云纹状，叶鞘受害严重。",
                    "damage_features": "主要危害叶鞘和叶片，影响养分输送，导致秕谷增多。",
                    "occurrence_season": "从分蘖期开始发生，孕穗至抽穗期达高峰。",
                    "favorable_conditions": "高温高湿（25-32℃，湿度90%以上）、长期深水灌溉易发病。",
                    "chemical_control": "使用井冈霉素、噻呋酰胺、苯甲·丙环唑等药剂，重点喷基部。",
                    "biological_control": "施用井冈霉素、多抗霉素等抗生素类杀菌剂。",
                    "agricultural_control": "合理密植，科学施肥，浅水灌溉，适时晒田。"
                },
                {
                    "pest_name": "小麦锈病", "english_name": "Wheat Rust", "crop_type": "小麦",
                    "category": "病害", "severity_level": "high", "urgency_level": "urgent",
                    "symptoms": "分条锈病、叶锈病和秆锈病三种，叶面出现鲜黄色至红褐色粉状孢子堆。",
                    "damage_features": "破坏叶绿素，影响光合作用，严重时植株枯死，减产30-50%。",
                    "occurrence_season": "春季3-5月和秋季9-11月为发病高峰期。",
                    "favorable_conditions": "温度15-22℃，高湿、结露、雾大天气有利于发病。",
                    "chemical_control": "使用三唑酮、戊唑醇、丙环唑等药剂，在发病初期防治。",
                    "biological_control": "使用中井909等生防菌剂。",
                    "agricultural_control": "选用抗病品种，合理轮作，适期播种，清除自生麦苗。"
                },
                {
                    "pest_name": "玉米螟", "english_name": "Corn Borer", "crop_type": "玉米",
                    "category": "虫害", "severity_level": "medium", "urgency_level": "normal",
                    "symptoms": "幼虫蛀食茎秆、穗轴和籽粒，造成茎折、穗腐和减产。",
                    "damage_features": "一般减产10-30%，严重时达50%以上，还传播玉米病害。",
                    "occurrence_season": "一年发生1-6代，春玉米心叶期和夏玉米穗期危害最重。",
                    "favorable_conditions": "温度22-28℃，相对湿度70%以上有利于发生。",
                    "chemical_control": "使用氯虫苯甲酰胺、阿维菌素、辛硫磷等药剂，在心叶末期施药。",
                    "biological_control": "释放赤眼蜂、使用白僵菌或苏云金杆菌制剂。",
                    "agricultural_control": "处理秸秆消灭越冬虫源，种植诱集作物，黑光灯诱杀成虫。"
                }
            ]

            for data in sample_data:
                cursor.execute('''
                    INSERT INTO pest_knowledge (
                        pest_name, english_name, crop_type, category, symptoms,
                        damage_features, occurrence_season, favorable_conditions,
                        chemical_control, biological_control, agricultural_control,
                        severity_level, urgency_level, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', datetime('now'), datetime('now'))
                ''', (
                    data['pest_name'], data['english_name'], data['crop_type'],
                    data['category'], data['symptoms'], data['damage_features'],
                    data['occurrence_season'], data['favorable_conditions'],
                    data['chemical_control'], data['biological_control'],
                    data['agricultural_control'], data['severity_level'],
                    data['urgency_level']
                ))

            conn.commit()
            print(f"已初始化 {len(sample_data)} 条示例知识数据")
    except Exception as e:
        print(f"初始化示例数据失败: {e}")


def update_farm_record(record_id, update_data, user_id):
    """更新农事记录（带用户权限验证）"""
    init_farm_records_db()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 先验证记录是否属于该用户
            cursor.execute('SELECT user_id FROM farm_records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": "记录不存在"}
            if row['user_id'] != user_id:
                return {"success": False, "error": "无权修改他人记录"}

            # 构建更新字段
            allowed_fields = ['type', 'field', 'date', 'operator', 'content', 'materials', 'status', 'remark']
            sets = []
            params = []

            for field in allowed_fields:
                if field in update_data:
                    sets.append(f"{field} = ?")
                    params.append(update_data[field])

            # 【修复点】以下 4 行必须与 for 循环同级缩进（在 with 块内）
            if not sets:
                return {"success": False, "error": "无有效更新字段"}

            params.append(record_id)
            cursor.execute(f'''
                UPDATE farm_records 
                SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', params + [user_id])

            conn.commit()
            return {"success": True, "affected": cursor.rowcount}
    except Exception as e:
        print(f"更新农事记录失败: {e}")
        return {"success": False, "error": str(e)}


# ==================== 成本管理 ====================
def init_cost_db():
    """初始化成本记录表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cost_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            item_name TEXT,
            amount REAL NOT NULL DEFAULT 0,
            record_date DATE NOT NULL,
            related_record_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cost_user ON cost_records(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cost_date ON cost_records(record_date)')
    conn.commit()
    conn.close()


def add_cost_record(user_id, category, amount, item_name=None, record_date=None, notes=None):
    """添加成本记录"""
    init_cost_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO cost_records (user_id, category, item_name, amount, record_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, category, item_name, amount,
              record_date or datetime.now().strftime('%Y-%m-%d'), notes))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_cost_stats_real(user_id, period='month'):
    """获取真实成本统计"""
    init_cost_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 根据 period 确定时间范围
    if period == 'month':
        date_filter = "strftime('%Y-%m', record_date) = strftime('%Y-%m', 'now')"
        prev_filter = "strftime('%Y-%m', record_date) = strftime('%Y-%m', 'now', '-1 month')"
    elif period == 'quarter':
        date_filter = "record_date >= date('now', '-3 months')"
        prev_filter = "record_date >= date('now', '-6 months') AND record_date < date('now', '-3 months')"
    else:  # year
        date_filter = "strftime('%Y', record_date) = strftime('%Y', 'now')"
        prev_filter = "strftime('%Y', record_date) = strftime('%Y', 'now', '-1 year')"

    # 本期统计
    cursor.execute(f'''
        SELECT category, SUM(amount) as total 
        FROM cost_records 
        WHERE user_id = ? AND {date_filter}
        GROUP BY category
    ''', (user_id,))
    rows = cursor.fetchall()

    # 上期统计（用于计算趋势）
    cursor.execute(f'''
        SELECT SUM(amount) as prev_total 
        FROM cost_records 
        WHERE user_id = ? AND {prev_filter}
    ''', (user_id,))
    prev_total = cursor.fetchone()['prev_total'] or 0

    conn.close()

    # 构建返回数据
    total = sum(r['total'] for r in rows) if rows else 0

    # 计算环比趋势
    trend = 0
    if prev_total > 0:
        trend = round((total - prev_total) / prev_total * 100, 1)

    # 默认分类映射
    colors = {
        '肥料': '#52c41a',
        '农药': '#fa8c16',
        '水电': '#1890ff',
        '人工': '#722ed1',
        '种子': '#eb2f96',
        '机械': '#13c2c2'
    }
    icons = {
        '肥料': 'fas fa-leaf',
        '农药': 'fas fa-spray-can',
        '水电': 'fas fa-bolt',
        '人工': 'fas fa-user',
        '种子': 'fas fa-seedling',
        '机械': 'fas fa-tractor'
    }

    breakdown = []
    for row in rows:
        cat = row['category']
        val = row['total']
        breakdown.append({
            "name": cat,
            "value": round(val, 2),
            "percent": round(val / total * 100, 1) if total else 0,
            "color": colors.get(cat, '#666'),
            "icon": icons.get(cat, 'fas fa-circle')
        })

    # 如果没有任何记录，返回空结构而非假数据
    if not breakdown:
        breakdown = [
            {"name": "暂无数据", "value": 0, "percent": 0, "color": "#d9d9d9", "icon": "fas fa-minus"}
        ]

    return {
        "total": round(total, 2),
        "trend": trend,
        "breakdown": breakdown
    }

def init_environment_db():
    """初始化环境数据表（用于存储传感器历史）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS environment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_id TEXT,
            temperature REAL,
            humidity REAL,
            soil_moisture REAL,
            light REAL,
            record_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_environment_data(user_id, device_id, temp, humidity, soil, light):
    """保存传感器数据"""
    init_environment_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO environment_records (user_id, device_id, temperature, humidity, soil_moisture, light)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, device_id, temp, humidity, soil, light))
    conn.commit()
    conn.close()

def get_latest_environment(user_id):
    """获取最新环境数据"""
    init_environment_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM environment_records 
        WHERE user_id = ? 
        ORDER BY record_time DESC LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== 设备管理 ====================

def get_all_devices():
    """获取所有设备列表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, lat, lng, status, last_update FROM devices ORDER BY id')
        return [dict(row) for row in cursor.fetchall()]


def add_device(name, lat, lng, status='online'):
    """添加设备"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO devices (name, lat, lng, status, last_update)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (name, lat, lng, status))
            conn.commit()
            return {"success": True, "id": cursor.lastrowid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_device(device_id, data):
    """更新设备信息"""
    allowed_fields = ['name', 'lat', 'lng', 'status']
    sets = []
    params = []
    for field in allowed_fields:
        if field in data:
            sets.append(f"{field} = ?")
            params.append(data[field])
    if not sets:
        return {"success": False, "error": "无有效更新字段"}

    sets.append("last_update = datetime('now')")
    params.append(device_id)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE devices SET {', '.join(sets)} WHERE id = ?
            ''', params)
            conn.commit()
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_device(device_id):
    """删除设备"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
            conn.commit()
            return {"success": True, "deleted": cursor.rowcount}
    except Exception as e:
        return {"success": False, "error": str(e)}


def init_sample_devices():
    """初始化示例设备数据（仅在空表时插入，方便首次体验）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM devices')
        if cursor.fetchone()[0] == 0:
            sample_devices = [
                ("田间摄像头-01", 23.3242, 113.8291, "online"),
                ("土壤传感器-A", 23.3250, 113.8300, "online"),
                ("气象监测站", 23.3230, 113.8280, "warning"),
                ("无人机基站", 23.3260, 113.8310, "offline")
            ]
            cursor.executemany('''
                INSERT INTO devices (name, lat, lng, status, last_update)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', sample_devices)
            conn.commit()
            print("已初始化 4 个示例设备")


def update_farm_tasks_order(user_id, ordered_ids):
    """
    批量更新任务排序顺序（拖拽排序后调用）

    Args:
        user_id: 当前用户ID（权限验证）
        ordered_ids: 按新顺序排列的任务ID列表 [3, 1, 2]
    """
    init_farm_tasks_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('BEGIN')

        # 验证所有ID是否属于当前用户（防止横向越权）
        if ordered_ids:
            placeholders = ','.join('?' * len(ordered_ids))
            cursor.execute(f'''
                SELECT id FROM farm_tasks 
                WHERE id IN ({placeholders}) AND user_id = ?
            ''', (*ordered_ids, user_id))
            owned_ids = {row['id'] for row in cursor.fetchall()}

            # 过滤掉不属于用户的ID
            valid_ids = [id for id in ordered_ids if id in owned_ids]

            if not valid_ids:
                conn.rollback()
                return {"success": False, "error": "无权操作这些任务"}

            # 使用事务批量更新 sort_order（索引0=最前）
            for index, task_id in enumerate(valid_ids):
                cursor.execute('''
                    UPDATE farm_tasks 
                    SET sort_order = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (index, task_id, user_id))

        conn.commit()
        return {
            "success": True,
            "message": f"已更新 {len(valid_ids)} 个任务的排序",
            "updated": len(valid_ids)
        }

    except Exception as e:
        conn.rollback()
        print(f"保存任务排序失败: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# 【新增】重置密码函数（必须放在 if __name__ 块之前）
def reset_user_password(email, new_password):
    """重置密码（保留原用户名，仅更新密码）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            pwd_hash = hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ?, has_password = 1, updated_at = datetime('now') WHERE email = ?",
                (pwd_hash, email)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"重置密码失败: {e}")
        return False

def init_model_registry():
    """初始化模型版本库"""
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


if __name__ == "__main__":
    clean_expired_codes()
    # 测试检测数据库
    init_detection_database()
    init_chat_database()
    print("所有数据库已准备就绪")