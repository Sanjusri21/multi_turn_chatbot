import pytest
from app.repositories.settings_repository import SettingsRepository

def test_user_settings_lifecycle(test_db, test_user):
    repo = SettingsRepository(test_db)

    # 1. Fetch defaults
    settings = repo.get_or_create(test_user.id)
    assert settings.user_id == test_user.id
    assert settings.theme == "dark"
    assert settings.memory_enabled is True
    assert settings.response_style == "balanced"

    # 2. Update settings
    updated = repo.update(test_user.id, {
        "theme": "light",
        "response_style": "creative",
        "animations_enabled": False
    })
    assert updated.theme == "light"
    assert updated.response_style == "creative"
    assert updated.animations_enabled is False

    # 3. Retrieve again
    reloaded = repo.get_by_user_id(test_user.id)
    assert reloaded.theme == "light"
    assert reloaded.response_style == "creative"
