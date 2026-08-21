from pwnv.models import CTF, Challenge


def test_model_defaults_are_generated_per_instance(tmp_path):
    first_ctf = CTF(name="first", path=tmp_path / "first")
    second_ctf = CTF(name="second", path=tmp_path / "second")

    first_challenge = Challenge(
        name="first", ctf_id=first_ctf.id, path=first_ctf.path / "first"
    )
    second_challenge = Challenge(
        name="second", ctf_id=first_ctf.id, path=first_ctf.path / "second"
    )

    assert first_ctf.id != second_ctf.id
    assert first_challenge.id != second_challenge.id
