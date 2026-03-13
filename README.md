# 数据标注工作流程说明

本项目包含两个脚本，用于管理数据标注的分配和批次划分。

## 📁 文件结构

```
connect_html/
├── allocate_data.py          # 数据分配脚本
├── batch_split.py            # 批次划分脚本（增量模式）
├── sampled_2500.json         # 原始数据（2500条对话）
├── allocated_data.csv        # 分配后的CSV（250个标注者）
├── allocation_info.json      # 分配记录
├── connect_upload.html       # Connect平台HTML模板
├── batches/                  # 批次文件夹
│   ├── batch_1.csv          # 第1批次
│   ├── batch_2.csv          # 第2批次
│   └── ...
└── batch_record.json         # 批次记录
```

---

## 📝 工作流程

### 步骤 1: 数据分配（一次性）

使用 `allocate_data.py` 将原始数据分配给标注者。

```bash
python allocate_data.py
```

**功能：**
- ✅ 兼容新旧数据格式（JSON数组 / JSONL）
- ✅ 自动字段映射（post_id → id, conversation → text.Conversation）
- ✅ 固定随机种子（seed=42），确保结果可重复
- ✅ 随机打乱数据后分配给标注者
- ✅ CSV中 Participants=3

**输入示例：**
```
使用默认数据文件 (e:\projects\connect_html\sampled_2500.json)? (y/n): y
请输入每个标注者需要标注的对话数量: 10
确认开始分配？(y/n): y
```

**输出文件：**
- `allocated_data.csv` - 分配后的CSV（250行，每行1个标注者的10条对话）
- `allocation_info.json` - 分配记录
- `connect_upload.html` - 用于Connect平台的HTML模板

---

### 步骤 2: 批次划分（增量模式，可多次运行）

使用 `batch_split.py` 将大CSV分割成小批次，**每次运行只生成一个新批次**。

```bash
python batch_split.py
```

**功能：**
- ✅ 增量模式：每次只生成下一个批次
- ✅ 灵活配置：您决定每批次包含多少个标注者
- ✅ 自动记录：跟踪已分配的标注者数量和进度
- ✅ 状态显示：显示已创建批次和剩余标注者

**第一次运行示例：**
```
使用默认CSV文件 (e:\projects\connect_html\allocated_data.csv)? (y/n): y
批次文件命名前缀 (默认: batch): batch

当前批次状态
============================================================
还未创建任何批次
============================================================

剩余 250 个标注者可分配
本批次要分配多少个标注者? (1-250): 5
确认创建此批次？(y/n): y

批次创建成功！
批次编号: 1
文件路径: e:\projects\connect_html\batches\batch_1.csv
标注者数: 5
进度: 5/250 (2.0%)
剩余: 245 个标注者
```

**第二次运行示例：**
```
当前批次状态
============================================================
已创建批次数: 1
已分配标注者数: 5
剩余标注者数: 245

已创建的批次:
  ✓ 批次 1: batch_1.csv (5 个标注者, 创建于 2026-03-14T06:19:33)
============================================================

剩余 245 个标注者可分配
本批次要分配多少个标注者? (1-245): 10
确认创建此批次？(y/n): y

批次创建成功！
批次编号: 2
文件路径: e:\projects\connect_html\batches\batch_2.csv
标注者数: 10
进度: 15/250 (6.0%)
剩余: 235 个标注者
```

**输出文件：**
- `batches/batch_1.csv` - 第1批次（5个标注者）
- `batches/batch_2.csv` - 第2批次（10个标注者）
- `batches/batch_N.csv` - 第N批次
- `batch_record.json` - 批次记录（包含所有批次信息）

---

## 📊 批次记录格式

`batch_record.json` 记录了所有批次的详细信息：

```json
{
  "created_at": "2026-03-14T06:19:33.818991",
  "updated_at": "2026-03-14T06:19:47.922125",
  "source_file": "e:\\projects\\connect_html\\allocated_data.csv",
  "prefix": "batch",
  "total_allocated": 15,
  "batches": [
    {
      "batch_number": 1,
      "filename": "batch_1.csv",
      "filepath": "e:\\projects\\connect_html\\batches\\batch_1.csv",
      "row_count": 5,
      "start_index": 1,
      "end_index": 5,
      "created_at": "2026-03-14T06:19:33.825604",
      "status": "created"
    },
    {
      "batch_number": 2,
      "filename": "batch_2.csv",
      "filepath": "e:\\projects\\connect_html\\batches\\batch_2.csv",
      "row_count": 10,
      "start_index": 6,
      "end_index": 15,
      "created_at": "2026-03-14T06:19:47.922104",
      "status": "created"
    }
  ]
}
```

---

## 🎯 使用场景

### 典型工作流

1. **初始分配**（运行一次）
   ```bash
   python allocate_data.py
   # 生成 allocated_data.csv (250个标注者，每人10条对话)
   ```

2. **发布批次1**（5个标注者）
   ```bash
   python batch_split.py
   # 输入: 5
   # 生成: batches/batch_1.csv
   # 上传到Connect平台
   ```

3. **发布批次2**（10个标注者）
   ```bash
   python batch_split.py
   # 输入: 10
   # 生成: batches/batch_2.csv
   # 上传到Connect平台
   ```

4. **继续发布更多批次...**
   ```bash
   python batch_split.py
   # 根据需要继续创建批次
   ```

---

## ⚙️ 技术细节

### allocate_data.py

- **随机种子**: `random.seed(42)` - 确保每次运行结果相同
- **数据格式**: 自动检测JSON数组或JSONL格式
- **字段映射**:
  - `post_id` → `id`
  - `conversation` → `text.Conversation`
  - `title` → `text.Title`
- **CSV格式**: 每行包含 Participants=3 + id1...id10 + title1...title10 + convo1...convo10

### batch_split.py

- **增量模式**: 只生成下一个批次，不重新生成已有批次
- **状态管理**: 通过 batch_record.json 跟踪进度
- **灵活分配**: 每批次可包含不同数量的标注者
- **进度跟踪**: 实时显示已分配/剩余标注者数量

---

## 🔍 常见问题

**Q: 如果想重新开始批次划分怎么办？**
A: 删除 `batch_record.json` 和 `batches/` 文件夹，重新运行 `batch_split.py`

**Q: 批次记录丢失了怎么办？**
A: 批次记录保存在 `batch_record.json`，建议定期备份此文件

**Q: 可以修改已创建的批次吗？**
A: 不建议修改。如需调整，建议删除对应批次文件和记录，重新创建

**Q: 每次运行 allocate_data.py 结果都一样吗？**
A: 是的，因为使用了固定随机种子（seed=42），确保结果可重复

---

## 📈 进度监控

查看批次记录：
```bash
cat batch_record.json
```

查看已创建的批次文件：
```bash
ls -lh batches/
```

统计总进度：
```bash
python -c "import json; r=json.load(open('batch_record.json')); print(f'进度: {r[\"total_allocated\"]}/250 ({r[\"total_allocated\"]/250*100:.1f}%)')"
```

---

## 📌 注意事项

1. ✅ 每次只运行 `allocate_data.py` **一次**（生成初始分配）
2. ✅ 多次运行 `batch_split.py` 以创建多个批次
3. ✅ 每个批次独立的CSV文件，方便单独上传到Connect平台
4. ✅ 批次记录自动保存，断点续传
5. ✅ 所有批次文件包含完整表头，可独立使用

---

生成时间: 2026-03-14
