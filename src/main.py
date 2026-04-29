"""CLI runner for the Music Recommender Simulation.

Allows specifying a simple profile via CLI flags or interactively.
Prints a formatted table of top-K recommendations including reasons.
"""

import argparse
import textwrap
from typing import Dict

try:
    # package-style import when running `python -m src.main`
    from src.recommender import load_songs, recommend_songs
except Exception:
    from recommender import load_songs, recommend_songs


def format_table(rows):
    """Format rows into a readable table. Uses tabulate when available, falls back to ASCII."""
    try:
        from tabulate import tabulate
        headers = ["Rank", "Title", "Artist", "Score", "Reasons"]
        return tabulate(rows, headers=headers, tablefmt="github")
    except Exception:
        # Simple ASCII fallback
        col_widths = [6, 30, 18, 6, 50]
        out = []
        header = f"{'Rank':<{col_widths[0]}} {'Title':<{col_widths[1]}} {'Artist':<{col_widths[2]}} {'Score':<{col_widths[3]}} Reasons"
        out.append(header)
        out.append('-' * (sum(col_widths) + 20))
        for row in rows:
            rank, title, artist, score, reasons = row
            reasons_short = textwrap.shorten(reasons, width=col_widths[4], placeholder='...')
            out.append(f"{str(rank):<{col_widths[0]}} {title[:col_widths[1]]:<{col_widths[1]}} {artist[:col_widths[2]]:<{col_widths[2]}} {score:<{col_widths[3]}.2f} {reasons_short}")
        return "\n".join(out)


def build_user_prefs_from_args(args: argparse.Namespace) -> Dict:
    """Create user_prefs dict expected by score_song/recommend_songs from parsed args."""
    prefs: Dict = {}
    if args.genre:
        prefs['genre'] = args.genre
    if args.mood:
        prefs['mood'] = args.mood
    if args.energy is not None:
        prefs['energy'] = float(args.energy)
    if args.valence is not None:
        prefs['valence'] = float(args.valence)
    if args.danceability is not None:
        prefs['danceability'] = float(args.danceability)
    if args.acousticness is not None:
        prefs['acousticness'] = float(args.acousticness)
    if args.tempo is not None:
        prefs['tempo'] = float(args.tempo)
    return prefs


def prompt_for_profile() -> Dict:
    """Prompt user interactively for a small profile; empty input keeps field unset."""
    print("Enter profile values (press Enter to skip / use default):")
    genre = input("Preferred genre (e.g., pop, lofi): ").strip() or None
    mood = input("Preferred mood (e.g., chill, happy): ").strip() or None
    energy = input("Target energy (0.0-1.0, e.g., 0.5): ").strip() or None
    if energy:
        try:
            energy = float(energy)
        except Exception:
            energy = None
    prefs = {}
    if genre:
        prefs['genre'] = genre
    if mood:
        prefs['mood'] = mood
    if energy is not None:
        prefs['energy'] = energy
    return prefs


def main() -> None:
    parser = argparse.ArgumentParser(description='Music Recommender CLI')
    parser.add_argument('--csv', default='data/songs.csv', help='Path to songs CSV')
    parser.add_argument('--genre', help='Preferred genre')
    parser.add_argument('--mood', help='Preferred mood')
    parser.add_argument('--energy', type=float, help='Target energy 0.0-1.0')
    parser.add_argument('--valence', type=float, help='Target valence 0.0-1.0')
    parser.add_argument('--danceability', type=float, help='Target danceability 0.0-1.0')
    parser.add_argument('--acousticness', type=float, help='Target acousticness 0.0-1.0')
    parser.add_argument('--tempo', type=float, help='Target tempo in BPM (e.g., 80)')
    parser.add_argument('-k', type=int, default=5, help='How many recommendations to show')
    parser.add_argument('--interactive', action='store_true', help='Prompt for a small profile interactively')
    parser.add_argument(
        '--show-workflow',
        action='store_true',
        help='Show the retrieval, ranking, and self-check workflow summary',
    )

    args = parser.parse_args()

    try:
        songs = load_songs(args.csv)

        if args.interactive:
            user_prefs = prompt_for_profile()
        else:
            # Build from CLI args, fall back to a sensible default if nothing provided
            user_prefs = build_user_prefs_from_args(args)
            if not user_prefs:
                # default example profile
                user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

        recommendations, trace = recommend_songs(
            user_prefs, songs, k=args.k, return_trace=True
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")

    rows = []
    for i, rec in enumerate(recommendations, start=1):
        song, score, explanation = rec
        rows.append([i, song['title'], song.get('artist', ''), score, explanation])

    table = format_table(rows)
    print('\nTop recommendations:\n')
    print(table)
    print(f"\nConfidence: {trace.confidence:.2f}")
    if trace.warnings:
        print("Warnings:")
        for warning in trace.warnings:
            print(f"- {warning}")
    if args.show_workflow:
        print("\nWorkflow:")
        for step in trace.steps:
            print(f"- {step.name}: {step.detail}")


if __name__ == "__main__":
    main()
