"""YAML 提示词计划解析与组合生成

最小可用版本：
- 支持按分类多选 + 主提示词的笛卡尔积组合
- 主提示词始终位于提示词最前面
- 支持 per-subject 指定使用的分类与 overrides
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import itertools
import yaml


@dataclass
class PlanGlobal:
    joiner: str = ", "
    order: Optional[List[str]] = None
    max_combinations: Optional[int] = None


@dataclass
class SubjectPlan:
    name: str
    use_categories: Optional[List[str]] = None


@dataclass
class PromptPlan:
    global_cfg: PlanGlobal
    categories: Dict[str, List[str]]
    subjects: List[SubjectPlan]
    overrides: Dict[str, Dict[str, List[str]]]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PromptPlan":
        global_section = data.get("global", {}) or {}
        global_cfg = PlanGlobal(
            joiner=global_section.get("joiner", ", "),
            order=global_section.get("order"),
            max_combinations=global_section.get("max_combinations"),
        )

        categories = data.get("categories", {}) or {}

        # 规范化：允许 categories 值为字符串列表
        norm_categories: Dict[str, List[str]] = {}
        for cat, values in categories.items():
            if isinstance(values, list):
                # items 可以是字符串或带 name 的对象
                items: List[str] = []
                for v in values:
                    if isinstance(v, str):
                        items.append(v)
                    elif isinstance(v, dict) and "name" in v:
                        items.append(str(v["name"]))
                norm_categories[cat] = items

        subjects_raw = data.get("subjects", []) or []
        subjects: List[SubjectPlan] = []
        for s in subjects_raw:
            if isinstance(s, dict) and "name" in s:
                subjects.append(
                    SubjectPlan(name=str(s["name"]), use_categories=s.get("use_categories"))
                )

        overrides = data.get("overrides", {}) or {}
        # 规范化 overrides 为 Dict[str, Dict[str, List[str]]]
        norm_overrides: Dict[str, Dict[str, List[str]]] = {}
        for subj, cats in overrides.items():
            norm_overrides[subj] = {}
            for cat, vals in (cats or {}).items():
                if isinstance(vals, list):
                    norm_overrides[subj][cat] = [str(v["name"]) if isinstance(v, dict) and "name" in v else str(v) for v in vals]

        return PromptPlan(
            global_cfg=global_cfg,
            categories=norm_categories,
            subjects=subjects,
            overrides=norm_overrides,
        )


def load_prompt_plan(plan_file: Path | str) -> PromptPlan:
    path = Path(plan_file)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return PromptPlan.from_dict(data)


def generate_prompts_from_plan(plan: PromptPlan) -> List[str]:
    """根据计划生成提示词列表（主提示词 + 分类笛卡尔积）。"""
    prompts: List[str] = []

    # 计算全局拼接顺序
    global_order = plan.global_cfg.order or list(plan.categories.keys())

    for subject in plan.subjects:
        subject_name = subject.name.strip()
        if not subject_name:
            continue

        # 本主题使用的分类顺序
        category_order = subject.use_categories or global_order

        # 为每个分类获取可用选项（优先 overrides）
        category_values: List[List[str]] = []
        for cat in category_order:
            # 可选分类：如果该分类在 categories 中不存在，跳过
            base_vals = plan.categories.get(cat, [])
            override_vals = plan.overrides.get(subject_name, {}).get(cat)
            vals = override_vals if override_vals is not None else base_vals
            vals = [v for v in (vals or []) if isinstance(v, str) and v.strip()]
            if vals:
                category_values.append(vals)

        # 如果没有任何分类值，提示词就是主提示词
        if not category_values:
            prompts.append(subject_name)
            continue

        # 做笛卡尔积
        joiner = plan.global_cfg.joiner
        max_combos = plan.global_cfg.max_combinations

        count = 0
        for combo in itertools.product(*category_values):
            aux = [part for part in combo if part]
            final_prompt = joiner.join([subject_name] + aux) if aux else subject_name
            prompts.append(final_prompt)
            count += 1
            if max_combos is not None and count >= max_combos:
                break

    return prompts


