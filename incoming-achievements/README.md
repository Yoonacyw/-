# GitHub 自动成果上传区

此文件夹用于从 GitHub 网页上传新的学术论文 PDF。请不要删除本说明。

## 上传步骤

1. 在 GitHub 仓库中打开 `incoming-achievements` 文件夹。
2. 点击 `Add file`，选择 `Upload files`。
3. 拖入一个或多个 PDF；GitHub 网页单个文件不能超过 25 MiB。
4. 点击 `Commit changes`，直接提交到 `main` 分支。
5. 打开仓库的 `Actions` 页面，查看“自动识别并发布成果 PDF”。
6. 工作流成功后，PDF 会移入 `files/achievements/年份`，成果信息会写入 `data/achievements.json`，随后 GitHub Pages 自动更新。

## 识别规则

- 系统先从 PDF 前三页提取 DOI、题目和作者。
- 有 DOI 时会通过 Crossref 补全标准题名、全部作者、期刊、年份和卷期页码。
- 知网 PDF 会按期刊首页版式直接识别中文题名、英文作者行、卷期页码和 DOI，不依赖 Crossref。
- 题目、年份或论文作者无法可靠识别时，工作流会失败并保留 PDF，不会发布不完整记录。
- 重复上传相同 PDF 时，系统会按文件哈希自动跳过。

## 可选：人工覆盖识别结果

如果 PDF 排版特殊，可在上传 PDF 时同时上传一个同名 JSON 文件。例如：

- `new-paper.pdf`
- `new-paper.json`

JSON 内容示例：

```json
{
  "type": "paper",
  "year": "2026",
  "title": "Paper title",
  "authorLine": "Dong, Wenhao; Ma, Feng; Fu, Zhen",
  "authors": "Dong, Wenhao; Ma, Feng; Fu, Zhen; Other, Author",
  "journal": "Journal Name",
  "citation": "158 (2026) 105459",
  "doi": "10.1016/j.example.2026.123456"
}
```

JSON 中填写的字段会覆盖自动识别结果；未填写的字段仍使用自动识别值。
