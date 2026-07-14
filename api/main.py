"""API FastAPI exposant les 3 modeles ML (regression, classification, clustering).

Consommee par Power Automate (Flow_Machine_Learning) a chaque nouvelle
demande soumise dans le portail.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

REGRESSION_MODEL_PATH = MODELS_DIR / "model_regression.pkl"
CLASSIFICATION_MODEL_PATH = MODELS_DIR / "model_classification.pkl"
CLUSTERING_MODEL_PATH = MODELS_DIR / "model_clustering.pkl"
CLUSTERING_SCALER_PATH = MODELS_DIR / "scaler_clustering.pkl"
PROFILS_PATH = DATA_DIR / "profils_gestionnaires.csv"
DATA_V2_PATH = DATA_DIR / "demandes_dataset_final_v2.csv"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))
from src.module1_regression import predict_delai
from src.module2_classification import predict_risque_retard
from src.module3_clustering import predict_profil_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api_ml")

VALID_NIVEAUX_URGENCE = ["Faible", "Normal", "Urgent", "Critique"]

models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Demarrage de l'API - chargement des modeles...")

    try:
        models["regression"] = joblib.load(REGRESSION_MODEL_PATH)
        logger.info(f"Modele regression charge ({REGRESSION_MODEL_PATH})")
    except Exception as e:
        logger.error(f"Echec du chargement du modele regression: {e}")

    try:
        models["classification"] = joblib.load(CLASSIFICATION_MODEL_PATH)
        logger.info(f"Modele classification charge ({CLASSIFICATION_MODEL_PATH})")
    except Exception as e:
        logger.error(f"Echec du chargement du modele classification: {e}")

    try:
        models["clustering_kmeans"] = joblib.load(CLUSTERING_MODEL_PATH)
        models["clustering_scaler"] = joblib.load(CLUSTERING_SCALER_PATH)
        models["profils_df"] = pd.read_csv(PROFILS_PATH, encoding="utf-8")
        models["data_v2_df"] = pd.read_csv(DATA_V2_PATH, encoding="utf-8")
        logger.info(f"Modele clustering + profils charges ({CLUSTERING_MODEL_PATH})")
    except Exception as e:
        logger.error(f"Echec du chargement du modele clustering: {e}")

    logger.info(f"Modeles disponibles au demarrage: {list(models.keys())}")
    yield
    logger.info("Arret de l'API - liberation des modeles.")
    models.clear()


app = FastAPI(
    title="API ML - Gestion des demandes",
    description="Expose les modeles de prediction de delai, risque de retard et profil comportemental des gestionnaires.",
    version="1.0.0",
    lifespan=lifespan,
)


class DemandeInput(BaseModel):
    service: str
    niveau_urgence: str
    type_demande: str
    heure_soumission: int
    jour_semaine: int
    sla_service_heures: float

    @field_validator("niveau_urgence")
    @classmethod
    def valider_niveau_urgence(cls, v):
        if v not in VALID_NIVEAUX_URGENCE:
            raise ValueError(f"niveau_urgence doit etre l'un de {VALID_NIVEAUX_URGENCE}")
        return v

    @field_validator("heure_soumission")
    @classmethod
    def valider_heure_soumission(cls, v):
        if not (0 <= v <= 23):
            raise ValueError("heure_soumission doit etre entre 0 et 23")
        return v

    @field_validator("jour_semaine")
    @classmethod
    def valider_jour_semaine(cls, v):
        if not (0 <= v <= 6):
            raise ValueError("jour_semaine doit etre entre 0 et 6")
        return v

    @field_validator("sla_service_heures")
    @classmethod
    def valider_sla(cls, v):
        if v <= 0:
            raise ValueError("sla_service_heures doit etre > 0")
        return v


class GestionnaireInput(BaseModel):
    gestionnaire: str


@app.get("/health")
async def health():
    loaded = []
    if "regression" in models:
        loaded.append("regression")
    if "classification" in models:
        loaded.append("classification")
    if "clustering_kmeans" in models and "clustering_scaler" in models and "profils_df" in models:
        loaded.append("clustering")
    return {"status": "ok", "models_loaded": loaded}


@app.post("/predict/delai")
async def predict_delai_endpoint(payload: DemandeInput):
    if "regression" not in models:
        raise HTTPException(status_code=503, detail="Modele de regression non charge")
    try:
        return predict_delai(
            payload.service,
            payload.niveau_urgence,
            payload.type_demande,
            payload.heure_soumission,
            payload.jour_semaine,
            payload.sla_service_heures,
            model=models["regression"],
        )
    except Exception as e:
        logger.error(f"Erreur /predict/delai: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la prediction du delai")


@app.post("/predict/risque")
async def predict_risque_endpoint(payload: DemandeInput):
    if "classification" not in models:
        raise HTTPException(status_code=503, detail="Modele de classification non charge")
    try:
        return predict_risque_retard(
            payload.service,
            payload.niveau_urgence,
            payload.type_demande,
            payload.heure_soumission,
            payload.jour_semaine,
            payload.sla_service_heures,
            model=models["classification"],
        )
    except Exception as e:
        logger.error(f"Erreur /predict/risque: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la prediction du risque")


@app.post("/predict/profil")
async def predict_profil_endpoint(payload: GestionnaireInput):
    if "profils_df" not in models:
        raise HTTPException(status_code=503, detail="Profils gestionnaires non charges")
    try:
        result = predict_profil_agent(
            payload.gestionnaire,
            profils_df=models["profils_df"],
            df_v2=models["data_v2_df"],
        )
    except Exception as e:
        logger.error(f"Erreur /predict/profil: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la recherche du profil")

    if result is None:
        return {"cluster": None, "profil_label": "Inconnu", "stats": None}
    return result
