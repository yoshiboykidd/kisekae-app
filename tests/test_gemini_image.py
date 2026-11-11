"""Offline regression tests: no API key or paid Gemini calls required."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from gemini_image import generate_image, IMAGE_MODEL


def response(*parts, reason=None):
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=list(parts)), finish_reason=reason)],
        prompt_feedback=None,
    )


def image(data=b"fake-image-bytes"):
    return SimpleNamespace(inline_data=SimpleNamespace(data=data))


class ImageGenerationTests(unittest.TestCase):
    def test_extracts_image_from_later_part(self):
        client = Mock()
        client.models.generate_content.return_value = response(
            SimpleNamespace(text="reasoning", inline_data=None), image()
        )
        result = generate_image(client, [], "portrait")
        self.assertEqual(result, b"fake-image-bytes")
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], IMAGE_MODEL)

    def test_missing_image_returns_error_not_exception(self):
        client = Mock()
        client.models.generate_content.return_value = response(
            SimpleNamespace(text="no output", inline_data=None), reason="IMAGE_SAFETY"
        )
        self.assertIn("IMAGE_SAFETY", generate_image(client, [], "portrait"))

    def test_503_retries_twice_then_succeeds(self):
        client = Mock()
        client.models.generate_content.side_effect = [
            RuntimeError("503 UNAVAILABLE"), RuntimeError("503 UNAVAILABLE"), response(image())
        ]
        sleep = Mock()
        self.assertEqual(generate_image(client, [], "test", sleep=sleep), b"fake-image-bytes")
        self.assertEqual(client.models.generate_content.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])

    def test_503_stops_after_three_attempts(self):
        client = Mock()
        client.models.generate_content.side_effect = RuntimeError("503 UNAVAILABLE")
        sleep = Mock()
        self.assertIn("503", generate_image(client, [], "test", sleep=sleep))
        self.assertEqual(client.models.generate_content.call_count, 3)

    def test_404_never_retries(self):
        client = Mock()
        client.models.generate_content.side_effect = RuntimeError("404 NOT_FOUND")
        sleep = Mock()
        self.assertIn("404", generate_image(client, [], "test", sleep=sleep))
        client.models.generate_content.assert_called_once()
        sleep.assert_not_called()

    def test_flatlay_ratio(self):
        client = Mock()
        client.models.generate_content.return_value = response(image())
        generate_image(client, [], "clothing", aspect_ratio="1:1")
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.image_config.aspect_ratio, "1:1")


if __name__ == "__main__":
    unittest.main()
