import pytest

from songs.chords import plan_for, sounding_key_for, suggest_capos, written_key_for
from songs.chords.capo import CapoPlan


def test_no_capo_leaves_the_key_alone():
    plan = plan_for("G", 0)

    assert plan.written_key == "G"
    assert plan.sounding_key == "G"


def test_capo_two_in_f_shapes_sounds_in_g():
    plan = plan_for("F", 2)

    assert plan.sounding_key == "G"
    assert plan.describe() == "Capo 2, play F shapes, sounds in G"


def test_written_key_for_is_the_inverse():
    for sounding, capo in [("G", 2), ("C", 3), ("A", 5)]:
        written = written_key_for(sounding, capo)
        assert sounding_key_for(written, capo) == sounding


def test_flat_keys_stay_flat():
    # Bb sounding with a capo 3 is G shapes.
    assert written_key_for("Bb", 3) == "G"
    # Ab sounding with a capo 1 is G shapes.
    assert written_key_for("Ab", 1) == "G"


def test_capo_above_eleven_wraps():
    assert sounding_key_for("C", 12) == "C"


def test_describe_without_capo():
    assert plan_for("G", 0).describe() == "Play in G, no capo"


def test_describe_without_key_is_quiet():
    assert plan_for("", 2).describe() == ""


def test_uses_capo():
    assert plan_for("F", 2).uses_capo is True
    assert plan_for("G", 0).uses_capo is False


def test_suggest_capos_for_bb():
    capos = {plan.capo: plan.written_key for plan in suggest_capos("Bb", max_capo=7)}

    assert capos[1] == "A"
    assert capos[3] == "G"
    assert 0 not in capos


def test_suggest_capos_respects_max():
    assert all(plan.capo <= 3 for plan in suggest_capos("Bb", max_capo=3))


def test_suggest_capos_for_unknown_key():
    assert suggest_capos("") == []


def test_suggestion_keys_match_the_plan():
    for plan in suggest_capos("B", max_capo=7):
        assert plan.sounding_key == "B"
        assert sounding_key_for(plan.written_key, plan.capo) == "B"


def test_plan_is_hashable_and_frozen():
    plan = CapoPlan(written_key="F", sounding_key="G", capo=2)

    with pytest.raises(AttributeError):
        plan.capo = 3
