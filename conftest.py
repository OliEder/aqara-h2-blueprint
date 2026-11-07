import pytest

# Makes pytest load the harness' fixture (`blueprint_env`) for every test in this project.
pytest_plugins = ["ha_blueprint_test_harness.pytest_plugin"]


# Home Assistant's test setup fails a test that ends with timers still armed. This blueprint has a
# state trigger and waits for templates, so it always leaves some; tell the setup that this is expected.
@pytest.fixture
def expected_lingering_timers() -> bool:
    return True


# Home Assistant logs a failing template or action of an automation as a warning or error and carries on,
# so a test can pass while the blueprint is broken. After every test, fail it if the automation logged
# (only the "call" phase of the test counts: caplog.records in teardown would be empty)
# anything at warning level or above, unless the test says it expects that (marker `allow_warnings`).
@pytest.fixture(autouse=True)
def no_automation_warnings(request, caplog):
    yield
    if request.node.get_closest_marker("allow_warnings"):
        return
    bad = [r.getMessage() for r in caplog.get_records("call")
           if r.name.startswith("homeassistant.components.automation") and r.levelname in ("WARNING", "ERROR", "CRITICAL")]
    assert not bad, f"the automation logged problems: {bad}"
