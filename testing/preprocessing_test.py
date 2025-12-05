import pytest
import pandas as pd
import numpy as np
import sys
import os

# --- CONFIGURATION DES CHEMINS D'IMPORTATION ---
# Permet de trouver 'preprocessing.py' dans le dossier '../backend/source' ou à la racine
current_dir = os.path.dirname(os.path.abspath(__file__))
# On tente d'ajouter le dossier parent (racine du projet) et backend/source
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..')))
sys.path.insert(0, os.path.join(current_dir, '../backend/source'))

try:
    from preprocessing import categorize_crime, preprocess_data
except ImportError as e:
    pytest.fail(f"ERREUR CRITIQUE : Impossible d'importer 'preprocessing'. Vérifiez le chemin. Détail : {e}")

# --- FIXTURE (Données de test) ---
@pytest.fixture
def df_raw():
    """
    Crée un DataFrame factice (Mock) avec des cas limites pour tester
    les nouvelles règles (Sexe 'H' -> 'X', Arabe, etc.)
    """
    return pd.DataFrame({
        'DR_NO': [1, 2, 3, 4, 5],
        'Date Rptd': ['01/01/2023 10:00:00 AM', '01/02/2023 11:00:00 AM', '01/03/2023 12:00:00 PM', '01/04/2023 01:00:00 PM', '01/05/2023 02:00:00 PM'],
        'DATE OCC': ['01/01/2023 09:00:00 AM', '01/02/2023 10:00:00 AM', '01/03/2023 11:00:00 AM', '01/04/2023 12:00:00 PM', '01/05/2023 01:00:00 PM'],
        'TIME OCC': [900, 1000, 1100, 1200, 1300],
        'AREA': [1, 2, 3, 1, 2],
        'Rpt Dist No': [101, 202, 303, 101, 202],
        'Part 1-2': [1, 1, 2, 1, 2],
        'Crm Cd': [510, 330, 624, 510, 740],
        'Crm Cd Desc': [
            'VEHICLE - STOLEN',           # -> Vol
            'BURGLARY FROM VEHICLE',      # -> Vol
            'BATTERY - SIMPLE ASSAULT',   # -> Violence
            'RAPE, FORCIBLE',             # -> Sexuel
            'VANDALISM - FELONY'          # -> Vandalisme
        ],
        'Mocodes': ['0100', np.nan, '0200', '0100', '0300'],
        'Vict Age': [25, 30, 35, 40, 45],
        # TEST CRITIQUE : 'H' et '-' doivent devenir 'X' dans le nouveau code
        'Vict Sex': ['M', 'F', '-', np.nan, 'H'], 
        'Vict Descent': ['H', 'W', '-', np.nan, 'B'],
        'Premis Cd': [101.0, 102.0, np.nan, 101.0, 103.0],
        'Premis Desc': ['STREET', 'SIDEWALK', np.nan, 'STREET', 'PARKING LOT'],
        'Weapon Used Cd': [np.nan, 400.0, np.nan, np.nan, 500.0],
        'Weapon Desc': [np.nan, 'STRONG-ARM', np.nan, np.nan, 'UNKNOWN WEAPON'],
        'Status': ['AA', 'IC', 'AO', 'AA', np.nan],
        # Colonnes à supprimer
        'Crm Cd 1': [510.0, 330.0, 624.0, 510.0, 740.0],
        'Cross Street': [np.nan, np.nan, 'MAIN ST', np.nan, np.nan],
        'LAT': [34.05, 34.06, 34.07, 34.05, 34.06],
        'LON': [-118.24, -118.25, -118.26, -118.24, -118.25]
    })

# --- TESTS UNITAIRES ---

