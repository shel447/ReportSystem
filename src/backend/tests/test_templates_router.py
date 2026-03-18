import unittest

from backend.routers.templates import _clean_template_payload


class TemplatesRouterTests(unittest.TestCase):
    def test_clean_template_payload_validates_and_normalizes_v2_template(self):
        payload = {
            "name": "设备健康报告",
            "type": "设备健康评估",
            "scene": "总部",
            "parameters": [],
            "sections": [
                {
                    "title": "概述",
                    "content": {
                        "source": {"kind": "sql", "query": "SELECT 1 AS value"},
                        "presentation": {"type": "value", "anchor": "{$value}"},
                    },
                }
            ],
        }

        cleaned = _clean_template_payload(payload)

        self.assertEqual(cleaned["schema_version"], "v2.0")
        self.assertEqual(cleaned["template_type"], "设备健康评估")
        self.assertEqual(cleaned["sections"][0]["content"]["datasets"][0]["id"], "ds_main")


if __name__ == "__main__":
    unittest.main()
