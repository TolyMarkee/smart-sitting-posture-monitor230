"""测试 K-Means 聚类模块"""

import sys
import numpy as np
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "app" / "core"))

from kmeans_cluster import find_optimal_k, prepare_features, CLUSTER_NAMES
from data_preprocess import MockRecord, make_records


class MockRecord:
    def __init__(self, head_angle, shoulder_diff, hunchback_score, body_tilt, round_shoulder, created_at):
        self.head_angle = head_angle
        self.shoulder_diff = shoulder_diff
        self.hunchback_score = hunchback_score
        self.body_tilt = body_tilt
        self.round_shoulder = round_shoulder
        self.created_at = created_at


def make_records(n=50):
    import datetime
    base = datetime.datetime(2026, 5, 29, 8, 0, 0)
    rng = np.random.RandomState(42)
    return [
        MockRecord(
            head_angle=20 + rng.normal(0, 5),
            shoulder_diff=0.02 + abs(rng.normal(0, 0.01)),
            hunchback_score=0.15 + abs(rng.normal(0, 0.05)),
            body_tilt=2 + rng.normal(0, 1),
            round_shoulder=0.1 + abs(rng.normal(0, 0.03)),
            created_at=base + datetime.timedelta(minutes=i * 5),
        )
        for i in range(n)
    ]


class TestKMeans:
    def test_find_optimal_k(self):
        rng = np.random.RandomState(42)
        X = rng.rand(100, 5)
        k = find_optimal_k(X, max_k=5)
        assert 2 <= k <= 5

    def test_prepare_features(self):
        records = make_records(30)
        X = prepare_features(records)
        assert X.shape[1] == 5
        assert X.shape[0] > 0

    def test_cluster_names(self):
        assert CLUSTER_NAMES[0] == "标准坐姿型"
        assert len(CLUSTER_NAMES) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
