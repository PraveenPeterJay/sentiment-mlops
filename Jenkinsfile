pipeline {
    agent any

    environment {
        // Your existing credential ID
        
        DOCKERHUB_CREDENTIALS = credentials('dockerhub_credentials')
        
        // YOUR Docker Hub Username
        DOCKERHUB_USER = "aayushbhargav57" 
        
        // Image Names
        BACKEND_IMAGE = "${DOCKERHUB_USER}/mlops-backend"
        FRONTEND_IMAGE = "${DOCKERHUB_USER}/mlops-frontend"
        DOCKER_TAG = "latest"
        
        // Email for notifications
        EMAIL_ID = "aayushbhargav0507@gmail.com"
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulls code from the branch that triggered the webhook
                checkout scm
            }
        }

        stage('Train Model (CI)') {
            steps {
                echo 'Training the model inside Jenkins...'
                sh '''
                python3 -m venv venv
                . venv/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                
                # 1. CLEANUP (Start fresh)
                rm -rf mlruns
                rm -f mlflow.db
                mkdir -p data
                
                # 2. DATA INGESTION (Simulating DVC)
                # We create the data here. In the "Story", this is DVC pulling data.
                echo "review,sentiment" > data/train.csv
                echo '"This movie was fantastic and I loved it",positive' >> data/train.csv
                echo '"Terrible acting",negative' >> data/train.csv
                echo '"I will never watch this",negative' >> data/train.csv
                echo '"Best film",positive' >> data/train.csv
                echo '"It was okay",positive' >> data/train.csv
                
                # 3. TRAIN & LOG TO MLFLOW
                # This generates the 'mlruns' folder with the new model
                python3 train.py
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building Images (With Model Baked In)...'
                // The Dockerfile now copies the 'mlruns' folder we just created!
                sh "docker build -f Dockerfile.backend -t ${BACKEND_IMAGE}:${DOCKER_TAG} ."
                sh "docker build -f Dockerfile.frontend -t ${FRONTEND_IMAGE}:${DOCKER_TAG} ."
            }
        }

        stage('Push to Docker Hub') {
            steps {
                // Secure login using your existing credentials syntax
                sh """
                echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin
                
                # Push Backend
                docker push ${BACKEND_IMAGE}:${DOCKER_TAG}
                
                # Push Frontend
                docker push ${FRONTEND_IMAGE}:${DOCKER_TAG}
                
                docker logout
                """
            }
        }

        stage('Update Kubernetes') {
            steps {
                echo 'Updating K8s Deployment...'
                // We point kubectl explicitly to the config file we just copied
                sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig rollout restart deployment/backend-deployment"
                sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig rollout restart deployment/frontend-deployment"
            }
        }
    }

    post {
        success {
            mail bcc: '',
                 body: "SUCCESS: MLOps Pipeline (Build ${BUILD_NUMBER}) deployed new AI models to Docker Hub.",
                 from: 'jenkins@localhost',
                 subject: "Pipeline SUCCESS: MLOps Project Build #${BUILD_NUMBER}",
                 to: "${EMAIL_ID}"
        }
        failure {
            mail bcc: '',
                 body: "FAILURE: MLOps Pipeline (Build ${BUILD_NUMBER}) crashed. Check logs.",
                 from: 'jenkins@localhost',
                 subject: "Pipeline FAILURE: MLOps Project Build #${BUILD_NUMBER}",
                 to: "${EMAIL_ID}"
        }
        always {
            cleanWs()
        }
    }
}