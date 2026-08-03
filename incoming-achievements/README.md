# GitHub 成果上传与人工确认区

此文件夹用于从 GitHub 网页上传成果 PDF。上传后不会立即发布，必须先检查自动生成的 JSON，再手动运行发布工作流。

## 第一步：上传并自动识别

1. 打开仓库的 `incoming-achievements` 文件夹。
2. 点击 `Add file` → `Upload files`。
3. 只上传 PDF，然后点击 `Commit changes` 提交到 `main`。
4. 打开仓库的 `Actions` 页面，等待“识别成果 PDF（等待人工确认）”运行成功。
5. 返回本文件夹并刷新页面。PDF 旁会出现一个同名 JSON，例如：
   - `new-paper.pdf`
   - `new-paper.json`

## 第二步：人工检查和修改

1. 打开自动生成的同名 JSON。
2. 点击右上角铅笔按钮 `Edit this file`。
3. 检查并修改 `year`、`title`、`authors`、`journal`、`citation` 和 `doi`。
4. 点击 `Commit changes` 保存。此时仍不会发布到成果页面。

中文论文作者使用中文姓名和中文逗号，例如 `马峰，傅珍，张天义`；英文论文使用 `Last, First` 和英文分号，例如 `Ma, Feng; Fu, Zhen; Zhang, Tianyi`。

自动生成的 JSON 类似：

```json
{
  "_instructions": "请检查并修改下面字段，保存后到 Actions 运行“发布已人工确认的成果”",
  "_pdf": "new-paper.pdf",
  "type": "paper",
  "year": "2026",
  "title": "Paper title",
  "authors": "Dong, Wenhao; Ma, Feng; Fu, Zhen; Other, Author",
  "journal": "Journal Name",
  "citation": "158 (2026) 105459",
  "doi": "10.1016/j.example.2026.123456"
}
```

请保留 `_instructions` 和 `_pdf`，它们只是提示信息，不会显示在网站中。`type` 通常保持为 `paper`。

## 第三步：确认发布

1. 打开仓库的 `Actions` 页面。
2. 在左侧选择“发布已人工确认的成果”。
3. 点击 `Run workflow`。
4. 只有一个待发布 PDF 时，文件名可以留空；有多个时填写需要发布的完整 PDF 文件名。
5. 再次点击绿色 `Run workflow`。
6. 工作流成功后，PDF 才会移入 `files/achievements/年份`，审核 JSON 会被删除，成果信息会写入 `data/achievements.json` 和 `publications.html`。

## 注意事项

- 不要直接修改 `publications.html` 中的自动成果区。
- 自动识别结果不正确时，直接修改同名 JSON；发布时以 JSON 内容为准。
- `year`、`title` 和论文 `authors` 不能为空，否则发布工作流会停止并提示具体字段。
- 系统会检查 PDF 哈希，已经发布的附件不能重复添加。
- GitHub 网页单个上传文件不能超过 25 MiB。
