# 🔧 Branche `dev` - Environnement de Développement

Cette branche est dédiée au **développement actif** et à l'**expérimentation** du projet MLOps. Elle sert d'environnement isolé pour tester de nouvelles fonctionnalités, expérimenter avec des modèles et valider les changements avant leur déploiement en branche main de production.

## 📋 Contenu de la branche

- **`notebooks/`** : Notebooks Jupyter pour l'exploration des données, l'entraînement des modèles et l'analyse exploratoire
- **`jenkins_k8s/`** : Configurations pour l'orchestration CI/CD avec Jenkins et Kubernetes
- **`captures/`** : Captures d'écran et documentation visuelle du projet
- **`commandes/`** : Scripts et commandes utiles pour le développement
- **Fichiers de données d'exemple** : `crime_sample_150.csv`, `crime_sample_20.csv` pour les tests
- **Configuration Docker** : `docker-compose.yml` pour l'environnement de développement conteneurisé -tester le network entre les images docker et leur fonctionnement 

## 🎯 Objectif

La branche `dev` permet aux développeurs de :
- Expérimenter avec de nouveaux algorithmes et approches ML
- Tester les pipelines d'entraînement et de déploiement
- Valider les configurations d'infrastructure (Jenkins, Kubernetes, Docker)
- Itérer rapidement sans impacter l'environnement de production

## ⚠️ Important

Les modifications sur cette branche ne sont **pas directement déployées en production**. Toutes les fonctionnalités doivent être testées, validées et fusionnées vers la branche principale avant déploiement.

## 🚀 Workflow de développement

1. Créer une nouvelle branche feature à partir de `dev`
2. Développer et tester localement
3. Créer une Pull Request vers `dev`
4. Après validation, merger vers la branche de production