"""测试数据预处理模块"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "app" / "core"))

from data_preprocess import (
    records_to_dataframe,
    remove_outliers,
    fill_missing,
    aggregate_daily,
    METRIC_COLUMNS,
)


class MockRecord:
    def __init__(self, head_angle, shoulder_diff, hunchback_score, body_tilt, round_shoulder, created_at):
        self.head_angle = head_angle
        self.shoulder_diff = shoulder_diff
        self.hunchback_score = hunchback_score
        self.body_tilt = body_tilt
        self.round_shoulder = round_shoulder
        self.created_at = created_at


def make_records(n=50):
    """生成模拟 ORM 记录"""
    import datetime
    base = datetime.datetime(2026, 5, 29, 8, 0, 0)
    records = []
    rng = np.random.RandomState(42)
    for i in range(n):
        records.append(MockRecord(
            head_angle=20 + rng.normal(0, 5),
            shoulder_diff=0.02 + abs(rng.normal(0, 0.01)),
            hunchback_score=0.15 + abs(rng.normal(0, 0.05)),
            body_tilt=2 + rng.normal(0, 1),
            round_shoulder=0.1 + abs(rng.normal(0, 0.03)),
            created_at=base + datetime.timedelta(minutes=i * 5),
        ))
    return records


class TestPreprocessing:
    def test_records_to_dataframe(self):
        records = make_records(20)
        df = records_to_dataframe(records)
        assert len(df) == 20
        for col in METRIC_COLUMNS:
            assert col in df.columns

    def test_remove_outliers(self):
        records = make_records(50)
        df = records_to_dataframe(records)
        # 人为加入一个异常值
        df.loc[25, "head_angle"] = 999
        cleaned = remove_outliers(df)
        assert len(cleaned) < len(df)

    def test_fill_missing(self):
        records = make_records(10)
        df = records_to_dataframe(records)
        df.loc[3, "head_angle"] = None
        df.loc[5, "shoulder_diff"] = None
        filled = fill_missing(df)
        assert filled["head_angle"].isna().sum() == 0
        assert filled["shoulder_diff"].isna().sum() == 0

    def test_aggregate_daily(self):
        records = make_records(100)
        df = records_to_dataframe(records)
        daily = aggregate_daily(df)
        assert len(daily) > 0
        assert "avg_head_angle" in daily.columns
        assert "record_count" in daily.columns
        assert "bad_posture_ratio" in daily.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
