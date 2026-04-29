from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


LOGGER = logging.getLogger("music_recommender")


def _configure_logger() -> None:
    if LOGGER.handlers:
        return

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    handler = logging.FileHandler(log_dir / "recommender.log", encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)

    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """

    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """

    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


@dataclass
class RecommendationStep:
    name: str
    detail: str


@dataclass
class RecommendationTrace:
    profile: Dict
    retrieved_candidates: int
    evaluated_candidates: int
    confidence: float
    warnings: List[str] = field(default_factory=list)
    steps: List[RecommendationStep] = field(default_factory=list)
    diversity_applied: bool = False

    def workflow_summary(self) -> str:
        return " -> ".join(f"{step.name}: {step.detail}" for step in self.steps)


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """
        Recommend top-k songs for a UserProfile.

        This implementation uses the same workflow as the functional API,
        then returns Song objects sorted by descending score.
        """

        results, _trace = recommend_songs(
            self._user_to_dict(user),
            [self._song_to_dict(song) for song in self.songs],
            k=k,
            return_trace=True,
        )
        song_ids = [result[0]["id"] for result in results]
        songs_by_id = {song.id: song for song in self.songs}
        return [songs_by_id[song_id] for song_id in song_ids if song_id in songs_by_id]

    def recommend_with_trace(
        self, user: UserProfile, k: int = 5
    ) -> Tuple[List[Song], RecommendationTrace]:
        results, trace = recommend_songs(
            self._user_to_dict(user),
            [self._song_to_dict(song) for song in self.songs],
            k=k,
            return_trace=True,
        )
        song_ids = [result[0]["id"] for result in results]
        songs_by_id = {song.id: song for song in self.songs}
        ordered_songs = [
            songs_by_id[song_id] for song_id in song_ids if song_id in songs_by_id
        ]
        return ordered_songs, trace

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """
        Return a short, human-readable explanation for why `song` was
        recommended to `user`.
        """

        _, reasons = score_song(self._user_to_dict(user), self._song_to_dict(song))
        return "; ".join(reasons)

    @staticmethod
    def _song_to_dict(song: Song) -> Dict:
        return {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "genre": song.genre,
            "mood": song.mood,
            "energy": song.energy,
            "tempo_bpm": song.tempo_bpm,
            "valence": song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
        }

    @staticmethod
    def _user_to_dict(user: UserProfile) -> Dict:
        return {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }


