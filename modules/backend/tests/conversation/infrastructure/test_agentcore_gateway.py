import unittest
import json

from src.contexts.conversation.infrastructure.agentcore import ExternalConversationHistoryGateway
from src.contexts.conversation.application.ports import HostedAnswer, HostedChat
from src.shared.kernel.errors import ErrorCode, UpstreamError


class _QuotaExceededClient:
    def post_json(self, **_kwargs):
        raise UpstreamError(
            "upstream quota exceeded",
            details={"upstreamCode": "naie.aiagent.452", "upstreamMessage": "quota exceeded"},
            http_status=409,
        )


class AgentCoreGatewayErrorTests(unittest.TestCase):
    def test_agentcore_quota_error_is_mapped_to_chatbi_code(self):
        gateway = ExternalConversationHistoryGateway(client=_QuotaExceededClient())

        with self.assertRaises(UpstreamError) as ctx:
            gateway.create_conversation(title="新会话", description=None, user_id="u_001")

        self.assertEqual(ctx.exception.error_code, ErrorCode.CONVERSATION_QUOTA_EXCEEDED)
        self.assertEqual(ctx.exception.http_status, 409)
        self.assertEqual(ctx.exception.source, "agentcore")
        self.assertEqual(ctx.exception.details["upstreamCode"], "naie.aiagent.452")
        self.assertNotIn("naie", ctx.exception.error_code)


class _RecordingClient:
    def __init__(self, *, history_payload=None):
        self.requests = []
        self.history_payload = history_payload or {"records": []}

    def post_json(self, *, path_or_url, payload=None, user_id=None, **_kwargs):
        self.requests.append({"method": "POST", "path": path_or_url, "payload": payload, "user_id": user_id})
        if path_or_url.endswith("/chat/history"):
            return self.history_payload
        return {"status": "ok"}


class AgentCoreGatewayStandardRecordTests(unittest.TestCase):
    def test_import_chat_writes_standard_record_answers(self):
        client = _RecordingClient()
        gateway = ExternalConversationHistoryGateway(client=client, piu_name="ReportGenerationPIU")
        piu_content = json.dumps(
            {
                "piuName": "ReportGenerationPIU",
                "answers": {"steps": [], "ask": None, "delta": [], "answer": {"answerType": "REPORT", "answer": {"reportId": "rpt_001"}}, "errors": []},
            },
            ensure_ascii=False,
        )

        gateway.import_chat(
            chat=HostedChat(
                chat_id="chat_001",
                conversation_id="conv_001",
                question="生成总部网络运行日报",
                created_at=1780368000000,
                answers=[
                    HostedAnswer(type="TEXT", content="已收到请求，正在分析报告诉求。", answer_time=1780368000100),
                    HostedAnswer(type="PIU", content=piu_content, answer_time=1780368000300),
                ],
            ),
            user_id="u_001",
        )

        payload = client.requests[0]["payload"]
        self.assertEqual(payload["conversationId"], "conv_001")
        self.assertEqual(payload["chatId"], "chat_001")
        self.assertEqual(payload["question"], "生成总部网络运行日报")
        self.assertNotIn("content", payload)
        self.assertEqual(payload["answers"][0]["type"], "TEXT")
        self.assertEqual(json.loads(payload["answers"][1]["content"])["answers"]["answer"]["answerType"], "REPORT")

    def test_query_chat_history_decodes_standard_record_answers(self):
        piu_content = json.dumps(
            {
                "piuName": "ReportGenerationPIU",
                "answers": {
                    "steps": [{"stepId": "step_root", "title": "生成总部网络运行日报", "status": "running"}],
                    "ask": None,
                    "delta": [],
                    "answer": {"answerType": "REPORT", "answer": {"reportId": "rpt_001"}},
                    "errors": [],
                },
            },
            ensure_ascii=False,
        )
        client = _RecordingClient(
            history_payload={
                "records": [
                    {
                        "conversationId": "conv_001",
                        "chatId": "chat_001",
                        "question": "生成总部网络运行日报",
                        "askTime": 1780368000000,
                        "answers": [
                            {"type": "TEXT", "content": "已收到请求，正在分析报告诉求。", "answerTime": 1780368000100},
                            {"type": "PIU", "content": piu_content, "answerTime": 1780368000300},
                        ],
                    }
                ]
            }
        )
        gateway = ExternalConversationHistoryGateway(client=client)

        records = gateway.query_chat_history(conversation_id="conv_001", page_num=1, page_size=20, user_id="u_001")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].question, "生成总部网络运行日报")
        self.assertEqual(records[0].answers[0].type, "TEXT")
        self.assertEqual(records[0].answers[1].type, "PIU")
        self.assertEqual(records[0].response_payload["answer"]["answer"]["reportId"], "rpt_001")
        self.assertEqual(records[0].response_payload["steps"][0]["stepId"], "step_root")


if __name__ == "__main__":
    unittest.main()
