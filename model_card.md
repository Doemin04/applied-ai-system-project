# Model Card: Music Recommender Workflow

## 1. Model Name

VibeFinder Workflow 2.0

## 2. Intended Use

This system recommends 3 to 5 songs from a small local catalog based on a user's preferred genre, mood, and numeric listening targets such as energy and tempo. It is intended for classroom demonstration, portfolio presentation, and discussion of AI system design, not for production deployment.

## 3. How It Works

The model uses a four-step pipeline:

1. It validates the user profile.
2. It retrieves candidate songs that look promising based on the requested signals.
3. It scores those candidates using genre match, mood match, and numeric closeness across energy, valence, danceability, acousticness, and tempo.
4. It runs a small self-check that can discourage repeated artists and produces a confidence score plus warnings.

The scoring logic is intentionally transparent. Exact genre matches receive the strongest boost, mood matches receive a smaller boost, and numeric features use a smooth Gaussian-style closeness score so near matches still receive partial credit.

## 4. Data

The dataset contains 18 songs stored in `data/songs.csv`. The catalog includes pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, metal, reggae, hip hop, country, blues, electronic, and folk. Moods include happy, chill, intense, focused, contemplative, laidback, confident, nostalgic, sultry, and euphoric.

This is a hand-built dataset, so it reflects the choices and assumptions of the person who assembled it. It does not include real listener histories, lyrics, or audio embeddings.

## 5. Strengths

- Easy to explain because every recommendation includes explicit reasons.
- Handles cold-start songs well because it only needs metadata, not prior interactions.
- Supports workflow inspection through confidence scoring, warnings, and logged recommendation steps.
- Produces strong results for clear preference profiles such as "lofi + chill" or "pop + intense."

## 6. Limitations and Bias

- The catalog is very small, so coverage is narrow and rankings can be unstable.
- Exact genre matching can over-prioritize tags even when songs from other genres may feel similar.
- The model does not account for context such as time of day, lyrics, language, or long-term taste drift.
- Confidence is a heuristic, not a guarantee of correctness.

If used in a real product, these limitations could unfairly narrow user discovery or over-amplify the biases of whoever created the catalog and labels.

## 7. Evaluation

I evaluated the system in two ways:

- `tests/test_recommender.py` runs 5 direct automated checks covering ranking behavior, explanation generation, validation, trace generation, and acoustic preference handling.
- `src/evaluate.py` runs 4 fixed user scenarios and summarizes pass/fail results and average confidence.

Current observed results:

- 5 of 5 automated tests passed.
- 4 of 4 evaluation scenarios passed.
- Average confidence across evaluation scenarios was 0.78.

The weakest case was a sparse profile that only specified energy, which confirms that the system is less reliable when user intent is underspecified.

## 8. Future Work

- Expand the song catalog and add more balanced genre coverage.
- Add semantic similarity between genres and moods instead of exact string matching.
- Introduce user feedback signals such as likes, skips, or replays.
- Compare this explainable rules-based system against an embedding-driven recommender.

## 9. Personal Reflection

This project showed me that a recommendation system is more than a formula. The surrounding workflow, especially validation, retrieval, self-checks, logging, and testing, changes how trustworthy the final output feels.

It also reinforced that human judgment still matters. Even when the model gives plausible results, people still need to inspect whether the recommendations are diverse, fair, and appropriate for the context.
