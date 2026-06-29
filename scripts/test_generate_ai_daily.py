import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("generate-ai-daily.py")
SPEC = importlib.util.spec_from_file_location("generate_ai_daily", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerateFallbackTest(unittest.TestCase):
    def test_fallback_uses_numbered_archive_and_source_subheadings(self):
        output = MODULE._generate_fallback({
            "Hacker News": [{
                "title": "A signal",
                "description": "A description",
                "url": "https://example.com/signal",
            }]
        })

        self.assertTrue(output.startswith("## 01 📡 原始信号归档"))
        self.assertIn("### Hacker News", output)
        self.assertNotIn("## 📊 Hacker News", output)
        self.assertIn("[链接](https://example.com/signal)", output)

    def test_empty_fallback_keeps_the_archive_contract(self):
        output = MODULE._generate_fallback({})

        self.assertTrue(output.startswith("## 01 📡 原始信号归档"))
        self.assertIn("### 系统状态", output)


if __name__ == "__main__":
    unittest.main()
