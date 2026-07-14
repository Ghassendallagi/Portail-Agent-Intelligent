"""Module ML-1 : prediction du delai de traitement (regression).

Predit Delai_Traitement_Heures a partir des informations disponibles au
moment de la soumission d'une demande. Alimente le champ
Prediction_Delai_ML dans SharePoint via l'API FastAPI (module a venir).
"""

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

try:
    from .features import FEATURE_COLUMNS, build_feature_pipeline_steps
except ImportError:
    from features import FEATURE_COLUMNS, build_feature_pipeline_steps

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "demandes_dataset_final.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "model_regression.pkl")

TARGET_COLUMN = "Delai_Traitement_Heures"


def load_training_data(path=DATA_PATH):
    """Charge et filtre les donnees : demandes terminees uniquement
    (Statut_Final != 'En cours' et Delai_Traitement_Heures non-NaN)."""
    df = pd.read_csv(path, encoding="utf-8")
    mask = (df["Statut_Final"] != "En cours") & df[TARGET_COLUMN].notna()
    df_filtered = df.loc[mask].copy()
    return df_filtered


def build_pipeline():
    steps = build_feature_pipeline_steps()
    steps.append(("model", RandomForestRegressor(n_estimators=100, random_state=42)))
    return Pipeline(steps=steps)


def train_and_evaluate():
    df = load_training_data()
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    print(f"Lignes disponibles apres filtre (Statut_Final != 'En cours', delai non-NaN): {len(df)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=X["Service"]
    )
    print(f"Train: {len(X_train)} lignes | Test: {len(X_test)} lignes")

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred_train = pipeline.predict(X_train)
    y_pred_test = pipeline.predict(X_test)

    mae_train = mean_absolute_error(y_train, y_pred_train)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    r2_test = r2_score(y_test, y_pred_test)

    print("\n=== METRIQUES TRAIN ===")
    print(f"MAE (train): {mae_train:.2f} h")

    print("\n=== METRIQUES TEST ===")
    print(f"MAE  (test): {mae_test:.2f} h  ({mae_test / 24:.2f} jours)")
    print(f"RMSE (test): {rmse_test:.2f} h")
    print(f"R2   (test): {r2_test:.4f}")

    # --- feature importance ---
    feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    importances = pipeline.named_steps["model"].feature_importances_
    importance_df = pd.DataFrame({"feature": feature_names, "importance": importances})
    importance_df = importance_df.sort_values("importance", ascending=False).head(10)

    print("\n=== TOP 10 FEATURE IMPORTANCE ===")
    print(importance_df.to_string(index=False))

    # --- validation croisee 5-fold sur le train set ---
    cv_scores = cross_val_score(
        pipeline, X_train, y_train, cv=5, scoring="neg_mean_absolute_error"
    )
    cv_mae_scores = -cv_scores
    print("\n=== CROSS-VALIDATION (5-fold, train set) ===")
    print(f"MAE par fold: {np.round(cv_mae_scores, 2).tolist()}")
    print(f"MAE moyenne: {cv_mae_scores.mean():.2f} h +/- {cv_mae_scores.std():.2f} h")

    # --- sauvegarde du modele ---
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    model_size_kb = os.path.getsize(MODEL_PATH) / 1024
    print(f"\n=== MODELE SAUVEGARDE ===")
    print(f"{MODEL_PATH} ({model_size_kb:.1f} Ko)")

    return pipeline, {
        "mae_train": mae_train,
        "mae_test": mae_test,
        "rmse_test": rmse_test,
        "r2_test": r2_test,
        "cv_mae_mean": cv_mae_scores.mean(),
        "cv_mae_std": cv_mae_scores.std(),
        "importance_df": importance_df,
    }


def _niveau_confiance(prediction_heures: float) -> str:
    if prediction_heures < 24:
        return "Rapide"
    elif prediction_heures <= 72:
        return "Normal"
    else:
        return "Long"


def predict_delai(
    service: str,
    niveau_urgence: str,
    type_demande: str,
    heure_soumission: int,
    jour_semaine: int,
    sla_service_heures: float,
    model=None,
) -> dict:
    """Predit le delai de traitement d'une nouvelle demande.

    Retourne un dict avec :
    - prediction_heures (float, arrondi a 1 decimale)
    - prediction_jours (float, arrondi a 1 decimale)
    - niveau_confiance (str : "Rapide" <24h / "Normal" 24-72h / "Long" >72h)

    `model` : pipeline sklearn deja charge (evite de relire le .pkl a chaque
    appel, utile pour un serveur qui charge le modele une seule fois au
    demarrage). Si omis, le modele est charge depuis MODEL_PATH.
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

    prediction_heures = float(model.predict(X_new)[0])

    return {
        "prediction_heures": round(prediction_heures, 1),
        "prediction_jours": round(prediction_heures / 24, 1),
        "niveau_confiance": _niveau_confiance(prediction_heures),
    }


if __name__ == "__main__":
    train_and_evaluate()

    print("\n=== TEST predict_delai() ===")
    result = predict_delai("Technique Auto", "Normal", "Autre", 9, 0, 48.0)
    print(result)
