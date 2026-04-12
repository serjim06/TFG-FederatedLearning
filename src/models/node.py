from __future__ import annotations

import csv
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import DataLoader, TensorDataset

from src.db import dbcon
from src.projects.projects import cargar_modulo, verificar_modulo

# Raíz de datasets (misma convención que ``src.gui.add_dataset``)
DATASETS_ROOT = Path(__file__).resolve().parent.parent.parent / "database" / "datasets"


def _node_uuid_str(node_id: bytes) -> str:
    return str(uuid.UUID(bytes=node_id))


def _resolve_model_path(model_path: str) -> str:
    if not (model_path or "").strip():
        raise ValueError("El proyecto no tiene model_path definido.")
    p = model_path.strip()
    if os.path.isabs(p):
        return os.path.normpath(p)
    return os.path.normpath(os.path.join(os.getcwd(), p))


def _fetch_node_row(node_id: bytes) -> dict:
    rows = dbcon.command("select", "nodes", {"id": node_id})
    if not rows:
        raise ValueError("El nodo no existe en la base de datos.")
    return rows[0]


def _fetch_project_for_node(node_id: bytes) -> dict:
    """Obtiene la fila del proyecto asociado al nodo (vía ``nodes.project_id``)."""
    n = _fetch_node_row(node_id)
    pid = n.get("project_id")
    if pid is None or pid == "":
        raise ValueError("El nodo no está asignado a ningún proyecto (project_id vacío).")
    rows = dbcon.command("select", "projects", {"id": pid})
    if not rows:
        raise ValueError("No se encontró el proyecto del nodo en la base de datos.")
    return rows[0]


def _dataset_csv_path(node_id: bytes, project_row: dict) -> Path:
    """Ruta al CSV de la ronda actual del nodo (misma lógica que la GUI)."""
    r = int(project_row.get("training_round") or 0)
    node_dir = DATASETS_ROOT / f"node_{_node_uuid_str(node_id)}"
    path = node_dir / f"dataset_{r}.csv"
    if not path.is_file():
        raise FileNotFoundError(
            f"No existe el dataset local esperado: {path}. "
            "Añade datos con la opción «Añadir dataset» o crea el CSV."
        )
    return path


def _task_kind(metrics: str) -> str:
    if metrics == "mean_squared_error":
        return "regression"
    return "classification"


def _parse_header_and_rows(
    path: Path, expected_cols: list[str]
) -> tuple[bool, list[list[str]]]:
    """Devuelve (tiene_cabecera_con_etiquetas, filas_datos)."""
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.reader(f))
    while rows and not any((c or "").strip() for c in rows[-1]):
        rows.pop()
    if not rows:
        raise ValueError("El CSV está vacío.")

    def _row_matches_header(r: list[str]) -> bool:
        if len(r) != len(expected_cols):
            return False
        return all((a or "").strip() == (b or "").strip() for a, b in zip(r, expected_cols))

    if _row_matches_header(rows[0]):
        if len(rows) < 2:
            raise ValueError("El CSV solo contiene cabecera; no hay filas de datos.")
        return True, rows[1:]
    return False, rows


def _to_float_cell(s: str, col: str) -> float:
    t = (s or "").strip()
    try:
        return float(t)
    except ValueError as e:
        raise ValueError(
            f"Se esperaba un número en la columna de entrada «{col}», se obtuvo «{s}»."
        ) from e


