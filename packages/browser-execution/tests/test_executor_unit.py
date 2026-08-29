from qgate_browser_execution.classification import assertion_failure, classify_exception
from qgate_browser_execution.models import ExecutionStatus, FailureCategory, OperationKind


def test_assertion_failure_is_not_execution_environment_error() -> None:
    status, category = assertion_failure()
    assert status == ExecutionStatus.FAILED
    assert category == FailureCategory.ASSERTION_FAILURE


def test_navigation_connection_refused_is_environment_failure() -> None:
    status, category = classify_exception(
        OperationKind.NAVIGATE, RuntimeError("net::ERR_CONNECTION_REFUSED")
    )
    assert status == ExecutionStatus.EXECUTION_ERROR
    assert category == FailureCategory.ENVIRONMENT_FAILURE
