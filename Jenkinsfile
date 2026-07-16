// Jenkinsfile — the automation station.
// Train + upload model to S3, then build a code-only image and deploy.
// Jenkins only needs Docker, AWS CLI, and kubectl — no Python required.

pipeline {
  agent any

  environment {
    AWS_REGION      = "ca-central-1"
    ECR_REPO_NAME   = "churn-api"
    CLUSTER_NAME    = "churn-mlops"
    MODEL_S3_BUCKET = "churn-mlops-models"
    TAG             = "${env.BUILD_NUMBER}"
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

    stage('Train + Upload') {
      // Train the model and upload to S3.
      // If accuracy < threshold, train.py exits non-zero → stage fails → pipeline stops.
      steps {
        sh """
          docker run --rm \
            -e MODEL_S3_BUCKET=${MODEL_S3_BUCKET} \
            -e AWS_ACCESS_KEY_ID=\$(aws configure get aws_access_key_id) \
            -e AWS_SECRET_ACCESS_KEY=\$(aws configure get aws_secret_access_key) \
            -e AWS_DEFAULT_REGION=${AWS_REGION} \
            -v \$(pwd):/work -w /work \
            python:3.12-slim \
            bash -c "pip install -q -r requirements.txt && python train.py"
        """
      }
    }

    stage('Build Image') {
      // Builds a code-only image — model is NOT inside, it comes from S3.
      steps {
        sh "docker build -t \${IMAGE}:${TAG} -t \${IMAGE}:latest ."
      }
    }

    stage('Test') {
      // Run tests inside a container with the model downloaded from S3.
      steps {
        sh """
          docker run --rm \
            -e MODEL_S3_BUCKET=${MODEL_S3_BUCKET} \
            -e AWS_ACCESS_KEY_ID=\$(aws configure get aws_access_key_id) \
            -e AWS_SECRET_ACCESS_KEY=\$(aws configure get aws_secret_access_key) \
            -e AWS_DEFAULT_REGION=${AWS_REGION} \
            \${IMAGE}:${TAG} \
            python -m pytest -q
        """
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
