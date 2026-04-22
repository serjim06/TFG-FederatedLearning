"""
Entrenamiento federado con Flower y simulación Ray: los clientes de cada ronda se
ejecutan en paralelo vía el motor virtual de Flower.
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
from flwr.common import Context, Scalar, ndarrays_to_parameters
from flwr.common.constant import PARTITION_ID_KEY
from flwr.server.server_config import ServerConfig
from flwr.simulation import start_simulation
from sklearn.metrics import confusion_matrix as sk_confusion_matrix

from src.federated.strategy import (
    ProgressCallback,
    create_tracking_strategy,
    fit_metrics_noop,
    weighted_evaluate_metrics,
)
from src.models import node as nm


def _persist_global_weights_for_train_id(
    project_row: dict[str, Any],
    global_sd: dict[str, torch.Tensor],
    train_id: str,
) -> None:
    """Guarda el ``state_dict`` global como ``{train_id}.pth`` junto al ``.py`` del modelo."""
    if not global_sd or not (train_id or "").strip():
        return
    mp = (project_row.get("model_path") or "").strip()
    if not mp:
        return
    nm.persist_state_dict_for_train(mp, train_id.strip(), global_sd, project_row)


def _flower_client_resources() -> tuple[dict[str, float], Optional[dict[str, Any]]]:
    """
    Recursos por cliente Flower y configuración opcional de Ray.

    Si hay CUDA disponible, cada cliente reserva 1 GPU para garantizar
    que el entrenamiento local se ejecute en GPU.
    """
    has_cuda = torch.cuda.is_available() and torch.cuda.device_count() > 0
    if not has_cuda:
        return {"num_cpus": 1.0, "num_gpus": 0.0}, None

    return {"num_cpus": 1.0, "num_gpus": 1.0}, {"num_gpus": torch.cuda.device_count()}


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


def _json_to_ndarrays(raw: Any) -> list[np.ndarray]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    out: list[np.ndarray] = []
    for x in data:
        out.append(np.asarray(x, dtype=np.float32))
    return out


def _ndarrays_to_json(arrays: list[np.ndarray]) -> str:
    return json.dumps([a.astype(np.float32).tolist() for a in arrays], ensure_ascii=False)


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
            task=self.task,
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
        in_arrays = [np.asarray(a, dtype=np.float32).copy() for a in parameters]
        net.load_state_dict(
            {k: v.to(device) for k, v in _ndarrays_to_state_dict(in_arrays, self.param_keys).items()}
        )
        metrics_out: dict[str, Scalar] = {}
        use_scaffold = float(config.get("scaffold_enabled", 0.0)) > 0.0
        local_epochs = int(self.params.get("epochs", 3))
        lr = float(self.params.get("learning_rate", 0.01))
        if use_scaffold:
            local_epochs = max(1, int(float(config.get("scaffold_local_epochs", float(local_epochs)))))
            lr = float(config.get("scaffold_learning_rate", lr))
            c_global = _json_to_ndarrays(config.get("scaffold_c_global"))
            c_client = _json_to_ndarrays(config.get("scaffold_c_client"))
            correction_by_param: dict[str, torch.Tensor] = {}
            if len(c_global) == len(in_arrays) and len(c_client) == len(in_arrays):
                for j, key in enumerate(self.param_keys):
                    corr = np.asarray(c_global[j], dtype=np.float32) - np.asarray(
                        c_client[j], dtype=np.float32
                    )
                    correction_by_param[key] = torch.from_numpy(corr).to(device)
            steps_done = nm._train_loop_scaffold(
                net,
                train_loader,
                epochs=local_epochs,
                learning_rate=lr,
                optimizer_name=str(self.params.get("optimizer", "adam")),
                criterion=crit,
                task=self.task,
                metrics=self.metrics,
                device=device,
                correction_by_param=correction_by_param,
            )
        else:
            nm._train_loop(
                net,
                train_loader,
                val_loader,
                epochs=local_epochs,
                learning_rate=lr,
                optimizer_name=str(self.params.get("optimizer", "adam")),
                criterion=crit,
                task=self.task,
                metrics=self.metrics,
                device=device,
            )
            steps_done = max(1, local_epochs * max(1, len(train_loader)))
        n_train = len(train_loader.dataset)
        out_sd = {k: v.detach().cpu() for k, v in net.state_dict().items()}
        out_arrays = _state_dict_to_ndarrays(out_sd)

        if use_scaffold:
            c_global = _json_to_ndarrays(config.get("scaffold_c_global"))
            c_client = _json_to_ndarrays(config.get("scaffold_c_client"))
            eff = max(1e-12, float(steps_done) * max(lr, 1e-12))
            if len(c_global) == len(out_arrays) and len(c_client) == len(out_arrays):
                c_new: list[np.ndarray] = []
                for j in range(len(out_arrays)):
                    w_t = in_arrays[j]
                    w_i = np.asarray(out_arrays[j], dtype=np.float32)
                    ci_new = (
                        np.asarray(c_client[j], dtype=np.float32)
                        - np.asarray(c_global[j], dtype=np.float32)
                        + (np.asarray(w_t, dtype=np.float32) - w_i) / eff
                    )
                    c_new.append(np.asarray(ci_new, dtype=np.float32))
                metrics_out["scaffold_ci_new"] = _ndarrays_to_json(c_new)
        return out_arrays, n_train, metrics_out

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
            task=self.task,
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
    *,
    full_detail: bool = True,
) -> tuple[list[dict[str, Any]], list[float], list[float], list[float]]:
    """
    Evalúa el modelo global de la ronda en cada cliente (mismo split val que en ``fit``).

    Si ``full_detail`` es False, solo se guardan pérdida/accuracy agregada por cliente
    (sin matrices ni vectores ``y_*``) para reducir tiempo y tamaño del JSON.
    """
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
            path, in_features, out_features, metrics, metadata, task=task
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

        if not full_detail:
            client_stats.append(
                {
                    "client_id": ns,
                    "val_loss": float(ev["loss"]),
                    "n_val_samples": int(n_samples),
                }
            )
            continue

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
    task = nm.resolve_task(params, metadata, metrics)

    device = nm._get_device()

    net = model_wrapper.load_model(model_path)
    nm.load_trained_weights_into(net, project_row, model_path)
    global_sd = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
    param_keys = list(global_sd.keys())
    initial_ndarrays = _state_dict_to_ndarrays(global_sd)
    initial_parameters = ndarrays_to_parameters(initial_ndarrays)

    snapshots: list[list[np.ndarray]] = []
    round_times: list[float] = []
    t_start = time.perf_counter()

    fraction_fit = project_row.get("fraction_fit", 1.0)
    fraction_evaluate = project_row.get("fraction_evaluate", 1.0)

    strategy = create_tracking_strategy(
        project_row.get("aggregation_strategy"),
        snapshots=snapshots,
        round_times=round_times,
        on_progress=on_progress,
        num_rounds=num_federated_rounds,
        t_run_start=t_start,
        param_keys=param_keys,
        local_epochs=int(params.get("epochs", 3)),
        learning_rate=float(params.get("learning_rate", 0.01)),
        total_clients=n_clients,
        fraction_fit=fraction_fit,
        fraction_evaluate=fraction_evaluate,
        min_fit_clients=int(n_clients * fraction_fit),
        min_evaluate_clients=int(n_clients * fraction_evaluate),
        min_available_clients=n_clients,
        initial_parameters=initial_parameters,
        on_fit_config_fn=lambda rnd: {"server_round": float(rnd)},
        on_evaluate_config_fn=lambda rnd: {"server_round": float(rnd)},
        fit_metrics_aggregation_fn=fit_metrics_noop,
        evaluate_metrics_aggregation_fn=weighted_evaluate_metrics,
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

    client_resources, ray_gpu_args = _flower_client_resources()
    ray_init_args: dict[str, Any] = {
        "ignore_reinit_error": True,
        "include_dashboard": False,
    }
    if ray_gpu_args is not None:
        ray_init_args.update(ray_gpu_args)

    try:
        start_simulation(
            client_fn=client_fn,
            num_clients=n_clients,
            config=ServerConfig(num_rounds=num_federated_rounds),
            strategy=strategy,
            client_resources=client_resources,
            ray_init_args=ray_init_args,
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
    n_clients = len(node_ids_bytes)
    for r in range(num_federated_rounds):
        round_time = round_times[r] if r < len(round_times) else 0.0
        snap = snapshots[r]
        is_last = r == num_federated_rounds - 1

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
            full_detail=is_last,
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
            "participating_clients": n_clients,
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
        path, in_features, out_features, metrics, metadata, task=task
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

    fed_train_id = f"fed_{uuid.uuid4()}"
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
    training_results_entry["train_id"] = fed_train_id
    training_results_entry["results_per_round"] = results_per_round
    training_results_entry["federated_rounds"] = num_federated_rounds
    training_results_entry["final_metrics"]["total_time_seconds"] = total_time
    if task == "classification" and results_per_round:
        training_results_entry["final_metrics"]["best_accuracy"] = float(
            max(r.get("global_accuracy", 0.0) for r in results_per_round)
        )

    last_cs = results_per_round[-1].get("client_stats") or []
    training_results_entry["final_metrics"]["client_stats_final"] = last_cs
    if task == "regression" and last_cs and isinstance(last_cs[0], dict) and "y_true" in last_cs[0]:
        yt_f: list[float] = []
        yp_f: list[float] = []
        for c in last_cs:
            yt_f.extend(c.get("y_true", []))
            yp_f.extend(c.get("y_pred", []))
        training_results_entry["final_metrics"]["y_true_final"] = yt_f
        training_results_entry["final_metrics"]["y_pred_final"] = yp_f
    elif task == "classification" and last_cs and isinstance(last_cs[0], dict):
        if "confusion_matrix" in last_cs[0]:
            yt_all: list[int] = []
            yp_all: list[int] = []
            for c in last_cs:
                cm = np.asarray(c["confusion_matrix"], dtype=int)
                for i in range(cm.shape[0]):
                    for j in range(cm.shape[1]):
                        n_ij = int(cm[i, j])
                        yt_all.extend([i] * n_ij)
                        yp_all.extend([j] * n_ij)
            training_results_entry["final_metrics"]["y_true_final"] = yt_all
            training_results_entry["final_metrics"]["y_pred_final"] = yp_all

    _persist_global_weights_for_train_id(project_row, global_sd, fed_train_id)

    return {
        "training_results_entry": training_results_entry,
        "total_time_seconds": total_time,
        "global_state_dict": global_sd,
    }
