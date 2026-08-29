from __future__ import annotations

from .models import ExecutionStatus, FailureCategory, OperationKind


def classify_exception(operation: OperationKind, exc: BaseException) -> tuple[ExecutionStatus, FailureCategory]:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return ExecutionStatus.EXECUTION_ERROR, FailureCategory.TIMEOUT
    if operation == OperationKind.NAVIGATE:
        if any(token in message for token in ("connection refused", "net::err", "name not resolved")):
            return ExecutionStatus.EXECUTION_ERROR, FailureCategory.ENVIRONMENT_FAILURE
        return ExecutionStatus.EXECUTION_ERROR, FailureCategory.NAVIGATION_FAILURE
    if operation in {
        OperationKind.CLICK,
        OperationKind.FILL,
        OperationKind.SELECT,
        OperationKind.ASSERT_VISIBLE,
        OperationKind.ASSERT_HIDDEN,
        OperationKind.ASSERT_TEXT,
        OperationKind.ASSERT_VALUE,
        OperationKind.ASSERT_ATTRIBUTE,
        OperationKind.ASSERT_LAYOUT_STATE,
    }:
        return ExecutionStatus.EXECUTION_ERROR, FailureCategory.TARGET_RESOLUTION_FAILURE
    return ExecutionStatus.EXECUTION_ERROR, FailureCategory.UNKNOWN_EXECUTION_FAILURE


def assertion_failure() -> tuple[ExecutionStatus, FailureCategory]:
    return ExecutionStatus.FAILED, FailureCategory.ASSERTION_FAILURE
