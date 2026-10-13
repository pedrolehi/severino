"""Regenera o relatório HTML mais recente aplicando o novo layout."""

import json
from pathlib import Path
from scripts.icd_html_reporter import generate_html_report

ROOT_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT_DIR / "reports"

json_files = sorted(REPORTS_DIR.glob("icd_cleanup_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
if not json_files:
    print("Nenhum icd_cleanup_*.json encontrado em reports/")
    exit(1)

latest_cleanup_json = json_files[0]
html_path = REPORTS_DIR / f"icd_audit_{latest_cleanup_json.stem.replace('icd_cleanup_', '')}.html"

data = json.loads(latest_cleanup_json.read_text(encoding="utf-8"))
# Força grupo limpo se tiver o resquício de script antigo
for it in data.get("items", []):
    if "clientAreaId" in it.get("grupo_atendimento", ""):
        it["grupo_atendimento"] = "CAS - Central de Atendimento ao Servidor"

generate_html_report(data, html_path, keep_history=10)
print(f"Relatório HTML atualizado com sucesso em: {html_path}")
