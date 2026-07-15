"""Module ML-3 : profilage comportemental des agents demandeurs (clustering K-Means).

Regroupe les agents demandeurs en profils comportementaux homogenes a partir
de leurs statistiques de soumission de demandes. Alimente le champ
Profil_Comportemental_ML dans la liste Agents de SharePoint.

Colonne source : le dataset ne contient qu'une seule colonne personne
("Gestionnaire"). En l'absence d'une colonne "Agent_Demandeur" dediee,
c'est cette colonne qui est utilisee comme identifiant de l'agent demandeur
pour l'agregation (les noms qu'elle contient correspondent aux agents reels
de la liste SharePoint Agents).
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
PROFILS_PATH = os.path.join(PROJECT_ROOT, "data", "profils_agents.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "model_clustering_agents.pkl")
SCALER_PATH = os.path.join(PROJECT_ROOT, "models", "scaler_clustering_agents.pkl")

AGENT_COL = "Gestionnaire"

FEATURE_COLS = [
    "nb_demandes_total", "taux_urgent_critique", "taux_rejete",
    "delai_moyen_traitement_h", "nb_transferts_moyen", "diversite_services",
]


# =========================================================
# ETAPE 0 : coherence agent / service
# =========================================================
def fix_gestionnaire_service_coherence(path=DATA_PATH, out_path=DATA_V2_PATH, seed=42):
    """Reaffecte, pour les lignes synthetiques, l'agent a un agent reel dont
    le service reel correspond au Service de la demande. Laisse 'Inconnu'
    si aucun agent reel n'existe pour ce service."""
    rng = np.random.default_rng(seed)
    df = pd.read_csv(path, encoding="utf-8")
    reel_mask = df["Source"] == "reel"

    service_to_agents = {}
    for service, agent in df.loc[reel_mask, ["Service", AGENT_COL]].drop_duplicates().itertuples(index=False):
        service_to_agents.setdefault(service, []).append(agent)

    print("=== Agents reels par service ===")
    for service, agents in service_to_agents.items():
        print(f"  {service}: {agents}")

    services_sans = sorted(set(df["Service"].unique()) - set(service_to_agents.keys()))
    if services_sans:
        print(f"Services sans agent reel (-> 'Inconnu'): {services_sans}")
    else:
        print("Tous les services ont au moins un agent reel associe.")

    def reassign(row):
        if row["Source"] != "synthetique":
            return row[AGENT_COL]
        candidates = service_to_agents.get(row["Service"])
        if not candidates:
            return "Inconnu"
        return rng.choice(candidates)

    old_agent = df[AGENT_COL].copy()
    df[AGENT_COL] = df.apply(reassign, axis=1)
    n_changed = ((df["Source"] == "synthetique") & (df[AGENT_COL] != old_agent)).sum()

    print(f"\nAgents synthetiques reassignes: {n_changed} / {(df['Source'] == 'synthetique').sum()}")
    print(f"Agent = 'Inconnu' apres correction: {(df[AGENT_COL] == 'Inconnu').sum()} lignes")

    df.to_csv(out_path, encoding="utf-8", sep=",", index=False)
    print(f"Sauvegarde: {out_path}")
    return df


# =========================================================
# ETAPE 1 : agregation par agent demandeur
# =========================================================
def aggregate_by_agent(df):
    df = df.loc[df[AGENT_COL] != "Inconnu"].copy()

    grouped = df.groupby(AGENT_COL).agg(
        nb_demandes_total=(AGENT_COL, "size"),
        taux_urgent_critique=("Niveau_Urgence", lambda s: s.isin(["Urgent", "Critique"]).mean()),
        taux_rejete=("Statut_Final", lambda s: (s == "Rejeté").mean()),
        delai_moyen_traitement_h=("Delai_Traitement_Heures", "mean"),
        nb_transferts_moyen=("Nb_Transferts", "mean"),
        diversite_services=("Service", "nunique"),
    ).reset_index().rename(columns={AGENT_COL: "Agent"})

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
# ETAPE 4 : nommage des profils (data-driven, 4 labels metier)
# =========================================================
def name_clusters(grouped):
    """Attribue un profil parmi {"Autonome", "Récurrent", "À accompagner",
    "Critique"} a chaque cluster en comparant ses moyennes a la moyenne
    (ponderee par taille) des AUTRES clusters. Vocabulaire impose par le
    champ Choice SharePoint
    Profil_Comportemental_ML (allowTextEntry=False) : Autonome / Recurrent /
    A accompagner / Critique -- pas de label libre possible. Regles evaluees
    par ordre de priorite metier (pire cas d'abord) ; la premiere qui matche
    est retenue, sinon "Récurrent" par defaut."""
    cluster_means = grouped.groupby("Cluster")[FEATURE_COLS].mean()
    cluster_sizes = grouped.groupby("Cluster").size()
    labels = {}

    for cid in cluster_means.index:
        this_mean = cluster_means.loc[cid]
        other_clusters = [c for c in cluster_means.index if c != cid]

        if not other_clusters:
            labels[cid] = "Récurrent"
            continue

        other_weights = cluster_sizes.loc[other_clusters]
        other_mean = (cluster_means.loc[other_clusters].mul(other_weights, axis=0).sum() / other_weights.sum())

        if this_mean["taux_rejete"] > max(other_mean["taux_rejete"] * 1.5, 0.15):
            label = "Critique"
        elif this_mean["taux_urgent_critique"] > max(other_mean["taux_urgent_critique"] * 1.3, 0.05):
            label = "À accompagner"
        elif (this_mean["taux_rejete"] < other_mean["taux_rejete"] * 0.6
              and this_mean["nb_demandes_total"] >= other_mean["nb_demandes_total"] * 0.8):
            label = "Autonome"
        else:
            label = "Récurrent"

        labels[cid] = label

    return labels, cluster_means


