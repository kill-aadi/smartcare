from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.factories import DoctorFactory, HospitalFactory, PatientFactory, PharmacyFactory
from hospitals.models import ApprovalStatus

THRISSUR = ("10.527642", "76.214435")


@pytest.fixture
def api(db):
    client = APIClient()
    client.force_authenticate(PatientFactory())
    return client


def _at(lat, lng, **kwargs):
    return HospitalFactory(latitude=Decimal(lat), longitude=Decimal(lng), **kwargs)


def test_list_without_location_is_sorted_by_name_with_null_distance(api):
    _at("10.3", "76.3", name="Beta Care")
    _at("10.4", "76.2", name="Alpha Care")

    response = api.get("/api/hospitals/")

    assert response.status_code == 200
    assert [h["name"] for h in response.data] == ["Alpha Care", "Beta Care"]
    assert response.data[0]["distance_km"] is None
    assert response.data[0]["straight_line_minutes"] is None


def test_nearby_sorts_by_distance_and_adds_estimate(api):
    _at("10.594", "76.041", name="Far")  # Guruvayur, ~20 km
    _at("10.528", "76.215", name="Here")  # Thrissur
    _at("10.343", "76.211", name="Middle")  # Irinjalakuda, ~20 km south

    response = api.get("/api/hospitals/", {"lat": THRISSUR[0], "lng": THRISSUR[1]})

    names = [h["name"] for h in response.data]
    assert names[0] == "Here"
    assert set(names) == {"Here", "Far", "Middle"}
    distances = [h["distance_km"] for h in response.data]
    assert distances == sorted(distances)
    assert response.data[0]["distance_km"] == pytest.approx(0.0, abs=0.2)
    assert all(isinstance(h["straight_line_minutes"], int) for h in response.data)


def test_item_shape(api):
    HospitalFactory()

    item = api.get("/api/hospitals/").data[0]

    assert set(item) == {
        "id",
        "name",
        "place",
        "phone",
        "email",
        "photo_url",
        "latitude",
        "longitude",
        "distance_km",
        "straight_line_minutes",
    }


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_unapproved_hospitals_never_listed_or_shown(api, status):
    hidden = HospitalFactory(approval_status=status)

    assert api.get("/api/hospitals/").data == []
    assert api.get(f"/api/hospitals/{hidden.pk}/").status_code == 404
    assert api.get(f"/api/hospitals/{hidden.pk}/pharmacies/").status_code == 404


def test_search_matches_place_case_insensitively(api):
    HospitalFactory(name="One", place="Chalakudy")
    HospitalFactory(name="Two", place="Thrissur")

    response = api.get("/api/hospitals/", {"search": "chala"})

    assert [h["name"] for h in response.data] == ["One"]


@pytest.mark.parametrize(
    "params",
    [{"lat": "abc", "lng": "76.2"}, {"lat": "10.5"}, {"lat": "91", "lng": "76"}, {"lng": "200"}],
)
def test_bad_location_is_400(api, params):
    assert api.get("/api/hospitals/", params).status_code == 400


def test_list_is_capped_at_50(api):
    HospitalFactory.create_batch(55)

    assert len(api.get("/api/hospitals/").data) == 50


def test_detail_and_pharmacies(api):
    hospital = HospitalFactory()
    PharmacyFactory(hospital=hospital, name="Ward Pharmacy")
    PharmacyFactory(name="Elsewhere")

    assert api.get(f"/api/hospitals/{hospital.pk}/").data["name"] == hospital.name
    response = api.get(f"/api/hospitals/{hospital.pk}/pharmacies/")
    assert [p["name"] for p in response.data] == ["Ward Pharmacy"]
    assert set(response.data[0]) == {"id", "name", "phone"}


def test_staff_cannot_use_catalogue(db):
    client = APIClient()
    client.force_authenticate(DoctorFactory().user)

    assert client.get("/api/hospitals/").status_code == 403


def test_anonymous_gets_401(db):
    assert APIClient().get("/api/hospitals/").status_code == 401


def test_nearest_hospital_is_found_even_beyond_the_first_50_by_name(api):
    for i in range(55):
        _at("12.000000", "77.000000", name=f"A Far {i:02d}")  # ~170 km away, sort first by name
    _at("10.528000", "76.215000", name="Z Nearest")

    response = api.get("/api/hospitals/", {"lat": THRISSUR[0], "lng": THRISSUR[1]})

    assert len(response.data) == 50
    assert response.data[0]["name"] == "Z Nearest"
