from types import SimpleNamespace


def test_init_yes_skips_prompts(monkeypatch, tmp_path):
    import pwnv.utils as utils
    from pwnv.cli.init import init

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
    init(yes=True, no_install=True, ctfs_folder=ctfs_path)

    assert prompts == []
    assert ctfs_path.is_dir()
    assert utils.get_ctfs_path() == ctfs_path
