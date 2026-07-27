"""FinalAnswer and related schema tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from geoagent.schemas import Citation, FinalAnswer, GeoRef, Handoff, Quantity, Refusal


def test_final_answer_answered_ok():
    answer = FinalAnswer(
        trace_id="01TESTTRACE00000000000000",
        status="answered",
        answer_md="Tree cover declined by about 12 ha.",
        numbers=[
            Quantity(
                name="tree_cover_loss",
                value=12.0,
                unit="ha",
                source_tool="landcover_classify",
            )
        ],
        citations=[
            Citation(
                doc_id="attica-env-plan-sample",
                chunk_id="c1",
                quote="Ring road corridor vegetation loss noted.",
            )
        ],
        geometries=[
            GeoRef(
                name="buffer",
                geojson={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [23.7, 37.9],
                            [23.8, 37.9],
                            [23.8, 38.0],
                            [23.7, 38.0],
                            [23.7, 37.9],
                        ]
                    ],
                },
                epsg_computed="EPSG:2100",
            )
        ],
        model_roster={"intake": "Qwen3.5-9B@Q4_K_M"},
    )
    assert answer.status == "answered"
    assert answer.refusal is None


def test_final_answer_refused_requires_refusal_and_empty_md():
    with pytest.raises(ValidationError):
        FinalAnswer(
            trace_id="t1",
            status="refused",
            answer_md="should be empty",
            refusal=Refusal(reason_code="out_of_aoi", message="Outside demo AOI"),
        )
    with pytest.raises(ValidationError):
        FinalAnswer(trace_id="t1", status="refused", answer_md="")

    ok = FinalAnswer(
        trace_id="t1",
        status="refused",
        answer_md="",
        refusal=Refusal(reason_code="out_of_aoi", message="Outside demo AOI"),
    )
    assert ok.refusal is not None


def test_citation_requires_span_or_quote():
    with pytest.raises(ValidationError):
        Citation(doc_id="d", chunk_id="c")
    Citation(doc_id="d", chunk_id="c", span_start=0, span_end=10)
    Citation(doc_id="d", chunk_id="c", quote="enough evidence")


def test_handoff_is_typed():
    handoff = Handoff(to="geodata", reason="Need ring-road geometry", state_delta={"aoi": "Attica"})
    assert handoff.to == "geodata"
    with pytest.raises(ValidationError):
        Handoff(to="supervisor", reason="not allowed")  # type: ignore[arg-type]
