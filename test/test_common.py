import operator
import re
import sys
import types
import typing
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, is_dataclass
from pathlib import Path
from unittest.mock import Mock, patch

from pytest_mock import MockerFixture
import win32gui
from test.conftest import DISPLAYS1, DISPLAYS2, RULES1, RULES2, WINDOWS1, WINDOWS2

import pytest
from pytest import MonkeyPatch

sys.path.insert(0, str((Path(__file__).parent / '../').resolve()))
from src import common  # noqa:E402
from src.common import Display, Rect, Rule, Snapshot, Window, WindowType  # noqa:E402


def test_local_path(monkeypatch: MonkeyPatch):
    def lp(*a, **kw):
        return Path(common.local_path(*a, **kw))

    base_dir = Path(__file__).parent.parent
    assert lp('./') == base_dir
    assert lp('./test') == base_dir / 'test'
    assert lp('./../') == (base_dir / '..').resolve()

    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(base_dir / 'test'), raising=False)

    assert lp('./') == Path(sys.executable).parent, 'base path should be executable when frozen'
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
def test_size_from_rect(rect: Rect):
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


class TestStrToOp:
    valid_ops = {'lt': operator.lt, 'le': operator.le, 'eq': operator.eq, 'ge': operator.ge, 'gt': operator.gt}

    @pytest.mark.parametrize('name,func', valid_ops.items())
    def test_valid(self, name, func):
        assert common.str_to_op(name) is func

    @pytest.mark.parametrize(
        'name',
        (i for i in dir(operator) if i not in TestStrToOp.valid_ops),  # noqa: F821 # type: ignore
    )
    def test_invalid(self, name):
        with pytest.raises(ValueError):
            common.str_to_op(name)


@pytest.mark.parametrize(
    'input,expected',
    (([1, 2, 3], (1, 2, 3)), ([1, [2, 3]], (1, (2, 3))), ([1, [2, [3, [4, 5], 6]]], (1, (2, (3, (4, 5), 6))))),
)
def test_tuple_convert(input, expected: tuple):
    from src.common import tuple_convert

    assert tuple_convert(input) == expected
    assert tuple_convert(expected, from_=tuple, to=list) == input


def recursive_type_check(field, value, v_type):
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

    if field != 'comparison_params':
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
            recursive_type_check(field, item, sub)
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
        params=[{'a': 1, 'b': (2, '3', False)}, {'a': '4', 'b': [5, '6', True]}, {'a': 7, 'b': ['8', 9, 10]}],
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

                recursive_type_check(prop, value, p_type)

        def test_invalid(self, klass: common.JSONType):
            assert klass.from_json({}) is None

        def test_ignores_extra_info(self, klass: common.JSONType, sample_json):
            instance = klass.from_json({**sample_json, 'something': 'else'})
            assert not hasattr(instance, 'something')


# includes `Window` type, since they are pretty much the same
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

    def test_fits_display(self, klass: WindowType, mocker: MockerFixture, sample_json, display_json, expected=None):
        if expected is None:
            expected = (sample_json in WINDOWS1 and display_json in DISPLAYS1) or (
                sample_json in WINDOWS2 and display_json in DISPLAYS2
            )
        instance = klass.from_json(sample_json)
        mocker.patch.object(instance, 'get_border_and_shadow_thickness', Mock(spec=True, return_value=8))
        display_json = Display.from_json(display_json)
        assert instance.fits_display(display_json) is expected

    def test_fits_display_config(self, sample_cls: WindowType, mocker: MockerFixture, displays: list[Display]):
        mocker.patch.object(sample_cls, 'get_border_and_shadow_thickness', Mock(spec=True, return_value=8))
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

    def test_fits_display(self, klass: Rule, mocker: MockerFixture, sample_json, display_json):
        expected = (sample_json in RULES1 and display_json in DISPLAYS1) or (
            sample_json in RULES2 and display_json in DISPLAYS2
        )
        return super().test_fits_display(klass, mocker, sample_json, display_json, expected)


