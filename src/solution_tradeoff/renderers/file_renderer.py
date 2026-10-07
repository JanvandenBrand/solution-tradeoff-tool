"""FileRenderer — writes prompt files, manifest, and review checklist to disk."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FileRenderer:
    """Writes all output files for a build-prompts run.

    Args:
        output_root: Root directory under which {decision_id}/ is created.
        config: The parsed config.yaml dict (must contain 'output' section).
    """

    def __init__(self, output_root: Path, config: dict[str, Any]) -> None:
        self._output_root = output_root
        self._cfg = config

    def write(
        self,
        decision_id: str,
        decision_name: str,
        candidates: list[dict[str, Any]],
        context_block: str,
        perspective_prompts: list[tuple[dict[str, Any], str]],
        synthesis_prompt: str,
        compile_prompt: str,
        must_reqs: list[dict[str, Any]],
        should_reqs: list[dict[str, Any]],
        principles: list[dict[str, Any]],
        perspective_objects: list[dict[str, Any]],
        point_budget: int,
        criteria_count: int,
        force: bool = False,
        problem_statement: str = "",
        planning_horizon: str = "",
        plateau: int | None = None,
    ) -> Path:
        """Write all output files and return the output directory path.

        Args:
            decision_id: e.g. 'AD-069'.
            decision_name: Human-readable decision name.
            candidates: List of candidate dicts.
            context_block: Pre-rendered context block Markdown.
            perspective_prompts: List of (perspective_dict, prompt_str) tuples.
            synthesis_prompt: Rendered synthesis prompt Markdown.
            must_reqs: Filtered Must requirement rows.
            should_reqs: Filtered Should requirement rows.
            principles: Principle rows.
            perspective_objects: Perspective dicts (same as first element of each tuple).
            point_budget: Budget per agent.
            criteria_count: Total Must + Should count.
            force: If False, existing directory is overwritten silently (idempotent).

        Returns:
            Path to the output directory (output_root / decision_id).
        """
        out_cfg = self._cfg["output"]
        out_dir = self._output_root / decision_id
        agents_dir = out_dir / "agents"
        if agents_dir.exists():
            shutil.rmtree(agents_dir)
        agents_dir.mkdir(parents=True)

        # Context block
        context_path = agents_dir / out_cfg["context_filename"]
        context_path.write_text(context_block, encoding="utf-8")

        agent_entries: list[dict[str, Any]] = [
            {
                "index": 0,
                "id": "context",
                "label": "Context Block",
                "file": f"agents/{out_cfg['context_filename']}",
                "type": "context",
            }
        ]

        # Perspective prompts
        for perspective, prompt in perspective_prompts:
            fname = out_cfg["agent_filename_pattern"].format(
                index=perspective["index"], perspective=perspective["id"]
            )
            (agents_dir / fname).write_text(prompt, encoding="utf-8")
            agent_entries.append(
                {
                    "index": perspective["index"],
                    "id": perspective["id"],
                    "label": perspective["label"],
                    "file": f"agents/{fname}",
                    "type": "perspective",
                }
            )

        # Synthesis prompt — numbered after the highest perspective index
        max_idx = max((p["index"] for p, _ in perspective_prompts), default=0)
        n = max_idx + 1
        synthesis_fname = out_cfg["synthesis_filename"].format(N=f"{n:02d}")
        (agents_dir / synthesis_fname).write_text(synthesis_prompt, encoding="utf-8")
        agent_entries.append(
            {
                "index": n,
                "id": "synthesis",
                "label": "Synthesis Agent",
                "file": f"agents/{synthesis_fname}",
                "type": "synthesis",
            }
        )

        # Manifest
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest = {
            "decision_id": decision_id,
            "decision_name": decision_name,
            "generated_at": timestamp,
            "candidates": candidates,
            "point_budget": point_budget,
            "criteria_count": criteria_count,
            "must_count": len(must_reqs),
            "should_count": len(should_reqs),
            "agents": agent_entries,
        }
        manifest_path = out_dir / out_cfg["manifest_filename"]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Compile prompt
        compile_path = out_dir / out_cfg["compile_filename"]
        compile_path.write_text(compile_prompt, encoding="utf-8")

        # Build review entries in original format: context has no "agents/" prefix
        review_entries = [{"file": out_cfg["context_filename"]}]
        review_entries += [{"file": e["file"]} for e in agent_entries[1:]]

        # Review checklist
        review_content = _build_review_md(
            decision_id=decision_id,
            decision_name=decision_name,
            candidates=candidates,
            must_reqs=must_reqs,
            should_reqs=should_reqs,
            principles=principles,
            perspective_objects=perspective_objects,
            point_budget=point_budget,
            criteria_count=criteria_count,
            out_dir_rel=str(out_dir),
            agent_entries=review_entries,
            timestamp=timestamp,
            problem_statement=problem_statement,
            planning_horizon=planning_horizon,
            plateau=plateau,
        )
        review_path = out_dir / out_cfg["review_filename"]
        review_path.write_text(review_content, encoding="utf-8")

        return out_dir


def _build_review_md(
    decision_id: str,
    decision_name: str,
    candidates: list[dict[str, Any]],
    must_reqs: list[dict[str, Any]],
    should_reqs: list[dict[str, Any]],
    principles: list[dict[str, Any]],
    perspective_objects: list[dict[str, Any]],
    point_budget: int,
    criteria_count: int,
    out_dir_rel: str,
    agent_entries: list[dict[str, Any]],
    timestamp: str,
    problem_statement: str = "",
    planning_horizon: str = "",
    plateau: "int | None" = None,
) -> str:
    """Build the review.md checklist content."""

    def table(headers: list[str], rows: list[list[str]]) -> str:
        sep = " | ".join("---" for _ in headers)
        head = " | ".join(headers)
        lines = [f"| {head} |", f"| {sep} |"]
        for row in rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
        return "\n".join(lines)

    cand_table = table(
        ["ID", "Name"],
        [[c["id"], c["name"]] for c in candidates],
    )

    reqs_rows = [
        [r["req_id"], r["description"], r["domain"], r["moscow"]] for r in must_reqs + should_reqs
    ]
    reqs_table = (
        table(["Req ID", "Description", "Domain", "MoSCoW"], reqs_rows) if reqs_rows else "_None_"
    )

    pri_rows = [[p["principle_id"], p["description"]] for p in principles]
    pri_table = table(["Principle ID", "Description"], pri_rows) if pri_rows else "_None_"

    persp_rows = [
        [p["index"], p["id"], p["label"], f"agents/{p['id']}.md"] for p in perspective_objects
    ]
    persp_table = table(["Index", "ID", "Label", "File"], persp_rows)

    files_list = "\n".join(f"- `{e['file']}`" for e in agent_entries)

    plateau_val = plateau or "none"

    return f"""# Trade-Off Prompt Package — Review Checklist
**Decision**: {decision_id} — {decision_name}
**Generated**: {timestamp}

## 1. Decision context (verify before proceeding)
- [ ] Decision ID is correct: {decision_id}
- [ ] Problem statement is accurate: "{problem_statement}"
- [ ] Planning horizon is correct: {planning_horizon}
- [ ] Plateau filter applied: {plateau_val}

## 2. Candidates (verify all are present and correctly named)
{cand_table}

## 3. Requirements included ({len(must_reqs)} Must, {len(should_reqs)} Should)
{reqs_table}

## 4. Principles included ({len(principles)})
{pri_table}

## 5. Perspectives selected ({len(perspective_objects)})
{persp_table}

## 6. Point budget
- Criteria count: {criteria_count}
- Budget per agent: {point_budget} points

## 7. Output files
{files_list}

---
> If all boxes above are checked, the package is ready for the multi-agent run.
> Edit decision.yaml and re-run the script to correct any errors.
"""
