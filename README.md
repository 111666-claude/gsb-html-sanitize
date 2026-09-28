# html-sanitize

HTML 子集净化（标签/属性白名单、实体处理、自动闭合），只用 Python 标准库。

```
python3 -m htmlsanitize.cli --html '&lt;script&gt;alert(1)&lt;/script&gt;'
python3 -m htmlsanitize.cli --html '<b>x'
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **文本必须重新转义**：`--html '&lt;script&gt;alert(1)&lt;/script&gt;'` 的输入是一段纯文本，
  按口径输出仍然是 `&lt;script&gt;alert(1)&lt;/script&gt;`；现在解码后直接拼回去，
  放出真的 `<script>alert(1)</script>`（等于自己造了一个 XSS）。
- **未闭合标签要补**：`--html '<b>x'` 按口径是 `<b>x</b>`，现在原样给 `<b>x`。
- **属性要查协议**：`--html '<a href="javascript:alert(1)">x</a>'` 按口径要把 `href` 丢掉（给 `<a>x</a>`），
  现在原样保留；允许 http、https、mailto、以 `/` 或 `#` 开头的相对地址。
- 白名单：`p br b i em strong u code pre ul ol li blockquote a img span`；
  属性只有 `a[href,title]` 与 `img[src,alt,title]`；`script`/`style` 连内容一起丢掉；其它标签丢掉但保留文字。
- 输出规范：属性一律双引号并去掉值里的 `"`，文本里的 `<` `>` `&` `"` 都要转义成实体，
  多余的结束标签直接丢掉，`br`/`img` 不写结束标签。
- 不变量：`sanitize(sanitize(x)) == sanitize(x)`（幂等）；结果里不能再出现可执行标签；
  去掉标签后的可见文字与输入一致。
- 规模：1 MB 输入单遍处理，内存 O(标签深度)；不许用正则去「清标签」。

## 现在的行为

- `_Collector.handle_data` 把数据 `html.unescape` 之后直接拼进结果：文本里的 `<` 会被当成标签放出去。
- 没有标签栈：`<b>x` 就这样输出，`<p>a</p></p>` 的第二个 `</p>` 也照抄。
- `_safe_url` 是个恒等函数：`javascript:`、`data:` 都放行。

## 计划新增的能力

```
--html 文本     HTML 文本
--file 文件     从文件读
```

## 输出

```
&lt;script&gt;alert(1)&lt;/script&gt;
```

## 目录

```
htmlsanitize/sanitize.py   白名单、转义与闭合
htmlsanitize/cli.py        命令行入口
tests/                     unittest 用例
```
