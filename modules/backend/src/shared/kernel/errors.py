from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


class ErrorCode:
    """Public ChatBI error codes.

    Codes must use the `chatbi.` prefix and must not expose internal framework
    names or upstream module names as the public code prefix.
    """

    BASE_UNKNOWN = "chatbi.base.unknown"
    BASE_PARAM_INVALID = "chatbi.base.param.invalid"
    BASE_OVERTIME = "chatbi.base.overtime"
    BASE_AUTH_REQUIRED = "chatbi.base.auth.required"
    BASE_PERMISSION_DENIED = "chatbi.base.permission.denied"
    BASE_RESOURCE_NOT_FOUND = "chatbi.base.resource.not_found"
    BASE_RESOURCE_CONFLICT = "chatbi.base.resource.conflict"
    BASE_CAPABILITY_UNSUPPORTED = "chatbi.base.capability.unsupported"
    BASE_UPSTREAM_UNAVAILABLE = "chatbi.base.upstream.unavailable"
    BASE_UPSTREAM_INVALID_RESPONSE = "chatbi.base.upstream.invalid_response"

    CONVERSATION_IN_PROGRESS = "chatbi.conversation.in_progress"
    CONVERSATION_QUOTA_EXCEEDED = "chatbi.conversation.quota_exceeded"
    CONVERSATION_CREATE_FAILED = "chatbi.conversation.create_failed"
    CONVERSATION_CHAT_CREATE_FAILED = "chatbi.conversation.chat_create_failed"
    CONVERSATION_ASK_NOT_PENDING = "chatbi.conversation.ask_not_pending"
    CONVERSATION_CANCEL_NOT_RUNNING = "chatbi.conversation.cancel_not_running"
    CONVERSATION_CANCELLED = "chatbi.conversation.cancelled"
    CONVERSATION_TERMINATED = "chatbi.conversation.terminated"
    CONVERSATION_REFUSED = "chatbi.conversation.refused"
    CONVERSATION_ARCHIVE_FAILED = "chatbi.conversation.archive_failed"

    REPORT_TEMPLATE_NOT_FOUND = "chatbi.report.template.not_found"
    REPORT_TEMPLATE_ID_CONFLICT = "chatbi.report.template.id_conflict"
    REPORT_TEMPLATE_SCHEMA_INVALID = "chatbi.report.template.schema_invalid"
    REPORT_PARAMETER_MISSING_REQUIRED = "chatbi.report.parameter.missing_required"
    REPORT_PARAMETER_OPTIONS_UNAVAILABLE = "chatbi.report.parameter.options_unavailable"
    REPORT_PARAMETER_EXTRACTION_FAILED = "chatbi.report.parameter.extraction_failed"
    REPORT_PARAMETER_PROMPT_FAILED = "chatbi.report.parameter.prompt_failed"
    REPORT_GENERATION_DSL_INVALID = "chatbi.report.generation.dsl_invalid"
    REPORT_GENERATION_CANCELLED = "chatbi.report.generation.cancelled"
    REPORT_SECTION_NOT_FOUND = "chatbi.report.section.not_found"
    REPORT_DATASET_INVALID_RESPONSE = "chatbi.report.dataset.invalid_response"
    REPORT_DATASET_BUSINESS_FAILED_DEGRADED = "chatbi.report.dataset.business_failed_degraded"
    REPORT_DOCUMENT_PDF_NOT_AVAILABLE = "chatbi.report.document.pdf_not_available"
    REPORT_DOCUMENT_EXPORT_FAILED = "chatbi.report.document.export_failed"
    REPORT_DOCUMENT_FILE_MISSING = "chatbi.report.document.file_missing"

    DATA_ANALYSIS_QUERY_BLOCKED = "chatbi.data_analysis.query_blocked"
    DATA_ANALYSIS_QUERY_GENERATION_FAILED = "chatbi.data_analysis.query_generation_failed"
    DATA_ANALYSIS_QUERY_UNSUPPORTED_SYNTAX = "chatbi.data_analysis.query.unsupported_syntax"
    DATA_ANALYSIS_QUERY_FIELD_NOT_FOUND = "chatbi.data_analysis.query.field_not_found"
    DATA_ANALYSIS_DATASOURCE_UNAVAILABLE = "chatbi.data_analysis.datasource_unavailable"
    DATA_ANALYSIS_RESULT_INVALID = "chatbi.data_analysis.result_invalid"
    DATA_ANALYSIS_VISUALIZATION_FAILED = "chatbi.data_analysis.visualization_failed"
    DATA_ANALYSIS_SUMMARY_FAILED = "chatbi.data_analysis.summary_failed"


