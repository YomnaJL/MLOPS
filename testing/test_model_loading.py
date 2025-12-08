import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
import os

# Configuration des chemins
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../backend/src')))

from api import load_best_model

@patch('api.mlflow')
@patch('api.pickle')
@patch('builtins.open', new_callable=MagicMock)
def test_load_best_model_logic(mock_open, mock_pickle, mock_mlflow):
    print("\n\n" + "="*60)
    print("🎬 DÉBUT DU SCÉNARIO DE TEST")
    print("="*60)

    # --- 1. MISE EN SCÈNE (MOCKS) ---
    print("🤖 1. Simulation : Création de 3 faux modèles...")
    
    # On simule que l'expérience existe
    mock_experiment = MagicMock()
    mock_experiment.experiment_id = "EXP_001"
    mock_mlflow.get_experiment_by_name.return_value = mock_experiment

    # On crée notre faux tableau de résultats (Le Run B est le meilleur)
    fake_runs = pd.DataFrame({
        'run_id': ['RUN_B_WINNER', 'RUN_C_AVG', 'RUN_A_BAD'],
        'metrics.f1_weighted': [0.92, 0.85, 0.50],
        'tags.model_name': ['XGBoost', 'RandomForest', 'LogisticRegression'],
        'tags.stage': ['Tuned', 'Baseline', 'Baseline']
    })
    
    # On dit à MLflow (le faux) : "Quand on te demande les runs, donne cette liste"
    mock_mlflow.search_runs.return_value = fake_runs
    print(f"📊 Données simulées envoyées à l'API :\n{fake_runs[['run_id', 'metrics.f1_weighted', 'tags.model_name']]}")

    # On simule le contenu du fichier modèle
    fake_model_content = "Je suis l'objet modèle XGBoost"
    mock_pickle.load.return_value = fake_model_content

    # --- 2. ACTION ---
    print("\n🏃 2. Action : L'API appelle la fonction 'load_best_model()'...")
    model, name = load_best_model()

    # --- 3. VÉRIFICATION ---
    print("\n🕵️ 3. Vérification : Qui a été choisi ?")
    
    # Vérification du tri
    args, kwargs = mock_mlflow.search_runs.call_args
    print(f"   👉 Critère de tri utilisé par l'API : {kwargs['order_by']}")

    # Vérification du téléchargement
    # On récupère les arguments avec lesquels download_artifacts a été appelé
    call_args = mock_mlflow.artifacts.download_artifacts.call_args
    downloaded_run_id = call_args.kwargs['run_id']
    downloaded_file = call_args.kwargs['artifact_path']

    print(f"   👉 L'API a téléchargé le Run ID : '{downloaded_run_id}'")
    print(f"   👉 L'API a cherché le fichier   : '{downloaded_file}'")

    # TEST FINAL
    if downloaded_run_id == 'RUN_B_WINNER':
        print("\n✅ SUCCÈS : L'API a bien pris le modèle avec le meilleur score (0.92) !")
    else:
        print(f"\n❌ ÉCHEC : L'API a pris {downloaded_run_id} au lieu de RUN_B_WINNER.")
        pytest.fail("Mauvais modèle sélectionné")

    print("="*60 + "\n")