import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_create_user_normalises_email_and_hashes_password():
    user = get_user_model().objects.create_user("Alice@Example.TEST", "a-long-password-123")
    assert user.email == "alice@example.test"
    assert user.check_password("a-long-password-123")
    assert user.password != "a-long-password-123"
    assert not user.is_staff and not user.is_superuser


@pytest.mark.django_db
def test_user_ids_are_uuids():
    user = get_user_model().objects.create_user("bob@example.test", "a-long-password-123")
    assert len(str(user.id)) == 36