@dataclass(slots=True)
class DomainError(Exception):
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class ErrorDescriptor:
    error_code: str
    error_msg: str
    category: str = "business"
    retryable: bool = False
    source: str | None = None
    details: Dict[str, Any] = field(default_factory=dict)
    http_status: int = 400


class ApplicationError(Exception):
    error_code: str = ErrorCode.BASE_UNKNOWN
    category: str = "business"
    retryable: bool = False
    source: str | None = None
    http_status: int = 400

    def __init__(
        self,
        message: str,
        details: Dict[str, Any] | None = None,
        *,
        error_code: str | None = None,
        category: str | None = None,
        retryable: bool | None = None,
        source: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})
        if error_code is not None:
            self.error_code = error_code
        if category is not None:
            self.category = category
        if retryable is not None:
            self.retryable = retryable
        if source is not None:
            self.source = source
        if http_status is not None:
            self.http_status = http_status

    def __str__(self) -> str:
        return self.message


class ValidationError(ApplicationError):
    error_code = ErrorCode.BASE_PARAM_INVALID
    category = "param"
    http_status = 400


class PermissionDeniedError(ApplicationError):
    error_code = ErrorCode.BASE_PERMISSION_DENIED
    category = "auth"
    retryable = False
    http_status = 403


class NotFoundError(ApplicationError):
    error_code = ErrorCode.BASE_RESOURCE_NOT_FOUND
    category = "resource"
    http_status = 404


class ConflictError(ApplicationError):
    error_code = ErrorCode.BASE_RESOURCE_CONFLICT
    category = "state"
    http_status = 409


class UpstreamError(ApplicationError):
    error_code = ErrorCode.BASE_UPSTREAM_UNAVAILABLE
    category = "upstream"
    retryable = True
    http_status = 502


class UnsupportedCapabilityError(ApplicationError):
    error_code = ErrorCode.BASE_CAPABILITY_UNSUPPORTED
    category = "capability"
    http_status = 501


def error_response_payload(
    error: ApplicationError | ErrorDescriptor | Exception | str,
    *,
    request_id: str | None = None,
    fallback_message: str | None = None,
) -> dict[str, Any]:
    """Serialize errors to the public ChatBI error object."""

    if isinstance(error, ErrorDescriptor):
        payload = {
            "errorCode": error.error_code,
            "errorMsg": error.error_msg,
            "category": error.category,
            "retryable": error.retryable,
            "source": error.source,
            "requestId": request_id,
            "details": dict(error.details),
        }
    elif isinstance(error, ApplicationError):
        payload = {
            "errorCode": error.error_code,
            "errorMsg": error.message,
            "category": error.category,
            "retryable": error.retryable,
            "source": error.source,
            "requestId": request_id,
            "details": dict(error.details),
        }
    else:
        payload = {
            "errorCode": ErrorCode.BASE_UNKNOWN,
            "errorMsg": fallback_message or str(error or "系统处理失败，请稍后重试。"),
            "category": "unknown",
            "retryable": False,
            "source": None,
            "requestId": request_id,
            "details": {},
        }
    return {key: value for key, value in payload.items() if value is not None}


def http_status_for(error: ApplicationError | ErrorDescriptor | Exception) -> int:
    if isinstance(error, ErrorDescriptor):
        return error.http_status
    if isinstance(error, ApplicationError):
        return error.http_status
    return 500
