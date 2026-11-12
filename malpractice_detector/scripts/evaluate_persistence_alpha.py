"""
evaluate_persistence_alpha.py
=============================
Isolated synthetic evaluation script comparing TIME_NORM_PERSISTENCE_ALPHA
values: alpha = 0.10 (FairSight production default) vs alpha = 0.20 (proposed alternative).

Evaluates 4 synthetic test scenarios across 10-minute windows (TIME_WINDOW_SEC = 600s):
  Scenario 1: One window with serious violations (e.g. multiple_faces = 60 pts, rest 0)
  Scenario 2: Three consecutive windows with scores of 45 each (rest 0)
  Scenario 3: Repeated moderate violations across an exam
  Scenario 4: Honest candidate with natural movements (3-hour exam, 18 windows, 12 pts each)

Note: All test cases in this script are purely synthetic simulations designed to
rigorously quantify mathematical escalation behavior without altering the production configuration.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.scoring import RiskScorer
import scoring_config as cfg


def run_evaluation():
    print("=" * 80)
    print("FAIRSIGHT WP1: PERSISTENCE FACTOR (ALPHA) COMPARATIVE EVALUATION")
    print("=" * 80)
    print(f"Current Central Config TIME_NORM_PERSISTENCE_ALPHA: {cfg.TIME_NORM_PERSISTENCE_ALPHA}")
    print(f"Risk Bands: Low (0-29), Medium (30-59), High (60-100)")
    print("-" * 80)

    scenarios = [
        {
            "name": "Scenario 1: Acute Serious Violation in Single Window",
            "desc": "Window 0: multiple_faces (60 pts). Windows 1-5 (1 hour total): clean (0 pts).",
            "windows_scores": [60, 0, 0, 0, 0, 0],
            "duration_sec": 3600.0,
        },
        {
            "name": "Scenario 2: Three Consecutive Windows with 45 Pts Each",
            "desc": "Windows 0, 1, 2: 45 pts each (head turn + gaze away + frequency). Windows 3-5: 0 pts.",
            "windows_scores": [45, 45, 45, 0, 0, 0],
            "duration_sec": 3600.0,
        },
        {
            "name": "Scenario 3A: Repeated Moderate Violations (5 Windows x 20 Pts in 2-Hour Exam)",
            "desc": "Windows 0-4: 20 pts each (1 sustained gaze + 1 brief cluster). Windows 5-11: 0 pts.",
            "windows_scores": [20, 20, 20, 20, 20, 0, 0, 0, 0, 0, 0, 0],
            "duration_sec": 7200.0,
        },
        {
            "name": "Scenario 3B: Sustained Moderate Violations (6 Windows x 30 Pts in 1-Hour Exam)",
            "desc": "Windows 0-5: 30 pts each (head turn or frequent glances in every window).",
            "windows_scores": [30, 30, 30, 30, 30, 30],
            "duration_sec": 3600.0,
        },
        {
            "name": "Scenario 4: Honest Candidate Natural Movements (3-Hour Exam, 18 Windows)",
            "desc": "Windows 0-17: 12 pts each (1 natural sustained glance away every 10 minutes).",
            "windows_scores": [12] * 18,
            "duration_sec": 10800.0,
        },
        {
            "name": "Scenario 4B: Honest Candidate with Slight Fidgeting (3-Hour Exam, 18 Windows)",
            "desc": "Windows 0-17: 18 pts each (1 sustained glance + occasional brief glance).",
            "windows_scores": [18] * 18,
            "duration_sec": 10800.0,
        },
    ]

    results = []

    for sc in scenarios:
        w_scores = sc["windows_scores"]
        peak = max(w_scores)
        peak_idx = w_scores.index(peak)
        other_sum = sum(score for idx, score in enumerate(w_scores) if idx != peak_idx)

        # Alpha = 0.10
        score_10 = min(100, round(peak + 0.10 * other_sum))
        level_10 = "High" if score_10 >= 60 else ("Medium" if score_10 >= 30 else "Low")

        # Alpha = 0.20
        score_20 = min(100, round(peak + 0.20 * other_sum))
        level_20 = "High" if score_20 >= 60 else ("Medium" if score_20 >= 30 else "Low")

        results.append({
            "name": sc["name"],
            "desc": sc["desc"],
            "peak": peak,
            "other_sum": other_sum,
            "score_10": score_10,
            "level_10": level_10,
            "score_20": score_20,
            "level_20": level_20,
            "delta": score_20 - score_10,
            "level_changed": level_10 != level_20,
        })

    for r in results:
        print(f"\n{r['name']}")
        print(f"  Description: {r['desc']}")
        print(f"  Window Peak: {r['peak']} | Other Windows Sum: {r['other_sum']}")
        print(f"  alpha = 0.10 -> Score: {r['score_10']:2d}/100 [{r['level_10']}]")
        print(f"  alpha = 0.20 -> Score: {r['score_20']:2d}/100 [{r['level_20']}]")
        print(f"  Delta: +{r['delta']} pts | Risk Band Escalation: {'YES (' + r['level_10'] + ' -> ' + r['level_20'] + ')' if r['level_changed'] else 'NO (Same band)'}")

    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON & TRADE-OFF ANALYSIS:")
    print("=" * 80)
    print("""
1. Acute Malpractice Detection:
   - Scenario 1 (Single severe event): Both alpha=0.10 and alpha=0.20 score 60 (High).
     Alpha does not affect single-window severe detections because other_sum = 0.

2. Persistent Low-to-Moderate Cheating vs Natural Behavior:
   - Scenario 2 (Three consecutive windows with 45 pts):
     * alpha = 0.10 -> Score 54 (Medium - upper advisory).
     * alpha = 0.20 -> Score 63 (High - flagged for critical review).
     Here alpha=0.20 effectively detects sustained persistent cheating across half an hour.

   - Scenario 3B (Six windows with 30 pts):
     * alpha = 0.10 -> Score 45 (Medium).
     * alpha = 0.20 -> Score 60 (High).
     Under alpha=0.20, repeated violations across an entire exam escalate into High.

3. False Positive Risk in Extended Examinations (3 Hours):
   - Scenario 4 (Honest candidate with 1 glance per 10m):
     * alpha = 0.10 -> Score 32 (Medium advisory, comfortably 28 points below High).
     * alpha = 0.20 -> Score 53 (Medium advisory, but only 7 points away from false High!).
   - Scenario 4B (Honest candidate with natural minor movements, 18 pts per window):
     * alpha = 0.10 -> Score 49 (Medium advisory - safe from false High accusation).
     * alpha = 0.20 -> Score 79 (HIGH RISK - FALSE POSITIVE ACCUSATION!).

RECOMMENDATION:
   Keep TIME_NORM_PERSISTENCE_ALPHA = 0.10 in production.
   Alpha = 0.20 creates severe false positive risk for honest candidates taking 2-3 hour exams,
   converting innocent candidates with natural fatigue or minor fidgeting into High Risk (>=60).
   Alpha = 0.10 provides the ideal conservative baseline required for an evaluator-assistance tool.
""")

if __name__ == "__main__":
    run_evaluation()
