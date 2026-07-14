# Churn MLOps — Student Solution Guide (Day 1 to Day 4)

This is your step-by-step lab guide. Follow each day in order. Every command is copy-paste ready.

---

## Prerequisites

Before starting, make sure you have:

- Python 3.9+ installed (`python3 --version`)
- Docker installed and running (`docker --version`)
- Git installed (`git --version`)
- An AWS account with CLI configured (`aws sts get-caller-identity`)
- Terraform 1.5+ installed (`terraform --version`)
- kubectl installed (`kubectl version --client`)
- A Docker Hub account (https://hub.docker.com)

---

## Day 1 — Git + Docker

### Goal

Go from raw Python files to a running containerized ML API.

---

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd churn-predictor
```

---

### Step 2: Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verify:

```bash
python -c "import sklearn; print(sklearn.__version__)"
# Expected: 1.5.1
```

---

### Step 3: Train the Model

```bash
python train.py
```

Expected output:

```
Churn rate in data : 52.4%
Test accuracy      : 0.879
Accuracy threshold : 0.78
PASS: saved model.joblib
```

What just happened:
- Generated 5000 synthetic customer records
- Trained a Logistic Regression pipeline (StandardScaler + LogisticRegression)
- Accuracy (0.879) exceeded the threshold (0.78) — model was saved
- `model.joblib` now exists in your directory

Verify:

```bash
ls -lh model.joblib
# Should show the file, roughly 2-3 KB
```

---

### Step 4: Break the Accuracy Gate (Then Fix It)

Edit `train.py` — change line 24:

```python
ACCURACY_THRESHOLD = 0.99    # was 0.78
```

Run again:

```bash
python train.py
```

Expected output:

```
Churn rate in data : 52.4%
Test accuracy      : 0.879
Accuracy threshold : 0.99
FAIL: accuracy 0.879 < threshold 0.99. Refusing to save a sub-par model.
```

The script exited with an error. No model was saved. This is the quality gate.

Now revert — change it back:

```python
ACCURACY_THRESHOLD = 0.78
```

---

### Step 5: Start the API Server

```bash
uvicorn app:app --reload --port 8000
```

Expected output:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Open your browser: http://localhost:8000/docs

You should see the interactive Swagger UI with two endpoints:
- `GET /health`
- `POST /predict`

---

### Step 6: Test the API Manually

Open a **new terminal** (keep the server running) and run:

**Health check:**

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "trained_accuracy": 0.879}
```

**Predict — high-risk customer:**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tenure_months": 2,
    "monthly_charges": 95.0,
    "total_charges": 190.0,
    "contract_type": 0,
    "has_tech_support": 0,
    "has_online_security": 0,
    "is_electronic_check": 1
  }'
```

Expected:

```json
{"churn": true, "churn_probability": 0.9976}
```

**Predict — low-risk customer:**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tenure_months": 60,
    "monthly_charges": 40.0,
    "total_charges": 2400.0,
    "contract_type": 2,
    "has_tech_support": 1,
    "has_online_security": 1,
    "is_electronic_check": 0
  }'
```

Expected: churn_probability should be very low (close to 0).

**Predict — bad input (validation test):**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tenure_months": 2,
    "monthly_charges": 95.0,
    "total_charges": 190.0,
    "contract_type": 9,
    "has_tech_support": 0,
    "has_online_security": 0,
    "is_electronic_check": 1
  }'
```

Expected: HTTP 422 error — `contract_type` must be 0, 1, or 2.

---

### Step 7: Run Automated Tests

Stop the server (Ctrl+C), then run:

```bash
pytest -q
```

Expected:

```
....                                                                     [100%]
4 passed in 1.20s
```

What each test does:
- `test_health_ok` — GET /health returns 200 with "ok"
- `test_predict_response_shape` — POST /predict returns churn + churn_probability
- `test_validation_rejects_bad_input` — contract_type=9 returns 422
- `test_model_behaves_sensibly` — high-risk customer scores higher than low-risk

---

### Step 8: Build the Docker Image

```bash
docker build -t churn-api:latest .
```

Watch the output — each step in the Dockerfile runs:
1. Pulls `python:3.12-slim`
2. Installs dependencies
3. Copies source files
4. Runs `python train.py` inside the image
5. Image is ready

Verify:

```bash
docker images | grep churn-api
# Should show churn-api with tag "latest"
```

---

### Step 9: Run the Container

```bash
docker run -p 8000:8000 churn-api:latest
```

Test it (in another terminal):

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "trained_accuracy": 0.879}
```

