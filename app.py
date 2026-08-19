from __future__ import annotations

import json
import logging
import pickle
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict

ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "concrete_xgb_model.pkl"
FEATURE_PATH = ROOT / "feature_names.pkl"
DATA_PATH = ROOT / "concrete_data.csv"
HISTORY_PATH = ROOT / "prediction_history.json"
STATIC_PATH = ROOT / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("concrete-strength")

RAW_FEATURES = [
    "cement", "blast_furnace_slag", "fly_ash", "water", "superplasticizer",
    "coarse_aggregate", "fine_aggregate", "age"
]
DISPLAY_NAMES = {
    "cement": "Cement", "blast_furnace_slag": "Blast furnace slag", "fly_ash": "Fly ash",
    "water": "Water", "superplasticizer": "Superplasticizer", "coarse_aggregate": "Coarse aggregate",
    "fine_aggregate": "Fine aggregate", "age": "Curing age"
}


def load_pickle(path: Path):
    with path.open("rb") as handle:
        return pickle.load(handle)


try:
    MODEL = load_pickle(MODEL_PATH)
    SAVED_FEATURES = [str(name) for name in load_pickle(FEATURE_PATH)]
except Exception as exc:
    logger.exception("Unable to load model artifacts")
    raise RuntimeError(f"Model artifacts could not be loaded: {exc}") from exc

DATA = pd.read_csv(DATA_PATH, encoding="latin1")
DATA.columns = [str(name).strip() for name in DATA.columns]
TARGET = "concrete_compressive_strength"


def engineer_features(values: dict[str, float]) -> pd.DataFrame:
    row = {key: float(values[key]) for key in RAW_FEATURES}
    binder = row["cement"] + row["blast_furnace_slag"] + row["fly_ash"]
    row.update({
        "binder": binder,
        "wc_ratio": row["water"] / binder if binder else 0.0,
        "log_age": float(np.log1p(row["age"])),
        "has_slag": float(row["blast_furnace_slag"] > 0),
        "has_flyash": float(row["fly_ash"] > 0),
        "has_super": float(row["superplasticizer"] > 0),
    })
    ordered = list(SAVED_FEATURES) if len(SAVED_FEATURES) == len(row) else list(row)
    return pd.DataFrame([[row[str(name).strip()] for name in ordered]], columns=ordered)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cement: Annotated[float, Field(ge=0, le=1000)]
    blast_furnace_slag: Annotated[float, Field(ge=0, le=500)]
    fly_ash: Annotated[float, Field(ge=0, le=500)]
    water: Annotated[float, Field(gt=0, le=400)]
    superplasticizer: Annotated[float, Field(ge=0, le=100)]
    coarse_aggregate: Annotated[float, Field(ge=0, le=1500)]
    fine_aggregate: Annotated[float, Field(ge=0, le=1500)]
    age: Annotated[float, Field(gt=0, le=1000)]


class PredictionResponse(BaseModel):
    id: str
    strength_mpa: float
    band: str
    interpretation: str
    created_at: str
    inputs: dict[str, float]


app = FastAPI(title="Concrete Strength Intelligence API", version="1.0.0", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def classify(value: float) -> tuple[str, str]:
    if value < 20:
        return "Low", "The estimated strength is below a typical structural benchmark. Review the mix design and curing plan before use."
    if value < 40:
        return "Moderate", "The estimate sits in a moderate range. Validate the mix with laboratory testing for the intended application."
    if value < 60:
        return "High", "The estimate indicates a high-strength mix for many general applications, subject to project specifications."
    return "Very high", "The estimate indicates a very high-strength mix. Confirm with project-specific testing and standards."


def read_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text())
    except Exception:
        return []


def append_history(item: dict) -> None:
    history = [item] + read_history()
    HISTORY_PATH.write_text(json.dumps(history[:25], indent=2))


@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": MODEL is not None, "dataset_rows": len(DATA)}


@app.get("/api/metadata")
def metadata():
    return {
        "model": "XGBoost regressor",
        "version": "concrete_xgb_model.pkl",
        "features": [{"key": key, "label": DISPLAY_NAMES[key], "unit": "kg/m³" if key != "age" else "days"} for key in RAW_FEATURES],
        "dataset_rows": int(len(DATA)),
        "target": "Compressive strength (MPa)",
        "dataset_summary": {
            "mean_strength": round(float(DATA[TARGET].mean()), 2),
            "min_strength": round(float(DATA[TARGET].min()), 2),
            "max_strength": round(float(DATA[TARGET].max()), 2),
            "median_age": round(float(DATA["age"].median()), 1),
        },
    }


@app.get("/api/history")
def history():
    return {"items": read_history()}


@app.post("/api/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    values = request.model_dump()
    try:
        features = engineer_features(values)
        raw = float(MODEL.predict(features)[0])
        strength = round(max(0.0, raw), 2)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=503, detail="The prediction service is temporarily unavailable.") from exc
    band, interpretation = classify(strength)
    item = {
        "id": str(uuid.uuid4()), "strength_mpa": strength, "band": band,
        "interpretation": interpretation, "created_at": datetime.now(timezone.utc).isoformat(), "inputs": values,
    }
    append_history(item)
    return item


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_PATH / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")
