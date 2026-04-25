"""
智能农务系统 - 完整示例数据初始化脚本（字段补全版）
运行方式: python init_demo_data.py
"""

import sqlite3
import random
import json
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path

# 数据库路径配置
DB_PATHS = {
    'email': 'data/email.db',
    'detection': 'data/detection_history.db',
    'chat': 'data/chat_history.db',
    'comments': 'data/comments.db',
    'knowledge': 'data/knowledge_base.db'
}

# ==================== 七个真实用户数据（补全安全字段） ====================
DEMO_USERS = [
    {
        'id': 1, 'phone': '13800138001', 'email': 'admin@farm.com',
        'name': '张管理员', 'role': 'admin', 'status': 'active',
        'avatar': None, 'max_plots': 0, 'is_online': 1, 'login_count': 128,
        'last_login_ip': '192.168.1.100', 'last_login_at': datetime.now().isoformat(),
        'created_at': (datetime.now() - timedelta(days=90)).isoformat(),
        'updated_at': datetime.now().isoformat(),
        'password_hash': 'admin123',
        'has_password': 1,
        'failed_login_attempts': 0,
        'locked_until': 0
    },
    {
        'id': 2, 'phone': '13812345678', 'email': 'farmer1@farm.com',
        'name': '李大叔', 'role': 'farmer', 'status': 'active',
        'avatar': None, 'max_plots': 5, 'is_online': 1, 'login_count': 356,
        'last_login_ip': '192.168.1.101', 'last_login_at': datetime.now().isoformat(),
        'created_at': (datetime.now() - timedelta(days=60)).isoformat(),
        'updated_at': datetime.now().isoformat(),
        'password_hash': 'farmer123',
        'has_password': 1,
        'failed_login_attempts': 0,
        'locked_until': 0
    },
    {
        'id': 3, 'phone': '13987654321', 'email': 'farmer2@farm.com',
        'name': '王婶', 'role': 'farmer', 'status': 'active',
        'avatar': None, 'max_plots': 5, 'is_online': 1, 'login_count': 289,
        'last_login_ip': '192.168.1.102', 'last_login_at': (datetime.now() - timedelta(hours=2)).isoformat(),
        'created_at': (datetime.now() - timedelta(days=45)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=2)).isoformat(),
        'password_hash': 'farmer123',
        'has_password': 1,
        'failed_login_attempts': 0,
        'locked_until': 0
    },
    {
        'id': 4, 'phone': '13700137001', 'email': 'farmer3@farm.com',
        'name': '赵技术员', 'role': 'farmer', 'status': 'pending',
        'avatar': None, 'max_plots': 5, 'is_online': 0, 'login_count': 0,
        'last_login_ip': None, 'last_login_at': None,
        'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
        'updated_at': None,
        'password_hash': None,
        'has_password': 0,
        'failed_login_attempts': 0,
        'locked_until': 0
    },
    {
        'id': 5, 'phone': '13600136001', 'email': 'farmer4@farm.com',
        'name': '陈大姐', 'role': 'farmer', 'status': 'active',
        'avatar': None, 'max_plots': 5, 'is_online': 0, 'login_count': 156,
        'last_login_ip': '192.168.1.103', 'last_login_at': (datetime.now() - timedelta(days=2)).isoformat(),
        'created_at': (datetime.now() - timedelta(days=30)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=2)).isoformat(),
        'password_hash': 'farmer123',
        'has_password': 1,
        'failed_login_attempts': 0,
        'locked_until': 0
    },
    {
        'id': 6, 'phone': '13500135001', 'email': 'farmer5@farm.com',
        'name': '刘师傅', 'role': 'farmer', 'status': 'active',
        'avatar': None, 'max_plots': 5, 'is_online': 1, 'login_count': 198,
        'last_login_ip': '192.168.1.104', 'last_login_at': (datetime.now() - timedelta(hours=5)).isoformat(),
        'created_at': (datetime.now() - timedelta(days=20)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=5)).isoformat(),
        'password_hash': 'farmer123',
        'has_password': 1,
        'failed_login_attempts': 0,
        'locked_until': 0
    },
    {
        'id': 7, 'phone': '13400134001', 'email': 'banned@farm.com',
        'name': '违规用户', 'role': 'farmer', 'status': 'banned',
        'avatar': None, 'max_plots': 0, 'is_online': 0, 'login_count': 12,
        'last_login_ip': '192.168.1.999', 'last_login_at': (datetime.now() - timedelta(days=15)).isoformat(),
        'created_at': (datetime.now() - timedelta(days=25)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=15)).isoformat(),
        'password_hash': 'banned123',
        'has_password': 1,
        'failed_login_attempts': 5,
        'locked_until': int((datetime.now() - timedelta(days=10)).timestamp())
    },
]

DEMO_PLOTS = [
    {'id': 1, 'name': '增城01区-水稻主田', 'location': '增城农场A区东侧', 'crop_type': '水稻',
     'area': 25.5, 'lat': 23.3242, 'lng': 113.8291, 'device_id': 'CAM_001', 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=90)).isoformat()},
    {'id': 2, 'name': '增城02区-玉米试验田', 'location': '增城农场A区西侧', 'crop_type': '玉米',
     'area': 18.3, 'lat': 23.3255, 'lng': 113.8280, 'device_id': 'CAM_002', 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=85)).isoformat()},
    {'id': 3, 'name': '增城03区-番茄大棚', 'location': '增城农场B区大棚区', 'crop_type': '番茄',
     'area': 8.5, 'lat': 23.3230, 'lng': 113.8305, 'device_id': 'CAM_003', 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=80)).isoformat()},
    {'id': 4, 'name': '天河A区-大豆基地', 'location': '增城农场C区科研用地', 'crop_type': '大豆',
     'area': 15.2, 'lat': 23.3260, 'lng': 113.8310, 'device_id': None, 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=75)).isoformat()},
    {'id': 5, 'name': '天河B区-荔枝园', 'location': '增城农场D区山坡地', 'crop_type': '荔枝',
     'area': 32.8, 'lat': 23.3215, 'lng': 113.8275, 'device_id': 'CAM_004', 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=70)).isoformat()},
    {'id': 6, 'name': 'E区-休耕地', 'location': '增城农场E区', 'crop_type': None,
     'area': 20.0, 'lat': 23.3270, 'lng': 113.8320, 'device_id': None, 'status': 'inactive',
     'created_at': (datetime.now() - timedelta(days=60)).isoformat()},
    {'id': 7, 'name': '增城04区-小麦田', 'location': '增城农场F区', 'crop_type': '小麦',
     'area': 22.0, 'lat': 23.3225, 'lng': 113.8285, 'device_id': 'CAM_005', 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=65)).isoformat()},
    {'id': 8, 'name': '增城05区-蔬菜大棚', 'location': '增城农场G区', 'crop_type': '黄瓜',
     'area': 6.5, 'lat': 23.3235, 'lng': 113.8295, 'device_id': 'CAM_006', 'status': 'active',
     'created_at': (datetime.now() - timedelta(days=50)).isoformat()},
]

USER_PLOT_BINDINGS = [
    {'user_id': 2, 'plot_id': 1, 'is_default': 1, 'bind_at': (datetime.now() - timedelta(days=60)).isoformat()},
    {'user_id': 2, 'plot_id': 2, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=55)).isoformat()},
    {'user_id': 2, 'plot_id': 5, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=40)).isoformat()},
    {'user_id': 3, 'plot_id': 3, 'is_default': 1, 'bind_at': (datetime.now() - timedelta(days=45)).isoformat()},
    {'user_id': 3, 'plot_id': 8, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=30)).isoformat()},
    {'user_id': 5, 'plot_id': 4, 'is_default': 1, 'bind_at': (datetime.now() - timedelta(days=30)).isoformat()},
    {'user_id': 5, 'plot_id': 7, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=20)).isoformat()},
    {'user_id': 6, 'plot_id': 1, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=20)).isoformat()},
    {'user_id': 6, 'plot_id': 2, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=19)).isoformat()},
    {'user_id': 6, 'plot_id': 3, 'is_default': 1, 'bind_at': (datetime.now() - timedelta(days=18)).isoformat()},
    {'user_id': 6, 'plot_id': 7, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=15)).isoformat()},
    {'user_id': 6, 'plot_id': 8, 'is_default': 0, 'bind_at': (datetime.now() - timedelta(days=10)).isoformat()},
]

DEMO_DEVICES = [
    {'id': 1, 'device_id': 'DEV-CAM001', 'name': '田间监测站-A1', 'type': 'camera', 'location': '增城01区-水稻主田北侧',
     'lat': 23.3242, 'lng': 113.8291, 'ip_address': '192.168.1.101', 'firmware_version': 'v2.1.0',
     'status': 'online', 'last_update': datetime.now().strftime('%H:%M')},
    {'id': 2, 'device_id': 'DEV-CAM002', 'name': '智能摄像头-B2', 'type': 'camera', 'location': '增城02区-玉米试验田西侧',
     'lat': 23.3255, 'lng': 113.8280, 'ip_address': '192.168.1.102', 'firmware_version': 'v2.0.8',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=5)).strftime('%H:%M')},
    {'id': 3, 'device_id': 'DEV-ENV001', 'name': '环境监测节点-C1', 'type': 'sensor', 'location': '增城03区-番茄大棚东侧',
     'lat': 23.3230, 'lng': 113.8305, 'ip_address': '192.168.1.103', 'firmware_version': 'v1.9.5',
     'status': 'warning', 'last_update': (datetime.now() - timedelta(hours=2)).strftime('%H:%M')},
    {'id': 4, 'device_id': 'DEV-DRN001', 'name': '无人机停机坪-D1', 'type': 'drone', 'location': '天河A区-大豆基地中心',
     'lat': 23.3260, 'lng': 113.8310, 'ip_address': '192.168.1.104', 'firmware_version': 'v3.0.1',
     'status': 'offline', 'last_update': '昨日 18:30'},
    {'id': 5, 'device_id': 'DEV-IRR001', 'name': '灌溉控制单元-E2', 'type': 'irrigation', 'location': '天河B区-荔枝园南侧',
     'lat': 23.3215, 'lng': 113.8275, 'ip_address': '192.168.1.105', 'firmware_version': 'v2.1.2',
     'status': 'online', 'last_update': datetime.now().strftime('%H:%M')},
    {'id': 6, 'device_id': 'DEV-SOL001', 'name': '土壤传感器-F3', 'type': 'sensor', 'location': '增城04区-小麦田中部',
     'lat': 23.3225, 'lng': 113.8285, 'ip_address': '192.168.1.106', 'firmware_version': 'v1.8.9',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=3)).strftime('%H:%M')},
    {'id': 7, 'device_id': 'DEV-MET001', 'name': '气象站-G1', 'type': 'weather', 'location': '增城05区-蔬菜大棚北侧',
     'lat': 23.3240, 'lng': 113.8290, 'ip_address': '192.168.1.107', 'firmware_version': 'v2.2.0',
     'status': 'online', 'last_update': datetime.now().strftime('%H:%M')},
    {'id': 8, 'device_id': 'DEV-CAM003', 'name': '摄像头-H2', 'type': 'camera', 'location': '增城03区-番茄大棚西侧',
     'lat': 23.3235, 'lng': 113.8295, 'ip_address': '192.168.1.108', 'firmware_version': 'v2.0.5',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=10)).strftime('%H:%M')},
    {'id': 9, 'device_id': 'DEV-SEN002', 'name': '传感器-I3', 'type': 'sensor', 'location': '增城01区-水稻主田南侧',
     'lat': 23.3245, 'lng': 113.8285, 'ip_address': '192.168.1.109', 'firmware_version': 'v1.9.2',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=2)).strftime('%H:%M')},
    {'id': 10, 'device_id': 'DEV-CTL001', 'name': '控制器-J1', 'type': 'controller', 'location': '增城02区-玉米试验田东侧',
     'lat': 23.3250, 'lng': 113.8290, 'ip_address': '192.168.1.110', 'firmware_version': 'v2.1.5',
     'status': 'warning', 'last_update': (datetime.now() - timedelta(hours=1)).strftime('%H:%M')},
    {'id': 11, 'device_id': 'DEV-MON002', 'name': '监测站-K2', 'type': 'camera', 'location': '天河B区-荔枝园东侧',
     'lat': 23.3220, 'lng': 113.8280, 'ip_address': '192.168.1.111', 'firmware_version': 'v2.0.3',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=8)).strftime('%H:%M')},
    {'id': 12, 'device_id': 'DEV-VLV001', 'name': '灌溉阀-L3', 'type': 'irrigation', 'location': '增城04区-小麦田北侧',
     'lat': 23.3230, 'lng': 113.8280, 'ip_address': '192.168.1.112', 'firmware_version': 'v1.9.8',
     'status': 'online', 'last_update': datetime.now().strftime('%H:%M')},
    {'id': 13, 'device_id': 'DEV-CAM004', 'name': '摄像头-M1', 'type': 'camera', 'location': '天河A区-大豆基地西侧',
     'lat': 23.3265, 'lng': 113.8300, 'ip_address': '192.168.1.113', 'firmware_version': 'v2.1.1',
     'status': 'offline', 'last_update': '昨日 20:15'},
    {'id': 14, 'device_id': 'DEV-SEN003', 'name': '传感器-N2', 'type': 'sensor', 'location': '增城05区-蔬菜大棚南侧',
     'lat': 23.3210, 'lng': 113.8270, 'ip_address': '192.168.1.114', 'firmware_version': 'v1.8.5',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=15)).strftime('%H:%M')},
    {'id': 15, 'device_id': 'DEV-MET002', 'name': '气象仪-O3', 'type': 'weather', 'location': '增城01区-水稻主田东侧',
     'lat': 23.3250, 'lng': 113.8300, 'ip_address': '192.168.1.115', 'firmware_version': 'v2.2.1',
     'status': 'online', 'last_update': (datetime.now() - timedelta(minutes=1)).strftime('%H:%M')},
    {'id': 16, 'device_id': 'DEV-CTL002', 'name': '控制站-P1', 'type': 'controller', 'location': '增城03区-番茄大棚中心',
     'lat': 23.3225, 'lng': 113.8290, 'ip_address': '192.168.1.116', 'firmware_version': 'v2.0.9',
     'status': 'warning', 'last_update': (datetime.now() - timedelta(minutes=30)).strftime('%H:%M')},
]