Same API, now running inside a container. Stop it with Ctrl+C.

---

### Step 10: Push to Docker Hub

```bash
# Log in to Docker Hub
docker login

# Tag with your username
docker tag churn-api:latest <your-dockerhub-username>/churn-api:latest

# Push
docker push <your-dockerhub-username>/churn-api:latest
```

Verify: go to https://hub.docker.com — you should see your `churn-api` repository.

---

### Step 11: Initialize Git (if not already done)

```bash
git init
git add .
git status
```

Verify that `model.joblib` is NOT listed (it's in `.gitignore`).

```bash
git commit -m "Day 1: churn prediction API with Docker"
```

---

### Day 1 Checklist

- [ ] Python environment set up, dependencies installed
- [ ] Model trained successfully (accuracy > 0.78)
- [ ] Accuracy gate tested (broke it, then fixed it)
- [ ] API running locally, tested all 3 scenarios (high-risk, low-risk, bad input)
- [ ] All 4 pytest tests passing
- [ ] Docker image built and running
- [ ] Image pushed to Docker Hub
- [ ] Code committed to Git

---

## Day 2 — Jenkins CI/CD

### Goal

Automate everything from Day 1 so a `git push` triggers: train, test, build, push, and deploy — with no human steps.

---

### Step 1: Start Jenkins

```bash
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```

Note: Mounting `docker.sock` lets Jenkins build Docker images. In production, you'd use a dedicated Docker agent instead.

---

### Step 2: Get the Initial Admin Password

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Copy the password.

---

### Step 3: Set Up Jenkins

1. Open http://localhost:8080
2. Paste the admin password
3. Click **Install suggested plugins** — wait for installation
4. Create your admin user (or skip and continue as admin)
5. Set the Jenkins URL (keep the default http://localhost:8080)
6. Click **Start using Jenkins**

---

### Step 4: Install Required Plugins

Go to **Manage Jenkins > Plugins > Available plugins**

Search and install:
- **Docker Pipeline**
- **Pipeline** (usually pre-installed)

Restart Jenkins if prompted.

---

### Step 5: Add Docker Hub Credentials

1. Go to **Manage Jenkins > Credentials > System > Global credentials**
2. Click **Add Credentials**
3. Kind: **Username with password**
4. Username: your Docker Hub username
5. Password: your Docker Hub password or access token
6. ID: `registry-credentials` (must match the Jenkinsfile)
7. Click **Create**

---

### Step 6: Update the Jenkinsfile

Edit `Jenkinsfile` — change line 13:

```groovy
IMAGE = "<your-dockerhub-username>/churn-api"    // was REPLACE_ME/churn-api
```

Commit and push:

```bash
git add Jenkinsfile
git commit -m "Day 2: configure Jenkinsfile with Docker Hub username"
git push
```

---

### Step 7: Create the Pipeline Job

1. From the Jenkins dashboard, click **New Item**
2. Name: `churn-api`
3. Type: **Pipeline**
4. Click **OK**
5. Scroll to **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: your Git repo URL
   - Branch: `*/main` (or `*/master`)
   - Script Path: `Jenkinsfile`
6. Click **Save**

---

### Step 8: Run the Pipeline

Click **Build Now**.

Watch the **Stage View** — each stage should light up green:

```
Setup [green] > Train + Gate [green] > Test [green] > Build Image [green] > Push Image [green] > Deploy to EKS [green]
```

Note: The **Deploy to EKS** stage will fail if you haven't set up EKS yet — that's expected. It will work after Day 3.

Click on any stage to see console output.

---

### Step 9: Verify the Train + Gate Stage

Click into the **Train + Gate** stage console. You should see:

```
Churn rate in data : 52.4%
Test accuracy      : 0.879
Accuracy threshold : 0.78
PASS: saved model.joblib
```

---

### Step 10: Verify the Test Stage

Click into the **Test** stage console:

```
....                                                                     [100%]
4 passed in 1.20s
```

---

### Step 11: Break the Pipeline (Demo the Gate)

Edit `train.py` — change:

```python
ACCURACY_THRESHOLD = 0.99
```

Commit and push:

```bash
git add train.py
git commit -m "Raise threshold to 0.99 (will fail)"
git push
```

Go to Jenkins — a new build triggers automatically (or click **Build Now**).

Watch the Stage View:

```
Setup [green] > Train + Gate [RED] > Test [not run] > Build [not run] > Push [not run] > Deploy [not run]
```

The pipeline stopped at **Train + Gate**. Click into it:

```
FAIL: accuracy 0.879 < threshold 0.99. Refusing to save a sub-par model.
```

Key observation: **No image was built. Nothing was pushed. Nothing was deployed.** The bad model was caught.

---

### Step 12: Fix and Re-run

Revert `train.py`:

```python
ACCURACY_THRESHOLD = 0.78
```

Commit and push:

```bash
git add train.py
git commit -m "Revert threshold to 0.78"
git push
```

Watch Jenkins — all stages go green again.

---

### Step 13: Verify the Image Was Pushed

Go to https://hub.docker.com and check your `churn-api` repository. You should see a new tag matching the Jenkins build number (e.g., `2`, `3`).

---

### Day 2 Checklist

- [ ] Jenkins running locally via Docker
- [ ] Docker Hub credentials configured in Jenkins
- [ ] Jenkinsfile updated with your Docker Hub username
- [ ] Pipeline job created, pointing to your Git repo
- [ ] First build ran successfully (all green stages)
- [ ] Broke the accuracy gate — saw the pipeline fail at Train + Gate
- [ ] Fixed the gate — pipeline went green again
- [ ] Verified image was pushed to Docker Hub with build number tag

---

## Day 3 — Terraform (Provision AWS Infrastructure)

### Goal

Use Infrastructure as Code to provision ECR (container registry), VPC (network), and EKS (Kubernetes cluster) on AWS.

---

### Step 1: Verify AWS CLI Access

```bash
aws sts get-caller-identity
```

Expected: your AWS account ID and user/role ARN. If this fails, configure your credentials:

```bash
aws configure
```

Enter your Access Key ID, Secret Access Key, region (`ca-central-1`), and output format (`json`).

---

### Step 2: Verify Terraform

```bash
terraform --version
```

Expected: v1.5.0 or higher.

---

### Step 3: Review the Terraform Files

Before running anything, understand what you're about to create:

```bash
ls *.tf
```

```
ecr.tf          # Container registry (where Docker images are stored)
main.tf         # VPC (network) + EKS (Kubernetes cluster)
variables.tf    # Input parameters (region, cluster name, K8s version)
versions.tf     # Provider configuration (AWS, version constraints)
outputs.tf      # Values printed after creation (ECR URL, kubectl command)
```

---

### Step 4: Initialize Terraform

```bash
terraform init
```

Expected output:

```
Initializing provider plugins...
- Installing hashicorp/aws v5.x.x...

Terraform has been successfully initialized!
```

This downloads the AWS provider and the VPC/EKS modules.

---

### Step 5: Preview the Plan

```bash
terraform plan
```

Review the output. You should see something like:

```
Plan: 47 to add, 0 to change, 0 to destroy.
```

Key resources being created:
- 1 ECR repository
- 1 VPC with 4 subnets (2 public, 2 private)
- 1 NAT Gateway
- 1 Internet Gateway
- 1 EKS cluster
- 1 EKS managed node group (2 t3.medium instances)
- Multiple IAM roles and security groups

---

### Step 6: Apply (Create Everything)

```bash
terraform apply
```

When prompted, type `yes` and press Enter.

This will take **15-20 minutes** (mostly the EKS cluster). You'll see resources being created one by one.

Expected final output:

```
Apply complete! Resources: 47 added, 0 changed, 0 destroyed.

Outputs:

cluster_name = "churn-mlops"
configure_kubectl = "aws eks update-kubeconfig --name churn-mlops --region ca-central-1"
ecr_repository_url = "123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api"
```

Save these output values — you'll need them.

---

### Step 7: Connect kubectl to the Cluster

Copy the `configure_kubectl` output and run it:

```bash
aws eks update-kubeconfig --name churn-mlops --region ca-central-1
```

Expected:

```
Added new context arn:aws:eks:ca-central-1:123456789012:cluster/churn-mlops to /Users/<you>/.kube/config
```

---

### Step 8: Verify the Cluster

```bash
kubectl get nodes
```

Expected:

```
NAME                                        STATUS   ROLES    AGE   VERSION
ip-10-0-1-xx.ca-central-1.compute.internal  Ready    <none>   5m    v1.30.x
ip-10-0-2-xx.ca-central-1.compute.internal  Ready    <none>   5m    v1.30.x
```

Two nodes, both `Ready`. Your cluster is live.

---

### Step 9: Push Your Image to ECR

Authenticate Docker with ECR:

```bash
aws ecr get-login-password --region ca-central-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.ca-central-1.amazonaws.com
```

(Replace `123456789012` with your actual AWS account ID from the terraform output.)

Tag and push:

```bash
# Tag your existing image for ECR
docker tag churn-api:latest 123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api:latest

# Push
docker push 123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api:latest
```

---

### Step 10: Verify the Image in ECR

```bash
aws ecr list-images --repository-name churn-api --region ca-central-1
```

Expected:

```json
{
    "imageIds": [
        {
            "imageDigest": "sha256:...",
            "imageTag": "latest"
        }
    ]
}
```

---

### Step 11: View All Outputs

```bash
terraform output
```

Keep these values handy for Day 4:
- `ecr_repository_url` — goes in `deployment.yaml`
- `configure_kubectl` — connects your terminal to the cluster

---

### Day 3 Checklist

- [ ] AWS CLI configured and working
- [ ] Terraform initialized successfully
- [ ] Reviewed the plan (47 resources)
- [ ] Applied — ECR, VPC, and EKS created
- [ ] kubectl connected to the cluster
- [ ] 2 nodes showing `Ready`
- [ ] Docker image pushed to ECR
- [ ] Image verified in ECR

---

## Day 4 — Kubernetes (EKS Deployment)

### Goal

Deploy the churn API onto the EKS cluster with replicas, health checks, load balancing, self-healing, and auto-scaling. Close the full loop.

---

### Step 1: Verify Cluster Access

```bash
kubectl get nodes
```

Should show 2 nodes in `Ready` state. If not, run the `configure_kubectl` command from Day 3.

---

### Step 2: Update the Deployment Image

Edit `deployment.yaml` — change line 21:

```yaml
image: 123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api:latest
```

Replace with your actual ECR URL from `terraform output ecr_repository_url`.

---

### Step 3: Apply All Kubernetes Manifests

```bash
kubectl apply -f configmap.yaml -f deployment.yaml -f service.yaml
```

Expected:

```
configmap/churn-api-config created
deployment.apps/churn-api created
service/churn-api created
```

---

### Step 4: Watch Pods Come Up

```bash
kubectl get pods -w
```

Expected progression:

```
NAME                        READY   STATUS              RESTARTS   AGE
churn-api-7d4f8b6c9-abc12   0/1     ContainerCreating   0          2s
churn-api-7d4f8b6c9-def34   0/1     ContainerCreating   0          2s
churn-api-7d4f8b6c9-abc12   1/1     Running             0          15s
churn-api-7d4f8b6c9-def34   1/1     Running             0          18s
```

Wait until both pods show `1/1 Running`. Press Ctrl+C to stop watching.

---

### Step 5: Get the Load Balancer URL

```bash
kubectl get svc churn-api
```

Expected:

```
NAME        TYPE           CLUSTER-IP     EXTERNAL-IP                                          PORT(S)
churn-api   LoadBalancer   10.100.45.67   a1b2c3-1234.ca-central-1.elb.amazonaws.com           80:31234/TCP
```

The `EXTERNAL-IP` is your production URL. It may take 1-2 minutes to provision — if it shows `<pending>`, wait and run the command again.

Save this URL:

```bash
export API_URL="http://<your-EXTERNAL-IP>"
```

---

### Step 6: Test the Production Endpoint

**Health check:**

```bash
curl $API_URL/health
```

Expected:

```json
{"status": "ok", "trained_accuracy": 0.879}
```

**Prediction — high-risk customer:**

```bash
curl -X POST $API_URL/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tenure_months": 2,
    "monthly_charges": 95.0,
    "total_charges": 190.0,
    "contract_type": 0,
    "has_tech_support": 0,
    "has_online_security": 0,
    "is_electronic_check": 1
  }'
```

Expected:

```json
{"churn": true, "churn_probability": 0.9976}
```

Same result as Day 1, now running on a Kubernetes cluster in AWS.

---

### Step 7: Explore the Deployment

**View all resources:**

```bash
kubectl get all
```

**View pod details:**

```bash
kubectl describe pod -l app=churn-api
```

Look for the Events section — you should see:
- Scheduled
- Pulling image
- Created container
- Started container
- Readiness probe passed

**View logs:**

```bash
kubectl logs -l app=churn-api --tail=20
```

---

### Step 8: Demo — Self-Healing

Open two terminals.

**Terminal 1 — watch pods:**

```bash
kubectl get pods -w
```

**Terminal 2 — kill a pod:**

```bash
kubectl delete pod -l app=churn-api --wait=false | head -1
```

(This deletes the first pod matching the label.)

**Watch Terminal 1:**

```
churn-api-7d4f8b6c9-abc12   1/1     Terminating   0     5m
churn-api-7d4f8b6c9-ghi56   0/1     Pending       0     0s
churn-api-7d4f8b6c9-ghi56   0/1     ContainerCreating   0   1s
churn-api-7d4f8b6c9-ghi56   1/1     Running       0     15s
```

Kubernetes detected the missing pod and created a replacement. The other pod kept serving traffic the entire time.

**Verify the API is still working:**

```bash
curl $API_URL/health
```

Still returns `200 OK`. Zero downtime.

---

### Step 9: Demo — Manual Scaling

Scale up to 4 replicas:

```bash
kubectl scale deployment churn-api --replicas=4
```

Watch:

```bash
kubectl get pods -w
```

Two new pods appear. Verify:

```bash
kubectl get pods
```

Should show 4 pods, all `1/1 Running`.

Scale back down:

```bash
kubectl scale deployment churn-api --replicas=2
```

Two pods are terminated. Back to 2.

---

### Step 10: Demo — Rolling Update

Make a visible change to the API. Edit `app.py` — change the version:

```python
app = FastAPI(title="Churn Prediction API", version="2.0.0")
```

Build and push a new image:

```bash
docker build -t 123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api:v2 .
docker push 123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api:v2
```

Update the deployment:

```bash
kubectl set image deployment/churn-api \
  churn-api=123456789012.dkr.ecr.ca-central-1.amazonaws.com/churn-api:v2
```

Watch the rollout:

```bash
kubectl rollout status deployment/churn-api
```

Expected:

```
Waiting for deployment "churn-api" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "churn-api" rollout to finish: 1 old replicas are pending termination...
deployment "churn-api" successfully rolled out
```

During the rollout, the API never went down — old pods served traffic until new pods were ready.

---

### Step 11: Demo — Rollback

Something wrong with v2? Roll back:

```bash
kubectl rollout undo deployment/churn-api
```

Watch:

```bash
kubectl rollout status deployment/churn-api
```

You're back on the previous image. Verify:

```bash
curl $API_URL/health
```

---

### Step 12: (Optional) Apply the HPA — Auto-Scaling

First, install the metrics server (required for HPA):

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Wait a minute, then apply the HPA:

```bash
kubectl apply -f hpa.yaml
```

Check the HPA status:

```bash
kubectl get hpa
```

Expected:

```
NAME        REFERENCE              TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
churn-api   Deployment/churn-api   10%/60%   2         6         2          30s
```

The HPA is watching CPU utilization. If average CPU exceeds 60%, it will add pods (up to 6). If it drops, it removes pods (down to 2).

---

### Step 13: View the Complete System

```bash
kubectl get all
```

You should see:
- 2 pods (running)
- 1 deployment (2/2 ready)
- 1 replicaset
- 1 service (LoadBalancer with external IP)
- 1 HPA (if applied)

---

### Step 14: The Full Loop — Git Push to Production

This is the complete workflow:

```bash
# 1. Make a code change
#    (edit train.py, app.py, or test_app.py)

# 2. Test locally
python train.py
pytest -q

# 3. Commit and push
git add .
git commit -m "Your change description"
git push

# 4. Jenkins takes over automatically:
#    Setup > Train+Gate > Test > Build > Push > Deploy

# 5. Verify in production
curl $API_URL/predict -X POST \
  -H "Content-Type: application/json" \
  -d '{"tenure_months":2,"monthly_charges":95,"total_charges":190,"contract_type":0,"has_tech_support":0,"has_online_security":0,"is_electronic_check":1}'
```

---

### Step 15: Teardown (IMPORTANT — Saves Money)

**Delete Kubernetes resources first** (removes the Load Balancer):

```bash
kubectl delete -f hpa.yaml          # if applied
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
kubectl delete -f configmap.yaml
```

Or all at once:

```bash
kubectl delete -f configmap.yaml -f deployment.yaml -f service.yaml -f hpa.yaml
```

**Destroy Terraform infrastructure:**

```bash
terraform destroy
```

Type `yes` when prompted. Wait ~10 minutes.

**Verify everything is gone:**

```bash
terraform show
# Should show empty state
```

**Stop Jenkins:**

```bash
docker stop jenkins
docker rm jenkins
```

---

### Day 4 Checklist

- [ ] Cluster access verified (2 nodes ready)
- [ ] deployment.yaml updated with ECR image URL
- [ ] All manifests applied (ConfigMap, Deployment, Service)
- [ ] 2 pods running, both 1/1 Ready
- [ ] Load Balancer URL obtained
- [ ] Production endpoint tested (health + predict)
- [ ] Self-healing demo — killed a pod, watched it recover
- [ ] Manual scaling — scaled to 4, then back to 2
- [ ] Rolling update — deployed v2 with zero downtime
- [ ] Rollback — reverted to previous version
- [ ] (Optional) HPA applied and monitoring CPU
- [ ] Full loop demonstrated (git push to production)
- [ ] Teardown complete (kubectl delete + terraform destroy + jenkins stopped)

---

## Quick Reference — Key Commands

### Python / API

```bash
python train.py                              # Train the model
uvicorn app:app --reload --port 8000         # Start local server
pytest -q                                    # Run tests
```

### Docker

```bash
docker build -t churn-api:latest .           # Build image
docker run -p 8000:8000 churn-api:latest     # Run container
docker push <user>/churn-api:latest          # Push to registry
```

### Terraform

```bash
terraform init                               # Initialize
terraform plan                               # Preview changes
terraform apply                              # Create resources
terraform output                             # Show outputs
terraform destroy                            # Delete everything
```

### Kubernetes

```bash
kubectl apply -f <file.yaml>                 # Apply manifest
kubectl get pods                             # List pods
kubectl get pods -w                          # Watch pods
kubectl get svc                              # List services
kubectl logs -l app=churn-api                # View logs
kubectl describe pod <name>                  # Pod details
kubectl delete pod <name>                    # Kill a pod
kubectl scale deployment churn-api --replicas=N   # Scale
kubectl set image deployment/churn-api churn-api=<image>  # Update
kubectl rollout status deployment/churn-api  # Watch rollout
kubectl rollout undo deployment/churn-api    # Rollback
kubectl get hpa                              # Check autoscaler
```

---

## Troubleshooting

### "model.joblib not found" when starting app.py

Run `python train.py` first. The model must be trained before the API can start.

### Docker build fails at "pip install"

Make sure `requirements.txt` exists and has correct package versions. Try `pip install -r requirements.txt` locally first.

### kubectl can't connect to cluster

Re-run: `aws eks update-kubeconfig --name churn-mlops --region ca-central-1`

### Pods stuck in ImagePullBackOff

The image URL in `deployment.yaml` is wrong, or ECR authentication expired. Verify with:

```bash
kubectl describe pod -l app=churn-api
```

Check the Events section for the exact error.

### Load Balancer EXTERNAL-IP shows `<pending>`

Wait 1-2 minutes. ELB provisioning takes time. If it stays pending, check:

```bash
kubectl describe svc churn-api
```

### HPA shows `<unknown>/60%` for targets

The metrics-server isn't installed or hasn't started collecting data yet. Wait 1-2 minutes after installing it.

### terraform destroy fails

Some resources may have dependencies. Run `kubectl delete -f k8s/` first to remove the Load Balancer, then retry `terraform destroy`.
