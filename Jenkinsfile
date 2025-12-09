pipeline {
    agent any

    environment {
        // --- Configuration Docker Hub ---
        DOCKER_IMAGE_NAME = 'imen835/mlops-crime'
        
        // --- Variables non sensibles ---
        DAGSHUB_USERNAME = 'YomnaJL'
        DAGSHUB_REPO_NAME = 'MLOPS_Project'
        MLFLOW_TRACKING_URI = 'https://dagshub.com/YomnaJL/MLOPS_Project.mlflow'
        ARIZE_SPACE_ID = 'U3BhY2U6MzEyNjA6QzFTdw=='
        
        // --- Secrets (Correspondance exacte avec vos IDs Jenkins) ---
        // J'ai remis les noms standards que nous avions définis ensemble
        DAGSHUB_TOKEN = credentials('dagshub-credentials') 
        ARIZE_API_KEY = credentials('arize-api-key-id') 
        // Note: Pour Docker Hub, on utilisera withCredentials plus bas pour plus de sécurité
    }

    stages {
        // 1. Nettoyage et Récupération du code
        stage('Clean & Checkout') {
            steps {
                cleanWs()
                checkout scm
            }
        }

        // 2. Tests Unitaires (Backend)
        stage('Test Backend') {
            steps {
                script {
                    echo "🚀 Lancement des tests dans un environnement isolé..."
                    
                    // ASTUCE : '-u root' permet d'installer des paquets pip sans erreur de permission
                    docker.image('python:3.9-slim').inside('-u root') {
                        
                        // Installation des dépendances
                        sh 'pip install --no-cache-dir -r backend/src/requirements-backend.txt'
                        sh 'pip install pytest httpx'
                        
                        // Exécution des tests avec injection des secrets
                        withEnv([
                            "DAGSHUB_TOKEN=${DAGSHUB_TOKEN}",
                            "DAGSHUB_USERNAME=${DAGSHUB_USERNAME}",
                            "DAGSHUB_REPO_NAME=${DAGSHUB_REPO_NAME}",
                            "MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}",
                            "ARIZE_SPACE_ID=${ARIZE_SPACE_ID}",
                            "ARIZE_API_KEY=${ARIZE_API_KEY}"
                        ]) {
                            // On ajoute le dossier src au PYTHONPATH pour les imports
                            sh '''
                                export PYTHONPATH=$PYTHONPATH:$(pwd)/backend/src
                                pytest testing/
                            '''
                        }
                    }
                }
            }
        }

        // 3. Construction des Images (Build)
        stage('Build Images') {
            steps {
                script {
                    echo "🏗️ Construction du Backend..."
                    // CORRECTION MAJEURE : On build depuis la racine (.) avec -f
                    sh "docker build -t ${DOCKER_IMAGE_NAME}:backend-${BUILD_NUMBER} -t ${DOCKER_IMAGE_NAME}:backend-latest -f backend/src/Dockerfile ."
                    
                    echo "🏗️ Construction du Frontend..."
                    // Pour le frontend, le contexte ./frontend suffit généralement
                    sh "docker build -t ${DOCKER_IMAGE_NAME}:frontend-${BUILD_NUMBER} -t ${DOCKER_IMAGE_NAME}:frontend-latest -f frontend/Dockerfile ./frontend"
                }
            }
        }

        // 4. Envoi vers Docker Hub (Push)
        stage('Push to Docker Hub') {
            steps {
                script {
                    echo "🔓 Connexion et Push..."
                    
                    // Utilisation de withCredentials pour une sécurité maximale et éviter les erreurs de variable
                    withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh '''
                            echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                            
                            # Push Backend
                            docker push ${DOCKER_IMAGE_NAME}:backend-${BUILD_NUMBER}
                            docker push ${DOCKER_IMAGE_NAME}:backend-latest
                            
                            # Push Frontend
                            docker push ${DOCKER_IMAGE_NAME}:frontend-${BUILD_NUMBER}
                            docker push ${DOCKER_IMAGE_NAME}:frontend-latest
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                echo "🧹 Nettoyage des images locales..."
                // Le '|| true' empêche le pipeline d'échouer si l'image n'existe pas
                sh "docker rmi ${DOCKER_IMAGE_NAME}:backend-${BUILD_NUMBER} || true"
                sh "docker rmi ${DOCKER_IMAGE_NAME}:backend-latest || true"
                sh "docker rmi ${DOCKER_IMAGE_NAME}:frontend-${BUILD_NUMBER} || true"
                sh "docker rmi ${DOCKER_IMAGE_NAME}:frontend-latest || true"
                sh "docker logout"
            }
        }
        success {
            echo "✅ Succès ! Images disponibles sur Docker Hub : ${DOCKER_IMAGE_NAME}"
        }
        failure {
            echo "❌ Échec du pipeline."
        }
    }
}