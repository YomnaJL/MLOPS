pipeline {
    agent any

    environment {
        // On garde uniquement le tag ici. 
        // Le user sera récupéré via les Credentials Jenkins.
        IMAGE_TAG = "latest"
    }

    stages {
        
        // --- ÉTAPE 1 : INSTALLATION ---
        stage('Setup Environment') {
            steps {
                script {
                    echo "🐍 Création de l'environnement virtuel..."
                    sh '''
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --upgrade pip
                        pip install -r backend/src/requirements-backend.txt
                        pip install pytest httpx
                    '''
                }
            }
        }

        // --- ÉTAPE 2 : TESTS (CI) ---
        stage('Run Tests') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dagshub-credentials', usernameVariable: 'DAGSHUB_USERNAME', passwordVariable: 'DAGSHUB_TOKEN')]) {
                    script {
                        sh '''
                            . venv/bin/activate
                            
                            export DAGSHUB_REPO_NAME="MLOPS_Project"
                            export PYTHONPATH=$PYTHONPATH:$(pwd)/backend/src
                            
                            echo "🧪 Lancement des tests Preprocessing..."
                            python3 -m pytest testing/preprocessing_test.py
                            
                            echo "🧪 Lancement des tests Model Loading..."
                            python3 -m pytest testing/test_model_loading.py
                        '''
                    }
                }
            }
        }

        // --- ÉTAPE 3 : BUILD & PUSH (CD) ---
        stage('Build & Push Docker') {
            steps {
                script {
                    echo "🐳 Connexion et Push vers Docker Hub..."
                    
                    // Jenkins met le username dans DOCKER_USER et le password dans DOCKER_PASS
                    withCredentials([usernamePassword(credentialsId: 'docker-hub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh '''
                            # 1. Login
                            echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin

                            # 2. Backend (On utilise $DOCKER_USER partout pour être cohérent)
                            docker build -t $DOCKER_USER/crime-backend:${IMAGE_TAG} -f backend/src/Dockerfile .
                            docker push $DOCKER_USER/crime-backend:${IMAGE_TAG}

                            # 3. Frontend
                            docker build -t $DOCKER_USER/crime-frontend:${IMAGE_TAG} -f frontend/Dockerfile ./frontend
                            docker push $DOCKER_USER/crime-frontend:${IMAGE_TAG}
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'rm -rf venv'
            cleanWs()
        }
    }
}