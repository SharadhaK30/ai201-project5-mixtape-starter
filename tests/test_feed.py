"""
tests/test_feed.py - Mixtape

Tests for feed service behavior.
"""

import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import ListeningEvent, Song, User, friendships
from services.feed_service import get_friends_listening_now


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def listening_now_data(app):
    with app.app_context():
        viewer = User(username="viewer", email="viewer@example.com")
        recent_friend = User(username="recent", email="recent@example.com")
        stale_friend = User(username="stale", email="stale@example.com")
        db.session.add_all([viewer, recent_friend, stale_friend])
        db.session.flush()

        for friend in (recent_friend, stale_friend):
            db.session.execute(friendships.insert().values(user_id=viewer.id, friend_id=friend.id))
            db.session.execute(friendships.insert().values(user_id=friend.id, friend_id=viewer.id))

        song = Song(title="Now Track", artist="Current Artist", shared_by=viewer.id)
        db.session.add(song)
        db.session.flush()

        now = datetime.now(timezone.utc)
        db.session.add_all([
            ListeningEvent(
                user_id=recent_friend.id,
                song_id=song.id,
                listened_at=now - timedelta(minutes=10),
            ),
            ListeningEvent(
                user_id=stale_friend.id,
                song_id=song.id,
                listened_at=now - timedelta(hours=23),
            ),
        ])
        db.session.commit()

        yield {"viewer": viewer, "recent_friend": recent_friend, "stale_friend": stale_friend}


def test_listening_now_excludes_yesterdays_events(app, listening_now_data):
    with app.app_context():
        feed = get_friends_listening_now(listening_now_data["viewer"].id)
        usernames = [item["friend"]["username"] for item in feed]

        assert usernames == ["recent"]
