# Merchant Risk Scoring & Underwriting Toolkit

This project provides a modular merchant underwriting engine designed for PSPs and PayFacs that must underwrite new merchants with limited or no historical transaction data. The toolkit emphasises:

- **Rule-based triage** to immediately catch sanctions hits, high-risk industries, and unrealistic volume claims.
- **Weighted component scoring** that combines KYC integrity, promoter reputation, industry risk, financial stability, and digital footprint signals into a composite risk score.
- **Vision-Language OCR integration** using [Ollama](https://ollama.com/) with the `qwen2.5` multimodal model to extract structured fields from KYC documents and onboarding artefacts.
- **FastAPI services** that expose both OCR extraction and risk scoring endpoints for easy integration with onboarding workflows.

## Project Layout

```
merchant_risk_scoring/
├── models.py                 # Pydantic domain models used throughout the engine
├── ocr/
│   └── ollama_qwen.py        # Client wrapper for Ollama's qwen2.5 VLM OCR extraction
└── scoring/
    ├── components.py         # Heuristic scoring logic per risk component
    ├── engine.py             # Composite scoring orchestrator + recommendations
    ├── rules.py              # Deterministic policy rules (sanctions, high risk flags)
    └── weights.py            # Configurable component weightings
app/
└── main.py                   # FastAPI app exposing `/ocr/extract` and `/score`
```

Unit tests for the scoring heuristics live in `tests/test_engine.py`.

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the API server**

   Ensure [Ollama](https://ollama.com/) is running locally with the `qwen2.5-vl` model pulled. Then start the FastAPI application:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   - `POST /ocr/extract` accepts a base64 encoded image and list of fields to extract. The request is proxied to Ollama running at `http://localhost:11431` by default.
   - `POST /score` ingests a `MerchantApplication` payload (see `merchant_risk_scoring/models.py`) and returns a `RiskAssessmentResult` with rule findings, component breakdown, and recommended next steps.

3. **Run tests**

   ```bash
   pytest
   ```

## Example Usage

### OCR Extraction

```bash
curl -X POST http://localhost:8000/ocr/extract \
  -H "Content-Type: application/json" \
  -d '{
        "image_base64": "<base64-string>",
        "fields": ["business_name", "gst_number", "address"],
        "extra_instructions": "Prefer Indian government GST formatting."
      }'
```

### Risk Scoring

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
        "merchant_id": "demo-123",
        "business_name": "Acme Retail",
        "registration_country": "IN",
        "industry_category": "Retail",
        "business_model": "Card-present retail",
        "documents": [
          {"document_type": "GST", "provided": true, "verified": true},
          {"document_type": "PAN", "provided": true, "verified": true}
        ],
        "promoters": [
          {
            "full_name": "Priya Singh",
            "credit_score": 760,
            "years_of_experience": 8
          }
        ],
        "digital_footprint": {
          "website_quality": "high",
          "domain_age_months": 36,
          "social_presence": "moderate",
          "review_volume": 120,
          "average_review_rating": 4.4,
          "contact_email_domain_matches": true,
          "ip_geolocation_match": true
        },
        "financial_profile": {
          "years_in_business": 5,
          "average_monthly_balance": 250000.0,
          "projected_monthly_volume": 500000.0,
          "average_ticket_size": 2500.0,
          "bank_account_age_months": 48,
          "financial_documents_provided": true
        }
      }'
```

The response contains:

- `composite_score`: weighted 0-100 score.
- `risk_level`: `low`, `medium`, or `high`.
- `decision`: immediate recommendation (`approve`, `manual_review`, or `reject`).
- `component_scores`: breakdown per risk dimension with narrative reasons.
- `rule_findings`: deterministic policy triggers (e.g. high-risk industry flags).
- `recommendations`: operational actions (e.g. collect more docs, hold reserves).

## Extending the Engine

- **Add new data sources** by extending `merchant_risk_scoring/models.py` and augmenting `components.py` with additional scoring factors (e.g. geo-risk, device intelligence). Update `RiskWeights` accordingly.
- **Integrate machine learning** by feeding historical labeled outcomes into a model whose output can populate the `other` weight bucket or override component scores.
- **Customise OCR prompts** by supplying `prompt_override` or `extra_instructions` fields in the `/ocr/extract` request body to steer Qwen2.5 towards bespoke document layouts.

## Notes

- The project assumes Ollama is reachable at `http://localhost:11431`. Override the base URL or model by instantiating `OllamaQwenExtractor` with custom parameters.
- Default scoring thresholds are intentionally conservative for early-stage PSPs. Tune weights and thresholds inside `weights.py` and `engine.py` as your portfolio matures.
