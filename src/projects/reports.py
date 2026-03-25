from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, r2_score

import io
import numpy as np
from collections import Counter
import json
from datetime import datetime

"""
Clasificación:
[
  "train_id": "exp_001",
  "config": 
    {
      "strategy": "FedAvg", 
      "total_clients": [...], 
      "epochs": 3, 
      "batch_size": 32, 
      "learning_rate": 0.001, 
      "optimizer": "Adam", 
      "classes": [...], 
      "loss": "categorical_crossentropy"
    },
  "results_per_round": [
    {
      "round": 1,
      "global_loss": 2.45,
      "global_accuracy": 0.15,
      "client_stats": [
        {
          "client_id": 1,
          "confusion_matrix": [[10, 20, 30], [40, 50, 60], [70, 80, 90]]
        },
        {
          "client_id": 2,
          "confusion_matrix": [[10, 20, 30], [40, 50, 60], [70, 80, 90]]
        }
      ]
    },
    {
      "round": 2,
      "global_loss": 1.80,
      "global_accuracy": 0.42,
      "client_stats": [
        {
          "client_id": 1,
          "confusion_matrix": [[10, 20, 30], [40, 50, 60], [70, 80, 90]]
        },
        {
          "client_id": 2,
          "confusion_matrix": [[10, 20, 30], [40, 50, 60], [70, 80, 90]]
        }
      ]
    }
  ],
  "final_metrics": {
    "total_time_seconds": 1200,
    "y_true_final": [...], 
    "y_pred_final": [...]
  }
]
"""

"""
Regresión:
[
  "train_id": "exp_001",
  "config": 
    {
      "strategy": "FedAvg", 
      "total_clients": [...], 
      "epochs": 3, 
      "batch_size": 32, 
      "learning_rate": 0.001, 
      "optimizer": "Adam",
      "loss": "mse"
    },
  "results_per_round": [
    {
      "round": 1,
      "global_loss": 2.45,
      "client_stats": [
        {
          "client_id": 1,
          "y_pred": [30, 5, ...],
          "y_true": [30, 0, ...]
        },
        {
          "client_id": 2,
          "y_pred": [10, 20, ...],
          "y_true": [10, 0, ...]
        }
      ]
    },
    {
      "round": 2,
      "global_loss": 1.80,
      "client_stats": [
        {
          "client_id": 1,
          "y_pred": [10, 20, ...],
          "y_true": [10, 0, ...]
        },
        {
          "client_id": 2,
          "y_pred": [10, 20, ...],
          "y_true": [10, 0, ...]
        }
      ]
    }
  ],
  "final_metrics": {
    "total_time_seconds": 1200,
    "y_true_final": [...], 
    "y_pred_final": [...]  
  }
]
"""


