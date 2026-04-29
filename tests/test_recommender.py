import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import Recommender, Song, UserProfile, recommend_songs


def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


class RecommenderTests(unittest.TestCase):
    def test_recommend_returns_songs_sorted_by_score(self) -> None:
        user = UserProfile(
            favorite_genre="pop",
            favorite_mood="happy",
            target_energy=0.8,
            likes_acoustic=False,
        )
        rec = make_small_recommender()
        results = rec.recommend(user, k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].genre, "pop")
        self.assertEqual(results[0].mood, "happy")

    def test_explain_recommendation_returns_non_empty_string(self) -> None:
        user = UserProfile(
            favorite_genre="pop",
            favorite_mood="happy",
            target_energy=0.8,
            likes_acoustic=False,
        )
        rec = make_small_recommender()
        song = rec.songs[0]

        explanation = rec.explain_recommendation(user, song)
        self.assertIsInstance(explanation, str)
        self.assertTrue(explanation.strip())

    def test_recommend_songs_returns_trace_with_confidence(self) -> None:
        songs = [
            {
                "id": 1,
                "title": "Test Pop Track",
                "artist": "Test Artist",
                "genre": "pop",
                "mood": "happy",
                "energy": 0.8,
                "tempo_bpm": 120,
                "valence": 0.9,
                "danceability": 0.8,
                "acousticness": 0.2,
            },
            {
                "id": 2,
                "title": "Chill Lofi Loop",
                "artist": "Second Artist",
                "genre": "lofi",
                "mood": "chill",
                "energy": 0.4,
                "tempo_bpm": 80,
                "valence": 0.6,
                "danceability": 0.5,
                "acousticness": 0.9,
            },
        ]

        results, trace = recommend_songs(
            {"genre": "pop", "mood": "happy", "energy": 0.8},
            songs,
            k=2,
            return_trace=True,
        )

        self.assertEqual(len(results), 2)
        self.assertGreaterEqual(trace.retrieved_candidates, 1)
        self.assertGreaterEqual(trace.confidence, 0.0)
        self.assertLessEqual(trace.confidence, 1.0)
        self.assertTrue(trace.steps)

    def test_invalid_energy_preference_raises_value_error(self) -> None:
        songs = [
            {
                "id": 1,
                "title": "Test Pop Track",
                "artist": "Test Artist",
                "genre": "pop",
                "mood": "happy",
                "energy": 0.8,
                "tempo_bpm": 120,
                "valence": 0.9,
                "danceability": 0.8,
                "acousticness": 0.2,
            }
        ]

        with self.assertRaises(ValueError):
            recommend_songs({"energy": 1.5}, songs)

    def test_likes_acoustic_preference_boosts_acoustic_song(self) -> None:
        songs = [
            {
                "id": 1,
                "title": "Dry Beat",
                "artist": "Test Artist",
                "genre": "folk",
                "mood": "calm",
                "energy": 0.3,
                "tempo_bpm": 76,
                "valence": 0.5,
                "danceability": 0.3,
                "acousticness": 0.1,
            },
            {
                "id": 2,
                "title": "Acoustic Glow",
                "artist": "Other Artist",
                "genre": "folk",
                "mood": "calm",
                "energy": 0.32,
                "tempo_bpm": 75,
                "valence": 0.52,
                "danceability": 0.31,
                "acousticness": 0.95,
            },
        ]

        results = recommend_songs(
            {"genre": "folk", "energy": 0.31, "likes_acoustic": True}, songs, k=2
        )

        self.assertEqual(results[0][0]["title"], "Acoustic Glow")


if __name__ == "__main__":
    unittest.main()
