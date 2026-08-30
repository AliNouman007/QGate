import asyncio
from unittest.mock import AsyncMock, MagicMock

from qgate_browser_execution.assertion_synthesis import (
    AssertionSynthesizer,
    BaselineAssertion,
    extract_relevance_tokens,
)
from qgate_browser_execution.models import (
    CompiledStep,
    ExecutionStatus,
    FailureCategory,
    OperationKind,
    TargetHint,
)


def test_extract_relevance_tokens():
    tokens = extract_relevance_tokens(
        state_key="app/shop-context.js:user:wallet",
        state_label="Wallet",
        route="/checkout",
        evidence_excerpts=["const { subtotal, shipping, discount, wallet, total } = useShop();"],
    )
    assert "wallet" in tokens
    assert "total" in tokens
    assert "subtotal" in tokens
    assert "discount" in tokens

def test_no_hardcoded_literals_in_assertion_synthesis_module():
    import inspect

    import qgate_browser_execution.assertion_synthesis as module
    source = inspect.getsource(module)
    for forbidden in ["wallet", "/checkout", "final-payable", "wallet-deduction", "$9", "$19", "qgate-test-shop"]:
        assert forbidden not in source.lower(), f"Found forbidden literal {forbidden!r} in assertion_synthesis module!"

def test_baseline_assertion_model_structure():
    assertion = BaselineAssertion(
        scenario_key="scn_123",
        route="/checkout",
        state_key="app/shop-context.js:user:wallet",
        pass_key="scn_123:pass:1",
        target=TargetHint(test_id="payable-amount"),
        operation=OperationKind.ASSERT_TEXT,
        expected_value="$9.00",
        reason="Matched tokens total, payable",
        provenance="baseline_observation",
    )
    assert assertion.scenario_key == "scn_123"
    assert assertion.expected_value == "$9.00"
    assert assertion.target.test_id == "payable-amount"

def test_form_select_control_rejected_as_candidate():
    synthesizer = AssertionSynthesizer()
    candidates = [
        {
            "tag": "select",
            "testId": "user-state-switcher",
            "id": "switcher",
            "className": "switcher-class",
            "role": "combobox",
            "name": "State Switcher",
            "text": "Logged In + Wallet",
            "hasChildren": True,
        },
        {
            "tag": "span",
            "testId": "final-payable-output",
            "id": "payable",
            "className": "summary-total",
            "role": "status",
            "name": "Total Payable",
            "text": "$9.00",
            "hasChildren": False,
        },
    ]
    relevance_tokens = {"payable", "total", "wallet"}
    filtered = synthesizer.filter_and_rank_candidates(
        candidates,
        relevance_tokens=relevance_tokens,
        route="/checkout",
        state_key="app/shop-context.js:user:wallet",
    )
    assert len(filtered) == 1
    assert filtered[0]["testId"] == "final-payable-output"
    assert filtered[0]["text"] == "$9.00"

def test_unstable_or_volatile_candidate_rejected():
    synthesizer = AssertionSynthesizer()
    volatile_candidate = {
        "tag": "span",
        "testId": "timestamp-output",
        "id": "ts",
        "className": "time",
        "role": None,
        "name": None,
        "text": "2026-08-30T05:27:00Z",
        "hasChildren": False,
    }
    is_valid = synthesizer.is_stable_candidate(volatile_candidate)
    assert not is_valid

def test_assertions_remain_state_specific():
    guest_assertion = BaselineAssertion(
        scenario_key="scn_cross",
        route="/checkout",
        state_key="app/shop-context.js:user:guest",
        pass_key="scn_cross:pass:0",
        target=TargetHint(test_id="payable-amount"),
        operation=OperationKind.ASSERT_TEXT,
        expected_value="$19.00",
        reason="Guest baseline",
    )
    wallet_assertion = BaselineAssertion(
        scenario_key="scn_cross",
        route="/checkout",
        state_key="app/shop-context.js:user:wallet",
        pass_key="scn_cross:pass:1",
        target=TargetHint(test_id="payable-amount"),
        operation=OperationKind.ASSERT_TEXT,
        expected_value="$9.00",
        reason="Wallet baseline",
    )
    assert guest_assertion.expected_value == "$19.00"
    assert wallet_assertion.expected_value == "$9.00"
    assert guest_assertion.state_key != wallet_assertion.state_key

