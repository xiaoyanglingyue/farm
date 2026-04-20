import folium
from folium.plugins import HeatMap, TimestampedGeoJson
import pandas as pd
from datetime import datetime, timedelta


class RiskMapGenerator:
    """风险地图生成器"""

    def __init__(self, center_lat=23.3242, center_lng=113.8291):
        self.center = [center_lat, center_lng]

    def generate_heatmap(self, detection_data, forecast_data=None):
        """
        生成风险热力图（支持时间轴播放）

        Args:
            detection_data: 检测记录列表（含lat/lng/confidence/time）
            forecast_data: 预测数据（未来风险分布）
        """
        m = folium.Map(location=self.center, zoom_start=14, tiles='Satellite')

        # 1. 历史检测热力图
        if detection_data:
            heat_data = [[d['lat'], d['lng'], d['confidence']] for d in detection_data]
            HeatMap(heat_data, radius=15, blur=10).add_to(m)

        # 2. 预测风险区域（红色多边形）
        if forecast_data:
            for area in forecast_data:
                folium.Circle(
                    location=[area['lat'], area['lng']],
                    radius=area.get('radius', 100),
                    popup=f"风险等级: {area['risk_level']}<br>概率: {area['probability']:.1%}",
                    color='red' if area['risk_level'] == 'high' else 'orange',
                    fill=True,
                    fill_opacity=0.3
                ).add_to(m)

        # 3. 添加设备标记
        for device in get_all_devices():
            icon_color = 'green' if device['status'] == 'online' else 'red'
            folium.Marker(
                [device['lat'], device['lng']],
                popup=f"{device['name']}<br>状态: {device['status']}",
                icon=folium.Icon(color=icon_color, icon='camera')
            ).add_to(m)

        return m._repr_html_()

    def generate_time_series_chart(self, user_id, days=30):
        """生成时序统计图表（用于前端ECharts）"""
        records = get_detection_history(user_email=None, limit=1000)  # 管理员看全部

        # 按日期聚合
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['created_at']).dt.date
        daily_stats = df.groupby('date').agg({
            'id': 'count',
            'confidence': 'mean',
            'risk_level': lambda x: (x == 'high').sum()
        }).reset_index()

        return {
            "dates": daily_stats['date'].tolist(),
            "counts": daily_stats['id'].tolist(),
            "avg_confidence": [round(c, 1) for c in daily_stats['confidence'].tolist()],
            "high_risk_counts": daily_stats['risk_level'].tolist()
        }


# ==================== API路由（添加到app.py） ====================
@app.get("/api/visualization/dashboard")
async def get_dashboard_data(request: Request, user=Depends(get_current_user_dep)):
    """获取首页数据看板"""
    viz = RiskMapGenerator()

    # 统计数据
    stats = {
        "detection_trend": viz.generate_time_series_chart(user['id']),
        "pest_distribution": get_pest_distribution(user['id']),
        "farm_health_score": calculate_farm_health(user['id']),
        "upcoming_tasks": get_farm_tasks(user['id'], limit=5)
    }

    return {"code": 200, "data": stats}


def calculate_farm_health(user_id):
    """计算农场健康度评分（0-100）"""
    # 基于近期检测频率、病虫害严重程度、防治及时性
    recent_detections = get_detection_history(user_email=None, limit=30)

    if not recent_detections:
        return 100  # 无数据默认健康

    # 计算指标
    high_risk_ratio = sum(1 for r in recent_detections if r['risk_level'] == 'high') / len(recent_detections)
    detection_frequency = len(recent_detections) / 30  # 每日检测次数

    # 健康度 = 100 - 高风险比例*50 - 检测频率不足扣分
    health = 100 - (high_risk_ratio * 50) - max(0, (1 - detection_frequency) * 10)
    return max(0, min(100, int(health)))