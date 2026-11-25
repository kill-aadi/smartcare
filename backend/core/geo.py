"""Straight-line distances, so "sort by nearby" needs no map API key."""

from math import asin, ceil, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0
ASSUMED_SPEED_KMH = 30  # rough town driving speed for the straight-line time estimate


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points on Earth, in kilometres."""
    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def straight_line_minutes(km: float) -> int:
    """Travel-time estimate shown as a "straight-line estimate", never as a promise."""
    return ceil(km / ASSUMED_SPEED_KMH * 60)
