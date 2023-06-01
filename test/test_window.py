import dataclasses
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

sys.path.insert(0, str((Path(__file__).parent / '../src').resolve()))
from src import common, window  # noqa:E402


class TestIsWindowValid:
    @pytest.fixture(
        params=[(0, False), (1, False), (2, ''), (3, (0, 0, 0, 0))],
        ids=['is-not-window', 'window-not-visible', 'empty-title-bar', 'zeroed-rect'],
    )
    def mock_checks(self, mocker: MockerFixture, request: pytest.FixtureRequest):
        patches = [
            ['win32gui.IsWindow', True],
            ['win32gui.IsWindowVisible', True],
            ['win32gui.GetWindowText', 'abc'],
            ['win32gui.GetWindowRect', (1, 2, 3, 4)],
        ]
        patches[request.param[0]][1] = request.param[1]
        for name, ret_val in patches:
            mocker.patch(name, return_value=ret_val)

    def test_basic_rejections(self, mock_checks):
        from window import is_window_valid

        assert is_window_valid(1234) is False


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
