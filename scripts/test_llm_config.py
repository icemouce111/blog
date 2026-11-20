import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import github_daily
from scripts.llm_config import DEEPSEEK_BASE_URL, llm_settings


SPEC = importlib.util.spec_from_file_location(
    "ai_daily_llm_test", Path(__file__).with_name("generate-ai-daily.py")
)
AI_DAILY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AI_DAILY)


class ModelSelectionTest(unittest.TestCase):
    def test_deepseek_wins_over_openai_with_current_default(self):
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "synthetic-deepseek-credential",
            "OPENAI_API_KEY": "synthetic-openai-credential",
        }, clear=True):
            self.assertEqual(llm_settings(), (
                "synthetic-deepseek-credential", DEEPSEEK_BASE_URL, "deepseek-flash"
            ))

    def test_both_generators_share_model_override_and_empty_default(self):
        for value, expected in [(" deepseek-v4-pro ", "deepseek-v4-pro"), ("", "deepseek-flash")]:
            with self.subTest(value=value), patch.dict(os.environ, {
                "DEEPSEEK_API_KEY": "synthetic-deepseek-credential",
                "DEEPSEEK_MODEL": value,
            }, clear=True):
                self.assertEqual(llm_settings()[2], expected)
                self.assertEqual(github_daily._llm_settings()[2], expected)

    def test_compatible_provider_remains_opt_in(self):
        with patch.dict(os.environ, {
            "DESIRECORE_CLOUD_API_KEY": "synthetic-compatible-credential",
            "DESIRECORE_BASE_URL": "https://provider.example/v1/",
            "DESIRECORE_MODEL": "custom-model",
            "DEEPSEEK_API_KEY": "synthetic-deepseek-credential",
        }, clear=True):
            self.assertEqual(llm_settings()[1], DEEPSEEK_BASE_URL)
            self.assertEqual(github_daily._llm_settings(), (
                "synthetic-compatible-credential", "https://provider.example/v1", "custom-model"
            ))

    def test_openai_fallback_and_missing_key_are_preserved(self):
        for env, expected in [({}, None), ({"OPENAI_API_KEY": "synthetic-openai-credential"}, "synthetic-openai-credential")]:
            with self.subTest(configured=bool(env)), patch.dict(os.environ, env, clear=True):
                self.assertEqual(llm_settings(), (expected, "https://api.openai.com/v1", "gpt-4o"))


class CompletionCompatibilityTest(unittest.TestCase):
    def assert_request_options(self, request, deepseek):
        payload = json.loads(request.data)
        if deepseek:
            self.assertEqual(payload["thinking"], {"type": "disabled"})
        else:
            self.assertNotIn("thinking", payload)

    def mock_response(self, mocked_open):
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "choices": [{"message": {"content": "synthetic reply"}}]
        }).encode()

    def test_editor_repair_and_trends_use_provider_specific_options(self):
        for base_url in [DEEPSEEK_BASE_URL, "https://api.openai.com/v1"]:
            for name in ["call_llm", "call_quality_repair", "call_trend_llm"]:
                with self.subTest(provider=base_url, call=name), patch.multiple(
                    AI_DAILY, LLM_API_KEY="synthetic-credential", LLM_BASE_URL=base_url,
                    LLM_MODEL="test-model",
                ), patch.object(AI_DAILY, "urlopen") as mocked_open:
                    self.mock_response(mocked_open)
                    self.assertEqual(getattr(AI_DAILY, name)("synthetic prompt"), "synthetic reply")
                    request = mocked_open.call_args.args[0]
                    self.assertEqual(request.full_url, base_url + "/chat/completions")
                    self.assert_request_options(request, base_url == DEEPSEEK_BASE_URL)

    def test_github_digest_keeps_other_providers_compatible(self):
        for base_url in [DEEPSEEK_BASE_URL, "https://api.openai.com/v1", "https://provider.example/v1"]:
            with self.subTest(provider=base_url), patch.object(github_daily, "urlopen") as mocked_open:
                self.mock_response(mocked_open)
                self.assertEqual(github_daily.call_llm(
                    "synthetic prompt", "synthetic-credential", base_url, "test-model"
                ), "synthetic reply")
                self.assert_request_options(mocked_open.call_args.args[0], base_url == DEEPSEEK_BASE_URL)


if __name__ == "__main__":
    unittest.main()
