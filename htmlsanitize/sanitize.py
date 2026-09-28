"""HTML 子集净化（白名单 + 实体转义 + 自动闭合），只用标准库。

缺陷：文本解码后直接拼回去（会放出真标签）、未闭合标签不补、
属性不查协议、多余的结束标签照抄。
"""

import html
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "b", "i", "em", "strong", "u", "code", "pre",
                "ul", "ol", "li", "blockquote", "a", "img", "span"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title"}}
VOID_TAGS = {"br", "img"}
DROPPED_CONTENT = {"script", "style"}
SAFE_PREFIXES = ("http://", "https://", "mailto:", "/", "#")


class SanitizeError(ValueError):
    """输入不合法。缺陷：不带位置。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _safe_url(value):
    """缺陷：URL 协议完全不检查。"""
    return value


class _Collector(HTMLParser):
    """缺陷：没有标签栈，也不在输出时重新转义。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_CONTENT:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED_TAGS:
            return
        pieces = []
        for name, value in attrs:
            if name not in ALLOWED_ATTRS.get(tag, set()):
                continue
            pieces.append(' %s="%s"' % (name, _safe_url(value or "")))
        self.parts.append("<%s%s>" % (tag, "".join(pieces)))

    def handle_endtag(self, tag):
        if tag in DROPPED_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self.parts.append("</%s>" % tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.skip:
            return
        self.parts.append(html.unescape(data))  # 缺陷：输出时不再转义


def sanitize(text):
    """净化 HTML。缺陷：见模块说明。"""
    collector = _Collector()
    collector.feed(text)
    collector.close()
    return "".join(collector.parts)
