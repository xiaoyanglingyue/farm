import folium
from folium.plugins import HeatMap, TimestampedGeoJson
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.neighbors import KernelDensity

from database import get_detection_history, get_all_devices, get_detection_db_connection


class RiskMapGenerator:
    """风险地图生成器（增强版：支持蔓延分析）"""

    def __init__(self, center_lat=23.3242, center_lng=113.8291):
        self.center = [center_lat, center_lng]
        # 病虫害扩散参数（不同害虫有不同扩散系数，单位：米/天）
        self.spread_coefficients = {
            '稻飞虱': 150,
            '褐飞虱': 120,
            '灰飞虱': 100,
            '稻纵卷叶螟': 80,
            '二化螟': 60,
            '稻瘟病': 200,  # 病害传播更快
            '纹枯病': 180,
            'default': 100
        }

    def generate_heatmap(self, detection_data, forecast_data=None):
        """
        生成风险热力图（支持时间轴播放）
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

    def generate_time_series_chart(self, user_email=None, days=30):
        """生成时序统计图表（用于前端ECharts）"""
        try:
            with get_detection_db_connection() as conn:
                cursor = conn.cursor()
                thirty_days_ago = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

                if user_email:
                    cursor.execute('''
                        SELECT created_at, confidence, risk_level 
                        FROM detection_records 
                        WHERE user_email = ? AND DATE(created_at) >= ?
                        ORDER BY created_at
                    ''', (user_email, thirty_days_ago))
                else:
                    cursor.execute('''
                        SELECT created_at, confidence, risk_level 
                        FROM detection_records 
                        WHERE DATE(created_at) >= ?
                        ORDER BY created_at
                    ''', (thirty_days_ago,))

                records = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"获取时序数据失败: {e}")
            records = []

        if not records:
            return {
                "dates": [],
                "counts": [],
                "avg_confidence": [],
                "high_risk_counts": []
            }

        # 按日期聚合
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['created_at']).dt.date
        daily_stats = df.groupby('date').agg({
            'created_at': 'count',
            'confidence': 'mean',
            'risk_level': lambda x: (x == 'high').sum()
        }).reset_index()
        daily_stats.columns = ['date', 'count', 'avg_confidence', 'high_risk_count']

        return {
            "dates": [str(d) for d in daily_stats['date'].tolist()],
            "counts": daily_stats['count'].tolist(),
            "avg_confidence": [round(c, 1) for c in daily_stats['avg_confidence'].tolist()],
            "high_risk_counts": daily_stats['high_risk_count'].tolist()
        }

    def get_timeline_heatmap_data(self, user_email=None, days=7):
        """
        【新增】获取时间轴热力图数据（支持播放动画）
        返回每天的检测点数据，带时间衰减权重
        """
        try:
            with get_detection_db_connection() as conn:
                cursor = conn.cursor()
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

                if user_email:
                    cursor.execute('''
                        SELECT id, pest_name, confidence, location_lat, location_lng, 
                               risk_level, created_at
                        FROM detection_records 
                        WHERE user_email = ? AND DATE(created_at) >= ?
                        ORDER BY created_at
                    ''', (user_email, start_date))
                else:
                    cursor.execute('''
                        SELECT id, pest_name, confidence, location_lat, location_lng, 
                               risk_level, created_at
                        FROM detection_records 
                        WHERE DATE(created_at) >= ?
                        ORDER BY created_at
                    ''', (start_date,))

                records = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"获取时间轴数据失败: {e}")
            records = []

        # 按日期分组
        timeline_data = {}
        for record in records:
            date_key = record['created_at'][:10] if isinstance(record['created_at'], str) else record[
                'created_at'].strftime('%Y-%m-%d')
            if date_key not in timeline_data:
                timeline_data[date_key] = []

            # 计算时间衰减权重（越近权重越高）
            record_date = datetime.strptime(date_key, '%Y-%m-%d')
            days_ago = (datetime.now() - record_date).days
            time_weight = max(0.3, 1.0 - (days_ago / (days + 1)) * 0.7)  # 衰减系数

            timeline_data[date_key].append({
                'lat': record['location_lat'],
                'lng': record['location_lng'],
                'count': record['confidence'] * time_weight,  # 应用时间权重
                'confidence': record['confidence'],
                'pest_name': record['pest_name'],
                'risk_level': record['risk_level']
            })

        # 转换为数组格式，按日期排序
        result = []
        for date in sorted(timeline_data.keys()):
            result.append({
                'date': date,
                'points': timeline_data[date],
                'count': len(timeline_data[date])
            })

        return result

    def predict_spread(self, user_email=None, forecast_days=3):
        """
        【修复】蔓延预测算法：严格过滤无位置数据，避免空返回
        """
        try:
            # 获取最近7天的检测数据
            history = get_detection_history(user_email=user_email, limit=200)
            if not history:
                print("[预测] 无检测历史记录")
                return []

            # 【关键修复】只保留有位置坐标的记录
            valid_records = []
            for record in history:
                lat = record.get('location_lat')
                lng = record.get('location_lng')
                if lat and lng:
                    valid_records.append(record)

            if len(valid_records) < 15:
                print(f"[预测] 带位置记录不足: {len(valid_records)}条，需要至少15条才生成可靠预测")
                return []

            # 按病虫害类型分组
            pest_groups = {}
            for record in valid_records:
                pest = record.get('pest_name', 'unknown')
                if pest not in pest_groups:
                    pest_groups[pest] = []
                pest_groups[pest].append({
                    'lat': record.get('location_lat'),
                    'lng': record.get('location_lng'),
                    'confidence': record.get('confidence', 50),
                    'date': record.get('created_at', '')[:10] if isinstance(record.get('created_at'), str) else ''
                })

            predictions = []
            today = datetime.now()

            for pest_name, points in pest_groups.items():
                if len(points) < 2:
                    continue

                spread_rate = self.spread_coefficients.get(pest_name, self.spread_coefficients['default'])
                avg_lat = sum(p['lat'] for p in points) / len(points)
                avg_lng = sum(p['lng'] for p in points) / len(points)

                # 计算最近趋势（最近3天）
                recent_points = sorted(points, key=lambda x: x['date'])[-3:]
                lat_trend = recent_points[-1]['lat'] - recent_points[0]['lat'] if len(recent_points) >= 2 else 0
                lng_trend = recent_points[-1]['lng'] - recent_points[0]['lng'] if len(recent_points) >= 2 else 0

                avg_conf = sum(p['confidence'] for p in points) / len(points)

                day_count = max(1, len(recent_points) - 1)
                lat_velocity = lat_trend / day_count if day_count > 0 else 0
                lng_velocity = lng_trend / day_count if day_count > 0 else 0

                for day in range(1, forecast_days + 1):
                    # 扩散半径随时间增长（平方根定律）
                    radius = int(spread_rate * np.sqrt(day))

                    # 【优化】确定性趋势外推：基于历史速度推算，结果稳定可复现
                    pred_lat = avg_lat + (lat_velocity * day * 0.5)
                    pred_lng = avg_lng + (lng_velocity * day * 0.5)

                    # 【优化】概率随时间自然衰减（越远不确定性越大），不再单调递增
                    time_decay = 1.0 / (1 + 0.15 * day)  # 每天约衰减13%
                    probability = min(0.95, (avg_conf / 100) * time_decay)

                    predictions.append({
                        'date': (today + timedelta(days=day)).strftime('%Y-%m-%d'),
                        'pest_name': pest_name,
                        'lat': round(pred_lat, 6),
                        'lng': round(pred_lng, 6),
                        'radius': int(radius),
                        'probability': round(probability, 2),
                        'risk_level': 'high' if probability > 0.7 else 'medium' if probability > 0.4 else 'low',
                        'source_points': len(points)
                    })

            # 按日期正序、概率倒序排列
            return sorted(predictions, key=lambda x: (x['date'], -x['probability']))
        except Exception as e:
            print(f"蔓延预测失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def calculate_spread_stats(self, user_email=None, days=7):
        """
        【修复】计算蔓延统计指标：始终返回完整结构，前端不再"点了没用"
        """
        try:
            timeline = self.get_timeline_heatmap_data(user_email, days)

            # 【修复】即使只有1天数据也返回结构，不再返回空导致前端无响应
            if len(timeline) < 1:
                return {
                    'spread_speed': 0,
                    'spread_direction': '无数据',
                    'affected_area': 0,
                    'growth_rate': 0,
                    'daily_trend': [],
                    'data_sufficient': False,
                    'message': '暂无历史检测数据，请至少完成1次带位置的检测'
                }

            # 计算每日影响面积
            daily_areas = []
            for day_data in timeline:
                points = [(p['lat'], p['lng']) for p in day_data['points']]
                if len(points) >= 3:
                    lats = [p[0] for p in points]
                    lngs = [p[1] for p in points]
                    # 使用最小外接矩形估算面积（平方公里）
                    area = (max(lats) - min(lats)) * (max(lngs) - min(lngs)) * 111 * 111
                    daily_areas.append(max(0, area))
                else:
                    daily_areas.append(0)

            # 计算蔓延速度（最近两天的面积变化）
            if len(daily_areas) >= 2 and daily_areas[-2] > 0:
                recent_growth = daily_areas[-1] - daily_areas[-2]
                growth_rate = (daily_areas[-1] / max(daily_areas[-2], 0.1) - 1) * 100
            else:
                recent_growth = 0
                growth_rate = 0

            # 计算蔓延方向
            direction = '稳定'
            if len(timeline) >= 2:
                recent = timeline[-1]['points']
                prev = timeline[-2]['points']
                if recent and prev:
                    recent_center = (
                        sum(p['lat'] for p in recent) / len(recent),
                        sum(p['lng'] for p in recent) / len(recent)
                    )
                    prev_center = (
                        sum(p['lat'] for p in prev) / len(prev),
                        sum(p['lng'] for p in prev) / len(prev)
                    )
                    lat_diff = recent_center[0] - prev_center[0]
                    lng_diff = recent_center[1] - prev_center[1]
                    directions = []
                    if lat_diff > 0.0001:
                        directions.append('北')
                    elif lat_diff < -0.0001:
                        directions.append('南')
                    if lng_diff > 0.0001:
                        directions.append('东')
                    elif lng_diff < -0.0001:
                        directions.append('西')
                    direction = ''.join(directions) if directions else '稳定'

            return {
                'spread_speed': round(abs(recent_growth), 2),
                'spread_direction': direction,
                'affected_area': round(daily_areas[-1] if daily_areas else 0, 2),
                'growth_rate': round(growth_rate, 1),
                'daily_trend': [
                    {'date': t['date'], 'area': round(a, 2)}
                    for t, a in zip(timeline, daily_areas)
                ],
                'data_sufficient': len(timeline) >= 2,
                'message': '数据正常' if len(timeline) >= 2 else '已采集1天数据，继续记录可生成趋势'
            }
        except Exception as e:
            print(f"计算蔓延统计失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'spread_speed': 0,
                'spread_direction': '计算失败',
                'affected_area': 0,
                'growth_rate': 0,
                'daily_trend': [],
                'data_sufficient': False,
                'message': f'计算异常: {str(e)}'
            }


def calculate_farm_health(user_email):
    """计算农场健康度评分（0-100）"""
    try:
        with get_detection_db_connection() as conn:
            cursor = conn.cursor()
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT risk_level, confidence FROM detection_records 
                WHERE user_email = ? AND DATE(created_at) >= ?
            ''', (user_email, thirty_days_ago))

            recent_detections = [dict(row) for row in cursor.fetchall()]
    except Exception:
        recent_detections = []

    if not recent_detections:
        return 100  # 无数据默认健康

    # 计算指标
    high_risk_ratio = sum(1 for r in recent_detections if r.get('risk_level') == 'high') / len(recent_detections)
    detection_frequency = len(recent_detections) / 30.0  # 每日检测次数

    # 健康度 = 100 - 高风险比例*50 - 检测频率不足扣分
    health = 100 - (high_risk_ratio * 50) - max(0, (1 - detection_frequency) * 10)
    return max(0, min(100, int(health)))