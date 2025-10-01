"""FastAPI server exposing OCR extraction and risk scoring endpoints."""
from __future__ import annotations

import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from merchant_risk_scoring.models import MerchantApplication, RiskAssessmentResult
from merchant_risk_scoring.ocr.ollama_qwen import OllamaQwenExtractor
from merchant_risk_scoring.scoring.engine import RiskScoringEngine

app = FastAPI(title="Merchant Underwriting & Risk Scoring API")


class OCRRequest(BaseModel):
    image_base64: str
    fields: list[str]
    prompt_override: str | None = None
    extra_instructions: str | None = None
    model: str | None = None


class OCRResponse(BaseModel):
    extracted: dict[str, str | None]


class ScoreResponse(BaseModel):
    result: RiskAssessmentResult


@app.post("/ocr/extract", response_model=OCRResponse)
def extract_via_ollama(payload: OCRRequest) -> OCRResponse:
    try:
        extractor = OllamaQwenExtractor(model=payload.model or "qwen2.5-vl")
        image_bytes = payload.image_base64.encode("utf-8")
        decoded = base64.b64decode(image_bytes)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        extracted = extractor.extract_fields(
            decoded,
            fields=payload.fields,
            custom_prompt=payload.prompt_override,
            extra_instructions=payload.extra_instructions,
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return OCRResponse(extracted=extracted)


_engine = RiskScoringEngine()


@app.post("/score", response_model=ScoreResponse)
def score_merchant(application: MerchantApplication) -> ScoreResponse:
    try:
        result = _engine.score(application)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScoreResponse(result=result)