def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """

    _configure_logger()
    songs: List[Dict] = []
    path = Path(csv_path)

    LOGGER.info("Loading songs from %s", path)
    if not path.exists():
        raise FileNotFoundError(f"Could not find song catalog: {csv_path}")

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                song = {
                    "id": int(row.get("id", 0)),
                    "title": row.get("title", "").strip(),
                    "artist": row.get("artist", "").strip(),
                    "genre": row.get("genre", "").strip(),
                    "mood": row.get("mood", "").strip(),
                    "energy": float(row.get("energy", 0.0)),
                    "tempo_bpm": float(row.get("tempo_bpm", 0.0)),
                    "valence": float(row.get("valence", 0.0)),
                    "danceability": float(row.get("danceability", 0.0)),
                    "acousticness": float(row.get("acousticness", 0.0)),
                }
            except (TypeError, ValueError) as exc:
                LOGGER.warning("Skipping malformed row %s: %s", row, exc)
                continue
            songs.append(song)

    if not songs:
        raise ValueError(f"No valid songs were loaded from {csv_path}")

    LOGGER.info("Loaded %s songs", len(songs))
    return songs


def validate_user_preferences(user_prefs: Dict) -> Dict:
    """
    Normalize and validate user preferences before recommendation.
    """

    _configure_logger()
    cleaned: Dict = {}
    range_rules = {
        "energy": (0.0, 1.0),
        "valence": (0.0, 1.0),
        "danceability": (0.0, 1.0),
        "acousticness": (0.0, 1.0),
        "tempo": (40.0, 220.0),
    }

    for key in ("genre", "mood"):
        value = user_prefs.get(key)
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            cleaned[key] = normalized

    for key, (lower, upper) in range_rules.items():
        value = user_prefs.get(key)
        if value is None or value == "":
            continue
        numeric_value = float(value)
        if numeric_value < lower or numeric_value > upper:
            raise ValueError(
                f"{key} must be between {lower} and {upper}. Received {numeric_value}."
            )
        cleaned[key] = numeric_value

    if "likes_acoustic" in user_prefs:
        cleaned["likes_acoustic"] = bool(user_prefs["likes_acoustic"])

    if not cleaned:
        raise ValueError("Please provide at least one user preference.")

    LOGGER.info("Validated user preferences: %s", cleaned)
    return cleaned


def retrieve_candidate_songs(
    user_prefs: Dict, songs: List[Dict], candidate_limit: Optional[int] = None
) -> Tuple[List[Dict], str]:
    """
    Retrieve the most promising candidate songs before full scoring.

    This lightweight retrieval step keeps the existing scorer intact while
    making the recommendation flow more explicit and inspectable.
    """

    candidate_limit = candidate_limit or min(len(songs), 10)
    retrieval_pool: List[Tuple[float, Dict]] = []

    for song in songs:
        retrieval_score = 0.0
        if user_prefs.get("genre") and song.get("genre"):
            if song["genre"].lower() == user_prefs["genre"].lower():
                retrieval_score += 2.0

        if user_prefs.get("mood") and song.get("mood"):
            if song["mood"].lower() == user_prefs["mood"].lower():
                retrieval_score += 1.5

        if user_prefs.get("energy") is not None:
            energy_gap = abs(float(song.get("energy", 0.0)) - float(user_prefs["energy"]))
            retrieval_score += max(0.0, 1.0 - energy_gap * 2.0)

        if user_prefs.get("tempo") is not None:
            tempo_gap = abs(
                float(song.get("tempo_bpm", 0.0)) - float(user_prefs["tempo"])
            )
            retrieval_score += max(0.0, 1.0 - (tempo_gap / 40.0))

        if user_prefs.get("likes_acoustic"):
            retrieval_score += min(float(song.get("acousticness", 0.0)), 1.0)

        retrieval_pool.append((retrieval_score, song))

    ranked_pool = sorted(retrieval_pool, key=lambda item: item[0], reverse=True)
    positive_matches = [song for score, song in ranked_pool if score > 0]
    if not positive_matches:
        fallback_candidates = songs[:candidate_limit]
        return fallback_candidates, "retrieval fallback to full catalog"

    candidates = positive_matches[:candidate_limit]
    return candidates, f"retrieved {len(candidates)} candidate songs"


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py
    """

    reasons: List[str] = []
    raw_points = 0.0
    max_points = 0.0

    genre_weight = 2.0
    mood_weight = 1.0
    acoustic_preference_weight = 0.75
    max_points += genre_weight + mood_weight

    if user_prefs.get("genre") and song.get("genre"):
        if song["genre"].lower() == user_prefs["genre"].lower():
            raw_points += genre_weight
            reasons.append(f"genre match (+{genre_weight:.1f})")

    if user_prefs.get("mood") and song.get("mood"):
        if song["mood"].lower() == user_prefs["mood"].lower():
            raw_points += mood_weight
            reasons.append(f"mood match (+{mood_weight:.1f})")

    numeric_features = [
        ("energy", "energy", 0.12, 1.0),
        ("valence", "valence", 0.15, 1.0),
        ("danceability", "danceability", 0.12, 1.0),
        ("acousticness", "acousticness", 0.15, 1.0),
        ("tempo_bpm", "tempo", 12.0, 1.0),
    ]

    for song_key, user_key, sigma, weight in numeric_features:
        if user_prefs.get(user_key) is None or song_key not in song:
            continue

        s_val = float(song[song_key])
        u_val = float(user_prefs[user_key])
        diff = s_val - u_val
        score_f = math.exp(-((diff**2) / (2 * (sigma**2))))

        contrib = score_f * weight
        raw_points += contrib
        max_points += weight
        reasons.append(f"{song_key} closeness (+{contrib:.2f})")

    if user_prefs.get("likes_acoustic") is True:
        max_points += acoustic_preference_weight
        acoustic_boost = float(song.get("acousticness", 0.0)) * acoustic_preference_weight
        raw_points += acoustic_boost
        reasons.append(f"acoustic preference (+{acoustic_boost:.2f})")

    final_score = raw_points / max_points if max_points > 0 else 0.0
    return final_score, reasons


