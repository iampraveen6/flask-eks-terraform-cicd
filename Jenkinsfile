pipeline {
    agent any

    /* ---------------  GLOBAL PIPELINE CONFIG  --------------- */
    environment {
        /* AWS */
        AWS_REGION        = 'us-west-2'
        AWS_ACCOUNT_ID    = '975050024946'
        AWS_CREDENTIAL_ID = 'jenkins-aws-credentials'   // Jenkins credential id (AWS access-key/secret or IRSA)

        /* ECR */
        ECR_REPO_NAME     = 'flask-eks-demo-app'
        ECR_REPO          = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

        /* EKS */
        CLUSTER_NAME      = 'flask-eks-cluster'
        KUBECTL_NAMESPACE = 'default'                    // change if you deploy into a different namespace

        /* IMAGE */
        IMAGE_TAG         = "${BUILD_NUMBER}"
        DOCKER_FILE       = 'app/Dockerfile'             // Dockerfile location inside repo
        BUILD_CONTEXT     = 'app'                        // Docker build context path
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))   // keep last 10 builds
        // skipDefaultCheckout()                            // we explicitly checkout in stage 1
    }

    /* ---------------  STAGES  --------------- */
    stages {
        stage('Checkout') {
            steps {
                script { echo '--- Stage 1 : Checkout source from SCM ---' }
                checkout scm
                echo "Checked out revision : ${env.GIT_COMMIT.take(8)}  branch : ${env.GIT_BRANCH}"
            }
        }

        stage('Unit Tests') {
            steps {
                script { echo '--- Stage 2 : Run Python unit tests ---' }
                sh label: 'Install deps & test',
                   script: '''
                       cd app
                       python3 -m pip install --upgrade --user pip
                       python3 -m pip install --user -r requirements.txt
                       python3 -m unittest discover -s tests -v
                   '''
            }
            post { always { publishTestResults testResultsPattern: 'app/test-results.xml', allowEmptyResults: true } }
        }

        stage('Docker Build & Push') {
            steps {
                script { echo '--- Stage 3 : Build image and push to ECR ---' }
                withAWS(credentials: env.AWS_CREDENTIAL_ID, region: env.AWS_REGION) {
                    sh label: 'Docker build',
                       script: """
                           docker build -t flask-app:${IMAGE_TAG} -f ${DOCKER_FILE} ${BUILD_CONTEXT}
                           docker tag flask-app:${IMAGE_TAG} ${ECR_REPO}:${IMAGE_TAG}
                           docker tag flask-app:${IMAGE_TAG} ${ECR_REPO}:latest
                       """

                    sh label: 'ECR login & push',
                       script: """
                           aws ecr get-login-password --region ${AWS_REGION} | \
                           docker login --username AWS --password-stdin ${ECR_REPO}
                           docker push ${ECR_REPO}:${IMAGE_TAG}
                           docker push ${ECR_REPO}:latest
                       """
                }
            }
        }

        stage('Deploy to EKS') {
            steps {
                script { echo '--- Stage 4 : Deploy new image to EKS ---' }
                withAWS(credentials: env.AWS_CREDENTIAL_ID, region: env.AWS_REGION) {
                    sh label: 'Update kubeconfig',
                       script: "aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME} --alias ${CLUSTER_NAME}"

                    sh label: 'Rollout new image',
                       script: """
                           kubectl set image deployment/flask-app flask-app=${ECR_REPO}:${IMAGE_TAG} -n ${KUBECTL_NAMESPACE} --record
                           kubectl rollout status deployment/flask-app -n ${KUBECTL_NAMESPACE} --timeout=5m
                       """
                }
            }
        }

        stage('Post-Deployment Verification') {
            steps {
                script { echo '--- Stage 5 : Verify deployment & expose URL ---' }
                withAWS(credentials: env.AWS_CREDENTIAL_ID, region: env.AWS_REGION) {
                    sh label: 'Cluster status',
                       script: """
                           kubectl get deploy,po,svc -n ${KUBECTL_NAMESPACE} -l app=flask-app
                           LB_URL=\$(kubectl get svc flask-app-service -n ${KUBECTL_NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)
                           echo "LoadBalancer hostname : \${LB_URL}"
                           echo "\${LB_URL}" > lb_endpoint.txt
                       """
                }
                // expose URL in Jenkins UI
                archiveArtifacts artifacts: 'lb_endpoint.txt', allowEmptyArchive: true
            }
        }
    }

    /* ---------------  POST-BUILD ACTIONS  --------------- */
    post {
        success {
            echo '========================================='
            echo '✅  PIPELINE SUCCESS – APP DEPLOYED'
            echo '========================================='
            script {
                def url = readFile('lb_endpoint.txt').trim()
                if (url) {
                    echo "Application should be reachable soon at : http://${url}"
                    currentBuild.description = "Live @ http://${url}"
                }
            }
        }
        failure {
            echo '========================================='
            echo '❌  PIPELINE FAILED – CHECK LOGS'
            echo '========================================='
            withAWS(credentials: env.AWS_CREDENTIAL_ID, region: env.AWS_REGION) {
                sh label: 'Failure diagnostics',
                   script: """
                       echo '=== Deployment description ==='
                       kubectl describe deployment/flask-app -n ${KUBECTL_NAMESPACE} || true
                       echo '=== Recent pod logs ==='
                       kubectl logs -n ${KUBECTL_NAMESPACE} -l app=flask-app --tail=50 || true
                   """
            }
        }
        always {
            echo "Pipeline finished at : ${new Date()}"
            // clean workspace to save disk (optional)
            cleanWs()
        }
    }
}
