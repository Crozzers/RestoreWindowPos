import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).parent / '../src').resolve()))
from src import common, window  # noqa:E402


class TestFindMatchingRules:
    def test_sorting_typeerror(
        self, rules: list[common.Rule], windows: list[common.Window]
    ):
        # copy first rule, which matches first window
        rules = [rules[0], dataclasses.replace(rules[0])]
        # make them slightly unequal so any sort would have to use gt/lt compare
        rules[1].rule_name = 'Unnamed rule'
        try:
            window.find_matching_rules(rules, windows[0])
        except TypeError as e:
            pytest.fail(f'should not raise {e!r}')
