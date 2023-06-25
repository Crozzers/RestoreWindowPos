'''
This file contains sample data used for testing. Much of the sample data is
split for different display configurations, but grouped by numbering.

For example, `DISPLAYS1`, `WINDOWS1` and `RULES1` all go together to form a
cohesive snapshot, where the windows fit in the display and the rules match
the windows.

`(DISPLAYS|WINDOWS|RULES)2` are grouped similarly, but aren't compatible with
group 1.

The generic lists (`DISPLAYS`, `RULES`, etc...) simply combine all groups into
a single list
'''
import importlib.util
import os
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import pytest

__pyvda_utils = Path(importlib.util.find_spec('pyvda').origin).parent / 'utils.py'

sys.path.insert(0, str((Path(__file__).parent / '../').resolve()))
from src import common  # noqa:E402


if os.getenv('GITHUB_ACTIONS') == 'true':

    def pytest_sessionstart():
        shutil.copyfile(__pyvda_utils, __pyvda_utils.parent / 'utils-old.py')

        with open(__pyvda_utils, 'r') as f:
            contents = f.read().replace(
                'def get_vd_manager_internal2():',
                'def get_vd_manager_internal2():\n    return get_vd_manager_internal()',
            )

        with open(__pyvda_utils, 'w') as f:
            f.write(contents)

    def pytest_sessionfinish():
        utils_old = __pyvda_utils.parent / 'utils-old.py'
        shutil.copyfile(utils_old, __pyvda_utils)
        os.remove(utils_old)


DISPLAYS1 = [
    {
        'uid': 'UID11111',
        'name': 'Display1',
        'resolution': [2560, 1440],
        'rect': [0, 0, 2560, 1440],
        'comparison_params': {},
    }
]
DISPLAYS2 = [
    {
        'uid': 'UID22222',
        'name': 'Display2',
        'resolution': [1920, 1080],
        'rect': [-1920, 0, 0, 1080],
        'comparison_params': {},
    },
]
DISPLAYS = DISPLAYS1 + DISPLAYS2


@pytest.fixture(params=DISPLAYS)
def display_json(request: pytest.FixtureRequest):
    return request.param


@pytest.fixture
def display_cls(display_json):
    return common.Display.from_json(display_json)


@pytest.fixture
def displays():
    return [common.Display.from_json(d) for d in DISPLAYS]


# windows that match DISPLAYS1
WINDOWS1 = [
    {
        'size': [2560, 1440],
        'rect': [-8, -8, 2568, 1448],  # mimic maximised window
        'placement': [2, 3, [-1, -1], [-1, -1], [-8, -8, 2568, 1448]],
        'id': 1,
        'name': 'Maximised window 1',
        'executable': 'C:\\Program Files\\MyProgram1\\maximised.exe',
    },
    {
        # minimised windows often have wonky size and rect
        'size': [160, 28],
        'rect': [-32000, -32000, -31840, -31972],
        'placement': [
            2,
            2,
            [-32000, -32000],
            [-1, -1],
            [19, 203, 1239, 864],
        ],
        'id': 2,
        'name': 'Minimised window 1',
        'executable': 'C:\\Program Files\\MyProgram1\\minimised.exe',
    },
    {
        'size': [300, 200],
        'rect': [100, 100, 400, 300],
        'placement': [0, 1, [-1, -1], [-1, -1], [100, 100, 400, 300]],
        'id': 3,
        'name': 'Floating window 1',
        'executable': 'C:\\Program Files\\MyProgram1\\floating.exe',
    },
    {
        'size': [1290, 1405],
        'rect': [-5, 0, 1285, 1405],
        'placement': [0, 1, [-1, -1], [-1, -1], [-5, 0, 1285, 1405]],
        'id': 4,
        'name': 'Snapped LHS window 1',  # left hand side
        'executable': 'C:\\Program Files\\MyProgram1\\snapped-lhs.exe',
    },
    {
        'size': [1290, 705],
        'rect': [1275, 0, 2565, 705],
        'placement': [0, 1, [-1, -1], [-1, -1], [1275, 0, 2565, 705]],
        'id': 5,
        'name': 'Snapped RUQ window 1',  # right upper quarter
        'executable': 'C:\\Program Files\\MyProgram1\\snapped-ruq.exe',
    },
]
# windows that match DISPLAYS2
WINDOWS2 = [
    {
        'size': [1920, 1080],
        'rect': [-1928, -8, 8, 1088],  # mimic maximised window
        'placement': [2, 3, [-1, -1], [-1, -1], [-1500, 100, -150, 600]],
        'id': 1,
        'name': 'Maximised window 2',
        'executable': 'C:\\Program Files\\MyProgram2\\maximised.exe',
    },
    {
        # minimised windows often have wonky size and rects
        'size': [160, 28],
        'rect': [-32000, -32000, -31840, -31972],
        'placement': [2, 2, [-32000, -32000], [-1, -1], [-1549, 55, -579, 693]],
        'id': 2,
        'name': 'Minimised window 2',
        'executable': 'C:\\Program Files\\MyProgram2\\minimised.exe',
    },
    {
        'size': [300, 200],
        'rect': [-1500, 100, -1300, 200],
        'placement': [0, 1, [-1, -1], [-1, -1], [100, 100, 400, 300]],
        'id': 3,
        'name': 'Floating window 2',
        'executable': 'C:\\Program Files\\MyProgram2\\floating.exe',
    },
    {
        'size': [970, 1045],
        'rect': [-1925, 0, -955, 1045],
        'placement': [2, 1, [-32000, -32000], [-1, -1], [-2403, 548, -1433, 1186]],
        'id': 4,
        'name': 'Snapped LHS window 2',  # left hand side
        'executable': 'C:\\Program Files\\MyProgram2\\snapped-lhs.exe',
    },
    {
        'size': [970, 520],
        'rect': [-965, 0, 5, 520],
        'placement': [2, 1, [-32000, -32000], [-1, -1], [-443, 25, 527, 663]],
        'id': 5,
        'name': 'Snapped RUQ window 2',  # right upper quarter
        'executable': 'C:\\Program Files\\MyProgram2\\snapped-ruq.exe',
    },
]
WINDOWS = WINDOWS1 + WINDOWS2
assert len(WINDOWS1) == len(WINDOWS2), 'should be same number of windows per config'


