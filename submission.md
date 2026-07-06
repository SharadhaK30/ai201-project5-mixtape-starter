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

