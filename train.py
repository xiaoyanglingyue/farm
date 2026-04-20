import os
import shutil
import random
from pathlib import Path
from collections import defaultdict

# ==================== 配置区域 ====================
DATASET_PATH = "./dataset"  # 你的数据集根目录
TRAIN_RATIO = 0.8  # 训练集比例
RANDOM_SEED = 42  # 随机种子，保证可复现

# YOLOv11 模型选择（n/s/m/l/x，n最快，x最准）
MODEL_TYPE = "yolo11s"  # 推荐 s 或 m，平衡速度和精度

# 训练参数
EPOCHS = 100
BATCH_SIZE = 16
IMG_SIZE = 640


# ==================================================

def setup_dataset():
    """
    重组数据集结构：
    从：images/classID_XX/xxx.jpg  →  到：images/train/xxx.jpg, images/val/xxx.jpg
    """
    print("📁 正在准备数据集...")

    # 创建标准 YOLO 目录
    for split in ['train', 'val']:
        (Path(DATASET_PATH) / "images" / split).mkdir(parents=True, exist_ok=True)
        (Path(DATASET_PATH) / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 收集所有类别的文件
    all_images = []
    all_labels = []

    for class_id in range(10):  # 0-9
        class_folder = f"classID_{class_id:02d}"
        img_dir = Path(DATASET_PATH) / "images" / class_folder
        lbl_dir = Path(DATASET_PATH) / "labels" / class_folder

        if not img_dir.exists():
            print(f"⚠️  跳过不存在的文件夹: {img_dir}")
            continue

        # 获取该类别所有图片
        for img_file in img_dir.glob("*"):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                # 对应的标签文件
                lbl_file = lbl_dir / (img_file.stem + ".txt")
                if lbl_file.exists():
                    all_images.append(img_file)
                    all_labels.append(lbl_file)
                else:
                    print(f"⚠️  缺少标签: {img_file.name}")

    print(f"✅ 共找到 {len(all_images)} 个有效样本")

    # 随机划分
    random.seed(RANDOM_SEED)
    indices = list(range(len(all_images)))
    random.shuffle(indices)

    split_idx = int(len(indices) * TRAIN_RATIO)
    train_idx = indices[:split_idx]
    val_idx = indices[split_idx:]

    print(f"📊 训练集: {len(train_idx)} | 验证集: {len(val_idx)}")

    # 复制文件到对应目录
    def copy_files(indices, split):
        for idx in indices:
            img_src = all_images[idx]
            lbl_src = all_labels[idx]

            # 新文件名（避免重名，添加类别前缀）
            new_name = f"class{img_src.parent.name[-2:]}_{img_src.name}"

            img_dst = Path(DATASET_PATH) / "images" / split / new_name
            lbl_dst = Path(DATASET_PATH) / "labels" / split / (Path(new_name).stem + ".txt")

            shutil.copy2(img_src, img_dst)
            shutil.copy2(lbl_src, lbl_dst)

    copy_files(train_idx, "train")
    copy_files(val_idx, "val")

    print("✅ 数据集准备完成！")

    # 统计各类别分布
    stats = defaultdict(lambda: {'train': 0, 'val': 0})
    for idx in train_idx:
        class_id = all_images[idx].parent.name[-2:]
        stats[class_id]['train'] += 1
    for idx in val_idx:
        class_id = all_images[idx].parent.name[-2:]
        stats[class_id]['val'] += 1

    print("\n📈 各类别分布：")
    for class_id in sorted(stats.keys()):
        s = stats[class_id]
        print(f"  类别{class_id}: 训练{s['train']:>3} | 验证{s['val']:>3}")


def create_yaml():
    """生成 data.yaml 配置文件"""
    yaml_content = """# 水稻害虫检测数据集 - YOLOv11
        path: {path}
        train: images/train
        val: images/val
        
        nc: 10
        names:
          0: rice_leaf_roller        # 稻纵卷叶螟
          1: rice_leaf_caterpillar   # 稻螟蛉
          2: paddy_stem_maggot       # 稻茎虫
          3: asiatic_rice_borer      # 二化螟
          4: yellow_rice_borer       # 三化螟
          5: rice_gall_midge         # 稻瘿蚊
          6: rice_water_weevil       # 稻水象甲
          7: brown_plant_hopper      # 褐飞虱
          8: small_brown_plant_hopper # 灰飞虱
          9: rice_leaf_hopper        # 稻叶蝉
        """.format(path=os.path.abspath(DATASET_PATH))

    yaml_path = Path(DATASET_PATH) / "data.yaml"
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    print(f"✅ YAML 配置已保存: {yaml_path}")


def train_model():
    """训练 YOLOv11 模型"""
    print("\n🚀 开始训练 YOLOv11...")

    # 导入 ultralytics（如果没有安装会提示）
    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ 请先安装 ultralytics: pip install ultralytics")
        return

    # 加载预训练模型
    model = YOLO(f"{MODEL_TYPE}.pt")  # 自动下载预训练权重

    # 训练配置
    yaml_path = Path(DATASET_PATH) / "data.yaml"

    results = model.train(
        data=str(yaml_path),
        epochs=EPOCHS,
        batch=BATCH_SIZE,
        imgsz=IMG_SIZE,
        device=0,  # 使用 GPU 0，如果是 CPU 改为 device='cpu'
        workers=8,
        patience=20,  # 早停耐心值
        save=True,
        project="detect/rice_pest_detection",
        name=f"{MODEL_TYPE}_exp",
        exist_ok=True,
        pretrained=True,
        optimizer='AdamW',  # 或 'SGD'
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
    )

    print("\n✅ 训练完成！")

    # 输出 best.pt 路径
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    last_pt = Path(results.save_dir) / "weights" / "last.pt"

    print(f"\n🏆 最佳模型: {best_pt}")
    print(f"📝 最新模型: {last_pt}")

    # 验证模型
    print("\n🔍 正在验证最佳模型...")
    metrics = model.val()
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")

    return best_pt


if __name__ == "__main__":
    # 检查是否需要准备数据
    train_dir = Path(DATASET_PATH) / "images" / "train"
    if not train_dir.exists() or len(list(train_dir.glob("*"))) == 0:
        setup_dataset()
        create_yaml()
    else:
        print("✅ 检测到已存在 train/val 目录，跳过数据准备")

    # 开始训练
    best_model_path = train_model()

    print("\n" + "=" * 50)
    print("🎉 全部完成！")
    print(f"模型保存在: rice_pest_detection/{MODEL_TYPE}_exp/weights/")
    print("=" * 50)