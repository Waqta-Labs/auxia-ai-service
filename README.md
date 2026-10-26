# auxia-ai-service

AuxIA AI Service: Python/FastAPI microservice for NLP processing of field reports, zone urgency scoring, and aid distribution optimization.

It is stateless: `auxia-backend` sends all the data in each request through its
Anti-Corruption Layers (`RestFieldReportStructuringGateway`,
`RestUrgencyScoringGateway`, `RestDistributionOptimizationGateway` and
`RestStaffAssignmentGateway`) and keeps the results in its own database.

## Stack

| Item | Version |
|---|---|
| Python | 3.12 |
| FastAPI | 0.162.0 |
| Pydantic | 2.14.1 |
| Uvicorn | 0.54.0 |
| Tests and lint | pytest 9.1.1, ruff 0.17.2 |

Dependencies are pinned in `requirements.txt` (runtime) and
`requirements-dev.txt` (tests and lint).

## Structure

```text
app/
├── main.py        # creates the app, registers routers and error handlers
├── core/          # configuration, API key validation, error handling
├── api/           # one router per capability (health; api/v1 from phase 1)
├── schemas/       # Pydantic request and response models (the contract)
└── services/      # the models: nlp, urgency, optimization, staffing (from phase 1)
tests/
```

## Configuration

| Variable | Description |
|---|---|
| `AI_SERVICE_API_KEY` | Shared secret that `auxia-backend` sends in the `X-API-Key` header. At least 16 characters. Required: the service does not start without it. |

For local development, copy `.env.example` to `.env` and set the key. `.env`
is ignored by git and must never be committed.

## Running

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/openapi.json | OpenAPI document |
| http://localhost:8000/health | Health check (no API key needed) |

## Testing

```bash
ruff check .
pytest
```

## Backend contract

Contract agreed with `auxia-backend`. Any change is made here and in the
backend gateway at the same time.

### Conventions

- **Authentication.** Every `/api/v1/*` endpoint requires the `X-API-Key`
  header. `/health` is open.
- **JSON.** Requests and responses use camelCase.
- **Model version.** Every response includes `modelVersion`. The current
  models are explicit rules: `"rules-v1"`. Replacing a rule with a trained
  model changes `modelVersion`, not the contract.
- **Errors.** Every error, including validation errors, has the same format.
  Validation errors answer `400`, not FastAPI's default `422`. `details` lists
  each problem with the path of the field in camelCase, and is empty when
  there is nothing more to say.

  ```json
  {
    "code": "VALIDATION_ERROR",
    "message": "The request is not valid.",
    "details": [
      { "field": "zones[0].score", "message": "Input should be less than or equal to 100" }
    ]
  }
  ```

  | Status | `code` | When |
  |---|---|---|
  | 400 | `VALIDATION_ERROR` | Missing field, wrong type or value out of range. |
  | 400 | `INSUFFICIENT_VARIABLES` | The urgency score cannot be calculated with the variables received. |
  | 401 | `INVALID_API_KEY` | Missing or wrong `X-API-Key`. |
  | 404 | `NOT_FOUND` | Unknown route. |
  | 405 | `METHOD_NOT_ALLOWED` | Method not supported by the route. |
  | 500 | `INTERNAL_ERROR` | Unexpected error. No internal detail is exposed. |

### Shared types

**`FieldIndicators`.** Variables of a zone extracted from a field report. It is
the output of the structuring endpoint and the input of the urgency score, so
the backend chains both calls without translating anything. A variable that
could not be identified is `null` (or an empty list for `needs`) and is listed
in `missingVariables`.

| Field | Type | Values |
|---|---|---|
| `damageLevel` | string or `null` | `LOW`, `MODERATE`, `SEVERE`, `CRITICAL` |
| `familiesAffected` | integer ≥ 0 or `null` | |
| `peopleAffected` | integer ≥ 0 or `null` | |
| `children` | integer ≥ 0 or `null` | |
| `elderlyPeople` | integer ≥ 0 or `null` | |
| `disabledPeople` | integer ≥ 0 or `null` | |
| `needs` | list of strings | `WATER`, `FOOD`, `SHELTER`, `HYGIENE`, `MEDICINE`, `OTHER` |

The names and values match the `PopulationImpact` value object, the
`DamageLevel` enumeration and the resource categories of `auxia-backend`.

**`GeoPoint`.** `{ "latitude": number (-90 to 90), "longitude": number (-180 to 180) }`.

### 1. Structure a field report (US-02)

`POST /api/v1/field-reports/structure`

Extracts the indicators from the free text of a field report, written in
Spanish. `text` is required and has between 1 and 5000 characters.

Request:

```json
{
  "text": "Derrumbe de viviendas en el sector Alto Perú. Hay 35 familias afectadas, unas 140 personas, entre ellas 40 niños y 15 adultos mayores. Urge agua potable, alimentos y carpas."
}
```

Response `200`:

```json
{
  "indicators": {
    "damageLevel": "SEVERE",
    "familiesAffected": 35,
    "peopleAffected": 140,
    "children": 40,
    "elderlyPeople": 15,
    "disabledPeople": null,
    "needs": ["WATER", "FOOD", "SHELTER"]
  },
  "missingVariables": ["disabledPeople"],
  "modelVersion": "rules-v1"
}
```

Without `text`, or with an empty one: `400 VALIDATION_ERROR`.

### 2. Urgency score (US-04, US-05, TS-02)

