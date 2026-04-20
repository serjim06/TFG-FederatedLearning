"""
Entrenamiento federado con Flower (FedAvg + simulación Ray): los clientes de cada ronda
se ejecutan en paralelo vía el motor virtual de Flower.

Los resultados (`results_per_round`, métricas finales) mantienen la forma esperada por
informes y la GUI.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import ray
import torch
from flwr.client import Client
from flwr.client.numpy_client import NumPyClient
from flwr.common import Context, Scalar, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.common.constant import PARTITION_ID_KEY
from flwr.common.typing import FitRes
from flwr.server.client_proxy import ClientProxy
from flwr.server.server_config import ServerConfig
from flwr.server.strategy import FedAvg
from flwr.simulation import start_simulation
from sklearn.metrics import confusion_matrix as sk_confusion_matrix

from src.models import node as nm

ProgressCallback = Optional[
    Callable[[int, int, str, Optional[float]], None]
]


def _loader_seed(server_round: int, partition_index: int) -> int:
    """
    Misma semilla en fit, evaluate (Flower) y post-proceso para que el split
    train/val de cada cliente coincida con el usado al entrenar esa ronda.
    """
    return int(server_round) * 1000 + int(partition_index)


def _print_client_dataset(
    phase: str,
    partition_index: int,
    nid: bytes,
    path: Path | str,
    server_round: int,
) -> None:
    """
    Provisional: traza qué CSV usa cada cliente simulado.

    El nombre ``dataset_0.csv`` es la ronda de datos del *proyecto* (``training_round``);
    cada **nodo** tiene su propia carpeta ``database/datasets/node_<uuid>/``.

    Ray puede deduplicar líneas parecidas en el log; para ver cada línea:
    ``set RAY_DEDUP_LOGS=0`` (Windows) antes de ejecutar.
    """
    ns = str(uuid.UUID(bytes=nid))
    ap = Path(path).resolve()
    # Incluir carpeta explícita: varios nodos comparten nombre de archivo pero no la ruta.
    print(
        f"[Flower] {phase} | partición={partition_index} | nodo={ns} | "
        f"ronda_servidor={server_round} | carpeta_nodo={ap.parent.name} | "
        f"archivo={ap.name} | ruta={ap}",
        flush=True,
    )


def _state_dict_to_ndarrays(sd: dict[str, torch.Tensor]) -> list[np.ndarray]:
    return [np.asarray(v.detach().cpu().numpy(), dtype=np.float32) for v in sd.values()]


def _ndarrays_to_state_dict(
    ndarrays: list[np.ndarray], keys: list[str]
) -> dict[str, torch.Tensor]:
    return {k: torch.from_numpy(arr) for k, arr in zip(keys, ndarrays)}


def _weighted_evaluate_metrics(
    results: list[tuple[int, dict[str, Scalar]]],
) -> dict[str, Scalar]:
    if not results:
        return {}
    total = sum(n for n, _ in results)
    if total <= 0:
        return {}
    acc = sum(n * float(m.get("accuracy", 0.0)) for n, m in results) / total
    return {"accuracy": acc}


def _fit_metrics_noop(
    results: list[tuple[int, dict[str, Scalar]]],
) -> dict[str, Scalar]:
    _ = results
    return {}


class _TrackingFedAvg(FedAvg):
    """FedAvg de Flower con registro de pesos globales por ronda y tiempos."""

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


class _FederatedNumPyClient(NumPyClient):
    """Cliente Flower (NumPy) ligado a la partición `partition_index` del proyecto."""

    def __init__(
        self,
        partition_index: int,
        project_row: dict[str, Any],
        node_ids_bytes: list[bytes],
        param_keys: list[str],
        in_features: Any,
        out_features: Any,
        params: dict[str, Any],
        task: str,
        metrics: str,
        metadata: dict[str, Any],
    ) -> None:
        super().__init__()
        self.partition_index = partition_index
        self.project_row = project_row
        self.node_ids_bytes = node_ids_bytes
        self.param_keys = param_keys
        self.in_features = in_features
        self.out_features = out_features
        self.params = params
        self.task = task
        self.metrics = metrics
        self.metadata = metadata

    def fit(
        self, parameters: list[np.ndarray], config: dict[str, Scalar]
    ) -> tuple[list[np.ndarray], int, dict[str, Scalar]]:
        device = nm._get_device()
        rnd = int(config.get("server_round", 1))
        nid = self.node_ids_bytes[self.partition_index]
        model_wrapper, model_path = nm._instantiate_model(self.project_row)
        crit = nm._criterion(self.metrics, self.task)

        path = nm._dataset_csv_path(nid, self.project_row)
        _print_client_dataset("fit", self.partition_index, nid, path, rnd)
        X, y, _enc = nm._load_xy_from_csv(
            path,
            self.in_features,
            self.out_features,
            self.metrics,
            self.metadata,
        )
        train_loader, val_loader = nm._make_loaders(
            X,
            y,
            batch_size=int(self.params.get("batch_size", 32)),
            validation_split=float(self.params.get("validation_split", 0.2)),
            task=self.task,
            seed=_loader_seed(rnd, self.partition_index),
        )

        net = model_wrapper.load_model(model_path)
        net.load_state_dict(
            {k: v.to(device) for k, v in _ndarrays_to_state_dict(parameters, self.param_keys).items()}
        )
        nm._train_loop(
            net,
            train_loader,
            val_loader,
            epochs=int(self.params.get("epochs", 3)),
            learning_rate=float(self.params.get("learning_rate", 0.01)),
            optimizer_name=str(self.params.get("optimizer", "adam")),
            criterion=crit,
            task=self.task,
            metrics=self.metrics,
            device=device,
        )
        n_train = len(train_loader.dataset)
        out_sd = {k: v.detach().cpu() for k, v in net.state_dict().items()}
        return _state_dict_to_ndarrays(out_sd), n_train, {}

    def evaluate(
        self, parameters: list[np.ndarray], config: dict[str, Scalar]
    ) -> tuple[float, int, dict[str, Scalar]]:
        device = nm._get_device()
        rnd = int(config.get("server_round", 1))
        nid = self.node_ids_bytes[self.partition_index]
        model_wrapper, model_path = nm._instantiate_model(self.project_row)
        crit = nm._criterion(self.metrics, self.task)

        path = nm._dataset_csv_path(nid, self.project_row)
        _print_client_dataset("evaluate", self.partition_index, nid, path, rnd)
        X, y, _enc = nm._load_xy_from_csv(
            path,
            self.in_features,
            self.out_features,
            self.metrics,
            self.metadata,
        )
        _, val_loader = nm._make_loaders(
            X,
            y,
            batch_size=int(self.params.get("batch_size", 32)),
            validation_split=float(self.params.get("validation_split", 0.2)),
            task=self.task,
            seed=_loader_seed(rnd, self.partition_index),
        )
        net = model_wrapper.load_model(model_path)
        net.load_state_dict(
            {k: v.to(device) for k, v in _ndarrays_to_state_dict(parameters, self.param_keys).items()}
        )
        ev = nm._evaluate_loop(net, val_loader, crit, self.task, self.metrics, device)
        n_val = len(val_loader.dataset)
        metrics_out: dict[str, Scalar] = {}
        if self.task == "classification":
            metrics_out["accuracy"] = float(ev.get("accuracy", 0.0))
        return float(ev["loss"]), n_val, metrics_out


def _make_client_fn(
    project_row: dict[str, Any],
    node_ids_bytes: list[bytes],
    param_keys: list[str],
    in_features: Any,
    out_features: Any,
    params: dict[str, Any],
    task: str,
    metrics: str,
    metadata: dict[str, Any],
) -> Callable[[Context], Client]:
    def client_fn(context: Context) -> Client:
        pid = int(context.node_config[PARTITION_ID_KEY])
        return _FederatedNumPyClient(
            partition_index=pid,
            project_row=project_row,
            node_ids_bytes=node_ids_bytes,
            param_keys=param_keys,
            in_features=in_features,
            out_features=out_features,
            params=params,
            task=task,
            metrics=metrics,
            metadata=metadata,
        ).to_client()

    return client_fn


def _collect_round_client_stats(
    snapshot_ndarrays: list[np.ndarray],
    param_keys: list[str],
    project_row: dict[str, Any],
    node_ids_bytes: list[bytes],
    in_features: Any,
    out_features: Any,
    params: dict[str, Any],
    task: str,
    metrics: str,
    metadata: dict[str, Any],
    model_wrapper: Any,
    model_path: str,
    device: torch.device,
    round_seed: int,
) -> tuple[list[dict[str, Any]], list[float], list[float], list[float]]:
    """Evalúa el modelo global de la ronda en cada cliente (mismo split val que en ``fit``)."""
    gnet = model_wrapper.load_model(model_path)
    gnet.load_state_dict(
        {k: v.to(device) for k, v in _ndarrays_to_state_dict(snapshot_ndarrays, param_keys).items()}
    )
    crit = nm._criterion(metrics, task)

    client_stats: list[dict[str, Any]] = []
    val_losses: list[float] = []
    acc_weights: list[float] = []
    client_accs: list[float] = []

    for partition_index, nid in enumerate(node_ids_bytes):
        ns = str(uuid.UUID(bytes=nid))
        path = nm._dataset_csv_path(nid, project_row)
        X, y, _enc = nm._load_xy_from_csv(
            path, in_features, out_features, metrics, metadata
        )
        _, val_loader = nm._make_loaders(
            X,
            y,
            batch_size=int(params.get("batch_size", 32)),
            validation_split=float(params.get("validation_split", 0.2)),
            task=task,
            seed=_loader_seed(round_seed, partition_index),
        )
        ev = nm._evaluate_loop(gnet, val_loader, crit, task, metrics, device)
        val_losses.append(float(ev["loss"]))
        n_samples = len(val_loader.dataset)
        acc_weights.append(float(n_samples))
        if task == "classification":
            client_accs.append(float(ev.get("accuracy", 0.0)))

        yt, yp = nm._gather_predictions(gnet, val_loader, device, task, metrics)
        if task == "classification":
            n_cls = nm._num_classes_from_arrays(yt, yp, metadata)
            labels = list(range(n_cls))
            cm = sk_confusion_matrix(yt, yp, labels=labels)
            client_stats.append({"client_id": ns, "confusion_matrix": cm.tolist()})
        else:
            client_stats.append(
                {
                    "client_id": ns,
                    "y_true": np.asarray(yt).astype(float).ravel().tolist(),
                    "y_pred": np.asarray(yp).astype(float).ravel().tolist(),
                }
            )

    return client_stats, val_losses, acc_weights, client_accs


def run_federated_training(
    project_row: dict[str, Any],
    num_federated_rounds: int,
    on_progress: ProgressCallback = None,
) -> dict[str, Any]:
    """
    Ejecuta ``num_federated_rounds`` rondas FedAvg con Flower (simulación Ray en paralelo).

    Parameters
    ----------
    project_row
        Fila de ``projects`` (dict) con ``nodes``, ``parameters``, ``model_path``, etc.
    num_federated_rounds
        Número de rondas federadas (comunicación servidor-clientes).
    on_progress
        ``callback(ronda_actual, total_rondas, mensaje_corto, eta_segundos)``.

    Returns
    -------
    dict con ``training_results_entry`` (un experimento con varias rondas en ``results_per_round``),
    ``total_time_seconds`` y ``global_state_dict`` (último modelo global, tensors en CPU).
    """
    if num_federated_rounds < 1:
        raise ValueError("El número de rondas debe ser >= 1.")

    params = project_row["parameters"]
    if isinstance(params, str):
        params = json.loads(params)

    node_ids_str = nm._project_total_client_ids(project_row)
    if not node_ids_str:
        raise ValueError("El proyecto no tiene nodos asignados.")

    node_ids_bytes = [uuid.UUID(ns).bytes for ns in node_ids_str]
    n_clients = len(node_ids_bytes)

    model_wrapper, model_path = nm._instantiate_model(project_row)
    feats = model_wrapper.get_features()
    metadata = feats.get("metadata") if isinstance(feats.get("metadata"), dict) else {}

    in_features = (
        json.loads(project_row["input_features"])
        if isinstance(project_row["input_features"], str)
        else project_row["input_features"]
    )
    out_features = (
        json.loads(project_row["output_features"])
        if isinstance(project_row["output_features"], str)
        else project_row["output_features"]
    )

    metrics = project_row.get("metrics", "categorical_crossentropy")
    task = metadata.get("type") or nm._task_kind(metrics)

    device = nm._get_device()

    net = model_wrapper.load_model(model_path)
    global_sd = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
    param_keys = list(global_sd.keys())
    initial_ndarrays = _state_dict_to_ndarrays(global_sd)
    initial_parameters = ndarrays_to_parameters(initial_ndarrays)

    snapshots: list[list[np.ndarray]] = []
    round_times: list[float] = []
    t_start = time.perf_counter()

    strategy = _TrackingFedAvg(
        snapshots=snapshots,
        round_times=round_times,
        on_progress=on_progress,
        num_rounds=num_federated_rounds,
        t_run_start=t_start,
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=n_clients,
        min_evaluate_clients=n_clients,
        min_available_clients=n_clients,
        initial_parameters=initial_parameters,
        on_fit_config_fn=lambda rnd: {"server_round": float(rnd)},
        on_evaluate_config_fn=lambda rnd: {"server_round": float(rnd)},
        fit_metrics_aggregation_fn=_fit_metrics_noop,
        evaluate_metrics_aggregation_fn=_weighted_evaluate_metrics,
        inplace=True,
    )

    client_fn = _make_client_fn(
        project_row,
        node_ids_bytes,
        param_keys,
        in_features,
        out_features,
        params,
        task,
        metrics,
        metadata,
    )

    try:
        start_simulation(
            client_fn=client_fn,
            num_clients=n_clients,
            config=ServerConfig(num_rounds=num_federated_rounds),
            strategy=strategy,
            client_resources={"num_cpus": 1.0, "num_gpus": 0.0},
            ray_init_args={
                "ignore_reinit_error": True,
                "include_dashboard": False,
            },
        )
    finally:
        if ray.is_initialized():
            ray.shutdown()

    total_time = time.perf_counter() - t_start

    if len(snapshots) != num_federated_rounds:
        raise RuntimeError(
            f"Flower no devolvió un snapshot por ronda: "
            f"esperadas {num_federated_rounds}, obtenidas {len(snapshots)}."
        )

    results_per_round: list[dict[str, Any]] = []
    for r in range(num_federated_rounds):
        round_time = round_times[r] if r < len(round_times) else 0.0
        snap = snapshots[r]

        client_stats, val_losses, acc_weights, client_accs = _collect_round_client_stats(
            snap,
            param_keys,
            project_row,
            node_ids_bytes,
            in_features,
            out_features,
            params,
            task,
            metrics,
            metadata,
            model_wrapper,
            model_path,
            device,
            round_seed=r + 1,
        )

        global_loss = float(np.mean(val_losses)) if val_losses else 0.0
        if task == "classification" and acc_weights:
            w = np.array(acc_weights, dtype=float)
            w = w / w.sum() if w.sum() > 0 else w
            global_accuracy = float(np.dot(w, np.array(client_accs)))
        else:
            global_accuracy = 0.0

        row: dict[str, Any] = {
            "round": r + 1,
            "time": round_time,
            "global_loss": global_loss,
            "client_stats": client_stats,
        }
        if task == "classification":
            row["global_accuracy"] = global_accuracy
        results_per_round.append(row)

    final_ndarrays = snapshots[-1]
    global_sd = {
        k: torch.from_numpy(arr).cpu() for k, arr in zip(param_keys, final_ndarrays)
    }

    first_nid = node_ids_bytes[0]
    path = nm._dataset_csv_path(first_nid, project_row)
    X, y, _enc = nm._load_xy_from_csv(
        path, in_features, out_features, metrics, metadata
    )
    _, val_loader = nm._make_loaders(
        X,
        y,
        batch_size=int(params.get("batch_size", 32)),
        validation_split=float(params.get("validation_split", 0.2)),
        task=task,
        seed=_loader_seed(num_federated_rounds, 0),
    )
    gnet = model_wrapper.load_model(model_path)
    gnet.load_state_dict({k: v.to(device) for k, v in global_sd.items()})
    last_yt, last_yp = nm._gather_predictions(gnet, val_loader, device, task, metrics)

    training_results_entry = nm.build_training_results_entry(
        project_row,
        first_nid,
        task,
        metrics,
        metadata,
        params,
        last_yt,
        last_yp,
        round_num=num_federated_rounds,
        elapsed_seconds=total_time,
        global_loss=float(results_per_round[-1]["global_loss"]) if results_per_round else 0.0,
    )
    training_results_entry["train_id"] = f"fed_{uuid.uuid4()}"
    training_results_entry["results_per_round"] = results_per_round
    training_results_entry["federated_rounds"] = num_federated_rounds
    training_results_entry["final_metrics"]["total_time_seconds"] = total_time
    if task == "classification" and results_per_round:
        training_results_entry["final_metrics"]["best_accuracy"] = float(
            max(r.get("global_accuracy", 0.0) for r in results_per_round)
        )

    return {
        "training_results_entry": training_results_entry,
        "total_time_seconds": total_time,
        "global_state_dict": global_sd,
    }
