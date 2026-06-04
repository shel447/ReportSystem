"""Projection from report answers to chat stream deltas."""

from __future__ import annotations


class ReportFlowProjection:
    def delta_events(self, answer: dict[str, object]) -> list[dict[str, object]]:
        answer_type = str(answer.get("answerType") or "")
        if answer_type == "REPORT_SEGMENT":
            return [_report_segment_delta_event(answer)]
        if answer_type != "REPORT":
            return []
        report_answer = answer.get("answer") if isinstance(answer.get("answer"), dict) else {}
        report = report_answer.get("report") if isinstance(report_answer.get("report"), dict) else {}
        report_id = str(report_answer.get("reportId") or "")
        basic_info = report.get("basicInfo") if isinstance(report.get("basicInfo"), dict) else {}
        report_title = str(basic_info.get("name") or report_id)
        structure_type = str(report.get("structureType") or "flow")
        deltas: list[dict[str, object]] = [
            {"action": "init_report", "report": {"reportId": report_id, "title": report_title, "structureType": structure_type}},
        ]
        deltas.extend(_catalog_delta_events(list(report.get("catalogs") or []), parent_catalog_id=None, parent_catalog_path=None))
        return deltas


def _report_segment_delta_event(answer: dict[str, object]) -> dict[str, object]:
    segment = answer.get("answer") if isinstance(answer.get("answer"), dict) else {}
    section = segment.get("section") if isinstance(segment.get("section"), dict) else {}
    outline = segment.get("outline") if isinstance(segment.get("outline"), dict) else {}
    return {
        "action": "add_section",
        "structureType": "flow",
        "parent": {"type": "section", "id": str(segment.get("sectionId") or section.get("id") or ""), "path": []},
        "sections": [
            {
                "sectionId": str(segment.get("sectionId") or section.get("id") or ""),
                "status": str(segment.get("status") or "available"),
                "requirement": str(outline.get("renderedRequirement") or outline.get("requirement") or ""),
                "components": list(section.get("components") or []),
            }
        ],
    }


def _catalog_delta_events(
    catalogs: list[dict[str, object]],
    *,
    parent_catalog_id: str | None,
    parent_catalog_path: list[int] | None,
) -> list[dict[str, object]]:
    deltas: list[dict[str, object]] = []
    if catalogs:
        deltas.append(
            {
                "action": "add_catalog",
                "structureType": "flow",
                "parentCatalogId": parent_catalog_id,
                "parentCatalog": parent_catalog_path,
                "parent": {
                    "type": "report" if parent_catalog_id is None else "catalog",
                    "id": parent_catalog_id,
                    "path": parent_catalog_path,
                },
                "catalogs": [
                    {
                        "catalogId": str(catalog.get("id") or ""),
                        "title": str(catalog.get("name") or catalog.get("title") or catalog.get("id") or ""),
                    }
                    for catalog in catalogs
                ],
            }
        )
    for index, catalog in enumerate(catalogs):
        catalog_path = [*parent_catalog_path, index] if parent_catalog_path is not None else [index]
        sections = list(catalog.get("sections") or [])
        if sections:
            deltas.append(
                {
                    "action": "add_section",
                    "structureType": "flow",
                    "parentCatalogId": str(catalog.get("id") or ""),
                    "parentCatalog": catalog_path,
                    "parent": {"type": "catalog", "id": str(catalog.get("id") or ""), "path": catalog_path},
                    "sections": [
                        {
                            "sectionId": str(section.get("id") or ""),
                            "status": "finished",
                            "requirement": str(section.get("title") or section.get("requirement") or section.get("id") or ""),
                            "components": list(section.get("components") or []),
                        }
                        for section in sections
                    ],
                }
            )
        deltas.extend(
            _catalog_delta_events(
                list(catalog.get("subCatalogs") or []),
                parent_catalog_id=str(catalog.get("id") or ""),
                parent_catalog_path=catalog_path,
            )
        )
    return deltas
