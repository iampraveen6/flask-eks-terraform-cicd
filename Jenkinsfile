pipeline {
    agent any

    environment {
        AWS_REGION     = 'us-west-2'
        AWS_ACCOUNT_ID = '975050024946'
        ECR_REPO       = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/flask-eks-demo-app"
        CLUSTER_NAME   = 'flask-eks-cluster'
        IMAGE_TAG      = "${BUILD_NUMBER}"
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps {
                script { echo '=== Stage 1: Checking out code from GitHub ===' }
                checkout scm
                echo 'Code checkout completed'
            }
        }

        stage('Test') {
            steps {
                script { echo '=== Stage 2: Running unit tests ===' }
                sh '''
                    cd app
                    python3 -m pip install --upgrade --user pip
                    python3 -m pip install --user -r requirements.txt
                    python3 -m unittest discover -s tests -v
                '''
                echo 'Tests completed successfully'
            }
        }

        stage('Build & Push') {
            steps {
                script { echo '=== Stage 3: Building and pushing Docker image ===' }
                sh '''
                    # build from Dockerfile inside app/
                    docker build -t flask-app:${IMAGE_TAG} -f app/Dockerfile app

                    # tag images
                    docker tag flask-app:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}
                    docker tag flask-app:${IMAGE_TAG} ${ECR_REPO}:latest

                    # ECR login & push
                    aws ecr get-login-password --region ${AWS_REGION} | \
                        docker login --username AWS --password-stdin ${ECR_REPO}

                    docker push ${ECR_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REPO}:latest
                '''
                echo 'Docker image built and pushed successfully'
            }
        }

        stage('Deploy to EKS') {
            steps {
                script { echo '=== Stage 4: Deploying to EKS cluster ===' }
                sh '''
                    aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}

                    # update deployment image
                    kubectl set image deployment/flask-app \
                        flask-app=${ECR_REPO}:${IMAGE_TAG} || \
                    kubectl apply -f k8s/deployment.yaml

                    # wait for rollout
                    kubectl rollout status deployment/flask-app --timeout=5m
                '''
                echo 'Deployment to EKS completed'
            }
        }

        stage('Verify') {
            steps {
                script { echo '=== Stage 5: Verifying deployment ===' }
                sh '''
                    kubectl get deployments
                    kubectl get pods
                    kubectl get services

                    echo "========================================="
                    echo "Application URL:"
                    kubectl get service flask-app-service \
                        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
                    echo ""
                    echo "========================================="
                '''
                echo 'Verification completed successfully'
            }
        }
    }

    post {
        success {
            echo '========================================='
            echo '✅ DEPLOYMENT SUCCESSFUL!'
            echo '========================================='
            script {
                sh '''
                    LB_URL=$(kubectl get service flask-app-service \
                        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null \
                        || echo "LoadBalancer URL not ready yet")
                    echo "Application accessible at: http://${LB_URL}"
                '''
            }
        }
        failure {
            echo '========================================='
            echo '❌ PIPELINE FAILED!'
            echo '========================================='
            sh '''
                echo "Deployment logs:"
                kubectl describe deployment/flask-app || true
                echo ""
                echo "Pod logs:"
                kubectl logs -l app=flask-app --tail=50 || true
            '''
        }
        always {
            echo "Pipeline execution completed at: ${new Date()}"
        }
    }
}        
