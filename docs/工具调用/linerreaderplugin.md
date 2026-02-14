# .LinkReaderPlugin
该插件是一个强大的网页内容抓取工具。它不仅能够返回网页的原始内容，包括标题、内容、链接等，而且还可以对这些内容进行筛选和解析。无论是需要进行网页内容分析，还是需要从各种网页中提取有价值的信息，这个插件都能大显身手。
网页信息提取: 网页标题、内容等基础信息一应俱全。
精准快速的抓取: 只需要提供网页的URL，就能快速获取完整网页的原始内容，无需任何编程或复杂操作。
高度兼容: 该插件可以处理各种类型的网页，包括但不限于HTML、PDF等，无论是静态页面还是动态页面，都能准确无误地抓取内容。
使用说明：
确定你需要抓取的网页URL有效。
插件会在短时间内返回这个网页的原始内容，包括标题、内容等。
需要解析用户query当中的url，根据url提取网页当中的内容

```
import reasync def main(args: Args) -> Output:    params = args.params    text = (params.get('input') or '').strip()    # 匹配 URL（防止吃掉逗号、中文逗号、引号等分隔符）    url_pattern = r'https?://[^\s,，\)\]\}\<\>\'"]+'    # 提取全部 URL    urls = re.findall(url_pattern, text)    urls = [u.rstrip('.,，;；)）]\'"') for u in urls]    # 去除 URL 后剩下用户输入内容    user_input = re.sub(url_pattern, '', text)    user_input = re.sub(r'^[,，;；\s]+', '', user_input)    user_input = re.sub(r'[,，;；\s]+$', '', user_input)    user_input = re.sub(r'[,，;；\s]+', ' ', user_input).strip()    # 输出结果    ret: Output = {        "urls": urls,        "user_input": user_input    }    return ret
```
