import re
import unittest

from htmlsanitize.sanitize import sanitize

VISIBLE_TEXT = re.compile(r"<[^>]+>")


def visible_text(value):
    return VISIBLE_TEXT.sub("", value)


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
        self.assertEqual(
            sanitize('<a onclick="x" href="/y">t</a>'),
            '<a href="/y">t</a>')

    def test_void_tag_without_end(self):
        self.assertEqual(sanitize("a<br>b"), "a<br>b")

    def test_nested_unknown_tags(self):
        self.assertEqual(sanitize("<div><p>x</p></div>"), "<p>x</p>")

    def test_drops_style_content(self):
        self.assertEqual(sanitize("<style>.x{}</style>x"), "x")

    def test_script_nested_inside_unknown_tag(self):
        self.assertEqual(
            sanitize("<div><script>x</script>y</div>"), "y")


class EntityTest(unittest.TestCase):
    def test_text_lt_gt_amp_quote_escaped(self):
        self.assertEqual(
            sanitize("<b>& < > \"</b>"),
            "<b>&amp; &lt; &gt; &#x27;</b>".replace("&#x27;", "&quot;"))

    def test_named_entities_decoded_then_escaped(self):
        self.assertEqual(
            sanitize("&lt;script&gt;alert(1)&lt;/script&gt;"),
            "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_numeric_entity_decoded_then_escaped(self):
        self.assertEqual(sanitize("&#60;b&#62;"), "&lt;b&gt;")

    def test_text_with_real_angle_brackets(self):
        self.assertEqual(sanitize("a < b && b > c"), "a &lt; b &amp;&amp; b &gt; c")

    def test_no_bare_angle_brackets_in_output(self):
        samples = [
            "&lt;script&gt;alert(1)&lt;/script&gt;",
            "<b>x</b>",
            "<a href='/a'>t</a>",
        ]
        for sample in samples:
            output = sanitize(sample)
            text_parts = VISIBLE_TEXT.sub("", output)
            self.assertNotIn("<", text_parts)
            self.assertNotIn(">", text_parts)


class ProtocolTest(unittest.TestCase):
    def test_javascript_href_dropped(self):
        self.assertEqual(
            sanitize('<a href="javascript:alert(1)">x</a>'), "<a>x</a>")

    def test_data_src_dropped(self):
        self.assertEqual(
            sanitize('<img src="data:text/html,x" alt="x">'),
            '<img alt="x">')

    def test_case_insensitive_protocol_blocked(self):
        self.assertEqual(
            sanitize('<a href="JaVaScRiPt:alert(1)">x</a>'), "<a>x</a>")

    def test_whitespace_obfuscation_blocked(self):
        self.assertEqual(
            sanitize('<a href="java\tscript:alert(1)">x</a>'), "<a>x</a>")

    def test_allowed_protocols_kept(self):
        for url in ("http://e.com", "https://e.com", "mailto:a@b.com",
                    "/path", "#anchor"):
            self.assertEqual(
                sanitize('<a href="%s">x</a>' % url),
                '<a href="%s">x</a>' % url)

    def test_title_attr_not_protocol_checked(self):
        self.assertEqual(
            sanitize('<a title="javascript:x">y</a>'),
            '<a title="javascript:x">y</a>')


class AutoCloseTest(unittest.TestCase):
    def test_unclosed_bold_closed(self):
        self.assertEqual(sanitize("<b>x"), "<b>x</b>")

    def test_extra_end_tag_dropped(self):
        self.assertEqual(sanitize("<p>a</p></p>"), "<p>a</p>")

    def test_close_through_nesting(self):
        self.assertEqual(sanitize("<b><i>x</b>y"), "<b><i>x</i></b>y")

    def test_void_tags_never_closed(self):
        self.assertEqual(sanitize("a<br/>b<img src='/x'/>c"),
                         "a<br>b<img src=\"/x\">c")

    def test_implicit_close_li(self):
        self.assertEqual(
            sanitize("<ul><li>a<li>b</ul>"),
            "<ul><li>a</li><li>b</li></ul>")

    def test_implicit_close_p_before_block(self):
        self.assertEqual(
            sanitize("<p>a<p>b"), "<p>a</p><p>b</p>")

    def test_implicit_close_open_anchor(self):
        self.assertEqual(
            sanitize('<a href="/a">x<a href="/b">y</a>'),
            '<a href="/a">x</a><a href="/b">y</a>')


class AttributeFormatTest(unittest.TestCase):
    def test_attributes_double_quoted(self):
        self.assertEqual(
            sanitize("<a href='/x' title='hi'>t</a>"),
            '<a href="/x" title="hi">t</a>')

    def test_quotes_stripped_from_attribute_values(self):
        self.assertEqual(
            sanitize('<a href="/x" title="a&quot;b">t</a>'),
            '<a href="/x" title="ab">t</a>')

    def test_attrs_keep_input_order(self):
        self.assertEqual(
            sanitize('<img title="t" alt="a" src="/x">'),
            '<img title="t" alt="a" src="/x">')


class InvariantTest(unittest.TestCase):
    def test_idempotent(self):
        samples = [
            "<b>x</b>",
            "&lt;script&gt;alert(1)&lt;/script&gt;",
            '<a href="javascript:alert(1)">x</a>',
            "<b><i>x</b>y",
            "<p>a<p>b",
            '<img src="data:text/html,x" alt="x">',
            "<ul><li>a<li>b</ul>",
            "<script>alert(1)</script>ok",
        ]
        for sample in samples:
            once = sanitize(sample)
            self.assertEqual(sanitize(once), once, sample)

    def test_visible_text_preserved(self):
        samples = [
            "a &lt;b&gt; c",
            "<div><p>x</p></div>y",
            "<b><i>nested</i></b> text",
            "<script>gone</script>kept",
            '<a href="javascript:alert(1)">link</a>',
        ]
        for sample in samples:
            source = visible_text(sample).replace("gone", "")
            self.assertEqual(visible_text(sanitize(sample)), source, sample)

    def test_no_executable_tags(self):
        output = sanitize(
            "<script>x</script><style>y</style>"
            "<iframe>z</iframe><object>q</object>")
        self.assertNotIn("<script", output)
        self.assertNotIn("<style", output)
        self.assertNotIn("<iframe", output)
        self.assertNotIn("<object", output)


if __name__ == "__main__":
    unittest.main()
