import cv2
import numpy as np
import sqlite3
import time
import os
from datetime import datetime
try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    GPIO = None
    print("⚠️ 非树莓派环境，GPIO 控制已禁用")



class EdgeDeviceController:
    """边缘设备控制器（树莓派端）"""

    def __init__(self, device_id):
        self.device_id = device_id
        self.db_path = "local_cache.db"
        self.init_local_db()

        # 省电模式配置
        self.power_save_mode = False
        self.last_detection_time = time.time()
        self.idle_threshold = 1800  # 30分钟无操作进入省电

        # 脏污检测配置
        self.dirt_threshold = 120  # 灰度阈值
        self.last_clean_check = None

        if GPIO is None:
            self.gpio_available = False
        else:
            self.gpio_available = True

    def init_local_db(self):
        """初始化本地SQLite（离线缓存）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pest_name TEXT,
                confidence REAL,
                image_path TEXT,
                timestamp TIMESTAMP,
                synced INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def check_lens_dirt(self):
        """镜头脏污检测（白卡检测+灰度阈值）"""
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return False, "无法读取图像"

        # 转换为灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)

        # 边缘清晰度检测（Laplacian方差）
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 判断逻辑
        is_dirty = mean_brightness < self.dirt_threshold and laplacian_var < 100

        if is_dirty:
            self._play_voice_alert("检测到镜头脏污，请擦拭镜头")

        return is_dirty, {
            "brightness": mean_brightness,
            "sharpness": laplacian_var,
            "needs_cleaning": is_dirty
        }

    def power_management(self):
        """省电模式管理"""
        idle_time = time.time() - self.last_detection_time

        if idle_time > self.idle_threshold and not self.power_save_mode:
            self.enter_power_save()
        elif idle_time < 60 and self.power_save_mode:
            self.exit_power_save()

    def enter_power_save(self):
        """进入省电模式（降频+关闭非必要外设）"""
        self.power_save_mode = True
        # 降低CPU频率（树莓派命令）
        os.system("sudo cpufreq-set -g powersave")
        # 关闭显示器背光（如有）
        os.system("sudo echo 0 > /sys/class/backlight/rpi_backlight/brightness")
        print("🔋 已进入省电模式")

    def exit_power_save(self):
        """退出省电模式"""
        self.power_save_mode = False
        os.system("sudo cpufreq-set -g ondemand")
        os.system("sudo echo 1 > /sys/class/backlight/rpi_backlight/brightness")
        print("⚡ 已退出省电模式")

    def offline_detect(self, image, model):
        """离线检测（无网络时）"""
        results = model.predict(image, verbose=False)

        # 保存到本地数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for r in results:
            if len(r.boxes) > 0:
                cursor.execute('''
                    INSERT INTO offline_detections 
                    (pest_name, confidence, image_path, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (
                    r.names[int(r.boxes.cls[0])],
                    float(r.boxes.conf[0]),
                    "local_cache.jpg",
                    datetime.now()
                ))

        conn.commit()
        conn.close()

        # 尝试同步（如有网络）
        self.sync_offline_data()

        return results

    def sync_offline_data(self):
        """断网续存：有网络时自动上传"""
        # 检查网络
        if os.system("ping -c 1 baidu.com > /dev/null 2>&1") != 0:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM offline_detections WHERE synced=0")
        records = cursor.fetchall()

        # 批量上传（调用云端API）
        for record in records:
            # upload_to_cloud(record)
            cursor.execute("UPDATE offline_detections SET synced=1 WHERE id=?", (record[0],))

        conn.commit()
        conn.close()
        return True

    def _play_voice_alert(self, message):
        """本地语音播报（树莓派）"""
        os.system(f"espeak -vzh '{message}'")  # 需要安装espeak
