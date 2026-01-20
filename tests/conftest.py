from env_loader import load_env


def pytest_configure(config):  # noqa: D103 - pytest hook
    load_env()
