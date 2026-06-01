"""把已解析的模板实例编译为正式 Report DSL，不访问任何基础设施。"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from .generation_models import (
    ChartComponent,
    ChartDataProperties,
    CompositeTableComponent,
    CompositeTableDataProperties,
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
    ReportSummary,
    TableComponent,
    TableDataProperties,
    TemplateInstance,
    TextComponent,
    TextDataProperties,
)
from .template_models import ReportTemplate


class ReportDslCompiler:
    """将实例树确定性编译为 flow Report DSL。"""

    def compile(
        self,
        *,
        report_id: str,
        template: ReportTemplate,
        template_instance: TemplateInstance,
        custom_catalogs: dict[str, ReportCatalog] | None = None,
        custom_sections: dict[str, ReportSection] | None = None,
    ) -> ReportDsl:
        report_meta: dict[str, ReportGenerateMeta] = {}
        catalogs = [
            self._compile_catalog(
                item,
                report_meta=report_meta,
                custom_catalogs=custom_catalogs or {},
                custom_sections=custom_sections or {},
            )
            for item in template_instance.catalogs
        ]
        today = datetime.now(timezone.utc).date().isoformat()
        return ReportDsl(
            structure_type="flow",
            basic_info=ReportBasicInfo(
                id=report_id,
                schema_version="1.0.0",
                status="Success",
                name=_build_report_name(template=template, template_instance=template_instance),
                report_type="Word",
                description=template.description,
                template_id=template.id,
                template_name=template.name,
                create_date=f"{today}T00:00:00Z",
                modify_date=f"{today}T00:00:00Z",
                creator="report-system",
                modifier="report-system",
                category=template.category,
            ),
            catalogs=catalogs,
            summary=ReportSummary(id="summary_report", overview=_build_report_summary(catalogs)),
            report_meta=report_meta,
            layout=ReportLayout(type="grid", grid=GridDefinition(cols=12, row_height=24)),
        )

    def compile_section(self, section) -> tuple[ReportSection, ReportGenerateMeta]:
        components, summary, additional_infos = _build_section_components(section)
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

    def _compile_catalog(
        self,
        catalog,
        *,
        report_meta: dict[str, ReportGenerateMeta],
        custom_catalogs: dict[str, ReportCatalog],
        custom_sections: dict[str, ReportSection],
    ) -> ReportCatalog:
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
                report_meta[resolved.id] = ReportGenerateMeta(
                    status="Success",
                    question=str(section.outline.rendered_requirement or section.outline.requirement or ""),
                    additional_infos=[],
                )
                continue
            compiled, meta = self.compile_section(section)
            sections.append(compiled)
            report_meta[section.id] = meta
        return ReportCatalog(
            id=catalog.id,
            name=catalog.rendered_title or catalog.title or catalog.id,
            sub_catalogs=[
                self._compile_catalog(
                    item,
                    report_meta=report_meta,
                    custom_catalogs=custom_catalogs,
                    custom_sections=custom_sections,
                )
                for item in list(catalog.sub_catalogs or [])
            ],
            sections=sections,
        )


def build_generation_progress(report: ReportDsl) -> tuple[int, int]:
    return len(_collect_section_titles(list(report.catalogs or []))), _count_catalogs(list(report.catalogs or []))


def find_template_instance_section(catalogs, section_id: str):
    for catalog in list(catalogs or []):
        for section in list(catalog.sections or []):
            if str(section.id or "") == section_id:
                return section
        found = find_template_instance_section(catalog.sub_catalogs, section_id)
        if found is not None:
            return found
    return None


def resource_status_from_dsl(report: ReportDsl) -> str:
    status = str(report.basic_info.status or "").strip()
    if status == "Running":
        return "generating"
    if status == "Failed":
        return "failed"
    return "available"


def _build_section_components(section) -> tuple[list[Any], str, list[ReportAdditionalInfo]]:
    requirement_text = str(section.outline.rendered_requirement or section.outline.requirement or "")
    additional_infos = [
        ReportAdditionalInfo(type="SQL", value=str(binding.resolved_query or "").strip())
        for binding in list(section.runtime_context.bindings or [])
        if str(binding.resolved_query or "").strip()
    ]
    components = [
        MarkdownComponent(
            id=f"component_{section.id}_markdown",
            type="markdown",
            data_properties=MarkdownDataProperties(data_type="static", content=_build_markdown_content(section, requirement_text)),
        )
    ]
    components.extend(_build_presentation_components(section))
    return components, (requirement_text or str(section.id or ""))[:160], additional_infos


def _build_markdown_content(section, requirement_text: str) -> str:
    lines = [f"## {_section_title(section)}".strip(), "", requirement_text or "本章节基于模板诉求自动生成。", ""]
    if section.outline.items:
        lines.extend(["### 诉求要素", ""])
        for item in section.outline.items:
            values = [str(value.label or value.value or "") for value in item.values or []]
            lines.append(f"- {item.label}: {'、'.join([value for value in values if value]) or '未设置'}")
        lines.append("")
    lines.extend(["### 生成说明", "", "当前实现按正式模板实例生成报告 DSL，并保留诉求文本与执行绑定证据。"])
    return "\n".join(lines).strip()


def _build_presentation_components(section) -> list[Any]:
    components: list[Any] = []
    for block in list(section.content.presentation.blocks or []):
        if block.type == "composite_table":
            components.append(_build_composite_table_component(block))
        elif block.type == "text":
            components.append(_build_text_component(block))
        elif block.type == "table":
            components.append(_build_table_component(block))
        elif block.type == "chart":
            components.append(_build_chart_component(block))
    return components


def _build_text_component(block) -> TextComponent:
    return TextComponent(
        id=str(block.id or ""),
        type="text",
        data_properties=TextDataProperties(
            data_type="static",
            content=str(getattr(block, "content", None) or ""),
            title=str(block.title or ""),
        ),
    )


def _build_table_component(block) -> TableComponent:
    columns = _table_columns(getattr(getattr(block, "properties", None), "columns", []))
    data: list[dict[str, Any]] = []
    return TableComponent(
        id=str(block.id or ""),
        type="table",
        data_properties=TableDataProperties(
            data_type="datasource",
            source_id=str(block.dataset_id or ""),
            title=str(block.title or ""),
            columns=columns,
            merge_columns=list(getattr(getattr(block, "properties", None), "merge_columns", []) or []),
            merge_rows=_build_merge_rows(
                data=data,
                columns=columns,
                definitions=list(getattr(getattr(block, "properties", None), "merge_rows", []) or []),
            ),
            data=data,
        ),
    )


def _build_chart_component(block) -> ChartComponent:
    return ChartComponent(
        id=str(block.id or ""),
        type="chart",
        data_properties=ChartDataProperties(data_type="datasource", source_id=str(block.dataset_id or ""), title=str(block.title or "")),
    )


def _build_composite_table_component(block) -> CompositeTableComponent:
    return CompositeTableComponent(
        id=str(block.id or ""),
        type="compositeTable",
        tables=[_build_composite_table_part(part) for part in list(block.parts or [])],
        data_properties=CompositeTableDataProperties(data_type="static", title=str(block.title or "")),
    )


def _build_composite_table_part(part) -> TableComponent:
    columns = _table_columns(getattr(getattr(part, "table_layout", None), "columns", []))
    if str(part.source_type or "") == "summary":
        rows = [{"title": str(row.title or ""), "content": "待补充"} for row in list((part.summary_spec.rows if part.summary_spec else []) or [])]
        return TableComponent(
            id=str(part.id or ""),
            type="table",
            data_properties=TableDataProperties(
                data_type="static",
                title=str(part.title or ""),
                columns=columns,
                merge_rows=_build_merge_rows(
                    data=rows,
                    columns=columns,
                    definitions=list(getattr(getattr(part, "table_layout", None), "merge_rows", []) or []),
                ),
                data=rows,
            ),
        )
    data: list[dict[str, Any]] = []
    return TableComponent(
        id=str(part.id or ""),
        type="table",
        data_properties=TableDataProperties(
            data_type="datasource",
            source_id=str(part.dataset_id or ""),
            title=str(part.title or ""),
            columns=columns,
            merge_columns=list(getattr(getattr(part, "table_layout", None), "merge_columns", []) or []),
            merge_rows=_build_merge_rows(
                data=data,
                columns=columns,
                definitions=list(getattr(getattr(part, "table_layout", None), "merge_rows", []) or []),
            ),
            data=data,
        ),
    )


def _table_columns(columns) -> list[ReportColumn]:
    return [
        ReportColumn(key=str(item.key or ""), title=str(item.title or ""), width=getattr(item, "width", None), align=getattr(item, "align", None))
        for item in list(columns or [])
    ]


def _build_merge_rows(*, data: list[dict[str, Any]], columns: list[ReportColumn], definitions) -> list[MergeRowInfo]:
    if not data or not definitions:
        return []
    keys = {str(column.key or "") for column in columns if str(column.key or "")}
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


def _build_report_name(*, template: ReportTemplate, template_instance: TemplateInstance) -> str:
    values = [str(parameter.values[0].label or parameter.values[0].value or "") for parameter in template_instance.parameters if parameter.values][:2]
    return f"{' '.join([value for value in values if value])} {template.name}".strip() if values else template.name


def _build_report_summary(catalogs: list[ReportCatalog]) -> str:
    titles = _collect_section_titles(catalogs)
    return f"报告已生成，共包含 {len(titles)} 个章节：{'、'.join(titles[:5])}" if titles else "报告已生成。"


def _collect_section_titles(catalogs: list[ReportCatalog]) -> list[str]:
    titles: list[str] = []
    for catalog in catalogs:
        titles.extend([str(section.title or "").strip() for section in list(catalog.sections or []) if str(section.title or "").strip()])
        titles.extend(_collect_section_titles(list(catalog.sub_catalogs or [])))
    return titles


def _count_catalogs(catalogs: list[ReportCatalog]) -> int:
    return sum(1 + _count_catalogs(list(catalog.sub_catalogs or [])) for catalog in catalogs)


def _record_custom_catalog_meta(catalog: ReportCatalog, report_meta: dict[str, ReportGenerateMeta], *, prompt: str) -> None:
    for section in list(catalog.sections or []):
        report_meta[section.id] = ReportGenerateMeta(status="Success", question=prompt, additional_infos=[])
    for sub_catalog in list(catalog.sub_catalogs or []):
        _record_custom_catalog_meta(sub_catalog, report_meta, prompt=prompt)


def _section_title(section) -> str:
    requirement = str(section.outline.rendered_requirement or section.outline.requirement or "").strip()
    return requirement[:80] if requirement else str(section.id or "")
