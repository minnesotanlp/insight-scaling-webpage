#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取多个数据集的 insights 数据并生成交互式可视化所需的 JSON 数据
"""

import os
import json
import shutil
from typing import List, Dict, Any, Tuple

# 数据集配置
DATASETS = {
    "diabetes": {
        "runs_path": "/home/shuyu/projects/insight_scaling/ablation/new_prompt/diabetes/baseline/diabetes.csv_20251222-024828/runs",
        "display_name": "Diabetes",
        "interval": 10
    },
    "education": {
        "runs_path": "/home/shuyu/projects/insight_scaling/ablation/new_prompt/Education/baseline/Education.csv_20251222-034020/runs",
        "display_name": "Education",
        "interval": 10
    },
    "happiness": {
        "runs_path": "/home/shuyu/projects/insight_scaling/ablation/new_prompt/Happiness/baseline/Happiness.csv_20251222-051331/runs",
        "display_name": "World Happiness",
        "interval": 10
    },
    "insurance": {
        "runs_path": "/home/shuyu/projects/insight_scaling/ablation/new_prompt/Insurance/baseline/Insurance.csv_20251222-015937/runs",
        "display_name": "Medical Insurance",
        "interval": 10
    },
    "shopping": {
        "runs_path": "/home/shuyu/projects/insight_scaling/ablation/new_prompt/shopping/baseline/shopping.csv_20251222-043132/runs",
        "display_name": "Shopping Behavior",
        "interval": 10
    }
}

OUTPUT_BASE = "/home/shuyu/projects/insight-scaling-webpage"


def load_all_insights(runs_root: str) -> List[Dict[str, Any]]:
    """加载所有 insights"""
    all_insights = []

    for run_name in sorted(os.listdir(runs_root)):
        run_dir = os.path.join(runs_root, run_name)
        if not os.path.isdir(run_dir) or not run_name.startswith("run_"):
            continue

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


def sample_insights(insights: List[Dict], interval: int = 10) -> Tuple[List[Dict], List[int]]:
    """按分数排序后采样，首尾必须包含"""
    sorted_insights = sorted(insights, key=lambda x: x["score"])
    n = len(sorted_insights)

    if n == 0:
        return [], []
    if n == 1:
        return [sorted_insights[0]], [0]

    sampled = [sorted_insights[0]]
    indices = [0]

    last_idx = n - 1
    for i in range(interval, last_idx, interval):
        sampled.append(sorted_insights[i])
        indices.append(i)

    sampled.append(sorted_insights[-1])
    indices.append(last_idx)

    return sampled, indices


def process_dataset(dataset_key: str, config: Dict):
    """处理单个数据集"""
    print(f"\n{'='*50}")
    print(f"Processing: {config['display_name']} ({dataset_key})")
    print(f"{'='*50}")

    runs_root = config["runs_path"]
    interval = config["interval"]

    output_dir = os.path.join(OUTPUT_BASE, "data")
    img_output_dir = os.path.join(OUTPUT_BASE, f"img/interactive_{dataset_key}")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(img_output_dir, exist_ok=True)

    print(f"Loading insights from: {runs_root}")
    all_insights = load_all_insights(runs_root)
    print(f"Total insights: {len(all_insights)}")

    if len(all_insights) == 0:
        print(f"[ERROR] No insights found for {dataset_key}")
        return

    sorted_insights = sorted(all_insights, key=lambda x: x["score"])
    all_scores = [ins["score"] for ins in sorted_insights]

    sampled, sampled_indices = sample_insights(all_insights, interval)
    print(f"Sampled {len(sampled)} insights at interval {interval}")

    curve_data = {
        "scores": all_scores,
        "total_count": len(all_scores),
        "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0,
        "min_score": min(all_scores) if all_scores else 0,
        "max_score": max(all_scores) if all_scores else 0,
    }

    sampled_data = []
    for i, (ins, idx) in enumerate(zip(sampled, sampled_indices)):
        img_filename = f"sample_{i}.png"
        dest_path = os.path.join(img_output_dir, img_filename)

        if os.path.exists(ins["img_path"]):
            shutil.copy2(ins["img_path"], dest_path)
        else:
            print(f"[WARN] Image not found: {ins['img_path']}")

        sampled_data.append({
            "index": idx,
            "score": round(ins["score"], 2),
            "insight": ins["insight"],
            "img_url": f"img/interactive_{dataset_key}/sample_{i}.png",
            "run_name": ins["run_name"]
        })

    output_data = {
        "dataset": dataset_key,
        "display_name": config["display_name"],
        "curve": curve_data,
        "samples": sampled_data,
        "interval": interval
    }

    output_path = os.path.join(output_dir, f"interactive_{dataset_key}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Saved: {output_path}")
    print(f"Stats: {curve_data['total_count']} points, avg={curve_data['avg_score']:.2f}, sampled={len(sampled_data)}")


def main():
    print("Extracting interactive data for all datasets...")

    for dataset_key, config in DATASETS.items():
        process_dataset(dataset_key, config)

    print("\n" + "="*50)
    print("All datasets processed!")
    print("="*50)


if __name__ == "__main__":
    main()
