import uuid

import pytest

from pwnv.models import CTF, Challenge
from pwnv.models.challenge import Category, Solved
from pwnv.utils import (
    add_challenge,
    add_ctf,
    get_challenges,
    get_ctfs,
    get_ctfs_path,
    is_duplicate,
    remove_challenge,
    remove_ctf,
    search_challenges,
    update_challenge,
)


@pytest.fixture
def fresh_ctf(tmp_path):
    """Create and return a CTF model pointing to the isolated ctfs_path."""
    ctfs_path = get_ctfs_path()
    ctf_path = ctfs_path / "example_ctf"
    ctf = CTF(name="ExampleCTF", path=ctf_path)
    add_ctf(ctf)
    return ctf


def test_add_ctf_creates_directory_and_persists(fresh_ctf):
    ctfs = get_ctfs()
    assert len(ctfs) == 1
    ctf = ctfs[0]
    assert ctf.name == "ExampleCTF"
    assert ctf.path.exists() and ctf.path.is_dir()


def test_add_and_update_challenge(fresh_ctf):
    ch_path = fresh_ctf.path / "pwn" / "first-blood"
    challenge = Challenge(
        ctf_id=fresh_ctf.id,
        name="First Blood",
        path=ch_path,
        category=Category.pwn,
        points=100,
    )
    add_challenge(challenge)

    # Added to config and directory created
    challenges = get_challenges()
    assert len(challenges) == 1
    stored = challenges[0]
    assert stored.name == "First Blood"
    assert stored.path.exists() and stored.path.is_dir()

    # Update metadata
    stored.solved = Solved.solved
    stored.flag = "FLAG{test}"
    stored.tags = ["pwn", "rop"]
    update_challenge(stored)

    updated = get_challenges()[0]
    assert updated.solved == Solved.solved
    assert updated.flag == "FLAG{test}"
    assert set(updated.tags) == {"pwn", "rop"}


def test_remove_challenge_and_ctf_cascade(fresh_ctf):
    # Add two challenges
    for name in ("Alpha", "Beta"):
        add_challenge(
            Challenge(
                id=uuid.uuid4(),
                ctf_id=fresh_ctf.id,
                name=name,
                path=fresh_ctf.path / "misc" / name.lower(),
                category=Category.misc,
            )
        )

    assert len(get_challenges()) == 2

    # Remove one challenge
    to_remove = get_challenges()[0]
    remove_challenge(to_remove)
    remaining = get_challenges()
    assert len(remaining) == 1
    assert not to_remove.path.exists()

    # Removing the CTF should delete remaining challenges and directory
    remove_ctf(fresh_ctf)
    assert get_ctfs() == []
    assert get_challenges() == []
    assert not fresh_ctf.path.exists()


def test_is_duplicate_by_name_and_path(fresh_ctf):
    duplicate_ctf = CTF(name="ExampleCTF", path=fresh_ctf.path)
    assert is_duplicate(model_list=get_ctfs(), path=duplicate_ctf.path)
    # Different path but same name also considered duplicate
    other_path = get_ctfs_path() / "other_ctf"
    duplicate_ctf_other_path = CTF(name="ExampleCTF", path=other_path)
    assert is_duplicate(model_list=get_ctfs(), name=duplicate_ctf_other_path.name)


def test_search_challenges_matches_metadata(fresh_ctf):
    challenge = Challenge(
        ctf_id=fresh_ctf.id,
        name="Hidden Message",
        path=fresh_ctf.path / "forensics" / "hidden-message",
        category=Category.forensics,
        tags=["steganography"],
        extras={"description": "Inspect the suspicious image"},
    )
    add_challenge(challenge)

    assert search_challenges("hidden") == [challenge]
    assert search_challenges("SUSPICIOUS") == [challenge]
    assert search_challenges("forensic") == [challenge]
    assert search_challenges("stegano") == [challenge]
    assert search_challenges("missing") == []
