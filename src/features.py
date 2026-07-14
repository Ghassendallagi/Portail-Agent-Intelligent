"""Preprocessing partage entre les modules ML (regression, classification, clustering)."""

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer

FEATURE_COLUMNS = [
    "Service",
    "Niveau_Urgence",
    "Type_Demande",
    "Heure_Soumission",
    "Jour_Semaine",
    "SLA_Service_Heures",
]

CATEGORICAL_COLUMNS = ["Service", "Type_Demande"]
NUMERIC_PASSTHROUGH_COLUMNS = ["Niveau_Urgence", "Heure_Soumission", "Jour_Semaine", "SLA_Service_Heures"]

NIVEAU_URGENCE_MAPPING = {"Faible": 0, "Normal": 1, "Urgent": 2, "Critique": 3}


def map_niveau_urgence(X):
    """Encode Niveau_Urgence en ordinal (Faible=0, Normal=1, Urgent=2, Critique=3)."""
    X = X.copy()
    X["Niveau_Urgence"] = X["Niveau_Urgence"].map(NIVEAU_URGENCE_MAPPING)
    return X


def build_preprocessor():
    """ColumnTransformer : OneHotEncoding sur Service/Type_Demande, passthrough sur le reste."""
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ],
        remainder="passthrough",
    )


def build_feature_pipeline_steps():
    """Retourne les etapes de preprocessing (mapping ordinal + ColumnTransformer)
    a inserer avant le modele dans un Pipeline sklearn."""
    return [
        ("urgence_mapper", FunctionTransformer(map_niveau_urgence, validate=False)),
        ("preprocessor", build_preprocessor()),
    ]