def generate_report(project_id, project_name, project_description, num_rounds, project_type, data, path):
    data = json.loads(data) # loads every training result

    if not data or len(data) == 0:
        raise ValueError("No data to generate report")

    if project_type != "classification" and project_type != "regression":
        raise ValueError("Invalid report type")
    
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"Reporte de resultados del proyecto {project_name}", styles["Title"]))
    story.append(Spacer(1, 12))

    # Info
    story.append(Paragraph("Información general", styles["Heading1"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"ID del proyecto: {project_id}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Descripción del proyecto: {project_description}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Tipo de proyecto: {project_type}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Número de entrenamientos: {len(data)}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Número de rondas: {num_rounds}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Configuración:", style=styles["Heading2"]))
    story.append(Spacer(1, 6))
    config = []
    config.append(ListItem(Paragraph(f"Estrategia de agregación: {data[0]['config']['strategy']}", styles["BodyText"])))
    config.append(ListItem(Paragraph(f"Número de épocas: {data[0]['config']['epochs']}", styles["BodyText"])))
    config.append(ListItem(Paragraph(f"Tamaño del lote: {data[0]['config']['batch_size']}", styles["BodyText"])))
    config.append(ListItem(Paragraph(f"Tasa de aprendizaje: {data[0]['config']['learning_rate']}", styles["BodyText"])))
    config.append(ListItem(Paragraph(f"Optimizador: {data[0]['config']['optimizer']}", styles["BodyText"])))
    config.append(ListItem(Paragraph(f"Función de pérdida: {data[0]['config']['loss']}", styles["BodyText"])))
    if project_type == "classification":
        config.append(ListItem(Paragraph(f"Clases: {data[0]['config']['classes']}", styles["BodyText"])))
    story.append(ListFlowable(config, bulletType="bullet"))
    story.append(Spacer(1, 24))

    # Training results
    story.append(Paragraph("Entrenamientos", styles["Heading1"]))
    story.append(Spacer(1, 6))

    for idx, train in enumerate(data):
        train_id = train["train_id"]
        strategy = train["config"]["strategy"]
        total_clients = train["config"]["total_clients"]
        results_per_round = train["results_per_round"]
        final_metrics = train["final_metrics"]
        if project_type == "classification":
            classes = train["config"]["classes"]
            story = generate_classification_report(story, train_id, strategy, total_clients, results_per_round, final_metrics, classes, path, idx)
        elif project_type == "regression":
            story = generate_regression_report(story, train_id, strategy, total_clients, results_per_round, final_metrics, path, idx)
        else:
            raise ValueError("Invalid report type")

    doc.build(story)

def add_training_head(story, idx, train_id, strategy, total_clients, styles):
    story.append(Paragraph(f"Entrenamiento {idx + 1}", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"ID del entrenamiento: {train_id}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Estrategia de agregación: {strategy}", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Número total de nodos: {len(total_clients)}", styles["BodyText"]))
    story.append(Spacer(1, 6))

    # Nodos
    story.append(Paragraph("Nodos", styles["Heading3"]))
    story.append(Spacer(1, 6))
    nodes = []
    for node_id in total_clients:
        nodes.append(ListItem(Paragraph(f"Nodo {node_id}", styles["BodyText"])))
    story.append(ListFlowable(nodes, bulletType="bullet"))
    story.append(Spacer(1, 6))

    # Results per round
    story.append(Paragraph("Resultados por ronda", styles["Heading3"]))
    story.append(Spacer(1, 6))

    return story

def generate_classification_report(story, train_id, strategy, total_clients, results_per_round, final_metrics, classes, path, idx):
    styles = getSampleStyleSheet()

    story = add_training_head(story, idx, train_id, strategy, total_clients, styles)
    
    for result in results_per_round:
        stats = []
        story.append(Paragraph(f"<b>Ronda {result['round']}</b>", styles["BodyText"]))
        stats.append(ListItem(Paragraph(f"Pérdida global: {result['global_loss']}", styles["BodyText"])))
        stats.append(ListItem(Paragraph(f"Precisión global: {result['global_accuracy']}", styles["BodyText"])))   
        story.append(ListFlowable(stats, bulletType="bullet"))
    story.append(Spacer(1, 6))

    # Table with precision, recall and f1_score for each node and each class
    story.append(Paragraph("Precisión, recall y f1_score por nodo y por clase", styles["Heading3"]))
    story.append(Spacer(1, 6))
    table_data = [["Nodo", "Clase", "Precisión", "Recall", "F1_score"]]
    confusion_matrix = [[0 for _ in range(len(classes))] for _ in range(len(classes))]
    confusion_matrix_per_client = {}
    for client in total_clients:
        precision, recall, f1_score, total_confusion_matrix = get_precision_recall_f1score(client, results_per_round, classes)
        for class_name in precision.keys():
            table_data.append([client, class_name, precision[class_name], recall[class_name], f1_score[class_name]])
        for i in range(len(classes)):
            for j in range(len(classes)):
                confusion_matrix[i][j] += total_confusion_matrix[i][j]
        confusion_matrix_per_client[client] = total_confusion_matrix
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    
    story.append(Paragraph("Matriz de confusión", styles["Heading3"]))
    story.append(Spacer(1, 6))

    # Table with confusion matrix
    table_data = [["Clase"] + classes]
    for i in range(len(classes)):
        row = [classes[i]]
        for j in range(len(classes)):
            row.append(confusion_matrix[i][j])
        table_data.append(row)
    
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    max_val = max(max(row) for row in confusion_matrix)
    for i in range(len(classes)):
        for j in range(len(classes)):
            val = confusion_matrix[i][j]
            color = get_color_intensity(val, max_val)
            table_styles.append(('BACKGROUND', (j + 1, i + 1), (j + 1, i + 1), color))
            if val > max_val * 0.7:
                table_styles.append(('TEXTCOLOR', (j + 1, i + 1), (j + 1, i + 1), colors.whitesmoke))

    table = Table(table_data)
    table.setStyle(TableStyle(table_styles))
    story.append(table)
    story.append(Spacer(1, 6))

    # Class distribution per node
    story.append(Paragraph("Distribución de clases por nodo", styles["Heading3"]))
    story.append(Spacer(1, 6))
    cols = ["Nodo"] + classes
    table_data = [cols]
    for node in total_clients:
        row = [node]
        for n_class, class_name in enumerate(classes):
            row.append(sum(confusion_matrix_per_client[node][n_class][j] for j in range(len(classes))))
        table_data.append(row)
    
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    col_maxima = []
    for c in range(1, len(cols)):
        valores_columna = [fila[c] for fila in table_data[1:]] # Ignoramos la cabecera
        col_maxima.append(max(valores_columna) if valores_columna else 1)
    
    for row_idx, row in enumerate(table_data[1:], start=1):
        for col_idx, valor in enumerate(row[1:], start=1):
            max_val = col_maxima[col_idx - 1]
            color = get_color_intensity(valor, max_val)
            
            table_styles.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), color))
            
            if (valor / max_val if max_val > 0 else 0) > 0.7:
                table_styles.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.whitesmoke))

    table = Table(table_data)
    table.setStyle(TableStyle(table_styles))
    story.append(table)
    story.append(Spacer(1, 6))

    story.append(Paragraph(f"Conclusiones del entrenamiento {idx + 1}", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Tiempo total del entrenamiento: {final_metrics['total_time_seconds']} segundos", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Comparativa de frecuencias: Real vs Predicho:</b>", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(get_distribution_plot(final_metrics['y_true_final'], final_metrics['y_pred_final'], classes))
    story.append(Spacer(1, 6))
    
    
    return story
    

def generate_regression_report(story, train_id, strategy, total_clients, results_per_round, final_metrics, path, idx):
    styles = getSampleStyleSheet()
    story = add_training_head(story, idx, train_id, strategy, total_clients, styles)

    for result in results_per_round:
      stats = []

      story.append(Paragraph(f"Ronda {result['round']}", styles["Heading3"]))
      stats.append(ListItem(Paragraph(f"Pérdida global: {result['global_loss']}", styles["BodyText"])))
      total_y_true = []
      total_y_pred = []
      for c in result["client_stats"]:
        total_y_true.extend(c["y_true"])
        total_y_pred.extend(c["y_pred"])
      stats.append(ListItem(Paragraph(f"Error absoluto medio: {mean_absolute_error(total_y_true, total_y_pred)}")))
      stats.append(ListItem(Paragraph(f"Puntuación R<sup>2</sup>: {r2_score(total_y_true, total_y_pred)}")))
      story.append(ListFlowable(stats, bulletType="bullet"))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Conclusiones del entrenamiento", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Tiempo total del entrenamiento: {final_metrics['total_time_seconds']} segundos", styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(get_scatter_plot(total_y_true, total_y_pred))
    story.append(Spacer(1, 6))
    story.append(get_residuals_histogram(total_y_true, total_y_pred))
    story.append(Spacer(1, 6))
    
    return story


def get_scatter_plot(y_true, y_pred):
    fig, ax = plt.subplots(figsize=(6, 6))
    
    ax.scatter(y_true, y_pred, alpha=0.5, color='#4A90E2', edgecolors='white', label='Predicciones')
    
    lims = [
        min(min(y_true), min(y_pred)),
        max(max(y_true), max(y_pred)),
    ]
    ax.plot(lims, lims, color='#FF6B6B', linestyle='--', linewidth=2, label='Ideal ($y=x$)')
    
    ax.set_aspect('equal')
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    
    ax.set_xlabel('Valores Reales')
    ax.set_ylabel('Predicciones del Modelo')
    ax.set_title('Gráfico de Dispersión: Real vs. Predicho')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.6)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
    img_buffer.seek(0)
    plt.close(fig)
    
    return Image(img_buffer, width=350, height=350)

def get_residuals_histogram(y_true, y_pred):
    residuos = np.array(y_true) - np.array(y_pred)
    
    fig, ax = plt.subplots(figsize=(7, 4))
    
    n, bins, patches = ax.hist(residuos, bins=30, color='#6BCB77', edgecolor='white', alpha=0.8)
    
    ax.axvline(0, color='#FF6B6B', linestyle='--', linewidth=2, label='Error 0')
    
    ax.set_xlabel('Valor del Error (Real - Predicho)')
    ax.set_ylabel('Frecuencia de Apariciones')
    ax.set_title('Distribución de Residuos (Análisis de Sesgo)')
    ax.legend()
    ax.grid(axis='y', linestyle=':', alpha=0.6)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
    img_buffer.seek(0)
    plt.close(fig)
    
    return Image(img_buffer, width=450, height=250)

def get_precision_recall_f1score(client, results_per_round, classes):
    confusion_matrix = [[0 for _ in range(len(classes))] for _ in range(len(classes))]

    for result in results_per_round:
        for c in result["client_stats"]: 
            if c["client_id"] == client:
                for i in range(len(classes)):
                    for j in range(len(classes)):
                        confusion_matrix[i][j] += c["confusion_matrix"][i][j]
    
    precision = {}
    recall = {}
    f1_score = {}
    
    for i in range(len(classes)):
        if sum(confusion_matrix[i]) == 0:
            precision[classes[i]] = 0
            recall[classes[i]] = 0
            f1_score[classes[i]] = 0
            continue
        precision[classes[i]] = confusion_matrix[i][i] / sum(confusion_matrix[i])
        if sum(confusion_matrix[j][i] for j in range(len(classes))) == 0:
            recall[classes[i]] = 0
            f1_score[classes[i]] = 0
            continue
        recall[classes[i]] = confusion_matrix[i][i] / sum(confusion_matrix[j][i] for j in range(len(classes)))
        if precision[classes[i]] + recall[classes[i]] == 0:
            f1_score[classes[i]] = 0
            continue
        f1_score[classes[i]] = 2 * precision[classes[i]] * recall[classes[i]] / (precision[classes[i]] + recall[classes[i]])
    
    return precision, recall, f1_score, confusion_matrix

def get_distribution_plot(y_true, y_pred, classes):
    true_counts = Counter(y_true)
    pred_counts = Counter(y_pred)
    
    x = range(len(classes))
    true_vals = [true_counts.get(i, 0) for i in x]
    pred_vals = [pred_counts.get(i, 0) for i in x]

    fig, ax = plt.subplots(figsize=(6, 4))
    width = 0.35
    ax.bar([i - width/2 for i in x], true_vals, width, label='Real', color='#4A90E2')
    ax.bar([i + width/2 for i in x], pred_vals, width, label='Predicho', color='#FF6B6B')

    ax.set_ylabel('Cantidad de Muestras')
    ax.set_title('Distribución de Clases: Real vs. Predicho')
    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.legend()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150)
    img_buffer.seek(0)
    plt.close(fig)
    
    return Image(img_buffer, width=400, height=250)

def get_color_intensity(value, max_value):
    if max_value == 0: return colors.whitesmoke
    intensity = float(value) / max_value
    return colors.Color(1 - intensity, 1 - intensity, 1, alpha=1)