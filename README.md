# Savant clip downloader

Download pitch videos from Baseball Savant, one pitch at a time, a whole game, or every pitch for a specific player in a season or date range.

## Use

```
python download_clips.py 2f22ed14-a540-37f3-9bbc-3f44ed2f945f
```

An argument with dashes is a `playId`, the ID at the end of a Savant video link (`sporty-videos?playId=...`). The clip saves to `clips/<playId>.mp4`, and the script prints a count of results:

```
2f22ed14-a540-37f3-9bbc-3f44ed2f945f {'ok': 1}
```

An argument of only digits is a `game_pk`, the number in the game's MLB.com or Baseball Savant link. The script then downloads every pitch of that game:

```
python download_clips.py 776188
```

Clips are about 4 MB each, which puts a full game around 1 GB. The script downloads them one at a time and skips any clip already on disk, so you can rerun a game safely.

After each clip, the script reports its result and the remaining count:

```
[1/42] 2f22ed14-a540-37f3-9bbc-3f44ed2f945f: downloaded; 41 remaining
[2/42] 7d7d40b7-6aa2-42cc-a337-3b3e5c8ca732: already on disk; 40 remaining
```

Other possible results are `no video` when Savant has no clip and `failed` when all download attempts fail.

### Downloading every pitch for a player

```
python download_clips.py --player 592450 --season 2024
python download_clips.py --player 592789 --season 2024 --pitching
```

`--player` takes an MLB player ID and `--season` the year. By default this pulls every pitch the player *faced as a batter*; add `--pitching` to instead pull every pitch they *threw*. This downloads every pitch of every game they appeared in that season, so it can be a large number of clips (see clip size above).

To limit the download to an inclusive date range, pass dates in `YYYY-MM-DD` format. For example, this downloads every pitch Sal Stewart (player `701398`) faced from September 15 through September 17, 2025:

```
python download_clips.py --player 701398 --season 2025 --start-date 2025-09-15 --end-date 2025-09-17
```

### How `download_clips.py` uses `api_scraper.py`

The `api_scraper.py` included in this repository comes from [tnestico/mlb_scraper](https://github.com/tnestico/mlb_scraper). In player mode, `download_clips.py` imports its `MLB_Scrape` class, calls `get_player_pitches(...)` with the player, season, optional date range, and batting/pitching mode, then downloads the Savant video for each returned `play_id`.

Keep `api_scraper.py` in the same folder as `download_clips.py` (as it is in this repository), or make it importable through `PYTHONPATH`. Its dependencies are:

```
pip install requests polars numpy tqdm pytz
```

Single-pitch and whole-game downloads do not import `api_scraper.py`; it is only used with `--player`.

## How it works

1. For a game, the MLB Stats API game feed lists the `playId` of each pitch.
2. For a player and season or date range, the bundled `api_scraper.py` from [mlb_scraper](https://github.com/tnestico/mlb_scraper) looks up every game they appeared in, pulls the play-by-play data for each, and filters it down to that player's pitches.
3. The Savant page `sporty-videos?playId=...` has the clip link in a `<source>` tag.
4. The script downloads the clip from that link.

## Notes

- If a page has no `<source>` tag, Savant has no video for that pitch. Spring training games and games from the last day or so often have none.
- Timeouts and server errors often clear up on their own. The script tries each clip 3 times, and if one still fails you can run the game again later.