pipeline {
    agent any

    environment {
        // Existing credential ID
        DOCKER_CREDS = credentials('dockerhub_credentials')
        
        // Image Names
        BACKEND_IMAGE = "${DOCKER_CREDS_USR}/mlops-backend"
        FRONTEND_IMAGE = "${DOCKER_CREDS_USR}/mlops-frontend"
        DOCKER_TAG = "latest"

        // Ansible vault password
        ANSIBLE_VAULT_PASSWORD = credentials('rotpot_vault_pass')
        
        // Email for notifications
        EMAIL_ID = credentials('email_id')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('MLOps Pipeline: Configure, Build, Train, & Deploy on Host(s)') {
            steps {
                echo 'Executing full CI/CD pipeline on Ansible Host(s)...'

                sh '''
                    printf "%s" "$ANSIBLE_VAULT_PASSWORD" > vault-pass.txt

                    ansible-playbook \
                        -i ansible/inventory.ini \
                        ansible/playbook.yml \
                        --vault-password-file vault-pass.txt \
                        --extra-vars workspace="$WORKSPACE" \

                    rm -f vault-pass.txt
                '''
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