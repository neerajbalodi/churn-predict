# Day 1 — Command Reference

Every command you'll run on Day 1, in order, with explanations.

---

## Setup

### 1. Check Python version

```bash
python3 --version
```

What it does: Confirms Python 3.9+ is installed. If this fails, Python isn't installed or isn't in your PATH.

---

### 2. Check Docker is running

```bash
docker --version
```

What it does: Confirms Docker CLI is installed. If Docker Desktop isn't running, later commands will fail with "daemon not running."

---

### 3. Check Git is installed

```bash
git --version
```

What it does: Confirms Git is available.

---

## Python Environment

### 4. Create a virtual environment

```bash
python3 -m venv venv
```

What it does: Creates an isolated Python environment in a `venv/` folder. This keeps project dependencies separate from your system Python — no conflicts with other projects.

---

### 5. Activate the virtual environment

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

What it does: Switches your shell to use the isolated Python. Your terminal prompt will show `(venv)` at the start. All `pip install` and `python` commands now use this environment.

---

### 6. Install dependencies

```bash
pip install -r requirements.txt
```

What it does: Reads `requirements.txt` and installs all 9 packages (FastAPI, uvicorn, scikit-learn, pandas, numpy, pydantic, joblib, httpx, pytest) with their exact pinned versions. Takes ~30 seconds.

---

### 7. Verify scikit-learn installed correctly

```bash
python -c "import sklearn; print(sklearn.__version__)"
```

What it does: Imports scikit-learn and prints its version. Expected output: `1.5.1`. If this fails, the pip install had a problem.

---

## Model Training

### 8. Train the model

```bash
python train.py
```

What it does:
1. Generates 5000 synthetic customer records
2. Splits into 80% train / 20% test
3. Trains a StandardScaler + LogisticRegression pipeline
4. Evaluates accuracy on the test set
5. Checks accuracy (0.879) against the threshold (0.78)
6. Saves the model, feature list, and accuracy to `model.joblib`

Expected output:

```
Churn rate in data : 52.4%
Test accuracy      : 0.879
Accuracy threshold : 0.78
PASS: saved model.joblib
```

---

### 9. Verify the model file was created

```bash
ls -lh model.joblib
```

What it does: Lists the model file with its size. Expected: a file of ~2-3 KB. If this file doesn't exist, training failed.

---

### 10. Break the accuracy gate (teaching demo)

Edit `train.py` line 24 — change `0.78` to `0.99`, then run:

```bash
python train.py
```

What it does: Trains the same model, but now the threshold is 0.99. Accuracy (0.879) is below 0.99, so the script exits with an error and refuses to save the model. This demonstrates the quality gate.

Expected output:

```
FAIL: accuracy 0.879 < threshold 0.99. Refusing to save a sub-par model.
```

Revert `train.py` back to `0.78` after this demo.

---

## Running the API

### 11. Start the API server

```bash
uvicorn app:app --reload --port 8000
```

What it does:
- `uvicorn` — the ASGI server that runs FastAPI apps
- `app:app` — load the `app` object from `app.py`
- `--reload` — auto-restart when code changes (dev mode only)
- `--port 8000` — listen on port 8000

At startup, `app.py` loads `model.joblib` into memory. The API is now ready at http://localhost:8000.

---

### 12. Open the Swagger UI

```bash
open http://localhost:8000/docs
```

On Linux:

```bash
xdg-open http://localhost:8000/docs
```

What it does: Opens the browser to FastAPI's auto-generated interactive documentation. You can test both endpoints directly from this page.

---

### 13. Health check

```bash
curl http://localhost:8000/health
```

What it does: Sends a GET request to the /health endpoint. Returns the API status and the model's training accuracy. On Day 4, Kubernetes uses this endpoint to detect if a pod is alive.

Expected output:

```json
{"status": "ok", "trained_accuracy": 0.879}
```

---

### 14. Predict — high-risk customer

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

What it does: Sends customer data to the /predict endpoint.
- `curl -X POST` — make a POST request
- `-H "Content-Type: application/json"` — tell the server we're sending JSON
- `-d '{...}'` — the JSON body with 7 customer features

This customer is high-risk: 2 months tenure, high bill, month-to-month contract, no support, e-check payment.

Expected output:

```json
{"churn": true, "churn_probability": 0.9976}
```

