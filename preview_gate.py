#!/usr/bin/env python3
"""Shared baw preview gate — the ONE implementation every snipe/claim driver must use.

Born from three gate failures with the same root cause (a gate that was never
tested against the real shape of a successful preview):
- DrawFish round 1 (2026-11-04): `risks` dict judged by truthiness -> clean previews rejected.
- PEARL snipe (2026-11-05): simulationCode "000000000" misread as failure -> clean previews skipped.
- ASOC snipe (2026-11-05): balanceChanges `change` arrived as the string "5.555e+21"
  and int() raised -> clean previews rejected 4x per wallet while the quota sold out.
  Proof the format varies was already on disk: PACTURE ACC previews return change as
  float 7e+24, AMBER previews return it as a plain JSON int.

Rules implemented here (do not re-implement elsewhere):
- Amounts are parsed with Decimal(str(value)) so int, float (7e+24), plain integer
  strings and scientific-notation strings ("5.555e+21") all parse exactly.
  A parse problem must NEVER be the silent reason a success=true preview is rejected;
  if an amount cannot be parsed, the gate fails LOUDLY with that reason.
- simulationCode "000000000" means SUCCESS (any all-zero rendering counts).
- `risks` is a dict {addresses, riskDetails, riskBehaviors}: clean iff riskDetails
  AND riskBehaviors are both empty, checked at simulationResult level AND data level.
- balanceChanges live at data.simulationResult.balanceChanges, amount field "change".
- Clean = success true, code success, no simulation error detail, risks clean,
  authorityChanges empty, allowanceChanges empty (unless caller allows), and the
  parsed balance changes match the expected movements EXACTLY (nothing extra, nothing out).

CLI:
  python3 preview_gate.py PREVIEW_JSON EXPECTED_JSON
  EXPECTED_JSON: {"changes": [{"contract": "0x..", "change": "12345" or 12345, "owner": "0x.." (optional)}],
                  "allow_allowance_changes": false}
  Prints one JSON line: {"ok": bool, "reasons": [...], "parsed_changes": [...]}
  Exit code 0 when ok, 1 when rejected, 2 on usage/IO error.
Self-test (regression suite over real captured previews):
  python3 preview_gate.py --selftest
"""
import json
import sys
from decimal import Decimal, InvalidOperation


def parse_amount(value):
    """Parse a baw amount in any of its observed renderings into an exact Decimal.

    Accepts int, float (7e+24), "5555000000000000000000", "5.555e+21".
    Raises ValueError on anything else — callers must treat that as a LOUD gate failure.
    """
    if isinstance(value, bool):
        raise ValueError("boolean is not an amount")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # str(float) gives the shortest repr ("7e+24", "5.555e+21") which Decimal reads exactly.
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if s.startswith("+"):
            s = s[1:]
        try:
            return Decimal(s)
        except InvalidOperation:
            raise ValueError("unparseable amount string: %r" % value)
    raise ValueError("unsupported amount type: %r" % type(value).__name__)


def _code_is_success(code):
    if code is None:
        return False
    try:
        return parse_amount(code) == 0
    except ValueError:
        return str(code).strip() == "000000000"


def _empty(x):
    return x is None or x == "" or x == [] or x == {}


def _risks_clean(risks):
    """Return (seen, clean). seen=False when risks is absent/not a dict at this level."""
    if not isinstance(risks, dict):
        return False, True
    details = risks.get("riskDetails") or []
    behaviors = risks.get("riskBehaviors") or []
    return True, (len(details) == 0 and len(behaviors) == 0)


