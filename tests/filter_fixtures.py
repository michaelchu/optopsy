import pytest
from optopsy.enums import Period


@pytest.fixture
def test_single_filters():
    return {
    'abs_delta': (0.4, 0.5, 0.6),
    'dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    )
}


@pytest.fixture
def test_vertical_filters():
    return {
    'abs_delta': (0.4, 0.5, 0.6),
    'leg_1_abs_delta': (0.1, 0.2, 0.3),
    'leg_2_abs_delta': (0.3, 0.4, 0.5),
    'leg_3_abs_delta': (0.5, 0.6, 0.7),
    'leg_4_abs_delta': (0.7, 0.8, 0.9),

    'dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    )
}