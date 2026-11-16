"""Deterministic executor, model and account suggestions (P6)."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .core import GFError


def load_routing(path=None):
    """Read and validate the user-editable routing table."""
    path = Path(path) if path is not None else Path(__file__).resolve().parents[2] / "routing.json"
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(table, dict) and table["schema_version"] == 1
        assert table["default_family"] in ("claude", "openai")
        efforts = table["efforts"]
        assert isinstance(efforts, list) and efforts and len(set(efforts)) == len(efforts)
        assert all(isinstance(e, str) and e for e in efforts)
        for family in ("claude", "openai"):
            ladder = table["ladders"][family]
            assert isinstance(ladder, list) and ladder and len(set(ladder)) == len(ladder)
            assert all(isinstance(m, str) and m for m in ladder)
            for grade in ("bulk", "scoped", "daily", "large", "security"):
                entry = table["grades"][grade][family]
                assert entry["model"] in ladder and entry["effort"] in efforts
        assert isinstance(table["effort_caps"], dict)
        for model, cap in table["effort_caps"].items():
            assert any(model in ladder for ladder in table["ladders"].values()) and cap in efforts
        for key in ("provider_full_at", "usage_stale_hours", "prefer_other_family_at"):
            value = table["thresholds"][key]
            assert _number(value) and value >= 0
        return table
    except (OSError, ValueError, TypeError, KeyError, AssertionError, UnicodeError) as exc:
        raise GFError("bad_routing", "Cannot load routing table: %s" % exc) from exc


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def load_usage(cache_dir=None):
    """Read eligible host cache entries without changing cache contents."""
    directory = Path(cache_dir) if cache_dir is not None else Path.home() / ".t3" / "caches"
    if not directory.exists():
        return {}
    result = {"providers": [], "warnings": []}
    now = datetime.now(timezone.utc)
    stale_hours = load_routing()["thresholds"]["usage_stale_hours"]
    try:
        paths = sorted(directory.glob("*.json"))
    except OSError as exc:
        result["warnings"].append("Cannot read usage cache: %s" % exc)
        return result
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("cache entry must be an object")
            if not data.get("enabled") or data.get("status") != "ready":
                continue
            if (data.get("auth") or {}).get("status") != "authenticated":
                continue
            limits = data.get("usageLimits") or {}
            windows = limits.get("windows") or []
            if not isinstance(windows, list):
                raise ValueError("windows must be a list")
            values = [w.get("usedPercent", 0) for w in windows]
            if not all(_number(v) for v in values):
                raise ValueError("usedPercent must be numeric")
            checked_at = limits.get("checkedAt")
            checked = datetime.fromisoformat(checked_at.replace("Z", "+00:00")) if checked_at else None
            if checked is not None and checked.tzinfo is None:
                raise ValueError("checkedAt must include a timezone")
            stale = checked is None or not windows or (now - checked).total_seconds() > stale_hours * 3600
            instance = data.get("instanceId") or path.stem
            if not isinstance(instance, str):
                raise ValueError("instanceId must be a string")
            if stale:
                result["warnings"].append("%s: usage is missing or stale" % instance)
            result["providers"].append({
                "provider": instance,
                "family": {"codex": "openai", "claudeAgent": "claude"}.get(data.get("driver"), "other"),
                "used_percent": max(values) if values else None,
                "checked_at": checked_at,
                "stale": stale,
            })
        except (OSError, ValueError, TypeError, AttributeError, UnicodeError) as exc:
            result["warnings"].append("%s: malformed usage cache (%s)" % (path.name, exc))
    return result


def suggest(node, node_state, host, usage, routing):
    """Suggest a route from explicit inputs only; never mutate them."""
    grade = node.get("grade") or "daily"
    state = node_state or {}
    review = node.get("kind") == "review"
    default = routing["default_family"]
    family = default
    other = "openai" if default == "claude" else "claude"
    providers = (usage or {}).get("providers", [])
    full = routing["thresholds"]["provider_full_at"]
    why = ["grade %s" % grade]
    if review:
        target = state.get("target_family")
        if target in ("claude", "openai"):
            family = "openai" if target == "claude" else "claude"
            why.append("review uses a different family from its target")
        else:
            why.append("target family unknown; using default family")
    else:
        own = [p for p in providers if p["family"] == default]
        if (own and all(not p["stale"] and _number(p["used_percent"]) and
                        p["used_percent"] >= routing["thresholds"]["prefer_other_family_at"] for p in own)
                and any(p["family"] == other and not p["stale"] and _number(p["used_percent"])
                        and p["used_percent"] < full for p in providers)):
            family = other
            why.append("default family usage is high")
        else:
            why.append("using default family")
    model = routing["grades"][grade][family]["model"]
    effort = routing["grades"][grade][family]["effort"]
    rejections = state.get("rejections", [])
    if rejections:
        ladder = routing["ladders"][family]
        efforts = routing["efforts"]
        approach = rejections[-1].get("reason", "").startswith("approach:")
        cap = routing["effort_caps"].get(model, efforts[-1])
        if not approach and efforts.index(effort) < efforts.index(cap):
            effort = efforts[efforts.index(effort) + 1]
            why.append("rejection raises effort")
        elif ladder.index(model) < len(ladder) - 1:
            model = ladder[ladder.index(model) + 1]
            effort = "medium"
            why.append("approach rejection raises model" if approach else "effort cap raises model")
        else:
            why.append("at the top of the ladder")
    eligible = [p for p in providers if p["family"] == family and not p["stale"]
                and _number(p["used_percent"]) and p["used_percent"] < full]
    provider = min(eligible, key=lambda p: (p["used_percent"], p["provider"]))["provider"] if eligible else None
    why.append("lowest eligible provider usage" if eligible else
               "usage missing; no provider selected" if not usage else "no eligible provider")
    isolation = "worktree" if node.get("kind") == "work" and "worktree" in host else "shared"
    if "t3_delegate" in host and (family != default or review or grade in ("large", "security")):
        executor = "t3"
    elif "workflow" in host and grade == "bulk":
        executor = "workflow"
    elif "subagent" in host:
        executor = "subagent"
    elif "t3_delegate" in host:
        executor = "t3"
    else:
        executor = "inline"
    why.append("%s executor; %s isolation" % (executor, isolation))
    return dict(executor=executor, model=model, effort=effort, provider=provider,
                family=family, isolation=isolation, why="; ".join(why) + ".")
