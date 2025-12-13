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
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    cd app
                    python3 -m pip install --user -r requirements.txt
                    python3 -m unittest discover -s tests -v
                '''
            }
        }

        stage('Build & Push') {
            steps {
                withAWS(credentials: 'jenkins-aws-credentials', region: env.AWS_REGION) {
                    sh '''
                        docker build -t flask-app:${IMAGE_TAG} -f app/Dockerfile app
                        docker tag flask-app:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}
                        aws ecr get-login-password | docker login --username AWS --password-stdin ${ECR_REPO}
                        docker push ${ECR_REPO}:${IMAGE_TAG}
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withAWS(credentials: 'jenkins-aws-credentials', region: env.AWS_REGION) {
                    sh '''
                        aws eks update-kubeconfig --name ${CLUSTER_NAME}
                        kubectl set image deployment/flask-app flask-app=${ECR_REPO}:${IMAGE_TAG}
                        kubectl rollout status deployment/flask-app --timeout=5m
                    '''
                }
            }
        }
    }

    post {
        success {
            echo '✅ DEPLOYMENT SUCCESSFUL'
            script {
                withAWS(credentials: 'jenkins-aws-credentials', region: env.AWS_REGION) {
                    def url = sh(
                        script: "kubectl get svc flask-app-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true",
                        returnStdout: true
                    ).trim()
                    if (url) echo "Application URL: http://${url}"
                }
            }
        }
        failure {
            echo '❌ PIPELINE FAILED'
            withAWS(credentials: 'jenkins-aws-credentials', region: env.AWS_REGION) {
                sh '''
                    kubectl describe deployment/flask-app || true
                    kubectl logs -l app=flask-app --tail=30 || true
                '''
            }
        }
        always {
            echo "Pipeline finished at: ${new Date()}"
            cleanWs()
        }
    }
}