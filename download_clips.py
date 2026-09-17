"""Download pitch videos from Baseball Savant, one pitch or every pitch of a game.

Use:  python download_clips.py 2f22ed14-a540-37f3-9bbc-3f44ed2f945f   (one pitch, by play id)
      python download_clips.py 776188                                 (a whole game, by game_pk)
Out:  clips/<play_id>.mp4
"""
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


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for arg in sys.argv[1:]:
        ids = [arg] if "-" in arg else play_ids(arg)  # play ids have dashes, game_pks are digits
        results = [download(play_id) for play_id in ids]
        print(arg, {r: results.count(r) for r in set(results)})
