"""Métadonnées du dépôt : URLs du manifest et sources des données (issue #474)."""

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
INTEGRATION = RACINE / "custom_components" / "tarifenergie"
DEPOT = "https://github.com/Mathilde-Team/Tarif-Energie"


def test_manifest_pointe_vers_le_depot():
    """documentation et issue_tracker visent le vrai dépôt (plus « Mathide-Team »)."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["documentation"] == DEPOT
    assert manifest["issue_tracker"] == f"{DEPOT}/issues"


def test_chaque_offre_cite_sa_source():
    """Chaque grille de fournisseur cite le document d'où viennent ses prix."""
    sans_source = [
        f.name
        for f in sorted((INTEGRATION / "offres").glob("*.yaml"))
        if not any(ligne.startswith("source: http") for ligne in f.read_text(encoding="utf-8").splitlines())
    ]
    assert sans_source == []


def test_readme_documente_donnees_et_licences():
    """Le README nomme la source des TRV (CRE) et la règle d'attribution."""
    readme = (RACINE / "README.md").read_text(encoding="utf-8")
    assert "## Données et licences" in readme
    assert "Commission de régulation de l'énergie (CRE)" in readme
    assert "Mathide-Team" not in readme