99.76% churn probability — this customer is almost certainly leaving.

---

### 15. Predict — low-risk customer

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

What it does: Same endpoint, but with a loyal customer profile — 5 years tenure, low bill, two-year contract, has support and security, pays by credit card.

Expected output:

```json
{"churn": false, "churn_probability": 0.0031}
```

0.3% churn probability — this customer is happy and staying.

---

### 16. Predict — bad input (validation test)

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

What it does: Sends invalid data — `contract_type: 9` is outside the allowed range (0-2). Pydantic validation catches this BEFORE the model sees it.

Expected output: HTTP 422 Unprocessable Entity with a validation error message. The model never ran — bad input was blocked at the door.

---

### 17. Stop the server

```
Ctrl+C
```

What it does: Sends SIGINT to the uvicorn process, shutting it down gracefully.

---

## Testing

### 18. Run all tests

```bash
pytest -q
```

What it does:
- `pytest` — Python test runner, discovers and runs all `test_*.py` files
- `-q` — quiet mode, minimal output

Runs 4 tests from `test_app.py`:
1. `test_health_ok` — GET /health returns 200 + "ok"
2. `test_predict_response_shape` — POST /predict returns churn + churn_probability, probability is between 0 and 1
3. `test_validation_rejects_bad_input` — contract_type=9 gets 422
4. `test_model_behaves_sensibly` — high-risk customer's probability > low-risk customer's probability

Expected output:

```
....                                                                     [100%]
4 passed in 1.20s
```

---

### 19. Run tests with verbose output (optional)

```bash
pytest -v
```

What it does: Same tests, but shows each test name and its pass/fail status individually. Useful for debugging when a test fails.

Expected output:

```
test_app.py::test_health_ok PASSED
test_app.py::test_predict_response_shape PASSED
test_app.py::test_validation_rejects_bad_input PASSED
test_app.py::test_model_behaves_sensibly PASSED
```

---

## Docker

### 20. Build the Docker image

```bash
docker build -t churn-api:latest .
```

What it does:
- `docker build` — build an image from a Dockerfile
- `-t churn-api:latest` — tag the image with name `churn-api` and tag `latest`
- `.` — use the current directory as the build context (where Dockerfile is)

Steps Docker executes:
1. Pulls `python:3.12-slim` base image (first time only)
2. Copies `requirements.txt` and installs dependencies
3. Copies `train.py` and `app.py`
4. Runs `python train.py` INSIDE the image — model is baked in
5. Image is ready

Takes ~1-2 minutes first time, faster on subsequent builds due to layer caching.

---

### 21. Verify the image was created

```bash
docker images | grep churn-api
```

What it does: Lists all Docker images and filters for `churn-api`. Shows the image name, tag, image ID, creation time, and size.

Expected: one row showing `churn-api` with tag `latest`, size ~500-600MB.

---

### 22. Run the container

```bash
docker run -p 8000:8000 churn-api:latest
```

What it does:
- `docker run` — start a container from an image
- `-p 8000:8000` — map port 8000 on your machine (left) to port 8000 in the container (right)
- `churn-api:latest` — the image to run

The container starts uvicorn with `--host 0.0.0.0` (listens on all interfaces) and `--workers 2` (two worker processes).

---

### 23. Test the container (in a new terminal)

```bash
curl http://localhost:8000/health
```

What it does: Same health check, but now hitting the containerized app instead of the local Python process. Should return the same response.

Expected:

```json
{"status": "ok", "trained_accuracy": 0.879}
```

---

### 24. Test prediction from the container

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

What it does: Same prediction request as command #14, but served from inside the Docker container. Same result proves the container is working identically to the local setup.

Expected:

```json
{"churn": true, "churn_probability": 0.9976}
```

---

### 25. Stop the container

```
Ctrl+C
```

What it does: Stops the running container.

---

### 26. Run the container in background (alternative)

```bash
docker run -d --name churn-api -p 8000:8000 churn-api:latest
```

