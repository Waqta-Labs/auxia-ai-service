"""Extraction of field indicators from a report written in Spanish (rules-v1).

The text is normalized (lowercase, no accents) and read with explicit rules:

- Counts are numbers written with digits, followed by the group they count:
  "35 familias", "140 personas", "40 niños", "15 adultos mayores",
  "3 personas con discapacidad". Thousands separators are accepted
  ("1.200", "1,200"). When a group is mentioned several times, the largest
  number is kept. Numbers written with words are not recognized.
- The damage level comes from a dictionary of terms. When terms of several
  levels appear, the highest level wins.
- The needs come from another dictionary and are listed in the order of Need.

Anything that is not found stays None (or an empty list for needs) and is
reported as missing.
"""

import re
import unicodedata
from dataclasses import dataclass

from app.schemas.indicators import DamageLevel, FieldIndicators, Need

_NUMBER = r"(\d{1,3}(?:[.,]\d{3})+|\d+)"

_COUNT_PATTERNS: dict[str, re.Pattern[str]] = {
    "families_affected": re.compile(_NUMBER + r"\s+familias?\b"),
    "people_affected": re.compile(
        _NUMBER
        + r"\s+(?:personas?|habitantes|pobladores|damnificad[oa]s|afectad[oa]s)\b"
        + r"(?!\s+(?:con\s+discapacidad|de\s+la\s+tercera\s+edad|adultas?\s+mayores))"
    ),
    "children": re.compile(_NUMBER + r"\s+(?:ninos?|ninas?|menores|infantes)\b"),
    "elderly_people": re.compile(
        _NUMBER
        + r"\s+(?:adult[oa]s\s+mayores|ancian[oa]s|personas\s+de\s+la\s+tercera\s+edad"
        + r"|personas\s+adultas\s+mayores)\b"
    ),
    "disabled_people": re.compile(
        _NUMBER + r"\s+(?:personas?\s+con\s+discapacidad|discapacitad[oa]s)\b"
    ),
}

# From the highest level to the lowest: the first level with a match wins.
_DAMAGE_PATTERNS: list[tuple[DamageLevel, re.Pattern[str]]] = [
    (
        DamageLevel.CRITICAL,
        re.compile(
            r"\b(?:colapso\s+total|destruccion\s+total|totalmente\s+destruid|arrasad"
            r"|sepultad|fallecid|muertos|desaparecid)"
        ),
    ),
    (
        DamageLevel.SEVERE,
        re.compile(r"\b(?:derrumb|colaps|destruid|inhabitable|sin\s+techo|graves?\s+danos)"),
    ),
    (
        DamageLevel.MODERATE,
        re.compile(r"\b(?:danos\s+parciales|parcialmente|grietas|fisuras|inundad|danad)"),
    ),
    (
        DamageLevel.LOW,
        re.compile(r"\b(?:danos\s+leves|danos\s+menores|levemente|sin\s+danos\s+mayores)"),
    ),
]

_NEED_PATTERNS: dict[Need, re.Pattern[str]] = {
    # Drinking water, not the water of a flood.
    Need.WATER: re.compile(
        r"\bagua\s+(?:potable|embotellada|para\s+(?:beber|consumo)|segura)\b"
        r"|\b(?:sin|falta\s+de|necesitan?|requieren?|urge|piden?)\s+agua\b"
        r"|\bbidones?\b|\bcisternas?\b"
    ),
    Need.FOOD: re.compile(r"\b(?:alimento|comida|viveres|raciones)"),
    Need.SHELTER: re.compile(
        r"\b(?:carpas?|albergues?|refugios?|frazadas?|colchon|techo\s+temporal|sin\s+techo)\b"
    ),
    Need.HYGIENE: re.compile(r"\b(?:higiene|aseo|panales|jabon|kits?\s+de\s+limpieza)\b"),
    Need.MEDICINE: re.compile(
        r"\b(?:medicina|medicamento|atencion\s+medica|botiquin|primeros\s+auxilios)"
    ),
}


@dataclass(frozen=True)
class StructuredReport:
    indicators: FieldIndicators
    missing_variables: list[str]


def structure_field_report(text: str) -> StructuredReport:
    """Extracts the indicators of a field report and lists the ones not found."""
    normalized = _normalize(text)
    indicators = FieldIndicators(
        damage_level=_damage_level(normalized),
        needs=_needs(normalized),
        **{name: _largest_count(pattern, normalized) for name, pattern in _COUNT_PATTERNS.items()},
    )
    return StructuredReport(indicators=indicators, missing_variables=_missing(indicators))


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents)


def _largest_count(pattern: re.Pattern[str], text: str) -> int | None:
    counts = [int(re.sub(r"[.,]", "", match)) for match in pattern.findall(text)]
    return max(counts, default=None)


def _damage_level(text: str) -> DamageLevel | None:
    return next((level for level, pattern in _DAMAGE_PATTERNS if pattern.search(text)), None)


def _needs(text: str) -> list[Need]:
    return [need for need, pattern in _NEED_PATTERNS.items() if pattern.search(text)]


def _missing(indicators: FieldIndicators) -> list[str]:
    fields = FieldIndicators.model_fields
    return [
        fields[name].alias or name
        for name, value in indicators
        if value is None or value == []
    ]
