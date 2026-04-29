"""Evaluation harness for the Music Recommender Simulation.

Runs a handful of fixed recommendation scenarios and prints a compact
pass/fail summary with average confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple

try:
    from src.recommender import load_songs, recommend_songs
except Exception:
    from recommender import load_songs, recommend_songs


RecommendationRow = Tuple[Dict, float, str]
ScenarioCheck = Callable[[Sequence[RecommendationRow]], bool]


@dataclass
class EvaluationScenario:
    name: str
    user_prefs: Dict
    check: ScenarioCheck
    expectation: str


def top_song_has(genre: str | None = None, mood: str | None = None) -> ScenarioCheck:
    def _check(results: Sequence[RecommendationRow]) -> bool:
        if not results:
            return False
        song = results[0][0]
        if genre is not None and song.get("genre") != genre:
            return False
        if mood is not None and song.get("mood") != mood:
            return False
        return True

    return _check


def top_k_contains_title(title: str) -> ScenarioCheck:
    def _check(results: Sequence[RecommendationRow]) -> bool:
        return any(song["title"] == title for song, _score, _reason in results)

    return _check


def unique_artist_count_at_least(minimum: int) -> ScenarioCheck:
    def _check(results: Sequence[RecommendationRow]) -> bool:
        artists = {song["artist"] for song, _score, _reason in results}
        return len(artists) >= minimum

    return _check


def run_evaluation(csv_path: str = "data/songs.csv", k: int = 3) -> Dict:
    songs = load_songs(csv_path)
    scenarios: List[EvaluationScenario] = [
        EvaluationScenario(
            name="Chill Lofi",
            user_prefs={"genre": "lofi", "mood": "chill", "energy": 0.4},
            check=top_song_has(genre="lofi", mood="chill"),
            expectation="Top result should be a chill lofi song.",
        ),
        EvaluationScenario(
            name="Workout Pop",
            user_prefs={"genre": "pop", "mood": "intense", "energy": 0.9},
            check=top_song_has(genre="pop", mood="intense"),
            expectation="Top result should match energetic pop workout taste.",
        ),
        EvaluationScenario(
            name="Acoustic Reflection",
            user_prefs={
                "genre": "folk",
                "mood": "contemplative",
                "energy": 0.35,
                "likes_acoustic": True,
            },
            check=top_k_contains_title("Autumn Walk"),
            expectation="Autumn Walk should appear in the top recommendations.",
        ),
        EvaluationScenario(
            name="Diversity Guardrail",
            user_prefs={"energy": 0.75},
            check=unique_artist_count_at_least(2),
            expectation="Top results should not collapse to a single artist when alternatives exist.",
        ),
    ]

    rows: List[Dict] = []
    passed = 0
    confidence_total = 0.0

    for scenario in scenarios:
        results, trace = recommend_songs(
            scenario.user_prefs, songs, k=k, return_trace=True
        )
        result = scenario.check(results)
        passed += int(result)
        confidence_total += trace.confidence
        rows.append(
            {
                "name": scenario.name,
                "passed": result,
                "confidence": round(trace.confidence, 2),
                "expectation": scenario.expectation,
                "top_title": results[0][0]["title"] if results else "None",
            }
        )

    average_confidence = confidence_total / len(scenarios) if scenarios else 0.0
    return {
        "rows": rows,
        "passed": passed,
        "total": len(scenarios),
        "average_confidence": round(average_confidence, 2),
    }


def main() -> None:
    summary = run_evaluation()
    print("Evaluation summary")
    print("------------------")
    for row in summary["rows"]:
        status = "PASS" if row["passed"] else "FAIL"
        print(
            f"{status} | {row['name']:<20} | confidence={row['confidence']:.2f} | "
            f"top={row['top_title']} | {row['expectation']}"
        )

    print()
    print(
        f"Passed {summary['passed']} of {summary['total']} scenarios. "
        f"Average confidence: {summary['average_confidence']:.2f}"
    )


if __name__ == "__main__":
    main()
