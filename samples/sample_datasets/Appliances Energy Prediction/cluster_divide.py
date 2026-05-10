import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

def create_federated_appliances_dataset(n_clients=7):
    df = pd.read_csv("energydata_complete.csv")
    
    cluster_features = ["T1", "RH_1", "T2", "RH_2", "T_out", "RH_out"]
    cluster_scaler = StandardScaler()
    scaled_for_clustering = cluster_scaler.fit_transform(df[cluster_features])

    print(f"Agrupando datos en {n_clients} clusters...")
    kmeans = KMeans(n_clusters=n_clients, random_state=42, n_init=10)
    df["client_id"] = kmeans.fit_predict(scaled_for_clustering)

    # Escalado de las variables numéricas
    features_to_scale = [c for c in df.columns if c not in ['date', 'client_id']]
    data_scaler = MinMaxScaler()
    df[features_to_scale] = data_scaler.fit_transform(df[features_to_scale])

    plt.figure(figsize=(16, 6))
    plt.subplot(1, 3, 1)
    sns.countplot(x='client_id', data=df, palette='viridis')
    plt.title('Muestras por Cliente')

    plt.subplot(1, 3, 2)
    pca = PCA(n_components=2)
    pca_data = pca.fit_transform(scaled_for_clustering)
    plt.scatter(pca_data[:, 0], pca_data[:, 1], c=df['client_id'], cmap='viridis', s=1, alpha=0.5)
    plt.title('Clusters (PCA 2D)')

    plt.subplot(1, 3, 3)
    sns.boxplot(x='client_id', y='Appliances', data=df, palette='viridis')
    plt.title('Consumo Escalado [0,1] por Cliente')

    plt.tight_layout()
    plt.show()

    output_dir = "federated_appliances_data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Guardando archivos escalados por cliente...")
    for client_id in range(n_clients):
        client_data = df[df["client_id"] == client_id].copy()
        client_data = client_data.drop(columns=["date", "client_id"])
        
        cols = [c for c in client_data.columns if c != "Appliances"] + ["Appliances"]
        client_data = client_data[cols]
        
        file_path = os.path.join(output_dir, f"client_{client_id}.csv")
        client_data.to_csv(file_path, index=False)
        print(f"  -> {file_path} | Muestras: {len(client_data)}")

    print("\nDatos particionados y escalados con éxito.")

if __name__ == "__main__":
    create_federated_appliances_dataset(n_clients=7)