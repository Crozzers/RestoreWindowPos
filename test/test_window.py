import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).parent / '../src').resolve()))
from src import common, window  # noqa:E402


class TestFindMatchingRules:
    def test_sorting_typeerror(
        self, rule_cls: common.Rule, window_cls: common.Window
    ):
        # copy first rule, which matches first window
        rule_cls = [rule_cls, dataclasses.replace(rule_cls)]
        # make them slightly unequal so any sort would have to use gt/lt compare
        rule_cls[1].rule_name = 'Unnamed rule'
        try:
            window.find_matching_rules(rule_cls, window_cls)
        except TypeError as e:
            pytest.fail(f'should not raise {e!r}')
