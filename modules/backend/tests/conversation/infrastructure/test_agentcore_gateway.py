import unittest

from src.contexts.conversation.infrastructure.agentcore import ExternalConversationHistoryGateway
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


if __name__ == "__main__":
    unittest.main()