def check_preview(preview, expected_changes, allow_allowance_changes=False):
    """Return (ok, reasons, parsed_changes). expected_changes: list of dicts
    {contract, change, owner?} — the EXACT set of balance movements allowed."""
    reasons = []
    if not isinstance(preview, dict):
        return False, ["preview is not a JSON object"], []
    if preview.get("success") is not True:
        err = preview.get("error")
        reasons.append("success != true (error: %s)" % (json.dumps(err)[:200] if err else "none"))

    data = preview.get("data") if isinstance(preview.get("data"), dict) else {}
    sr = data.get("simulationResult") or preview.get("simulationResult") or {}
    if not isinstance(sr, dict):
        sr = {}

    if not _code_is_success(sr.get("simulationCode")):
        reasons.append("simulationCode is not success: %r" % sr.get("simulationCode"))
    if not _empty(sr.get("simulationErrorDetail")):
        reasons.append("simulationErrorDetail not empty: %r" % str(sr.get("simulationErrorDetail"))[:200])

    seen_risks = False
    for level_name, holder in (("simulationResult", sr), ("data", data)):
        seen, clean = _risks_clean(holder.get("risks"))
        if seen:
            seen_risks = True
            if not clean:
                reasons.append("risks not clean at %s level" % level_name)
    if not seen_risks:
        reasons.append("risks object not found at either level")

    if not _empty(sr.get("authorityChanges")):
        reasons.append("authorityChanges not empty")
    if not allow_allowance_changes and not _empty(sr.get("allowanceChanges")):
        reasons.append("allowanceChanges not empty")

    raw_changes = sr.get("balanceChanges")
    parsed = []
    if raw_changes is None:
        reasons.append("balanceChanges missing")
    else:
        for entry in raw_changes:
            try:
                amt = parse_amount(entry.get("change"))
            except ValueError as e:
                reasons.append("balanceChanges amount unparseable: %s" % e)
                continue
            parsed.append({
                "contract": str(entry.get("contractAddress") or "").lower(),
                "change": amt,
                "owner": str(entry.get("owner") or "").lower(),
            })

    expected = []
    for e in expected_changes:
        expected.append({
            "contract": str(e.get("contract") or "").lower(),
            "change": parse_amount(e.get("change")),
            "owner": str(e.get("owner") or "").lower(),
        })

    def key(c):
        return (c["contract"], c["change"], c["owner"])

    if not reasons:
        # Only compare movements when the rest of the gate is clean, so the
        # failure reason stays precise.
        exp_sorted = sorted(expected, key=key)
        got_sorted = sorted(parsed, key=key)
        if len(exp_sorted) != len(got_sorted):
            reasons.append("balanceChanges count mismatch: expected %d, got %d"
                           % (len(exp_sorted), len(got_sorted)))
        else:
            for exp, got in zip(exp_sorted, got_sorted):
                if exp["contract"] != got["contract"] or exp["change"] != got["change"]:
                    reasons.append("balanceChanges mismatch: expected %s %+s, got %s %+s"
                                   % (exp["contract"], exp["change"], got["contract"], got["change"]))
                    break
                if exp["owner"] and got["owner"] and exp["owner"] != got["owner"]:
                    reasons.append("balanceChanges owner mismatch")
                    break

    return (len(reasons) == 0), reasons, parsed


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def selftest():
    import copy
    import os
    base = os.path.expanduser("~/workspace")
    cases = []

    amber = _load(os.path.join(base, "amber/preview-day2-cashier.json"))
    cases.append(("AMBER clean preview (int change) must PASS", amber,
                  [{"contract": "0x4008a353d3476884DC8Cd8fBf314970C8409FB22",
                    "change": "9560159289",
                    "owner": "0x7ab7cB03fA3e2019d0c60D6485C7D43Fa4812dd2"}], True))

    pact = _load(os.path.join(base, "pacture/prev2_acc_cashier.json"))
    cases.append(("PACTURE ACC clean preview (float 7e+24 change) must PASS", pact,
                  [{"contract": "0xeEB4E27bCf62e257920cB573eb8ca14392C62637",
                    "change": "7000000000000000000000000"}], True))

    asoc_shape = copy.deepcopy(amber)
    sr = asoc_shape["data"]["simulationResult"]
    sr["balanceChanges"] = [{"contractAddress": "0x43cEef9313CB8c4ca3757bA841C44DF40A223205",
                             "change": "5.555e+21",
                             "owner": "0x7ab7cB03fA3e2019d0c60D6485C7D43Fa4812dd2",
                             "tokenType": "Erc20", "tokenId": None}]
    cases.append(("ASOC-shaped clean preview (string '5.555e+21' change) must PASS", asoc_shape,
                  [{"contract": "0x43cEef9313CB8c4ca3757bA841C44DF40A223205",
                    "change": "5555000000000000000000"}], True))

    dry = _load(os.path.join(base, "asoc/prev_dryrun_cashier.json"))
    cases.append(("ASOC pre-open dry-run (success=false) must REJECT", dry,
                  [{"contract": "0x43cEef9313CB8c4ca3757bA841C44DF40A223205",
                    "change": "5555000000000000000000"}], False))

    dirty = copy.deepcopy(amber)
    dirty["data"]["risks"] = {"addresses": {}, "riskDetails": [{"x": 1}], "riskBehaviors": []}
    cases.append(("Tampered preview (riskDetails non-empty) must REJECT", dirty,
                  [{"contract": "0x4008a353d3476884DC8Cd8fBf314970C8409FB22",
                    "change": "9560159289"}], False))

    outflow = copy.deepcopy(amber)
    outflow["data"]["simulationResult"]["balanceChanges"].append(
        {"contractAddress": "0x4008a353d3476884DC8Cd8fBf314970C8409FB22",
         "change": "-100", "owner": "0x7ab7cB03fA3e2019d0c60D6485C7D43Fa4812dd2",
         "tokenType": "Erc20", "tokenId": None})
    cases.append(("Tampered preview (extra outflow) must REJECT", outflow,
                  [{"contract": "0x4008a353d3476884DC8Cd8fBf314970C8409FB22",
                    "change": "9560159289"}], False))

    all_ok = True
    for name, preview, expected, want in cases:
        ok, reasons, _ = check_preview(preview, expected)
        verdict = "OK " if ok == want else "FAIL"
        if ok != want:
            all_ok = False
        print("%s %s -> gate=%s (want %s) reasons=%s" % (verdict, name, ok, want, reasons))
    print("SELFTEST", "PASSED" if all_ok else "FAILED")
    return 0 if all_ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 3:
        print(__doc__)
        return 2
    preview = _load(argv[1])
    spec = _load(argv[2])
    ok, reasons, parsed = check_preview(
        preview, spec.get("changes", []),
        allow_allowance_changes=bool(spec.get("allow_allowance_changes", False)))
    print(json.dumps({"ok": ok, "reasons": reasons,
                      "parsed_changes": [{"contract": p["contract"],
                                          "change": str(p["change"]),
                                          "owner": p["owner"]} for p in parsed]}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
