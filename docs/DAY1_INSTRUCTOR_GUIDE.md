# Day 1 — Instructor Guide: Git + Docker

**Duration:** ~3 hours (with breaks)
**Goal:** Students go from zero to a running containerized ML API.
**End state:** Every student has a Docker image pushed to Docker Hub, and understands why each layer exists.

---

## Agenda

| Time | Section | What happens |
|---|---|---|
| 20 min | Part 1: What Are We Building? | Business context, feature walkthrough |
| 30 min | Part 2: Training Script | Walk through train.py, live demo, break the gate |
| 30 min | Part 3: The API | Walk through app.py, live demo, Swagger UI, 3 test requests |
| 20 min | Part 4: Testing | Walk through test_app.py, behavioral ML test concept |
| 10 min | Break | |
| 40 min | Part 5: Docker | The problem, Dockerfile walkthrough, build and run |
| 15 min | Part 6: Git | Init, .gitignore, why models don't go in Git |
| 10 min | Part 7: Wrap-Up | Recap, Day 2 preview |

---

## Part 1: What Are We Building? (20 min)

### Talking Points

Start with the business problem before touching any code. Students need to understand WHY this app exists.

> "You work at a telecom company. Every month, customers cancel their plans. This is called churn. Acquiring a new customer costs 5-10x more than keeping an existing one. If you could predict which customers are about to leave, you could intervene — call them, offer a discount, assign a support rep — before they cancel."

> "That's what this app does. It takes 7 pieces of information about a customer and tells you the probability they'll churn."

### What to Draw on the Whiteboard

The business flow:

```
Customer Data --> ML Model --> Churn Prediction --> Business Action
                                                      |
                                                Call the customer
                                                Offer a discount
                                                Assign a support rep
```

### Feature Table — Walk Through Each One

Explain each feature and WHY it matters for churn. This connects business intuition to data science.

| Feature | What it means | Why it predicts churn |
|---|---|---|
| `tenure_months` | How long they've been a customer | New customers leave more easily |
| `monthly_charges` | Monthly bill amount | Higher bill = more pain = more churn |
| `total_charges` | Lifetime spend | Low total = new and unhappy |
| `contract_type` | 0=month-to-month, 1=1yr, 2=2yr | No lock-in = easy to walk away |
| `has_tech_support` | 0=no, 1=yes | Support reduces frustration |
| `has_online_security` | 0=no, 1=yes | More services = more sticky |
| `is_electronic_check` | 0=no, 1=yes | This payment type correlates with churn in real telecom data |

### Questions to Ask the Class

