from __future__ import annotations

import time
from typing import Any, Callable, Optional

import numpy as np
from flwr.common import Scalar, parameters_to_ndarrays
from flwr.common.typing import FitRes
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg, FedMedian, Strategy

ProgressCallback = Optional[
    Callable[[int, int, str, Optional[float]], None]
]


def weighted_evaluate_metrics(
    results: list[tuple[int, dict[str, Scalar]]],
) -> dict[str, Scalar]:
    """Return accuracy averaged across clients weighted by validation sample count."""
    if not results:
        return {}
    total = sum(n for n, _ in results)
    if total <= 0:
        return {}
    acc = sum(n * float(m.get("accuracy", 0.0)) for n, m in results) / total
    return {"accuracy": acc}


def fit_metrics_noop(
    results: list[tuple[int, dict[str, Scalar]]],
) -> dict[str, Scalar]:
    """Ignore per-client fit metrics and return an empty aggregation."""
    _ = results
    return {}


class _FedStrategyRoundTracking:
    """Record aggregated global parameters after each fit round and per-round wall times."""

    _snapshots: list[list[np.ndarray]]
    _round_times: list[float]
    _on_progress: ProgressCallback
    _num_rounds: int
    _t_run_start: float
    _t_round_start: float | None

    def configure_fit(
        self,
        server_round: int,
        parameters: Any,
        client_manager: Any,
    ) -> list[tuple[ClientProxy, Any]]:
        self._t_round_start = time.perf_counter()
        if self._on_progress:
            self._on_progress(
                server_round,
                self._num_rounds,
                (
                    f"Ronda {server_round}/{self._num_rounds} — Flower (Ray): "
                    "entrenamiento paralelo de clientes…"
                ),
                None,
            )
        return super().configure_fit(server_round, parameters, client_manager)

    def aggregate_fit(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, FitRes]],
        failures: list[tuple[ClientProxy, FitRes] | BaseException],
    ) -> tuple[Any, dict[str, Scalar]]:
        out = super().aggregate_fit(server_round, results, failures)
        params, metrics = out
        if params is not None:
            self._snapshots.append(
                [np.asarray(a, dtype=np.float32).copy() for a in parameters_to_ndarrays(params)]
            )
        return out

    def aggregate_evaluate(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, Any]],
        failures: list[tuple[ClientProxy, Any] | BaseException],
    ) -> tuple[float | None, dict[str, Scalar]]:
        out = super().aggregate_evaluate(server_round, results, failures)
        if self._t_round_start is not None:
            self._round_times.append(time.perf_counter() - self._t_round_start)
        if self._on_progress:
            elapsed = time.perf_counter() - self._t_run_start
            eta: float | None = None
            if server_round > 0:
                avg = elapsed / server_round
                eta = max(0.0, avg * (self._num_rounds - server_round))
            self._on_progress(
                server_round,
                self._num_rounds,
                f"Ronda {server_round}/{self._num_rounds} — modelo global actualizado",
                eta,
            )
        return out


class TrackingFedAvg(_FedStrategyRoundTracking, FedAvg):
    """Flower FedAvg with per-round global weight snapshots and round timing."""

    def __init__(
        self,
        *,
        snapshots: list[list[np.ndarray]],
        round_times: list[float],
        on_progress: ProgressCallback,
        num_rounds: int,
        t_run_start: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._snapshots = snapshots
        self._round_times = round_times
        self._on_progress = on_progress
        self._num_rounds = num_rounds
        self._t_run_start = t_run_start
        self._t_round_start: float | None = None


class TrackingFedMedian(_FedStrategyRoundTracking, FedMedian):
    """Flower FedMedian with per-round global weight snapshots and round timing."""

    def __init__(
        self,
        *,
        snapshots: list[list[np.ndarray]],
        round_times: list[float],
        on_progress: ProgressCallback,
        num_rounds: int,
        t_run_start: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._snapshots = snapshots
        self._round_times = round_times
        self._on_progress = on_progress
        self._num_rounds = num_rounds
        self._t_run_start = t_run_start
        self._t_round_start: float | None = None


def create_tracking_strategy(
    aggregation_strategy: str | None,
    *,
    snapshots: list[list[np.ndarray]],
    round_times: list[float],
    on_progress: ProgressCallback,
    num_rounds: int,
    t_run_start: float,
    **flower_kwargs: Any,
) -> Strategy:
    """Build a Flower server strategy that aggregates client updates and records state each round.

    The returned instance subclasses Flower's ``FedAvg`` or ``FedMedian`` and mixes in
    round timing plus a copy of the global parameters after every successful ``aggregate_fit``
    into ``snapshots`` (one list of weight arrays per federated round).

    Selection rule (case-insensitive, surrounding whitespace ignored):

    * ``fed_med`` → ``TrackingFedMedian`` (coordinate-wise median).
    * Any other value, including ``None`` or empty string → ``TrackingFedAvg``
      (sample-weighted average).

    Args:
        aggregation_strategy: Project field ``aggregation_strategy``; drives which base
            aggregation is used.
        snapshots: Mutable list filled by the strategy with one entry per completed round;
            each entry is a list of ``float32`` arrays matching the model parameter tensors.
        round_times: Mutable list filled with wall-clock seconds from configure_fit to
            end of aggregate_evaluate for each round.
        on_progress: Optional callback ``(current_round, total_rounds, message, eta_seconds)``.
        num_rounds: Total planned federated rounds (used for progress messages and ETA).
        t_run_start: Monotonic time reference (e.g. ``time.perf_counter()`` at run start)
            for ETA computation in progress callbacks.
        **flower_kwargs: Forwarded unchanged to the underlying Flower strategy constructor
            (e.g. ``fraction_fit``, ``min_fit_clients``, ``initial_parameters``,
            ``on_fit_config_fn``, ``fit_metrics_aggregation_fn``, ``inplace``).

    Returns:
        A Flower ``Strategy`` instance ready for ``start_simulation`` or an equivalent server loop.

    Note:
        ``FedMedian`` requires enough participating clients per round to form a median (at least 2);
        ensure ``min_fit_clients`` and sampling fractions match your deployment.
    """
    key = (aggregation_strategy or "").strip().lower()
    tracking_kwargs: dict[str, Any] = {
        "snapshots": snapshots,
        "round_times": round_times,
        "on_progress": on_progress,
        "num_rounds": num_rounds,
        "t_run_start": t_run_start,
    }
    if key == "fed_med":
        return TrackingFedMedian(**tracking_kwargs, **flower_kwargs)
    return TrackingFedAvg(**tracking_kwargs, **flower_kwargs)
