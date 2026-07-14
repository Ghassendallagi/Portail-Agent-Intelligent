"""Module ML-3 : profilage comportemental des agents (clustering K-Means).

Regroupe les gestionnaires en profils comportementaux homogenes a partir
de leurs statistiques de traitement. Alimente le champ
Profil_Comportemental_ML dans la liste Agents de SharePoint.
"""

import os

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "demandes_dataset_final.csv")
DATA_V2_PATH = os.path.join(PROJECT_ROOT, "data", "demandes_dataset_final_v2.csv")
ELBOW_PLOT_PATH = os.path.join(PROJECT_ROOT, "data", "elbow_curve.png")
PROFILS_PATH = os.path.join(PROJECT_ROOT, "data", "profils_gestionnaires.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "model_clustering.pkl")
SCALER_PATH = os.path.join(PROJECT_ROOT, "models", "scaler_clustering.pkl")

FEATURE_COLS = [
    "nb_demandes", "delai_moyen_h", "delai_median_h", "taux_retard",
    "taux_rejet", "delai_assignation_moyen_h", "nb_transferts_moyen", "diversite_types",
]


# =========================================================
# ETAPE 0 : coherence gestionnaire / service
# =========================================================
def fix_gestionnaire_service_coherence(path=DATA_PATH, out_path=DATA_V2_PATH, seed=42):
    """Reaffecte, pour les lignes synthetiques, le Gestionnaire a un gestionnaire
    reel dont le service reel correspond au Service de la demande. Laisse
    'Inconnu' si aucun gestionnaire reel n'existe pour ce service."""
    rng = np.random.default_rng(seed)
    df = pd.read_csv(path, encoding="utf-8")
    reel_mask = df["Source"] == "reel"

    service_to_gestionnaires = {}
    for service, gestionnaire in df.loc[reel_mask, ["Service", "Gestionnaire"]].drop_duplicates().itertuples(index=False):
        service_to_gestionnaires.setdefault(service, []).append(gestionnaire)

    print("=== Gestionnaires reels par service ===")
    for service, gestionnaires in service_to_gestionnaires.items():
        print(f"  {service}: {gestionnaires}")

    services_sans = sorted(set(df["Service"].unique()) - set(service_to_gestionnaires.keys()))
    if services_sans:
        print(f"Services sans gestionnaire reel (-> 'Inconnu'): {services_sans}")
    else:
        print("Tous les services ont au moins un gestionnaire reel associe.")

    def reassign(row):
        if row["Source"] != "synthetique":
            return row["Gestionnaire"]
        candidates = service_to_gestionnaires.get(row["Service"])
        if not candidates:
            return "Inconnu"
        return rng.choice(candidates)

    old_gestionnaire = df["Gestionnaire"].copy()
    df["Gestionnaire"] = df.apply(reassign, axis=1)
    n_changed = ((df["Source"] == "synthetique") & (df["Gestionnaire"] != old_gestionnaire)).sum()

    print(f"\nGestionnaires synthetiques reassignes: {n_changed} / {(df['Source'] == 'synthetique').sum()}")
    print(f"Gestionnaire = 'Inconnu' apres correction: {(df['Gestionnaire'] == 'Inconnu').sum()} lignes")

    df.to_csv(out_path, encoding="utf-8", sep=",", index=False)
    print(f"Sauvegarde: {out_path}")
    return df


# =========================================================
# ETAPE 1 : agregation par gestionnaire
# =========================================================
def aggregate_by_gestionnaire(df):
    df = df.loc[df["Gestionnaire"] != "Inconnu"].copy()

    grouped = df.groupby("Gestionnaire").agg(
        nb_demandes=("Gestionnaire", "size"),
        delai_moyen_h=("Delai_Traitement_Heures", "mean"),
        delai_median_h=("Delai_Traitement_Heures", "median"),
        taux_retard=("En_Retard", "mean"),
        taux_rejet=("Statut_Final", lambda s: (s == "Rejeté").mean()),
        delai_assignation_moyen_h=("Delai_Assignation_Heures", "mean"),
        nb_transferts_moyen=("Nb_Transferts", "mean"),
        diversite_types=("Type_Demande", "nunique"),
    ).reset_index()

    service_mode = (
        df.groupby("Gestionnaire")["Service"]
        .agg(lambda s: s.value_counts().idxmax())
        .reset_index()
        .rename(columns={"Service": "Service"})
    )
    grouped = grouped.merge(service_mode, on="Gestionnaire")
    return grouped


# =========================================================
# ETAPE 3 : choix de k (coude + silhouette)
# =========================================================
def choose_k(X_scaled, k_max):
    ks = list(range(2, k_max + 1))
    inertias, silhouettes = [], []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X_scaled, labels))
        print(f"  k={k}: inertie={km.inertia_:.2f}, silhouette={silhouettes[-1]:.4f}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(ks, inertias, marker="o")
    axes[0].set_xlabel("k")
    axes[0].set_ylabel("Inertie (within-cluster SSE)")
    axes[0].set_title("Methode du coude")

    axes[1].plot(ks, silhouettes, marker="o", color="darkorange")
    axes[1].set_xlabel("k")
    axes[1].set_ylabel("Silhouette Score")
    axes[1].set_title("Silhouette Score")

    fig.tight_layout()
    fig.savefig(ELBOW_PLOT_PATH, dpi=120)
    plt.close(fig)

    k_optimal = ks[int(np.argmax(silhouettes))]
    return k_optimal, ks, inertias, silhouettes


# =========================================================
# ETAPE 4 : nommage des profils (data-driven, pas de labels forces)
# =========================================================
def name_clusters(grouped):
    """Attribue un nom de profil metier a chaque cluster en comparant ses
    moyennes a la moyenne des AUTRES clusters (pas a la moyenne globale,
    trop sensible aux outliers avec peu d'individus). Regles evaluees par
    ordre de priorite metier ; la premiere qui matche est retenue."""
    cluster_means = grouped.groupby("Cluster")[FEATURE_COLS].mean()
    cluster_sizes = grouped.groupby("Cluster").size()
    labels = {}

    for cid in cluster_means.index:
        this_mean = cluster_means.loc[cid]
        other_clusters = [c for c in cluster_means.index if c != cid]
        other_weights = cluster_sizes.loc[other_clusters]
        other_mean = (cluster_means.loc[other_clusters].mul(other_weights, axis=0).sum() / other_weights.sum())

        if this_mean["taux_retard"] > max(other_mean["taux_retard"] * 1.5, 0.01) and this_mean["taux_retard"] > 0.3:
            label = "À risque"
        elif this_mean["delai_moyen_h"] < other_mean["delai_moyen_h"] * 0.7 and this_mean["taux_retard"] <= other_mean["taux_retard"]:
            label = "Efficace"
        elif this_mean["nb_demandes"] > other_mean["nb_demandes"] * 1.3 and this_mean["delai_moyen_h"] > other_mean["delai_moyen_h"]:
            label = "Surchargé"
        elif this_mean["nb_demandes"] < other_mean["nb_demandes"] * 0.7 and this_mean["taux_rejet"] == 0:
            label = "Prudent"
        else:
            label = f"Profil {cid}"

        labels[cid] = label

    return labels, cluster_means


def train_and_evaluate():
    fix_gestionnaire_service_coherence()

    df = pd.read_csv(DATA_V2_PATH, encoding="utf-8")
    grouped = aggregate_by_gestionnaire(df)

    print(f"\n=== TABLEAU AGREGE PAR GESTIONNAIRE (n={grouped.shape[0]}) ===")
    print(grouped.to_string(index=False))

    if grouped.shape[0] < 10:
        print(f"\nATTENTION: seulement {grouped.shape[0]} gestionnaires -- "
              f"K-Means sur si peu d'individus est fragile, on continue pour la demonstration.")

    X = grouped[FEATURE_COLS].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    k_max = min(6, grouped.shape[0] - 1)
    print(f"\n=== CHOIX DE k (coude + silhouette), k=2..{k_max} ===")
    k_optimal, ks, inertias, silhouettes = choose_k(X_scaled, k_max)
    print(f"\nk_optimal retenu (max silhouette) = {k_optimal}")
    print(f"Courbes sauvegardees: {ELBOW_PLOT_PATH}")

    kmeans = KMeans(n_clusters=k_optimal, random_state=42, n_init=10)
    grouped["Cluster"] = kmeans.fit_predict(X_scaled)

    labels_map, cluster_means = name_clusters(grouped)
    grouped["Profil_Label"] = grouped["Cluster"].map(labels_map)

    print("\n=== MOYENNES DES FEATURES PAR CLUSTER ===")
    display_means = cluster_means.copy()
    display_means["Profil_Label"] = display_means.index.map(labels_map)
    display_means["n_gestionnaires"] = grouped.groupby("Cluster").size()
    print(display_means.to_string())

    print("\n=== GESTIONNAIRE -> CLUSTER / PROFIL ===")
    print(grouped[["Gestionnaire", "Service", "nb_demandes", "delai_moyen_h",
                   "taux_retard", "Cluster", "Profil_Label"]].sort_values("Cluster").to_string(index=False))

    # --- sauvegardes ---
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(kmeans, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    model_size_kb = os.path.getsize(MODEL_PATH) / 1024
    scaler_size_kb = os.path.getsize(SCALER_PATH) / 1024
    print(f"\n=== MODELES SAUVEGARDES ===")
    print(f"{MODEL_PATH} ({model_size_kb:.1f} Ko)")
    print(f"{SCALER_PATH} ({scaler_size_kb:.1f} Ko)")

    profils_out = grouped[["Gestionnaire", "Service", "nb_demandes", "delai_moyen_h",
                            "taux_retard", "taux_rejet", "Cluster", "Profil_Label"]]
    profils_out.to_csv(PROFILS_PATH, encoding="utf-8", sep=",", index=False)
    print(f"Profils sauvegardes: {PROFILS_PATH}")

    return grouped, kmeans, scaler, labels_map


def predict_profil_agent(gestionnaire: str, profils_df=None, df_v2=None) -> dict:
    """Retourne le profil comportemental d'un gestionnaire.

    - cluster (int)
    - profil_label (str, ex "Efficace")
    - stats (dict des 8 features de ce gestionnaire)
    Retourne None si le gestionnaire est inconnu du fichier de profils.

    `profils_df` / `df_v2` : DataFrames deja charges (evite de relire les
    CSV a chaque appel). Si omis, charges depuis PROFILS_PATH / DATA_V2_PATH.
    """
    if profils_df is None:
        profils_df = pd.read_csv(PROFILS_PATH, encoding="utf-8")
    row = profils_df.loc[profils_df["Gestionnaire"] == gestionnaire]
    if row.empty:
        return None

    row = row.iloc[0]
    if df_v2 is None:
        df_v2 = pd.read_csv(DATA_V2_PATH, encoding="utf-8")
    df_gest = df_v2.loc[df_v2["Gestionnaire"] == gestionnaire]
    grouped = aggregate_by_gestionnaire(df_gest)
    raw_stats = grouped.iloc[0][FEATURE_COLS].to_dict()
    stats = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v) for k, v in raw_stats.items()}

    return {
        "cluster": int(row["Cluster"]),
        "profil_label": row["Profil_Label"],
        "stats": stats,
    }


if __name__ == "__main__":
    train_and_evaluate()

    print("\n=== TEST predict_profil_agent() ===")
    for nom in ["Jamila Hadj Salah", "Mehdi Kahouach", "Wiem Ben Moussa", "Inconnu XYZ"]:
        print(f"\n-- {nom} --")
        print(predict_profil_agent(nom))
