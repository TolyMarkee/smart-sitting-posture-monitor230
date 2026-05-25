"""
YOLOv8-Pose 微调训练脚本
支持：本地 GPU（NVIDIA RTX 5080）或 矩池云/恒源云（AICube）

用法:
    # 本地训练
    python train.py --epochs 100 --batch 16

    # 继续训练
    python train.py --resume runs/pose/train/weights/last.pt

    # AICube 云平台训练
    python train.py --epochs 100 --batch 32 --device 0
"""

import argparse
import yaml
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="YOLOv8-Pose 坐姿关键点训练")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--device", type=str, default="0", help="GPU ID，CPU 用 'cpu'")
    parser.add_argument("--resume", type=str, default=None, help="从 checkpoint 继续训练")
    parser.add_argument("--output", type=str, default="runs/pose/train", help="输出目录")
    args = parser.parse_args()

    # 加载配置
    config = {}
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        print(f"[Config] 已加载: {config_path}")

    train_cfg = config.get("train", {})
    aug_cfg = config.get("augmentation", {})
    model_cfg = config.get("model", {})

    model_name = model_cfg.get("name", "yolov8n-pose")
    pretrained = model_cfg.get("pretrained", "yolov8n-pose.pt")
    img_size = train_cfg.get("img_size", 320)

    print(f"[Model] {model_name}, pretrained={pretrained}, img_size={img_size}")

    # 加载模型
    if args.resume:
        print(f"[Resume] 从 {args.resume} 继续训练")
        model = YOLO(args.resume)
    else:
        model = YOLO(pretrained)

    # 开始训练
    results = model.train(
        data=config.get("dataset", {}).get("yaml", "coco8-pose.yaml"),
        epochs=args.epochs or train_cfg.get("epochs", 100),
        batch=args.batch or train_cfg.get("batch_size", 16),
        imgsz=img_size,
        lr0=args.lr or train_cfg.get("learning_rate", 0.001),
        device=args.device,
        project=args.output,
        name=model_name,
        # 数据增强
        hsv_h=aug_cfg.get("hsv_h", 0.015),
        hsv_s=aug_cfg.get("hsv_s", 0.7),
        hsv_v=aug_cfg.get("hsv_v", 0.4),
        degrees=aug_cfg.get("degrees", 10.0),
        translate=aug_cfg.get("translate", 0.1),
        scale=aug_cfg.get("scale", 0.5),
        shear=aug_cfg.get("shear", 2.0),
        fliplr=aug_cfg.get("flip_lr", 0.5),
        mosaic=aug_cfg.get("mosaic", 1.0),
        # 优化器
        warmup_epochs=train_cfg.get("warmup_epochs", 3),
        weight_decay=train_cfg.get("weight_decay", 0.0005),
        momentum=train_cfg.get("momentum", 0.937),
    )

    # 导出最佳模型
    best_pt = Path(args.output) / model_name / "weights" / "best.pt"
    if best_pt.exists():
        print(f"\n[Best] 最佳模型保存至: {best_pt}")
        print(f"[Metrics] mAP@50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")

    print("\n训练完成！使用 convert_to_k230.py 将模型转为 .kmodel 部署到 K230")


if __name__ == "__main__":
    main()
