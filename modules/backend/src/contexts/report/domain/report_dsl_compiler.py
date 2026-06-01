"""把已解析的模板实例编译为正式 Report DSL，不访问任何基础设施。"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

from .generation_models import (
    BackCoverConfig,
    ChartComponent,
    ChartDataProperties,
    CompositeTableComponent,
    CompositeTableDataProperties,
    DatasetExecutionResult,
    GridDefinition,
    MarkdownComponent,
    MarkdownDataProperties,
    MergeRowInfo,
    ReportAdditionalInfo,
    ReportBasicInfo,
    ReportCatalog,
    ReportColumn,
    ReportDsl,
    ReportGenerateMeta,
    ReportLayout,
    ReportSection,
    ReportSlide,
    ReportSlideSection,
    ReportSummary,
    TableComponent,
    TableDataProperties,
    TemplateInstance,
    TextComponent,
    TextDataProperties,
)
from .template_models import ReportTemplate

DATASET_PLACEHOLDER_PATTERN = re.compile(r"\{#([A-Za-z0-9_\-]+)\.([A-Za-z0-9_\-]+)\}")
DatasetResults = dict[str, dict[str, DatasetExecutionResult]]


class ReportDslCompiler:
    """将实例树确定性编译为 flow 或 paged Report DSL。"""

    def compile(
        self,
        *,
        report_id: str,
        template: ReportTemplate,
        template_instance: TemplateInstance,
        dataset_results: DatasetResults | None = None,
        custom_catalogs: dict[str, ReportCatalog] | None = None,
        custom_sections: dict[str, ReportSection] | None = None,
        custom_slides: dict[str, ReportSlide] | None = None,
        custom_components: dict[str, list[Any]] | None = None,
    ) -> ReportDsl:
        results = dataset_results or {}
        custom_catalogs = custom_catalogs or {}
        custom_sections = custom_sections or {}
        custom_slides = custom_slides or {}
        custom_components = custom_components or {}
        report_meta: dict[str, ReportGenerateMeta] = {}
        today = datetime.now(timezone.utc).date().isoformat()
        basic_info = ReportBasicInfo(
            id=report_id,
            schema_version="1.0.0",
            status="Success",
            name=_build_report_name(template=template, template_instance=template_instance),
            report_type="PPT" if (template_instance.structure_type or "flow") == "paged" else "Word",
            description=template.description,
            template_id=template.id,
            template_name=template.name,
            create_date=f"{today}T00:00:00Z",
            modify_date=f"{today}T00:00:00Z",
            creator="report-system",
            modifier="report-system",
            category=template.category,
        )
        if (template_instance.structure_type or "flow") == "paged":
            content = [
                ReportSlideSection(
                    id=chapter.id,
                    title=chapter.title,
                    slides=[
                        self._compile_slide(
                            slide,
                            report_meta=report_meta,
                            dataset_results=results,
                            custom_sections=custom_sections,
                            custom_slides=custom_slides,
                            custom_components=custom_components,
                        )
                        for slide in list(chapter.slides or [])
                    ],
                )
                for chapter in list(template_instance.chapters or [])
            ]
            return ReportDsl(
                structure_type="paged",
                basic_info=basic_info,
                content=content,
                back_cover=BackCoverConfig(text="谢谢"),
                report_meta=report_meta,
            )
        catalogs = [
            self._compile_catalog(
                item,
                report_meta=report_meta,
                dataset_results=results,
                custom_catalogs=custom_catalogs,
                custom_sections=custom_sections,
            )
            for item in template_instance.catalogs
        ]
        return ReportDsl(
            structure_type="flow",
            basic_info=basic_info,
            catalogs=catalogs,
            summary=ReportSummary(id="summary_report", overview=_build_report_summary(catalogs)),
            report_meta=report_meta,
            layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
        )

    def compile_section(
        self,
        section,
        *,
        dataset_results: dict[str, DatasetExecutionResult] | None = None,
        custom_components: list[Any] | None = None,
    ) -> tuple[ReportSection, ReportGenerateMeta]:
        components, summary, additional_infos = _build_section_components(section, dataset_results or {})
        components.extend(copy.deepcopy(list(custom_components or [])))
        return (
            ReportSection(
                id=section.id,
                title=_section_title(section),
                components=components,
                summary=ReportSummary(id=f"summary_{section.id}", overview=summary),
            ),
            ReportGenerateMeta(
                status="Success",
                question=section.outline.rendered_requirement or section.outline.requirement or "",
                additional_infos=[ReportAdditionalInfo(type="Summary", value=summary), *additional_infos],
                outline=copy.deepcopy(section.outline),
                parameters={parameter.id: copy.deepcopy(parameter) for parameter in list(section.parameters or [])},
            ),
        )

    def _compile_catalog(self, catalog, *, report_meta, dataset_results, custom_catalogs, custom_sections) -> ReportCatalog:
        custom_catalog = custom_catalogs.get(str(catalog.id or ""))
        if custom_catalog is not None:
            resolved = copy.deepcopy(custom_catalog)
            _record_custom_catalog_meta(resolved, report_meta, prompt=str(catalog.rendered_title or catalog.title or catalog.id or ""))
            return resolved
        sections: list[ReportSection] = []
        for section in list(catalog.sections or []):
            custom_section = custom_sections.get(str(section.id or ""))
            if custom_section is not None:
                resolved = copy.deepcopy(custom_section)
                sections.append(resolved)
                report_meta[resolved.id] = _custom_meta(section)
            else:
                compiled, meta = self.compile_section(section, dataset_results=dataset_results.get(section.id, {}))
                sections.append(compiled)
                report_meta[section.id] = meta
        return ReportCatalog(
            id=catalog.id,
            name=catalog.rendered_title or catalog.title or catalog.id,
            sub_catalogs=[
                self._compile_catalog(
                    item,
                    report_meta=report_meta,
                    dataset_results=dataset_results,
                    custom_catalogs=custom_catalogs,
                    custom_sections=custom_sections,
                )
                for item in list(catalog.sub_catalogs or [])
            ],
            sections=sections,
        )

    def _compile_slide(self, slide, *, report_meta, dataset_results, custom_sections, custom_slides, custom_components) -> ReportSlide:
        custom_slide = custom_slides.get(str(slide.id or ""))
        if custom_slide is not None:
            return copy.deepcopy(custom_slide)
        components: list[Any] = []
        for section in list(slide.sections or []):
            custom_section = custom_sections.get(str(section.id or ""))
            if custom_section is not None:
                components.extend(copy.deepcopy(custom_section.components))
                report_meta[section.id] = _custom_meta(section)
                continue
            compiled, meta = self.compile_section(
                section,
                dataset_results=dataset_results.get(section.id, {}),
                custom_components=custom_components.get(section.id, []),
            )
            components.extend(compiled.components)
            report_meta[section.id] = meta
        return ReportSlide(
            id=slide.id,
            title=slide.title,
            layout=ReportLayout(type="grid", auto_layout=True, grid=GridDefinition(cols=12, row_height=24)),
            components=components,
        )


def build_generation_progress(report: ReportDsl) -> tuple[int, int]:
    if (report.structure_type or "flow") == "paged":
        slides = [slide for item in list(report.content or []) for slide in (item.slides if isinstance(item, ReportSlideSection) else [item])]
        return len(slides), len(report.content or [])
    return len(_collect_section_titles(list(report.catalogs or []))), _count_catalogs(list(report.catalogs or []))


def find_template_instance_section(catalogs, section_id: str, *, chapters=None):
    for catalog in list(catalogs or []):
        for section in list(catalog.sections or []):
            if str(section.id or "") == section_id:
                return section
        found = find_template_instance_section(catalog.sub_catalogs, section_id)
        if found is not None:
            return found
    for chapter in list(chapters or []):
        for slide in list(chapter.slides or []):
            for section in list(slide.sections or []):
                if str(section.id or "") == section_id:
                    return section
    return None


def resource_status_from_dsl(report: ReportDsl) -> str:
    status = str(report.basic_info.status or "").strip()
    return "generating" if status == "Running" else "failed" if status == "Failed" else "available"


def _build_section_components(section, dataset_results: dict[str, DatasetExecutionResult]) -> tuple[list[Any], str, list[ReportAdditionalInfo]]:
    requirement = str(section.outline.rendered_requirement or section.outline.requirement or "")
    additional_infos = [
        ReportAdditionalInfo(type="SQL", value=str(binding.resolved_query or "").strip())
        for binding in list(section.runtime_context.bindings or [])
        if str(binding.resolved_query or "").strip()
    ]
    components: list[Any] = [
        MarkdownComponent(
            id=f"component_{section.id}_markdown",
            type="markdown",
            data_properties=MarkdownDataProperties(data_type="static", content=_build_markdown_content(section, requirement)),
        )
    ]
    for block in list(section.content.presentation.blocks or []):
        if block.type == "text":
            components.append(_build_text_component(block, dataset_results))
        elif block.type == "table":
            components.append(_build_table_component(block, dataset_results))
        elif block.type == "chart":
            components.append(_build_chart_component(block, dataset_results))
        elif block.type == "composite_table":
            components.append(_build_composite_table_component(block, dataset_results))
    return components, (requirement or str(section.id or ""))[:160], additional_infos


def _build_markdown_content(section, requirement: str) -> str:
    return f"## {_section_title(section)}\n\n{requirement or '本章节基于模板诉求自动生成。'}"


def _build_text_component(block, datasets) -> TextComponent:
    content = DATASET_PLACEHOLDER_PATTERN.sub(
        lambda match: _dataset_value(datasets, match.group(1), match.group(2)),
        str(getattr(block, "content", None) or ""),
    )
    return TextComponent(id=str(block.id or ""), type="text", data_properties=TextDataProperties(data_type="static", content=content, title=str(block.title or "")))


def _build_table_component(block, datasets) -> TableComponent:
    result = datasets.get(str(block.dataset_id or "")) or DatasetExecutionResult(dataset_id=str(block.dataset_id or ""))
    columns = _merge_table_columns(getattr(getattr(block, "properties", None), "columns", []), result)
    rows = copy.deepcopy(result.rows)
    definitions = list(getattr(getattr(block, "properties", None), "merge_rows", []) or [])
    return TableComponent(
        id=str(block.id or ""),
        type="table",
        data_properties=TableDataProperties(
            data_type="static",
            source_id=str(block.dataset_id or ""),
            title=str(block.title or ""),
            columns=columns,
            merge_columns=list(getattr(getattr(block, "properties", None), "merge_columns", []) or []),
            merge_rows=_build_merge_rows(data=rows, columns=columns, definitions=definitions),
            data=rows,
        ),
    )


def _build_chart_component(block, datasets) -> ChartComponent:
    result = datasets.get(str(block.dataset_id or "")) or DatasetExecutionResult(dataset_id=str(block.dataset_id or ""))
    columns = _result_columns(result)
    series_type = str(getattr(getattr(block, "properties", None), "preferred_type", None) or "line")
    return ChartComponent(
        id=str(block.id or ""),
        type="chart",
        data_properties=ChartDataProperties(
            data_type="static",
            source_id=str(block.dataset_id or ""),
            title=str(block.title or ""),
            columns=columns,
            data=copy.deepcopy(result.rows),
            series=_chart_series(series_type, columns),
        ),
    )


def _build_composite_table_component(block, datasets) -> CompositeTableComponent:
    return CompositeTableComponent(
        id=str(block.id or ""),
        type="compositeTable",
        tables=[_build_composite_table_part(part, datasets) for part in list(block.parts or [])],
        data_properties=CompositeTableDataProperties(data_type="static", title=str(block.title or "")),
    )


def _build_composite_table_part(part, datasets) -> TableComponent:
    columns = _table_columns(getattr(getattr(part, "table_layout", None), "columns", []))
    if str(part.source_type or "") == "summary":
        rows = [{"title": str(row.title or ""), "content": "待补充"} for row in list((part.summary_spec.rows if part.summary_spec else []) or [])]
    else:
        result = datasets.get(str(part.dataset_id or "")) or DatasetExecutionResult(dataset_id=str(part.dataset_id or ""))
        columns = _merge_table_columns(getattr(getattr(part, "table_layout", None), "columns", []), result)
        rows = copy.deepcopy(result.rows)
    definitions = list(getattr(getattr(part, "table_layout", None), "merge_rows", []) or [])
    return TableComponent(
        id=str(part.id or ""),
        type="table",
        data_properties=TableDataProperties(
            data_type="static",
            source_id=str(part.dataset_id or ""),
            title=str(part.title or ""),
            columns=columns,
            merge_columns=list(getattr(getattr(part, "table_layout", None), "merge_columns", []) or []),
            merge_rows=_build_merge_rows(data=rows, columns=columns, definitions=definitions),
            data=rows,
        ),
    )


def _table_columns(columns) -> list[ReportColumn]:
    return [ReportColumn(key=str(item.key or ""), title=str(item.title or ""), width=getattr(item, "width", None), align=getattr(item, "align", None)) for item in list(columns or [])]


def _merge_table_columns(columns, result: DatasetExecutionResult) -> list[ReportColumn]:
    configured = _table_columns(columns)
    resolved = _result_columns(result)
    if not configured:
        return resolved
    resolved_by_key = {column.key: column for column in resolved}
    return [
        ReportColumn(
            key=column.key,
            title=(resolved_by_key.get(column.key) or column).title,
            type=(resolved_by_key.get(column.key) or column).type,
            width=column.width,
            sortable=column.sortable,
            filterable=column.filterable,
            align=column.align,
            lineage_tracing=copy.deepcopy((resolved_by_key.get(column.key) or column).lineage_tracing),
            children=copy.deepcopy(column.children),
        )
        for column in configured
    ]


def _result_columns(result: DatasetExecutionResult) -> list[ReportColumn]:
    columns = list(result.columns or [])
    if not columns and result.rows:
        columns = [{"key": key, "title": key} for key in result.rows[0]]
    return [_result_column(item) for item in columns]


def _result_column(item: dict[str, Any]) -> ReportColumn:
    key = str(item.get("key") or item.get("name") or "")
    lineage = item.get("lineageTracing") if isinstance(item.get("lineageTracing"), dict) else None
    sources = list(lineage.get("sources") or []) if lineage else []
    first_source = sources[0] if sources and isinstance(sources[0], dict) else {}
    title = str(first_source.get("businessName_cn") or first_source.get("businessName") or key)
    return ReportColumn(
        key=key,
        title=title,
        type=_normalize_column_type(item.get("type")),
        lineage_tracing=_report_lineage_tracing(lineage),
    )


def _report_lineage_tracing(lineage: dict[str, Any] | None) -> dict[str, Any] | None:
    if not lineage:
        return None
    sources = []
    for item in list(lineage.get("sources") or []):
        if not isinstance(item, dict):
            continue
        sources.append(
            {
                key: copy.deepcopy(item[key])
                for key in ("dataSourceName", "field", "businessName", "businessName_cn", "enumValues", "ui")
                if key in item
            }
        )
    return {"sources": sources} if sources else None


def _normalize_column_type(value: Any) -> str | None:
    normalized = str(value or "").strip()
    aliases = {
        "number": "double",
        "integer": "int",
        "datetime": "timestamp",
        "bool": "boolean",
    }
    return aliases.get(normalized, normalized or None)


def _chart_series(series_type: str, columns: list[ReportColumn]) -> list[dict[str, Any]]:
    keys = [column.key for column in columns if column.key]
    if len(keys) < 2:
        return []
    category, metrics = keys[0], keys[1:]
    if series_type == "pie":
        return [{"type": "pie", "encode": {"name": category, "value": metrics[0]}, "name": metrics[0]}]
    if series_type not in {"line", "bar", "scatter"}:
        series_type = "line"
    return [{"type": series_type, "encode": {"x": category, "y": metric}, "name": metric} for metric in metrics]


def _dataset_value(datasets, dataset_id: str, field: str) -> str:
    rows = list((datasets.get(dataset_id) or DatasetExecutionResult(dataset_id=dataset_id)).rows or [])
    return str(rows[0].get(field, "")) if rows else ""


def _build_merge_rows(*, data, columns, definitions) -> list[MergeRowInfo]:
    if not data or not definitions:
        return []
    keys = {column.key for column in columns if column.key}
    result: list[MergeRowInfo] = []
    for definition in definitions:
        column = str(getattr(definition, "column", "") or "")
        if column not in keys:
            continue
        start = 0
        while start < len(data):
            value = data[start].get(column)
            end = start + 1
            while end < len(data) and data[end].get(column) == value:
                end += 1
            if end - start > 1:
                result.append(MergeRowInfo(start_row_index=start, row_span=end - start, column=column, merged_text="" if value is None else str(value)))
            start = end
    return result


def _build_report_name(*, template, template_instance) -> str:
    values = [str(parameter.values[0].label or parameter.values[0].value or "") for parameter in template_instance.parameters if parameter.values][:2]
    return f"{' '.join([value for value in values if value])} {template.name}".strip() if values else template.name


def _build_report_summary(catalogs) -> str:
    titles = _collect_section_titles(catalogs)
    return f"报告已生成，共包含 {len(titles)} 个章节：{'、'.join(titles[:5])}" if titles else "报告已生成。"


def _collect_section_titles(catalogs) -> list[str]:
    titles: list[str] = []
    for catalog in catalogs:
        titles.extend([str(section.title or "").strip() for section in list(catalog.sections or []) if str(section.title or "").strip()])
        titles.extend(_collect_section_titles(list(catalog.sub_catalogs or [])))
    return titles


def _count_catalogs(catalogs) -> int:
    return sum(1 + _count_catalogs(list(catalog.sub_catalogs or [])) for catalog in catalogs)


def _custom_meta(section) -> ReportGenerateMeta:
    return ReportGenerateMeta(status="Success", question=str(section.outline.rendered_requirement or section.outline.requirement or ""), additional_infos=[])


def _record_custom_catalog_meta(catalog, report_meta, *, prompt: str) -> None:
    for section in list(catalog.sections or []):
        report_meta[section.id] = ReportGenerateMeta(status="Success", question=prompt, additional_infos=[])
    for sub_catalog in list(catalog.sub_catalogs or []):
        _record_custom_catalog_meta(sub_catalog, report_meta, prompt=prompt)


def _section_title(section) -> str:
    requirement = str(section.outline.rendered_requirement or section.outline.requirement or "").strip()
    return requirement[:80] if requirement else str(section.id or "")
