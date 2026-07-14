// Jenkinsfile — the automation station.
// All Python work (train, test) runs INSIDE Docker containers,
// so Jenkins only needs Docker, AWS CLI, and kubectl — no Python required.

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
      }
    }

    stage('Build Image') {
      // Docker build installs deps + trains the model (RUN python train.py).
      // If accuracy < threshold, train.py exits non-zero and the build FAILS.
      // This IS the quality gate — baked right into the Docker build.
      steps {
        sh "docker build -t \${IMAGE}:${TAG} -t \${IMAGE}:latest ."
      }
    }

    stage('Test') {
      // Run tests inside the built image — guaranteed same Python + deps
      steps {
        sh "docker run --rm \${IMAGE}:${TAG} python -m pytest -q"
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