@pytest.fixture(params=WINDOWS)
def window_json(request: pytest.FixtureRequest):
    return request.param


@pytest.fixture()
def window_cls(window_json):
    return common.Window.from_json(window_json)


RULES1 = []
RULES2 = []


def populate_rules():
    for w_list, r_list in zip((WINDOWS1, WINDOWS2), (RULES1, RULES2)):
        for window in w_list:
            rule = deepcopy(window)
            del rule['id']
            rule['rule_name'] = rule['name'].replace('window', 'rule').strip()
            rule['name'] = rule['name'].lower().replace('window ', '').strip()
            r_list.append(rule)


# saves cleaning up all the loop vars
populate_rules()
del populate_rules
RULES = RULES1 + RULES2
assert len(RULES1) == len(RULES2), 'should be same number of rules per config'


@pytest.fixture(params=RULES)
def rule_json(request: pytest.FixtureRequest):
    return request.param


@pytest.fixture
def rule_cls(rule_json):
    return common.Rule.from_json(rule_json)


@pytest.fixture(
    params=(
        (DISPLAYS1, WINDOWS1, RULES1),
        (DISPLAYS2, WINDOWS2, RULES2),
        (DISPLAYS, WINDOWS, RULES),
    )
)
def snapshot_json(request: pytest.FixtureRequest):
    '''
    Combines `DISPLAYS*` and both `WINDOWS*` and `RULES*` lists
    '''
    displays, windows, rules = request.param
    return {
        'displays': deepcopy(displays),
        'history': [
            {'time': 1677924200, 'windows': deepcopy(windows)},
        ],
        'mru': None,
        'rules': deepcopy(rules),
        'phony': '',
    }


@pytest.fixture
def snapshot_cls(snapshot_json) -> common.Snapshot:
    return common.Snapshot.from_json(snapshot_json)


@pytest.fixture
def snapshots() -> list[common.Snapshot]:
    snapshots = []
    for d, w, r in (
        (DISPLAYS1, WINDOWS1, RULES1),
        (DISPLAYS2, WINDOWS2, RULES2),
        (DISPLAYS, WINDOWS, RULES),
    ):
        snapshots.append(
            common.Snapshot.from_json(
                {
                    'displays': deepcopy(d),
                    'history': [
                        {'time': 1677924200, 'windows': deepcopy(w)},
                    ],
                    'mru': None,
                    'rules': deepcopy(r),
                    'phony': '',
                }
            )
        )
    return snapshots
