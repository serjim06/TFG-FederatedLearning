import json
import math
from pathlib import Path

import pytest

from src.application.services.project_metrics_calculations import (
    get_datasets_changes,
    get_metrics_per_round,
    get_regression_metrics_bundle,
    get_time_per_round,
)


@pytest.fixture
def classification_training() -> list:
    path = Path(__file__).resolve().parent / "sample_results.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def regression_training() -> list:
    path = Path(__file__).resolve().parent / "sample_regression.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def test_get_metrics_per_round_classification_shape_and_participation(
    classification_training: list,
) -> None:
    metrics = get_metrics_per_round(classification_training, "classification")
    assert len(metrics) == 2
    assert metrics[0].keys() == {"loss", "accuracy", "f1", "participation"}
    assert math.isclose(metrics[0]["loss"], 2.45)
    assert math.isclose(metrics[0]["accuracy"], 0.35)
    assert math.isclose(metrics[0]["participation"], 2 / 3)
    assert not math.isnan(metrics[0]["f1"])
    assert math.isclose(metrics[1]["loss"], 1.20)
    assert math.isclose(metrics[1]["accuracy"], 0.72)


def test_get_metrics_per_round_regression_with_r2(regression_training: list) -> None:
    metrics = get_metrics_per_round(regression_training, "regression")
    assert len(metrics) == 2
    assert metrics[0].keys() == {"loss", "r2", "participation"}
    assert not math.isnan(metrics[0]["r2"])
    assert not math.isnan(metrics[1]["r2"])


def test_get_metrics_per_round_regression_on_classification_data_yields_nan_r2(
    classification_training: list,
) -> None:
    metrics = get_metrics_per_round(classification_training, "regression")
    assert len(metrics) == 2
    assert all(math.isnan(m["r2"]) for m in metrics)


def test_get_regression_metrics_bundle_aligns_totals(regression_training: list) -> None:
    metrics, y_true_total, y_pred_total = get_regression_metrics_bundle(regression_training)
    assert len(metrics) == 2
    assert len(y_true_total) == len(y_pred_total)
    assert len(y_true_total) > 0


def test_get_time_per_round_order(classification_training: list) -> None:
    times = get_time_per_round(classification_training)
    assert times == [600, 600]


def test_get_datasets_changes_missing_nodes_returns_empty() -> None:
    out = get_datasets_changes(["__nonexistent_node_xyz__"])
    assert out["datasets_changes"] == {}
    assert out["composed_changes"] == {}


def test_get_datasets_changes_empty_node_list() -> None:
    out = get_datasets_changes([])
    assert out["datasets_changes"] == {}
    assert out["composed_changes"] == {}