def train_and_evaluate():
    fix_gestionnaire_service_coherence()

    df = pd.read_csv(DATA_V2_PATH, encoding="utf-8")
    grouped = aggregate_by_agent(df)

    print(f"\n=== TABLEAU AGREGE PAR AGENT (n={grouped.shape[0]}) ===")
    print(grouped.to_string(index=False))

    if grouped.shape[0] < 10:
        print(f"\nATTENTION: seulement {grouped.shape[0]} agents -- "
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
    display_means["n_agents"] = grouped.groupby("Cluster").size()
    print(display_means.to_string())

    print("\n=== AGENT -> CLUSTER / PROFIL ===")
    print(grouped[["Agent", "nb_demandes_total", "taux_urgent_critique", "taux_rejete",
                   "Cluster", "Profil_Label"]].sort_values("Cluster").to_string(index=False))

    # --- sauvegardes ---
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(kmeans, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    model_size_kb = os.path.getsize(MODEL_PATH) / 1024
    scaler_size_kb = os.path.getsize(SCALER_PATH) / 1024
    print(f"\n=== MODELES SAUVEGARDES ===")
    print(f"{MODEL_PATH} ({model_size_kb:.1f} Ko)")
    print(f"{SCALER_PATH} ({scaler_size_kb:.1f} Ko)")

    profils_out = grouped[["Agent", "nb_demandes_total", "taux_urgent_critique",
                            "taux_rejete", "Cluster", "Profil_Label"]].rename(
        columns={"nb_demandes_total": "nb_demandes"}
    )
    profils_out.to_csv(PROFILS_PATH, encoding="utf-8", sep=",", index=False)
    print(f"Profils sauvegardes: {PROFILS_PATH}")

    return grouped, kmeans, scaler, labels_map


def _match_agent_row(profils_df, agent_email_or_name):
    """Recherche une ligne agent par nom exact (insensible a la casse), puis,
    si l'entree ressemble a un email et qu'aucun nom ne correspond, par une
    heuristique de conversion locale-part -> nom (ex: 'ahlem.mallous@x.tn' ->
    'ahlem mallous'). Le dataset ne contenant que des noms (pas d'emails),
    cette heuristique est un best-effort, pas une garantie de resolution."""
    needle = agent_email_or_name.strip().lower()

    exact = profils_df.loc[profils_df["Agent"].str.lower() == needle]
    if not exact.empty:
        return exact.iloc[0]

    if "@" in needle:
        local_part = needle.split("@", 1)[0]
        normalized = local_part.replace(".", " ").replace("_", " ").strip()
        candidate = profils_df.loc[profils_df["Agent"].str.lower() == normalized]
        if not candidate.empty:
            return candidate.iloc[0]

    return None


def predict_profil_agent(agent_email_or_name: str, profils_df=None, df_v2=None) -> dict:
    """Retourne le profil comportemental d'un agent demandeur.

    - cluster (int)
    - profil_label (str, ex "À accompagner")
    - stats (dict des 6 features de cet agent)
    Retourne None si l'agent est inconnu du fichier de profils.

    `agent_email_or_name` : nom complet (correspondance exacte, insensible a
    la casse) ou email (best-effort via la partie locale). `profils_df` /
    `df_v2` : DataFrames deja charges (evite de relire les CSV a chaque
    appel). Si omis, charges depuis PROFILS_PATH / DATA_V2_PATH.
    """
    if profils_df is None:
        profils_df = pd.read_csv(PROFILS_PATH, encoding="utf-8")

    row = _match_agent_row(profils_df, agent_email_or_name)
    if row is None:
        return None

    agent_name = row["Agent"]
    if df_v2 is None:
        df_v2 = pd.read_csv(DATA_V2_PATH, encoding="utf-8")
    df_agent = df_v2.loc[df_v2[AGENT_COL] == agent_name]
    grouped = aggregate_by_agent(df_agent)
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
