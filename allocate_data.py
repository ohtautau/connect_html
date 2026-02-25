#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分配脚本
用于将对话数据分配给不同的标注者，生成CSV和JSON格式的分配结果
"""

import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """加载JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def get_annotators_info(total_data: int) -> tuple:
    """通过终端交互获取标注者信息"""
    print("\n" + "="*60)
    print("数据分配工具 - 标注者信息收集")
    print("="*60)
    print(f"\n数据集总共包含: {total_data} 条对话")

    # 获取每个标注者需要标注的数量
    while True:
        try:
            count_per_annotator = int(input("\n请输入每个标注者需要标注的对话数量: "))
            if count_per_annotator <= 0:
                print("数量必须大于0，请重新输入。")
                continue
            if count_per_annotator > total_data:
                print(f"数量不能超过数据集总量({total_data})，请重新输入。")
                continue
            break
        except ValueError:
            print("输入无效，请输入一个整数。")

    # 计算需要的标注者数量
    num_annotators = (total_data + count_per_annotator - 1) // count_per_annotator

    print(f"\n根据数据量，将创建 {num_annotators} 个标注者")
    print(f"前 {num_annotators - 1} 个标注者各标注 {count_per_annotator} 条")

    remaining = total_data - (num_annotators - 1) * count_per_annotator
    print(f"最后一个标注者标注 {remaining} 条")

    # 创建标注者列表
    annotators = []
    for i in range(1, num_annotators + 1):
        if i < num_annotators:
            annotators.append((str(i), count_per_annotator))
        else:
            annotators.append((str(i), remaining))

    return annotators, count_per_annotator


def allocate_data(data: List[Dict], annotators: List[tuple]) -> Dict[str, List[Dict]]:
    """将数据分配给标注者"""
    allocation = {}
    current_idx = 0
    total_needed = sum(count for _, count in annotators)

    print(f"\n总共需要分配 {total_needed} 条对话")
    print(f"数据集包含 {len(data)} 条对话")

    if total_needed > len(data):
        print(f"\n警告：需要的对话数量({total_needed})超过了数据集大小({len(data)})")
        response = input("是否继续分配可用的数据？(y/n): ").strip().lower()
        if response != 'y':
            print("分配已取消。")
            sys.exit(0)

    for name, count in annotators:
        allocated_items = []
        for _ in range(min(count, len(data) - current_idx)):
            allocated_items.append(data[current_idx])
            current_idx += 1

        allocation[name] = allocated_items
        print(f"已为 {name} 分配 {len(allocated_items)} 条对话")

        if current_idx >= len(data):
            print(f"\n警告：数据已用完，后续标注者可能无法获得足够的数据。")
            break

    return allocation


def save_csv(allocation: Dict[str, List[Dict]], output_path: str, convos_per_annotator: int):
    """保存为CSV格式"""
    # 准备CSV头部，列数由每个标注者需要标注的数量决定
    headers = ['Participants'] + [f'convo{i+1}' for i in range(convos_per_annotator)]

    # 写入CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for annotator, convos in allocation.items():
            row = [1]  # Participants = 1，表示这一行由1个人标注

            # 将每个对话的完整数据转为JSON字符串
            for convo in convos:
                row.append(json.dumps(convo, ensure_ascii=False))

            # 如果不足指定数量，填充空列
            while len(row) < len(headers):
                row.append('')

            writer.writerow(row)

    print(f"\nCSV文件已保存到: {output_path}")


