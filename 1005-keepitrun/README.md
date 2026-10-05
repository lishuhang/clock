# 1005-keepitrun

keepitrun 同步脚本（04_convert-blog.py）在 2026-10-05 的修补：

## 修复内容：slugify 特殊字符污染

**问题**：`slugify()` 原实现用 `re.sub(r'[^\w\s-]', '', slug)` 清洗标题拼音，
其中 `\w` 包含下划线 `_`，导致标题中残留的下划线会进入 slug（甚至出现在开头），
生成 `_xxx` 这类非法路径（如 `_-bie-ba-li-guo-qing`），使文章 URL、图片路径全部错位。

**修复**：slug 清洗后增加一行，把下划线统一转为连字符并去掉首尾：

```python
slug = slug.replace('_', '-').strip('-')
```

**效果**：
- `_别把李国庆俞瑜，跟贝佐斯麦肯齐放在一起比` → `bie-ba-li-guo-qing-yu`（旧版：`_-bie-ba-li-guo-qing`）
- 竖线 `|` 等特殊字符本就由 `[^\w\s-]` 移除，不受影响
- 公众号标题中若含 `_`（如 `你命由天不由你 _ 航通社的朋友们`），也不会再污染 slug
