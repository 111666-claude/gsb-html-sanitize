"""HTML 子集净化（白名单 + 实体重新转义 + 标签栈自动闭合），只用标准库。"""

import html
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "b", "i", "em", "strong", "u", "code", "pre",
                "ul", "ol", "li", "blockquote", "a", "img", "span"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title"}}
VOID_TAGS = {"br", "img"}
DROPPED_CONTENT = {"script", "style"}

# 块级标签开标签会隐式闭合未闭合的 <p>；这些标签自身也不允许嵌套。
BLOCK_TAGS = {"p", "ul", "ol", "li", "blockquote", "pre"}
SAFE_URL_PREFIXES = ("http://", "https://", "mailto:", "/", "#")


class SanitizeError(ValueError):
    """输入不合法。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _safe_url(value):
    """返回可安全输出的 URL；不允许的协议（javascript:/data: 等）返回 None。

    浏览器会忽略 URL 里的控制字符与空白，先把它们去掉再比较前缀，
    防止 ``java\\tscript:`` 这类绕过；前缀比较不区分大小写。
    """
    cleaned = "".join(ch for ch in value
                      if ord(ch) > 0x20 and ord(ch) != 0x7f)
    lowered = cleaned.lower()
    if lowered.startswith(SAFE_URL_PREFIXES):
        return cleaned
    return None


def _escape_text(data):
    """文本节点重新转义：& < > " 一律变成实体。"""
    return html.escape(data, quote=True)


def _escape_attr(value):
    """属性值去掉引号后转义，保证双引号包裹且幂等。"""
    return html.escape(value.replace('"', ""), quote=False)


class _Collector(HTMLParser):
    """单遍扫描：文本转义、标签/属性白名单、栈式自动闭合。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.skip_depth = 0

    def _emit_open(self, tag, attrs):
        pieces = []
        allowed = ALLOWED_ATTRS.get(tag, ())
        for name, value in attrs:
            if name not in allowed:
                continue
            value = value or ""
            if name in ("href", "src"):
                safe = _safe_url(value)
                if safe is None:
                    continue
                value = safe
            pieces.append(' %s="%s"' % (name, _escape_attr(value)))
        self.parts.append("<%s%s>" % (tag, "".join(pieces)))

    def _emit_close(self, tag):
        self.parts.append("</%s>" % tag)

    def _close_through(self, tag):
        """闭合从栈顶到 ``tag``（含）的所有标签。"""
        if tag not in self.stack:
            return False
        while self.stack[-1] != tag:
            self._emit_close(self.stack.pop())
        self._emit_close(self.stack.pop())
        return True

    def _implicit_close(self, tag):
        """开新标签前按 HTML 嵌套规则隐式闭合栈顶标签。"""
        if tag == "p":
            self._close_through("p")
        elif tag == "li":
            self._close_through("li")
        elif tag in BLOCK_TAGS:
            if self.stack and self.stack[-1] == "p":
                self._emit_close(self.stack.pop())
        if tag == "a":
            self._close_through("a")

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_CONTENT:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in ALLOWED_TAGS:
            return
        if tag in VOID_TAGS:
            self._emit_open(tag, attrs)
            return
        self._implicit_close(tag)
        self._emit_open(tag, attrs)
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in DROPPED_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self._close_through(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in VOID_TAGS or tag not in ALLOWED_TAGS:
            self.handle_starttag(tag, attrs)
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.skip_depth:
            return
        escaped = _escape_text(data)
        if escaped:
            self.parts.append(escaped)

    def finish(self):
        while self.stack:
            self._emit_close(self.stack.pop())


def sanitize(text):
    """净化 HTML：白名单标签/属性、文本重新转义、未闭合标签自动补齐。"""
    collector = _Collector()
    collector.feed(text)
    collector.close()
    collector.finish()
    return "".join(collector.parts)