def generate_html(convos_per_annotator: int, output_path: str):
    """根据 convo 数量生成 Connect 用的 HTML"""
    # 隐藏数据 div
    convo_divs = '\n        '.join(
        f"<div class=\"convo-raw\" style=\"display:none\">{{{{ task.row_data['convo{i+1}'] }}}}</div>"
        for i in range(convos_per_annotator)
    )
    # 隐藏 answer input
    answer_inputs = '\n        '.join(
        f'<input type="hidden" name="answer_convo{i+1}" id="answer_convo{i+1}" value="">'
        for i in range(convos_per_annotator)
    )

    html = f'''<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <link href="dist/main.css" rel="stylesheet"/>
</head>
<body>
<div>
    <form>
        <details
                class="w-full border border-brand-primary-main dark:border-dark-100 rounded-md cr-bg-tertiary cr-text-primary">
            <summary class="py-3 px-4 font-bold cr-text-secondary cursor-pointer">
                Instructions
            </summary>
            <div class="pb-3 px-4 ql-editor ql-display !min-h-0">
                {{{{ task.instructions ?? 'No instructions provided.'}}}}
            </div>
        </details>

        <!-- raw convo data (hidden) -->
        {convo_divs}

        <!-- hidden answer inputs -->
        {answer_inputs}

        <!-- progress -->
        <div style="height:6px; background:#e0e0e0; border-radius:3px; margin:12px 0; overflow:hidden;">
            <div id="progressFill" style="height:100%; background:#4a90d9; width:0%; transition:width .3s;"></div>
        </div>
        <div id="progressText" style="text-align:center; font-size:14px; color:#555;"></div>

        <!-- conversation display -->
        <div style="border:1px solid #d0d0d0; border-radius:8px; padding:20px; margin:16px 0; background:#fafafa;">
            <div id="convoTitle" style="font-size:16px; font-weight:bold; margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid #4a90d9;"></div>
            <div id="convoBody" style="white-space:pre-wrap; line-height:1.7; font-size:14px; color:#333;"></div>
        </div>

        <!-- question -->
        <div style="margin:20px 0; padding:16px; background:#eef5fc; border-left:4px solid #4a90d9; border-radius:0 6px 6px 0;">
            <p style="font-weight:600; margin:0 0 12px 0;">Does this conversation contain any issues?</p>
            <label style="margin-right:24px;"><input type="radio" name="currentAnswer" value="Yes"> Yes</label>
            <label><input type="radio" name="currentAnswer" value="No"> No</label>
        </div>

        <!-- navigation -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin:24px 0;">
            <button type="button" id="prevBtn" onclick="go(-1)" style="padding:10px 28px; border:none; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; color:#fff; background:#6c757d;">&#8592; Previous</button>
            <span id="pageNum" style="font-size:14px; color:#555;"></span>
            <button type="button" id="nextBtn" onclick="go(1)" style="padding:10px 28px; border:none; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; color:#fff; background:#4a90d9;">Next &#8594;</button>
        </div>

        <!-- submit -->
        <div id="submitRow" style="text-align:center; margin:20px 0; display:none;">
            <button type="submit" id="submitBtn" disabled style="padding:12px 48px; font-size:15px; font-weight:600; border:none; border-radius:6px; background:#28a745; color:#fff; cursor:pointer;">Submit</button>
        </div>
    </form>
</div>

<script>
(function () {{
    /* parse all convo data from hidden divs */
    var slots = document.querySelectorAll('.convo-raw');
    var convos = [];
    for (var i = 0; i < slots.length; i++) {{
        var raw = slots[i].textContent.trim();
        if (!raw) continue;
        try {{ convos.push(JSON.parse(raw)); }} catch(e) {{ /* skip */ }}
    }}
    var total = convos.length;
    var cur = 0;
    var radios = document.querySelectorAll('input[name="currentAnswer"]');

    function getAnswer(idx) {{
        var el = document.getElementById('answer_convo' + (idx + 1));
        return el ? el.value : '';
    }}
    function setAnswer(idx, val) {{
        var el = document.getElementById('answer_convo' + (idx + 1));
        if (el) el.value = val;
    }}
    function countAnswered() {{
        var n = 0;
        for (var k = 0; k < total; k++) {{ if (getAnswer(k)) n++; }}
        return n;
    }}
    function saveCurrent() {{
        for (var j = 0; j < radios.length; j++) {{
            if (radios[j].checked) {{ setAnswer(cur, radios[j].value); return; }}
        }}
    }}
    function render() {{
        var c = convos[cur];
        document.getElementById('convoTitle').textContent = (c && c.text && c.text.Title) || '';
        document.getElementById('convoBody').textContent = (c && c.text && c.text.Conversation) || '';

        var saved = getAnswer(cur);
        for (var j = 0; j < radios.length; j++) {{
            radios[j].checked = (radios[j].value === saved);
        }}

        document.getElementById('prevBtn').disabled = (cur === 0);
        var isLast = (cur === total - 1);
        document.getElementById('nextBtn').style.display = isLast ? 'none' : '';
        document.getElementById('submitRow').style.display = isLast ? '' : 'none';

        var answered = countAnswered();
        document.getElementById('progressFill').style.width = (answered / total * 100) + '%';
        document.getElementById('progressText').textContent = 'Answered ' + answered + ' / ' + total;
        document.getElementById('pageNum').textContent = (cur + 1) + ' / ' + total;
        document.getElementById('submitBtn').disabled = (answered < total);
    }}

    for (var r = 0; r < radios.length; r++) {{
        radios[r].addEventListener('change', function () {{
            saveCurrent();
            var answered = countAnswered();
            document.getElementById('progressFill').style.width = (answered / total * 100) + '%';
            document.getElementById('progressText').textContent = 'Answered ' + answered + ' / ' + total;
            document.getElementById('submitBtn').disabled = (answered < total);
        }});
    }}

    window.go = function (dir) {{
        saveCurrent();
        var next = cur + dir;
        if (next < 0 || next >= total) return;
        cur = next;
        render();
        window.scrollTo(0, 0);
    }};

    if (total > 0) render();
}})();
</script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML模板已保存到: {output_path}")


def save_allocation_json(allocation: Dict[str, List[Dict]], output_path: str, annotators: List[tuple]):
    """保存分配情况的JSON文件"""
    allocation_info = {
        "participants": len(annotators),
        "total_conversations_allocated": sum(len(convos) for convos in allocation.values()),
        "annotators": []
    }

    for name, expected_count in annotators:
        actual_count = len(allocation.get(name, []))
        annotator_info = {
            "name": name,
            "expected_count": expected_count,
            "actual_count": actual_count,
            "conversation_ids": [item['id'] for item in allocation.get(name, [])]
        }
        allocation_info["annotators"].append(annotator_info)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(allocation_info, f, ensure_ascii=False, indent=2)

    print(f"分配情况JSON文件已保存到: {output_path}")


def main():
    # 默认路径
    default_data_path = r"e:\projects\connect_html\dataset_400_1.jsonl"
    default_output_csv = r"e:\projects\connect_html\allocated_data.csv"
    default_output_json = r"e:\projects\connect_html\allocation_info.json"
    html_output_path = r"e:\projects\connect_html\connect_upload.html"

    print("\n" + "="*60)
    print("欢迎使用数据分配工具")
    print("="*60)

    # 询问是否使用默认数据路径
    use_default = input(f"\n使用默认数据文件 ({default_data_path})? (y/n): ").strip().lower()

    if use_default == 'y':
        data_path = default_data_path
    else:
        data_path = input("请输入数据文件路径: ").strip()

    # 检查文件是否存在
    if not Path(data_path).exists():
        print(f"\n错误：文件不存在: {data_path}")
        sys.exit(1)

    # 加载数据
    print(f"\n正在加载数据...")
    try:
        data = load_jsonl(data_path)
        print(f"成功加载 {len(data)} 条对话数据")
    except Exception as e:
        print(f"\n错误：加载数据失败: {e}")
        sys.exit(1)

    # 获取标注者信息
    annotators, convos_per_annotator = get_annotators_info(len(data))

    # 显示分配计划
    print("\n" + "="*60)
    print("分配计划摘要")
    print("="*60)
    for name, count in annotators:
        print(f"标注者{name}: {count} 条对话")
    print(f"\n总计: {sum(count for _, count in annotators)} 条对话")

    confirm = input("\n确认开始分配？(y/n): ").strip().lower()
    if confirm != 'y':
        print("分配已取消。")
        sys.exit(0)

    # 分配数据
    print("\n正在分配数据...")
    allocation = allocate_data(data, annotators)

    # 保存结果
    print("\n正在保存结果...")
    save_csv(allocation, default_output_csv, convos_per_annotator)
    save_allocation_json(allocation, default_output_json, annotators)
    generate_html(convos_per_annotator, html_output_path)

    print("\n" + "="*60)
    print("分配完成！")
    print("="*60)
    print(f"生成的文件：")
    print(f"1. CSV文件:  {default_output_csv}")
    print(f"2. JSON文件: {default_output_json}")
    print(f"3. HTML模板: {html_output_path}  (上传到Connect)")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已被用户中断。")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