def _load_xy_from_csv(
    path: Path,
    in_features: list[str],
    out_features: list[str],
    metrics: str,
    metadata: Optional[dict],
) -> tuple[np.ndarray, np.ndarray, Optional[LabelEncoder]]:
    """Construye matrices X, y (y opcional encoder de etiquetas para clasificación)."""
    expected = list(in_features) + list(out_features)
    _, data_rows = _parse_header_and_rows(path, expected)
    if not data_rows:
        raise ValueError("No hay filas de datos en el CSV.")

    n_in, n_out = len(in_features), len(out_features)
    in_idx = list(range(n_in))
    out_idx = list(range(n_in, n_in + n_out))

    X_list: list[list[float]] = []
    y_raw: list[list[Any]] = [[] for _ in range(n_out)]

    for ri, row in enumerate(data_rows, start=1):
        if len(row) != len(expected):
            raise ValueError(
                f"Fila {ri}: se esperaban {len(expected)} columnas, hay {len(row)}."
            )
        for j, cell in enumerate(row):
            if not (cell or "").strip():
                raise ValueError(f"Fila {ri}: celda vacía en «{expected[j]}».")
        X_list.append([_to_float_cell(row[j], expected[j]) for j in in_idx])
        for k, j in enumerate(out_idx):
            y_raw[k].append((row[j] or "").strip())

    X = np.asarray(X_list, dtype=np.float32)

    task = (metadata or {}).get("type") or _task_kind(metrics)

    if task == "regression":
        y_blocks = []
        for k in range(n_out):
            col_vals = y_raw[k]
            nums: list[float] = []
            for s in col_vals:
                try:
                    nums.append(float(s))
                except ValueError as e:
                    raise ValueError(
                        f"Regresión: la salida «{out_features[k]}» debe ser numérica; "
                        f"valor problemático: «{s}»."
                    ) from e
            y_blocks.append(np.asarray(nums, dtype=np.float32))
        if n_out == 1:
            y = y_blocks[0]
        else:
            y = np.stack(y_blocks, axis=1)
        return X, y, None

    # Clasificación: una columna de salida típica
    if n_out != 1:
        raise NotImplementedError(
            "La carga automática de CSV solo soporta clasificación con una columna de salida."
        )
    raw_labels = y_raw[0]
    try:
        y_num = np.asarray([float(x) for x in raw_labels], dtype=np.float64)
        if np.all(y_num == np.floor(y_num)):
            y = y_num.astype(np.int64)
            return X, y, None
    except ValueError:
        pass

    le = LabelEncoder()
    y = le.fit_transform(raw_labels).astype(np.int64)
    return X, y, le


def _make_loaders(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    validation_split: float,
    task: str,
    seed: int = 0,
) -> tuple[DataLoader, DataLoader]:
    rng = np.random.RandomState(seed)
    if len(X) < 2:
        # Un solo ejemplo: no hay validación
        ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
        loader = DataLoader(ds, batch_size=max(1, min(batch_size, len(X))), shuffle=False)
        return loader, loader

    stratify = None
    if task == "classification":
        u, c = np.unique(y, return_counts=True)
        if len(u) > 1 and c.min() >= 2:
            stratify = y

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=validation_split,
        random_state=rng.randint(0, 2**31 - 1),
        stratify=stratify,
    )
    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True),
        DataLoader(val_ds, batch_size=batch_size, shuffle=False),
    )


def _instantiate_model(project_row: dict):
    """Carga el módulo .py del proyecto y devuelve una instancia de la subclase de BaseModel."""
    mp = _resolve_model_path(project_row["model_path"])
    mod = cargar_modulo(mp)
    cls = verificar_modulo(mod)
    if cls is None:
        raise ValueError("El archivo del modelo no define una clase que herede de BaseModel.")
    return cls(), mp


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _criterion(metrics: str, task: str) -> nn.Module:
    m = (metrics or "").lower().strip()
    if task == "regression" or m == "mean_squared_error":
        return nn.MSELoss()
    if m == "binary_crossentropy":
        return nn.BCEWithLogitsLoss()
    return nn.CrossEntropyLoss()


def _optimizer(name: str, parameters, lr: float) -> torch.optim.Optimizer:
    n = (name or "adam").lower().strip()
    if n == "sgd":
        return torch.optim.SGD(parameters, lr=lr)
    if n == "rmsprop":
        return torch.optim.RMSprop(parameters, lr=lr)
    return torch.optim.Adam(parameters, lr=lr)


