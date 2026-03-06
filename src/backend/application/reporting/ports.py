from __future__ import annotations

from typing import Any, Dict, List, Protocol

from ...domain.reporting.entities import ReportTemplateEntity, ReportInstanceEntity


class TemplateReader(Protocol):
    def get_by_id(self, template_id: str) -> ReportTemplateEntity | None:
        ...


class InstanceWriter(Protocol):
    def create(
        self,
        *,
        template_id: str,
        template_version: str,
        input_params: Dict[str, Any],
        outline_content: List[Dict[str, Any]],
        status: str = "draft",
    ) -> ReportInstanceEntity:
        ...


class InstanceReader(Protocol):
    def get_input_params(self, instance_id: str) -> Dict[str, Any] | None:
        ...


class ContentGenerator(Protocol):
    def generate(
        self,
        template: ReportTemplateEntity,
        outline: List[Dict[str, Any]],
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        ...
