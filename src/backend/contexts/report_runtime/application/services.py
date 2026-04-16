from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from ..domain.models import ReportInstance, TemplateInstance
from ....shared.kernel.errors import NotFoundError, ValidationError


class ReportRuntimeService:
    def __init__(
        self,
        *,
        instance_creator,
        instance_repository,
        template_instance_repository,
        template_repository,
        legacy_runtime,
    ) -> None:
        self.instance_creator = instance_creator
        self.instance_repository = instance_repository
        self.template_instance_repository = template_instance_repository
        self.template_repository = template_repository
        self.legacy_runtime = legacy_runtime

    def create_instance(self, *, template_id: str, input_params: dict[str, Any], outline_override: Optional[list[Any]] = None, user_id: str = "default", source_session_id: str | None = None, source_message_id: str | None = None) -> dict[str, Any]:
        try:
            return self.instance_creator.create_instance(
                template_id=template_id,
                input_params=input_params or {},
                outline_override=outline_override,
                user_id=user_id,
                source_session_id=source_session_id,
                source_message_id=source_message_id,
            )
        except ValueError as exc:
            if str(exc) == "Template not found":
                raise NotFoundError("Template not found") from exc
            raise ValidationError(str(exc)) from exc

    def get_instance(self, instance_id: str, *, user_id: str = "default") -> dict[str, Any]:
        instance = self._require_instance(instance_id, user_id=user_id)
        template_instance = self.template_instance_repository.get_by_instance(instance_id)
        return self.serialize_instance(instance, template_instance)

    def list_instances(self, *, template_id: str | None = None, user_id: str = "default") -> list[dict[str, Any]]:
        instances = self.instance_repository.list(template_id, user_id=user_id)
        template_instance_map = self.template_instance_repository.list_map_by_instances([item.instance_id for item in instances])
        return [self.serialize_instance(item, template_instance_map.get(item.instance_id)) for item in instances]

    def update_instance(self, instance_id: str, updates: dict[str, Any], *, user_id: str = "default") -> dict[str, Any]:
        try:
            instance = self.instance_repository.update_fields(instance_id, updates, user_id=user_id)
        except LookupError as exc:
            raise NotFoundError("Instance not found") from exc
        template_instance = self.template_instance_repository.get_by_instance(instance_id)
        return self.serialize_instance(instance, template_instance)

    def delete_instance(self, instance_id: str, *, user_id: str = "default") -> dict[str, Any]:
        try:
            self.template_instance_repository.delete_by_instance(instance_id)
            self.instance_repository.delete(instance_id, user_id=user_id)
        except LookupError as exc:
            raise NotFoundError("Instance not found") from exc
        return {"message": "deleted"}

    def finalize_instance(self, instance_id: str, *, user_id: str = "default") -> dict[str, Any]:
        try:
            self.instance_repository.update_fields(instance_id, {"status": "finalized"}, user_id=user_id)
        except LookupError as exc:
            raise NotFoundError("Instance not found") from exc
        return {"message": "finalized", "instance_id": instance_id}

    def get_generation_baseline(self, instance_id: str, *, user_id: str = "default") -> dict[str, Any]:
        self._require_instance(instance_id, user_id=user_id)
        template_instance = self.template_instance_repository.get_by_instance(instance_id)
        if not template_instance:
            raise NotFoundError("Template instance not found")
        return build_generation_baseline_payload(template_instance)

    def regenerate_section(self, instance_id: str, section_index: int, *, user_id: str = "default") -> dict[str, Any]:
        instance = self._require_instance(instance_id, user_id=user_id)
        content = list(instance.outline_content or [])
        if section_index < 0 or section_index >= len(content):
            raise ValidationError("Invalid section index")

        current = content[section_index]
        template_entity = self.template_repository.get_template_entity(instance.template_id)
        template_record = self.template_repository.get_runtime_template(instance.template_id)
        regenerated = self.legacy_runtime.regenerate_section(
            template_entity=template_entity,
            template_record=template_record,
            current_section=current,
            input_params=instance.input_params or {},
            existing_sections=content,
            section_index=section_index,
        )
        updated = self.instance_repository.replace_outline_section(
            instance_id,
            section_index,
            {**current, **regenerated, "regenerated": True},
            user_id=user_id,
        )
        self.template_instance_repository.save_runtime_updates(
            report_instance_id=instance_id,
            outline_snapshot=updated.outline_content or [],
            generated_sections=updated.outline_content or [],
            status="completed",
        )
        template_instance = self.template_instance_repository.get_by_instance(instance_id)
        return self.serialize_instance(updated, template_instance)

    @staticmethod
    def serialize_instance(instance: ReportInstance, template_instance: TemplateInstance | None) -> dict[str, Any]:
        has_generation_baseline = template_instance is not None
        supports_fork_chat = bool(has_generation_baseline and getattr(template_instance, "session_id", ""))
        return {
            "instance_id": instance.instance_id,
            "template_id": instance.template_id,
            "status": instance.status,
            "user_id": instance.user_id,
            "source_session_id": instance.source_session_id,
            "source_message_id": instance.source_message_id,
            "input_params": deepcopy(instance.input_params or {}),
            "outline_content": deepcopy(instance.outline_content or []),
            "report_time": str(instance.report_time) if instance.report_time else None,
            "report_time_source": instance.report_time_source or "",
            "created_at": str(instance.created_at),
            "updated_at": str(instance.updated_at),
            "has_generation_baseline": has_generation_baseline,
            "supports_update_chat": has_generation_baseline,
            "supports_fork_chat": supports_fork_chat,
        }

    def _require_instance(self, instance_id: str, *, user_id: str = "default") -> ReportInstance:
        instance = self.instance_repository.get(instance_id, user_id=user_id)
        if not instance:
            raise NotFoundError("Instance not found")
        return instance


