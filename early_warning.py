import torch
import torch.nn as nn
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier


class CropFormer(nn.Module):
    """时空Transformer预警模型（开题报告提到的CropFormer）"""

    def __init__(self, d_model=256, nhead=8, num_layers=6):
        super().__init__()
        # 图像特征编码（YOLO输出）
        self.image_encoder = nn.Linear(1024, d_model)  # YOLO特征维度->d_model

        # 气象特征编码
        self.weather_encoder = nn.Linear(5, d_model)  # [温度,湿度,降雨,风速,光照]

        # 时序Transformer
        self.temporal_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead),
            num_layers=num_layers
        )

        # 风险预测头
        self.risk_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 3)  # [初发,盛发,爆发]概率
        )

    def forward(self, image_feats, weather_seq, temporal_mask=None):
        """
        Args:
            image_feats: [batch, 1024] 当前图像特征
            weather_seq: [batch, seq_len, 5] 历史气象序列
        """
        # 编码
        img_emb = self.image_encoder(image_feats)  # [batch, d_model]
        weather_emb = self.weather_encoder(weather_seq)  # [batch, seq_len, d_model]

        # 融合：图像特征作为CLS token
        cls_token = img_emb.unsqueeze(1)  # [batch, 1, d_model]
        sequence = torch.cat([cls_token, weather_emb], dim=1)  # [batch, seq_len+1, d_model]

        # 时序编码
        output = self.temporal_encoder(sequence.permute(1, 0, 2))  # [seq_len+1, batch, d_model]
        cls_output = output[0]  # [batch, d_model]

        # 预测
        risk_probs = torch.softmax(self.risk_head(cls_output), dim=-1)
        return risk_probs


class EarlyWarningSystem:
    """早期预警系统（5-7天提前量）"""

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = CropFormer().to(self.device)
        self.model.eval()

        # 传统机器学习备用（数据量小时使用）
        self.rf_model = RandomForestClassifier(n_estimators=100)

    def predict_outbreak(self, detection_history, weather_forecast, crop_type="rice"):
        """
        预测未来5-7天爆发概率

        Args:
            detection_history: 最近7天的检测记录列表
            weather_forecast: 未来7天天气预报
            crop_type: 作物类型
        """
        # 1. 提取时序特征
        seq_len = 7
        features = np.zeros((seq_len, 5))  # [温度,湿度,降雨,虫害密度,作物生长阶段]

        for i, day_data in enumerate(detection_history[-seq_len:]):
            features[i] = [
                day_data.get('temp', 25),
                day_data.get('humidity', 60),
                day_data.get('rain', 0),
                day_data.get('pest_count', 0) / 100,  # 归一化
                day_data.get('growth_stage', 0.5)
            ]

        # 2. 当前图像特征（最后一次检测的YOLO特征）
        last_image_feat = torch.randn(1024).to(self.device)  # 实际应从YOLO中间层提取

        # 3. 预测
        with torch.no_grad():
            weather_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            probs = self.model(last_image_feat.unsqueeze(0), weather_tensor)

        risk_levels = ['low', 'medium', 'high']
        max_idx = torch.argmax(probs, dim=1).item()

        return {
            "risk_level": risk_levels[max_idx],
            "probability": float(probs[0][max_idx]),
            "forecast_days": 7,
            "trigger_factors": self._explain_risk(features, weather_forecast),
            "advice": self._generate_advice(risk_levels[max_idx], crop_type)
        }

    def _explain_risk(self, features, forecast):
        """可解释性：分析触发预警的关键因素"""
        factors = []
        avg_temp = np.mean(features[:, 0])
        avg_humidity = np.mean(features[:, 1])

        if avg_temp > 28 and avg_humidity > 80:
            factors.append("高温高湿环境（适宜病虫害繁殖）")
        if np.sum(features[:, 2]) > 50:  # 累计降雨
            factors.append("连续降雨（利于真菌传播）")
        if features[-1, 3] > features[0, 3] * 2:  # 虫害密度翻倍
            factors.append("虫害密度快速增长（指数级扩散风险）")

        return factors

    def _generate_advice(self, risk_level, crop_type):
        """生成防治建议"""
        advice_map = {
            'low': "当前风险较低，保持常规监测频率（每3天一次巡查）",
            'medium': "风险上升期，建议：1)增加监测频率至每日一次 2)准备防治药剂 3)关注气象变化",
            'high': "⚠️ 高风险预警！建议立即：1)全面喷药防治 2)开启所有监测设备 3)通知周边农户联防"
        }
        return advice_map.get(risk_level, "请保持监测")
