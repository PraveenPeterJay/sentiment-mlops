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

        stage('Test') {
            steps {
                // Run the training script quickly to ensure code integrity
                echo 'Running Model Training Test...'
                sh 'python3 train.py' 
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building Backend Image...'
                sh "docker build -f Dockerfile.backend -t ${BACKEND_IMAGE}:${DOCKER_TAG} ."
                
                echo 'Building Frontend Image...'
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
                // Since K8s is already configured to pull 'Always', 
                // we just need to restart the pods to pick up the new image.
                // Note: Jenkins needs 'kubectl' installed for this to work.
                // If not, you can comment this out.
                sh "kubectl rollout restart deployment/backend-deployment"
                sh "kubectl rollout restart deployment/frontend-deployment"
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