import pytest

from app.schemas.indicators import DamageLevel, Need
from app.services.nlp import structure_field_report

README_REPORT = (
    "Derrumbe de viviendas en el sector Alto Perú. Hay 35 familias afectadas, unas 140"
    " personas, entre ellas 40 niños y 15 adultos mayores. Urge agua potable, alimentos y carpas."
)


def test_complete_report_extracts_every_indicator() -> None:
    report = structure_field_report(
        README_REPORT + " También hay 6 personas con discapacidad y faltan medicamentos."
    )

    indicators = report.indicators
    assert indicators.damage_level == DamageLevel.SEVERE
    assert indicators.families_affected == 35
    assert indicators.people_affected == 140
    assert indicators.children == 40
    assert indicators.elderly_people == 15
    assert indicators.disabled_people == 6
    assert indicators.needs == [Need.WATER, Need.FOOD, Need.SHELTER, Need.MEDICINE]
    assert report.missing_variables == []


def test_variables_not_found_are_null_and_listed_as_missing() -> None:
    report = structure_field_report(README_REPORT)

    assert report.indicators.disabled_people is None
    assert report.missing_variables == ["disabledPeople"]


def test_ambiguous_report_marks_every_variable_as_missing() -> None:
    report = structure_field_report("Se reportan problemas en la zona, se pide apoyo.")

    assert report.indicators.damage_level is None
    assert report.indicators.needs == []
    assert report.missing_variables == [
        "damageLevel",
        "familiesAffected",
        "peopleAffected",
        "children",
        "elderlyPeople",
        "disabledPeople",
        "needs",
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.200 damnificados", 1200),
        ("1,200 damnificados", 1200),
        ("80 habitantes afectados", 80),
        ("30 personas y luego otras 120 personas", 120),
    ],
)
def test_people_affected_reads_separators_and_keeps_the_largest(text: str, expected: int) -> None:
    assert structure_field_report(text).indicators.people_affected == expected


@pytest.mark.parametrize(
    ("text", "field", "expected"),
    [
        ("8 personas con discapacidad", "disabled_people", 8),
        ("8 discapacitados", "disabled_people", 8),
        ("12 personas de la tercera edad", "elderly_people", 12),
        ("12 ancianos", "elderly_people", 12),
        ("25 menores", "children", 25),
        ("1 familia", "families_affected", 1),
    ],
)
def test_vulnerable_groups_are_recognized(text: str, field: str, expected: int) -> None:
    assert getattr(structure_field_report(text).indicators, field) == expected


@pytest.mark.parametrize(
    "text",
    ["8 personas con discapacidad", "12 personas de la tercera edad"],
)
def test_vulnerable_groups_are_not_counted_as_people_affected(text: str) -> None:
    assert structure_field_report(text).indicators.people_affected is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Daños leves en algunas fachadas", DamageLevel.LOW),
        ("Viviendas con grietas", DamageLevel.MODERATE),
        ("Calles inundadas", DamageLevel.MODERATE),
        ("Viviendas colapsadas", DamageLevel.SEVERE),
        ("COLAPSO TOTAL del puente", DamageLevel.CRITICAL),
        ("Grietas en muros y colapso total de 3 casas", DamageLevel.CRITICAL),
    ],
)
def test_damage_level_takes_the_highest_level_found(text: str, expected: DamageLevel) -> None:
    assert structure_field_report(text).indicators.damage_level == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Necesitan agua", [Need.WATER]),
        ("Calles inundadas por el agua del río", []),
        ("Faltan víveres y frazadas", [Need.FOOD, Need.SHELTER]),
        ("Se requieren kits de limpieza y pañales", [Need.HYGIENE]),
        ("Urge atención médica", [Need.MEDICINE]),
    ],
)
def test_needs_come_from_the_dictionary(text: str, expected: list[Need]) -> None:
    assert structure_field_report(text).indicators.needs == expected
