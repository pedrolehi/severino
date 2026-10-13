"""Teste de validação da geração do relatório HTML e da política de retenção."""

from pathlib import Path
from scripts.icd_html_reporter import generate_html_report, prune_old_reports

ROOT_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT_DIR / "reports"

sample_data = {
    "timestamp_str": "13/10/2026 15:25:00",
    "total": 5,
    "enfileirados_count": 4,
    "nao_enfileirados_count": 1,
    "excluidos_count": 5,
    "manual_count": 0,
    "items": [
        {
            "ticket_id": "6438504",
            "flow_name": "gep_abertura_chamado_crachas",
            "subject": "GEP - Abertura de Chamado de Crachás",
            "grupo_atendimento": "CAS - Registro",
            "enfileirou": True,
            "wait_seconds": 22,
            "reclassificado": True,
            "attempts": 1,
            "manual_action_required": False,
            "direct_link": "https://suporte.sp.senac.br/maximo/ui/?event=loadapp&value=sr&uniqueid=6438504",
            "screenshots": [
                {
                    "stage": "1. Abertura",
                    "caption": "Tela inicial do chamado (Antes de reclassificar)",
                    "path": "reports/screenshots/ticket_6438504_1_abertura_sample.png",
                },
                {
                    "stage": "2. Enfileirado",
                    "caption": "Enfileirado no grupo: CAS - Registro (22s)",
                    "path": "reports/screenshots/ticket_6438504_2_enfileiramento_sample.png",
                },
                {
                    "stage": "3. Exclusão",
                    "caption": "Reclassificado como 'Excluir chamado teste'",
                    "path": "reports/screenshots/ticket_6438504_3_exclusao_sample.png",
                },
            ],
        },
        {
            "ticket_id": "6438505",
            "flow_name": "gep_abertura_chamado_ponto_eletronico",
            "subject": "GEP - Abertura de Chamado de Ponto Eletrônico",
            "grupo_atendimento": "GCR - Atendimento",
            "enfileirou": True,
            "wait_seconds": 18,
            "reclassificado": True,
            "attempts": 1,
            "manual_action_required": False,
            "direct_link": "https://suporte.sp.senac.br/maximo/ui/?event=loadapp&value=sr&uniqueid=6438505",
            "screenshots": [],
        },
        {
            "ticket_id": "6438510",
            "flow_name": "gcr_abertura_chamado",
            "subject": "GCR - Abertura de Chamado",
            "grupo_atendimento": "",
            "enfileirou": False,
            "wait_seconds": 240,
            "reclassificado": True,
            "attempts": 2,
            "manual_action_required": False,
            "direct_link": "https://suporte.sp.senac.br/maximo/ui/?event=loadapp&value=sr&uniqueid=6438510",
            "screenshots": [],
        },
    ],
}

output_path = REPORTS_DIR / "icd_audit_sample.html"
generate_html_report(sample_data, output_path, keep_history=10)
print(f"HTML gerado com sucesso em: {output_path}")
