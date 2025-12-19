import os
import shutil
import pickle
import json
import mlflow
import dagshub
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

# Import des librairies de modèles (pour le support dynamique)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import accuracy_score, f1_score, classification_report
from preprocessing import run_preprocessing_pipeline

# ==========================================
# CONFIGURATION
# ==========================================
EXPERIMENT_NAME = "Crime_MLOPS1"  # Ton expérience existante
REGISTERED_MODEL_NAME = "Crime_Prediction_Model"
ARTIFACT_PATH = "processors"      # Dossier local contenant scaler.pkl, etc.

# Configuration DagsHub
DAGSHUB_REPO_OWNER = os.getenv("DAGSHUB_USERNAME", "YomnaJL")
DAGSHUB_REPO_NAME = os.getenv("DAGSHUB_REPO_NAME", "MLOPS_Project")

def setup_mlflow():
    """Connexion à DagsHub."""
    try:
        dagshub.init(repo_owner=DAGSHUB_REPO_OWNER, repo_name=DAGSHUB_REPO_NAME, mlflow=True)
        print(f"✅ DagsHub MLflow connecté.")
    except Exception as e:
        print(f"⚠️ Erreur init DagsHub: {e}. Vérifiez les variables d'environnement.")

def get_best_run_config():
    """
    🔍 Recherche dynamique :
    Va chercher dans l'historique MLflow quel modèle a le meilleur F1-Weighted.
    Retourne : (type_algo, hyperparamètres)
    """
    client = MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    
    if not experiment:
        raise ValueError(f"Expérience '{EXPERIMENT_NAME}' introuvable !")

    # 1. On cherche le meilleur Run (Trié par F1 Descendant)
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.f1_weighted DESC"],
        max_results=1
    )
    
    if not runs:
        raise ValueError("Aucun run trouvé dans MLflow.")

    best_run = runs[0]
    run_id = best_run.info.run_id
    run_name = best_run.data.tags.get("mlflow.runName", "Unknown")
    f1_score_val = best_run.data.metrics.get('f1_weighted', 0)
    
    print(f"\n🏆 MEILLEUR MODÈLE TROUVÉ DANS L'HISTORIQUE :")
    print(f"   - Nom : {run_name}")
    print(f"   - ID  : {run_id}")
    print(f"   - F1  : {f1_score_val:.4f}")

    # 2. Détection du type de modèle via le nom
    algo_type = "unknown"
    name_upper = run_name.upper()
    
    if "XGB" in name_upper:
        algo_type = "xgboost"
    elif "CAT" in name_upper:
        algo_type = "catboost"
    elif "LGB" in name_upper or "LIGHT" in name_upper:
        algo_type = "lightgbm"
    elif "FOREST" in name_upper or "RF" in name_upper:
        algo_type = "randomforest"
    
    # 3. Récupération des paramètres
    return algo_type, best_run.data.params

def instantiate_model(algo_type, params, y_train_sample):
    """
    🏭 Factory : Crée l'objet modèle Python à partir des params MLflow (qui sont des strings).
    """
    # Nettoyage des paramètres (conversion string -> int/float/bool)
    clean_params = {}
    for k, v in params.items():
        if k.startswith("mlflow"): continue # Ignorer les tags internes
        try:
            if v.lower() == 'none': clean_params[k] = None
            elif v.lower() == 'true': clean_params[k] = True
            elif v.lower() == 'false': clean_params[k] = False
            elif '.' in v: clean_params[k] = float(v)
            else: clean_params[k] = int(v)
        except:
            clean_params[k] = v

    print(f"🔧 Configuration du modèle '{algo_type}' avec params nettoyés.")

    if algo_type == "xgboost":
        # XGBoost a besoin du nombre de classes pour certains objectifs
        num_class = len(np.unique(y_train_sample))
        # On force num_class si l'objectif est multi
        if 'objective' in clean_params and 'multi' in clean_params['objective']:
            clean_params['num_class'] = num_class
        return XGBClassifier(**clean_params)
    
    elif algo_type == "catboost":
        return CatBoostClassifier(**clean_params)
    
    elif algo_type == "lightgbm":
        return LGBMClassifier(**clean_params)
    
    elif algo_type == "randomforest":
        return RandomForestClassifier(**clean_params)
    
    else:
        raise ValueError(f"Type d'algorithme non supporté : {algo_type}")

