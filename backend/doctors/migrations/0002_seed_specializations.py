"""Seed the canonical specialisations. The ML mapping and seed_demo use exactly these names."""

from django.db import migrations

NAMES = [
    "General Physician",
    "Dermatology",
    "Pulmonology",
    "Cardiology",
    "Neurology",
    "Orthopaedics",
    "Gastroenterology",
    "Urology",
    "Endocrinology",
    "General Surgery",
    "ENT",
    "Gynaecology",
]

DESCRIPTIONS = {
    "General Physician": "Everyday illnesses such as fever, infections, colds and general check-ups.",
    "Dermatology": "Skin, hair and nail problems such as rashes, acne, itching and patches.",
    "Pulmonology": "Lungs and breathing, such as cough, asthma, breathlessness and chest infections.",
    "Cardiology": "Heart and blood pressure, such as chest pain, palpitations and hypertension.",
    "Neurology": "Brain and nerves, such as headaches, migraines, dizziness and numbness.",
    "Orthopaedics": "Bones, joints and muscles, such as joint pain, back and neck pain and injuries.",
    "Gastroenterology": "Stomach, gut and liver, such as acidity, abdominal pain and jaundice.",
    "Urology": "Kidneys and bladder, such as painful or frequent urination and urinary infections.",
    "Endocrinology": "Hormones and metabolism, such as diabetes, thyroid problems and weight changes.",
    "General Surgery": "Problems that may need an operation, such as hernias, lumps and varicose veins.",
    "ENT": "Ear, nose and throat, such as earache, sinus problems and sore throat.",
    "Gynaecology": "Women's reproductive health, such as periods, pregnancy and pelvic pain.",
}


def seed(apps, schema_editor):
    Specialization = apps.get_model("doctors", "Specialization")
    for name in NAMES:
        Specialization.objects.update_or_create(
            name=name, defaults={"description": DESCRIPTIONS[name]}
        )


def unseed(apps, schema_editor):
    apps.get_model("doctors", "Specialization").objects.filter(name__in=NAMES).delete()


class Migration(migrations.Migration):
    dependencies = [("doctors", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
