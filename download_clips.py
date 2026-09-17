"""Download pitch videos from Baseball Savant, one pitch, a whole game, or every pitch for a player in a season.

Use:  python download_clips.py 2f22ed14-a540-37f3-9bbc-3f44ed2f945f        (one pitch, by play id)
      python download_clips.py 776188                                      (a whole game, by game_pk)
      python download_clips.py --player 592450 --season 2024               (every pitch a batter saw in 2024)
      python download_clips.py --player 592789 --season 2024 --pitching    (every pitch a pitcher threw in 2024)
            python download_clips.py --player 701398 --season 2025 --start-date 2025-09-15 --end-date 2025-09-17
Out:  clips/<play_id>.mp4
"""
import argparse
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

USER_AGENT = "savant-clip-downloader"
OUT = Path("clips")


def get(url):
    """Bytes at url."""
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as r:
        return r.read()


def play_ids(game_pk):
    """Every pitch's play id in one game, from the MLB Stats API game feed."""
    feed = json.loads(get(f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"))
    return [ev["playId"] for play in feed["liveData"]["plays"]["allPlays"]
            for ev in play["playEvents"] if ev.get("isPitch") and ev.get("playId")]


def player_play_ids(player_id, season, pitching=False, start_date=None, end_date=None,
                     sport_id=1, game_type=('R',)):
    """Every pitch play id for one player in a season, via tnestico/mlb_scraper."""
    try:
        from api_scraper import MLB_Scrape
    except ImportError:
        sys.exit(
            "The --player option needs tnestico/mlb_scraper installed and importable.\n"
            "See: https://github.com/tnestico/mlb_scraper"
        )
    scraper = MLB_Scrape()
    df = scraper.get_player_pitches(
        player_id=player_id,
        season=season,
        start_date=start_date,
        end_date=end_date,
        sport_id=sport_id,
        game_type=list(game_type),
        pitching=pitching,
    )
    return [pid for pid in df["play_id"].to_list() if pid]


def download(play_id, tries=3):
    """One pitch video to clips/. Returns ok | no video | failed."""
    dest = OUT / f"{play_id}.mp4"
    if dest.exists():
        return "ok"
    for attempt in range(1, tries + 1):
        try:
            page = get(f"https://baseballsavant.mlb.com/sporty-videos?playId={play_id}").decode()
            source = re.search(r'<source\s+src="([^"]+\.mp4[^"]*)"', page)
            if not source:
                return "no video"  # Savant never published one (spring training, very recent games, etc.)
            clip = get(html.unescape(source.group(1)))
            if clip[4:8] == b"ftyp":  # every MP4 file has "ftyp" at byte 4
                dest.write_bytes(clip)
                return "ok"
        except OSError:
            pass
        time.sleep(5 * attempt)
    return "failed"


def download_all(play_ids):
    """Download clips sequentially and print progress after each one."""
    total = len(play_ids)
    results = []
    for completed, play_id in enumerate(play_ids, start=1):
        already_exists = (OUT / f"{play_id}.mp4").exists()
        result = download(play_id)
        results.append(result)
        status = "already on disk" if already_exists and result == "ok" else result
        if result == "ok" and not already_exists:
            status = "downloaded"
        print(f"[{completed}/{total}] {play_id}: {status}; {total - completed} remaining")
    return results


def parse_args(argv):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--player", type=int, help="player_id: download every pitch for this player")
    parser.add_argument("--season", type=int, help="season year, required with --player")
    parser.add_argument("--start-date", help="with --player, inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="with --player, inclusive end date (YYYY-MM-DD)")
    parser.add_argument("--pitching", action="store_true",
                         help="with --player, get pitches thrown rather than seen")
    parser.add_argument("targets", nargs="*", help="play_id or game_pk values")
    return parser.parse_args(argv)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    args = parse_args(sys.argv[1:])

    if args.player:
        if not args.season:
            sys.exit("--season is required with --player")
        ids = player_play_ids(
            args.player,
            args.season,
            pitching=args.pitching,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        results = download_all(ids)
        label = f"player {args.player} ({'pitching' if args.pitching else 'batting'}) {args.season}"
        print(label, {r: results.count(r) for r in set(results)})
    else:
        for arg in args.targets:
            ids = [arg] if "-" in arg else play_ids(arg)  # play ids have dashes, game_pks are digits
            results = download_all(ids)
            print(arg, {r: results.count(r) for r in set(results)})