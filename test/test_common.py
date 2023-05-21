import re
import sys
import types
import typing
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, is_dataclass
from pathlib import Path
from test.conftest import DISPLAYS1, DISPLAYS2, RULES1, RULES2, WINDOWS1, WINDOWS2

import pytest
from pytest import MonkeyPatch

sys.path.insert(0, str((Path(__file__).parent / '../').resolve()))
from src import common  # noqa:E402
from src.common import Display, Rule, Window, WindowType  # noqa:E402


def test_local_path(monkeypatch: MonkeyPatch):
    def lp(*a, **kw):
        return Path(common.local_path(*a, **kw))

    base_dir = Path(__file__).parent.parent
    assert lp('./') == base_dir
    assert lp('./test') == base_dir / 'test'
    assert lp('./../') == (base_dir / '..').resolve()

    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(base_dir / 'test'), raising=False)

    assert (
        lp('./') == Path(sys.executable).parent
    ), 'base path should be executable when frozen'
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


@pytest.mark.parametrize('rect', ((0, 0, 1920, 1080), (-1920, 1080, 2160, 1440)))
def test_size_from_rect(rect: tuple[int]):
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


@pytest.mark.parametrize(
    'input,expected',
    (
        ([1, 2, 3], (1, 2, 3)),
        ([1, [2, 3]], (1, (2, 3))),
        ([1, [2, [3, [4, 5], 6]]], (1, (2, (3, (4, 5), 6)))),
    ),
)
def test_tuple_convert(input, expected: tuple):
    from src.common import tuple_convert

    assert tuple_convert(input) == expected
    assert tuple_convert(expected, from_=tuple, to=list) == input


def recursive_type_check(value, v_type):
    sub_types = typing.get_args(v_type)
    if not sub_types:
        # no parameterized types, eg: int or str
        assert isinstance(value, v_type)
        return

    # get the original type from the generic
    # tuple[int, int] -> tuple
    o_type = typing.get_origin(v_type)
    if issubclass(o_type, types.UnionType):
        assert isinstance(value, sub_types)
        return
    else:
        assert isinstance(value, o_type)

    # some typing guides for better dataclasses
    assert o_type != dict, 'use a dataclass instead of dict'
    if o_type == list:
        assert len(sub_types) == 1, 'lists should be homogeneous'

    # sub_types is truthy, so value must be iterable
    # check each item matches it's corresponding sub_type
    for index, item in enumerate(value):
        # lists are homogeneous, others are positional
        sub = sub_types[0 if o_type == list else index]
        # get origin of sub_type in case of nested param generics
        o_sub = typing.get_origin(sub) or sub
        if issubclass(o_sub, Iterable):
            recursive_type_check(item, sub)
        else:
            assert isinstance(item, sub)


class TestJSONType:
    @pytest.fixture
    def klass(self):
        @dataclass
        class Sample(common.JSONType):
            a: int
            b: tuple[int, str, bool]

        return Sample

    @pytest.fixture(
        params=[
            {'a': 1, 'b': (2, '3', False)},
            {'a': '4', 'b': [5, '6', True]},
            {'a': 7, 'b': ['8', 9, 10]},
        ],
        ids=['standard', 'compliant-types', 'tuple-sub-types'],
    )
    def sample_json(self, request):
        return request.param

    class TestFromJson:
        def test_basic(self, klass: common.JSONType, sample_json):
            base = klass.from_json(sample_json)
            # check base was initialized correctly
            assert is_dataclass(base)
            assert isinstance(base, klass)

            # check each field
            hints = typing.get_type_hints(klass)
            for prop, p_type in hints.items():
                assert hasattr(base, prop)
                value = getattr(base, prop)

                recursive_type_check(value, p_type)

        def test_invalid(self, klass: common.JSONType):
            assert klass.from_json({}) is None

        def test_ignores_extra_info(self, klass: common.JSONType, sample_json):
            instance = klass.from_json({**sample_json, 'something': 'else'})
            assert not hasattr(instance, 'something')


# includes Window type, since they are pretty much the same
class TestWindowType(TestJSONType):
    @pytest.fixture(params=[WindowType, Window])
    def klass(self, request):
        return request.param

    @pytest.fixture
    def sample_json(self, window_json):
        return window_json

    @pytest.fixture
    def sample_cls(self, window_cls):
        return window_cls

    def test_fits_display(
        self, klass: WindowType, sample_json, display_json, expected=None
    ):
        if expected is None:
            expected = (sample_json in WINDOWS1 and display_json in DISPLAYS1) or (
                sample_json in WINDOWS2 and display_json in DISPLAYS2
            )
        instance = klass.from_json(sample_json)
        display_json = Display.from_json(display_json)
        assert instance.fits_display(display_json) is expected

    def test_fits_display_config(self, sample_cls: WindowType, displays: list[Display]):
        assert sample_cls.fits_display_config(displays) is True


class TestRule(TestWindowType):
    @pytest.fixture
    def klass(self):
        return Rule

    @pytest.fixture
    def sample_json(self, rule_json):
        return rule_json

    @pytest.fixture
    def sample_cls(self, rule_cls):
        return rule_cls

    def test_post_init(self, klass: Rule):
        rule = deepcopy(RULES1[0])
        del rule['rule_name']
        instance = klass.from_json(rule)
        assert instance.name is not None
        assert isinstance(instance.name, str)

    def test_fits_display(self, klass: Rule, sample_json, display_json):
        expected = (sample_json in RULES1 and display_json in DISPLAYS1) or (
            sample_json in RULES2 and display_json in DISPLAYS2
        )
        return super().test_fits_display(klass, sample_json, display_json, expected)
