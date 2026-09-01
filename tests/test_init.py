from types import SimpleNamespace


def test_init_yes_skips_prompts(monkeypatch, tmp_path):
    import pwnv.utils as utils
    from pwnv.cli.init import init
    from pwnv.constants import DEFAULT_PYTHON_VERSION

    config_path = utils.get_config_path()
    config_path.unlink()
    prompts = []

    monkeypatch.setattr("shutil.which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        "subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )
    monkeypatch.setattr(
        utils, "prompt_confirm", lambda *args, **kwargs: prompts.append(args)
    )

    ctfs_path = tmp_path / "ctfs"
    init(
        yes=True,
        no_install=True,
        ctfs_folder=ctfs_path,
        python=DEFAULT_PYTHON_VERSION,
    )

    assert prompts == []
    assert ctfs_path.is_dir()
    assert utils.get_ctfs_path() == ctfs_path


def test_init_installs_defaults_into_created_environment(monkeypatch, tmp_path):
    import pwnv.utils as utils
    from pwnv.cli.init import init
    from pwnv.constants import (
        DEFAULT_PACKAGES,
        DEFAULT_PWNVENV_FOLDER_NAME,
        DEFAULT_PYTHON_VERSION,
    )

    utils.get_config_path().unlink()
    calls = []

    monkeypatch.setattr("shutil.which", lambda command: f"/usr/bin/{command}")

    def _run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", _run)

    ctfs_path = tmp_path / "ctfs"
    init(
        yes=True,
        no_install=False,
        ctfs_folder=ctfs_path,
        python=DEFAULT_PYTHON_VERSION,
    )

    python_path = ctfs_path / DEFAULT_PWNVENV_FOLDER_NAME / "bin" / "python"
    assert calls[0][0] == [
        "uv",
        "venv",
        "--python",
        DEFAULT_PYTHON_VERSION,
        str(ctfs_path / DEFAULT_PWNVENV_FOLDER_NAME),
    ]
    assert calls[1][0] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(python_path),
        *DEFAULT_PACKAGES,
    ]
    assert calls[1][1]["cwd"] == ctfs_path
    assert calls[2][0] == [
        "uv",
        "pip",
        "check",
        "--python",
        str(python_path),
    ]
