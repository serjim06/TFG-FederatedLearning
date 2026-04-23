from __future__ import annotations

import time
import json
from typing import Any, Callable, Optional

import numpy as np
from flwr.common import FitIns, Scalar, ndarrays_to_parameters, parameters_to_ndarrays
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


class TrackingScaffold(_FedStrategyRoundTracking, FedAvg):
    """Flower SCAFFOLD-like strategy with per-round snapshots and timing."""

    _param_keys: list[str]
    _local_epochs: int
    _learning_rate: float
    _total_clients: int
    _c_global: list[np.ndarray] | None
    _c_clients: dict[str, list[np.ndarray]]

    def __init__(
        self,
        *,
        snapshots: list[list[np.ndarray]],
        round_times: list[float],
        on_progress: ProgressCallback,
        num_rounds: int,
        t_run_start: float,
        param_keys: list[str],
        local_epochs: int,
        learning_rate: float,
        total_clients: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._snapshots = snapshots
        self._round_times = round_times
        self._on_progress = on_progress
        self._num_rounds = num_rounds
        self._t_run_start = t_run_start
        self._t_round_start = None
        self._param_keys = list(param_keys)
        self._local_epochs = max(1, int(local_epochs))
        self._learning_rate = float(learning_rate)
        self._total_clients = max(1, int(total_clients))
        self._c_global = None
        self._c_clients = {}

    @staticmethod
    def _serialize_arrays(arrays: list[np.ndarray]) -> str:
        return json.dumps([a.astype(np.float32).tolist() for a in arrays], ensure_ascii=False)

    @staticmethod
    def _deserialize_arrays(raw: Scalar | None) -> list[np.ndarray] | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        data = json.loads(raw)
        if not isinstance(data, list):
            return None
        out: list[np.ndarray] = []
        for x in data:
            out.append(np.asarray(x, dtype=np.float32))
        return out

    def _ensure_global_cv(self, parameters: Any) -> None:
        if self._c_global is not None:
            return
        nds = parameters_to_ndarrays(parameters)
        self._c_global = [np.zeros_like(np.asarray(a, dtype=np.float32)) for a in nds]

    def configure_fit(
        self,
        server_round: int,
        parameters: Any,
        client_manager: Any,
    ) -> list[tuple[ClientProxy, FitIns]]:
        pairs = super().configure_fit(server_round, parameters, client_manager)
        self._ensure_global_cv(parameters)
        c_global = self._c_global or []
        c_global_json = self._serialize_arrays(c_global)
        for client_proxy, fit_ins in pairs:
            cid = client_proxy.cid
            c_client = self._c_clients.get(cid)
            if c_client is None:
                c_client = [np.zeros_like(a) for a in c_global]
                self._c_clients[cid] = c_client
            cfg = dict(fit_ins.config)
            cfg["scaffold_enabled"] = 1.0
            cfg["scaffold_param_keys"] = json.dumps(self._param_keys, ensure_ascii=False)
            cfg["scaffold_c_global"] = c_global_json
            cfg["scaffold_c_client"] = self._serialize_arrays(c_client)
            cfg["scaffold_local_epochs"] = float(self._local_epochs)
            cfg["scaffold_learning_rate"] = float(self._learning_rate)
            fit_ins.config = cfg
        return pairs

    def aggregate_fit(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, FitRes]],
        failures: list[tuple[ClientProxy, FitRes] | BaseException],
    ) -> tuple[Any, dict[str, Scalar]]:
        valid = [
            (proxy, fit_res)
            for proxy, fit_res in results
            if fit_res.metrics.get("scaffold_ci_new") is not None
        ]
        if valid and self._c_global is not None:
            deltas = [np.zeros_like(a) for a in self._c_global]
            for client_proxy, fit_res in valid:
                cid = client_proxy.cid
                old_ci = self._c_clients.get(cid)
                new_ci = self._deserialize_arrays(fit_res.metrics.get("scaffold_ci_new"))
                if old_ci is None or new_ci is None or len(new_ci) != len(self._c_global):
                    continue
                self._c_clients[cid] = [np.asarray(a, dtype=np.float32) for a in new_ci]
                for j in range(len(deltas)):
                    deltas[j] += self._c_clients[cid][j] - old_ci[j]
            scale = 1.0 / float(self._total_clients)
            for j in range(len(self._c_global)):
                self._c_global[j] = self._c_global[j] + deltas[j] * scale
        return super().aggregate_fit(server_round, results, failures)


