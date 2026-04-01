import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.query_engine import QueryRunResult
from backend.models import ChatSession, ReportTemplate, TemplateInstance
from backend.routers.chat import ChatForkRequest, ChatMessage, fork_session, get_session, list_sessions, send_message


class ChatRouterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.template = ReportTemplate(
            template_id="tpl-1",
            name="设备巡检报告",
            template_type="设备健康评估",
            scene="总部",
            parameters=[
                {"id": "scene", "label": "场景", "required": True, "input_type": "enum", "options": ["总部"]},
                {
                    "id": "devices",
                    "label": "设备编号",
                    "required": True,
                    "input_type": "dynamic",
                    "multi": True,
                    "source": "api:/devices/list",
                },
            ],
            sections=[
                {
                    "title": "{scene}概述",
                    "description": "巡检范围",
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                },
                {
                    "title": "设备 {$device}",
                    "description": "检查项",
                    "foreach": {"param": "devices", "as": "device"},
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                },
            ],
            schema_version="v2.0",
        )
        self.db.add(self.template)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_send_message_returns_review_params_before_generation(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001", "A002"]},
             ):
            response = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        self.assertEqual(response["action"]["type"], "review_params")
        self.assertEqual(response["reply"], "参数已收集完成，请确认后生成大纲。")
        self.assertEqual(response["action"]["params"][0]["id"], "scene")

    def test_send_message_confirms_then_generates_document(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
            ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="prepare_outline_review"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "review_outline")
        self.assertEqual(second["action"]["outline"][0]["title"], "总部概述")
        self.assertEqual(second["action"]["outline"][1]["title"], "设备 A001")
        self.assertEqual(self.db.query(TemplateInstance).count(), 0)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            saved = send_message(
                ChatMessage(session_id=first["session_id"], command="edit_outline", outline_override=second["action"]["outline"]),
                db=self.db,
            )

        self.assertEqual(saved["action"]["type"], "review_outline")
        self.assertEqual(self.db.query(TemplateInstance).count(), 0)

        fake_app_service = SimpleNamespace(create_instance=lambda **_kwargs: {"instance_id": "inst-1"})
        fake_doc = SimpleNamespace(document_id="doc-1", instance_id="inst-1", template_id="tpl-1", format="md", file_path="x.md", file_size=10, status="ready", version=1, created_at="now")
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.gateways.build_instance_application_service", return_value=fake_app_service), \
             patch("backend.contexts.conversation.infrastructure.gateways.create_markdown_document", return_value=fake_doc), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.serialize_document",
                 return_value={"document_id": "doc-1", "download_url": "/api/documents/doc-1/download"},
             ):
            third = send_message(
                ChatMessage(
                    session_id=first["session_id"],
                    command="confirm_outline_generation",
                    outline_override=[
                        {
                            "node_id": second["action"]["outline"][0]["node_id"],
                            "title": "总部总览",
                            "description": "巡检范围",
                            "level": 1,
                            "children": [],
                        },
                        second["action"]["outline"][1],
                    ],
                ),
                db=self.db,
            )

        self.assertEqual(third["action"]["type"], "download_document")
        self.assertEqual(third["action"]["document"]["document_id"], "doc-1")
        confirmed_record = self.db.query(TemplateInstance).filter(TemplateInstance.report_instance_id == "inst-1").first()
        self.assertIsNotNone(confirmed_record)
        self.assertEqual(confirmed_record.report_instance_id, "inst-1")
        self.assertEqual(confirmed_record.capture_stage, "generation_baseline")
        self.assertEqual(len(self.db.query(TemplateInstance).all()), 1)

    def test_confirm_outline_generation_resolves_outline_blocks_into_execution_baseline(self):
        outline_template = ReportTemplate(
            template_id="tpl-outline",
            name="蓝图设备巡检报告",
            template_type="设备健康评估",
            scene="总部",
            parameters=[
                {"id": "scene", "label": "场景", "required": True, "input_type": "enum", "options": ["总部"]},
            ],
            sections=[
                {
                    "title": "分析章节",
                    "description": "查看章节内容",
                    "outline": {
                        "document": "分析 {@target_scene} 的巡检情况",
                        "blocks": [
                            {
                                "id": "target_scene",
                                "type": "param_ref",
                                "hint": "分析范围",
                                "param_id": "scene",
                            }
                        ],
                    },
                    "content": {
                        "datasets": [
                            {
                                "id": "ds_main",
                                "source": {
                                    "kind": "sql",
                                    "query": "SELECT '{@target_scene}' AS scene_name",
                                    "description": "统计 {@target_scene} 设备状态",
                                },
                            }
                        ],
                        "presentation": {"type": "text", "template": "结论：{@target_scene}"},
                    },
                }
            ],
            schema_version="v2.0",
        )
        self.db.add(outline_template)
        self.db.commit()

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-outline", "score": 0.96},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作蓝图设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="prepare_outline_review"),
                db=self.db,
            )

        captured: dict[str, object] = {}

        class FakeAppService:
            def create_instance(self, **kwargs):
                captured["kwargs"] = kwargs
                return {"instance_id": "inst-outline"}

        fake_doc = SimpleNamespace(
            document_id="doc-outline",
            instance_id="inst-outline",
            template_id="tpl-outline",
            format="md",
            file_path="outline.md",
            file_size=10,
            status="ready",
            version=1,
            created_at="now",
        )
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.gateways.build_instance_application_service", return_value=FakeAppService()), \
             patch("backend.contexts.conversation.infrastructure.gateways.create_markdown_document", return_value=fake_doc), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.serialize_document",
                 return_value={"document_id": "doc-outline", "download_url": "/api/documents/doc-outline/download"},
             ):
            edited_outline = second["action"]["outline"]
            edited_outline[0]["outline_instance"]["rendered_document"] = "分析 湿度 的巡检情况"
            edited_outline[0]["outline_instance"]["segments"][1]["value"] = "湿度"
            edited_outline[0]["outline_instance"]["blocks"][0]["value"] = "湿度"
            third = send_message(
                ChatMessage(
                    session_id=first["session_id"],
                    command="confirm_outline_generation",
                    outline_override=edited_outline,
                ),
                db=self.db,
            )

        self.assertEqual(third["action"]["type"], "download_document")
        outline_override = captured["kwargs"]["outline_override"]
        self.assertEqual(outline_override[0]["content"]["presentation"]["template"], "结论：{@target_scene}")
        self.assertEqual(outline_override[0]["resolved_content"]["presentation"]["template"], "结论：湿度")
        self.assertEqual(
            outline_override[0]["resolved_content"]["datasets"][0]["source"]["description"],
            "统计 湿度 设备状态",
        )
        confirmed_record = self.db.query(TemplateInstance).filter(TemplateInstance.report_instance_id == "inst-outline").first()
        self.assertEqual(
            confirmed_record.outline_snapshot[0]["resolved_content"]["presentation"]["template"],
            "结论：湿度",
        )

    def test_send_message_reset_params_restarts_required_collection(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="reset_params"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "ask_param")
        self.assertEqual(second["action"]["param"]["id"], "scene")

    def test_send_message_edit_param_rewinds_following_slots(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="edit_param", target_param_id="devices"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "ask_param")
        self.assertEqual(second["action"]["param"]["id"], "devices")

    def test_send_message_edit_param_from_outline_review_returns_review_params(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001"]},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], command="prepare_outline_review"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "review_outline")

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            third = send_message(
                ChatMessage(session_id=first["session_id"], command="edit_param"),
                db=self.db,
            )

        self.assertEqual(third["action"]["type"], "review_params")

    def test_send_message_with_query_intent_during_report_progress_returns_switch_confirmation(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], message="顺便查一下昨天华东区域告警TOP10"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "confirm_task_switch")
        self.assertEqual(second["action"]["from_capability"], "report_generation")
        self.assertEqual(second["action"]["to_capability"], "smart_query")
        self.assertIn("将结束当前任务", second["reply"])

    def test_send_message_with_natural_query_phrase_during_report_progress_returns_switch_confirmation(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], message="先别做报告了，我想知道昨天华东区域告警最多的三个站点"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "confirm_task_switch")
        self.assertEqual(second["action"]["to_capability"], "smart_query")

    def test_confirm_task_switch_discards_report_progress_and_enters_smart_query(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], message="顺便查一下昨天华东区域告警TOP10"),
                db=self.db,
            )

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.gateways.handle_smart_query_turn", return_value=("这是问数结果。", None, {"stage": "answered"})):
            third = send_message(
                ChatMessage(session_id=first["session_id"], command="confirm_task_switch"),
                db=self.db,
            )

        self.assertEqual(third["reply"], "这是问数结果。")
        self.assertIsNone(third["action"])
        detail = get_session(first["session_id"], db=self.db)
        state_messages = [
            item for item in detail["messages"]
            if (item.get("meta") or {}).get("type") == "context_state"
        ]
        latest = state_messages[-1]["meta"]["state"]
        self.assertEqual(latest["active_task"]["capability"], "smart_query")
        self.assertEqual(latest["active_task"]["stage"], "answered")
        self.assertEqual(latest["report"]["template_id"], "")
        self.assertEqual(latest["slots"], {})

    def test_confirm_task_switch_into_smart_query_uses_structured_result(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], message="先别做报告了，我想知道昨天华东区域告警最多的三个站点"),
                db=self.db,
            )

        fake_query_result = QueryRunResult(
            success=True,
            model="test-query-model",
            compiled_sql="SELECT site_name, alarm_count FROM alarm_top_sites",
            sample_rows=[
                {"site_name": "华东一号站", "alarm_count": 18},
                {"site_name": "华东二号站", "alarm_count": 13},
            ],
            row_count=3,
            debug={
                "strategy": "ibis_planner",
                "query_spec": {
                    "intent": "统计昨日华东区域告警最多站点",
                    "tables": ["fact_alarm_event"],
                    "dimensions": ["site_name"],
                    "measures": ["alarm_count"],
                    "filters": [{"field": "region_name", "op": "=", "value": "华东"}],
                    "warnings": [],
                },
                "schema_candidates": [{"table": "fact_alarm_event", "score": 6}],
                "compiled_sql": "SELECT site_name, alarm_count FROM alarm_top_sites",
                "error_stage": "",
                "error_message": "",
            },
        )

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.chat_capability_service.build_completion_provider_config", return_value=SimpleNamespace(temperature=0.2, model="test-query-model")), \
             patch("backend.chat_capability_service.run_query", return_value=fake_query_result):
            third = send_message(
                ChatMessage(session_id=first["session_id"], command="confirm_task_switch"),
                db=self.db,
            )

        self.assertIn("已完成智能问数", third["reply"])
        self.assertIn("华东一号站", third["reply"])
        self.assertIn("昨日华东区域", third["reply"])
        detail = get_session(first["session_id"], db=self.db)
        latest = [
            item for item in detail["messages"]
            if (item.get("meta") or {}).get("type") == "context_state"
        ][-1]["meta"]["state"]
        self.assertEqual(latest["active_task"]["capability"], "smart_query")
        self.assertEqual(latest["active_task"]["stage"], "answered")
        self.assertIn("query_debug", latest["active_task"]["context_payload"])

    def test_preferred_capability_routes_first_turn_to_fault_diagnosis(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.gateways.handle_fault_diagnosis_turn", return_value=("请补充故障现象。", None, {"stage": "clarifying"})):
            response = send_message(
                ChatMessage(message="站点掉站了", preferred_capability="fault_diagnosis"),
                db=self.db,
            )

        self.assertEqual(response["reply"], "请补充故障现象。")
        self.assertIsNone(response["action"])
        detail = get_session(response["session_id"], db=self.db)
        state_messages = [
            item for item in detail["messages"]
            if (item.get("meta") or {}).get("type") == "context_state"
        ]
        latest = state_messages[-1]["meta"]["state"]
        self.assertEqual(latest["active_task"]["capability"], "fault_diagnosis")
        self.assertEqual(latest["active_task"]["stage"], "clarifying")

    def test_send_message_with_natural_fault_phrase_during_report_progress_returns_switch_confirmation(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], message="先别做报告了，帮我看下 1 号站点昨晚是不是出问题了"),
                db=self.db,
            )

        self.assertEqual(second["action"]["type"], "confirm_task_switch")
        self.assertEqual(second["action"]["to_capability"], "fault_diagnosis")

    def test_confirm_task_switch_discards_report_progress_and_enters_fault_diagnosis(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            first = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            second = send_message(
                ChatMessage(session_id=first["session_id"], message="先别做报告了，帮我看下 1 号站点昨晚是不是出问题了"),
                db=self.db,
            )

        diagnosis_payload = {
            "symptom_summary": "1 号站点昨晚出现退服风险。",
            "judgment": "更像是站点退服或传输中断，需要先核查站点在线状态和传输链路。",
            "possible_causes": ["站点主设备离线", "回传链路中断"],
            "next_steps": ["检查站点在线/退服告警", "核查传输链路与电源状态"],
            "missing_info": [],
            "risk_level": "high",
        }
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.chat_capability_service.build_completion_provider_config", return_value=SimpleNamespace(temperature=0.2, model="diag-model")), \
             patch("backend.ai_gateway.OpenAICompatGateway.chat_completion", return_value={"content": json.dumps(diagnosis_payload, ensure_ascii=False), "model": "diag-model"}):
            third = send_message(
                ChatMessage(session_id=first["session_id"], command="confirm_task_switch"),
                db=self.db,
            )

        self.assertIn("已进入智能故障分析", third["reply"])
        self.assertIn("回传链路中断", third["reply"])
        detail = get_session(first["session_id"], db=self.db)
        latest = [
            item for item in detail["messages"]
            if (item.get("meta") or {}).get("type") == "context_state"
        ][-1]["meta"]["state"]
        self.assertEqual(latest["active_task"]["capability"], "fault_diagnosis")
        self.assertIn("possible_causes", latest["active_task"]["context_payload"])

    def test_send_message_empty_payload_does_not_create_session(self):
        response = send_message(ChatMessage(), db=self.db)

        self.assertEqual(response["session_id"], "")
        self.assertEqual(response["messages"], [])
        self.assertEqual(self.db.query(ChatSession).count(), 0)

    def test_send_message_persists_message_timestamps(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部", "devices": ["A001", "A002"]},
             ):
            response = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        visible_response_messages = [
            item for item in response["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertGreaterEqual(len(visible_response_messages), 2)
        self.assertTrue(all(item.get("created_at") for item in visible_response_messages))

        session_payload = get_session(response["session_id"], db=self.db)
        visible_session_messages = [
            item for item in session_payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertGreaterEqual(len(visible_session_messages), 2)
        self.assertTrue(all(item.get("created_at") for item in visible_session_messages))

    def test_list_sessions_returns_recent_summaries_with_generated_title(self):
        first = ChatSession(
            session_id="s-1",
            messages=[
                {"role": "user", "content": "制作设备巡检报告并输出总部结果"},
                {"role": "assistant", "content": "请补充参数。"},
            ],
            matched_template_id="tpl-1",
            instance_id="inst-1",
        )
        second = ChatSession(
            session_id="s-2",
            messages=[
                {"role": "user", "content": "统计昨日告警"},
                {
                    "role": "assistant",
                    "content": "",
                    "meta": {"type": "context_state", "schema_version": "ctx.v1", "state": {}},
                },
                {"role": "assistant", "content": "已生成结果。"},
            ],
        )
        self.db.add_all([first, second])
        self.db.commit()

        sessions = list_sessions(db=self.db)

        self.assertEqual([item["session_id"] for item in sessions], ["s-2", "s-1"])
        self.assertEqual(sessions[0]["title"], "统计昨日告警")
        self.assertEqual(sessions[0]["message_count"], 2)
        self.assertEqual(sessions[0]["last_message_preview"], "已生成结果。")
        self.assertEqual(sessions[1]["title"], "制作设备巡检报告并输出总部结果")
        self.assertEqual(sessions[1]["matched_template_id"], "tpl-1")
        self.assertEqual(sessions[1]["instance_id"], "inst-1")

    def test_get_session_lazy_backfills_message_ids(self):
        session = ChatSession(
            session_id="s-legacy",
            messages=[
                {"role": "user", "content": "旧用户消息", "created_at": "2026-03-20T10:00:00Z"},
                {
                    "role": "assistant",
                    "content": "旧助手消息",
                    "created_at": "2026-03-20T10:00:01Z",
                },
                {
                    "role": "assistant",
                    "content": "",
                    "meta": {"type": "context_state", "schema_version": "ctx.v1", "state": {"flow": {"stage": "idle"}}},
                },
            ],
        )
        self.db.add(session)
        self.db.commit()

        payload = get_session("s-legacy", db=self.db)

        visible = [
            item for item in payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertEqual(len(visible), 2)
        self.assertTrue(all(item.get("message_id") for item in visible))

        stored = self.db.query(ChatSession).filter(ChatSession.session_id == "s-legacy").first()
        stored_visible = [
            item for item in (stored.messages or [])
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertTrue(all(item.get("message_id") for item in stored_visible))

    def test_fork_from_user_message_returns_draft_and_preserves_anchor_message(self):
        source = ChatSession(
            session_id="source-user",
            messages=[
                {"role": "user", "content": "制作设备巡检报告", "message_id": "msg-user-1", "created_at": "2026-03-20T10:00:00Z"},
                {
                    "role": "assistant",
                    "content": "请补充参数。",
                    "message_id": "msg-assistant-1",
                    "created_at": "2026-03-20T10:00:01Z",
                },
            ],
            matched_template_id="tpl-1",
        )
        self.db.add(source)
        self.db.commit()

        payload = fork_session(
            ChatForkRequest(
                source_kind="session_message",
                source_session_id="source-user",
                source_message_id="msg-user-1",
            ),
            db=self.db,
        )

        self.assertNotEqual(payload["session_id"], "source-user")
        self.assertTrue(payload["title"].startswith("制作设备巡检报告 copy_"))
        self.assertEqual(payload["draft_message"], "制作设备巡检报告")
        visible = [
            item for item in payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertEqual(visible[-1]["role"], "user")
        self.assertEqual(visible[-1]["content"], "制作设备巡检报告")
        self.assertEqual(payload["fork_meta"]["source_kind"], "session_message")
        self.assertEqual(payload["fork_meta"]["source_message_id"], "msg-user-1")

    def test_fork_from_assistant_panel_restores_action_and_context(self):
        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch("backend.contexts.conversation.infrastructure.parameters.get_dynamic_options", return_value=["A001", "A002"]), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-1", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            original = send_message(ChatMessage(message="制作设备巡检报告"), db=self.db)

        assistant_panel = next(
            item for item in original["messages"]
            if item.get("role") == "assistant" and item.get("action", {}).get("type") == "ask_param"
        )

        forked = fork_session(
            ChatForkRequest(
                source_kind="session_message",
                source_session_id=original["session_id"],
                source_message_id=assistant_panel["message_id"],
            ),
            db=self.db,
        )

        self.assertEqual(forked["draft_message"], "")
        visible = [
            item for item in forked["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertEqual(visible[-1]["action"]["type"], "ask_param")
        forked_session = self.db.query(ChatSession).filter(ChatSession.session_id == forked["session_id"]).first()
        self.assertEqual(forked_session.matched_template_id, "tpl-1")
        self.assertEqual(forked_session.fork_meta["source_message_id"], assistant_panel["message_id"])

    def test_fork_from_template_instance_restores_outline_review(self):
        template_instance = TemplateInstance(
            template_instance_id="ti-outline",
            template_id="tpl-1",
            template_name="设备巡检报告",
            template_version="1.0",
            session_id="sess-1",
            capture_stage="outline_saved",
            input_params_snapshot={"scene": "总部", "devices": ["A001"]},
            outline_snapshot=[
                {
                    "node_id": "node-1",
                    "title": "总部概述",
                    "description": "巡检范围",
                    "level": 1,
                    "display_text": "总部概述：巡检范围",
                    "children": [],
                }
            ],
            warnings=["参数缺失已跳过"],
        )
        self.db.add(template_instance)
        self.db.commit()

        payload = fork_session(
            ChatForkRequest(source_kind="template_instance", template_instance_id="ti-outline"),
            db=self.db,
        )

        self.assertEqual(payload["draft_message"], "")
        self.assertEqual(payload["matched_template_id"], "tpl-1")
        visible = [
            item for item in payload["messages"]
            if item.get("role") in {"user", "assistant"} and (item.get("meta") or {}).get("type") != "context_state"
        ]
        self.assertEqual(visible[-1]["action"]["type"], "review_outline")
        self.assertEqual(visible[-1]["action"]["warnings"], ["参数缺失已跳过"])
        self.assertEqual(payload["fork_meta"]["source_kind"], "template_instance")

    def test_fork_from_outline_confirmed_template_instance_conflicts(self):
        template_instance = TemplateInstance(
            template_instance_id="ti-confirmed",
            template_id="tpl-1",
            template_name="设备巡检报告",
            capture_stage="outline_confirmed",
        )
        self.db.add(template_instance)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            fork_session(
                ChatForkRequest(source_kind="template_instance", template_instance_id="ti-confirmed"),
                db=self.db,
            )

        self.assertEqual(ctx.exception.status_code, 409)

    def test_send_message_asks_next_chat_mode_param_with_plain_text_reply(self):
        mixed_template = ReportTemplate(
            template_id="tpl-mixed",
            name="混合追问模板",
            template_type="设备健康评估",
            scene="总部",
            parameters=[
                {
                    "id": "scene",
                    "label": "场景",
                    "required": True,
                    "input_type": "enum",
                    "options": ["总部", "区域"],
                    "interaction_mode": "form",
                },
                {
                    "id": "analysis_goal",
                    "label": "分析目标",
                    "required": True,
                    "input_type": "free_text",
                    "interaction_mode": "chat",
                },
            ],
            sections=[
                {
                    "title": "{scene}概览",
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                }
            ],
            schema_version="v2.0",
        )
        self.db.add(mixed_template)
        self.db.commit()

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-mixed", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={"scene": "总部"},
             ):
            response = send_message(ChatMessage(message="制作混合追问模板"), db=self.db)

        self.assertIsNone(response["action"])
        self.assertEqual(response["reply"], "请提供参数「分析目标」的取值。")

    def test_send_message_uses_chat_mode_answer_as_report_param_instead_of_switching(self):
        mixed_template = ReportTemplate(
            template_id="tpl-mixed-continue",
            name="混合追问继续模板",
            template_type="设备健康评估",
            scene="总部",
            parameters=[
                {
                    "id": "scene",
                    "label": "场景",
                    "required": True,
                    "input_type": "enum",
                    "options": ["总部", "区域"],
                    "interaction_mode": "form",
                },
                {
                    "id": "analysis_goal",
                    "label": "分析目标",
                    "required": True,
                    "input_type": "free_text",
                    "interaction_mode": "chat",
                },
            ],
            sections=[
                {
                    "title": "{scene}概览",
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                }
            ],
            schema_version="v2.0",
        )
        self.db.add(mixed_template)
        self.db.commit()

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-mixed-continue", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 side_effect=[{}, {"analysis_goal": "设备健康趋势"}],
             ):
            first = send_message(ChatMessage(message="制作混合追问继续模板"), db=self.db)
            second = send_message(
                ChatMessage(session_id=first["session_id"], param_id="scene", param_value="总部"),
                db=self.db,
            )
            third = send_message(
                ChatMessage(session_id=first["session_id"], message="设备健康趋势"),
                db=self.db,
            )

        self.assertEqual(first["action"]["type"], "ask_param")
        self.assertIsNone(second["action"])
        self.assertEqual(second["reply"], "请提供参数「分析目标」的取值。")
        self.assertEqual(third["action"]["type"], "review_params")
        self.assertEqual(third["reply"], "参数已收集完成，请确认后生成大纲。")

    def test_send_message_still_confirms_switch_when_chat_mode_pending_and_user_explicitly_switches(self):
        mixed_template = ReportTemplate(
            template_id="tpl-mixed-switch",
            name="混合追问切换模板",
            template_type="设备健康评估",
            scene="总部",
            parameters=[
                {
                    "id": "scene",
                    "label": "场景",
                    "required": True,
                    "input_type": "enum",
                    "options": ["总部", "区域"],
                    "interaction_mode": "form",
                },
                {
                    "id": "analysis_goal",
                    "label": "分析目标",
                    "required": True,
                    "input_type": "free_text",
                    "interaction_mode": "chat",
                },
            ],
            sections=[
                {
                    "title": "{scene}概览",
                    "content": {"presentation": {"type": "text", "template": "ok"}},
                }
            ],
            schema_version="v2.0",
        )
        self.db.add(mixed_template)
        self.db.commit()

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.match_templates",
                 return_value={
                     "auto_match": True,
                     "best": {"template_id": "tpl-mixed-switch", "score": 0.95},
                     "candidates": [],
                 },
             ), \
             patch(
                 "backend.contexts.conversation.infrastructure.gateways.extract_params_from_message",
                 return_value={},
             ):
            first = send_message(ChatMessage(message="制作混合追问切换模板"), db=self.db)
            second = send_message(
                ChatMessage(session_id=first["session_id"], param_id="scene", param_value="总部"),
                db=self.db,
            )

        with patch("backend.contexts.conversation.infrastructure.gateways.get_settings_payload", return_value={"is_ready": True}):
            third = send_message(
                ChatMessage(
                    session_id=first["session_id"],
                    message="先别做报告了，我想知道昨天华东区域告警最多的三个站点",
                ),
                db=self.db,
            )

        self.assertIsNone(second["action"])
        self.assertEqual(second["reply"], "请提供参数「分析目标」的取值。")
        self.assertEqual(third["action"]["type"], "confirm_task_switch")
        self.assertEqual(third["action"]["to_capability"], "smart_query")


if __name__ == "__main__":
    unittest.main()