- "If you had to guess — which of these features matters MOST for churn?" (Let them discuss. They'll validate their intuition against the model later.)
- "A customer has been with you for 1 month, pays $100/month, is on a month-to-month contract, has no support. Will they churn?" (Obviously yes — build intuition.)

### What to Draw on the Whiteboard

The 4-day journey:

```
Day 1: Python script --> API --> Docker container
Day 2: Manual steps --> Jenkins automates everything
Day 3: "Where does it run?" --> Terraform provisions AWS
Day 4: "How does it scale?" --> Kubernetes orchestrates it
```

> "The model never changes. We just keep wrapping it in more infrastructure. By Day 4, the same curl command that works on your laptop will work against a production cloud endpoint."

---

## Part 2: The Training Script — train.py (30 min)

### File to Open

`train.py` — display on screen for the class.

### Section A: Data Generation (lines 37-79)

#### What to Explain

- We use synthetic data — no downloads, no broken URLs, no privacy issues during the lab
- 5000 customers, 7 features each
- The churn score formula uses a logistic function

#### Key Lines to Highlight

The coefficient signs in the score formula (lines 51-60):

```python
score = (
    1.8
    - 0.060 * tenure          # negative = longer tenure = LESS churn
    + 0.022 * monthly          # positive = higher bill = MORE churn
    - 1.2 * contract           # negative = longer contract = LESS churn
    - 0.7 * tech               # negative = has support = LESS churn
    - 0.6 * security           # negative = has security = LESS churn
    + 0.8 * echeck             # positive = e-check = MORE churn
)
```

#### Questions to Ask

- "Look at the coefficient for tenure: -0.060. What does the negative sign mean?" (Longer tenure = lower score = less churn.)
- "Which feature has the biggest magnitude? -1.2 for contract_type. What does that tell you?" (Contract type is the strongest predictor.)
- "Do these signs match your intuition from Part 1?"

#### What to Explain About Noise

Label flipping (lines 66-68) — 8% of labels are randomly flipped.

- "Why add noise? Why not a perfectly clean dataset?"
- Answer: Real data is messy. A perfect dataset would give a perfect model with probabilities of exactly 0.0 or 1.0 — that looks fake and teaches nothing about real ML.

### Section B: The Pipeline (lines 89-93)

#### What to Explain

```python
model = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(max_iter=1000)),
])
```

- Pipeline bundles preprocessing + model into ONE object
- When you call `predict()`, it scales first, then predicts — automatically

#### Questions to Ask

- "Why not scale the data separately and then fit the model?"
- Answer: If you scale separately, you must remember to scale at prediction time too, using the SAME scaler (same mean and standard deviation). Pipeline handles this automatically. Forgetting this causes train/serve skew — one of the most common ML bugs in production.

### Section C: The Accuracy Gate (lines 95-104)

This is the MOST IMPORTANT concept of Day 1. Spend time here.

#### What to Explain

```python
ACCURACY_THRESHOLD = 0.78

if acc < ACCURACY_THRESHOLD:
    raise SystemExit(
        "FAIL: accuracy ... Refusing to save a sub-par model."
    )
```

> "In regular software, CI checks if the code compiles and tests pass. In ML, you ALSO need to check: is the model good enough? This threshold is that check. Tomorrow, Jenkins will enforce this automatically — a bad model never ships."

### Section D: Model Serialization (line 106)

#### What to Explain

```python
joblib.dump({"model": model, "features": FEATURES, "accuracy": acc}, MODEL_PATH)
```

- Saves a dictionary, not just the model — includes feature names and accuracy
- The serving code reads `_features` from this dictionary to build the DataFrame in the correct column order

#### Questions to Ask

- "Why save feature names alongside the model?" — If you add or reorder features and forget to update the API, you get silent wrong predictions. The saved feature list prevents this.
- "Why is model.joblib in .gitignore?" — It's a build artifact, like a .exe file. Code goes in Git, artifacts don't. In real MLOps, you'd use DVC or MLflow to version models separately.

### Live Demo

Have everyone run:

```bash
python train.py
```

Expected output on screen:

```
Churn rate in data : 52.4%
Test accuracy      : 0.879
Accuracy threshold : 0.78
PASS: saved model.joblib
```

### Exercise: Break the Gate (2 minutes)

Have students change `ACCURACY_THRESHOLD = 0.99` and rerun.

They should see:

```
FAIL: accuracy 0.879 < threshold 0.99. Refusing to save a sub-par model.
```

Then revert to `0.78`. This plants the seed for Day 2's Jenkins gate.

---

## Part 3: The API — app.py (30 min)

### File to Open

`app.py` — display on screen.

### How to Introduce This Section

> "You have a model file. But nobody can use a .joblib file. You need to wrap it in something people and other systems can call over the network. That's what an API does."

### Section A: Model Loading (lines 17-25)

#### What to Explain

```python
MODEL_PATH = os.getenv("MODEL_PATH", "model.joblib")

_bundle = joblib.load(MODEL_PATH)
_model = _bundle["model"]
_features = _bundle["features"]
_trained_accuracy = _bundle["accuracy"]
```

- Model loads ONCE when the app starts, stored in module-level variables
- Not per-request — that would be slow and wasteful

#### Questions to Ask

- "What if we loaded the model inside the /predict function instead?" — You'd read the file from disk on every single request. For a small model it's just slow; for a 2GB deep learning model it would be unusable.
- "Where does MODEL_PATH come from?" — An environment variable with a default. On Day 4, the Kubernetes ConfigMap will set this. For now, the default works.

### Section B: Input Validation (lines 28-36)

#### What to Explain

```python
class Customer(BaseModel):
    tenure_months: int = Field(..., ge=0, examples=[5])
    monthly_charges: float = Field(..., ge=0, examples=[89.5])
    contract_type: int = Field(..., ge=0, le=2, ...)
    has_tech_support: int = Field(..., ge=0, le=1, ...)
```

- FastAPI + Pydantic validates input BEFORE it reaches the model
- `ge=0` means "greater than or equal to 0", `le=2` means "less than or equal to 2"

#### Questions to Ask

- "Why is input validation critical for ML APIs specifically?"
- Answer: A traditional API crashes on bad input. An ML model SILENTLY returns a confident wrong answer on bad input. If someone sends contract_type=99, the model won't error — it'll give a meaningless probability. Validation is your first line of defense.

### Section C: Health Endpoint (lines 39-42)

#### What to Explain

```python
@app.get("/health")
def health():
    return {"status": "ok", "trained_accuracy": round(_trained_accuracy, 3)}
```

- Seems trivial now
- On Day 4, Kubernetes hits this endpoint every few seconds to check if the pod is alive. If it fails, Kubernetes restarts the pod automatically.
- Also exposes trained_accuracy — useful for monitoring which model version is deployed.

### Section D: Prediction Endpoint (lines 45-52)

#### What to Explain — Line by Line

```python
@app.post("/predict")
def predict(customer: Customer):
    row = pd.DataFrame([{f: getattr(customer, f) for f in _features}])
    proba = float(_model.predict_proba(row)[0][1])
    return {
        "churn": bool(proba >= 0.5),
        "churn_probability": round(proba, 4),
    }
```

1. Builds a single-row DataFrame using `_features` — exact same column order as training
2. `predict_proba(row)` returns `[[P(no churn), P(churn)]]`
3. `[0][1]` — row 0, class 1 (churn probability)
4. Returns both boolean decision (threshold at 0.5) AND raw probability

#### Questions to Ask

- "Why return the probability and not just true/false?"
- Answer: Different business actions need different thresholds. A 60% churn customer might get an email; a 95% churn customer gets a phone call. The raw probability gives the caller flexibility.

### Live Demo

Start the server:

```bash
uvicorn app:app --reload --port 8000
```

Open http://localhost:8000/docs in the browser — show the interactive Swagger UI.

### Three Requests for Students to Try

Walk through all three. Have students try them in the Swagger UI or with curl.

**Request 1 — High-risk customer:**

```json
{
  "tenure_months": 2, "monthly_charges": 95.0, "total_charges": 190.0,
  "contract_type": 0, "has_tech_support": 0, "has_online_security": 0,
  "is_electronic_check": 1
}
```

Expected: ~99.7% churn probability.

Say: "This customer is about to leave. Call them."

**Request 2 — Low-risk customer:**

```json
{
  "tenure_months": 60, "monthly_charges": 40.0, "total_charges": 2400.0,
  "contract_type": 2, "has_tech_support": 1, "has_online_security": 1,
  "is_electronic_check": 0
}
```

Expected: Very low churn probability.

Say: "This customer is happy. Leave them alone."

**Request 3 — Bad input:**

```json
{
  "tenure_months": 2, "monthly_charges": 95.0, "total_charges": 190.0,
  "contract_type": 9, "has_tech_support": 0, "has_online_security": 0,
  "is_electronic_check": 1
}
```

Expected: 422 Validation Error.

Say: "The API caught the bad input before the model ever saw it."

### Question to Ask After All Three

"Does the model's behavior match the intuition you had in Part 1 about which features matter?"

---

## Part 4: Testing — test_app.py (20 min)

### File to Open

`test_app.py` — display on screen.

### How to Introduce This Section

> "The model works. But how do you make sure it KEEPS working after every code change?"

### Section A: Standard API Tests (lines 28-44)

#### What to Explain

Three normal software tests:

- `test_health_ok` — GET /health returns 200 with status "ok"
- `test_predict_response_shape` — POST /predict returns the right keys (churn, churn_probability) and probability is between 0 and 1
- `test_validation_rejects_bad_input` — contract_type=9 returns 422

Say: "These are standard API tests. Nothing ML-specific. They verify the plumbing works."

### Section B: The Behavioral ML Test (lines 47-50)

This is the KEY concept. Spend time here.

#### What to Explain

```python
def test_model_behaves_sensibly():
    high = client.post("/predict", json=HIGH_RISK).json()["churn_probability"]
    low = client.post("/predict", json=LOW_RISK).json()["churn_probability"]
    assert high > low, "high-risk customer should out-score low-risk one"
```

#### Questions to Ask

- "Can you hardcode the expected output of a model prediction in a test?"
- Answer: No. When you retrain, the exact probabilities change. You can't write `assert probability == 0.9976`. But you CAN assert relative behavior — a clearly risky customer should ALWAYS score higher than a safe one, regardless of exact numbers.

> "This is what makes ML testing different from regular testing. You test BEHAVIOR and INVARIANTS, not exact values."

#### Mention (But Don't Implement) Other Behavioral Test Ideas

- Increasing tenure should never increase churn probability
- Two identical inputs should always produce identical outputs
- Switching from month-to-month to two-year contract should decrease churn

### Live Demo

```bash
pytest -q
```

Expected on screen:

```
....                                                                     [100%]
4 passed in 1.20s
```

---

## Break (10 min)

---

## Part 5: Docker (40 min)

### How to Introduce This Section

#### The Problem (5 min)

Ask: "Everyone just ran this app. Raise your hand if you hit any issues — wrong Python version, missing package, OS difference."

Even if nobody did, pose the scenario:

> "Your teammate has Python 3.9, you have 3.12. They have numpy 1.24, you have 1.26. The model trains fine on your machine, gives different results on theirs. How do you guarantee identical behavior everywhere — your laptop, CI server, staging, production?"

Answer: Containers.

### What to Draw on the Whiteboard

```
Without Docker:
+----------------+  +----------------+  +----------------+
|  Your Laptop   |  |  CI Server     |  |  Production    |
|  Python 3.12   |  |  Python 3.9    |  |  Python 3.11   |
|  numpy 1.26    |  |  numpy 1.24    |  |  numpy 1.25    |
|  macOS         |  |  Ubuntu        |  |  Amazon Linux  |
+----------------+  +----------------+  +----------------+
     "works"           "breaks"           "who knows"

With Docker:
+--------------------------------------------------+
|              Same Container Image                 |
|              Python 3.12-slim                     |
|              numpy 1.26.4                         |
|              Identical everywhere                 |
+--------------------------------------------------+
```

### Dockerfile Walkthrough (15 min)

#### File to Open

`Dockerfile` — display on screen. Go line by line.

#### Line 1: Base Image

```dockerfile
FROM python:3.12-slim
```

Say: "Starting point — a minimal Linux with Python 3.12. Same on every machine in the world."

#### Line 2: Working Directory

```dockerfile
WORKDIR /app
```

Say: "All commands run inside /app in the container."

#### Lines 3-4: Dependencies

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

Question to ask: "Why copy requirements.txt FIRST, before the rest of the code?"

Answer: Layer caching. Docker caches each step. If you change app.py but not requirements.txt, this layer is cached — deps don't reinstall. Saves minutes on every build.

#### Lines 5-6: Source and Training

```dockerfile
COPY train.py app.py ./
RUN python train.py
```

Question to ask: "The model is trained INSIDE the image at build time. What are the pros and cons?"

- Pro: Image is fully self-contained. No network, no data needed at runtime. Perfectly reproducible.
- Con: Can't swap models without rebuilding. Training is part of the build — slow for large models.

Say: "In a real system, you'd train in CI separately and COPY the model artifact in. We bake it here to keep things simple — one moving part."

#### Line 7: Port

```dockerfile
EXPOSE 8000
```

Say: "Documentation only — tells readers which port the app uses. Doesn't actually open anything."

#### Line 8: Start Command

```dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Question to ask: "Why 0.0.0.0 instead of localhost?"

Answer: localhost inside a container means only accessible from inside the container. 0.0.0.0 means listen on all network interfaces — that's how traffic from outside the container reaches the app.

### .dockerignore (2 min)

#### What to Explain

Show the file — it excludes venv/, __pycache__/, model.joblib, .git/, etc.

Say: "Same idea as .gitignore. Without this, Docker copies your entire 200MB venv into the build context. The container installs its own deps — it doesn't need yours."

### Build and Run Demo (10 min)

Build:

```bash
docker build -t churn-api:latest .
```

Walk through the output as it builds — point out each layer.

Run:

```bash
docker run -p 8000:8000 churn-api:latest
```

Explain: "-p 8000:8000 maps port 8000 on your machine to port 8000 in the container."

Test (in another terminal):

```bash
curl -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{
  "tenure_months": 2, "monthly_charges": 95.0, "total_charges": 190.0,
  "contract_type": 0, "has_tech_support": 0, "has_online_security": 0,
  "is_electronic_check": 1
}'
```

Say: "Same result as before. Same app, now running in a container."

### Push to Docker Hub (3 min)

```bash
docker tag churn-api:latest <dockerhub-user>/churn-api:latest
docker push <dockerhub-user>/churn-api:latest
```

Say: "Now anyone in the world can docker pull your image and run the exact same API. This is what Jenkins will do on Day 2."

---

## Part 6: Git (15 min)

### What to Cover

If students are new to Git, cover the essentials:

```bash
git init
git add .
git commit -m "Initial commit: churn prediction API"
```

### Key Points to Make

1. `model.joblib` is in `.gitignore` — artifacts don't go in Git
2. Code is versioned, models are built from code

### Question to Ask

"If you delete model.joblib and run python train.py again with the same code, do you get the same model?"

Answer: Yes — `RANDOM_STATE = 42` makes it deterministic. The code is the source of truth, not the artifact. That's why the code goes in Git and the model doesn't.

---

## Part 7: Wrap-Up and Preview (10 min)

### What to Draw on the Whiteboard

The pipeline so far:

```
train.py --> model.joblib --> app.py --> Docker image --> Docker Hub
 (code)      (artifact)       (API)     (portable unit)   (registry)
```

### What Students Did Manually Today

Count them off:

1. Installed dependencies
2. Trained the model
3. Ran tests
4. Built a Docker image
5. Pushed the image

### Preview Day 2

> "You did 5 manual steps. What if you forget step 3? What if someone pushes code that breaks the model? Tomorrow, Jenkins does ALL of this on every single git push — and refuses to ship a bad model."

---

## Common Issues During Day 1 Labs

| Problem | Solution |
|---|---|
| `python3: command not found` | Install Python 3.9+ or use `python` instead of `python3` |
| `pip install` fails with permission error | Make sure venv is activated: `source venv/bin/activate` |
| `model.joblib not found` when starting app | Run `python train.py` first |
| `uvicorn: command not found` | Activate venv: `source venv/bin/activate` |
| Port 8000 already in use | Kill the old process: `lsof -ti:8000 \| xargs kill` or use a different port |
| Docker build fails | Make sure Docker Desktop is running |
| `docker push` access denied | Run `docker login` first |
| Swagger UI shows no endpoints | Check the terminal for import errors — model might not exist |

---

## Instructor Notes

### Timing Tips

- Part 2 (train.py) and Part 5 (Docker) tend to run long. If short on time, trim the Git section — students can do it as homework.
- The "break the accuracy gate" exercise is quick but high impact. Don't skip it.
- Let students explore the Swagger UI freely for a few minutes. They enjoy clicking around.

### What to Watch For

- Students who skip the venv and install globally — this causes conflicts later. Check early.
- Students who don't revert the accuracy threshold after breaking it — they'll be stuck at Step 5.
- Docker Desktop not running — the build will fail with a confusing "daemon not running" error.

### What Makes This Click

The moment students send the same curl command to Docker and get the same result — that's when "works on my machine" stops being abstract. Make sure everyone reaches that point.