class ReportDocumentService:
    def __init__(self, *, document_gateway) -> None:
        self.document_gateway = document_gateway

    def create_document(self, *, instance_id: str, format_name: str) -> dict[str, Any]:
        return self.document_gateway.create(instance_id=instance_id, format_name=format_name)

    def list_documents(self, *, instance_id: str | None = None) -> list[dict[str, Any]]:
        return self.document_gateway.list(instance_id=instance_id)

    def get_document(self, *, document_id: str) -> dict[str, Any]:
        document = self.document_gateway.get(document_id)
        if not document:
            raise NotFoundError("Document not found")
        return document

    def resolve_download(self, *, document_id: str) -> tuple[dict[str, Any], str]:
        document, absolute_path = self.document_gateway.resolve_download(document_id)
        if not document:
            raise NotFoundError("Document not found")
        if not absolute_path:
            raise ValidationError("Document file not found")
        return document, absolute_path

    def delete_document(self, *, document_id: str) -> dict[str, Any]:
        deleted = self.document_gateway.delete(document_id)
        if not deleted:
            raise NotFoundError("Document not found")
        return {"message": "deleted"}


def build_generation_baseline_payload(record: TemplateInstance) -> Dict[str, Any]:
    template_instance_payload = {
        "instance_template_id": record.template_instance_id,
        "schema_version": record.schema_version or "ti.v1.0",
        "base_template": {
            "id": record.template_id,
            "name": record.template_name or record.template_id,
            "category": (record.base_template.template_type if record.base_template else ""),
            "description": (record.base_template.description if record.base_template else ""),
            "parameters": deepcopy(record.base_template.parameters if record.base_template else []),
            "sections": deepcopy(record.base_template.sections if record.base_template else []),
        },
        "instance_meta": {
            "status": record.status,
            "revision": record.revision,
            "created_at": str(record.created_at) if record.created_at else None,
        },
        "runtime_state": deepcopy(record.runtime_state or {}),
        "resolved_view": deepcopy(record.resolved_view or {}),
        "generated_content": deepcopy(record.generated_content or {}),
        "fragments": deepcopy(record.fragments or {}),
    }
    return {
        "instance_id": record.report_instance_id,
        "template_id": record.template_id,
        "template_name": record.template_name or record.template_id,
        "params_snapshot": deepcopy(record.input_params_snapshot or {}),
        "outline": deepcopy(record.outline_snapshot or []),
        "warnings": list(record.warnings or []),
        "created_at": str(record.created_at),
        "template_instance": template_instance_payload,
    }
