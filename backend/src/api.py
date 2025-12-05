import os
import pickle
import pandas as pd
import numpy as np
import mlflow
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# =======================================================
# 1. IMPORT DU FICHIER PREPROCESSING EXISTANT
# =======================================================
import preprocessing 

# =======================================================
# 2. CONFIGURATION
# =======================================================
load_dotenv()

DAGSHUB_USERNAME = os.getenv('DAGSHUB_USERNAME')
DAGSHUB_TOKEN = os.getenv('DAGSHUB_TOKEN')
DAGSHUB_REPO = os.getenv('DAGSHUB_REPO_NAME')
MLFLOW_TRACKING_URI = f"https://dagshub.com/{DAGSHUB_USERNAME}/{DAGSHUB_REPO}.mlflow"
EXPERIMENT_NAME = "Crime_MLOPS"
ARTIFACTS_PATH = "../../processors"

os.environ['MLFLOW_TRACKING_USERNAME'] = DAGSHUB_USERNAME
os.environ['MLFLOW_TRACKING_PASSWORD'] = DAGSHUB_TOKEN
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment(EXPERIMENT_NAME)

# =======================================================
# 3. CLASSE DE PRÉDICTION
# =======================================================
class CrimePredictor:
    def __init__(self):
        self.scaler = None
        self.feature_encoders = None
        self.features_config = None
        self.target_mapping = None
        self.model = None
        self.load_artifacts()
        self.load_best_model()

    def load_artifacts(self):
        """Charge les pickles générés par preprocessing.py"""
        try:
            with open(os.path.join(ARTIFACTS_PATH, "robust_scaler.pkl"), "rb") as f:
                self.scaler = pickle.load(f)
            with open(os.path.join(ARTIFACTS_PATH, "feature_label_encoders.pkl"), "rb") as f:
                self.feature_encoders = pickle.load(f)
            with open(os.path.join(ARTIFACTS_PATH, "features_config.pkl"), "rb") as f:
                self.features_config = pickle.load(f)
            with open(os.path.join(ARTIFACTS_PATH, "target_mapping.pkl"), "rb") as f:
                self.target_mapping = pickle.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"❌ Artifacts introuvables dans '{ARTIFACTS_PATH}'. Lance preprocessing.py d'abord !")

    def load_best_model(self):
        """Récupère le meilleur modèle MLflow (F1 Score)"""
        print("🔍 Recherche du meilleur modèle...")
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="metrics.f1_weighted > 0",
            order_by=["metrics.f1_weighted DESC"],
            max_results=1
        )
        if runs.empty: raise ValueError("Aucun run trouvé.")
        
        run_id = runs.iloc[0].run_id
        print(f"🏆 Meilleur Run ID: {run_id}")
        
        try:
            self.model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")
        except:
            # Fallback si artifact pickle simple
            client = mlflow.tracking.MlflowClient()
            pkl = next(x.path for x in client.list_artifacts(run_id) if x.path.endswith('.pkl'))
            local = client.download_artifacts(run_id, pkl, dst_path=".")
            with open(local, "rb") as f: self.model = pickle.load(f)
            os.remove(local)

    def prepare_input(self, input_data: dict):
        """
        Utilise DIRECTEMENT les fonctions de preprocessing.py
        """
        # 1. Création DataFrame
        df = pd.DataFrame([input_data])

        # 2. Appel des fonctions de nettoyage de preprocessing.py
        df = preprocessing.clean_column_names(df)
        df = preprocessing.feature_engineering_temporal(df)
        df = preprocessing.handle_missing_values_and_text(df)

        # 3. Appel de l'encodage de preprocessing.py
        # On passe self.feature_encoders pour qu'il utilise ceux appris à l'entraînement
        # Cela gère le LabelEncoding ET le get_dummies (Sexe)
        df, _ = preprocessing.encode_features(df, encoders=self.feature_encoders)

        # 4. Alignement des colonnes (Gestion du problème get_dummies en prod)
        # Si 'vict_sex' est 'M', get_dummies ne crée pas 'vict_sex_F'.
        # On force la création des colonnes manquantes avec 0.
        required_features = self.features_config['final_feature_order']
        
        # On réindexe le DataFrame pour avoir exactement les mêmes colonnes que le train
        # fill_value=0 remplace les colonnes manquantes (ex: vict_sex_F) par 0
        df_final = df.reindex(columns=required_features, fill_value=0)

        # 5. Scaling
        X_scaled = self.scaler.transform(df_final)
        
        return X_scaled

# =======================================================
# 4. API FASTAPI
# =======================================================
predictor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    predictor = CrimePredictor()
    yield

app = FastAPI(lifespan=lifespan)

class CrimeInput(BaseModel):
    date_occ: str
    time_occ: int
    area: int
    vict_age: int
    vict_sex: str
    vict_descent: str
    premis_cd: float
    weapon_used_cd: float = None
    status: str
    mocodes: str
    location: str

@app.post("/predict")
def predict(data: CrimeInput):
    if not predictor.model: raise HTTPException(503, "Modèle non chargé")
    
    try:
        X = predictor.prepare_input(data.dict())
        pred = predictor.model.predict(X)[0]
        
        label = str(pred)
        if predictor.target_mapping:
            label = predictor.target_mapping["code_to_class"].get(pred, label)
            
        return {"prediction_code": int(pred), "prediction_class": label}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)