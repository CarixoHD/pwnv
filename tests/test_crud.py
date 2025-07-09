import importlib

from pwnv.models import CTF
from pwnv.models.ctf import Status


def _reload_modules():
    import pwnv.utils.config as config
    import pwnv.utils.crud as crud
    importlib.reload(config)
    importlib.reload(crud)
    return config, crud


def test_is_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv('PWNV_CONFIG', str(tmp_path / 'cfg.json'))
    config, crud = _reload_modules()

    ctfs = [CTF(name='one', path=tmp_path/'one')]
    assert crud.is_duplicate(name='one', model_list=ctfs)
    assert crud.is_duplicate(path=tmp_path/'one', model_list=ctfs)
    assert crud.is_duplicate(name='one', path=tmp_path/'other', model_list=ctfs)
    assert not crud.is_duplicate(name='two', path=tmp_path/'two', model_list=ctfs)


def test_update_ctf(tmp_path, monkeypatch):
    monkeypatch.setenv('PWNV_CONFIG', str(tmp_path / 'cfg.json'))
    config, crud = _reload_modules()

    ctf = CTF(name='ctf', path=tmp_path/'ctf')
    crud.add_ctf(ctf)
    ctf.running = Status.stopped
    crud.update_ctf(ctf)

    reloaded = crud.get_ctfs()[0]
    assert reloaded.running == Status.stopped
