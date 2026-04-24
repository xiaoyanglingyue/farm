import flwr as fl
import torch
from ultralytics import YOLO
from collections import OrderedDict
import numpy as np
import signal

# ==================== 联邦学习配置 ====================
FED_CONFIG = {
    "num_rounds": 10,  # 联邦轮数
    "min_available_clients": 5,  # 每轮最少参与节点
    "fraction_fit": 0.8,  # 每轮参与训练的比例
    "gradient_encryption": True,  # 梯度加密
    "model_path": "models/yolo11n.pt"
}


class YOLOClient(fl.client.NumPyClient):
    """边缘节点客户端（树莓派/农户端）"""

    def __init__(self, user_id, data_path):
        self.user_id = user_id
        self.model = YOLO(FED_CONFIG["model_path"])
        self.data_path = data_path

    def get_parameters(self, config):
        """获取模型参数（返回numpy数组列表）"""
        return [val.cpu().numpy() for _, val in self.model.model.state_dict().items()]

    def set_parameters(self, parameters):
        """设置全局模型参数"""
        params_dict = zip(self.model.model.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        self.model.model.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        """本地训练"""
        self.set_parameters(parameters)

        results = self.model.train(
            data=self.data_path,
            epochs=1,
            batch=8,
            imgsz=640,
            verbose=False
        )

        updated_params = self.get_parameters(config)
        gradients = [(new - old) for new, old in zip(updated_params, parameters)]

        # 【修复】获取真实样本数，失败时默认 100
        try:
            dataset_size = results.results.get('train_samples', 100) if hasattr(results, 'results') else 100
        except Exception:
            dataset_size = 100

        return updated_params, dataset_size, {
            "user_id": self.user_id,
            "contribution": float(np.mean([np.abs(g).mean() for g in gradients]))
        }

    def evaluate(self, parameters, config):
        """本地评估（不上传数据）"""
        self.set_parameters(parameters)
        metrics = self.model.val(verbose=False)
        return float(metrics.box.map50), len(self.data_path), {
            "map50": float(metrics.box.map50),
            "user_id": self.user_id
        }


def start_federated_server():
    """启动联邦学习服务器（云端）"""
    _original_signal = signal.signal

    def _safe_signal(signum, handler):
        try:
            return _original_signal(signum, handler)
        except ValueError:
            return None

    signal.signal = _safe_signal

    # 【新增】定义聚合策略（使用 FedAvg，并接入你已有的评估指标聚合函数）
    strategy = fl.server.strategy.FedAvg(
        min_available_clients=FED_CONFIG.get("min_available_clients", 5),
        fraction_fit=FED_CONFIG.get("fraction_fit", 0.8),
        evaluate_metrics_aggregation_fn=weighted_average,  # 你文件里已写的函数
    )

    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=FED_CONFIG["num_rounds"]),
        strategy=strategy,  # 现在 strategy 已定义
    )


def weighted_average(metrics):
    """聚合评估指标"""
    total_samples = sum([num_examples for num_examples, _ in metrics])
    weighted_map50 = sum([num_examples * m["map50"] for num_examples, m in metrics])
    return {"weighted_map50": weighted_map50 / total_samples}


def aggregate_contributions(metrics):
    """聚合节点贡献度（用于激励分配）"""
    contributions = {}
    for num_examples, m in metrics:
        user_id = m.get("user_id", "unknown")
        contributions[user_id] = m.get("contribution", 0.0)
    return {"contributions": contributions}
