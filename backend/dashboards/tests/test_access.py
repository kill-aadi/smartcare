import pytest
from django.core.files.base import ContentFile

from accounts.models import Role
from core.factories import (
    DoctorFactory,
    HospitalFactory,
    PatientFactory,
    PharmacyFactory,
    UserFactory,
)
from hospitals.models import ApprovalStatus

HOMES = {
    Role.ADMIN: "/dashboard/admin/",
    Role.HOSPITAL: "/dashboard/hospital/",
    Role.DOCTOR: "/dashboard/doctor/",
    Role.PHARMACY: "/dashboard/pharmacy/",
}


def make_user(role):
    if role == Role.ADMIN:
        return UserFactory(role=Role.ADMIN)
    if role == Role.HOSPITAL:
        return HospitalFactory().user
    if role == Role.DOCTOR:
        return DoctorFactory().user
    if role == Role.PHARMACY:
        return PharmacyFactory().user
    return PatientFactory()


ALL_ROLES = [Role.ADMIN, Role.HOSPITAL, Role.DOCTOR, Role.PHARMACY, Role.PATIENT]


@pytest.mark.parametrize("role", ALL_ROLES)
@pytest.mark.parametrize("home_role,url", HOMES.items())
def test_each_dashboard_home_only_opens_for_its_role(db, client, role, home_role, url):
    client.force_login(make_user(role))

    response = client.get(url)

    assert response.status_code == (200 if role == home_role else 403)


@pytest.mark.parametrize("url", list(HOMES.values()) + ["/dashboard/"])
def test_anonymous_is_sent_to_login(client, url):
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"/login/?next={url}"


@pytest.mark.parametrize("role", list(HOMES))
def test_dashboard_root_redirects_to_role_home(db, client, role):
    client.force_login(make_user(role))

    response = client.get("/dashboard/")

    assert response.status_code == 302
    assert response.url == HOMES[role]


def test_patient_on_dashboard_is_told_to_use_the_app(db, client):
    client.force_login(PatientFactory())

    response = client.get("/dashboard/", follow=True)

    assert response.status_code == 200
    assert b"SmartCare app" in response.content


def test_pending_hospital_is_redirected_to_pending_page(db, client):
    client.force_login(HospitalFactory(approval_status=ApprovalStatus.PENDING).user)

    response = client.get("/dashboard/hospital/", follow=True)

    assert response.redirect_chain[-1][0] == "/dashboard/pending/"
    assert b"awaiting approval" in response.content


def test_rejected_hospital_sees_reason(db, client):
    hospital = HospitalFactory(
        approval_status=ApprovalStatus.REJECTED, rejection_reason="Licence is unreadable"
    )
    client.force_login(hospital.user)

    response = client.get("/dashboard/hospital/", follow=True)

    assert response.redirect_chain[-1][0] == "/dashboard/rejected/"
    assert b"Licence is unreadable" in response.content


def test_login_page_logs_in_by_email_and_lands_on_role_home(db, client):
    UserFactory(email="admin@example.test", role=Role.ADMIN)

    response = client.post(
        "/login/", {"username": "ADMIN@example.test", "password": "x-pass-123"}, follow=True
    )

    assert response.redirect_chain[-1][0] == "/dashboard/admin/"


def test_logout_is_post_only_and_logs_out(db, client):
    client.force_login(UserFactory(role=Role.ADMIN))

    assert client.get("/logout/").status_code == 405
    client.post("/logout/")
    assert client.get("/dashboard/").status_code == 302


class TestAdminHospitalReview:
    @pytest.fixture
    def admin_client(self, db, client):
        client.force_login(UserFactory(role=Role.ADMIN))
        return client

    def test_list_filters_by_status(self, admin_client):
        HospitalFactory(name="Approved One")
        HospitalFactory(name="Pending One", approval_status=ApprovalStatus.PENDING)

        response = admin_client.get("/dashboard/admin/hospitals/?status=pending")

        assert b"Pending One" in response.content
        assert b"Approved One" not in response.content

    def test_approve_from_detail_page(self, admin_client):
        hospital = HospitalFactory(approval_status=ApprovalStatus.PENDING)

        admin_client.post(f"/dashboard/admin/hospitals/{hospital.pk}/", {"action": "approve"})

        hospital.refresh_from_db()
        assert hospital.approval_status == ApprovalStatus.APPROVED

    def test_reject_without_reason_shows_error_and_keeps_pending(self, admin_client):
        hospital = HospitalFactory(approval_status=ApprovalStatus.PENDING)

        response = admin_client.post(
            f"/dashboard/admin/hospitals/{hospital.pk}/",
            {"action": "reject", "reason": ""},
            follow=True,
        )

        hospital.refresh_from_db()
        assert hospital.approval_status == ApprovalStatus.PENDING
        assert b"Please give a reason" in response.content

    def test_admin_can_download_licence(self, admin_client):
        hospital = HospitalFactory(
            licence_proof=ContentFile(b"%PDF-1.4 secret", name="licence.pdf")
        )

        response = admin_client.get(f"/dashboard/admin/hospitals/{hospital.pk}/licence/")

        assert response.status_code == 200
        assert b"".join(response.streaming_content) == b"%PDF-1.4 secret"

    def test_users_page_lists_users(self, admin_client):
        UserFactory(email="someone@example.test")

        response = admin_client.get("/dashboard/admin/users/")

        assert b"someone@example.test" in response.content


@pytest.mark.parametrize("role", [Role.HOSPITAL, Role.DOCTOR, Role.PHARMACY, Role.PATIENT])
def test_non_admin_cannot_download_licence(db, client, role):
    hospital = HospitalFactory()
    client.force_login(make_user(role) if role != Role.HOSPITAL else hospital.user)

    response = client.get(f"/dashboard/admin/hospitals/{hospital.pk}/licence/")

    assert response.status_code == 403


@pytest.mark.parametrize("prefix", ["", "./", "hospitals/../", "hospitals/photos/../../"])
def test_licences_are_never_served_from_media_url(db, client, settings, prefix):
    settings.DEBUG = True
    hospital = HospitalFactory(licence_proof=ContentFile(b"%PDF", name="licence.pdf"))

    response = client.get(f"/media/{prefix}{hospital.licence_proof.name}")

    assert response.status_code == 404


def test_public_photos_are_served_in_debug(db, client, settings):
    settings.DEBUG = True
    hospital = HospitalFactory(photo=ContentFile(b"\x89PNG fake", name="front.png"))

    response = client.get(f"/media/{hospital.photo.name}")

    assert response.status_code == 200


def test_media_not_served_when_debug_is_off(db, client, settings):
    settings.DEBUG = False
    hospital = HospitalFactory(photo=ContentFile(b"\x89PNG fake", name="front.png"))

    assert client.get(f"/media/{hospital.photo.name}").status_code == 404
