from src.llm.schemas import (
    FinalizerOwner,
    FinalizerPeriod,
    FinalizerSupportedClaim,
    FinalizerInput,
    FinalizerOutput,
)
from src.db.enums import ReportPeriodType


def test_finalizer_input_and_output_shapes() -> None:
    owner = FinalizerOwner(display_name="Owner")
    period = FinalizerPeriod(type=ReportPeriodType.DAILY, label="Daily report")
    claim = FinalizerSupportedClaim(id="c1", text="x", signal_ids=["s1"])

    fin_in = FinalizerInput(
        report_id="r1",
        owner=owner,
        period=period,
        supported_claims=[claim],
    )
    assert fin_in.report_id == "r1"
    assert fin_in.supported_claims[0].id == "c1"

    fin_out = FinalizerOutput(report_id="r1", text="Hello")
    assert fin_out.text.startswith("Hello")

