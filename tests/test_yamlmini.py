import pytest

from sop_contract import yamlmini


def test_scalars_and_nesting():
    doc = yamlmini.parse(
        "workflow: demo\nmaximum: 100\nratio: 1.5\nflag: true\n"
        "items:\n  - a\n  - b\nnested:\n  id: x\n  tool: y\n")
    assert doc == {"workflow": "demo", "maximum": 100, "ratio": 1.5,
                   "flag": True, "items": ["a", "b"],
                   "nested": {"id": "x", "tool": "y"}}


def test_list_of_maps():
    doc = yamlmini.parse(
        "steps:\n  - id: one\n    tool: t1\n  - id: two\n    tool: t2\n"
        "    must_not_use:\n      - t3\n")
    assert doc["steps"][0] == {"id": "one", "tool": "t1"}
    assert doc["steps"][1] == {"id": "two", "tool": "t2", "must_not_use": ["t3"]}


def test_quoted_and_comment():
    doc = yamlmini.parse('name: "a # b"  # trailing\nempty: []\n')
    assert doc == {"name": "a # b", "empty": []}


def test_bad_line_raises():
    with pytest.raises(yamlmini.YamlError):
        yamlmini.parse("just some words\n")