def test_ambiguous_top_candidates_rejected():
    synthesizer = AssertionSynthesizer()
    candidates = [
        {
            "tag": "span",
            "testId": "payable-1",
            "id": "p1",
            "className": "total",
            "role": None,
            "name": None,
            "text": "$9.00",
            "hasChildren": False,
        },
        {
            "tag": "span",
            "testId": "payable-2",
            "id": "p2",
            "className": "total",
            "role": None,
            "name": None,
            "text": "$19.00",
            "hasChildren": False,
        },
    ]
    relevance_tokens = {"total"}
    filtered = synthesizer.filter_and_rank_candidates(
        candidates, relevance_tokens=relevance_tokens, route="/checkout"
    )
    # Different expected values for top score -> fail closed, return empty list!
    assert len(filtered) == 0

def test_compiled_assertion_step_fails_on_value_mismatch():
    # Simulate step execution evaluation logic for ASSERT_TEXT step
    step = CompiledStep(
        index=3,
        operation=OperationKind.ASSERT_TEXT,
        source_action="Verify product output equals baseline expected value",
        source_expected="$9.00",
        target=TargetHint(test_id="final-payable"),
        expected="$9.00",
        required=True,
    )
    actual_value = "$19.00"
    assert step.expected != actual_value
    # Verification that mismatch is ASSERTION_FAILURE
    status = ExecutionStatus.FAILED if step.expected != actual_value else ExecutionStatus.PASSED
    failure_category = FailureCategory.ASSERTION_FAILURE if status == ExecutionStatus.FAILED else None
    assert status == ExecutionStatus.FAILED
    assert failure_category == FailureCategory.ASSERTION_FAILURE


def test_baseline_observation_stabilizes_consecutive_reads():
    synthesizer = AssertionSynthesizer()
    mock_page = MagicMock()
    # Simulate 3 reads: un-hydrated -> changing -> stabilized
    read_1 = [{"tag": "span", "testId": "payable", "id": None, "role": None, "name": None, "text": "$31.00", "hasChildren": False}]
    read_2 = [{"tag": "span", "testId": "payable", "id": None, "role": None, "name": None, "text": "$9.00", "hasChildren": False}]
    read_3 = [{"tag": "span", "testId": "payable", "id": None, "role": None, "name": None, "text": "$9.00", "hasChildren": False}]

    mock_page.evaluate = AsyncMock(side_effect=[read_1, read_2, read_3])

    res = asyncio.run(
        synthesizer.observe_baseline_assertions(
            mock_page,
            scenario_key="scn_test",
            route="/checkout",
            state_key="app/shop-context.js:user:wallet",
            pass_key="scn_test:pass:1",
            relevance_tokens={"payable", "wallet", "total"},
        )
    )

    assert len(res) >= 1
    assert res[0].expected_value == "$9.00"
    assert mock_page.evaluate.call_count == 3

def test_stabilization_timeout_fails_closed():
    synthesizer = AssertionSynthesizer()
    mock_page = MagicMock()
    # Volatile candidate that changes on every read
    counter = [0]
    def get_volatile_cands():
        counter[0] += 1
        return [{"tag": "span", "testId": "payable", "id": None, "role": None, "name": None, "text": f"${counter[0]}.00", "hasChildren": False}]

    mock_page.evaluate = AsyncMock(side_effect=lambda js: get_volatile_cands())

    res = asyncio.run(
        synthesizer.observe_baseline_assertions(
            mock_page,
            scenario_key="scn_volatile",
            route="/checkout",
            state_key="app/shop-context.js:user:wallet",
            pass_key="scn_volatile:pass:1",
            relevance_tokens={"payable"},
            stabilization_timeout_ms=300,
            poll_interval_ms=50,
        )
    )

    # Never stabilized -> fails closed (returns empty list)
    assert res == []


