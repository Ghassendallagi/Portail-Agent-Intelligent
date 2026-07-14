"""Module ML-2 : detection du risque de retard (classification).

Predit si une demande va depasser son SLA (En_Retard=1) a partir des
informations disponibles au moment de la soumission. Alimente le champ
Probabilite_Retard_ML dans SharePoint via l'API FastAPI (module a venir).
"""

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

try:
    from .features import FEATURE_COLUMNS, build_feature_pipeline_steps
except ImportError:
    from features import FEATURE_COLUMNS, build_feature_pipeline_steps

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "demandes_dataset_final.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "model_classification.pkl")

TARGET_COLUMN = "En_Retard"


def load_training_data(path=DATA_PATH):
    df = pd.read_csv(path, encoding="utf-8")
    df = df.loc[df[TARGET_COLUMN].notna()].copy()
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
    return df


def build_pipeline(classifier):
    steps = build_feature_pipeline_steps()
    steps.append(("model", classifier))
    return Pipeline(steps=steps)


def _evaluate(name, pipeline, X_test, y_test):
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    auc = roc_auc_score(y_test, y_proba)
    f1_pos = f1_score(y_test, y_pred, pos_label=1)

    print(f"\n=== {name} ===")
    print(classification_report(y_test, y_pred, target_names=["0 (a temps)", "1 (en retard)"]))
    print(f"AUC-ROC: {auc:.4f}")
    print("Matrice de confusion (lignes=reel, colonnes=predit):")
    print(confusion_matrix(y_test, y_pred))

    return {"name": name, "pipeline": pipeline, "auc": auc, "f1_class1": f1_pos}


def train_and_evaluate():
    df = load_training_data()
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    print(f"Lignes disponibles: {len(df)} | Positifs (En_Retard=1): {y.sum()} ({y.mean() * 100:.1f}%)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)} lignes ({y_train.sum()} positifs) | "
          f"Test: {len(X_test)} lignes ({y_test.sum()} positifs)")

    candidates = [
        ("RandomForestClassifier", RandomForestClassifier(
            n_estimators=100, class_weight="balanced", random_state=42
        )),
        ("LogisticRegression", LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42
        )),
    ]

    results = []
    for name, clf in candidates:
        pipeline = build_pipeline(clf)
        pipeline.fit(X_train, y_train)
        results.append(_evaluate(name, pipeline, X_test, y_test))

    best = max(results, key=lambda r: r["f1_class1"])
    print(f"\n=== MODELE RETENU : {best['name']} ===")
    print(f"F1 (classe 1) = {best['f1_class1']:.4f} | AUC-ROC = {best['auc']:.4f}")
    print("Justification : retenu selon le F1-score de la classe 1 (les faux negatifs "
          "- manquer un retard - sont plus couteux qu'un faux positif dans ce contexte metier).")

    best_pipeline = best["pipeline"]

    # --- validation croisee 5-fold (AUC-ROC) sur le train set, pour chaque modele ---
    print("\n=== CROSS-VALIDATION (5-fold, train set, scoring=roc_auc) ===")
    for name, clf in candidates:
        cv_pipeline = build_pipeline(clf)
        cv_scores = cross_val_score(cv_pipeline, X_train, y_train, cv=5, scoring="roc_auc")
        marker = " <-- retenu" if name == best["name"] else ""
        print(f"{name}: AUC par fold = {np.round(cv_scores, 3).tolist()}")
        print(f"  AUC moyenne = {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}{marker}")

    # --- sauvegarde du meilleur modele ---
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(best_pipeline, MODEL_PATH)
    model_size_kb = os.path.getsize(MODEL_PATH) / 1024
    print(f"\n=== MODELE SAUVEGARDE ===")
    print(f"{MODEL_PATH} ({model_size_kb:.1f} Ko)")

    return best_pipeline, results


def _niveau_risque(probabilite: float) -> str:
    if probabilite < 0.30:
        return "Faible"
    elif probabilite <= 0.60:
        return "Modéré"
    else:
        return "Élevé"


def predict_risque_retard(
    service: str,
    niveau_urgence: str,
    type_demande: str,
    heure_soumission: int,
    jour_semaine: int,
    sla_service_heures: float,
    model=None,
) -> dict:
    """Predit le risque de retard d'une nouvelle demande.

    Retourne un dict avec :
    - probabilite_retard (float, 0.0-1.0, arrondi a 2 decimales)
    - prediction_binaire (int : 0 ou 1)
    - niveau_risque (str : "Faible" <30% / "Modéré" 30-60% / "Élevé" >60%)

    `model` : pipeline sklearn deja charge (evite de relire le .pkl a chaque
    appel). Si omis, le modele est charge depuis MODEL_PATH.
    """
    if model is None:
        model = joblib.load(MODEL_PATH)

    X_new = pd.DataFrame([{
        "Service": service,
        "Niveau_Urgence": niveau_urgence,
        "Type_Demande": type_demande,
        "Heure_Soumission": heure_soumission,
        "Jour_Semaine": jour_semaine,
        "SLA_Service_Heures": sla_service_heures,
    }])[FEATURE_COLUMNS]

    probabilite = float(model.predict_proba(X_new)[0, 1])

    return {
        "probabilite_retard": round(probabilite, 2),
        "prediction_binaire": int(probabilite >= 0.5),
        "niveau_risque": _niveau_risque(probabilite),
    }


if __name__ == "__main__":
    train_and_evaluate()

    print("\n=== TEST predict_risque_retard() ===")
    result = predict_risque_retard("Technique Auto", "Normal", "Autre", 9, 0, 48.0)
    print(result)