def generate_detection_history():
    records = []
    pests = ['草地贪夜蛾', '稻纵卷叶螟', '二化螟', '三化螟', '褐飞虱', '灰飞虱', '叶斑病', '锈病', '稻飞虱', '蚜虫']

    today_count = 342
    high_risk_indices = random.sample(range(today_count), 8)

    for i in range(today_count):
        date = datetime.now() - timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        pest = random.choice(pests)

        if i in high_risk_indices:
            conf = round(random.uniform(85, 98), 1)
            risk = 'high'
        else:
            conf = round(random.uniform(45, 75), 1)
            risk = 'medium' if conf >= 50 else 'low'

        device_id = f'CAM_{random.randint(1, 6):03d}'

        user_email = random.choice([
            None, 'farmer1@farm.com', 'farmer2@farm.com',
            'farmer4@farm.com', 'farmer5@farm.com'
        ])

        records.append({
            'id': i + 1,
            'pest_name': pest,
            'confidence': conf,
            'image_base64': None,
            'original_image_base64': None,
            'device_id': device_id,
            'location_lat': round(23.32 + random.uniform(-0.01, 0.01), 4),
            'location_lng': round(113.82 + random.uniform(-0.01, 0.01), 4),
            'risk_level': risk,
            'status': 'active',
            'notes': None,
            'crop_type': random.choice(['水稻', '玉米', '小麦', None]),
            'user_email': user_email,
            'created_at': date.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': date.strftime('%Y-%m-%d %H:%M:%S')
        })

    for day in range(1, 30):
        daily_count = random.randint(50, 150)
        for i in range(daily_count):
            date = datetime.now() - timedelta(
                days=day,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            pest = random.choice(pests)
            conf = round(random.uniform(45, 98), 1)
            risk = 'high' if conf >= 75 else ('medium' if conf >= 50 else 'low')
            device_id = f'CAM_{random.randint(1, 6):03d}'

            records.append({
                'id': len(records) + 1,
                'pest_name': pest,
                'confidence': conf,
                'image_base64': None,
                'original_image_base64': None,
                'device_id': device_id,
                'location_lat': round(23.32 + random.uniform(-0.01, 0.01), 4),
                'location_lng': round(113.82 + random.uniform(-0.01, 0.01), 4),
                'risk_level': risk,
                'status': 'active',
                'notes': None,
                'crop_type': random.choice(['水稻', '玉米', '小麦', None]),
                'created_at': date.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': date.strftime('%Y-%m-%d %H:%M:%S')
            })

    return sorted(records, key=lambda x: x['created_at'], reverse=True)

DEMO_DETECTIONS = generate_detection_history()

DEMO_COMMENTS = [
    {
        'id': 1, 'user_id': 2, 'user_email': 'farmer1@farm.com', 'author_name': '李大叔',
        'content': '最近发现田里有不少草地贪夜蛾的幼虫，用了系统推荐的生物农药，效果还不错！大家有什么其他防治经验吗？',
        'images': json.dumps([]),
        'location': '增城01区-水稻主田',
        'tags': '病害防治,经验分享',
        'status': 'approved',
        'is_pinned': 1,
        'pin_order': 1,
        'likes': 23,
        'views': 156,
        'created_at': (datetime.now() - timedelta(days=2)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=2)).isoformat()
    },
    {
        'id': 2, 'user_id': 3, 'user_email': 'farmer2@farm.com', 'author_name': '王婶',
        'content': '请问各位老师，大棚番茄叶子发黄是怎么回事？是不是缺肥了？附图是昨天拍的。',
        'images': json.dumps([]),
        'location': '增城03区-番茄大棚',
        'tags': '提问,番茄种植',
        'status': 'approved',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 8,
        'views': 89,
        'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=1)).isoformat()
    },
    {
        'id': 3, 'user_id': 2, 'user_email': 'farmer1@farm.com', 'author_name': '李大叔',
        'content': '@王婶 可能是缺氮，建议追施尿素，同时也要检查土壤湿度。另外看看根部有没有病虫害。',
        'images': json.dumps([]),
        'location': None,
        'tags': '回复',
        'status': 'approved',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 15,
        'views': 45,
        'created_at': (datetime.now() - timedelta(hours=20)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=20)).isoformat()
    },
    {
        'id': 4, 'user_id': 5, 'user_email': 'farmer4@farm.com', 'author_name': '陈大姐',
        'content': '分享一个好消息！天河A区的大豆今年长势特别好，预计亩产能比往年提高15%。关键是采用了新的轮作模式。',
        'images': json.dumps([]),
        'location': '天河A区-大豆基地',
        'tags': '经验分享,丰收',
        'status': 'approved',
        'is_pinned': 1,
        'pin_order': 2,
        'likes': 45,
        'views': 234,
        'created_at': (datetime.now() - timedelta(days=3)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=3)).isoformat()
    },
    {
        'id': 5, 'user_id': 6, 'user_email': 'farmer5@farm.com', 'author_name': '刘师傅',
        'content': '各位注意，CAM_003摄像头可能需要校准，昨天拍的照片有点模糊。我下午去现场看看。',
        'images': json.dumps([]),
        'location': '增城03区-番茄大棚',
        'tags': '设备维护,提醒',
        'status': 'approved',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 12,
        'views': 67,
        'created_at': (datetime.now() - timedelta(hours=18)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=18)).isoformat()
    },
    {
        'id': 6, 'user_id': 4, 'user_email': 'farmer3@farm.com', 'author_name': '赵技术员',
        'content': '新注册的账号，想学习一下如何操作智能监测设备，有大佬带带吗？可以线下交流。',
        'images': json.dumps([]),
        'location': '天河A区-大豆基地',
        'tags': '新手求助',
        'status': 'pending',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 0,
        'views': 12,
        'created_at': (datetime.now() - timedelta(hours=5)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=5)).isoformat()
    },
    {
        'id': 7, 'user_id': 7, 'user_email': 'banned@farm.com', 'author_name': '违规用户',
        'content': '这是一条违规广告内容，包含不良信息，应该被屏蔽',
        'images': json.dumps([]),
        'location': None,
        'tags': '广告',
        'status': 'rejected',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 0,
        'views': 2,
        'created_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=4)).isoformat()
    },
]

DEMO_FARM_RECORDS = [
    {
        'id': 1, 'user_id': 2, 'type': 'irrigation', 'field': '增城01区-水稻主田',
        'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
        'operator': '李大叔', 'content': '对01区进行滴灌浇水，持续2小时，土壤湿度已达标。',
        'materials': '水', 'remark': '灌溉后土壤湿度达到65%', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=2)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=2)).isoformat()
    },
    {
        'id': 2, 'user_id': 3, 'type': 'pest', 'field': '增城03区-番茄大棚',
        'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        'operator': '王婶', 'content': '发现叶斑病早期症状，已喷洒三唑酮防治。',
        'materials': '三唑酮 200ml', 'remark': '需3天后复查防治效果', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=1)).isoformat()
    },
    {
        'id': 3, 'user_id': 2, 'type': 'fertilize', 'field': '增城02区-玉米试验田',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'operator': '李大叔', 'content': '追施拔节肥，采用沟施方式，注意避免烧苗。',
        'materials': '尿素 50kg, 钾肥 20kg', 'remark': '施肥后需及时浇水', 'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    },
    {
        'id': 4, 'user_id': 5, 'type': 'weed', 'field': '天河A区-大豆基地',
        'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
        'operator': '陈大姐', 'content': '人工除草，清理田埂杂草，防止病虫害滋生。',
        'materials': '无', 'remark': '共清理杂草约15kg', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=3)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=3)).isoformat()
    },
    {
        'id': 5, 'user_id': 6, 'type': 'inspect', 'field': '天河B区-荔枝园',
        'date': (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d'),
        'operator': '刘师傅', 'content': '巡查荔枝园，检查病虫害情况，未发现异常。',
        'materials': '', 'remark': '荔枝树生长良好，预计下月开花', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(hours=6)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=6)).isoformat()
    },
    {
        'id': 6, 'user_id': 2, 'type': 'irrigation', 'field': '增城03区-番茄大棚',
        'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
        'operator': '李大叔', 'content': '大棚滴灌系统维护后首次使用，检查喷头通畅情况。',
        'materials': '水, 肥料混合液', 'remark': '土壤湿度从45%提升至72%', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=5)).isoformat()
    },
    {
        'id': 7, 'user_id': 2, 'type': 'fertilize', 'field': '增城01区-水稻主田',
        'date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        'operator': '李大叔', 'content': '水稻分蘖期追肥，每亩施用尿素12kg。',
        'materials': '尿素 12kg/亩', 'remark': '配合灌溉进行，提高肥料利用率', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=7)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=7)).isoformat()
    },
    {
        'id': 8, 'user_id': 3, 'type': 'pest', 'field': '增城05区-蔬菜大棚',
        'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'),
        'operator': '王婶', 'content': '防治黄瓜霜霉病，喷施烯酰吗啉和预防性药剂。',
        'materials': '烯酰吗啉 100ml, 代森锰锌 150g', 'remark': '注意轮换用药，避免抗性产生', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=4)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=4)).isoformat()
    },
    {
        'id': 9, 'user_id': 5, 'type': 'fertilize', 'field': '天河A区-大豆基地',
        'date': (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d'),
        'operator': '陈大姐', 'content': '大豆结荚期补充钾肥，促进籽粒饱满。',
        'materials': '硫酸钾 15kg/亩', 'remark': '叶面喷施配合根部追肥', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=6)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=6)).isoformat()
    },
    {
        'id': 10, 'user_id': 6, 'type': 'irrigation', 'field': '增城04区-小麦田',
        'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
        'operator': '刘师傅', 'content': '小麦灌浆期浇水，保证籽粒正常发育。',
        'materials': '水', 'remark': '避免大水漫灌，防止倒伏', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=3)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=3)).isoformat()
    },
    {
        'id': 11, 'user_id': 2, 'type': 'harvest', 'field': '增城02区-玉米试验田',
        'date': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
        'operator': '李大叔', 'content': '早熟玉米品种试采，评估产量和品质。',
        'materials': '收割机, 运输车', 'remark': '亩产达到预期650kg，品质优良', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=10)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=10)).isoformat()
    },
    {
        'id': 12, 'user_id': 3, 'type': 'sow', 'field': '增城03区-番茄大棚',
        'date': (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d'),
        'operator': '王婶', 'content': '春季番茄定植，采用穴盘育苗移栽方式。',
        'materials': '番茄苗 2000株, 有机肥 500kg', 'remark': '定植后及时浇定根水', 'status': 'completed',
        'created_at': (datetime.now() - timedelta(days=45)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=45)).isoformat()
    },
]