def _compute_batch_loss(
    out: torch.Tensor,
    yb: torch.Tensor,
    criterion: nn.Module,
    task: str,
    metrics: str,
) -> torch.Tensor:
    m = (metrics or "").lower().strip()
    if task == "regression":
        o = out
        y = yb.float()
        if o.dim() > 1 and o.size(-1) == 1:
            o = o.squeeze(-1)
        if y.dim() > 1 and y.size(-1) == 1:
            y = y.squeeze(-1)
        return criterion(o, y)

    if m == "binary_crossentropy":
        o = out.squeeze(-1) if out.dim() > 1 else out
        y = yb.float().flatten()
        o = o.flatten()
        return criterion(o, y)

    # Clasificación multiclase
    if yb.dtype != torch.long:
        yb = yb.long()
    return criterion(out, yb.squeeze())


def _train_loop(
    net: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    *,
    epochs: int,
    learning_rate: float,
    optimizer_name: str,
    criterion: nn.Module,
    task: str,
    metrics: str,
    device: torch.device,
) -> dict[str, Any]:
    net = net.to(device)
    opt = _optimizer(optimizer_name, net.parameters(), learning_rate)
    history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    for _ in range(epochs):
        net.train()
        total, seen = 0.0, 0
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            out = net(xb)
            loss = _compute_batch_loss(out, yb, criterion, task, metrics)
            loss.backward()
            opt.step()
            bs = xb.size(0)
            total += loss.item() * bs
            seen += bs
        history["train_loss"].append(total / max(seen, 1))

        net.eval()
        vtot, vseen = 0.0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(device)
                yb = yb.to(device)
                out = net(xb)
                loss = _compute_batch_loss(out, yb, criterion, task, metrics)
                bs = xb.size(0)
                vtot += loss.item() * bs
                vseen += bs
        history["val_loss"].append(vtot / max(vseen, 1))

    return {"history": history}


def _accuracy_batch(
    out: torch.Tensor, yb: torch.Tensor, metrics: str, task: str
) -> float:
    if task != "classification":
        return 0.0
    m = (metrics or "").lower().strip()
    if m == "binary_crossentropy":
        pred = (torch.sigmoid(out.squeeze()) > 0.5).long()
        t = yb.long().view_as(pred)
        return (pred == t).float().mean().item()
    pred = out.argmax(dim=-1)
    t = yb.long().view_as(pred)
    return (pred == t).float().mean().item()


def _evaluate_loop(
    net: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    task: str,
    metrics: str,
    device: torch.device,
) -> dict[str, Any]:
    net.eval()
    total_loss, total_acc, n = 0.0, 0.0, 0
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            out = net(xb)
            loss = _compute_batch_loss(out, yb, criterion, task, metrics)
            bs = xb.size(0)
            total_loss += loss.item() * bs
            if task == "classification":
                total_acc += _accuracy_batch(out, yb, metrics, task) * bs
            n += bs
    out_d: dict[str, Any] = {"loss": total_loss / max(n, 1)}
    if task == "classification":
        out_d["accuracy"] = total_acc / max(n, 1)
    return out_d


def _strategy_display(aggregation: str) -> str:
    m = {
        "fed_avg": "FedAvg",
        "fed_sum": "FedSum",
        "fed_weighted": "FedWeighted",
        "fed_prox": "FedProx",
    }
    return m.get((aggregation or "").lower(), aggregation or "FedAvg")


def _project_total_client_ids(project_row: dict) -> list[str]:
    raw = project_row.get("nodes") or "[]"
    if isinstance(raw, str):
        raw = json.loads(raw)
    return list(raw)


