"""
iOS Software Factory – Entry Point
====================================
Run:  python -m ios_factory.main
  or: crewai run

Flow:
  Step 0  GoNoGoCrew   → scores Idea Brightness & Market Opportunity → GO / NO-GO
  Step 1  market_researcher  → competitor analysis + market gaps
  Step 2  app_store_copywriter → title / subtitle / description
  Step 3  aso_specialist     → keywords + A/B variants
  Step 4  legal_reviewer     → compliance-checked final listing
"""

import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (works regardless of cwd or launch method)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from ios_factory.crew import GoNoGoCrew, iOSFactoryCrew

ROOT = Path(__file__).resolve().parents[2]
IOS_PROJECT = ROOT / "CrewAITest" / "CrewAITest"
IOS_TESTS   = ROOT / "CrewAITest" / "CrewAITestTests"

# ── Scoring thresholds (market-first, 4-tier framework) ─────────────────────
# Market Opportunity carries more weight: you can pivot an idea, not a market.
_W_OPP = 0.6   # weight for Market Opportunity
_W_BRI = 0.4   # weight for Idea Brightness
#
# Tier rules (evaluated top-down):
#   STRONG GO        : both dims ≥ 8.0
#   GO               : both dims ≥ 7.0  OR  (one ≥ 8.0 AND other ≥ 6.0)
#   CONDITIONAL GO   : weighted ≥ 6.5  AND  both dims ≥ 5.0
#   NO-GO            : either dim ≤ 4.0  OR  weighted < 6.5
_FLOOR_STRONG   = 8.0
_FLOOR_GO_BOTH  = 7.0
_FLOOR_GO_ASYM_HIGH = 8.0   # asymmetric GO: one dim at this…
_FLOOR_GO_ASYM_LOW  = 6.0   # …other dim at least this
_FLOOR_COND_W   = 6.5   # weighted score floor for CONDITIONAL GO
_FLOOR_COND_EACH = 5.0  # each dim floor for CONDITIONAL GO
# ─────────────────────────────────────────────────────────────────────────────


def _extract_swift_files(md_file: Path, target_dir: Path) -> list[Path]:
    """Parse fenced ```swift blocks with // FILE: <name> and write to target_dir."""
    if not md_file.exists():
        return []

    content = md_file.read_text(encoding="utf-8")
    pattern = re.compile(
        r"```swift[^\n]*\n"
        r"(?://\s*filepath:[^\n]*\n)?"
        r"//\s*FILE:\s*([^\n]+)\n"
        r"(.*?)"
        r"```",
        re.DOTALL,
    )

    written: list[Path] = []
    for filename, code in pattern.findall(content):
        filename = filename.strip()
        dest = target_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code.rstrip() + "\n", encoding="utf-8")
        written.append(dest)
        print(f"   ✍️  Written → {dest.relative_to(ROOT)}")

    return written


def _parse_gonogo_decision(report_path: Path) -> dict:
    """
    Extract scores and decision from output/0_GoNoGo_Decision.md.

    Returns a dict with keys:
        brightness  – float | None
        opportunity – float | None
        weighted    – float | None  (Opportunity×0.6 + Brightness×0.4)
        decision    – "STRONG GO" | "GO" | "CONDITIONAL GO" | "NO-GO" | "UNKNOWN"
        raw         – full file text
    """
    result: dict = {
        "brightness":  None,
        "opportunity": None,
        "weighted":    None,
        "decision":    "UNKNOWN",
        "raw":         "",
    }

    if not report_path.exists():
        return result

    text = report_path.read_text(encoding="utf-8")
    result["raw"] = text

    def _first_float(pattern: str) -> float | None:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

    result["brightness"]  = _first_float(r"IDEA BRIGHTNESS SCORE\s*:\s*([\d.]+)\s*/\s*10")
    result["opportunity"] = _first_float(r"MARKET OPPORTUNITY SCORE\s*:\s*([\d.]+)\s*/\s*10")
    result["weighted"]    = _first_float(r"WEIGHTED SCORE\s*:\s*([\d.]+)\s*/\s*10")

    # Parse the LLM's stated decision (order matters: most specific first)
    if re.search(r"DECISION\s*:\s*STRONG\s*GO", text, re.IGNORECASE):
        result["decision"] = "STRONG GO"
    elif re.search(r"DECISION\s*:\s*CONDITIONAL\s*GO", text, re.IGNORECASE):
        result["decision"] = "CONDITIONAL GO"
    elif re.search(r"DECISION\s*:\s*NO-GO", text, re.IGNORECASE):
        result["decision"] = "NO-GO"
    elif re.search(r"DECISION\s*:\s*GO", text, re.IGNORECASE):
        result["decision"] = "GO"

    # ── Safety net: always re-derive from raw numbers ─────────────────────────
    # The LLM's stated decision is overridden if the numbers tell a different story.
    b = result["brightness"]
    o = result["opportunity"]
    if b is not None and o is not None:
        w = round(b * _W_BRI + o * _W_OPP, 1)
        result["weighted"] = w  # always use computed value as source of truth

        if b <= 4.0 or o <= 4.0 or w < _FLOOR_COND_W:
            result["decision"] = "NO-GO"
        elif b >= _FLOOR_STRONG and o >= _FLOOR_STRONG:
            result["decision"] = "STRONG GO"
        elif (
            (b >= _FLOOR_GO_BOTH and o >= _FLOOR_GO_BOTH)
            or (b >= _FLOOR_GO_ASYM_HIGH and o >= _FLOOR_GO_ASYM_LOW)
            or (o >= _FLOOR_GO_ASYM_HIGH and b >= _FLOOR_GO_ASYM_LOW)
        ):
            result["decision"] = "GO"
        elif w >= _FLOOR_COND_W and b >= _FLOOR_COND_EACH and o >= _FLOOR_COND_EACH:
            result["decision"] = "CONDITIONAL GO"
        else:
            result["decision"] = "NO-GO"

    return result


