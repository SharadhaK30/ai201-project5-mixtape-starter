# Mixtape Bug Hunt Submission

## AI Usage

I used Codex to help navigate the unfamiliar Flask codebase, summarize the responsibilities of the route and service modules, and trace route-to-service flows before making changes. I also used it to run the test suite, compare failing test output with the service code, and draft root cause analysis notes while the code paths were fresh. I verified each diagnosis against the source files and test results before applying fixes.

## Codebase Map

### Main Files and Roles

- `app.py` creates the Flask application, configures SQLAlchemy, registers the route blueprints, and creates database tables inside the app context.
- `models.py` defines the data model: `User`, `Song`, `Tag`, `ListeningEvent`, `Rating`, `Playlist`, and `Notification`. It also defines many-to-many association tables for friendships, song tags, and ordered playlist entries.
- `routes/songs.py` handles song search, song detail, rating, and listening endpoints. It parses request data and delegates work to `search_service`, `notification_service`, and `streak_service`.
- `routes/playlists.py` handles playlist creation, playlist metadata, playlist song retrieval, and adding songs to playlists. Playlist song additions go through `notification_service.add_to_playlist()` because that action may notify a song sharer.
- `routes/users.py` handles user profiles, streak lookup, notification retrieval, and marking notifications as read.
- `routes/feed.py` handles friends-listening-now and activity-feed endpoints.
- `services/streak_service.py` records listening events and updates a user's listening streak.
- `services/feed_service.py` builds the friends listening now feed and the general activity feed from `ListeningEvent` rows.
- `services/search_service.py` searches songs and retrieves individual song records.
- `services/notification_service.py` creates notifications, handles rating writes, adds songs to playlists, retrieves notifications, and marks notifications as read.
- `services/playlist_service.py` creates playlists and retrieves playlist metadata or ordered playlist songs.
- `seed_data.py` resets and populates the database with users, friendships, songs, tags, listening events, playlists, playlist entries, ratings, and notifications for manual testing.
- `tests/` contains focused pytest tests for streak, search, and playlist behavior.

### Data Flow: Rating a Song

`POST /songs/<song_id>/rate` enters `routes/songs.py`. The route reads `user_id` and `score` from JSON, validates that both were provided, and calls `notification_service.rate_song(user_id, song_id, score)`. The service validates the score range, loads the `Song` and `User`, checks whether that user already has a `Rating` row for the song, then either updates the existing row or inserts a new `Rating`. After the fix for Issue 4, the same service also creates a `Notification` for the original song sharer when a different user rates their song.

### Pattern Noticed

Routes mostly do HTTP-specific work: parse request fields, call one service function, and format JSON responses. Business rules live in `services/`, while persistence details live in `models.py` and SQLAlchemy queries. Some service functions commit directly, so side effects such as creating a notification need to be handled deliberately in the same service path that performs the user action.

## Root Cause Analyses

### Issue 1: My Listening Streak Keeps Resetting

**How I reproduced it:** I ran the existing streak tests with `.venv/bin/python -m pytest tests/`. `test_streak_increments_on_sunday` created a user, recorded a Saturday listen, then recorded a Sunday listen. The streak stayed at `1` instead of increasing to `2`.

**How I found the root cause:** I traced `POST /songs/<song_id>/listen` in `routes/songs.py` to `services/streak_service.record_listening_event()`, then into `update_listening_streak()`. The failing test pointed at the Saturday-to-Sunday boundary, and the key line was the `days_since_last == 1 and today.weekday() != 6` condition.

**The root cause:** The service correctly calculated that Saturday to Sunday is a one-day gap, but then excluded Sundays from the consecutive-day increment path. Python's `weekday()` returns `6` for Sunday, so a valid consecutive listen on Sunday fell into the reset branch and set the streak back to `1`.

**Your fix and side-effect check:** I changed the condition so every `days_since_last == 1` case increments the streak. The existing same-day and skipped-day branches still handle duplicate listens and missed days separately, so Monday-to-Tuesday increments and Monday-to-Wednesday resets remain unchanged. I verified this with the streak test file.

