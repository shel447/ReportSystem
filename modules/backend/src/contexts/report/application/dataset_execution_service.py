"""报告数据集执行编排。"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any

from ....shared.kernel.errors import ErrorCode, UpstreamError, ValidationError
from ..domain.generation_models import DatasetExecutionResult, TemplateInstance, WarningItem
from ..domain.template_models import DatasetDefinition, Parameter, ParameterValue, parameter_value_to_dict

PARAMETER_PLACEHOLDER_PATTERN = re.compile(r"\{\$([A-Za-z0-9_\-]+)\}")
LOGGER = logging.getLogger(__name__)


class DatasetExecutionService:
    """执行 SQL/API 数据集，并把外部响应收口为强类型结果。"""

    def __init__(self, *, query_service, schema_gateway) -> None:
        self.query_service = query_service
        self.schema_gateway = schema_gateway

    def resolve(self, *, template_instance: TemplateInstance, user_id: str) -> dict[str, dict[str, DatasetExecutionResult]]:
        resolved: dict[str, dict[str, DatasetExecutionResult]] = {}
        for section, parameters in _iter_sections(template_instance):
            values = _merge_parameter_values(parameters)
            section_results: dict[str, DatasetExecutionResult] = {}
            for dataset in list(section.content.datasets or []):
                if dataset.id not in _referenced_dataset_ids(section):
                    continue
                section_results[dataset.id] = self._execute(
                    dataset=dataset,
                    template_instance_id=template_instance.id,
                    section_id=section.id,
                    parameters=values,
                    user_id=user_id,
                )
            resolved[section.id] = section_results
        return resolved

    def _execute(
        self,
        *,
        dataset: DatasetDefinition,
        template_instance_id: str,
        section_id: str,
        parameters: dict[str, list[ParameterValue]],
        user_id: str,
    ) -> DatasetExecutionResult:
        context = {
            "lineage.tracing.enable": True,
            "templateInstanceId": template_instance_id,
            "sectionId": section_id,
            "datasetId": dataset.id,
        }
        if dataset.source_type == "sql":
            query = _render_sql(dataset.source_ref, parameters)
            execute = lambda: self.query_service.execute_sql(query=query, context=context, user_id=user_id)
        elif dataset.source_type == "api":
            execute = lambda: self.query_service.execute_api(
                source=dataset.source_ref,
                payload={
                    "parameters": {
                        key: [parameter_value_to_dict(item) for item in items]
                        for key, items in parameters.items()
                    },
                    "context": context,
                },
                user_id=user_id,
            )
        else:
            raise ValidationError(
                f"dataset sourceType is not executable yet: {dataset.source_type}",
                error_code="chatbi.report.dataset.source_type_unsupported",
                category="capability",
            )
        try:
            result = execute()
        except UpstreamError as exc:
            ret_code = exc.details.get("retCode")
            if ret_code is None:
                raise
            ret_info = str(exc)
            warning = WarningItem(
                code=ErrorCode.REPORT_DATASET_BUSINESS_FAILED_DEGRADED,
                message=f"dataset {dataset.id} query failed: retCode={ret_code}, retInfo={ret_info}",
                target_id=dataset.id,
            )
            LOGGER.warning(warning.message)
            return DatasetExecutionResult(dataset_id=dataset.id, warnings=[warning])
        columns = {item.key: copy.deepcopy(item.metadata) for item in result.columns}
        _validate_lineage(columns=columns, enabled=bool(context["lineage.tracing.enable"]))
        return DatasetExecutionResult(
            dataset_id=dataset.id,
            columns=[{"key": key, **metadata} for key, metadata in columns.items()],
            rows=copy.deepcopy(list(result.rows)),
        )


def _render_sql(source: str, parameters: dict[str, list[ParameterValue]]) -> str:
    def replace(match: re.Match[str]) -> str:
        values = list(parameters.get(match.group(1)) or [])
        return ", ".join(str(item.query) for item in values if item.query is not None)

    return PARAMETER_PLACEHOLDER_PATTERN.sub(replace, str(source or "")).strip()


def _validate_lineage(*, columns: dict[str, Any], enabled: bool) -> None:
    if not enabled:
        return
    for key, metadata in columns.items():
        lineage = metadata.get("lineageTracing") if isinstance(metadata, dict) else None
        sources = lineage.get("sources") if isinstance(lineage, dict) else None
        if not isinstance(sources, list) or not sources:
            raise ValidationError(
                f"dataset column lineage is required when tracing is enabled: {key}",
                error_code=ErrorCode.REPORT_DATASET_INVALID_RESPONSE,
            )


def _merge_parameter_values(parameters: list[Parameter]) -> dict[str, list[ParameterValue]]:
    merged: dict[str, list[ParameterValue]] = {}
    for parameter in parameters:
        if parameter.id and parameter.values:
            merged[parameter.id] = copy.deepcopy(parameter.values)
    return merged


def _referenced_dataset_ids(section) -> set[str]:
    referenced: set[str] = set()
    for block in list(section.content.presentation.blocks or []):
        if getattr(block, "dataset_id", None):
            referenced.add(str(block.dataset_id))
        if block.type == "text":
            referenced.update(match.group(1) for match in re.finditer(r"\{#([A-Za-z0-9_\-]+)\.[A-Za-z0-9_\-]+\}", str(block.template or "")))
        if block.type == "composite_table":
            referenced.update(str(part.dataset_id) for part in list(block.parts or []) if getattr(part, "dataset_id", None))
    return referenced


def _iter_sections(template_instance: TemplateInstance):
    root = list(template_instance.parameters or [])

    def catalogs(items, inherited):
        for catalog in list(items or []):
            visible = [*inherited, *list(catalog.parameters or [])]
            for section in list(catalog.sections or []):
                yield section, [*visible, *list(section.parameters or [])]
            yield from catalogs(catalog.sub_catalogs, visible)

    def chapters(items, inherited):
        for chapter in list(items or []):
            chapter_visible = [*inherited, *list(chapter.parameters or [])]
            for slide in list(chapter.slides or []):
                slide_visible = [*chapter_visible, *list(slide.parameters or [])]
                for section in list(slide.sections or []):
                    yield section, [*slide_visible, *list(section.parameters or [])]

    if (template_instance.structure_type or "flow") == "paged":
        yield from chapters(template_instance.chapters, root)
    else:
        yield from catalogs(template_instance.catalogs, root)