def _diversify_ranked_results(
    scored_songs: List[Tuple[Dict, float, List[str]]], k: int
) -> Tuple[List[Tuple[Dict, float, List[str]]], bool]:
    if len(scored_songs) <= 1:
        return scored_songs[:k], False

    top_slice = scored_songs[:k]
    unique_artists = {song["artist"] for song, _, _ in top_slice}
    if len(unique_artists) >= min(k, 2):
        return top_slice, False

    selected: List[Tuple[Dict, float, List[str]]] = []
    artist_counts: Dict[str, int] = {}
    remaining = list(scored_songs)

    while remaining and len(selected) < k:
        best_index = 0
        best_adjusted_score = -1.0

        for index, (song, score, reasons) in enumerate(remaining):
            repeat_penalty = 0.08 * artist_counts.get(song["artist"], 0)
            adjusted_score = score - repeat_penalty
            if adjusted_score > best_adjusted_score:
                best_adjusted_score = adjusted_score
                best_index = index

        song, score, reasons = remaining.pop(best_index)
        selected.append((song, score, reasons))
        artist_counts[song["artist"]] = artist_counts.get(song["artist"], 0) + 1

    return selected, True


def _compute_confidence(
    scored_songs: List[Tuple[Dict, float, List[str]]], user_prefs: Dict
) -> Tuple[float, List[str]]:
    if not scored_songs:
        return 0.0, ["No songs were available to score."]

    warnings: List[str] = []
    top_score = scored_songs[0][1]
    second_score = scored_songs[1][1] if len(scored_songs) > 1 else top_score
    score_margin = max(0.0, top_score - second_score)

    requested_signals = sum(
        1
        for key in (
            "genre",
            "mood",
            "energy",
            "valence",
            "danceability",
            "acousticness",
            "tempo",
            "likes_acoustic",
        )
        if user_prefs.get(key) not in (None, "", False)
    )
    top_reason_count = len(scored_songs[0][2])
    reason_coverage = min(1.0, top_reason_count / max(requested_signals, 1))

    confidence = (0.65 * top_score) + (0.2 * min(score_margin * 4.0, 1.0)) + (
        0.15 * reason_coverage
    )
    confidence = max(0.0, min(confidence, 1.0))

    if top_score < 0.45:
        warnings.append("Top recommendation is a weak overall match.")
    if score_margin < 0.03:
        warnings.append("Top songs are very close in score, so ranking may be unstable.")
    if requested_signals >= 3 and reason_coverage < 0.5:
        warnings.append("Several requested preferences were not strongly reflected.")

    return confidence, warnings


def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5, return_trace: bool = False
):
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """

    _configure_logger()
    validated_prefs = validate_user_preferences(user_prefs)
    candidate_limit = min(len(songs), max(k * 3, 6))
    candidates, retrieval_note = retrieve_candidate_songs(
        validated_prefs, songs, candidate_limit=candidate_limit
    )

    scored: List[Tuple[Dict, float, List[str]]] = []
    for song in candidates:
        score, reasons = score_song(validated_prefs, song)
        scored.append((song, score, reasons))

    scored_sorted = sorted(scored, key=lambda item: item[1], reverse=True)
    diversified, diversity_applied = _diversify_ranked_results(scored_sorted, k=k)
    confidence, warnings = _compute_confidence(diversified, validated_prefs)

    results: List[Tuple[Dict, float, str]] = []
    for song, score, reasons in diversified:
        explanation = "; ".join(reasons) if reasons else "No strong signals"
        results.append((song, score, explanation))

    trace = RecommendationTrace(
        profile=validated_prefs,
        retrieved_candidates=len(candidates),
        evaluated_candidates=len(scored_sorted),
        confidence=confidence,
        warnings=warnings,
        diversity_applied=diversity_applied,
        steps=[
            RecommendationStep("validate", "validated user preference ranges"),
            RecommendationStep("retrieve", retrieval_note),
            RecommendationStep("rank", f"scored {len(scored_sorted)} candidates"),
            RecommendationStep(
                "self-check",
                "applied artist diversity guardrail"
                if diversity_applied
                else "ranking stable without diversity repair",
            ),
        ],
    )

    LOGGER.info(
        "Recommendation workflow completed | confidence=%.2f | candidates=%s | warnings=%s",
        confidence,
        len(candidates),
        warnings,
    )

    if return_trace:
        return results, trace
    return results
