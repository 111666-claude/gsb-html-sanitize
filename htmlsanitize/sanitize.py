"""HTML 子集净化（白名单 + 实体转义 + 栈自动闭合），只用标准库。

单遍流式处理（html.parser），状态内存只与标签深度相关；
文本先由 parser 解码成纯文本，输出时统一重新转义，杜绝实体还魂。
"""

import html
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "b", "i", "em", "strong", "u", "code", "pre",
                "ul", "ol", "li", "blockquote", "a", "img", "span"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title"}}
URL_ATTRS = {"a": {"href"}, "img": {"src"}}
VOID_TAGS = {"br", "img"}
DROPPED_CONTENT = {"script", "style"}
# 打开这些块级标签时，栈中未闭合的 <p> 先按栈闭合（HTML 的 p 为隐式闭合）。
BLOCK_TAGS = {"p", "ul", "ol", "li", "blockquote", "pre"}
SAFE_URL_PREFIXES = ("http://", "https://", "mailto:")

_CHUNK_SIZE = 64 * 1024


class SanitizeError(ValueError):
    """输入不合法。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _clean_text(data):
    """纯文本 -> 可放在元素内容里的转义文本（& < > " 全部实体化）。"""
    return html.escape(data, quote=True)


def _clean_attr_value(value):
    """属性值：去掉双引号，其余特殊字符实体化（保证幂等）。"""
    return html.escape(value.replace('"', ""), quote=True)


def _safe_url(value):
    """协议白名单：http/https/mailto 与以 / 或 # 开头的相对地址。

    属性值经过 parser 实体解码后才检查，因此 ``java&#115;cript:`` 之类的
    编码绕过同样会被拦下；前导空白/控制字符先剥掉，防止 ``java\\nscript:``。
    不合法返回 None（调用方丢弃该属性）。
    """
    if not value:
        return None
    url = value.lstrip()
    while url[:1] == "\x00":
        url = url[1:].lstrip()
    if not url:
        return None
    if url[0] in ("/", "#"):
        return url
    if url.lower().startswith(SAFE_URL_PREFIXES):
        return url
    return None


class _Collector(HTMLParser):
    """单遍收集器：白名单过滤、URL 协议检查、标签栈自动闭合。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.skip_depth = 0

    def _emit_close(self, tag):
        self.parts.append("</%s>" % tag)

    def _close_to(self, tag):
        """从栈顶一路闭合到最近的同名标签（含该标签）。"""
        while self.stack:
            current = self.stack.pop()
            self._emit_close(current)
            if current == tag:
                return

    def _close_open_for(self, tag):
        """新开始标签入栈前，先处理不合法嵌套。"""
        if tag in BLOCK_TAGS and "p" in self.stack:
            self._close_to("p")
        if tag == "li" and "li" in self.stack:
            self._close_to("li")
        if tag == "a" and "a" in self.stack:
            self._close_to("a")

    def _render_attrs(self, tag, attrs):
        allowed = ALLOWED_ATTRS.get(tag, ())
        url_attrs = URL_ATTRS.get(tag, ())
        pieces = []
        for name, value in attrs:  # parser 按输入顺序给出
            if name not in allowed:
                continue
            value = value if value is not None else ""
            if name in url_attrs:
                value = _safe_url(value)
                if value is None:
                    continue
            pieces.append(' %s="%s"' % (name, _clean_attr_value(value)))
        return "".join(pieces)

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_CONTENT:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag not in ALLOWED_TAGS:
            return  # 非白名单标签：丢掉标签，文字照常保留
        self._close_open_for(tag)
        self.parts.append("<%s%s>" % (tag, self._render_attrs(tag, attrs)))
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in DROPPED_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return  # 多余/非法结束标签直接丢掉
        if tag in self.stack:
            self._close_to(tag)
        # 栈里没有同名开标签：多余的结束标签，丢掉。

    def handle_startendtag(self, tag, attrs):
        if self.skip_depth or tag in DROPPED_CONTENT or tag not in ALLOWED_TAGS:
            if tag in DROPPED_CONTENT:
                self.skip_depth = max(0, self.skip_depth - 1)
            return
        attr_text = self._render_attrs(tag, attrs)
        if tag in VOID_TAGS:
            self.parts.append("<%s%s>" % (tag, attr_text))
        else:
            self.parts.append("<%s%s></%s>" % (tag, attr_text, tag))

    def handle_data(self, data):
        if self.skip_depth:
            return  # script/style 内容连文字一起丢
        self.parts.append(_clean_text(data))

    def finish(self):
        while self.stack:
            self._emit_close(self.stack.pop())


def sanitize(text):
    """净化 HTML 子集文本并返回规范化结果。

    结果满足：只含白名单标签/属性、文本全部实体转义、非 void 标签全部闭合、
    ``sanitize(sanitize(x)) == sanitize(x)``。
    """
    if not isinstance(text, str):
        raise SanitizeError("sanitize 需要 str 输入")
    collector = _Collector()
    for start in range(0, len(text), _CHUNK_SIZE):
        collector.feed(text[start:start + _CHUNK_SIZE])
    collector.close()
    collector.finish()
    return "".join(collector.parts)
