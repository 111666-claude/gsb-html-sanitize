import unittest

from htmlsanitize.sanitize import sanitize


def visible_text(html_text):
    """去掉所有标签后的可见文字（script/style 内容不计）。"""
    from html.parser import HTMLParser

    class _Text(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.skip = 0
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip += 1

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self.skip = max(0, self.skip - 1)

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

    parser = _Text()
    parser.feed(html_text)
    parser.close()
    return "".join(parser.parts)


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
            sanitize('<a onclick="x" href="/y">t</a>'), '<a href="/y">t</a>')

    def test_void_tag_without_end(self):
        self.assertEqual(sanitize("a<br>b"), "a<br>b")

    def test_nested_unknown_tags(self):
        self.assertEqual(sanitize("<div><p>x</p></div>"), "<p>x</p>")


class EntityTest(unittest.TestCase):
    def test_escaped_entity_is_not_resurrected(self):
        self.assertEqual(
            sanitize("&lt;script&gt;alert(1)&lt;/script&gt;"),
            "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_literal_special_chars_in_text_are_escaped(self):
        self.assertEqual(sanitize("a & b < c > d \"e\""),
                         "a &amp; b &lt; c &gt; d &quot;e&quot;")

    def test_decoded_entities_render_as_text(self):
        self.assertEqual(sanitize("&#60;&#98;&#62;"), "&lt;b&gt;")

    def test_script_seen_as_text_can_only_stay_text(self):
        once = sanitize("&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotIn("<script", once)
        self.assertEqual(sanitize(once), once)

    def test_attribute_value_quotes_removed_and_entities_escaped(self):
        self.assertEqual(
            sanitize('<a title="a&quot;b&c">x</a>'),
            '<a title="ab&amp;c">x</a>')


class ProtocolTest(unittest.TestCase):
    def test_allows_safe_schemes_and_relative(self):
        self.assertEqual(sanitize('<a href="http://a">x</a>'),
                         '<a href="http://a">x</a>')
        self.assertEqual(sanitize('<a href="https://a/b">x</a>'),
                         '<a href="https://a/b">x</a>')
        self.assertEqual(sanitize('<a href="mailto:a@b.com">x</a>'),
                         '<a href="mailto:a@b.com">x</a>')
        self.assertEqual(sanitize('<a href="/abs/path">x</a>'),
                         '<a href="/abs/path">x</a>')
        self.assertEqual(sanitize('<a href="#frag">x</a>'),
                         '<a href="#frag">x</a>')
        self.assertEqual(sanitize('<img src="https://i/a.png" alt="a">'),
                         '<img src="https://i/a.png" alt="a">')

    def test_drops_javascript_href(self):
        self.assertEqual(sanitize('<a href="javascript:alert(1)">x</a>'),
                         "<a>x</a>")

    def test_drops_data_href(self):
        self.assertEqual(sanitize('<a href="data:text/html,x">x</a>'),
                         "<a>x</a>")

    def test_scheme_check_uses_decoded_value(self):
        # 属性里的实体先解码再查协议，编码绕不过去。
        self.assertEqual(sanitize('<a href="javascript&colon;alert(1)">x</a>'),
                         "<a>x</a>")
        self.assertEqual(sanitize('<a href="&#106;avascript:x">x</a>'),
                         "<a>x</a>")

    def test_scheme_check_strips_leading_whitespace(self):
        self.assertEqual(sanitize('<a href="  javascript:x">x</a>'),
                         "<a>x</a>")
        self.assertEqual(sanitize('<a href=" JaVaScRiPt:x">x</a>'),
                         "<a>x</a>")

    def test_bare_relative_path_without_slash_is_dropped(self):
        self.assertEqual(sanitize('<a href="relative/x">x</a>'), "<a>x</a>")

    def test_img_src_checked_like_href(self):
        self.assertEqual(sanitize('<img src="javascript:x" alt="a">'),
                         '<img alt="a">')


class AutoCloseTest(unittest.TestCase):
    def test_unclosed_inline_tag_closed_at_eof(self):
        self.assertEqual(sanitize("<b>x"), "<b>x</b>")

    def test_multiple_unclosed_closed_in_reverse(self):
        self.assertEqual(sanitize("<b><i>x"), "<b><i>x</i></b>")

    def test_mismatched_nesting_closes_by_stack(self):
        self.assertEqual(sanitize("<b><i>x</b>y</i>"),
                         "<b><i>x</i></b>y")

    def test_stray_end_tags_are_dropped(self):
        self.assertEqual(sanitize("<p>a</p></p>"), "<p>a</p>")
        self.assertEqual(sanitize("a</p>b</b>"), "ab")

    def test_void_tags_have_no_end_tag(self):
        self.assertEqual(sanitize("a<br/>b"), "a<br>b")
        self.assertEqual(sanitize('<img src="/x"/>'), '<img src="/x">')

    def test_implicit_paragraph_closing(self):
        self.assertEqual(sanitize("<p>1<p>2"), "<p>1</p><p>2</p>")

    def test_implicit_li_closing(self):
        self.assertEqual(sanitize("<ul><li>a<li>b</ul>"),
                         "<ul><li>a</li><li>b</li></ul>")

    def test_nested_anchor_closes_outer_first(self):
        self.assertEqual(sanitize("<a>x<a>y</a>z</a>"),
                         "<a>x</a><a>y</a>z")

    def test_unclosed_script_drops_everything_after_open(self):
        self.assertEqual(sanitize("<script>alert(1)"), "")


class IdempotenceTest(unittest.TestCase):
    CASES = [
        "<b>x</b>",
        "&lt;script&gt;alert(1)&lt;/script&gt;",
        "<b>x",
        '<a href="javascript:alert(1)">x</a>',
        '<a href="https://x/?a=1&b=2" title="q&quot;r">x</a>',
        "<b><i>x</b>y</i>",
        "<p>1<p>2",
        "<ul><li>1<li>2</ul>",
        '<img src="javascript:x" alt="a" onerror="y">',
        "<script>var s='</script>'</script>tail",
        "plain &amp; &quot; &lt; text",
    ]

    def test_sanitize_twice(self):
        once = sanitize("<b>x</b>")
        self.assertEqual(sanitize(once), once)

    def test_all_fixed_points(self):
        for text in self.CASES:
            with self.subTest(text=text):
                once = sanitize(text)
                self.assertEqual(sanitize(once), once)

    def test_no_executable_tags_or_bare_angle_brackets(self):
        for text in self.CASES:
            with self.subTest(text=text):
                once = sanitize(text)
                self.assertNotIn("<script", once.lower())
                self.assertNotIn("<style", once.lower())
                # 文本里不允许裸 < 或 >：所有 < 必须紧跟白名单标签。
                import re
                for match in re.finditer(r"<[^>]*>", once):
                    inner = match.group(0)[1:-1].lstrip("/")
                    name = inner.split(None, 1)[0]
                    self.assertTrue(
                        name in {"p", "br", "b", "i", "em", "strong", "u",
                                 "code", "pre", "ul", "ol", "li",
                                 "blockquote", "a", "img", "span"},
                        "unexpected token: %r" % match.group(0))

    def test_visible_text_preserved(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(visible_text(text), visible_text(sanitize(text)))


if __name__ == "__main__":
    unittest.main()
