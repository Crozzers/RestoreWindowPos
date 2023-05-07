import re
import sys
from pathlib import Path

from pytest import MonkeyPatch
import pytest

sys.path.insert(0, str((Path(__file__).parent / '../').resolve()))
from src import common  # noqa:E402


def test_local_path(monkeypatch: MonkeyPatch):
    def lp(*a, **kw):
        return Path(common.local_path(*a, **kw))

    base_dir = Path(__file__).parent.parent
    assert lp('./') == base_dir
    assert lp('./test') == base_dir / 'test'
    assert lp('./../') == (base_dir / '..').resolve()

    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(base_dir / 'test'), raising=False)

    assert lp(
        './') == Path(sys.executable).parent, 'base path should be executable when frozen'
    assert lp('./', asset=True) == base_dir / 'test'


def test_single_call():
    var = 0

    @common.single_call
    def increment():
        nonlocal var
        var += 1

    assert var == 0
    increment()
    assert var == 1, 'should increment counter on first call'
    increment()
    assert var == 1, 'should not increment counter after first call'


def test_size_from_rect():
    for rect in (
        (0, 0, 1920, 1080),
        (-1920, 1080, 2160, 1440)
    ):
        size = common.size_from_rect(rect)
        assert isinstance(size, tuple)
        assert size[0] == rect[2] - rect[0]
        assert size[1] == rect[3] - rect[1]


def test_reverse_dict_lookup():
    d1 = {'abc': '123'}
    assert common.reverse_dict_lookup(d1, '123') == 'abc'


def test_match():
    from src.common import match

    case = 'returns 1 when any param is None'
    assert match(0, None) == 1, case
    assert match(None, 0) == 1, case
    assert match(None, None) == 1, 'returns 1 when both params are None'

    case = 'returns 2 when both params are equal'
    assert match(123, 123) == 2, case
    assert match('456', '456') == 2, case

    case = 'returns 2 on absolute integer match'
    assert match(-123, 123) == 2, case
    assert match(-0, 0) == 2, case
    assert match(123, 456) == 0, 'returns 0 on integer mismatch'

    case = 'returns 1 on regex match'
    assert match(r'[a-c]{3}', 'abc') == 1, case
    assert match(r'[A-C]{3}', 'abc') == 1, case
    assert match(r'[A-C]{5}', 'abc') == 0, 'returns 0 on regex mismatch'

    case = 'returns 0 on regex compile error'
    regex = r'(\w{3}\)'
    with pytest.raises(re.error):
        # check that our regex DOES indeed raise an error
        re.compile(regex)
    assert match(regex, 'abc') == 0, 'returns 0 on regex error'


def test_tuple_convert():
    from src.common import tuple_convert

    pairs = (
        ([1, 2, 3], (1, 2, 3)),
        ([1, [2, 3]], (1, (2, 3))),
        ([1, [2, [3, [4, 5], 6]]], (1, (2, (3, (4, 5), 6))))
    )

    for my_list, my_tuple in pairs:
        assert tuple_convert(my_list) == my_tuple
        assert tuple_convert(my_tuple, from_=tuple, to=list) == my_list
