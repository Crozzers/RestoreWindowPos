import dataclasses
import sys
from pathlib import Path

import pytest
import win32con
from pytest_mock import MockerFixture

sys.path.insert(0, str((Path(__file__).parent / '../src').resolve()))
from src import common, window  # noqa:E402


class TestIsWindowValid:
    @pytest.fixture
    def mock_checks(self, mocker: MockerFixture, request: pytest.FixtureRequest):
        patches = {
            'win32gui.IsWindow': True,
            'win32gui.IsWindowVisible': True,
            'win32gui.GetWindowText': 'abc',
            'win32gui.GetWindowRect': (1, 2, 3, 4),
            # need full "module" name for mock to work
            'src.window.is_window_cloaked': False,
        }
        for name, ret_val in patches.items():
            mocker.patch(name, return_value=ret_val)
        return patches

    def test_basic_success(self, mock_checks):
        assert window.is_window_valid(1234) is True

    @pytest.mark.parametrize(
        'index,value',
        ((0, False), (1, False), (2, ''), (3, (0, 0, 0, 0)), (4, True)),
        ids=[
            'is-not-window',
            'window-not-visible',
            'empty-title-bar',
            'zeroed-rect',
            'cloaked-window',
        ],
    )
    def test_basic_rejections(
        self, mocker: MockerFixture, mock_checks: dict, index: int, value
    ):
        func_name = tuple(mock_checks.keys())[index]
        mocker.patch(func_name, return_value=value)
        assert window.is_window_valid(1234) is False

    @pytest.mark.parametrize(
        'state,expected',
        (
            (0, True),
            (win32con.STATE_SYSTEM_FOCUSABLE, True),
            (win32con.STATE_SYSTEM_INVISIBLE, False),
            (win32con.STATE_SYSTEM_INVISIBLE | win32con.STATE_SYSTEM_FOCUSABLE, False),
        ),
        ids=[
            'no-state',
            'not-state-invisible',
            'state-invisible',
            'state-includes-invisible',
        ],
    )
    def test_titlebar_rejection(
        self, mocker: MockerFixture, mock_checks, state, expected
    ):
        def fake_titlebar_info(_, titlebar_ref):
            titlebar_ref._obj.rgState[0] = state  # nonlocal
            return 0

        mocker.patch('ctypes.windll.user32.GetTitleBarInfo', new=fake_titlebar_info)
        assert window.is_window_valid(1234) is expected


class TestFindMatchingRules:
    def test_sorting_typeerror(self, rule_cls: common.Rule, window_cls: common.Window):
        # copy first rule, which matches first window
        rule_cls = [rule_cls, dataclasses.replace(rule_cls)]
        # make them slightly unequal so any sort would have to use gt/lt compare
        rule_cls[1].rule_name = 'Unnamed rule'
        try:
            window.find_matching_rules(rule_cls, window_cls)
        except TypeError as e:
            pytest.fail(f'should not raise {e!r}')
