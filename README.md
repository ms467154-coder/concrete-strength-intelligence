# Concrete Strength Intelligence

**Concrete Strength Intelligence** is a production-style application wrapped around the project’s existing XGBoost regression model. It estimates concrete compressive strength in MPa from eight mix variables and curing age, while keeping the serialized model and original notebook workflow intact.

The product experience is branded for **Mohamed Salem** and uses a restrained cream, neutral, and muted-red visual system designed for an AI engineering portfolio or internal decision-support tool.

## What was built

The project now includes a FastAPI application layer, typed request validation, model artifact loading, feature engineering compatible with the existing trained model, user-friendly error handling, health and metadata endpoints, local prediction history, and a responsive frontend with prediction, result, model overview, and recent-run views.

| Layer | Implementation |
|---|---|
| UI | Responsive semantic HTML/CSS/JavaScript application in `static/` |
| API | FastAPI application in `app.py` |
| ML inference | Existing `concrete_xgb_model.pkl` and `feature_names.pkl` |
| Data | Existing `concrete_data.csv` used for metadata and summary metrics |
| Persistence | Local JSON history at runtime; replace with a database for multi-user deployment |
| Documentation | Interactive OpenAPI documentation at `/api/docs` |

## Run locally

Install the dependencies in a Python 3.11+ environment:

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API documentation is available at [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs).

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service and model health status |
| GET | `/api/metadata` | Model, feature, dataset, and summary information |
| GET | `/api/history` | Recent prediction records |
| POST | `/api/predict` | Validate inputs and return an ML prediction |
| GET | `/api/docs` | OpenAPI / Swagger documentation |

The prediction endpoint accepts `cement`, `blast_furnace_slag`, `fly_ash`, `water`, `superplasticizer`, `coarse_aggregate`, `fine_aggregate`, and `age`. Quantities are in kg/m³ and age is in days.

## ML integration notes

The application does not retrain or replace the existing model. It reproduces the feature engineering required by the serialized estimator: binder total, water-to-binder ratio, log-transformed age, and indicator variables for slag, fly ash, and superplasticizer presence. The adapter also preserves the serialized feature labels, including the original trailing-space artifact in the stored feature list, so inference remains compatible with the existing artifact.

The application presents predictions as decision support. It does not replace laboratory validation, project specifications, or applicable engineering standards.

## Verification

Run the included smoke test after installing dependencies:

```bash
python smoke_test.py
```

The test covers service health, metadata, real model inference, response classification, and frontend serving. The verified sample run returned a positive prediction and a valid strength band.

## Production follow-up

For a multi-user deployment, replace the local JSON history file with a database, add authentication and authorization, configure an explicit allowlist for CORS, add structured log shipping, pin dependencies with hashes, and add CI checks for API and browser flows. The model registry, experiment tracking, monitoring, and CI/CD should remain connected to the existing MLOps system if those services are introduced around this project.
