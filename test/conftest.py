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
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).parent / '../').resolve()))
from src import common  # noqa:E402

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


@pytest.fixture
def displays1():
    return [common.Display.from_json(d) for d in DISPLAYS1]


@pytest.fixture
def displays2():
    return [common.Display.from_json(d) for d in DISPLAYS2]


@pytest.fixture
def displays(displays1, displays2):
    return displays1 + displays2


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


@pytest.fixture
def windows1():
    return [common.Window.from_json(d) for d in WINDOWS1]


@pytest.fixture
def windows2():
    return [common.Window.from_json(d) for d in WINDOWS2]


@pytest.fixture
def windows(windows1, windows2):
    return windows1 + windows2


RULES1 = []
RULES2 = []


def populate_rules():
    for w_list, r_list in zip((WINDOWS1, WINDOWS2), (RULES1, RULES2)):
        for window in w_list:
            rule = deepcopy(window)
            del rule['id']
            rule['rule_name'] = rule['name'].replace('window', 'rule').strip()
            rule['name'] = rule['name'].lower().replace('window', '').strip()
            r_list.append(rule)


# saves cleaning up all the loop vars
populate_rules()
del populate_rules
RULES = RULES1 + RULES2
assert len(RULES1) == len(RULES2), 'should be same number of rules per config'


@pytest.fixture
def rules1():
    return [common.Rule.from_json(d) for d in RULES1]


@pytest.fixture
def rules2():
    return [common.Rule.from_json(d) for d in RULES2]


@pytest.fixture
def rules(rules1, rules2):
    return rules1 + rules2


@pytest.fixture
def snapshot0_json():
    '''
    Combines `DISPLAYS*` and both `WINDOWS*` and `RULES*` lists
    '''
    return {
        'displays': deepcopy(DISPLAYS),
        'history': [
            {'time': 1677924200, 'windows': deepcopy(WINDOWS)},
        ],
        'mru': None,
        'rules': deepcopy(RULES),
        'phony': '',
    }


@pytest.fixture
def snapshot1_json():
    return {
        'displays': [deepcopy(DISPLAYS1)],
        'history': [
            {'time': 1677924200, 'windows': deepcopy(WINDOWS1)},
        ],
        'mru': None,
        'rules': deepcopy(RULES1),
        'phony': '',
    }


@pytest.fixture
def snapshot2_json():
    return {
        'displays': [deepcopy(DISPLAYS2)],
        'history': [
            {'time': 1677924200, 'windows': deepcopy(WINDOWS2)},
        ],
        'mru': None,
        'rules': deepcopy(RULES2),
        'phony': '',
    }


@pytest.fixture
def snapshot0(snapshot0_json: dict) -> common.Snapshot:
    return common.Snapshot.from_json(snapshot0_json)


@pytest.fixture
def snapshot1(snapshot1_json: dict) -> common.Snapshot:
    return common.Snapshot.from_json(snapshot1_json)


@pytest.fixture
def snapshot2(snapshot2_json: dict) -> common.Snapshot:
    return common.Snapshot.from_json(snapshot2_json)