def _print_gate_summary(data: dict) -> None:
    """Print a formatted 4-tier viability scorecard to stdout."""
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    BGREEN = "\033[92;1m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"

    def score_bar(v: float | None) -> str:
        """Return a colored score string with a mini bar."""
        if v is None:
            return f"{YELLOW}?{RESET}"
        filled = int(round(v))
        bar = "█" * filled + "░" * (10 - filled)
        if v >= 8.0:
            color = BGREEN
        elif v >= 7.0:
            color = GREEN
        elif v >= 5.0:
            color = YELLOW
        else:
            color = RED
        return f"{color}{v:.1f}/10  {bar}{RESET}"

    _TIER_LABELS = {
        "STRONG GO":      f"{BGREEN}🚀  STRONG GO  ✅✅{RESET}",
        "GO":             f"{GREEN}✅  GO{RESET}",
        "CONDITIONAL GO": f"{YELLOW}⚠️   CONDITIONAL GO — pivot the weak leg first{RESET}",
        "NO-GO":          f"{RED}🚫  NO-GO — broken premise, do not build{RESET}",
        "UNKNOWN":        f"{YELLOW}❓  UNKNOWN — re-run the gate{RESET}",
    }

    decision  = data["decision"]
    dec_label = _TIER_LABELS.get(decision, decision)

    print(f"\n{'═' * 64}")
    print(f"  {BOLD}{CYAN}⚖️   IDEA VIABILITY GATE  (market-first, 4-tier){RESET}")
    print(f"{'═' * 64}")
    print(f"  💡  Idea Brightness      {score_bar(data['brightness'])}")
    print(f"  📈  Market Opportunity   {score_bar(data['opportunity'])}")
    print(f"  {DIM}{'─' * 60}{RESET}")
    print(f"  🔢  Weighted Score       {score_bar(data['weighted'])}")
    print(f"      {DIM}(Opportunity × 0.6 + Brightness × 0.4){RESET}")
    print(f"  {DIM}{'─' * 60}{RESET}")
    print(f"  {DIM}STRONG GO ✅✅ both ≥ 8 │ GO ✅ both ≥ 7 or asym 8+6{RESET}")
    print(f"  {DIM}COND. GO ⚠️  weighted ≥ 6.5 & both ≥ 5 │ NO-GO ❌ else{RESET}")
    print(f"  {'─' * 60}")
    print(f"  VERDICT  →  {dec_label}")
    print(f"{'═' * 64}\n")


def run() -> None:
    """Launch the App Store Launch Pipeline with a Go/No-Go gate."""
    user_idea = input(
        "\n🍎  iOS App Store Launch Pipeline\n"
        "─────────────────────────────────────\n"
        "Describe your iOS app idea:\n> "
    )

    if not user_idea.strip():
        print("⚠️  No app idea provided. Exiting.")
        sys.exit(1)

    output_dir = ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    inputs = {"user_idea": user_idea}

    # ── STEP 0: Go/No-Go Gate ─────────────────────────────────────────────────
    print("\n🔍  Step 0 – Evaluating idea viability (Brightness × Market Opportunity)…\n")
    GoNoGoCrew().crew().kickoff(inputs=inputs)

    gate_report = output_dir / "0_GoNoGo_Decision.md"
    gate_data   = _parse_gonogo_decision(gate_report)
    _print_gate_summary(gate_data)

    decision = gate_data["decision"]

    if decision == "NO-GO":
        print("🚫  Pipeline HALTED — fundamental viability issues detected.")
        print("📄  See output/0_GoNoGo_Decision.md for the full breakdown.")
        print("\n💡  Either dim scored ≤ 4, or the Weighted Score is below 6.5.")
        print("    Rethink the core premise before committing any resources.\n")
        sys.exit(0)

    if decision == "CONDITIONAL GO":
        print("⚠️   Pipeline HALTED — one dimension is below conviction threshold.")
        print("📄  See output/0_GoNoGo_Decision.md → PIVOT ADVICE section.")
        print("\n💡  Strengthen the weak leg (see PIVOT ADVICE), then re-run the gate.")
        print("    Do not start building until both dimensions earn a GO.\n")
        sys.exit(0)

    # ── STEPS 1-4: Full App Store Pipeline (STRONG GO or GO) ─────────────────
    label = "🚀  STRONG GO" if decision == "STRONG GO" else "✅  GO"
    print(f"{label} confirmed — launching full App Store pipeline…\n")
    iOSFactoryCrew().crew().kickoff(inputs=inputs)

    print("\n✅  Pipeline Complete!")
    print("═" * 64)
    print("\n📁  Output files:")
    print("   • output/0_GoNoGo_Decision.md  ← Idea viability gate verdict")
    print("   • output/1_Market_Research.md  ← Competitor analysis + gaps")
    print("   • output/2_App_Store_Copy.md   ← Title, subtitle, description")
    print("   • output/3_ASO_Report.md       ← Keywords + A/B variants")
    print("   • output/4_Final_Listing.md    ← Legal-approved final copy")


if __name__ == "__main__":
    run()

