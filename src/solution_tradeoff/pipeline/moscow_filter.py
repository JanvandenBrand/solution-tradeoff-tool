"""MoSCoWFilter — filters and splits requirements by MoSCoW level.

Pure function — no I/O, no side effects.
"""

from typing import Any

_EXCLUDED_STATUSES = {"deprecated", "rejected"}


class MoSCoWFilter:
    """Filters requirement rows by MoSCoW level, status, domain, and plateau."""

    def run(
        self,
        rows: list[dict[str, Any]],
        filter_config: dict[str, Any],
        plateau: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (must_requirements, should_requirements).

        Args:
            rows: Raw requirement dicts as loaded by RequirementsLoader.
            filter_config: The 'requirements_filter' block from decision.yaml.
                           Keys: 'domains' (list[str]), 'moscow' (list[str]).
            plateau: If set, exclude rows whose plateau value exceeds this.

        Returns:
            Tuple of (must_rows, should_rows), each sorted by req_id.
        """
        domain_filter = [d.lower() for d in (filter_config.get("domains") or [])]
        moscow_filter = [m.lower() for m in (filter_config.get("moscow") or ["must", "should"])]

        filtered: list[dict[str, Any]] = []
        for row in rows:
            status = (row.get("status") or "").strip().lower()
            if status in _EXCLUDED_STATUSES:
                continue

            if domain_filter:
                domain = (row.get("domain") or "").strip().lower()
                if domain not in domain_filter:
                    continue

            moscow = (row.get("moscow") or "").strip().lower()
            if moscow not in moscow_filter:
                continue

            if plateau is not None:
                plateau_val = row.get("plateau")
                if plateau_val is not None and plateau_val != "":
                    try:
                        if int(plateau_val) > plateau:
                            continue
                    except (ValueError, TypeError):
                        pass

            filtered.append(row)

        filtered.sort(key=lambda r: str(r.get("req_id") or ""))

        must = [r for r in filtered if (r.get("moscow") or "").strip().lower() == "must"]
        should = [r for r in filtered if (r.get("moscow") or "").strip().lower() == "should"]
        return must, should
