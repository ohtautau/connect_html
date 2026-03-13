#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次划分脚本（增量模式）
每次运行只生成下一个批次的CSV文件
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def read_csv_rows(file_path: str) -> tuple:
    """读取CSV文件，返回表头和所有数据行"""
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)
    return headers, rows


def load_batch_record(record_file: str) -> Dict[str, Any]:
    """加载批次记录，如果不存在则创建新记录"""
    if Path(record_file).exists():
        with open(record_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            "created_at": datetime.now().isoformat(),
            "batches": [],
            "total_allocated": 0,
            "prefix": "batch"
        }


def save_batch_record(record: Dict[str, Any], record_file: str):
    """保存批次记录"""
    record["updated_at"] = datetime.now().isoformat()
    with open(record_file, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def create_next_batch(headers: List[str], rows: List[List[str]],
                     record: Dict[str, Any], rows_in_batch: int,
                     output_dir: str) -> Dict[str, Any]:
    """创建下一个批次的CSV文件"""
    # 计算起始位置
    total_allocated = record["total_allocated"]
    remaining = len(rows) - total_allocated

    if remaining == 0:
        print("\n所有数据已分配完毕，没有更多数据可分配。")
        return None

    # 检查是否超出剩余数量
    if rows_in_batch > remaining:
        print(f"\n警告：请求分配 {rows_in_batch} 行，但只剩余 {remaining} 行")
        use_all = input(f"是否使用剩余的全部 {remaining} 行？(y/n): ").strip().lower()
        if use_all == 'y':
            rows_in_batch = remaining
        else:
            print("批次创建已取消。")
            return None

    # 提取批次数据
    start_idx = total_allocated
    end_idx = start_idx + rows_in_batch
    batch_rows = rows[start_idx:end_idx]

    # 生成批次编号和文件名
    batch_num = len(record["batches"]) + 1
    prefix = record["prefix"]
    batch_filename = f"{prefix}_{batch_num}.csv"

    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    batch_filepath = output_path / batch_filename

    # 写入CSV文件
    with open(batch_filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(batch_rows)

    # 创建批次信息
    batch_info = {
        "batch_number": batch_num,
        "filename": batch_filename,
        "filepath": str(batch_filepath),
        "row_count": len(batch_rows),
        "start_index": start_idx + 1,  # 1-based
        "end_index": end_idx,
        "created_at": datetime.now().isoformat(),
        "status": "created"
    }

    return batch_info


def display_status(record: Dict[str, Any], total_rows: int):
    """显示当前状态"""
    print("\n" + "="*60)
    print("当前批次状态")
    print("="*60)

    if len(record["batches"]) == 0:
        print("还未创建任何批次")
    else:
        print(f"\n已创建批次数: {len(record['batches'])}")
        print(f"已分配标注者数: {record['total_allocated']}")
        print(f"剩余标注者数: {total_rows - record['total_allocated']}")

        print("\n已创建的批次:")
        for batch in record["batches"]:
            status_emoji = "✓" if batch.get("status") == "created" else "○"
            print(f"  {status_emoji} 批次 {batch['batch_number']}: {batch['filename']} "
                  f"({batch['row_count']} 个标注者, 创建于 {batch['created_at'][:19]})")

    print("="*60)


def main():
    # 默认路径
    default_source_csv = r"e:\projects\connect_html\allocated_data.csv"
    default_output_dir = r"e:\projects\connect_html\batches"
    default_record_file = r"e:\projects\connect_html\batch_record.json"

    print("\n" + "="*60)
    print("批次划分工具 - 增量模式")
    print("="*60)
    print("每次运行生成一个新批次")

    # 加载批次记录
    record = load_batch_record(default_record_file)

    # 询问是否使用默认源文件
    use_default = input(f"\n使用默认CSV文件 ({default_source_csv})? (y/n): ").strip().lower()

    if use_default == 'y':
        source_csv = default_source_csv
    else:
        source_csv = input("请输入CSV文件路径: ").strip()

    # 检查文件是否存在
    if not Path(source_csv).exists():
        print(f"\n错误：文件不存在: {source_csv}")
        sys.exit(1)

    # 读取CSV数据
    print(f"\n正在读取CSV文件...")
    try:
        headers, rows = read_csv_rows(source_csv)
        print(f"成功读取: {len(rows)} 行数据")
    except Exception as e:
        print(f"\n错误：读取CSV文件失败: {e}")
        sys.exit(1)

    if len(rows) == 0:
        print("\n错误：CSV文件没有数据行")
        sys.exit(1)

    # 如果是第一次运行，设置前缀
    if len(record["batches"]) == 0:
        default_prefix = "batch"
        prefix = input(f"\n批次文件命名前缀 (默认: {default_prefix}): ").strip()
        if not prefix:
            prefix = default_prefix
        record["prefix"] = prefix
        record["source_file"] = source_csv

    # 显示当前状态
    display_status(record, len(rows))

    # 检查是否还有剩余数据
    remaining = len(rows) - record["total_allocated"]
    if remaining == 0:
        print("\n所有数据已分配完毕！")
        sys.exit(0)

    # 询问本次批次大小
    print(f"\n剩余 {remaining} 个标注者可分配")
    while True:
        try:
            rows_in_batch = int(input(f"本批次要分配多少个标注者? (1-{remaining}): "))
            if rows_in_batch <= 0:
                print("数量必须大于0，请重新输入。")
                continue
            if rows_in_batch > remaining:
                print(f"数量不能超过剩余数量({remaining})，请重新输入。")
                continue
            break
        except ValueError:
            print("输入无效，请输入一个整数。")

    # 确认创建
    next_batch_num = len(record["batches"]) + 1
    print(f"\n将创建批次 {next_batch_num}:")
    print(f"  文件名: {record['prefix']}_{next_batch_num}.csv")
    print(f"  标注者数: {rows_in_batch}")
    print(f"  范围: 第 {record['total_allocated'] + 1} - {record['total_allocated'] + rows_in_batch} 行")

    confirm = input("\n确认创建此批次？(y/n): ").strip().lower()
    if confirm != 'y':
        print("批次创建已取消。")
        sys.exit(0)

    # 创建批次
    print("\n正在创建批次...")
    batch_info = create_next_batch(headers, rows, record, rows_in_batch, default_output_dir)

    if batch_info:
        # 更新记录
        record["batches"].append(batch_info)
        record["total_allocated"] += batch_info["row_count"]

        # 保存记录
        save_batch_record(record, default_record_file)

        # 显示结果
        print("\n" + "="*60)
        print("批次创建成功！")
        print("="*60)
        print(f"\n批次编号: {batch_info['batch_number']}")
        print(f"文件路径: {batch_info['filepath']}")
        print(f"标注者数: {batch_info['row_count']}")
        print(f"\n批次记录已更新: {default_record_file}")

        # 显示更新后的状态
        remaining_after = len(rows) - record["total_allocated"]
        print(f"\n进度: {record['total_allocated']}/{len(rows)} "
              f"({record['total_allocated']/len(rows)*100:.1f}%)")
        if remaining_after > 0:
            print(f"剩余: {remaining_after} 个标注者")
            print("\n再次运行此脚本可创建下一个批次。")
        else:
            print("\n所有数据已分配完毕！")

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