def train_and_register():
    setup_mlflow()
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    print("\n🔄 1. PRÉPARATION DES DONNÉES (DRIFT MANAGED)")
    print("   On relance le pipeline complet pour générer de nouveaux processors adaptés à la nouvelle data.")
    # C'est ici que 'preprocessing.py' écrase les anciens encoders dans 'processors/'
    run_preprocessing_pipeline()
    
    # Chargement des données transformées
    data_path = os.path.join(ARTIFACT_PATH, "preprocessed_data.pkl")
    with open(data_path, "rb") as f:
        data = pickle.load(f)
    X_train, y_train = data["X_train_scaled"], data["y_train"]
    X_test, y_test = data["X_test_scaled"], data["y_test"]

    # 2. Récupération de la meilleure config
    algo_type, best_params = get_best_run_config()
    
    # 3. Instanciation
    model = instantiate_model(algo_type, best_params, y_train)
    
    print(f"\n🚀 2. DÉMARRAGE DE L'ENTRAÎNEMENT (Continuous Training)")
    
    with mlflow.start_run() as run:
        # A. Entraînement sur la NOUVELLE data
        model.fit(X_train, y_train)
        
        # B. Évaluation
        y_pred = model.predict(X_test)
        f1 = f1_score(y_test, y_pred, average='weighted')
        acc = accuracy_score(y_test, y_pred)
        
        print(f"✅ Entraînement terminé.")
        print(f"   - Nouveau F1-Score : {f1:.4f}")
        print(f"   - Accuracy : {acc:.4f}")
        
        # C. Logging Métriques & Params
        mlflow.log_params(best_params)
        mlflow.log_metrics({"f1_weighted": f1, "accuracy": acc})
        mlflow.log_param("training_mode", "retraining_on_new_data")
        mlflow.log_param("base_algo", algo_type)

        # D. SAUVEGARDE DE LA REFERENCE (Pour le Drift Detection futur)
        # On sauvegarde X_test comme "dataset de référence" pour Evidently
        ref_path = "reference_data.csv"
        # On reconstitue un petit CSV pour référence (optionnel mais recommandé pour Evidently)
        # pd.DataFrame(X_test).to_csv(ref_path, index=False)
        # mlflow.log_artifact(ref_path, artifact_path="drift_reference")

        # =========================================================
        # E. LA SOLUTION "PROCESSORS" (Artifact Bundling)
        # =========================================================
        print(f"📦 Sauvegarde du modèle ET du dossier '{ARTIFACT_PATH}' dans MLflow...")
        
        # 1. Sauvegarde des Processors (Encoders/Scaler)
        mlflow.log_artifacts(local_dir=ARTIFACT_PATH, artifact_path="processors")
        
        # 2. Sauvegarde du Modèle
        if algo_type == "xgboost":
            mlflow.xgboost.log_model(model, "model", registered_model_name=REGISTERED_MODEL_NAME)
        elif algo_type == "catboost":
            mlflow.catboost.log_model(model, "model", registered_model_name=REGISTERED_MODEL_NAME)
        elif algo_type == "lightgbm":
            mlflow.lightgbm.log_model(model, "model", registered_model_name=REGISTERED_MODEL_NAME)
        else:
            mlflow.sklearn.log_model(model, "model", registered_model_name=REGISTERED_MODEL_NAME)
            
        print(f"\n🎉 Succès ! Run ID : {run.info.run_id}")
        print(f"   Le modèle '{REGISTERED_MODEL_NAME}' a été mis à jour dans le Registry.")
        print(f"   Les 'processors' sont attachés à ce run.")

if __name__ == "__main__":
    train_and_register()