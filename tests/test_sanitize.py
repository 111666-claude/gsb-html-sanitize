import unittest

from htmlsanitize.sanitize import sanitize


class TagTest(unittest.TestCase):
    def test_keeps_allowed_tags(self):
        self.assertEqual(sanitize("<b>bold</b>"), "<b>bold</b>")

    def test_drops_unknown_tags_but_keeps_text(self):
        self.assertEqual(sanitize("<foo>text</foo>"), "text")

    def test_drops_script_content(self):
        self.assertEqual(sanitize("<script>alert(1)</script>ok"), "ok")

    def test_keeps_allowed_attributes(self):
        self.assertEqual(sanitize('<a href="/x">t</a>'), '<a href="/x">t</a>')

    def test_drops_unknown_attributes(self):
        self.assertEqual(sanitize('<a onclick="x" href="/y">t</a>'), '<a href="/y">t</a>')

    def test_void_tag_without_end(self):
        self.assertEqual(sanitize("a<br>b"), "a<br>b")

    def test_nested_unknown_tags(self):
        self.assertEqual(sanitize("<div><p>x</p></div>"), "<p>x</p>")


class IdempotenceTest(unittest.TestCase):
    def test_sanitize_twice(self):
        once = sanitize("<b>x</b>")
        self.assertEqual(sanitize(once), once)


if __name__ == "__main__":
    unittest.main()
