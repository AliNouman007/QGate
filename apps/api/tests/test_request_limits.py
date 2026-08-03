"""Trust-boundary limits for collection-heavy API payloads."""

import pytest
from pydantic import ValidationError
from suitest_api.schemas.ingest import IngestResult, IngestRunStep, RunIngestBody
from suitest_api.schemas.suite import SuiteUpdate


def test_rejects_oversized_collection_payloads() -> None:
    step = IngestRunStep(order=1)
    with pytest.raises(ValidationError):
        IngestResult(steps=[step] * 501)
    with pytest.raises(ValidationError):
        RunIngestBody(suite_name="suite", name="run", results=[IngestResult()] * 501)
    with pytest.raises(ValidationError):
        SuiteUpdate(case_order=[str(index) for index in range(1_001)])
