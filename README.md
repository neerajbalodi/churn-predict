# Churn MLOps — End-to-End Teaching Project

One small project that travels through **Git → Docker → Jenkins → Terraform → Kubernetes (EKS)**.
The data science is deliberately tiny so the engineering can be serious. The app
is intentionally **stateless** (no DB, no cache) — it loads a model into memory
and answers prediction requests.

## What's in here

| File / dir | What it is | Course day |
|---|---|---|
| `train.py` | Generates synthetic churn data, trains a model, **gates on accuracy**, saves `model.joblib` | Day 1 |
| `app.py` | FastAPI service: `/health` + `/predict`. Loads the model, serves predictions | Day 1 |
| `test_app.py` | Endpoint tests **and** a behavioral model test (Jenkins runs these) | Day 1–2 |
| `requirements.txt` | Pinned dependencies | Day 1 |
| `Dockerfile` | Packages the API; trains the model at build time so the image is self-contained | Day 1 |
| `Jenkinsfile` | CI/CD: setup → **train+gate** → test → build → push → deploy | Day 2 |
| `terraform/` | ECR repo (read line-by-line) + VPC/EKS via official modules (apply) | Day 3 |
| `k8s/` | Deployment, Service, ConfigMap, optional HPA | Day 4 |

The model file is a **build artifact, not source** — it's in `.gitignore`. That's
the DVC lesson in miniature: code goes in Git, models don't.

---

## Day 1 — Git + Docker

```bash
# Run it the "naked" way first — feel "works on my machine"
pip install -r requirements.txt
python train.py                       # -> model.joblib, prints accuracy vs gate
uvicorn app:app --reload --port 8000
# open http://localhost:8000/docs  (interactive Swagger UI)
```

Predict:
```bash
curl -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{
  "tenure_months": 2, "monthly_charges": 95.0, "total_charges": 190.0,
  "contract_type": 0, "has_tech_support": 0, "has_online_security": 0,
  "is_electronic_check": 1
}'
# -> {"churn": true, "churn_probability": 0.99...}
```

Then containerize:
```bash
docker build -t <dockerhub-user>/churn-api:latest .
docker run -p 8000:8000 <dockerhub-user>/churn-api:latest
docker push <dockerhub-user>/churn-api:latest
```

## Day 2 — Jenkins

Point a Jenkins job at this repo using `Jenkinsfile`. **Demo the gate:** raise
`ACCURACY_THRESHOLD` in `train.py` above the real accuracy, push, watch the
build fail at the *Train + Gate* stage. That's ML CI in one move.

## Day 3 — Terraform (provision cloud)

```bash
cd terraform
terraform init
terraform apply        # creates ECR + VPC + EKS (~15-20 min for EKS)
aws eks update-kubeconfig --name churn-mlops --region ca-central-1
kubectl get nodes
```
> Tip: kick off `apply` at a break so the cluster is warm. Keep a
> pre-provisioned backup cluster in case the lab apply goes sideways.

## Day 4 — Kubernetes (EKS)

Edit `k8s/deployment.yaml` — replace `REPLACE_ME/churn-api:latest` with your
image (Docker Hub or the ECR URL from `terraform output`). Then:

```bash
kubectl apply -f k8s/
kubectl get pods -w                   # watch them come up
kubectl get svc churn-api             # grab the LoadBalancer URL

# self-healing demo: kill a pod, watch Kubernetes replace it
kubectl delete pod -l app=churn-api --field-selector ...   # or just one pod
```

Close the loop: `git push` → Jenkins builds & pushes a new image → 
`kubectl set image` rolls it out. Same app, now in production.

---

## The mental model for students

The app never fundamentally changes. It just gets **packaged** (Docker),
**automated** (Jenkins), **given a home** (Terraform), and **run at scale**
(Kubernetes). Same churn predictor on Day 1 and Day 4 — just wearing more and
more infrastructure.

## Teardown (do this — it saves real money)

```bash
kubectl delete -f k8s/
cd terraform && terraform destroy
```

## What's intentionally NOT here

No database, Redis, or message queue — they'd add components to debug without
teaching a new DevOps tool. If you want students to see the fuller picture,
draw it on a whiteboard: API + DB + cache + queue, each box another Deployment
or StatefulSet. Free, no debugging.
# churn-predict
