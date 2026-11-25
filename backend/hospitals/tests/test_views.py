from django.core.files.uploadedfile import SimpleUploadedFile

from hospitals.models import ApprovalStatus, Hospital


def _data(**overrides):
    return {
        "email": "fresh@care.test",
        "password1": "a-long-pass-123",
        "password2": "a-long-pass-123",
        "name": "Fictional Care",
        "place": "Guruvayur",
        "phone": "0487 222 2222",
        "latitude": "10.594000",
        "longitude": "76.041000",
        "licence_proof": SimpleUploadedFile("licence.pdf", b"%PDF-1.4"),
    } | overrides


def test_register_page_renders(db, client):
    assert client.get("/register/hospital/").status_code == 200


def test_register_creates_pending_hospital_and_thanks(db, client):
    response = client.post("/register/hospital/", _data(), follow=True)

    hospital = Hospital.objects.get()
    assert hospital.approval_status == ApprovalStatus.PENDING
    assert hospital.user.email == "fresh@care.test"
    assert "Thanks — an admin will review your registration." in response.content.decode()


def test_register_with_errors_creates_nothing(db, client):
    response = client.post("/register/hospital/", _data(password2="nope-different-1"))

    assert response.status_code == 200
    assert not Hospital.objects.exists()