What it does:
- `-d` — detached mode, runs in the background (doesn't block your terminal)
- `--name churn-api` — gives the container a name for easy reference

---

### 27. View container logs (if running in background)

```bash
docker logs churn-api
```

What it does: Shows the stdout/stderr output from the container — uvicorn startup messages and access logs.

---

### 28. Stop and remove the background container

```bash
docker stop churn-api
docker rm churn-api
```

What it does:
- `docker stop` — gracefully stops the running container
- `docker rm` — removes the stopped container (frees the name for reuse)

---

### 29. Log in to Docker Hub

```bash
docker login
```

What it does: Prompts for your Docker Hub username and password (or access token). Stores credentials locally so you can push images.

---

### 30. Tag the image for Docker Hub

```bash
docker tag churn-api:latest <your-dockerhub-username>/churn-api:latest
```

What it does: Creates a new tag pointing to the same image. Docker Hub requires the format `username/image-name:tag`. The image isn't copied — the tag is just an alias.

---

### 31. Push to Docker Hub

```bash
docker push <your-dockerhub-username>/churn-api:latest
```

What it does: Uploads the image layers to Docker Hub. Only uploads layers that don't already exist in the registry. After this, anyone can `docker pull` your image.

---

### 32. Verify the push (optional)

```bash
docker pull <your-dockerhub-username>/churn-api:latest
```

What it does: Pulls the image back from Docker Hub. If this succeeds, the push worked. You can also verify at https://hub.docker.com.

---

## Git

### 33. Initialize the repository

```bash
git init
```

What it does: Creates a new Git repository in the current directory. Adds a `.git/` folder to track changes.

---

### 34. Check what will be committed

```bash
git status
```

What it does: Shows which files are tracked, modified, or untracked. Verify that `model.joblib` is NOT listed — it's in `.gitignore`.

---

### 35. Verify .gitignore is working

```bash
cat .gitignore
```

What it does: Shows the contents of `.gitignore`. Should include `model.joblib`, `venv/`, `__pycache__/`, etc. These files will never be committed to Git.

---

### 36. Stage all files

```bash
git add .
```

What it does: Stages all untracked and modified files (except those in `.gitignore`) for the next commit.

---

### 37. Review what's staged

```bash
git status
```

What it does: Confirms which files are staged. You should see `train.py`, `app.py`, `test_app.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `.gitignore`, Jenkinsfile, Terraform files, and Kubernetes manifests. You should NOT see `model.joblib` or `venv/`.

---

### 38. Commit

```bash
git commit -m "Day 1: churn prediction API with Docker"
```

What it does: Creates a snapshot of all staged files with a descriptive message. This is your first commit — the starting point of the project's history.

---

### 39. View the commit

```bash
git log --oneline
```

What it does: Shows the commit history in compact format — one line per commit with the hash and message.

Expected:

```
a1b2c3d Day 1: churn prediction API with Docker
```

---

## Cleanup (Optional)

### 40. Deactivate the virtual environment

```bash
deactivate
```

What it does: Switches your shell back to the system Python. The `(venv)` prefix disappears from your prompt. The venv still exists on disk — you just aren't using it.

---

### 41. Remove dangling Docker images (optional)

```bash
docker system prune -f
```

What it does: Removes unused Docker data — stopped containers, dangling images, unused networks. Frees disk space. The `-f` flag skips the confirmation prompt.

---

## Summary

| # | Command | Purpose |
|---|---|---|
| 1-3 | `python3 --version`, `docker --version`, `git --version` | Verify prerequisites |
| 4-6 | `python3 -m venv venv`, `source venv/bin/activate`, `pip install` | Set up Python environment |
| 7 | `python -c "import sklearn; ..."` | Verify installation |
| 8-9 | `python train.py`, `ls -lh model.joblib` | Train model and verify |
| 10 | `python train.py` (with threshold=0.99) | Demo the quality gate |
| 11-12 | `uvicorn app:app ...`, `open .../docs` | Start server, open Swagger |
| 13-16 | `curl /health`, `curl /predict` (x3) | Test health, high-risk, low-risk, bad input |
| 17 | Ctrl+C | Stop server |
| 18-19 | `pytest -q`, `pytest -v` | Run automated tests |
| 20-21 | `docker build`, `docker images` | Build Docker image |
| 22-25 | `docker run`, `curl`, Ctrl+C | Run and test container |
| 26-28 | `docker run -d`, `docker logs`, `docker stop/rm` | Background container management |
| 29-32 | `docker login`, `docker tag`, `docker push`, `docker pull` | Push to Docker Hub |
| 33-39 | `git init`, `git add`, `git commit`, `git log` | Version control |
| 40-41 | `deactivate`, `docker system prune` | Cleanup |
