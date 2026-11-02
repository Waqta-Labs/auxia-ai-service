import json

from fastapi.testclient import TestClient


def test_openapi_documents_400_instead_of_422(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    operations = [operation for path in document["paths"].values() for operation in path.values()]
    assert all("422" not in operation["responses"] for operation in operations)
    assert "400" in document["paths"]["/api/v1/urgency-scores"]["post"]["responses"]
    assert "400" in document["paths"]["/api/v1/field-reports/structure"]["post"]["responses"]


def test_openapi_has_no_reference_to_the_default_validation_schemas(client: TestClient) -> None:
    document = client.get("/openapi.json").json()

    assert "HTTPValidationError" not in json.dumps(document)
    assert "#/components/schemas/ValidationError" not in json.dumps(document)