def test_categorize_crime_bilingual():
    """Test des nouvelles catégories Bilingues (Arabe / Anglais)."""
    # 1. Test Catégorie : Vol
    assert categorize_crime('VEHICLE - STOLEN') == 'السرقة والسطو / Theft and Burglary'
    
    # 2. Test Catégorie : Violence
    assert categorize_crime('BATTERY - SIMPLE ASSAULT') == 'العنف والاعتداء / Violence and Assault'
    
    # 3. Test Catégorie : Vandalisme
    assert categorize_crime('VANDALISM - FELONY') == 'التخريب والتدمير / Vandalism and Destruction'
    
    # 4. Test Catégorie : Sexuel (Nouveau)
    assert categorize_crime('RAPE') == 'الجرائم الجنسية والاتجار / Sexual Crimes & Exploitation'
    
    # 5. Test Valeur Inconnue ou Manquante
    assert categorize_crime('UNKNOWN CRIME TYPE') == 'جرائم متنوعة / Miscellaneous Crimes'
    assert categorize_crime(np.nan) == 'جرائم متنوعة / Miscellaneous Crimes'

def test_preprocess_data_columns_drop(df_raw):
    """Vérifie que les colonnes inutiles sont supprimées et le renommage effectué."""
    # On met save_artifacts=False pour ne pas créer de fichiers pendant le test
    X, y, encoders = preprocess_data(df_raw, save_artifacts=False)
    
    # Vérification suppression
    dropped_cols = ['dr_no', 'crm_cd_1', 'cross_street']
    for col in dropped_cols:
        assert col not in X.columns, f"La colonne {col} aurait dû être supprimée"
        
    # Vérification renommage (Part 1-2 -> crm_categories)
    assert 'crm_categories' in X.columns
    assert 'part_1_2' not in X.columns

def test_preprocess_data_date_features(df_raw):
    """Vérifie que Year, Month, etc. sont gardés, mais PAS Weekday (selon votre config)."""
    X, y, encoders = preprocess_data(df_raw, save_artifacts=False)
    
    expected_date_cols = ['Year', 'Month', 'Day', 'Hour', 'Minute']
    for col in expected_date_cols:
        assert col in X.columns, f"La colonne temporelle {col} est manquante"
        
    # Selon votre liste 'cols_to_keep', Weekday n'est pas retenu à la fin
    assert 'Weekday' not in X.columns
    assert 'is_weekend' not in X.columns

def test_preprocess_data_imputation(df_raw):
    """Vérifie l'imputation spécifique (Sexe H->X, Arme NaN->0)."""
    X, y, encoders = preprocess_data(df_raw, save_artifacts=False)
    
    # 1. Arme (NaN doit devenir 0.0)
    assert X['weapon_used_cd'].iloc[0] == 0.0
    
    # 2. Premis (NaN remplacé par mode)
    assert not X['premis_cd'].isnull().any()

def test_preprocess_data_encoding_features(df_raw):
    """
    Vérifie:
    1. One-Hot Encoding du Sexe (M, F, X)
    2. Label Encoding de Descent
    3. Label Encoding de la Target
    """
    X, y, encoders = preprocess_data(df_raw, save_artifacts=False)
    
    # --- A. One-Hot Sex ---
    # Dans le mock, on a 'M', 'F', '-', 'NaN', 'H'
    # 'M' -> vict_sex_M
    # 'F' -> vict_sex_F
    # '-', 'NaN', 'H' -> Doivent être transformés en 'X' -> vict_sex_X
    
    assert 'vict_sex_M' in X.columns
    assert 'vict_sex_F' in X.columns
    assert 'vict_sex_X' in X.columns
    
    # Vérification ligne 0 (Homme) -> M=1, X=0
    assert X['vict_sex_M'].iloc[0] == 1
    assert X['vict_sex_X'].iloc[0] == 0
    
    # Vérification ligne 4 (H -> X)
    # L'ancien code mettait H en X. Vérifions que vict_sex_X est à 1 pour la ligne 4
    assert X['vict_sex_X'].iloc[4] == 1

    # --- B. Label Encoding Descent ---
    assert 'Vict_Descent_LE' in X.columns
    assert 'le_descent' in encoders

    # --- C. Target ---
    assert len(y) == 5
    assert 'le_target' in encoders
    # Vérif qu'on a bien encodé des entiers
    assert pd.api.types.is_integer_dtype(y)

def test_pipeline_execution(df_raw):
    """Vérifie que le pipeline s'exécute de bout en bout sans erreur."""
    try:
        X, y, encoders = preprocess_data(df_raw, save_artifacts=False)
        assert X.shape[0] == 5
        assert y.shape[0] == 5
    except Exception as e:
        pytest.fail(f"Le pipeline a planté : {e}")