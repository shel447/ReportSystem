import unittest

from backend.param_dialog_service import (
    build_missing_required,
    normalize_parameters,
    validate_and_merge_params,
)


class ParamDialogServiceTests(unittest.TestCase):
    def test_normalize_parameters_accepts_id_or_name(self):
        raw = [
            {"id": "date", "label": "日期", "required": True, "input_type": "free_text"},
            {"name": "device", "label": "设备", "required": False, "type": "enum", "options": ["A", "B"]},
        ]
        normalized = normalize_parameters(raw)
        self.assertEqual(normalized[0]["id"], "date")
        self.assertEqual(normalized[1]["id"], "device")
        self.assertEqual(normalized[1]["input_type"], "enum")

    def test_validate_and_merge_params_rejects_invalid_enum(self):
        template_params = [
            {
                "id": "scene",
                "label": "场景",
                "required": True,
                "input_type": "enum",
                "options": ["总部", "分部"],
                "multi": False,
            }
        ]
        merged, warnings = validate_and_merge_params(
            template_params=template_params,
            collected={},
            updates={"scene": "未知"},
        )
        self.assertEqual(merged, {})
        self.assertTrue(warnings)

    def test_build_missing_required(self):
        template_params = [
            {"id": "date", "required": True},
            {"id": "device", "required": False},
        ]
        missing = build_missing_required(template_params, {"device": "A"})
        self.assertEqual(missing, ["date"])

    def test_normalize_parameters_loads_dynamic_options(self):
        raw = [
            {
                "id": "devices",
                "label": "设备",
                "required": True,
                "input_type": "dynamic",
                "source": "api:/devices/list",
            }
        ]
        normalized = normalize_parameters(raw)
        self.assertTrue(normalized[0]["options"])


if __name__ == "__main__":
    unittest.main()