DEMO_FARM_PLOTS = [
    {
        'id': 1, 'user_id': 2, 'name': '试验田A-水稻', 'area': 25.5, 'crop': '水稻',
        'plantDate': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        'status': 'growing', 'location': '增城01区',
        'created_at': (datetime.now() - timedelta(days=90)).isoformat()
    },
    {
        'id': 2, 'user_id': 2, 'name': '大棚B-番茄', 'area': 8.5, 'crop': '番茄',
        'plantDate': (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
        'status': 'warning', 'location': '增城03区',
        'created_at': (datetime.now() - timedelta(days=60)).isoformat()
    },
    {
        'id': 3, 'user_id': 2, 'name': '玉米试验田', 'area': 18.3, 'crop': '玉米',
        'plantDate': (datetime.now() - timedelta(days=75)).strftime('%Y-%m-%d'),
        'status': 'growing', 'location': '增城02区',
        'created_at': (datetime.now() - timedelta(days=75)).isoformat()
    },
    {
        'id': 4, 'user_id': 5, 'name': '大豆科研基地', 'area': 15.2, 'crop': '大豆',
        'plantDate': (datetime.now() - timedelta(days=80)).strftime('%Y-%m-%d'),
        'status': 'growing', 'location': '天河A区',
        'created_at': (datetime.now() - timedelta(days=80)).isoformat()
    },
    {
        'id': 5, 'user_id': 5, 'name': '小麦田', 'area': 22.0, 'crop': '小麦',
        'plantDate': (datetime.now() - timedelta(days=70)).strftime('%Y-%m-%d'),
        'status': 'growing', 'location': '增城04区',
        'created_at': (datetime.now() - timedelta(days=70)).isoformat()
    },
    {
        'id': 6, 'user_id': 3, 'name': '蔬菜大棚', 'area': 6.5, 'crop': '黄瓜',
        'plantDate': (datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d'),
        'status': 'growing', 'location': '增城05区',
        'created_at': (datetime.now() - timedelta(days=40)).isoformat()
    },
]

DEMO_FARM_CROPS = [
    {
        'id': 1, 'plot_id': 1, 'name': '优质水稻', 'variety': 'Y两优1号',
        'area': 25.5, 'harvestDate': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'status': 'growing', 'tips': '拔节期，注意防治稻飞虱，保持土壤湿润',
        'stage': '拔节期', 'progress': 65, 'health': 92
    },
    {
        'id': 2, 'plot_id': 2, 'name': '樱桃番茄', 'variety': '圣女果红',
        'area': 8.5, 'harvestDate': (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d'),
        'status': 'warning', 'tips': '检测到叶斑病，已安排防治，注意通风降湿',
        'stage': '开花期', 'progress': 40, 'health': 75
    },
    {
        'id': 3, 'plot_id': 3, 'name': '甜玉米', 'variety': '黄金甜1号',
        'area': 18.3, 'harvestDate': (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
        'status': 'growing', 'tips': '抽穗期，即将进入采收期，减少氮肥使用',
        'stage': '抽穗期', 'progress': 80, 'health': 88
    },
    {
        'id': 4, 'plot_id': 4, 'name': '高蛋白大豆', 'variety': '中黄35',
        'area': 15.2, 'harvestDate': (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d'),
        'status': 'growing', 'tips': '结荚期，注意补充钾肥，防止倒伏',
        'stage': '结荚期', 'progress': 55, 'health': 95
    },
    {
        'id': 5, 'plot_id': 5, 'name': '冬小麦', 'variety': '济麦22',
        'area': 22.0, 'harvestDate': (datetime.now() + timedelta(days=25)).strftime('%Y-%m-%d'),
        'status': 'growing', 'tips': '灌浆期，注意防治锈病和蚜虫',
        'stage': '灌浆期', 'progress': 70, 'health': 90
    },
    {
        'id': 6, 'plot_id': 6, 'name': '黄瓜', 'variety': '津优35号',
        'area': 6.5, 'harvestDate': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
        'status': 'growing', 'tips': '盛果期，注意水肥管理，及时采收',
        'stage': '盛果期', 'progress': 85, 'health': 87
    },
]

DEMO_USER_DEVICES = [
    {'id': 1, 'user_id': 2, 'name': '智能摄像头-01', 'type': 'camera',
     'icon': 'fas fa-video', 'location': '增城01区', 'lat': 23.3242, 'lng': 113.8291, 'status': 'online',
     'last_online': datetime.now().isoformat()},
    {'id': 2, 'user_id': 2, 'name': '土壤传感器-02', 'type': 'sensor',
     'icon': 'fas fa-thermometer-half', 'location': '大棚B', 'lat': 23.3250, 'lng': 113.8300, 'status': 'online',
     'last_online': (datetime.now() - timedelta(minutes=30)).isoformat()},
    {'id': 3, 'user_id': 2, 'name': '气象站-03', 'type': 'sensor',
     'icon': 'fas fa-cloud-sun', 'location': '增城03区', 'lat': 23.3230, 'lng': 113.8305, 'status': 'online',
     'last_online': (datetime.now() - timedelta(hours=1)).isoformat()},
    {'id': 4, 'user_id': 3, 'name': '摄像头-04', 'type': 'camera',
     'icon': 'fas fa-video', 'location': '增城05区', 'lat': 23.3255, 'lng': 113.8280, 'status': 'online',
     'last_online': (datetime.now() - timedelta(minutes=15)).isoformat()},
    {'id': 5, 'user_id': 5, 'name': '监测站-05', 'type': 'sensor',
     'icon': 'fas fa-broadcast-tower', 'location': '天河A区', 'lat': 23.3260, 'lng': 113.8310, 'status': 'warning',
     'last_online': (datetime.now() - timedelta(hours=2)).isoformat()},
    {'id': 6, 'user_id': 6, 'name': '控制器-06', 'type': 'controller',
     'icon': 'fas fa-cog', 'location': '增城02区', 'lat': 23.3215, 'lng': 113.8275, 'status': 'online',
     'last_online': datetime.now().isoformat()},
    {'id': 7, 'user_id': 2, 'name': '灌溉阀-07', 'type': 'irrigation',
     'icon': 'fas fa-tint', 'location': '增城01区', 'lat': 23.3225, 'lng': 113.8285, 'status': 'online',
     'last_online': (datetime.now() - timedelta(minutes=5)).isoformat()},
    {'id': 8, 'user_id': 3, 'name': '气象仪-08', 'type': 'sensor',
     'icon': 'fas fa-wind', 'location': '增城03区', 'lat': 23.3235, 'lng': 113.8295, 'status': 'online',
     'last_online': (datetime.now() - timedelta(minutes=20)).isoformat()},
]

DEMO_FARM_ACTIVITIES = [
    {
        'id': 1, 'user_id': 2, 'type': 'irrigation', 'type_label': '灌溉',
        'content': '试验田A自动灌溉完成，用时45分钟', 'plot_name': '增城01区-水稻主田',
        'created_at': (datetime.now() - timedelta(hours=3)).isoformat()
    },
    {
        'id': 2, 'user_id': 2, 'type': 'inspect', 'type_label': '巡查',
        'content': '检查大棚B番茄生长情况，发现少量叶斑病', 'plot_name': '增城03区-番茄大棚',
        'created_at': (datetime.now() - timedelta(hours=6)).isoformat()
    },
    {
        'id': 3, 'user_id': 2, 'type': 'fertilize', 'type_label': '施肥',
        'content': '试验田A追施叶面肥，促进籽粒饱满', 'plot_name': '增城01区-水稻主田',
        'created_at': (datetime.now() - timedelta(days=1)).isoformat()
    },
    {
        'id': 4, 'user_id': 3, 'type': 'pest', 'type_label': '病虫害防治',
        'content': '大棚B喷洒杀虫剂防治蚜虫', 'plot_name': '增城03区-番茄大棚',
        'created_at': (datetime.now() - timedelta(hours=2)).isoformat()
    },
    {
        'id': 5, 'user_id': 5, 'type': 'detect', 'type_label': 'AI识别',
        'content': '天河A区大豆AI识别完成，健康度95%', 'plot_name': '天河A区-大豆基地',
        'created_at': (datetime.now() - timedelta(hours=4)).isoformat()
    },
    {
        'id': 6, 'user_id': 2, 'type': 'warning', 'type_label': '风险预警',
        'content': '增城03区湿度超过阈值(88%)，触发预警', 'plot_name': '增城03区-番茄大棚',
        'created_at': (datetime.now() - timedelta(minutes=30)).isoformat()
    },
    {
        'id': 7, 'user_id': 2, 'type': 'harvest', 'type_label': '采收',
        'content': '增城02区玉米试验田开始采收，预计产量5000kg', 'plot_name': '增城02区-玉米试验田',
        'created_at': (datetime.now() - timedelta(hours=5)).isoformat()
    },
    {
        'id': 8, 'user_id': 6, 'type': 'maintenance', 'type_label': '设备维护',
        'content': '完成CAM_003摄像头校准，图像清晰度已恢复', 'plot_name': '增城03区-番茄大棚',
        'created_at': (datetime.now() - timedelta(hours=1)).isoformat()
    },
    {
        'id': 9, 'user_id': 5, 'type': 'fertilize', 'type_label': '施肥',
        'content': '天河A区大豆基地追施钾肥，促进结荚', 'plot_name': '天河A区-大豆基地',
        'created_at': (datetime.now() - timedelta(hours=8)).isoformat()
    },
    {
        'id': 10, 'user_id': 2, 'type': 'weed', 'type_label': '除草',
        'content': '增城01区水稻田人工除草完成，共清理杂草20kg', 'plot_name': '增城01区-水稻主田',
        'created_at': (datetime.now() - timedelta(days=2)).isoformat()
    },
    {
        'id': 11, 'user_id': 3, 'type': 'irrigation', 'type_label': '灌溉',
        'content': '增城05区蔬菜大棚滴灌系统运行正常，土壤湿度达标', 'plot_name': '增城05区-蔬菜大棚',
        'created_at': (datetime.now() - timedelta(hours=12)).isoformat()
    },
    {
        'id': 12, 'user_id': 2, 'type': 'detect', 'type_label': 'AI识别',
        'content': '增城04区小麦田AI识别发现稻纵卷叶螟，置信度89%', 'plot_name': '增城04区-小麦田',
        'created_at': (datetime.now() - timedelta(minutes=15)).isoformat()
    },
]

# ==================== 农事任务（补全 sort_order 字段） ====================
DEMO_FARM_TASKS = [
    {
        'id': 1, 'user_id': 2, 'title': '试验田A灌溉作业', 'type': 'irrigation',
        'plot_name': '增城01区-水稻主田', 'plot_id': 1,
        'scheduled_time': (datetime.now() + timedelta(hours=2)).isoformat(),
        'priority': 'high', 'completed': 0, 'completed_at': None,
        'notes': '预计持续2小时，土壤湿度需达到60%', 'reminder_sent': 0,
        'sort_order': 0,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 2, 'user_id': 2, 'title': '大棚B氮肥追肥', 'type': 'fertilize',
        'plot_name': '增城03区-番茄大棚', 'plot_id': 2,
        'scheduled_time': (datetime.now() + timedelta(hours=6)).isoformat(),
        'priority': 'medium', 'completed': 0, 'completed_at': None,
        'notes': '采用沟施方式，避免烧苗，每亩15kg', 'reminder_sent': 0,
        'sort_order': 1,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 3, 'user_id': 2, 'title': '巡查03区叶斑病情况', 'type': 'inspect',
        'plot_name': '增城03区-番茄大棚', 'plot_id': 2,
        'scheduled_time': (datetime.now() - timedelta(hours=2)).isoformat(),
        'priority': 'high', 'completed': 1,
        'completed_at': (datetime.now() - timedelta(hours=1)).isoformat(),
        'notes': '已确认叶斑病，已安排防治', 'reminder_sent': 1,
        'sort_order': 2,
        'created_at': datetime.now().isoformat(), 'updated_at': (datetime.now() - timedelta(hours=1)).isoformat()
    },
    {
        'id': 4, 'user_id': 2, 'title': '设备维护检查', 'type': 'maintenance',
        'plot_name': '全部区域', 'plot_id': None,
        'scheduled_time': (datetime.now() + timedelta(hours=8)).isoformat(),
        'priority': 'low', 'completed': 0, 'completed_at': None,
        'notes': '检查摄像头和传感器状态，清洁镜头', 'reminder_sent': 0,
        'sort_order': 3,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 5, 'user_id': 3, 'title': '大棚通风降湿', 'type': 'inspect',
        'plot_name': '增城03区-番茄大棚', 'plot_id': 2,
        'scheduled_time': (datetime.now() + timedelta(hours=1)).isoformat(),
        'priority': 'high', 'completed': 0, 'completed_at': None,
        'notes': '湿度88%，需要立即通风，防止病害', 'reminder_sent': 0,
        'sort_order': 0,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 6, 'user_id': 2, 'title': '玉米试验田除草', 'type': 'weed',
        'plot_name': '增城02区-玉米试验田', 'plot_id': 3,
        'scheduled_time': (datetime.now() + timedelta(hours=4)).isoformat(),
        'priority': 'medium', 'completed': 0, 'completed_at': None,
        'notes': '人工除草，清理行间杂草', 'reminder_sent': 0,
        'sort_order': 4,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 7, 'user_id': 5, 'title': '大豆基地病虫害防治', 'type': 'pest',
        'plot_name': '天河A区-大豆基地', 'plot_id': 4,
        'scheduled_time': (datetime.now() + timedelta(hours=3)).isoformat(),
        'priority': 'high', 'completed': 0, 'completed_at': None,
        'notes': '防治蚜虫，使用生物农药', 'reminder_sent': 0,
        'sort_order': 0,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 8, 'user_id': 2, 'title': '荔枝园修剪枝条', 'type': 'prune',
        'plot_name': '天河B区-荔枝园', 'plot_id': 5,
        'scheduled_time': (datetime.now() - timedelta(hours=4)).isoformat(),
        'priority': 'medium', 'completed': 1,
        'completed_at': (datetime.now() - timedelta(hours=2)).isoformat(),
        'notes': '已完成枯枝修剪，促进新梢生长', 'reminder_sent': 1,
        'sort_order': 5,
        'created_at': datetime.now().isoformat(), 'updated_at': (datetime.now() - timedelta(hours=2)).isoformat()
    },
    {
        'id': 9, 'user_id': 6, 'title': '小麦田灌溉检查', 'type': 'irrigation',
        'plot_name': '增城04区-小麦田', 'plot_id': 7,
        'scheduled_time': (datetime.now() + timedelta(hours=5)).isoformat(),
        'priority': 'low', 'completed': 0, 'completed_at': None,
        'notes': '检查滴灌带是否堵塞', 'reminder_sent': 0,
        'sort_order': 0,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'id': 10, 'user_id': 3, 'title': '蔬菜大棚采收黄瓜', 'type': 'harvest',
        'plot_name': '增城05区-蔬菜大棚', 'plot_id': 8,
        'scheduled_time': (datetime.now() + timedelta(hours=2)).isoformat(),
        'priority': 'high', 'completed': 0, 'completed_at': None,
        'notes': '采收成熟黄瓜，预计产量200kg', 'reminder_sent': 0,
        'sort_order': 1,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
]

DEMO_PEST_KNOWLEDGE = [
    {
        'id': 1, 'pest_name': '稻瘟病', 'english_name': 'Rice Blast', 'crop_type': '水稻',
        'category': '病害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '叶片出现梭形或纺锤形病斑，边缘褐色，中央灰白色，两端有褐色坏死线。严重时全株枯死。',
        'damage_features': '主要危害叶片、茎秆和穗部，导致减产20-50%，严重时可绝收。',
        'morphological_features': '病斑梭形，边缘褐色，中央灰白，有坏死线',
        'occurrence_season': '苗期至穗期均可发生，分蘖盛期和抽穗期最易感病。',
        'favorable_conditions': '温度25-28℃，相对湿度90%以上，阴雨连绵天气易大流行。',
        'distribution_areas': '全国稻区均有发生，南方重于北方',
        'prevention_methods': '选用抗病品种，合理施肥，科学管水，及时喷药防治',
        'chemical_control': '选用三环唑、稻瘟灵、春雷霉素等药剂，在发病初期喷雾防治。',
        'biological_control': '使用枯草芽孢杆菌、井冈霉素等生物农药防治。',
        'agricultural_control': '选用抗病品种，合理施肥，避免过量氮肥，浅水灌溉。',
        'similar_pests': json.dumps(['纹枯病', '白叶枯病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1536617621572-1d5f1e6269a0?w=800&q=80', 'https://images.unsplash.com/photo-1595508064774-5ff825a60098?w=800&q=80']),
        'video_url': None,
        'is_personal': 0, 'owner_email': None, 'is_shared': 0,
        'view_count': 1250, 'created_by': 'admin@farm.com',
        'created_at': (datetime.now() - timedelta(days=180)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=30)).isoformat(),
        'status': 'active'
    },
    {
        'id': 2, 'pest_name': '二化螟', 'english_name': 'Striped Rice Stem Borer', 'crop_type': '水稻',
        'category': '虫害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '幼虫蛀食茎秆，造成枯心苗、白穗和虫伤株。',
        'damage_features': '一代幼虫造成枯心苗，二代幼虫造成白穗，严重影响产量。',
        'morphological_features': '幼虫淡黄色，背面有5条紫褐色纵线',
        'occurrence_season': '一年发生1-5代，以第一代和第二代危害最重。',
        'favorable_conditions': '高温高湿有利于发生，分蘖期和孕穗期最易受害。',
        'distribution_areas': '全国稻区普遍发生',
        'prevention_methods': '农业防治与化学防治相结合，注意保护天敌',
        'chemical_control': '使用氯虫苯甲酰胺、阿维菌素、杀虫双等药剂，在卵孵化高峰期施药。',
        'biological_control': '释放赤眼蜂防治，保护利用蜘蛛、青蛙等天敌。',
        'agricultural_control': '齐泥割稻、低茬收割，减少越冬虫源；灌水杀蛹。',
        'similar_pests': json.dumps(['三化螟', '大螟']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&q=80', 'https://images.unsplash.com/photo-1563514227148-568d215cd82b?w=800&q=80']),
        'video_url': None,
        'is_personal': 0, 'owner_email': None, 'is_shared': 0,
        'view_count': 980, 'created_by': 'admin@farm.com',
        'created_at': (datetime.now() - timedelta(days=170)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=25)).isoformat(),
        'status': 'active'
    },
    {
        'id': 3, 'pest_name': '草地贪夜蛾', 'english_name': 'Fall Armyworm', 'crop_type': '玉米',
        'category': '虫害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '幼虫取食叶片造成孔洞，严重时吃光叶片，仅剩叶脉。可危害心叶、雄穗和雌穗。',
        'damage_features': '暴食性害虫，可在短时间内造成严重减产，甚至绝收。可迁飞扩散。',
        'morphological_features': '幼虫头部有倒Y形黑斑，第8腹节背面有4个大黑点呈方形排列',
        'occurrence_season': '周年发生，春夏秋季危害重，可随季风迁飞。',
        'favorable_conditions': '温度25-30℃，湿度适中，寄主植物丰富。',
        'distribution_areas': '华南、西南、江南等地区普遍发生，可迁飞至全国',
        'prevention_methods': '理化诱杀、生物防治与化学防治相结合，加强监测预警',
        'chemical_control': '选用氯虫苯甲酰胺、乙基多杀菌素、甲氨基阿维菌素苯甲酸盐等高效低毒药剂。',
        'biological_control': '利用寄生蜂、病原微生物（白僵菌、绿僵菌）防治，保护利用自然天敌。',
        'agricultural_control': '调整播期，避免重茬，种植诱集植物，及时清除杂草。',
        'similar_pests': json.dumps(['玉米螟', '粘虫']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800&q=80', 'https://images.unsplash.com/photo-1592419044706-39796d40f98c?w=800&q=80']),
        'video_url': None,
        'is_personal': 0, 'owner_email': None, 'is_shared': 0,
        'view_count': 2150, 'created_by': 'admin@farm.com',
        'created_at': (datetime.now() - timedelta(days=160)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=20)).isoformat(),
        'status': 'active'
    },
]

SUPPLEMENT_KNOWLEDGE = [
    {
        'pest_name': '纹枯病', 'english_name': 'Sheath Blight', 'crop_type': '水稻',
        'category': '病害', 'severity_level': 'medium', 'urgency_level': 'normal',
        'symptoms': '叶鞘出现椭圆形暗绿色水渍状病斑，后扩大成云纹状，叶鞘受害严重。叶片上病斑呈云纹状，边缘褐色，中央灰绿色。',
        'damage_features': '主要危害叶鞘和叶片，影响养分输送，导致秕谷增多，一般减产10-20%，严重时达30%以上。',
        'morphological_features': '病斑云纹状，边缘褐色，中央灰绿色，湿度大时可见白色菌丝',
        'occurrence_season': '从分蘖期开始发生，孕穗至抽穗期达高峰，灌浆期仍可扩展。',
        'favorable_conditions': '高温高湿（25-32℃，湿度90%以上）、长期深水灌溉、氮肥过量易发病。',
        'distribution_areas': '全国稻区均有发生，华南、江南地区发生较重。',
        'prevention_methods': '合理密植，科学施肥，浅水灌溉，适时晒田，药剂防治。',
        'chemical_control': '使用井冈霉素、噻呋酰胺、苯甲·丙环唑等药剂，重点喷植株中下部。',
        'biological_control': '施用井冈霉素、多抗霉素等抗生素类杀菌剂，利用木霉菌防治。',
        'agricultural_control': '合理密植，科学施肥，浅水灌溉，适时晒田，清除田边杂草。',
        'similar_pests': json.dumps(['稻瘟病', '白叶枯病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800&q=80', 'https://images.unsplash.com/photo-1563514227148-568d215cd82b?w=800&q=80']),
        'view_count': 856
    },
    {
        'pest_name': '稻飞虱', 'english_name': 'Rice Planthopper', 'crop_type': '水稻',
        'category': '虫害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '成虫和若虫群集于稻丛下部刺吸汁液，严重时稻株枯萎倒伏，称为"冒穿"。受害部位出现黄白色斑点。',
        'damage_features': '直接吸食汁液造成黄熟枯萎，传播病毒病（如水稻黑条矮缩病），排泄蜜露诱发煤污病。可造成减产30-50%。',
        'morphological_features': '成虫体长3-4mm，有长翅型和短翅型，体色多变，从淡褐色到黑褐色。',
        'occurrence_season': '5-10月均可发生，以8-9月晚稻抽穗期危害最重。可随气流远距离迁飞。',
        'favorable_conditions': '夏季高温干旱、台风暴雨天气有利于迁入和繁殖，偏施氮肥的田块发生重。',
        'distribution_areas': '全国稻区普遍发生，华南、长江中下游地区是重灾区。',
        'prevention_methods': '监测预警，科学管水，保护天敌，适时药剂防治。',
        'chemical_control': '选用吡蚜酮、烯啶虫胺、呋虫胺等高效低毒药剂，注意轮换使用，喷雾要喷到基部。',
        'biological_control': '保护蜘蛛、黑肩绿盲蝽等天敌，使用真菌类生物农药（白僵菌、绿僵菌）。',
        'agricultural_control': '合理密植，科学管水，避免偏施氮肥，及时晒田，铲除田边杂草。',
        'similar_pests': json.dumps(['稻纵卷叶螟', '二化螟']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1595508064774-5ff825a60098?w=800&q=80', 'https://images.unsplash.com/photo-1536617621572-1d5f1e6269a0?w=800&q=80']),
        'view_count': 1423
    },
    {
        'pest_name': '稻纵卷叶螟', 'english_name': 'Rice Leaf Roller', 'crop_type': '水稻',
        'category': '虫害', 'severity_level': 'medium', 'urgency_level': 'normal',
        'symptoms': '幼虫纵卷稻叶成筒状虫苞，匿居其中取食叶肉，仅留白色表皮，受害叶呈现"白叶"。',
        'damage_features': '影响水稻光合作用，导致空壳率增加，一般减产10-20%，大发生时可达30%以上。',
        'morphological_features': '成虫体长7-9mm，翅展18-21mm，体色黄褐，前翅有两条褐色横纹。',
        'occurrence_season': '一年发生2-5代，以5-6月和8-9月危害最重，可随季风迁飞。',
        'favorable_conditions': '温度25-28℃，湿度80%以上，多雨日、多露水天气有利于发生。',
        'distribution_areas': '全国稻区普遍发生，南方重于北方，沿海重于内陆。',
        'prevention_methods': '合理施肥，保护天敌，适时药剂防治，注意迁飞监测。',
        'chemical_control': '使用氯虫苯甲酰胺、阿维菌素、甲维盐等药剂，在卵孵化高峰期至1-2龄幼虫期施药。',
        'biological_control': '保护利用赤眼蜂、寄生蝇等天敌，使用苏云金杆菌制剂。',
        'agricultural_control': '合理施肥，避免偏施氮肥，适时烤田，降低田间湿度。',
        'similar_pests': json.dumps(['稻飞虱', '二化螟']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1595508064774-5ff825a60098?w=800&q=80', 'https://images.unsplash.com/photo-1536617621572-1d5f1e6269a0?w=800&q=80']),
        'view_count': 678
    },
    {
        'pest_name': '小麦蚜虫', 'english_name': 'Wheat Aphid', 'crop_type': '小麦',
        'category': '虫害', 'severity_level': 'medium', 'urgency_level': 'normal',
        'symptoms': '成虫和若虫刺吸小麦茎叶和嫩穗汁液，受害叶片发黄，生长受阻，严重时植株矮小，穗小粒少。',
        'damage_features': '直接吸食造成生长不良，分泌蜜露诱发煤污病，传播病毒病。可减产20-30%。',
        'morphological_features': '体长1.5-2.5mm，体色绿色或黑绿色，腹管长，尾片呈圆锥形。',
        'occurrence_season': '苗期至灌浆期均可发生，以拔节期至孕穗期危害最重。',
        'favorable_conditions': '温度15-22℃，干旱少雨有利于发生，偏施氮肥的田块虫量多。',
        'distribution_areas': '全国麦区均有发生，华北、西北地区发生较重。',
        'prevention_methods': '保护天敌，药剂防治，合理施肥，清除杂草。',
        'chemical_control': '使用吡虫啉、啶虫脒、高效氯氰菊酯等药剂，注意喷洒穗部。',
        'biological_control': '保护利用瓢虫、草蛉、蚜茧蜂等天敌，使用真菌制剂。',
        'agricultural_control': '清除田边杂草，合理施肥，适时灌溉，破坏其适生环境。',
        'similar_pests': json.dumps(['小麦红蜘蛛', '麦叶蜂']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1501430654243-c934cec2e1c0?w=800&q=80', 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800&q=80']),
        'view_count': 542
    },
    {
        'pest_name': '小麦赤霉病', 'english_name': 'Fusarium Head Blight', 'crop_type': '小麦',
        'category': '病害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '主要危害麦穗，发病小穗和颖片上出现水渍状褐色斑点，后扩展至整个麦穗，湿度大时产生粉红色霉层。',
        'damage_features': '导致麦粒干瘪，千粒重下降，产生毒素（赤霉毒素），人畜食用后中毒。可减产20-40%。',
        'morphological_features': '病穗呈褐色或枯白色，湿度大时可见粉红色霉层（分生孢子）。',
        'occurrence_season': '抽穗扬花期最易感病，开花至灌浆期是发病高峰期。',
        'favorable_conditions': '温度24-28℃，连续阴雨天气，田间湿度大，通风透光差易发病。',
        'distribution_areas': '长江流域、黄淮麦区发生较重，华北、东北局部发生。',
        'prevention_methods': '选用抗病品种，药剂预防，清沟排渍，降低田间湿度。',
        'chemical_control': '在抽穗扬花期使用多菌灵、甲基硫菌灵、戊唑醇等药剂预防，抓住齐穗期喷药。',
        'biological_control': '使用枯草芽孢杆菌、木霉菌等生物制剂，在扬花期喷雾。',
        'agricultural_control': '选用抗病品种，合理密植，清沟排渍，降低田间湿度，清除病残体。',
        'similar_pests': json.dumps(['小麦锈病', '小麦白粉病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1501430654243-c934cec2e1c0?w=800&q=80', 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800&q=80']),
        'view_count': 1289
    },
    {
        'pest_name': '玉米螟', 'english_name': 'Corn Borer', 'crop_type': '玉米',
        'category': '虫害', 'severity_level': 'medium', 'urgency_level': 'normal',
        'symptoms': '幼虫蛀食茎秆、穗轴和籽粒，造成茎折、穗腐和减产。心叶被害后展开呈排孔状。',
        'damage_features': '一般减产10-30%，严重时达50%以上，还传播玉米病害，降低品质。',
        'morphological_features': '成虫体长10-15mm，翅展20-30mm，体色黄褐至灰褐色。幼虫体背有3条深色纵线。',
        'occurrence_season': '一年发生1-6代，春玉米心叶期和夏玉米穗期危害最重。',
        'favorable_conditions': '温度22-28℃，相对湿度70%以上有利于发生，高秆品种受害重。',
        'distribution_areas': '全国玉米产区普遍发生，黄淮海夏玉米区发生较重。',
        'prevention_methods': '农业防治，生物防治，药剂防治，种植抗虫品种。',
        'chemical_control': '使用氯虫苯甲酰胺、阿维菌素、辛硫磷等药剂，在心叶末期施药（灌心）。',
        'biological_control': '释放赤眼蜂防治，使用白僵菌或苏云金杆菌制剂，保护利用天敌。',
        'agricultural_control': '处理秸秆消灭越冬虫源，种植诱集作物，黑光灯诱杀成虫，及时摘除虫果。',
        'similar_pests': json.dumps(['草地贪夜蛾', '玉米蚜']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800&q=80', 'https://images.unsplash.com/photo-1592419044706-39796d40f98c?w=800&q=80']),
        'view_count': 967
    },
    {
        'pest_name': '玉米大斑病', 'english_name': 'Northern Corn Leaf Blight', 'crop_type': '玉米',
        'category': '病害', 'severity_level': 'medium', 'urgency_level': 'normal',
        'symptoms': '主要危害叶片，发病初期出现水渍状青灰色斑点，后沿叶脉向两端扩展成梭形大斑，中央淡褐色，边缘暗褐色。',
        'damage_features': '严重影响光合作用，导致减产20-30%，降低品质，感病品种减产可达50%以上。',
        'morphological_features': '病斑梭形，长可达5-20cm，中央淡褐色，边缘暗褐色，严重时病斑融合。',
        'occurrence_season': '整个生育期均可发生，以抽雄灌浆期危害最重。',
        'favorable_conditions': '温度18-22℃，湿度90%以上，多雨、多雾、寡照天气易大流行。',
        'distribution_areas': '东北、华北、西北春玉米区和黄淮海夏玉米区均有发生。',
        'prevention_methods': '选用抗病品种，合理轮作，药剂防治，清洁田园。',
        'chemical_control': '使用苯醚甲环唑、嘧菌酯、代森锰锌等药剂，在发病初期喷雾。',
        'biological_control': '使用枯草芽孢杆菌、多抗霉素等生物农药防治。',
        'agricultural_control': '选用抗病品种，合理密植，清洁田园，轮作倒茬，适期早播。',
        'similar_pests': json.dumps(['玉米小斑病', '玉米灰斑病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=800&q=80', 'https://images.unsplash.com/photo-1592419044706-39796d40f98c?w=800&q=80']),
        'view_count': 734
    },
    {
        'pest_name': '番茄灰霉病', 'english_name': 'Tomato Gray Mold', 'crop_type': '番茄',
        'category': '病害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '危害花、果、叶、茎。花受害后腐烂，幼果受害后变软腐烂，密生灰色霉层。叶片受害出现V字形病斑。',
        'damage_features': '导致大量烂果，减产30-50%，温室大棚发生尤其严重，是番茄主要病害之一。',
        'morphological_features': '病部密生灰色霉层（分生孢子梗和分生孢子），这是主要识别特征。',
        'occurrence_season': '苗期至成株期均可发生，花期和果实成熟期最易感病，低温高湿条件下大流行。',
        'favorable_conditions': '温度20-23℃，相对湿度90%以上，弱光、通风不良易发病。',
        'distribution_areas': '全国番茄产区普遍发生，设施栽培发生重于露地。',
        'prevention_methods': '通风降湿，清除病残体，药剂防治，沾花时加入防霉药剂。',
        'chemical_control': '使用腐霉利、异菌脲、啶酰菌胺等药剂，在沾花时加入防霉药剂预防。',
        'biological_control': '使用木霉菌、枯草芽孢杆菌等生物农药，注意棚内温湿度管理。',
        'agricultural_control': '加强通风，降低湿度，及时清除病花、病果、病叶，合理密植，地膜覆盖。',
        'similar_pests': json.dumps(['番茄叶霉病', '番茄早疫病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=800&q=80', 'https://images.unsplash.com/photo-1561136594-7f68413baa99?w=800&q=80']),
        'view_count': 1567
    },
    {
        'pest_name': '番茄病毒病', 'english_name': 'Tomato Virus Disease', 'crop_type': '番茄',
        'category': '病害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '主要有番茄黄化曲叶病毒病（TYLCV）和番茄花叶病毒病（ToMV）。植株矮化，叶片黄化、卷曲、皱缩，果实着色不均。',
        'damage_features': '导致植株矮化，开花结果减少，果实品质下降，可减产50-80%，甚至绝收。',
        'morphological_features': '叶片黄化、卷曲、皱缩，植株矮化，生长点停止生长，果实小且着色不均。',
        'occurrence_season': '整个生育期均可发生，苗期和开花期发病对产量影响最大。',
        'favorable_conditions': '高温干旱有利于蚜虫、粉虱传播病毒，强光照、缺肥加重病害。',
        'distribution_areas': '全国番茄产区普遍发生，近年来TYLCV在南方设施番茄区暴发。',
        'prevention_methods': '选用抗病品种，防虫网隔离，防治传毒媒介，种子消毒。',
        'chemical_control': '防治传毒媒介（烟粉虱、蚜虫），使用吡虫啉、啶虫脒等药剂，病毒病本身无特效药。',
        'biological_control': '使用病毒抑制剂，防治传毒媒介，培育无病苗。',
        'agricultural_control': '选用抗病品种，种子消毒，防虫网隔离，及时清除病株，加强肥水管理。',
        'similar_pests': json.dumps(['番茄褪绿病毒病', '番茄斑萎病毒病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=800&q=80', 'https://images.unsplash.com/photo-1561136594-7f68413baa99?w=800&q=80']),
        'view_count': 1123
    },
    {
        'pest_name': '黄瓜霜霉病', 'english_name': 'Cucumber Downy Mildew', 'crop_type': '黄瓜',
        'category': '病害', 'severity_level': 'high', 'urgency_level': 'urgent',
        'symptoms': '叶片正面出现黄色多角形病斑，背面产生紫黑色霉层（孢子囊），严重时病斑连成片，叶片干枯。',
        'damage_features': '严重影响光合作用，导致减产30-50%，是黄瓜最主要的病害，流行时可绝收。',
        'morphological_features': '叶片正面黄色多角形病斑，背面紫黑色霉层，这是诊断要点。',
        'occurrence_season': '整个生育期均可发生，结瓜期最易感病，秋季和春季大棚发生严重。',
        'favorable_conditions': '温度15-24℃，湿度85%以上，叶面有水膜时最易发病，昼夜温差大、结露时间长易大流行。',
        'distribution_areas': '全国黄瓜产区普遍发生，设施栽培和露地栽培均可严重发生。',
        'prevention_methods': '选用抗病品种，生态防治（控温控湿），药剂防治，营养防治。',
        'chemical_control': '使用霜霉威、烯酰吗啉、氟吡菌胺等药剂，注意轮换用药，喷药要均匀周到。',
        'biological_control': '使用枯草芽孢杆菌、木霉菌等生物农药，配合高温闷棚。',
        'agricultural_control': '选用抗病品种，加强通风降湿，膜下灌溉，高温闷棚（30℃以上2小时），合理施肥。',
        'similar_pests': json.dumps(['黄瓜细菌性角斑病', '黄瓜白粉病']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=800&q=80', 'https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=800&q=80']),
        'view_count': 1834
    },
    {
        'pest_name': '白粉虱', 'english_name': 'Whitefly', 'crop_type': '黄瓜',
        'category': '虫害', 'severity_level': 'medium', 'urgency_level': 'normal',
        'symptoms': '成虫和若虫群集于叶背刺吸汁液，叶片褪绿变黄，分泌蜜露诱发煤污病，传播病毒病。',
        'damage_features': '导致植株衰弱，产量下降，传播病毒病，分泌蜜露污染叶片和果实，降低品质。',
        'morphological_features': '成虫体长1-1.5mm，白色，翅上有白色蜡粉。若虫扁平，淡黄色或淡绿色。',
        'occurrence_season': '温室周年发生，露地春末至秋季发生，秋季危害最重。',
        'favorable_conditions': '温度25-30℃，干旱少雨，通风不良，氮肥过量易大发生。',
        'distribution_areas': '全国保护地和露地蔬菜产区普遍发生，是设施蔬菜的主要害虫。',
        'prevention_methods': '防虫网隔离，黄板诱杀，药剂防治，生物防治，清除残株杂草。',
        'chemical_control': '使用吡虫啉、啶虫脒、螺虫乙酯等药剂，注意轮换用药，喷药要喷到叶背。',
        'biological_control': '释放丽蚜小蜂、瓢虫等天敌，使用昆虫病原真菌。',
        'agricultural_control': '清除残株杂草，防虫网隔离，黄板诱杀，加强通风，合理施肥。',
        'similar_pests': json.dumps(['烟粉虱', '蚜虫']),
        'image_urls': json.dumps(['https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=800&q=80', 'https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=800&q=80']),
        'view_count': 892
    }
]

SUPPLEMENT_COMMENTS = [
    {
        'user_id': 5, 'user_email': 'farmer4@farm.com', 'author_name': '陈大姐',
        'content': '请教各位专家，小麦锈病现在用什么药效果最好？往年用的三唑酮感觉效果一般了。',
        'images': json.dumps([]),
        'location': '天河A区-小麦田',
        'tags': '病害防治,小麦,提问',
        'status': 'approved',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 6,
        'views': 78,
        'created_at': (datetime.now() - timedelta(hours=12)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=12)).isoformat()
    },
    {
        'user_id': 6, 'user_email': 'farmer5@farm.com', 'author_name': '刘师傅',
        'content': '分享一个好消息！使用系统推荐的生物农药防治玉米螟，防治效果达到85%以上，而且成本比化学农药低20%。推荐大家尝试生物防治。',
        'images': json.dumps([]),
        'location': '增城02区-玉米试验田',
        'tags': '经验分享,生物防治,玉米',
        'status': 'approved',
        'is_pinned': 1,
        'pin_order': 3,
        'likes': 34,
        'views': 289,
        'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
        'updated_at': (datetime.now() - timedelta(days=1)).isoformat()
    },
    {
        'user_id': 2, 'user_email': 'farmer1@farm.com', 'author_name': '李大叔',
        'content': '这两天降温，大棚里的黄瓜出现了霜霉病早期症状，大家有什么好办法吗？除了打药，生态防治有什么技巧？',
        'images': json.dumps([]),
        'location': '增城03区-番茄大棚',
        'tags': '病害防治,大棚管理,提问',
        'status': 'approved',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 9,
        'views': 112,
        'created_at': (datetime.now() - timedelta(hours=8)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=8)).isoformat()
    },
    {
        'user_id': 3, 'user_email': 'farmer2@farm.com', 'author_name': '王婶',
        'content': '最近小麦进入了灌浆期，每天都有新的农事提醒，这个系统真的很贴心！希望今年能有个好收成。',
        'images': json.dumps([]),
        'location': '天河A区-小麦田',
        'tags': '丰收展望,系统反馈',
        'status': 'approved',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 22,
        'views': 156,
        'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=2)).isoformat()
    },
    {
        'user_id': 3, 'user_email': 'farmer2@farm.com', 'author_name': '王婶',
        'content': '请问各位，大棚白粉虱除了黄板诱杀，还有什么好的物理防治方法？',
        'images': json.dumps([]),
        'location': '增城05区-蔬菜大棚',
        'tags': '虫害防治,物理防治,提问',
        'status': 'pending',
        'is_pinned': 0,
        'pin_order': 0,
        'likes': 2,
        'views': 34,
        'created_at': (datetime.now() - timedelta(hours=1)).isoformat(),
        'updated_at': (datetime.now() - timedelta(hours=1)).isoformat()
    }
]

SUPPLEMENT_COST_RECORDS = [
    {'user_id': 2, 'category': '肥料', 'item_name': '尿素', 'amount': 1250.0, 'record_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 'notes': '水稻追肥用'},
    {'user_id': 2, 'category': '农药', 'item_name': '井冈霉素', 'amount': 340.0, 'record_date': (datetime.now() - timedelta(days=25)).strftime('%Y-%m-%d'), 'notes': '防治纹枯病'},
    {'user_id': 2, 'category': '水电', 'item_name': '灌溉用电', 'amount': 580.0, 'record_date': (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d'), 'notes': '6月份电费'},
    {'user_id': 2, 'category': '人工', 'item_name': '除草人工', 'amount': 1200.0, 'record_date': (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d'), 'notes': '雇佣3人除草5天'},
    {'user_id': 2, 'category': '肥料', 'item_name': '复合肥', 'amount': 2100.0, 'record_date': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'), 'notes': '玉米底肥'},
    {'user_id': 2, 'category': '种子', 'item_name': '水稻种子', 'amount': 860.0, 'record_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), 'notes': '优质稻种'},
    {'user_id': 2, 'category': '机械', 'item_name': '旋耕机租赁', 'amount': 600.0, 'record_date': datetime.now().strftime('%Y-%m-%d'), 'notes': '整地费用'},
    {'user_id': 3, 'category': '肥料', 'item_name': '有机肥', 'amount': 1500.0, 'record_date': (datetime.now() - timedelta(days=28)).strftime('%Y-%m-%d'), 'notes': '大棚基肥'},
    {'user_id': 3, 'category': '农药', 'item_name': '腐霉利', 'amount': 420.0, 'record_date': (datetime.now() - timedelta(days=22)).strftime('%Y-%m-%d'), 'notes': '防治灰霉病'},
    {'user_id': 3, 'category': '水电', 'item_name': '大棚用水', 'amount': 320.0, 'record_date': (datetime.now() - timedelta(days=18)).strftime('%Y-%m-%d'), 'notes': '滴灌用水'},
    {'user_id': 3, 'category': '人工', 'item_name': '采摘人工', 'amount': 800.0, 'record_date': (datetime.now() - timedelta(days=12)).strftime('%Y-%m-%d'), 'notes': '番茄采摘'},
    {'user_id': 3, 'category': '种子', 'item_name': '番茄种苗', 'amount': 650.0, 'record_date': (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d'), 'notes': '抗病品种'},
    {'user_id': 5, 'category': '肥料', 'item_name': '钾肥', 'amount': 980.0, 'record_date': (datetime.now() - timedelta(days=26)).strftime('%Y-%m-%d'), 'notes': '大豆结荚期追肥'},
    {'user_id': 5, 'category': '农药', 'item_name': '吡虫啉', 'amount': 280.0, 'record_date': (datetime.now() - timedelta(days=21)).strftime('%Y-%m-%d'), 'notes': '防治蚜虫'},
    {'user_id': 5, 'category': '机械', 'item_name': '收割机', 'amount': 1500.0, 'record_date': (datetime.now() - timedelta(days=16)).strftime('%Y-%m-%d'), 'notes': '小麦收割'},
    {'user_id': 5, 'category': '水电', 'item_name': '排灌用电', 'amount': 450.0, 'record_date': (datetime.now() - timedelta(days=11)).strftime('%Y-%m-%d'), 'notes': '5月份电费'},
]

SUPPLEMENT_ENVIRONMENT_DATA = [
    {'user_id': 2, 'device_id': 'CAM_001', 'temperature': 28.5, 'humidity': 75.0, 'soil_moisture': 62.0, 'light': 45000.0, 'record_time': (datetime.now() - timedelta(hours=2)).isoformat()},
    {'user_id': 2, 'device_id': 'CAM_001', 'temperature': 30.2, 'humidity': 72.0, 'soil_moisture': 60.0, 'light': 52000.0, 'record_time': (datetime.now() - timedelta(hours=4)).isoformat()},
    {'user_id': 2, 'device_id': 'CAM_001', 'temperature': 26.8, 'humidity': 78.0, 'soil_moisture': 65.0, 'light': 38000.0, 'record_time': (datetime.now() - timedelta(hours=6)).isoformat()},
    {'user_id': 2, 'device_id': 'SENSOR_002', 'temperature': 27.5, 'humidity': 80.0, 'soil_moisture': 58.0, 'light': 0.0, 'record_time': (datetime.now() - timedelta(hours=1)).isoformat()},
    {'user_id': 3, 'device_id': 'CAM_003', 'temperature': 26.0, 'humidity': 88.0, 'soil_moisture': 70.0, 'light': 35000.0, 'record_time': (datetime.now() - timedelta(hours=3)).isoformat()},
    {'user_id': 3, 'device_id': 'CAM_003', 'temperature': 24.5, 'humidity': 92.0, 'soil_moisture': 72.0, 'light': 28000.0, 'record_time': (datetime.now() - timedelta(hours=5)).isoformat()},
    {'user_id': 3, 'device_id': 'CAM_003', 'temperature': 25.2, 'humidity': 85.0, 'soil_moisture': 68.0, 'light': 42000.0, 'record_time': (datetime.now() - timedelta(hours=7)).isoformat()},
]

DEMO_AI_SOLUTIONS = [
    {
        'pest_id': 1, 'pest_name': '稻瘟病',
        'ai_response': '【AI防治方案】针对稻瘟病，建议：\n1. 化学防治：三环唑（每亩75-100g）或稻瘟灵（每亩100-150ml），发病初期喷雾，隔7-10天再喷一次。\n2. 生物防治：枯草芽孢杆菌（每亩200-300g）或井冈霉素（每亩150-200ml）。\n3. 农业防治：选用抗病品种，避免过量氮肥，浅水灌溉。\n4. 喷药重点：植株中上部，遇雨需补喷。',
        'thinking_process': '1. 确认为稻瘟病（Pyricularia oryzae）\n2. 病斑已扩散至剑叶，属急性型，需立即防治\n3. 结合分蘖期推荐三环唑+生物农药组合\n4. 建议孕穗期再防一次穗颈瘟',
        'prevention_summary': '三环唑/稻瘟灵喷雾 + 枯草芽孢杆菌生物防治，7-10天后再防一次',
        'quality_score': 95, 'is_recommended': 1, 'usage_count': 128,
        'created_by': 'admin@farm.com', 'source_detection_id': 1
    },
    {
        'pest_id': 2, 'pest_name': '二化螟',
        'ai_response': '【AI防治方案】二化螟防治关键在抓准卵孵化高峰期：\n1. 化学防治：氯虫苯甲酰胺（康宽，每亩10ml）或阿维菌素（每亩50-75ml）。\n2. 生物防治：释放赤眼蜂（每亩2-3万头），在发蛾始盛期开始，隔3-5天一次，连续2-3次。\n3. 农业防治：齐泥割稻、低茬收割减少越冬虫源；春季灌水杀蛹。\n4. 注意轮换用药，避免抗性。',
        'thinking_process': '1. 根据蛀食症状和体背纵线，确诊为二化螟\n2. 田间以2龄幼虫为主，正是防治适期\n3. 氯虫苯甲酰胺内吸性强，对新孵幼虫效果好\n4. 建议结合灌水杀蛹和释放赤眼蜂综合治理',
        'prevention_summary': '氯虫苯甲酰胺/阿维菌素抓孵化高峰 + 赤眼蜂生物防治 + 灌水杀蛹',
        'quality_score': 92, 'is_recommended': 1, 'usage_count': 96,
        'created_by': 'admin@farm.com', 'source_detection_id': 2
    },
    {
        'pest_id': 3, 'pest_name': '草地贪夜蛾',
        'ai_response': '【紧急方案】草地贪夜蛾是暴食性迁飞害虫，需紧急处置：\n1. 化学防治：乙基多杀菌素（每亩20-30ml）、氯虫苯甲酰胺（每亩10-15ml），重点喷心叶和雄穗。\n2. 生物防治：白僵菌或绿僵菌制剂（每亩100-200g），幼虫低龄期喷雾。\n3. 理化诱杀：性诱捕器（每亩1-2个）或杀虫灯诱杀成虫。\n4. 应急：3龄以上大幼虫可人工摘除虫苞踩死。',
        'thinking_process': '1. 头部倒Y斑和第8腹节4个黑点，确认草地贪夜蛾\n2. 该虫暴食性强、扩散快，玉米心叶期可致绝收\n3. 乙基多杀菌素特效，氯虫苯甲酰胺持效期长\n4. 建议全田普查，周边田块同步预防',
        'prevention_summary': '乙基多杀菌素/氯虫苯甲酰胺紧急喷雾 + 白僵菌生物防治 + 性诱/灯诱成虫',
        'quality_score': 98, 'is_recommended': 1, 'usage_count': 215,
        'created_by': 'admin@farm.com', 'source_detection_id': 3
    },
]

# ==================== 模型版本示例数据（新增） ====================
DEMO_MODEL_VERSIONS = [
    {'id': 1, 'version': 'yolov8n-v1.0', 'model_path': '/models/yolov8n_v1.pt', 'size_mb': 6.2, 'latency_ms': 45.5, 'map50': 0.89, 'status': 'ready'},
    {'id': 2, 'version': 'yolov8s-v1.1', 'model_path': '/models/yolov8s_v1_1.pt', 'size_mb': 22.4, 'latency_ms': 78.3, 'map50': 0.92, 'status': 'ready'},
    {'id': 3, 'version': 'yolov8m-v2.0', 'model_path': '/models/yolov8m_v2.pt', 'size_mb': 52.1, 'latency_ms': 125.6, 'map50': 0.94, 'status': 'testing'},
    {'id': 4, 'version': 'yolov8l-v3.0-beta', 'model_path': '/models/yolov8l_v3b.pt', 'size_mb': 87.3, 'latency_ms': 210.4, 'map50': 0.96, 'status': 'deprecated'},
]

DEMO_KNOWLEDGE_COLLECTIONS = [
    {'user_email': 'farmer1@farm.com', 'pest_id': 1, 'collection_type': 'pest', 'notes': '水稻田重点关注，已发生两次'},
    {'user_email': 'farmer1@farm.com', 'pest_id': 3, 'collection_type': 'pest', 'notes': '玉米地主要威胁'},
    {'user_email': 'farmer2@farm.com', 'pest_id': 2, 'collection_type': 'pest', 'notes': '大棚番茄也要注意二化螟'},
    {'user_email': 'farmer2@farm.com', 'pest_id': 8, 'collection_type': 'pest', 'notes': '番茄灰霉病防治参考'},
    {'user_email': 'farmer4@farm.com', 'pest_id': 5, 'collection_type': 'pest', 'notes': '小麦锈病防治方案很好'},
    {'user_email': 'farmer5@farm.com', 'pest_id': 6, 'collection_type': 'pest', 'notes': '玉米螟防治备用'},
]


def init_ai_solutions():
    """补充 AI 防治方案示例数据"""
    conn = sqlite3.connect(DB_PATHS['knowledge'])
    cursor = conn.cursor()

    # 确保表存在
    cursor.execute("""
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
    """)

    cursor.execute("DELETE FROM ai_prevention_knowledge")

    for sol in DEMO_AI_SOLUTIONS:
        cursor.execute("""
            INSERT INTO ai_prevention_knowledge 
            (pest_id, pest_name, ai_response, thinking_process, prevention_summary,
             quality_score, is_recommended, usage_count, created_by, source_detection_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sol['pest_id'], sol['pest_name'], sol['ai_response'],
            sol['thinking_process'], sol['prevention_summary'],
            sol['quality_score'], sol['is_recommended'], sol['usage_count'],
            sol['created_by'], sol['source_detection_id']
        ))

    conn.commit()
    conn.close()
    print(f"[✓] 已补充 {len(DEMO_AI_SOLUTIONS)} 条 AI 防治方案")


def init_knowledge_collections():
    """补充用户知识收藏示例数据"""
    conn = sqlite3.connect(DB_PATHS['knowledge'])
    cursor = conn.cursor()

    cursor.execute("DELETE FROM user_knowledge_collections")

    for col in DEMO_KNOWLEDGE_COLLECTIONS:
        cursor.execute("""
            INSERT INTO user_knowledge_collections 
            (user_email, pest_id, collection_type, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (col['user_email'], col['pest_id'], col['collection_type'], col['notes']))

    conn.commit()
    conn.close()
    print(f"[✓] 已补充 {len(DEMO_KNOWLEDGE_COLLECTIONS)} 条用户知识收藏")

# ==================== 数据库初始化函数 ====================

def init_email_db():
    """初始化主数据库（email.db）包含用户、地块、设备、农事记录等"""
    conn = sqlite3.connect(DB_PATHS['email'])
    cursor = conn.cursor()

    # 创建用户表（完整字段 - 与 database.py 完全一致，包含安全字段）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
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
            has_password INTEGER DEFAULT 0,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # 创建地块表 - 添加status和created_at字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plots (
            id INTEGER PRIMARY KEY,
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
    """)

    # 创建用户-地块关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_plots (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plot_id INTEGER NOT NULL,
            is_default INTEGER DEFAULT 0,
            bind_at TEXT,
            UNIQUE(user_id, plot_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plot_id) REFERENCES plots(id) ON DELETE CASCADE
        )
    """)

    # 创建设备表（补全 database.py 中的新字段）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY,
            device_id TEXT,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'camera',
            location TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            ip_address TEXT,
            firmware_version TEXT,
            status TEXT DEFAULT 'online',
            last_update TEXT
        )
    """)

    # 创建农事记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farm_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            field TEXT,
            date TEXT NOT NULL,
            operator TEXT,
            content TEXT,
            materials TEXT,
            remark TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建邮箱验证码表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_code (
            "to" TEXT,
            code TEXT,
            expire_time INTEGER,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    # 创建农场管理相关表 - 添加created_at字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farm_plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            area REAL NOT NULL,
            crop TEXT,
            plantDate DATE,
            status TEXT DEFAULT 'growing',
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 添加farm_crops表的stage, progress, health字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farm_crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plot_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            variety TEXT,
            area REAL,
            harvestDate DATE,
            status TEXT DEFAULT 'growing',
            tips TEXT,
            stage TEXT,
            progress INTEGER DEFAULT 0,
            health INTEGER DEFAULT 100,
            FOREIGN KEY (plot_id) REFERENCES farm_plots(id) ON DELETE CASCADE
        )
    """)

    # 添加user_devices表的last_update字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT,
            icon TEXT DEFAULT 'fas fa-video',
            location TEXT,
            lat REAL,
            lng REAL,
            status TEXT DEFAULT 'offline',
            last_online TIMESTAMP,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farm_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            type_label TEXT,
            content TEXT NOT NULL,
            plot_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 农事任务表 - 添加notes, reminder_sent, sort_order, updated_at字段
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farm_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            plot_name TEXT,
            plot_id INTEGER,
            scheduled_time TIMESTAMP NOT NULL,
            priority TEXT DEFAULT 'medium',
            completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            notes TEXT,
            reminder_sent INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (plot_id) REFERENCES farm_plots(id) ON DELETE SET NULL
        )
    """)

    # 创建用户权限表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            menu_code TEXT NOT NULL,
            can_view INTEGER DEFAULT 0,
            can_edit INTEGER DEFAULT 0,
            can_delete INTEGER DEFAULT 0,
            UNIQUE(role, menu_code)
        )
    """)

    # 创建模型版本表（新增）
    cursor.execute("""
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
    """)

    # 清空旧数据
    tables = ['users', 'plots', 'user_plots', 'devices', 'farm_records', 'email_code',
              'farm_plots', 'farm_crops', 'user_devices', 'farm_activities', 'farm_tasks',
              'user_permissions', 'model_versions']
    for table in tables:
        cursor.execute(f'DELETE FROM {table}')

    # 【关键修复】插入用户数据时对明文密码进行 bcrypt 哈希处理，并包含安全字段
    for user in DEMO_USERS:
        plain_pwd = user.get('password_hash')
        if plain_pwd:
            # 使用 bcrypt 生成哈希，与 database.py 中的 hash_password 函数一致
            hashed_pwd = bcrypt.hashpw(plain_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            hashed_pwd = None

        cursor.execute("""
            INSERT INTO users (id, phone, email, name, role, status, avatar, max_plots, 
                             last_login_ip, last_login_at, is_online, login_count, has_password, 
                             failed_login_attempts, locked_until, created_at, updated_at, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user['id'], user['phone'], user['email'], user['name'], user['role'],
            user['status'], user['avatar'], user['max_plots'], user['last_login_ip'],
            user['last_login_at'], user['is_online'], user['login_count'], user['has_password'],
            user.get('failed_login_attempts', 0), user.get('locked_until', 0),
            user['created_at'], user.get('updated_at'), hashed_pwd
        ))

    # 插入地块数据 - 包含status和created_at
    for plot in DEMO_PLOTS:
        cursor.execute("""
            INSERT INTO plots (id, name, location, crop_type, area, lat, lng, device_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plot['id'], plot['name'], plot['location'], plot['crop_type'], plot['area'],
            plot['lat'], plot['lng'], plot['device_id'], plot['status'], plot['created_at']
        ))

    # 插入用户-地块绑定
    for binding in USER_PLOT_BINDINGS:
        cursor.execute("""
            INSERT INTO user_plots (user_id, plot_id, is_default, bind_at)
            VALUES (?, ?, ?, ?)
        """, (binding['user_id'], binding['plot_id'], binding['is_default'], binding['bind_at']))

    # 插入设备数据（包含新增字段）
    for device in DEMO_DEVICES:
        cursor.execute("""
            INSERT INTO devices (id, device_id, name, type, location, lat, lng, ip_address, firmware_version, status, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device['id'], device.get('device_id'), device['name'], device.get('type', 'camera'),
            device.get('location'), device['lat'], device['lng'],
            device.get('ip_address'), device.get('firmware_version'),
            device['status'], device['last_update']
        ))

    # 插入农事记录 - 包含user_id, remark, updated_at
    for record in DEMO_FARM_RECORDS:
        cursor.execute("""
            INSERT INTO farm_records (id, user_id, type, field, date, operator, content, materials, remark, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record['id'], record['user_id'], record['type'], record['field'], record['date'],
            record['operator'], record['content'], record['materials'], record.get('remark', ''),
            record['status'], record['created_at'], record['updated_at']
        ))

    # 插入农场管理数据 - 包含created_at
    for plot in DEMO_FARM_PLOTS:
        cursor.execute("""
            INSERT INTO farm_plots (id, user_id, name, area, crop, plantDate, status, location, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plot['id'], plot['user_id'], plot['name'], plot['area'], plot['crop'],
            plot['plantDate'], plot['status'], plot['location'], plot['created_at']
        ))

    # 插入作物数据 - 包含stage, progress, health
    for crop in DEMO_FARM_CROPS:
        cursor.execute("""
            INSERT INTO farm_crops (id, plot_id, name, variety, area, harvestDate, status, tips, stage, progress, health)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            crop['id'], crop['plot_id'], crop['name'], crop['variety'],
            crop['area'], crop['harvestDate'], crop['status'], crop['tips'],
            crop['stage'], crop['progress'], crop['health']
        ))

    for device in DEMO_USER_DEVICES:
        cursor.execute("""
            INSERT INTO user_devices (id, user_id, name, type, icon, location, lat, lng, status, last_online, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device['id'], device['user_id'], device['name'], device['type'],
            device['icon'], device['location'], device.get('lat'), device.get('lng'),
            device['status'], device['last_online'],
            datetime.now().isoformat()
        ))

    # 插入农场活动
    for activity in DEMO_FARM_ACTIVITIES:
        cursor.execute("""
            INSERT INTO farm_activities (id, user_id, type, type_label, content, plot_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            activity['id'], activity['user_id'], activity['type'], activity['type_label'],
            activity['content'], activity['plot_name'], activity['created_at']
        ))

    # 插入农事任务 - 包含notes, reminder_sent, sort_order, updated_at
    for task in DEMO_FARM_TASKS:
        cursor.execute("""
            INSERT INTO farm_tasks (id, user_id, title, type, plot_name, plot_id, scheduled_time, 
                                   priority, completed, completed_at, notes, reminder_sent, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task['id'], task['user_id'], task['title'], task['type'], task['plot_name'],
            task['plot_id'], task['scheduled_time'], task['priority'], task['completed'],
            task.get('completed_at'), task['notes'], task.get('reminder_sent', 0),
            task.get('sort_order', 0),
            task['created_at'], task['updated_at']
        ))

    # 初始化默认权限数据
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
    cursor.executemany("""
        INSERT INTO user_permissions (role, menu_code, can_view, can_edit, can_delete)
        VALUES (?, ?, ?, ?, ?)
    """, default_perms)

    # 插入模型版本示例数据（新增）
    for model in DEMO_MODEL_VERSIONS:
        cursor.execute("""
            INSERT INTO model_versions (id, version, model_path, size_mb, latency_ms, map50, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            model['id'], model['version'], model['model_path'],
            model['size_mb'], model['latency_ms'], model['map50'], model['status']
        ))

    conn.commit()
    conn.close()
    print(f"[✓] email.db 初始化完成（{len(DEMO_USERS)}个用户，{len(DEMO_PLOTS)}个地块，{len(DEMO_MODEL_VERSIONS)}个模型版本）- 密码已自动哈希，所有字段已补全")
    return len(DEMO_USERS), len(DEMO_PLOTS), len(DEMO_DEVICES)


def init_detection_db():
    """初始化检测历史数据库"""
    conn = sqlite3.connect(DB_PATHS['detection'])
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detection_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pest_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            image_base64 TEXT,
            original_image_base64 TEXT,
            device_id TEXT,
            location_lat REAL,
            location_lng REAL,
            risk_level TEXT DEFAULT 'low',
            status TEXT DEFAULT 'active',
            notes TEXT,
            crop_type TEXT,
            user_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pest_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            pest_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            bbox_x1 REAL,
            bbox_y1 REAL,
            bbox_x2 REAL,
            bbox_y2 REAL,
            FOREIGN KEY (record_id) REFERENCES detection_records(id) ON DELETE CASCADE
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON detection_records(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pest_name ON detection_records(pest_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_level ON detection_records(risk_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_record_id ON pest_details(record_id)")

    # 清空旧数据
    cursor.execute("DELETE FROM detection_records")
    cursor.execute("DELETE FROM pest_details")

    # 【新增】插入检测详情（边界框）
    for detail in DEMO_PEST_DETAILS:
        cursor.execute("""
                INSERT INTO pest_details 
                (record_id, pest_name, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
            detail['record_id'], detail['pest_name'], detail['confidence'],
            detail['bbox_x1'], detail['bbox_y1'], detail['bbox_x2'], detail['bbox_y2']
        ))

    print(f"[✓] 已补充 {len(DEMO_PEST_DETAILS)} 条检测详情边界框数据")

    # 插入检测记录 - 包含crop_type和updated_at
    for record in DEMO_DETECTIONS:
        cursor.execute("""
            INSERT INTO detection_records 
            (id, pest_name, confidence, image_base64, original_image_base64, device_id, 
             location_lat, location_lng, risk_level, status, notes, crop_type, user_email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record['id'], record['pest_name'], record['confidence'],
            record['image_base64'], record['original_image_base64'], record['device_id'],
            record['location_lat'], record['location_lng'], record['risk_level'],
            record['status'], record['notes'], record.get('crop_type'),
            record.get('user_email'),
            record['created_at'], record['updated_at']
        ))

    conn.commit()
    conn.close()
    today_count = sum(1 for r in DEMO_DETECTIONS if r['created_at'].startswith(datetime.now().strftime('%Y-%m-%d')))
    print(f"[✓] detection_history.db 初始化完成（{len(DEMO_DETECTIONS)}条记录，今日{today_count}条）")
    return len(DEMO_DETECTIONS)


def init_comments_db():
    """初始化评论数据库"""
    conn = sqlite3.connect(DB_PATHS['comments'])
    cursor = conn.cursor()

    # 创建评论主表 - 添加is_pinned, pin_order, likes, views, updated_at字段
    cursor.execute("""
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建回复表（支持嵌套回复）
    cursor.execute("""
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
    """)

    # 创建点赞记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comment_likes (
            comment_id INTEGER,
            user_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (comment_id, user_email),
            FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
        )
    """)

    # 创建回复点赞记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reply_likes (
            reply_id INTEGER,
            user_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (reply_id, user_email),
            FOREIGN KEY (reply_id) REFERENCES comment_replies(id) ON DELETE CASCADE
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_status ON comments(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_pinned ON comments(is_pinned)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comment_created ON comments(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reply_comment ON comment_replies(comment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reply_parent ON comment_replies(parent_reply_id)")

    # 清空旧数据
    cursor.execute("DELETE FROM reply_likes")
    cursor.execute("DELETE FROM comment_replies")
    cursor.execute("DELETE FROM comment_likes")
    cursor.execute("DELETE FROM comments")

    # 插入评论数据 - 包含is_pinned, pin_order, likes, views, updated_at
    for comment in DEMO_COMMENTS:
        cursor.execute("""
            INSERT INTO comments 
            (id, user_id, user_email, author_name, content, images, location, tags, 
             status, is_pinned, pin_order, likes, views, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comment['id'], comment['user_id'], comment['user_email'], comment['author_name'],
            comment['content'], comment['images'], comment['location'], comment['tags'],
            comment['status'], comment['is_pinned'], comment['pin_order'],
            comment['likes'], comment['views'], comment['created_at'], comment['updated_at']
        ))

    # 添加回复示例
    cursor.execute("""
        INSERT INTO comment_replies (comment_id, user_id, user_email, author_name, content, to_user, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (2, 2, 'farmer1@farm.com', '李大叔', '我之前也遇到过，是缺镁，建议补充硫酸钾镁肥', '王婶',
          (datetime.now() - timedelta(hours=2)).isoformat()))

    # 添加点赞示例
    cursor.execute("INSERT INTO comment_likes (comment_id, user_email, created_at) VALUES (?, ?, ?)",
                   (1, 'farmer2@farm.com', datetime.now().isoformat()))
    cursor.execute("INSERT INTO comment_likes (comment_id, user_email, created_at) VALUES (?, ?, ?)",
                   (1, 'farmer3@farm.com', datetime.now().isoformat()))

    # 【新增】插入回复点赞示例
    cursor.execute("""
        INSERT INTO reply_likes (reply_id, user_email, created_at) VALUES (?, ?, ?)
    """, (1, 'farmer2@farm.com', datetime.now().isoformat()))
    cursor.execute("""
        INSERT INTO reply_likes (reply_id, user_email, created_at) VALUES (?, ?, ?)
    """, (1, 'farmer4@farm.com', datetime.now().isoformat()))
    cursor.execute("""
        INSERT INTO reply_likes (reply_id, user_email, created_at) VALUES (?, ?, ?)
    """, (2, 'farmer1@farm.com', datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print(f"[✓] comments.db 初始化完成（{len(DEMO_COMMENTS)}条评论）")
    return len(DEMO_COMMENTS)


def init_chat_db():
    """初始化对话记录数据库"""
    conn = sqlite3.connect(DB_PATHS['chat'])
    cursor = conn.cursor()

    # 【修复】添加user_email字段，与_database.py保持一致
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            title TEXT NOT NULL,
            pest_name TEXT,
            image_base64 TEXT,
            messages TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_interrupted BOOLEAN DEFAULT 0
        )
    """)

    cursor.execute("DELETE FROM chat_sessions")

    # 添加示例对话
    sample_messages = [
        {
            'role': 'user',
            'text': '帮我看看这是什么病虫害？',
            'content': '帮我看看这是什么病虫害？',
            'type': 'text'
        },
        {
            'role': 'ai',
            'text': '根据您提供的图片，这看起来像是**草地贪夜蛾**的危害症状。主要特征：叶片出现不规则孔洞，有黑色虫粪，可见幼虫藏匿于心叶中。',
            'content': '根据您提供的图片，这看起来像是**草地贪夜蛾**的危害症状。主要特征：叶片出现不规则孔洞，有黑色虫粪，可见幼虫藏匿于心叶中。',
            'thinking': '1. 观察图片特征：叶片破损、虫粪\n2. 排除其他害虫：与玉米螟区别\n3. 确认：符合草地贪夜蛾幼虫特征',
            'type': 'markdown'
        },
        {
            'role': 'user',
            'text': '应该怎么防治？',
            'content': '应该怎么防治？',
            'type': 'text'
        },
        {
            'role': 'ai',
            'text': '推荐使用氯虫苯甲酰胺（康宽）进行防治，每亩用量20-30ml，兑水30公斤喷雾。最佳施药时间是清晨或傍晚，注意喷洒心叶部位。',
            'content': '推荐使用氯虫苯甲酰胺（康宽）进行防治，每亩用量20-30ml，兑水30公斤喷雾。最佳施药时间是清晨或傍晚，注意喷洒心叶部位。',
            'type': 'markdown'
        }
    ]

    # 【修复】插入时包含user_email字段
    cursor.execute("""
        INSERT INTO chat_sessions (user_email, title, pest_name, messages, created_at, updated_at, is_interrupted)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'farmer1@farm.com',
        '草地贪夜蛾咨询',
        '草地贪夜蛾',
        json.dumps(sample_messages, ensure_ascii=False),
        (datetime.now() - timedelta(hours=1)).isoformat(),
        (datetime.now() - timedelta(minutes=30)).isoformat(),
        0
    ))

    conn.commit()
    conn.close()
    print("[✓] chat_history.db 初始化完成（1条示例对话，含user_email）")


def init_knowledge_db():
    """初始化知识库数据库"""
    conn = sqlite3.connect(DB_PATHS['knowledge'])
    cursor = conn.cursor()

    # 病虫害知识库主表
    cursor.execute("""
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
            is_personal INTEGER DEFAULT 0,
            owner_email TEXT,
            is_shared INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pest_name, crop_type, owner_email)
        )
    """)

    # AI防治方案库
    cursor.execute("""
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
    """)

    # 用户收藏表
    cursor.execute("""
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
    """)

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_crop ON pest_knowledge(crop_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_category ON pest_knowledge(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_name ON pest_knowledge(pest_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_personal ON pest_knowledge(is_personal)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_owner ON pest_knowledge(owner_email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pest_status ON pest_knowledge(status)')

    # 清空旧数据
    cursor.execute('DELETE FROM user_knowledge_collections')
    cursor.execute('DELETE FROM ai_prevention_knowledge')
    cursor.execute('DELETE FROM pest_knowledge')

    # 插入知识库示例数据
    for knowledge in DEMO_PEST_KNOWLEDGE:
        cursor.execute("""
            INSERT INTO pest_knowledge (
                id, pest_name, english_name, crop_type, category, symptoms, damage_features,
                morphological_features, occurrence_season, favorable_conditions, distribution_areas,
                prevention_methods, chemical_control, biological_control, agricultural_control,
                similar_pests, image_urls, video_url, severity_level, urgency_level, status,
                is_personal, owner_email, is_shared, view_count, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            knowledge['id'], knowledge['pest_name'], knowledge['english_name'], knowledge['crop_type'],
            knowledge['category'], knowledge['symptoms'], knowledge['damage_features'],
            knowledge['morphological_features'], knowledge['occurrence_season'],
            knowledge['favorable_conditions'], knowledge['distribution_areas'],
            knowledge['prevention_methods'], knowledge['chemical_control'],
            knowledge['biological_control'], knowledge['agricultural_control'],
            knowledge['similar_pests'], knowledge['image_urls'], knowledge['video_url'],
            knowledge['severity_level'], knowledge['urgency_level'], knowledge['status'],
            knowledge['is_personal'], knowledge['owner_email'], knowledge['is_shared'],
            knowledge['view_count'], knowledge['created_by'], knowledge['created_at'],
            knowledge['updated_at']
        ))

    conn.commit()
    conn.close()
    print(f"[✓] knowledge_base.db 初始化完成（{len(DEMO_PEST_KNOWLEDGE)}条知识记录）")
    return len(DEMO_PEST_KNOWLEDGE)

# 为前30条检测记录生成边界框详情
DEMO_PEST_DETAILS = []
for record in DEMO_DETECTIONS[:30]:
    DEMO_PEST_DETAILS.append({
        'record_id': record['id'],
        'pest_name': record['pest_name'],
        'confidence': round(min(99.9, max(0, record['confidence'] + random.uniform(-3, 3))), 1),
        'bbox_x1': round(random.uniform(0.05, 0.35), 4),
        'bbox_y1': round(random.uniform(0.05, 0.35), 4),
        'bbox_x2': round(random.uniform(0.45, 0.85), 4),
        'bbox_y2': round(random.uniform(0.45, 0.85), 4)
    })


# ==================== 新增：补充数据初始化函数 ====================

def init_knowledge_supplement():
    """补充知识库数据"""
    conn = sqlite3.connect(DB_PATHS['knowledge'])
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for data in SUPPLEMENT_KNOWLEDGE:
        # 检查是否已存在（避免重复插入）
        cursor.execute(
            "SELECT id FROM pest_knowledge WHERE pest_name = ? AND crop_type = ? AND is_personal = 0",
            (data['pest_name'], data['crop_type'])
        )
        if cursor.fetchone():
            skipped += 1
            continue

        cursor.execute('''
            INSERT INTO pest_knowledge (
                pest_name, english_name, crop_type, category, symptoms, damage_features,
                morphological_features, occurrence_season, favorable_conditions, distribution_areas,
                prevention_methods, chemical_control, biological_control, agricultural_control,
                similar_pests, image_urls, video_url, severity_level, urgency_level, status,
                is_personal, owner_email, is_shared, view_count, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (
            data['pest_name'], data['english_name'], data['crop_type'],
            data['category'], data['symptoms'], data['damage_features'],
            data.get('morphological_features'), data['occurrence_season'],
            data['favorable_conditions'], data['distribution_areas'],
            data['prevention_methods'], data['chemical_control'],
            data['biological_control'], data['agricultural_control'],
            data['similar_pests'], data['image_urls'], data.get('video_url'),
            data['severity_level'], data['urgency_level'], 'active',
            0, None, 0, data.get('view_count', 0), 'admin@farm.com'
        ))
        inserted += 1

    conn.commit()
    conn.close()
    return inserted, skipped


def init_personal_knowledge():
    """补充农户个人知识（体现权限区别）"""
    conn = sqlite3.connect(DB_PATHS['knowledge'])
    cursor = conn.cursor()

    # 农户李大叔的个人知识（is_personal=1）
    cursor.execute('''
        INSERT INTO pest_knowledge (
            pest_name, crop_type, category, symptoms, prevention_methods,
            is_personal, owner_email, status, created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, 1, ?, 'active', ?, datetime('now'))
    ''', (
        '我家水稻的特殊叶斑病', '水稻', '病害',
        '叶片出现不规则黄斑，边缘褐色',
        '试用枯草芽孢杆菌防治',
        'farmer1@farm.com',
        'farmer1@farm.com'
    ))

    conn.commit()
    conn.close()


def init_comments_supplement():
    """补充评论数据"""
    conn = sqlite3.connect(DB_PATHS['comments'])
    cursor = conn.cursor()

    inserted = 0

    for data in SUPPLEMENT_COMMENTS:
        cursor.execute('''
            INSERT INTO comments 
            (user_id, user_email, author_name, content, images, location, tags, 
             status, is_pinned, pin_order, likes, views, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['user_id'], data['user_email'], data['author_name'],
            data['content'], data['images'], data['location'], data['tags'],
            data['status'], data['is_pinned'], data['pin_order'],
            data['likes'], data['views'], data['created_at'], data['updated_at']
        ))
        inserted += 1

    # 补充一些回复数据
    replies = [
        (8, None, 6, 'farmer5@farm.com', '刘师傅', '建议使用戊唑醇或丙环唑，现在抗性小，效果更好。', '陈大姐', 5),
        (10, None, 3, 'farmer2@farm.com', '王婶', '可以尝试高温闷棚，晴天上午闭棚升温到35-38℃维持2小时，然后通风降温，连续2-3天效果挺好。', '李大叔', 8),
    ]

    # 获取刚插入的评论ID（实际应该使用cursor.lastrowid，这里简化处理）
    cursor.execute("SELECT MAX(id) FROM comments")
    max_id = cursor.fetchone()[0] or 0

    for reply in replies:
        comment_id = max_id - 4 + reply[0] - 8  # 简单映射，实际应用需要更精确的处理
        if comment_id > 0:
            cursor.execute('''
                INSERT INTO comment_replies 
                (comment_id, parent_reply_id, user_id, user_email, author_name, content, to_user, likes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-2 hours'))
            ''', (comment_id, reply[1], reply[2], reply[3], reply[4], reply[5], reply[6], reply[7]))

    conn.commit()
    conn.close()
    return inserted


def init_cost_supplement():
    """补充成本记录数据"""
    conn = sqlite3.connect(DB_PATHS['email'])
    cursor = conn.cursor()

    # 确保成本表存在
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

    inserted = 0

    for data in SUPPLEMENT_COST_RECORDS:
        # 检查是否已存在类似记录（同一天、同一用户、同一类别、同一物品）
        cursor.execute('''
            SELECT 1 FROM cost_records 
            WHERE user_id = ? AND category = ? AND item_name = ? AND record_date = ?
        ''', (data['user_id'], data['category'], data['item_name'], data['record_date']))

        if cursor.fetchone():
            continue

        cursor.execute('''
            INSERT INTO cost_records 
            (user_id, category, item_name, amount, record_date, related_record_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['user_id'], data['category'], data['item_name'],
            data['amount'], data['record_date'],
            data.get('related_record_id'),
            data['notes']
        ))
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


def init_environment_supplement():
    """补充环境传感器数据"""
    conn = sqlite3.connect(DB_PATHS['email'])
    cursor = conn.cursor()

    # 确保环境表存在
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

    inserted = 0

    for data in SUPPLEMENT_ENVIRONMENT_DATA:
        cursor.execute('''
            INSERT INTO environment_records 
            (user_id, device_id, temperature, humidity, soil_moisture, light, record_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['user_id'], data['device_id'], data['temperature'],
            data['humidity'], data['soil_moisture'], data['light'], data['record_time']
        ))
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


def init_today_data_supplement():
    """补充今日待办任务（确保首页有数据显示）"""
    conn = sqlite3.connect(DB_PATHS['email'])
    cursor = conn.cursor()

    # 只添加给李大叔（user_id=2），确保他有今日待办
    inserted_tasks = 0
    for task in SUPPLEMENT_TODAY_TASKS:
        # 检查是否已存在类似任务（避免重复）
        cursor.execute('''
            SELECT 1 FROM farm_tasks 
            WHERE user_id = ? AND title = ? AND DATE(scheduled_time) = DATE(?)
        ''', (task['user_id'], task['title'], task['scheduled_time']))

        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO farm_tasks 
                (user_id, title, type, plot_name, plot_id, scheduled_time, 
                 priority, completed, completed_at, notes, reminder_sent, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task['user_id'], task['title'], task['type'], task['plot_name'],
                task['plot_id'], task['scheduled_time'], task['priority'],
                task['completed'], task['completed_at'], task['notes'],
                task['reminder_sent'], task.get('sort_order', 0), task['created_at'], task['updated_at']
            ))
            inserted_tasks += 1

    conn.commit()

    # 补充最近动态（确保"最近动态"有内容）
    inserted_activities = 0
    for activity in SUPPLEMENT_ACTIVITIES_FOR_TODAY:
        cursor.execute('''
            INSERT INTO farm_activities (user_id, type, type_label, content, plot_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            activity['user_id'], activity['type'], activity['type_label'],
            activity['content'], activity['plot_name'], activity['created_at']
        ))
        inserted_activities += 1

    conn.commit()
    conn.close()
    return inserted_tasks, inserted_activities


def print_summary():
    """打印初始化完成后的统计摘要"""
    print("\n" + "=" * 70)
    print("🌱 智能农务系统 - 示例数据初始化完成报告")
    print("=" * 70)

    # 用户统计
    conn = sqlite3.connect(DB_PATHS['email'])
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    role_dist = dict(cursor.fetchall())

    cursor.execute("SELECT status, COUNT(*) FROM users WHERE role='farmer' GROUP BY status")
    status_dist = dict(cursor.fetchall())

    print(f"\n👥 用户数据（七个用户）:")
    print(f"   总用户数: {total_users} 人")
    print(f"   角色分布: 管理员 {role_dist.get('admin', 0)} 人, 农户 {role_dist.get('farmer', 0)} 人")
    print(f"   农户状态: ", end="")
    status_map = {'active': '正常', 'pending': '待审核', 'banned': '已禁用'}
    print(", ".join([f"{status_map.get(k, k)} {v}人" for k, v in status_dist.items()]))

    # 显示具体用户
    print("\n   用户明细:")
    for user in DEMO_USERS:
        status_icon = "✓" if user['status'] == 'active' else "⏳" if user['status'] == 'pending' else "✗"
        role_icon = "👑" if user['role'] == 'admin' else "🌾"
        pwd_status = "🔐" if user.get('password_hash') else "⚠️无密码"
        lock_info = ""
        if user.get('failed_login_attempts', 0) >= 5:
            lock_info = f" [已锁定,失败{user['failed_login_attempts']}次]"
        print(f"   {status_icon} {role_icon} {user['name']} ({user['email']}) - {pwd_status}{lock_info}")

    cursor.execute("SELECT COUNT(*) FROM plots")
    total_plots = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(area) FROM plots WHERE status='active'")
    total_area = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM user_plots")
    total_bindings = cursor.fetchone()[0]

    print(f"\n🌾 地块数据:")
    print(f"   总地块数: {total_plots} 个")
    print(f"   总种植面积: {total_area:.1f} 亩")
    print(f"   已绑定: {total_bindings} 个用户-地块关联")

    cursor.execute("SELECT COUNT(*) FROM devices")
    total_devices = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM devices GROUP BY status")
    device_status = dict(cursor.fetchall())

    cursor.execute("SELECT type, COUNT(*) FROM devices GROUP BY type")
    device_types = dict(cursor.fetchall())

    print(f"\n📹 监测设备:")
    print(f"   总设备数: {total_devices} 个")
    print(f"   状态分布: ", end="")
    dev_map = {'online': '在线', 'warning': '异常', 'offline': '离线'}
    print(", ".join([f"{dev_map.get(k, k)} {v}个" for k, v in device_status.items()]))
    print(f"   类型分布: ", end="")
    type_map = {'camera': '摄像头', 'sensor': '传感器', 'controller': '控制器',
                'drone': '无人机', 'irrigation': '灌溉设备', 'weather': '气象站'}
    print(", ".join([f"{type_map.get(k, k)} {v}个" for k, v in device_types.items()]))

    cursor.execute("SELECT COUNT(*) FROM farm_records")
    total_records = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM farm_tasks")
    total_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM farm_tasks WHERE completed=0")
    pending_tasks = cursor.fetchone()[0]

    print(f"\n📝 农事管理:")
    print(f"   历史记录: {total_records} 条")
    print(f"   待办任务: {pending_tasks} 项")
    print(f"   总任务数: {total_tasks} 项")

    cursor.execute("SELECT COUNT(*) FROM farm_plots")
    farm_plots = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM farm_crops")
    farm_crops = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM farm_activities")
    activities = cursor.fetchone()[0]

    print(f"\n🚜 农场管理数据:")
    print(f"   农场地块: {farm_plots} 个")
    print(f"   种植作物: {farm_crops} 种")
    print(f"   最近活动: {activities} 条")

    # 成本管理统计（新增）
    cursor.execute("SELECT COUNT(*) FROM cost_records")
    total_cost = cursor.fetchone()[0]
    if total_cost > 0:
        cursor.execute("SELECT category, SUM(amount) FROM cost_records GROUP BY category")
        cost_dist = dict(cursor.fetchall())
        cursor.execute("SELECT SUM(amount) FROM cost_records")
        total_amount = cursor.fetchone()[0] or 0
    else:
        cost_dist = {}
        total_amount = 0

    print(f"\n💰 成本管理数据:")
    print(f"   总记录数: {total_cost} 条")
    print(f"   累计投入: ¥{total_amount:.2f}")
    if cost_dist:
        print(f"   分类统计:")
        for cat, amount in sorted(cost_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {cat}: ¥{amount:.2f}")

    # 环境数据（新增）
    cursor.execute("SELECT COUNT(*) FROM environment_records")
    total_env = cursor.fetchone()[0]
    print(f"\n🌡️ 环境监测数据:")
    print(f"   传感器记录: {total_env} 条")

    # 模型版本统计（新增）
    cursor.execute("SELECT COUNT(*) FROM model_versions")
    total_models = cursor.fetchone()[0]
    cursor.execute("SELECT status, COUNT(*) FROM model_versions GROUP BY status")
    model_status = dict(cursor.fetchall())
    print(f"\n🤖 模型版本管理:")
    print(f"   总版本数: {total_models} 个")
    if model_status:
        print(f"   状态分布: ", end="")
        m_map = {'ready': '就绪', 'testing': '测试中', 'deprecated': '已弃用'}
        print(", ".join([f"{m_map.get(k, k)} {v}个" for k, v in model_status.items()]))

    conn.close()

    # 检测记录统计
    conn = sqlite3.connect(DB_PATHS['detection'])
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM detection_records")
    total_detections = cursor.fetchone()[0]

    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM detection_records WHERE DATE(created_at) = DATE('now')")
    today_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM detection_records WHERE DATE(created_at) = DATE('now') AND risk_level='high'")
    today_high_risk = cursor.fetchone()[0]

    cursor.execute("SELECT risk_level, COUNT(*) FROM detection_records GROUP BY risk_level")
    risk_dist = dict(cursor.fetchall())

    print(f"\n🔍 检测历史:")
    print(f"   总记录数: {total_detections} 条")
    print(f"   今日检测: {today_count} 次")
    print(f"   今日异常: {today_high_risk} 处高风险")
    print(f"   风险分布: ", end="")
    risk_map = {'high': '高风险', 'medium': '中风险', 'low': '低风险'}
    print(", ".join([f"{risk_map.get(k, k)} {v}条" for k, v in risk_dist.items()]))
    conn.close()

    # 评论统计
    conn = sqlite3.connect(DB_PATHS['comments'])
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM comments")
    total_comments = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM comments GROUP BY status")
    comment_status = dict(cursor.fetchall())

    cursor.execute("SELECT COUNT(*) FROM comment_replies")
    total_replies = cursor.fetchone()[0]

    print(f"\n💬 交流社区:")
    print(f"   评论总数: {total_comments} 条")
    print(f"   审核状态: ", end="")
    cmt_map = {'approved': '已通过', 'pending': '待审核', 'rejected': '已拒绝'}
    print(", ".join([f"{cmt_map.get(k, k)} {v}条" for k, v in comment_status.items()]))
    print(f"   回复数量: {total_replies} 条")
    conn.close()

    # 知识库统计（合并后）
    conn = sqlite3.connect(DB_PATHS['knowledge'])
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pest_knowledge WHERE status = 'active'")
    total_knowledge = cursor.fetchone()[0]

    cursor.execute("SELECT crop_type, COUNT(*) FROM pest_knowledge WHERE status = 'active' GROUP BY crop_type")
    crop_dist = dict(cursor.fetchall())

    conn.close()

    print(f"\n📚 知识库:")
    print(f"   总病虫害知识: {total_knowledge} 条")
    print(f"   作物覆盖:")
    for crop, count in sorted(crop_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"      - {crop}: {count} 条")

    print("\n" + "-" * 70)
    print("✅ 所有示例数据已成功插入！包括：")
    print("   • 基础数据（7用户、8地块、16设备等）- 所有用户密码已自动哈希")
    print("   • 安全字段（failed_login_attempts、locked_until）- 违规用户已模拟锁定")
    print("   • 任务排序（sort_order）- 支持拖拽排序功能")
    print("   • 模型版本（4个YOLO版本）- 支持模型管理功能")
    print("   • 补充知识库（11条新增病虫害知识）")
    print("   • 补充评论（5条新讨论 + 回复）")
    print("   • 补充成本记录（19条成本数据）")
    print("   • 补充环境数据（7条传感器记录）")
    print("\n📱 测试账号（密码已通过 bcrypt 哈希，可正常登录）:")
    print("   🔐 管理员: admin@farm.com (密码: admin123)")
    print("   👨‍🌾 农户1: farmer1@farm.com (密码: farmer123)")
    print("   👩‍🌾 农户2: farmer2@farm.com (密码: farmer123)")
    print("   👩‍🔬 农户3: farmer4@farm.com (密码: farmer123)")
    print("   👨‍🔧 农户4: farmer5@farm.com (密码: farmer123)")
    print("   ⏳ 待审核: farmer3@farm.com (无密码，需管理员设置)")
    print("   🚫 已禁用: banned@farm.com (密码: banned123，已禁用，模拟锁定状态)")
    print("\n🚀 启动命令: python app.py")
    print("🌐 访问地址: http://localhost:8001")
    print("=" * 70)


def check_databases():
    """检查并创建数据库目录"""
    data_dir = Path('data')
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"[✓] 创建数据目录: {data_dir.absolute()}")


def main():
    """主函数：执行所有初始化"""
    print("🌱 智能农务系统 - 示例数据初始化工具（字段补全版）")
    print("=" * 70)

    # 检查路径
    check_databases()

    try:
        # 按依赖顺序初始化基础数据
        user_count, plot_count, device_count = init_email_db()
        detection_count = init_detection_db()
        comment_count = init_comments_db()
        init_chat_db()
        knowledge_count = init_knowledge_db()

        print("\n📚 正在补充知识库数据...")
        k_inserted, k_skipped = init_knowledge_supplement()
        print(f"   ✓ 新增 {k_inserted} 条病虫害知识，跳过 {k_skipped} 条重复数据")

        print("\n🤖 正在补充 AI 防治方案...")
        init_ai_solutions()

        print("\n⭐ 正在补充用户知识收藏...")
        init_knowledge_collections()

        print("\n💬 正在补充评论互动数据...")
        c_inserted = init_comments_supplement()
        print(f"   ✓ 新增 {c_inserted} 条评论及多条回复")

        print("\n💰 正在补充成本记录数据...")
        cost_inserted = init_cost_supplement()
        print(f"   ✓ 新增 {cost_inserted} 条成本记录")

        print("\n🌡️ 正在补充环境传感器数据...")
        env_inserted = init_environment_supplement()
        print(f"   ✓ 新增 {env_inserted} 条环境记录")

        print("\n📋 正在补充今日待办与动态数据...")
        task_count, activity_count = init_today_data_supplement()
        print(f"   ✓ 新增 {task_count} 条今日任务，{activity_count} 条动态")

        # 打印摘要
        print_summary()

        return 0

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

# ==================== 补充：今日待办 & 动态数据（解决空白问题） ====================

SUPPLEMENT_TODAY_TASKS = [
    {
        'user_id': 2, 'title': '水稻田追肥作业', 'type': 'fertilize',
        'plot_name': '增城01区-水稻主田', 'plot_id': 1,
        'scheduled_time': (datetime.now() + timedelta(hours=2)).isoformat(),
        'priority': 'high', 'completed': 0, 'completed_at': None,
        'notes': '每亩施用尿素15kg，注意均匀撒施', 'reminder_sent': 0,
        'sort_order': 10,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'user_id': 2, 'title': '大棚巡查-湿度检查', 'type': 'inspect',
        'plot_name': '增城03区-番茄大棚', 'plot_id': 2,
        'scheduled_time': (datetime.now() + timedelta(hours=4)).isoformat(),
        'priority': 'medium', 'completed': 0, 'completed_at': None,
        'notes': '检查通风情况，确保湿度低于80%', 'reminder_sent': 0,
        'sort_order': 11,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
    {
        'user_id': 2, 'title': '玉米地灌溉', 'type': 'irrigation',
        'plot_name': '增城02区-玉米试验田', 'plot_id': 3,
        'scheduled_time': (datetime.now() + timedelta(hours=6)).isoformat(),
        'priority': 'medium', 'completed': 0, 'completed_at': None,
        'notes': '滴灌2小时，土壤湿度目标65%', 'reminder_sent': 0,
        'sort_order': 12,
        'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()
    },
]

SUPPLEMENT_ACTIVITIES_FOR_TODAY = [
    {
        'user_id': 2, 'type': 'detect', 'type_label': 'AI识别',
        'content': '系统检测到01区水稻可能存在稻飞虱风险，建议巡查',
        'plot_name': '增城01区-水稻主田',
        'created_at': (datetime.now() - timedelta(hours=2)).isoformat()
    },
    {
        'user_id': 2, 'type': 'fertilize', 'type_label': '施肥',
        'content': '已完成02区玉米拔节期追肥，施用复合肥25kg',
        'plot_name': '增城02区-玉米试验田',
        'created_at': (datetime.now() - timedelta(hours=4)).isoformat()
    },
    {
        'user_id': 2, 'type': 'irrigation', 'type_label': '灌溉',
        'content': '番茄大棚自动滴灌启动，持续时间1.5小时',
        'plot_name': '增城03区-番茄大棚',
        'created_at': (datetime.now() - timedelta(hours=6)).isoformat()
    },
]


if __name__ == "__main__":
    exit(main())