class TrackingSSFed(_FedStrategyRoundTracking, FedAvg):
    """Flower SSFed strategy with significance-based weighted aggregation.
    
    This implementation is based on the pseudo-code and technical description of the SSFed algorithm.
    The algorithm is described in the following article:
    - Yousef Alsenani. “SSFed: Statistical Significance Aggregation Algorithm in Federated Learning”. International Journal of Advanced Computer Science and Applications (IJACSA) 16.3 (2025).
    - The referenced article is available at: http://dx.doi.org/10.14569/IJACSA.2025.01603112
    """

    _z_threshold: float
    _eps: float

    def __init__(
        self,
        *,
        snapshots: list[list[np.ndarray]],
        round_times: list[float],
        on_progress: ProgressCallback,
        num_rounds: int,
        t_run_start: float,
        z_threshold: float = 1.96,
        eps: float = 1e-12,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._snapshots = snapshots
        self._round_times = round_times
        self._on_progress = on_progress
        self._num_rounds = num_rounds
        self._t_run_start = t_run_start
        self._t_round_start = None
        self._z_threshold = float(z_threshold)
        self._eps = float(eps)

    def aggregate_fit(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, FitRes]],
        failures: list[tuple[ClientProxy, FitRes] | BaseException],
    ) -> tuple[Any, dict[str, Scalar]]:
        if not results:
            return super().aggregate_fit(server_round, results, failures)

        client_weights: list[list[np.ndarray]] = []
        for _, fit_res in results:
            client_weights.append(
                [np.asarray(w, dtype=np.float32) for w in parameters_to_ndarrays(fit_res.parameters)]
            )

        if not client_weights:
            return super().aggregate_fit(server_round, results, failures)

        n_clients = len(client_weights)
        n_tensors = len(client_weights[0])
        if n_clients < 2 or n_tensors == 0:
            return super().aggregate_fit(server_round, results, failures)

        client_max_z = np.zeros(n_clients, dtype=np.float64)
        client_avg_z = np.zeros(n_clients, dtype=np.float64)

        for j in range(n_tensors):
            stacked = np.stack([client_weights[i][j] for i in range(n_clients)], axis=0)
            mean_j = np.mean(stacked, axis=0)
            std_j = np.std(stacked, axis=0)
            z_j = np.abs(stacked - mean_j) / np.maximum(std_j, self._eps)
            flat = z_j.reshape(n_clients, -1)
            client_max_z = np.maximum(client_max_z, np.max(flat, axis=1))
            client_avg_z += np.mean(flat, axis=1)

        client_avg_z /= float(n_tensors)
        selected_idx = np.where(client_max_z > self._z_threshold)[0]
        if selected_idx.size == 0:
            selected_idx = np.arange(n_clients)

        selected_avg_z = client_avg_z[selected_idx]
        alpha = 1.0 / np.maximum(selected_avg_z, self._eps)
        alpha = alpha / np.sum(alpha)

        aggregated: list[np.ndarray] = []
        for j in range(n_tensors):
            acc = np.zeros_like(client_weights[0][j], dtype=np.float32)
            for local_pos, i in enumerate(selected_idx):
                acc += np.asarray(alpha[local_pos], dtype=np.float32) * client_weights[i][j]
            aggregated.append(acc.astype(np.float32, copy=False))

        out_parameters = ndarrays_to_parameters(aggregated)
        out_metrics: dict[str, Scalar] = {
            "ssfed_selected_clients": float(selected_idx.size),
            "ssfed_total_clients": float(n_clients),
            "ssfed_selection_ratio": float(selected_idx.size) / float(max(n_clients, 1)),
            "ssfed_threshold": float(self._z_threshold),
        }
        return out_parameters, out_metrics


def create_tracking_strategy(
    aggregation_strategy: str | None,
    *,
    snapshots: list[list[np.ndarray]],
    round_times: list[float],
    on_progress: ProgressCallback,
    num_rounds: int,
    t_run_start: float,
    param_keys: list[str] | None = None,
    local_epochs: int = 1,
    learning_rate: float = 0.01,
    total_clients: int = 1,
    ssfed_z_threshold: float = 1.96,
    **flower_kwargs: Any,
) -> Strategy:
    """Build a Flower server strategy that aggregates client updates and records state each round.

    The returned instance subclasses Flower's ``FedAvg`` or ``FedMedian``, or
    uses a SCAFFOLD-compatible variant, and mixes in round timing plus a copy of the global
    parameters after every successful ``aggregate_fit`` into ``snapshots`` (one list of
    weight arrays per federated round).

    Selection rule (case-insensitive, surrounding whitespace ignored):

    * ``fed_med`` → ``TrackingFedMedian`` (coordinate-wise median).
    * ``fed_scaffold`` → ``TrackingScaffold`` (control variates).
    * ``fed_ssfed`` → ``TrackingSSFed`` (significance-based weighting).
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
    if key not in {
        "",
        "fed_avg",
        "fed_med",
        "fed_scaffold",
        "fed_ssfed",
        "fed_sum",
        "fed_weighted",
        "fed_prox",
    }:
        raise ValueError(f"Estrategia de agregación no soportada: {aggregation_strategy!r}")
    if key == "fed_med":
        return TrackingFedMedian(**tracking_kwargs, **flower_kwargs)
    if key == "fed_scaffold":
        return TrackingScaffold(
            **tracking_kwargs,
            param_keys=list(param_keys or []),
            local_epochs=local_epochs,
            learning_rate=learning_rate,
            total_clients=total_clients,
            **flower_kwargs,
        )
    if key == "fed_ssfed":
        return TrackingSSFed(
            **tracking_kwargs,
            z_threshold=ssfed_z_threshold,
            **flower_kwargs,
        )
    return TrackingFedAvg(**tracking_kwargs, **flower_kwargs)
