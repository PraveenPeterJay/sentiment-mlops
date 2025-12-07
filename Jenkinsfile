pipeline {
    agent any

    environment {
        // Your existing credential ID
        
        DOCKERHUB_CREDENTIALS = credentials('dockerhub_credentials')
        
        // YOUR Docker Hub Username
        DOCKERHUB_USER = "praveenpeterjay2" 
        
        // Image Names
        BACKEND_IMAGE = "${DOCKERHUB_USER}/mlops-backend"
        FRONTEND_IMAGE = "${DOCKERHUB_USER}/mlops-frontend"
        DOCKER_TAG = "latest"
        
        // Email for notifications
        EMAIL_ID = "praveenpeterjay@gmail.com"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Configure Remote Host') {
            steps {
                echo 'Running Configuration Management playbook (install Docker/K8s tools)...'
                
                sh "ansible-playbook -i ansible/inventory.ini ansible/playbook-1.yml"

                echo 'Remote host configured and ready for deployment.'
            }
        }
        
        stage('Build, Train, & Deploy (Remote)') {
            steps {
                echo 'Executing full CI/CD pipeline on the configured Ansible Host...'
                
                sh "ansible-playbook -i ansible/inventory.ini ansible/playbook-2.yml --extra-vars 'workspace=${WORKSPACE}'"
            }
        }

        // stage('Train Model (CI)') {
        //     steps {
        //         echo 'Training with Persistent History...'
        //         sh '''
        //         python3 -m venv venv
        //         . venv/bin/activate
        //         pip install --upgrade pip
        //         pip install -r requirements.txt
                
        //         # 1. SETUP DVC
        //         dvc remote add -d -f mylocal /tmp/dvc_store
        //         dvc pull
                
        //         # 2. LINK TO PERMANENT HISTORY (The Trick)
        //         # Instead of deleting mlruns, we link it to the permanent folder
        //         # This way, Run 1, Run 2, Run 3... are all saved forever.
        //         ln -s /var/lib/jenkins/mlflow_history mlruns
                
        //         # 3. TRAIN
        //         # MLflow will now append the new run to the history
        //         python3 train.py
                
        //         # 4. UNLINK (Cleanup for Docker build)
        //         # We need to copy the *content* into the docker image, not the link
        //         rm mlruns
        //         cp -r /var/lib/jenkins/mlflow_history mlruns
        //         '''
        //     }
        // }

        // stage('Build Docker Images') {
        //     steps {
        //         echo 'Building Images (With Model Baked In)...'
        //         // The Dockerfile now copies the 'mlruns' folder we just created!
        //         sh "docker build -f Dockerfile.backend -t ${BACKEND_IMAGE}:${DOCKER_TAG} ."
        //         sh "docker build -f Dockerfile.frontend -t ${FRONTEND_IMAGE}:${DOCKER_TAG} ."
        //     }
        // }

        // stage('Push to Docker Hub') {
        //     steps {
        //         // Secure login using your existing credentials syntax
        //         sh """
        //         echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin
                
        //         # Push Backend
        //         docker push ${BACKEND_IMAGE}:${DOCKER_TAG}
                
        //         # Push Frontend
        //         docker push ${FRONTEND_IMAGE}:${DOCKER_TAG}
                
        //         docker logout
        //         """
        //     }
        // }

        // stage('Update Kubernetes') {
        //     steps {
        //         echo 'Applying new K8s Config...'
        //         // 1. Apply the YAML files (Updates config like removing volumes)
        //         sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig apply -f k8s-backend.yaml"
        //         sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig apply -f k8s-database.yaml"
        //         sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig apply -f k8s-frontend.yaml"
                
        //         // 2. Restart to pick up new images
        //         sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig rollout restart deployment/backend-deployment"
        //         sh "kubectl --kubeconfig=/var/lib/jenkins/kubeconfig rollout restart deployment/frontend-deployment"
        //     }
        // }
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