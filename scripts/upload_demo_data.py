"""
批量上传模拟数据到后端 API
配合 generate_demo_data.py 生成的 JSON 文件使用

用法:
    python upload_demo_data.py demo_data.json
    python upload_demo_data.py demo_data.json --api-url http://your-server:8000/api/v1/data/upload
"""

import json
import sys
import time
import argparse
from urllib.request import Request, urlopen
from urllib.error import URLError
import urllib.parse


def upload_records(records, api_url, batch_delay=0.01):
    """
    批量上传坐姿记录到后端

    Args:
        records: 记录列表
        api_url: 上传接口地址
        batch_delay: 每条之间的间隔（秒），模拟实时上传
    """
    success = 0
    failed = 0

    for i, record in enumerate(records):
        payload = {
            "user_id": record.get("user_id", 1),
            "head_angle": record["head_angle"],
            "shoulder_diff": record["shoulder_diff"],
            "hunchback_score": record["hunchback_score"],
            "body_tilt": record["body_tilt"],
            "round_shoulder": record["round_shoulder"],
            "posture_label": record["posture_label"],
            "confidence": record["confidence"],
            "timestamp": record.get("timestamp"),
        }

        data = json.dumps(payload).encode("utf-8")
        req = Request(api_url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    success += 1
                else:
                    failed += 1
        except URLError as e:
            failed += 1
            print(f"  Upload error at record {i+1}: {e}")

        # 进度输出
        if (i + 1) % 200 == 0:
            print(f"  Progress: {i+1}/{len(records)} (success={success}, failed={failed})")

        if batch_delay > 0:
            time.sleep(batch_delay)

    return success, failed


def main():
    parser = argparse.ArgumentParser(description="上传模拟数据到后端 API")
    parser.add_argument("json_file", help="模拟数据 JSON 文件路径")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/api/v1/data/upload",
        help="后端上传接口地址",
    )
    parser.add_argument("--delay", type=float, default=0.01, help="每条上传间隔（秒）")
    parser.add_argument("--limit", type=int, default=0, help="限制上传条数（0=全部）")
    args = parser.parse_args()

    print(f"Loading {args.json_file} ...")
    with open(args.json_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if args.limit > 0:
        records = records[: args.limit]

    print(f"Uploading {len(records)} records to {args.api_url} ...")
    start = time.time()
    success, failed = upload_records(records, args.api_url, args.delay)
    elapsed = time.time() - start

    print(f"\nDone in {elapsed:.1f}s: {success} success, {failed} failed")


if __name__ == "__main__":
    main()
