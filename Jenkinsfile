pipeline {
    agent any

    environment {
        COMPOSE_PROJECT_NAME = 'cloud-native-cicd'
        GATEWAY_URL = 'http://localhost:8000'
    }

    stages {
        stage('1. Checkout Code') {
            steps {
                echo 'Pulling latest application & infrastructure code...'
                checkout scm
            }
        }

        stage('2. Build Microservice Images') {
            steps {
                echo 'Building Docker images for User, Order, and Payment services...'
                sh 'docker compose build'
            }
        }

        stage('3. Deploy Full Stack') {
            steps {
                echo 'Deploying 5-container stack via Docker Compose...'
                sh 'docker compose up -d --remove-orphans'
            }
        }

        stage('4. Automated Smoke Test') {
            steps {
                echo 'Waiting for API Gateway and services to stabilize...'
                sh '''
                    sleep 5
                    curl -sf ${GATEWAY_URL}/api/v1/users > /dev/null
                    curl -sf ${GATEWAY_URL}/api/v1/orders > /dev/null
                    curl -sf ${GATEWAY_URL}/api/v1/payments > /dev/null
                    echo "All microservices passed live smoke checks!"
                '''
            }
        }
    }

    post {
        success {
            echo 'CI/CD Pipeline succeeded! All 5 containers are live on port 8000.'
        }
        failure {
            echo 'Pipeline failed! Collecting container logs for debugging...'
            sh 'docker compose logs --tail=50'
        }
    }
}