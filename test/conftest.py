import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str((Path(__file__).parent / '../').resolve()))
from src import common  # noqa:E402


@pytest.fixture
def displays():
    disp = [
        {
            'uid': 'UID11111',
            'name': 'Display1',
            'resolution': [2560, 1440],
            'rect': [0, 0, 2560, 1440],
            'comparison_params': {},
        },
        {
            'uid': 'UID22222',
            'name': 'Display2',
            'resolution': [1920, 1080],
            'rect': [-1920, 0, 0, 1080],
            'comparison_params': {},
        },
    ]
    return [common.Display.from_json(d) for d in disp]


@pytest.fixture
def windows():
    window = [
        {
            'size': [1920, 1080],
            'rect': [-1928, -8, 8, 1088],  # mimic maximised window
            'placement': [2, 3, [-1, -1], [-1, -1], [-1500, 100, -150, 600]],
            'id': 1,
            'name': 'Maximised window',
            'executable': 'C:\\Program Files\\MyProgram\\maximised.exe',
        },
        {
            'size': [160, 28],
            'rect': [
                -32000,
                -32000,
                -31840,
                -31972,
            ],  # minimised windows often have wonky rects
            'placement': [2, 2, [-32000, -32000], [-1, -1], [19, 203, 1239, 864]],
            'id': 2,
            'name': 'Minimised window',
            'executable': 'C:\\Program Files\\MyProgram\\minimised.exe',
        },
        {
            'size': [300, 200],
            'rect': [100, 100, 400, 300],
            'placement': [0, 1, [-1, -1], [-1, -1], [100, 100, 400, 300]],
            'id': 3,
            'name': 'Floating window',
            'executable': 'C:\\Program Files\\MyProgram\\floating.exe',
        },
        {
            'size': [1290, 1405],
            'rect': [-5, 0, 1285, 1405],
            'placement': [0, 1, [-1, -1], [-1, -1], [-5, 0, 1285, 1405]],
            'id': 4,
            'name': 'Snapped LHS window',  # left hand side
            'executable': 'C:\\Program Files\\MyProgram\\snapped-lhs.exe',
        },
        {
            'size': [1290, 705],
            'rect': [1275, 0, 2565, 705],
            'placement': [0, 1, [-1, -1], [-1, -1], [1275, 0, 2565, 705]],
            'id': 5,
            'name': 'Snapped RUQ window',  # right upper quarter
            'executable': 'C:\\Program Files\\MyProgram\\snapped-ruq.exe',
        },
    ]
    return [common.Window.from_json(w) for w in window]


@pytest.fixture
def rules(windows: list[common.Window]):
    '''
    Generate rules using the `windows` fixture. Each rule matches with the
    corresponding window in said fixture
    '''
    rule = []
    for window in windows:
        window = asdict(window)
        del window['id']
        window['rule_name'] = window['name'].replace('window', 'rule').strip()
        window['name'] = window['name'].lower().replace('window', '').strip()
        rule.append(common.Rule.from_json(window))
    return rule
