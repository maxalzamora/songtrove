import pytest

from songs.chords import plan_for, shape_key_for, sounding_key_for, suggest_capos
from songs.chords.capo import CapoPlan


def test_no_capo_leaves_the_key_alone():
    assert shape_key_for("G", 0) == "G"


def test_capo_two_in_g_means_f_shapes():
    assert shape_key_for("G", 2) == "F"


def test_capo_round_trip():
    cases = [("G", 2, None), ("C", 3, None), ("Eb", 1, True), ("A", 5, None)]
    for key, capo, prefer_flats in cases:
        shape = shape_key_for(key, capo, prefer_flats)
        assert sounding_key_for(shape, capo, prefer_flats) == key


def test_flat_keys_stay_flat():
    assert shape_key_for("Bb", 3) == "G"
    assert shape_key_for("Ab", 1) == "G"


def test_capo_above_eleven_wraps():
    assert shape_key_for("C", 12) == "C"


def test_plan_describe_without_capo():
    plan = plan_for("G", 0)

    assert plan.describe() == "Original G · no capo"
    assert plan.uses_capo is False


def test_plan_describe_with_capo():
    plan = plan_for("G", 2)

    assert plan.shape_key == "F"
    assert plan.describe() == "Original G · capo 2 → play F shapes"


def test_plan_without_key_is_quiet():
    assert plan_for("", 2).describe() == ""


def test_suggest_capos_for_bb():
    capos = {plan.capo: plan.shape_key for plan in suggest_capos("Bb", max_capo=7)}

    assert capos[1] == "A"
    assert capos[3] == "G"
    assert 0 not in capos


def test_suggest_capos_respects_max():
    assert all(plan.capo <= 3 for plan in suggest_capos("Bb", max_capo=3))


def test_suggest_capos_for_unknown_key():
    assert suggest_capos("") == []


def test_plan_is_hashable_and_frozen():
    plan = CapoPlan(sounding_key="G", shape_key="F", capo=2)

    with pytest.raises(AttributeError):
        plan.capo = 3
