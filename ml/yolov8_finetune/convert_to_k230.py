"""
YOLOv8-Pose 模型转换脚本：.pt → .onnx → .kmodel
将训练好的 PyTorch 模型转换为 K230 KPU 可运行的 .kmodel 格式

用法:
    python convert_to_k230.py --input runs/pose/train/weights/best.pt --output yolov8n-pose-custom.kmodel

要求:
    pip install onnx onnxsim nncase
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """检查必要的依赖"""
    deps = ["onnx", "onnxsim"]
    missing = []
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)

    # nncase 是 K230 专用工具
    try:
        subprocess.run(["nncase", "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        missing.append("nncase (K230 SDK 工具链)")

    if missing:
        print(f"[Error] 缺少依赖: {', '.join(missing)}")
        print("请安装:")
        print("  pip install onnx onnxsim")
        print("  nncase 请从 K230 SDK 安装: https://github.com/kendryte/nncase")
        return False
    return True


def pt_to_onnx(input_pt: Path, output_onnx: Path, img_size: int = 320):
    """PyTorch → ONNX"""
    print(f"\n[Step 1/3] 导出 ONNX: {input_pt} → {output_onnx}")

    from ultralytics import YOLO
    model = YOLO(str(input_pt))
    model.export(
        format="onnx",
        imgsz=img_size,
        opset=12,
        simplify=True,
    )

    # YOLO 导出的 ONNX 文件名
    exported = input_pt.with_suffix(".onnx")
    if exported.exists() and exported != output_onnx:
        exported.rename(output_onnx)

    print(f"  ONNX 已导出: {output_onnx} "
          f"({output_onnx.stat().st_size / 1024 / 1024:.1f} MB)")


def simplify_onnx(input_onnx: Path, output_onnx: Path):
    """简化 ONNX 模型"""
    print(f"\n[Step 2/3] 简化 ONNX: {input_onnx} → {output_onnx}")

    import onnx
    from onnxsim import simplify

    model = onnx.load(str(input_onnx))
    model_simp, check = simplify(model)

    if check:
        onnx.save(model_simp, str(output_onnx))
        print(f"  简化成功: {output_onnx} "
              f"({output_onnx.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print("  简化失败，使用原始 ONNX")
        input_onnx.rename(output_onnx)


def onnx_to_kmodel(input_onnx: Path, output_kmodel: Path):
    """ONNX → KModel（使用 K230 nncase 工具链）"""
    print(f"\n[Step 3/3] 转换为 KModel: {input_onnx} → {output_kmodel}")

    # nncase 命令行转换
    cmd = [
        "nncase",
        "compile",
        "--model", str(input_onnx),
        "--output", str(output_kmodel),
        "--target", "k230",
        "--input-shape", "1,3,320,320",
        "--quantize", "int8",
        "--dataset", "./calibration",  # 量化校准数据集
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  KModel 已生成: {output_kmodel} "
              f"({output_kmodel.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"  nncase 转换失败:")
        print(f"  stderr: {result.stderr}")
        print("\n  手动转换步骤:")
        print(f"  1. 将 {input_onnx} 拷贝到 K230 SDK 环境")
        print(f"  2. 使用 nncase 工具链编译为 .kmodel")
        print(f"  3. 将生成的 .kmodel 放到 edge/models/ 目录")


def main():
    parser = argparse.ArgumentParser(description="YOLOv8-Pose → K230 KModel 转换")
    parser.add_argument("--input", "-i", required=True, help="训练好的 .pt 模型路径")
    parser.add_argument("--output", "-o", default="yolov8n-pose-custom.kmodel")
    parser.add_argument("--img-size", type=int, default=320)
    parser.add_argument("--skip-simplify", action="store_true", help="跳过 ONNX 简化")
    parser.add_argument("--skip-nncase", action="store_true", help="跳过 nncase 转换（仅导出 ONNX）")
    args = parser.parse_args()

    input_pt = Path(args.input)
    if not input_pt.exists():
        print(f"[Error] 模型文件不存在: {input_pt}")
        sys.exit(1)

    check_dependencies()

    output_dir = Path(args.output).parent or Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_onnx = output_dir / f"{input_pt.stem}.onnx"
    output_simp = output_dir / f"{input_pt.stem}_sim.onnx"
    output_kmodel = Path(args.output)

    # Step 1: pt → onnx
    pt_to_onnx(input_pt, output_onnx, args.img_size)

    # Step 2: simplify onnx
    if not args.skip_simplify:
        simplify_onnx(output_onnx, output_simp)
    else:
        output_simp = output_onnx

    # Step 3: onnx → kmodel
    if not args.skip_nncase:
        onnx_to_kmodel(output_simp, output_kmodel)
    else:
        print("\n[Skip] 跳过 nncase 转换，ONNX 模型已就绪")
        print(f"  可在 K230 SDK 环境中手动编译: {output_simp}")

    print("\n转换流程完成！")
    print(f"  最终模型: {output_kmodel if not args.skip_nncase else output_simp}")
    print(f"  部署: 将模型文件拷贝到 edge/models/ 目录")


if __name__ == "__main__":
    main()
