import pytest

from core.geo import haversine_km, straight_line_minutes


def test_london_to_paris_is_about_343_km():
    assert haversine_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.5, abs=1.0)


def test_same_point_is_zero():
    assert haversine_km(10.5276, 76.2144, 10.5276, 76.2144) == 0


def test_distance_is_symmetric():
    a = haversine_km(10.5276, 76.2144, 9.9312, 76.2673)
    b = haversine_km(9.9312, 76.2673, 10.5276, 76.2144)

    assert a == pytest.approx(b)


@pytest.mark.parametrize("km,minutes", [(0, 0), (15, 30), (1, 2), (30, 60)])
def test_straight_line_minutes_at_30_kmh_rounded_up(km, minutes):
    assert straight_line_minutes(km) == minutes