`POST /api/v1/urgency-scores`

Calculates the urgency score of a zone from the same `indicators` returned by
the structuring endpoint, plus `zonePopulation`, the total number of people
living in the zone (integer > 0).

Request:

```json
{
  "indicators": {
    "damageLevel": "SEVERE",
    "familiesAffected": 35,
    "peopleAffected": 140,
    "children": 40,
    "elderlyPeople": 15,
    "disabledPeople": null,
    "needs": ["WATER", "FOOD", "SHELTER"]
  },
  "zonePopulation": 600
}
```

Response `200`:

```json
{
  "score": 78.4,
  "priorityLevel": "CRITICAL",
  "topFeatures": [
    { "feature": "damageLevel", "contribution": 30.0 },
    { "feature": "vulnerablePopulation", "contribution": 21.5 },
    { "feature": "peopleAffected", "contribution": 16.3 }
  ],
  "modelVersion": "rules-v1"
}
```

- `score` goes from 0 to 100 and has one decimal.
- `priorityLevel` is `LOW`, `MEDIUM`, `HIGH` or `CRITICAL`.
- `topFeatures` lists the variables that weighed the most, from highest to
  lowest. `contribution` is the number of score points each one added, with
  one decimal. `vulnerablePopulation` is `children + elderlyPeople +
  disabledPeople`.

When `damageLevel` or `peopleAffected` is `null`, the score is not available
(US-04, scenario 2): `400 INSUFFICIENT_VARIABLES`, with the missing variables
in `details`.

```json
{
  "code": "INSUFFICIENT_VARIABLES",
  "message": "The urgency score cannot be calculated with the variables received.",
  "details": [
    { "field": "indicators.damageLevel", "message": "Required to calculate the score" }
  ]
}
```

### 3. Distribution recommendation (US-11, TS-04)

`POST /api/v1/distribution-recommendations`

Recommends how to split the available inventory among the prioritized zones.
The quantities assigned to each resource **never** exceed its
`availableQuantity`. `zones` must have at least one zone.

Request:

```json
{
  "zones": [
    {
      "zoneId": "5b0c2f6e-8a1d-4c47-9f3e-2d6a1b7c9e01",
      "score": 78.4,
      "peopleAffected": 140,
      "needs": ["WATER", "FOOD"]
    },
    {
      "zoneId": "a3e9d4c2-1f6b-4e8a-b5d7-0c2e4f6a8b02",
      "score": 41.0,
      "peopleAffected": 90,
      "needs": ["WATER"]
    }
  ],
  "inventory": [
    {
      "resourceId": "c7f1e2d3-4b5a-4c6d-8e9f-0a1b2c3d4e03",
      "category": "WATER",
      "unit": "LITER",
      "availableQuantity": 500
    },
    {
      "resourceId": "d8a2f3e4-5c6b-4d7e-9f0a-1b2c3d4e5f04",
      "category": "FOOD",
      "unit": "KG",
      "availableQuantity": 300
    }
  ]
}
```

Response `200`:

```json
{
  "allocations": [
    {
      "zoneId": "5b0c2f6e-8a1d-4c47-9f3e-2d6a1b7c9e01",
      "items": [
        { "resourceId": "c7f1e2d3-4b5a-4c6d-8e9f-0a1b2c3d4e03", "quantity": 340 },
        { "resourceId": "d8a2f3e4-5c6b-4d7e-9f0a-1b2c3d4e5f04", "quantity": 140 }
      ],
      "coverage": "PARTIAL"
    },
    {
      "zoneId": "a3e9d4c2-1f6b-4e8a-b5d7-0c2e4f6a8b02",
      "items": [
        { "resourceId": "c7f1e2d3-4b5a-4c6d-8e9f-0a1b2c3d4e03", "quantity": 160 }
      ],
      "coverage": "PARTIAL"
    }
  ],
  "justification": "Inventory split in proportion to each zone's urgency score, capped by its needs and by the available stock.",
  "modelVersion": "rules-v1"
}
```

- `coverage` is `FULL`, `PARTIAL` or `NONE`. `PARTIAL` and `NONE` mark the
  zones left partially or totally unserved for lack of inventory (US-11,
  scenario 2).
- `unit` is `UNIT`, `KG`, `LITER` or `KIT`, as in the inventory of
  `auxia-backend`.

Without zones (`"zones": []`): `400 VALIDATION_ERROR`.

### 4. Brigade suggestion (Resource Management)

`POST /api/v1/brigade-assignments/suggestions`

Suggests the available brigade closest to the zone (haversine distance).
`brigades` must have at least one brigade.

Request:

```json
{
  "zoneLocation": { "latitude": -12.0464, "longitude": -77.0428 },
  "brigades": [
    {
      "brigadeId": "e9b3a4f5-6d7c-4e8f-a0b1-2c3d4e5f6a05",
      "location": { "latitude": -12.0560, "longitude": -77.0844 }
    },
    {
      "brigadeId": "f0c4b5a6-7e8d-4f9a-b1c2-3d4e5f6a7b06",
      "location": { "latitude": -12.1210, "longitude": -77.0300 }
    }
  ]
}
```

Response `200`:

```json
{
  "brigadeId": "e9b3a4f5-6d7c-4e8f-a0b1-2c3d4e5f6a05",
  "distanceKm": 4.6,
  "modelVersion": "rules-v1"
}
```

Without brigades (`"brigades": []`): `400 VALIDATION_ERROR`.
