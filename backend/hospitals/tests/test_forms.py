import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.factories import UserFactory
from hospitals.forms import HospitalRegistrationForm

PDF = b"%PDF-1.4 fictional licence"


def _form(files=None, **overrides):
    data = {
        "email": "new@care.test",
        "password1": "a-long-pass-123",
        "password2": "a-long-pass-123",
        "name": "Fictional Care",
        "place": "Chalakudy",
        "phone": "0480 000 0000",
        "latitude": "10.300000",
        "longitude": "76.330000",
    } | overrides
    files = {"licence_proof": SimpleUploadedFile("licence.pdf", PDF)} if files is None else files
    return HospitalRegistrationForm(data=data, files=files)


def test_valid_form(db):
    form = _form()

    assert form.is_valid(), form.errors


@pytest.mark.parametrize("name", ["l.pdf", "l.jpg", "l.jpeg", "l.PNG"])
def test_licence_accepts_pdf_and_images(db, name):
    assert _form(files={"licence_proof": SimpleUploadedFile(name, PDF)}).is_valid()


@pytest.mark.parametrize("name", ["l.exe", "l.docx", "l"])
def test_licence_rejects_other_types(db, name):
    form = _form(files={"licence_proof": SimpleUploadedFile(name, PDF)})

    assert not form.is_valid()
    assert "licence_proof" in form.errors


def test_licence_over_5_mb_is_rejected(db):
    big = SimpleUploadedFile("licence.pdf", b"0" * (6 * 1024 * 1024))

    form = _form(files={"licence_proof": big})

    assert not form.is_valid()
    assert form.errors["licence_proof"] == ["File too large (max 5 MB)."]


def test_licence_is_required(db):
    assert "licence_proof" in _form(files={}).errors


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude", "90.5"),
        ("latitude", "-91"),
        ("longitude", "180.1"),
        ("latitude", "abc"),
        ("latitude", "nan"),
        ("longitude", "inf"),
        ("longitude", ""),
    ],
)
def test_coordinates_out_of_range(db, field, value):
    form = _form(**{field: value})

    assert not form.is_valid()
    assert field in form.errors


def test_password_validators_apply(db):
    form = _form(password1="123", password2="123")

    assert "password2" in form.errors


def test_passwords_must_match(db):
    assert "password2" in _form(password2="different-pass-456").errors


def test_email_already_used_any_case(db):
    UserFactory(email="new@care.test")

    form = _form(email="NEW@Care.test")

    assert form.errors["email"] == ["A user with that email already exists."]


def test_full_precision_google_maps_coordinates_are_rounded(db):
    # Google Maps "copy coordinates" gives ~15 decimal places; the form must accept them.
    form = _form(latitude="10.527642345678912", longitude="76.214435123456789")

    assert form.is_valid(), form.errors
    assert str(form.cleaned_data["latitude"]) == "10.527642"
    assert str(form.cleaned_data["longitude"]) == "76.214435"


def test_pasted_lat_lng_pair_in_latitude_field_is_split(db):
    form = _form(latitude="10.527642345678912, 76.214435123456789", longitude="")

    assert form.is_valid(), form.errors
    assert str(form.cleaned_data["latitude"]) == "10.527642"
    assert str(form.cleaned_data["longitude"]) == "76.214435"