def _gather_predictions(
    net: nn.Module,
    loader: DataLoader,
    device: torch.device,
    task: str,
    metrics: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Acumula etiquetas y predicciones en el conjunto (p. ej. validación) para informes."""
    net.eval()
    ys_true: list[np.ndarray] = []
    ys_pred: list[np.ndarray] = []
    m = (metrics or "").lower().strip()
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            out = net(xb)
            if task == "regression":
                pred = out
                if pred.dim() > 1 and pred.size(-1) == 1:
                    pred = pred.squeeze(-1)
                yt = yb.float()
                if yt.dim() > 1 and yt.size(-1) == 1:
                    yt = yt.squeeze(-1)
                ys_true.append(yt.cpu().numpy())
                ys_pred.append(pred.cpu().numpy())
            else:
                if m == "binary_crossentropy":
                    pred = (torch.sigmoid(out.squeeze()) > 0.5).long()
                else:
                    pred = out.argmax(dim=-1)
                ys_true.append(yb.long().view_as(pred).cpu().numpy())
                ys_pred.append(pred.cpu().numpy())
    y_true = np.concatenate(ys_true, axis=0)
    y_pred = np.concatenate(ys_pred, axis=0)
    return y_true, y_pred


def _num_classes_from_arrays(
    y_true: np.ndarray, y_pred: np.ndarray, metadata: dict
) -> int:
    meta_labels = (metadata or {}).get("labels")
    if isinstance(meta_labels, list) and len(meta_labels) > 0:
        return len(meta_labels)
    if y_true.size == 0:
        return 1
    return int(max(np.max(y_true), np.max(y_pred))) + 1


def _class_names_for_config(n_classes: int, metadata: dict) -> list[str]:
    meta_labels = (metadata or {}).get("labels")
    if isinstance(meta_labels, list) and len(meta_labels) >= n_classes:
        return [str(x) for x in meta_labels[:n_classes]]
    return [str(i) for i in range(n_classes)]


def build_training_results_entry(
    project_row: dict,
    node_id: bytes,
    task: str,
    metrics: str,
    metadata: dict,
    params: dict,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    *,
    round_num: int,
    elapsed_seconds: float,
    global_loss: float,
    train_history: Optional[dict[str, list[float]]] = None,
    eval_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Construye un objeto compatible con ``training_results`` en BD: informes PDF,
    ``get_metrics_per_round``, ``get_time_per_round`` y ``ProjectMetricsDialog``.

    Puede serializarse con ``json.dumps`` y añadirse al array guardado en ``projects.training_results``.
    """
    node_str = _node_uuid_str(node_id)
    total_clients = _project_total_client_ids(project_row)
    if not total_clients:
        total_clients = [node_str]

    cfg: dict[str, Any] = {
        "strategy": _strategy_display(project_row.get("aggregation_strategy", "fed_avg")),
        "total_clients": total_clients,
        "epochs": int(params.get("epochs", 3)),
        "batch_size": int(params.get("batch_size", 32)),
        "learning_rate": float(params.get("learning_rate", 0.01)),
        "optimizer": str(params.get("optimizer", "adam")),
        "loss": project_row.get("metrics", "categorical_crossentropy"),
    }

    if task == "classification":
        n_classes = _num_classes_from_arrays(y_true, y_pred, metadata)
        labels = list(range(n_classes))
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        global_accuracy = float((y_true == y_pred).mean()) if y_true.size else 0.0
        cfg["classes"] = _class_names_for_config(n_classes, metadata)
        client_stats: list[dict[str, Any]] = [
            {
                "client_id": node_str,
                "confusion_matrix": cm.tolist(),
            }
        ]
        round_block: dict[str, Any] = {
            "round": round_num,
            "time": float(elapsed_seconds),
            "global_loss": float(global_loss),
            "global_accuracy": global_accuracy,
            "client_stats": client_stats,
        }
        final_metrics: dict[str, Any] = {
            "total_time_seconds": float(elapsed_seconds),
            "best_accuracy": global_accuracy,
            "y_true_final": np.asarray(y_true).astype(int).ravel().tolist(),
            "y_pred_final": np.asarray(y_pred).astype(int).ravel().tolist(),
        }
    else:
        client_stats = [
            {
                "client_id": node_str,
                "y_true": np.asarray(y_true).astype(float).ravel().tolist(),
                "y_pred": np.asarray(y_pred).astype(float).ravel().tolist(),
            }
        ]
        round_block = {
            "round": round_num,
            "time": float(elapsed_seconds),
            "global_loss": float(global_loss),
            "client_stats": client_stats,
        }
        final_metrics = {
            "total_time_seconds": float(elapsed_seconds),
            "y_true_final": np.asarray(y_true).astype(float).ravel().tolist(),
            "y_pred_final": np.asarray(y_pred).astype(float).ravel().tolist(),
        }

    entry = {
        "train_id": f"local_{uuid.uuid4()}",
        "config": cfg,
        "results_per_round": [round_block],
        "final_metrics": final_metrics,
    }
    if train_history is not None:
        entry["train_history"] = train_history
    if eval_result is not None:
        entry["eval_snapshot"] = eval_result
    return entry


def merge_project_training_results(
    existing: Optional[str | list],
    new_entry: dict[str, Any],
) -> str:
    """
    Añade ``new_entry`` al array JSON almacenado en ``projects.training_results``.
    ``existing`` puede ser el string JSON actual, una lista ya parseada o vacío.
    """
    if existing is None or existing == "":
        arr: list = []
    elif isinstance(existing, str):
        arr = json.loads(existing) if existing.strip() else []
    else:
        arr = list(existing)
    arr.append(new_entry)
    return json.dumps(arr, ensure_ascii=False)


def _tensor_from_predict_input(
    input_data: Any, input_features: list[str]
) -> torch.Tensor:
    if isinstance(input_data, torch.Tensor):
        t = input_data.float()
        return t.unsqueeze(0) if t.dim() == 1 else t

    if isinstance(input_data, (list, tuple)):
        vals = [float(x) for x in input_data]
        return torch.tensor([vals], dtype=torch.float32)

    if isinstance(input_data, dict):
        row = [float(input_data[name]) for name in input_features]
        return torch.tensor([row], dtype=torch.float32)

    raise TypeError(
        "input_data debe ser dict {nombre: valor}, lista de valores por orden de "
        "input_features, o un tensor."
    )


def _format_prediction(
    raw: torch.Tensor,
    feats: dict,
    task: str,
) -> dict[str, Any]:
    if raw.dim() >= 2 and raw.size(0) > 1:
        raw = raw[0:1]

    meta = feats.get("metadata") if isinstance(feats.get("metadata"), dict) else {}
    out_features = feats.get("output_features") or ["output"]
    names = out_features
    if task == "regression":
        vec = raw.squeeze().detach().cpu().numpy()
        return {
            "type": "regression",
            "output": vec.tolist() if vec.ndim > 0 else float(vec),
            "output_info": {"names": names, "dtype": ["float"] * len(names)},
        }

    m = (meta.get("labels") if meta else None) or []
    logits = raw.squeeze(0) if raw.dim() > 1 else raw
    idx = int(logits.argmax(-1).item()) if logits.dim() > 0 else int(logits.item())
    probs = F.softmax(logits, dim=-1).detach().cpu().numpy().tolist()
    label = m[idx] if m and idx < len(m) else idx
    return {
        "type": "classification",
        "output": idx,
        "labels": list(m) if m else [],
        "probabilities": probs,
        "output_info": {
            "names": names[:1],
            "dtype": ["str"] if m else ["int"],
        },
        "label": label,
    }


def flower_local_config(project_row: dict) -> dict[str, Any]:
    """
    Parámetros locales útiles para alinear con ``config`` en Flower (p. ej. simulaciones).

    No ejecuta Flower; solo devuelve un diccionario coherente con ``Project.parameters``.
    """
    params = project_row["parameters"]
    if isinstance(params, str):
        params = json.loads(params)
    return {
        "local_epochs": int(params.get("epochs", 3)),
        "batch_size": int(params.get("batch_size", 32)),
        "learning_rate": float(params.get("learning_rate", 0.01)),
        "optimizer": str(params.get("optimizer", "adam")),
        "validation_split": float(params.get("validation_split", 0.2)),
        "metrics": project_row.get("metrics", "categorical_crossentropy"),
        "aggregation_strategy": project_row.get("aggregation_strategy", "fed_avg"),
    }


def train(
    node: "Node",
    project: Optional[dict] = None,
    *,
    csv_path: Optional[Path | str] = None,
    seed: int = 0,
) -> dict[str, Any]:
    """
    Entrena el modelo del proyecto con el dataset local del nodo (paso local tipo ``Client.fit``).

    Returns
    -------
    dict con ``num_examples_train``, ``num_examples_val``, ``config``, ``history``,
    ``training_time_seconds``, ``training_results_entry`` (formato listo para
    ``projects.training_results`` / informes / vista de métricas) y ``model_path``.
    """
    project_row = project or _fetch_project_for_node(node.id)
    params = project_row["parameters"]
    if isinstance(params, str):
        params = json.loads(params)

    path = Path(csv_path) if csv_path else _dataset_csv_path(node.id, project_row)
    model, model_path = _instantiate_model(project_row)
    feats = model.get_features()
    metadata = feats.get("metadata") if isinstance(feats.get("metadata"), dict) else {}

    in_features = json.loads(project_row["input_features"]) if isinstance(
        project_row["input_features"], str
    ) else project_row["input_features"]
    out_features = json.loads(project_row["output_features"]) if isinstance(
        project_row["output_features"], str
    ) else project_row["output_features"]

    metrics = project_row.get("metrics", "categorical_crossentropy")
    task = metadata.get("type") or _task_kind(metrics)

    X, y, _enc = _load_xy_from_csv(
        path, in_features, out_features, metrics, metadata
    )
    train_loader, val_loader = _make_loaders(
        X,
        y,
        batch_size=int(params.get("batch_size", 32)),
        validation_split=float(params.get("validation_split", 0.2)),
        task=task,
        seed=seed,
    )

    net = model.load_model(model_path)
    device = _get_device()
    crit = _criterion(metrics, task)
    t0 = time.perf_counter()
    hist = _train_loop(
        net,
        train_loader,
        val_loader,
        epochs=int(params.get("epochs", 3)),
        learning_rate=float(params.get("learning_rate", 0.01)),
        optimizer_name=str(params.get("optimizer", "adam")),
        criterion=crit,
        task=task,
        metrics=metrics,
        device=device,
    )
    elapsed = time.perf_counter() - t0
    val_losses = hist.get("history", {}).get("val_loss", [])
    global_loss = float(val_losses[-1]) if val_losses else 0.0

    y_true, y_pred = _gather_predictions(net, val_loader, device, task, metrics)
    round_num = int(project_row.get("training_round") or 0)
    training_results_entry = build_training_results_entry(
        project_row,
        node.id,
        task,
        metrics,
        metadata,
        params,
        y_true,
        y_pred,
        round_num=round_num,
        elapsed_seconds=elapsed,
        global_loss=global_loss,
        train_history=hist.get("history"),
    )

    return {
        "num_examples_train": len(train_loader.dataset),
        "num_examples_val": len(val_loader.dataset),
        "config": flower_local_config(project_row),
        "model_path": model_path,
        "training_time_seconds": elapsed,
        "training_results_entry": training_results_entry,
        **hist,
    }


def evaluate(
    node: "Node",
    project: Optional[dict] = None,
    *,
    csv_path: Optional[Path | str] = None,
    seed: int = 0,
) -> dict[str, Any]:
    """
    Evalúa el modelo en el conjunto de validación obtenido del mismo CSV (tipo ``Client.evaluate``).

    Returns
    -------
    dict con ``num_examples``, ``loss``, ``result``, ``evaluation_time_seconds``,
    ``training_results_entry`` (misma forma que tras ``train``, útil para informes)
    y ``model_path``.
    """
    project_row = project or _fetch_project_for_node(node.id)
    params = project_row["parameters"]
    if isinstance(params, str):
        params = json.loads(params)

    path = Path(csv_path) if csv_path else _dataset_csv_path(node.id, project_row)
    model, model_path = _instantiate_model(project_row)
    feats = model.get_features()
    metadata = feats.get("metadata") if isinstance(feats.get("metadata"), dict) else {}

    in_features = json.loads(project_row["input_features"]) if isinstance(
        project_row["input_features"], str
    ) else project_row["input_features"]
    out_features = json.loads(project_row["output_features"]) if isinstance(
        project_row["output_features"], str
    ) else project_row["output_features"]

    metrics = project_row.get("metrics", "categorical_crossentropy")
    task = metadata.get("type") or _task_kind(metrics)

    X, y, _enc = _load_xy_from_csv(
        path, in_features, out_features, metrics, metadata
    )
    _, val_loader = _make_loaders(
        X,
        y,
        batch_size=int(params.get("batch_size", 32)),
        validation_split=float(params.get("validation_split", 0.2)),
        task=task,
        seed=seed,
    )

    net = model.load_model(model_path)
    device = _get_device()
    crit = _criterion(metrics, task)
    t0 = time.perf_counter()
    raw = _evaluate_loop(net, val_loader, crit, task, metrics, device)
    elapsed = time.perf_counter() - t0

    y_true, y_pred = _gather_predictions(net, val_loader, device, task, metrics)
    round_num = int(project_row.get("training_round") or 0)
    training_results_entry = build_training_results_entry(
        project_row,
        node.id,
        task,
        metrics,
        metadata,
        params,
        y_true,
        y_pred,
        round_num=round_num,
        elapsed_seconds=elapsed,
        global_loss=float(raw.get("loss", 0.0)),
        eval_result=raw,
    )

    out: dict[str, Any] = {
        "num_examples": len(val_loader.dataset),
        "result": raw,
        "loss": raw.get("loss"),
        "config": flower_local_config(project_row),
        "model_path": model_path,
        "evaluation_time_seconds": elapsed,
        "training_results_entry": training_results_entry,
    }
    return out


def predict(
    node: "Node",
    input_data: Any,
    project: Optional[dict] = None,
) -> Any:
    """
    Inferencia local con el ``nn.Module`` del proyecto.

    ``input_data`` puede ser un ``dict`` ``{nombre_columna: valor}``, una lista de valores
    en el orden de ``input_features``, o un tensor (filas = batch).
    """
    project_row = project or _fetch_project_for_node(node.id)
    model, model_path = _instantiate_model(project_row)
    feats = model.get_features()
    metadata = feats.get("metadata") if isinstance(feats.get("metadata"), dict) else {}
    metrics = project_row.get("metrics", "categorical_crossentropy")
    task = metadata.get("type") or _task_kind(metrics)

    in_features = json.loads(project_row["input_features"]) if isinstance(
        project_row["input_features"], str
    ) else project_row["input_features"]

    net = model.load_model(model_path)
    device = _get_device()
    net = net.to(device)
    net.eval()
    x = _tensor_from_predict_input(input_data, in_features).to(device)
    with torch.no_grad():
        out = net(x)
    return _format_prediction(out, feats, task)


class Node:
    def __init__(self, id, valid, project_id):
        self.id = id
        self.valid = valid
        self.project_id = project_id
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.local_dataset_path = os.path.join(
            BASE_DIR, "..", "..", "database", "datasets", "node_" + str(uuid.UUID(bytes=id))
        )

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        else:
            raise KeyError(item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def to_dict(self):
        return {
            "id": self.id,
            "valid": self.valid,
            "project_id": self.project_id,
            "local_dataset_path": self.local_dataset_path,
        }

    def train(self, project: Optional[dict] = None, **kwargs: Any) -> dict[str, Any]:
        """Delega en :func:`train`."""
        return train(self, project=project, **kwargs)

    def evaluate(self, project: Optional[dict] = None, **kwargs: Any) -> dict[str, Any]:
        """Delega en :func:`evaluate`."""
        return evaluate(self, project=project, **kwargs)

    def predict(self, input_data: Any, project: Optional[dict] = None) -> Any:
        """Delega en :func:`predict`."""
        return predict(self, input_data, project=project)