class TestSnapshot(TestJSONType):
    @pytest.fixture
    def klass(self):
        return Snapshot

    @pytest.fixture
    def sample_json(self, snapshot_json):
        return snapshot_json

    @pytest.fixture
    def sample_cls(self, snapshot_cls):
        return snapshot_cls

    class TestLastKnownProcessInstance:
        def test_basic(self, snapshots: list[Snapshot]):
            window = snapshots[0].history[-1].windows[0]
            assert snapshots[0].last_known_process_instance(window) is window

        def test_returns_most_recent_window(self, snapshots: list[Snapshot]):
            snapshot = deepcopy(snapshots[0])
            snapshot.history.append(deepcopy(snapshot.history[0]))

            window = snapshot.history[-1].windows[0]
            other_window = snapshot.history[0].windows[0]
            lkp = snapshot.last_known_process_instance(window)

            assert lkp is window
            assert lkp is not other_window

        def test_returns_none_if_window_not_found(self, snapshots: list[Snapshot]):
            window = deepcopy(snapshots[0].history[0].windows[0])
            window.executable = 'does-not-exist.exe'
            assert snapshots[0].last_known_process_instance(window) is None

        class TestMatchTitleKwarg:
            @pytest.fixture
            def sample(self) -> Snapshot:
                snap = Snapshot.from_json(
                    {
                        'history': [
                            {
                                'time': 0,
                                'windows': [
                                    {
                                        **WINDOWS1[0],
                                        'name': 'Some Other Website - Web Browser',
                                        'executable': 'browser.exe',
                                    },
                                    {**WINDOWS1[1], 'name': '12 Reminder(s)', 'executable': 'email.exe'},
                                ],
                            },
                            {
                                'time': 1,
                                'windows': [
                                    {
                                        **WINDOWS1[0],
                                        'name': 'Some Other Website - Web Browser',
                                        'executable': 'browser.exe',
                                    },
                                    {**WINDOWS1[2], 'name': 'My Website - Web Browser', 'executable': 'browser.exe'},
                                    {**WINDOWS1[3], 'name': 'Appointment - Email Client', 'executable': 'email.exe'},
                                    {**WINDOWS1[4], 'name': 'Inbox - Email Client', 'executable': 'email.exe'},
                                ],
                            },
                        ]
                    }
                )
                assert snap is not None
                return snap

            @pytest.mark.parametrize('title', ['12 Reminder(s)', '1 Reminder(s)', 'Email Reminder(s)'])
            def test_returns_high_overlap_title_matches(self, sample: Snapshot, title: str):
                window = deepcopy(sample.history[0].windows[0])
                window.executable = 'email.exe'
                window.name = title
                lkp = sample.last_known_process_instance(window, match_title=True)
                assert lkp is not None
                assert lkp.id == WINDOWS1[1]['id']

            def test_still_filters_by_process(self, sample: Snapshot):
                window = deepcopy(sample.history[0].windows[0])
                window.executable = 'doodad.exe'
                window.name = '12 Reminder(s)'
                lkp = sample.last_known_process_instance(window, match_title=True)
                assert lkp is None

        class TestMatchResizabilityKwarg:
            @pytest.fixture
            def sample(self) -> Snapshot:
                snap = Snapshot.from_json(
                    {
                        'history': [
                            {
                                'time': 0,
                                'windows': [{**WINDOWS1[0], 'name': 'My Document - My Program', 'resizable': True}],
                            },
                            {
                                'time': 1,
                                'windows': [{**WINDOWS1[0], 'name': 'Splash Screen - My Program', 'resizable': False}],
                            },
                        ]
                    }
                )
                assert snap is not None
                return snap

            def test_returns_windows_with_same_resizability(self, sample: Snapshot):
                window = deepcopy(sample.history[0].windows[0])
                window.resizable = False
                lkp = sample.last_known_process_instance(window, match_resizability=True)
                assert lkp is not None
                assert 'Splash Screen' in lkp.name
                window.resizable = True
                lkp2 = sample.last_known_process_instance(window, match_resizability=True)
                assert lkp2 is not None
                assert 'Splash Screen' not in lkp2.name

    class TestMatchesDisplayConfig:
        def test_basic(self, snapshots: list[Snapshot]):
            assert snapshots[0].matches_display_config(snapshots[2]) is True
            assert snapshots[0].matches_display_config(snapshots[1]) is False

        def test_config_param_types(self, snapshot_cls: Snapshot):
            assert snapshot_cls.matches_display_config(snapshot_cls) is True
            assert snapshot_cls.matches_display_config(snapshot_cls.displays) is True

        @pytest.mark.parametrize('param,expected', (('any', True), ('all', False)))
        def test_comparison_params(self, snapshots: list[Snapshot], param, expected):
            snapshots[2].comparison_params['displays'] = param
            assert snapshots[2].matches_display_config(snapshots[0]) is expected

    class TestSquashHistory:
        @pytest.fixture
        def squashable(self) -> Snapshot:
            # create copy of WINDOWS2 but with different hwnds because history squash
            # uses identical hwnds as factor in deciding which windows to squash
            windows2 = []
            for i, window in enumerate(deepcopy(WINDOWS2)):
                window['id'] = i + len(WINDOWS1)
                windows2.append(window)
            snap = Snapshot.from_json(
                {'history': [{'time': 0, 'windows': WINDOWS1[1:-1]}, {'time': 0, 'windows': WINDOWS1}]}
            )
            assert snap is not None
            return snap

        def test_previous_frames_that_overlap_are_removed(self, squashable: Snapshot):
            lesser, greater = squashable.history
            with patch.object(win32gui, 'IsWindow', Mock(return_value=1)):
                squashable.squash_history()
            assert greater in squashable.history
            assert lesser not in squashable.history

        def test_newer_frames_that_overlap_are_removed(self, squashable: Snapshot):
            lesser, greater = squashable.history
            squashable.history = list(reversed(squashable.history))
            with patch.object(win32gui, 'IsWindow', Mock(return_value=1)):
                squashable.squash_history(False)
            assert greater in squashable.history
            assert lesser not in squashable.history

        def test_pruning(self, squashable: Snapshot):
            lesser, greater = squashable.history
            squashable.history = list(reversed(squashable.history))
            with patch.object(win32gui, 'IsWindow', Mock(return_value=1)):
                squashable.squash_history()
            assert len(squashable.history) == 1
            assert greater == lesser, 'greater should have had dead windows pruned'
