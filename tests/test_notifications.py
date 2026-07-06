"""
tests/test_notifications.py - Mixtape

Tests for notification side effects.
"""

import pytest
from app import create_app, db
from models import Notification, Song, User
from services.notification_service import rate_song


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def rating_subjects(app):
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        rater = User(username="rater", email="rater@example.com")
        db.session.add_all([sharer, rater])
        db.session.flush()

        song = Song(title="Shared Track", artist="The Makers", shared_by=sharer.id)
        db.session.add(song)
        db.session.commit()

        yield {"sharer": sharer, "rater": rater, "song": song}


def test_rating_someone_elses_song_notifies_original_sharer(app, rating_subjects):
    with app.app_context():
        sharer_id = rating_subjects["sharer"].id
        rater_id = rating_subjects["rater"].id
        song_id = rating_subjects["song"].id

        rate_song(rater_id, song_id, 5)

        notification = db.session.query(Notification).filter_by(user_id=sharer_id).one()
        assert notification.notification_type == "song_rated"
        assert "rater rated your song 'Shared Track' 5/5." == notification.body


def test_rating_own_song_does_not_notify_self(app, rating_subjects):
    with app.app_context():
        sharer_id = rating_subjects["sharer"].id
        song_id = rating_subjects["song"].id

        rate_song(sharer_id, song_id, 4)

        notifications = db.session.query(Notification).filter_by(user_id=sharer_id).all()
        assert notifications == []
