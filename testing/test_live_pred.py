import requests
import json
import sys
import time

# ==========================================
# CONFIGURATION
# ==========================================
# URL locale (nécessite le port-forward Kubernetes)
URL = "http://127.0.0.1:5000/predict"

# Données de test (Basées sur une ligne réelle du dataset)
payload = {
  "DATE OCC": "01/01/2023 12:00:00 PM",
  "TIME OCC": 1200,
  "AREA": 1,
  "Rpt Dist No": 101,
  "Part 1-2": 1,
  "Crm Cd": 230,
  "Mocodes": "0400",
  "Vict Age": 30,
  "Vict Sex": "M",
  "Vict Descent": "W",
  "Premis Cd": 101.0,
  "Premis Desc": "STREET",
  "Weapon Used Cd": 400.0,
  "Weapon Desc": "STRONG-ARM (HANDS, FIST, FEET OR BODILY FORCE)",
  "Status": "IC",
  "LOCATION": "800 N ALAMEDA ST",
  "LAT": 34.0,
  "LON": -118.2
}

def test_prediction():
    print(f"\n📡 1. Tentative de connexion à {URL}...")
    print("⏳ En attente de réponse (Timeout: 10s)...")
    
    try:
        start_time = time.time()
        # On met un timeout de 10 secondes. 
        # Si le pod est OOMKilled (mémoire saturée), il ne répondra souvent pas.
        response = requests.post(URL, json=payload, timeout=10)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ SUCCÈS ! (Temps de réponse: {duration:.2f}s)")
            print("-" * 40)
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            print("-" * 40)
            
            # Validation du contenu
            data = response.json()
            if "prediction" in data and "confidence" in data:
                print("🎉 Le format de réponse est valide.")
            else:
                print("⚠️ Format de réponse inattendu (champs manquants).")
                
        else:
            print(f"❌ ERREUR HTTP {response.status_code}")
            print("Détails :", response.text)

    except requests.exceptions.ConnectionError:
        print("❌ ERREUR DE CONNEXION : Impossible d'atteindre l'API.")
        print("\n🔎 DIAGNOSTIC :")
        print("   1. Avez-vous lancé la commande 'kubectl port-forward' ?")
        print("   2. Le Pod Backend est-il en cours d'exécution (Running) ?")
        print("   3. Vérifiez 'kubectl get pods'")
        
    except requests.exceptions.ReadTimeout:
        print("❌ TIMEOUT : L'API met trop de temps à répondre.")
        print("\n🔎 DIAGNOSTIC OOMKilled :")
        print("   C'est souvent le signe que le Pod a crashé par manque de mémoire (OOM) pendant le chargement du modèle.")
        print("   -> Vérifiez les logs : kubectl logs -f deployment/backend-deployment")

if __name__ == "__main__":
    test_prediction()