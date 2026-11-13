#!/usr/bin/env python3
"""T3 제공자 캐시에서 남은 사용량을 읽어 Codex 계정 순위와 Claude 사용량을 JSON으로 출력한다.

사용: python3 pick-provider.py [병렬 위임 수]
출력: {codex: [순위순 계정], assign: [위임별 계정], claude: {...}, warnings: [...]}
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

CACHE = os.path.expanduser("~/.t3/caches")
FULL_AT = 90      # 이 이상 쓴 계정은 다른 계정이 있으면 제외
STALE_HOURS = 6   # 사용량 확인 시각이 이보다 오래되면 경고
CLAUDE_HIGH = 80  # Claude 주간 사용량이 이 이상이면 실행을 Codex로 넘길 것을 권고


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    now = datetime.now(timezone.utc)
    codex, claude, warnings = [], None, []

    for path in sorted(glob.glob(os.path.join(CACHE, "*.json"))):
        try:
            d = json.load(open(path))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not d.get("enabled") or d.get("status") != "ready":
            continue
        if (d.get("auth") or {}).get("status") != "authenticated":
            continue
        limits = d.get("usageLimits") or {}
        windows = limits.get("windows") or []
        checked = parse(limits.get("checkedAt"))
        instance = d.get("instanceId") or os.path.basename(path)[:-5]
        if checked is None or not windows:
            warnings.append(f"{instance}: 사용량 정보 없음")
        elif (now - checked).total_seconds() > STALE_HOURS * 3600:
            warnings.append(f"{instance}: 사용량 확인이 {int((now - checked).total_seconds() // 3600)}시간 전")

        if d.get("driver") == "codex":
            # 창이 여러 개면 가장 많이 쓴 창이 그 계정의 한도다.
            used = max((w.get("usedPercent", 0) for w in windows), default=None)
            tight = max(windows, key=lambda w: w.get("usedPercent", 0)) if windows else {}
            codex.append({
                "providerInstanceId": instance,
                "usedPercent": used,
                "remainingPercent": None if used is None else 100 - used,
                "resetsAt": tight.get("resetsAt"),
                "resetCredits": (limits.get("resetCredits") or {}).get("availableCount", 0),
            })
        elif d.get("driver") == "claudeAgent":
            claude = {
                "windows": [{"id": w.get("id"), "usedPercent": w.get("usedPercent"), "resetsAt": w.get("resetsAt")} for w in windows],
            }
            worst = max((w.get("usedPercent", 0) for w in windows), default=0)
            claude["preferCodexForExecution"] = worst >= CLAUDE_HIGH

    # 남은 사용량이 많은 순. 같으면 먼저 초기화되는 계정을 먼저 쓴다.
    known = [c for c in codex if c["remainingPercent"] is not None]
    known.sort(key=lambda c: (-c["remainingPercent"], c["resetsAt"] or ""))
    usable = [c for c in known if c["usedPercent"] < FULL_AT]
    if known and not usable:
        # 모두 한도에 가까우면 아직 남은 계정만 쓴다. 100%인 계정은 쓸 수 없다.
        usable = [c for c in known if c["usedPercent"] < 100]
        if usable:
            warnings.append(f"모든 Codex 계정이 {FULL_AT}% 이상 사용됨")
    if len(usable) < len(known):
        warnings.append("제외한 계정: " + ", ".join(c["providerInstanceId"] for c in known if c not in usable))
    if not usable:
        warnings.append("쓸 수 있는 Codex 계정이 없음")

    # 병렬 위임은 남은 사용량 비율대로 나눈다(가장 많이 남은 계정부터).
    assign = []
    if usable:
        left = {c["providerInstanceId"]: float(c["remainingPercent"]) for c in usable}
        step = max(1.0, sum(left.values()) / max(n, 1) / 2)
        for _ in range(n):
            pick = max(left, key=lambda k: left[k])
            assign.append(pick)
            left[pick] -= step

    print(json.dumps({"codex": usable, "assign": assign, "claude": claude, "warnings": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
