
// Jenkinsfile — the automation station.
// On every push: install deps, TRAIN + GATE on accuracy, run tests,
// build the image, push it, then (optionally) roll it out to EKS.
//
// The accuracy gate (train.py exits non-zero below threshold) is what makes
// this an ML pipeline rather than a plain app pipeline: a bad MODEL fails the
// build just like bad CODE would.

pipeline {
  agent any

  environment {
    AWS_REGION    = "ca-central-1"
    ECR_REPO_NAME = "churn-api"
    CLUSTER_NAME  = "churn-mlops"
    TAG           = "${env.BUILD_NUMBER}"
  }

  stages {
    stage('Setup') {
      steps {
        // Discover ECR URL from AWS — no hardcoded registry URL needed
        script {
          env.IMAGE = sh(
            script: "aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} --query 'repositories[0].repositoryUri' --output text",
            returnStdout: true
          ).trim()
        }
        // Connect kubectl to EKS cluster so Deploy stage can run
        sh "aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION}"
        // Install Python dependencies
        sh 'python3.13 -m venv venv'
        sh '. venv/bin/activate && pip install -r requirements.txt'
      }
    }

    stage('Train + Gate') {
      // train.py exits non-zero if accuracy < threshold -> stage fails here.
      steps {
        sh '. venv/bin/activate && python3 train.py'
      }
    }

    stage('Test') {
      steps {
        sh '. venv/bin/activate && pytest -q'
      }
    }

    stage('Build Image') {
      steps {
        sh "docker build -t \${IMAGE}:${TAG} -t \${IMAGE}:latest ."
      }
    }

    stage('Push Image') {
      steps {
        // ECR login via AWS CLI — no stored credentials needed
        sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin \${IMAGE}"
        sh "docker push \${IMAGE}:${TAG}"
        sh "docker push \${IMAGE}:latest"
      }
    }

    stage('Deploy to EKS') {
      steps {
        sh "kubectl set image deployment/churn-api churn-api=\${IMAGE}:${TAG}"
        sh "kubectl rollout status deployment/churn-api"
      }
    }
  }

  post {
    failure { echo 'Pipeline failed — model gate, tests, or deploy did not pass.' }
    success { echo "Shipped \${IMAGE}:${TAG} to EKS." }
  }
}
