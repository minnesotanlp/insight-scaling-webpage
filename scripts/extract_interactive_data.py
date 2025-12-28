#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取 insights 数据并生成交互式可视化所需的 JSON 数据
"""

import os
import json
import base64
import shutil
from typing import List, Dict, Any, Tuple

def load_all_insights(runs_root: str) -> List[Dict[str, Any]]:
    """
    加载所有 insights，包含分数、文本和图片路径
    """
    all_insights = []

    for run_name in sorted(os.listdir(runs_root)):
        run_dir = os.path.join(runs_root, run_name)
        if not os.path.isdir(run_dir) or not run_name.startswith("run_"):
            continue

        # 跳过 error.json
        if os.path.exists(os.path.join(run_dir, "error.json")):
            continue

        insight_path = os.path.join(run_dir, "insights_validated.json")
        if not os.path.exists(insight_path):
            continue

        try:
            with open(insight_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for img_path, ins_list in data.items():
                for ins in ins_list:
                    score = ins.get("avg_scores")
                    insight_text = ins.get("insight", "")
                    if score is not None:
                        # 从路径中提取实际图片文件名
                        img_filename = os.path.basename(img_path)
                        verified_dir = os.path.join(run_dir, "viz", "verified")
                        actual_img_path = os.path.join(verified_dir, img_filename)

                        all_insights.append({
                            "score": float(score),
                            "insight": insight_text,
                            "img_path": actual_img_path,
                            "run_name": run_name,
                            "original_path": img_path
                        })
        except Exception as e:
            print(f"[WARN] Failed to read {insight_path}: {e}")

    return all_insights


def sample_insights(insights: List[Dict], interval: int = 20) -> Tuple[List[Dict], List[int]]:
    """
    按分数排序后，按 interval 间隔采样
    策略：首尾必须包含，中间按 interval 均匀采样
    返回采样的 insights 和对应的原始索引
    """
    # 按分数排序
    sorted_insights = sorted(insights, key=lambda x: x["score"])
    n = len(sorted_insights)

    if n == 0:
        return [], []
    if n == 1:
        return [sorted_insights[0]], [0]

    # 首位必须包含
    sampled = [sorted_insights[0]]
    indices = [0]

    # 中间按 interval 采样（从 interval 开始，不包括最后一个）
    last_idx = n - 1
    for i in range(interval, last_idx, interval):
        sampled.append(sorted_insights[i])
        indices.append(i)

    # 添加最后一个点
    sampled.append(sorted_insights[-1])
    indices.append(last_idx)

    return sampled, indices


def image_to_base64(img_path: str) -> str:
    """将图片转换为 base64 字符串"""
    if not os.path.exists(img_path):
        return ""
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"[WARN] Failed to read image {img_path}: {e}")
        return ""


def main():
    runs_root = "/home/shuyu/projects/insight_scaling/ablation/tokens/6_sentences/pruning_0.6/VIS.csv_20251212-021125/runs"
    output_dir = "/home/shuyu/projects/insight-scaling-webpage/data"
    img_output_dir = "/home/shuyu/projects/insight-scaling-webpage/img/interactive_pruning_0.6"

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(img_output_dir, exist_ok=True)

    print("Loading all insights...")
    all_insights = load_all_insights(runs_root)
    print(f"Total insights: {len(all_insights)}")

    # 按分数排序
    sorted_insights = sorted(all_insights, key=lambda x: x["score"])

    # 提取所有分数用于绘制曲线
    all_scores = [ins["score"] for ins in sorted_insights]

    # 采样用于交互
    interval = 20
    sampled, sampled_indices = sample_insights(all_insights, interval)

    print(f"Sampled {len(sampled)} insights at interval {interval}")

    # 准备输出数据
    # 1. 所有分数数据（用于绘制曲线）
    curve_data = {
        "scores": all_scores,
        "total_count": len(all_scores),
        "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0,
        "min_score": min(all_scores) if all_scores else 0,
        "max_score": max(all_scores) if all_scores else 0,
    }

    # 2. 采样点数据（用于交互）
    sampled_data = []
    for i, (ins, idx) in enumerate(zip(sampled, sampled_indices)):
        # 复制图片到网页目录
        img_filename = f"sample_{i}.png"
        dest_path = os.path.join(img_output_dir, img_filename)

        if os.path.exists(ins["img_path"]):
            shutil.copy2(ins["img_path"], dest_path)
            print(f"Copied image {i}: {ins['img_path']} -> {dest_path}")
        else:
            print(f"[WARN] Image not found: {ins['img_path']}")

        sampled_data.append({
            "index": idx,
            "score": round(ins["score"], 2),
            "insight": ins["insight"],
            "img_url": f"img/interactive_pruning_0.6/sample_{i}.png",
            "run_name": ins["run_name"]
        })

    # 保存数据
    output_data = {
        "curve": curve_data,
        "samples": sampled_data,
        "interval": interval
    }

    output_path = os.path.join(output_dir, "interactive_scores_pruning_0.6.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved data to {output_path}")
    print(f"Curve data: {curve_data['total_count']} points, avg={curve_data['avg_score']:.2f}")
    print(f"Sampled: {len(sampled_data)} points")


if __name__ == "__main__":
    main()
