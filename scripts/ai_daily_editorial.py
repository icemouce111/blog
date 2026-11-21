"""Keep project intent shared by candidate ordering and editorial instructions."""
from __future__ import annotations

import json
from pathlib import Path


PROFILE_PATH = "src/data/ai-daily-editorial.json"


def load_profile(root: Path) -> dict:
    profile = json.loads((Path(root) / PROFILE_PATH).read_text(encoding="utf-8"))
    if profile.get("schemaVersion") != 1 or not profile.get("missions"):
        raise ValueError("Unsupported or empty AI daily editorial profile")
    return profile


def editorial_context(profile: dict) -> str:
    lines = ["本日报服务读者正在积累的三类长期资产："]
    for mission in profile["missions"]:
        lines.append(f"- {mission['name']}：{mission['purpose']}")
    lines.append("输入分类的编辑优先级（不是成稿栏目或条数配额）：")
    for category in sorted(profile["categories"].values(), key=lambda item: item["priority"], reverse=True):
        lines.append(f"- {category['name']}：{category['guidance']}")
    lines.extend(f"- {rule}" for rule in profile["selectionRules"])
    lines.append("项目匹配标签只是候选提示，最终仍须判断语义、证据和读者价值。")
    return "\n".join(lines)


def prioritize_items(items, profile: dict):
    """Stable ordering hints; unmatched material is not automatically rejected."""
    for item in items:
        text = f"{item.title}\n{item.summary}".casefold()
        item.metadata["editorial_matches"] = [
            mission["name"] for mission in profile["missions"]
            if any(topic.casefold() in text for topic in mission["topics"])
        ]

    def priority(item):
        matches = item.metadata["editorial_matches"]
        category = profile["categories"].get(item.metadata.get("aihot_category"), {})
        score = item.metadata.get("aihot_score", 0)
        score = score if type(score) in (int, float) else 0
        return bool(matches), len(matches), category.get("priority", 0), score

    return sorted(items, key=priority, reverse=True)
