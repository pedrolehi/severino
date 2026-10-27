"""Gerador de Relatórios HTML Modernos para Auditoria e Enfileiramento no ICD (Maximo).

Recursos:
- Interface moderna, responsiva e independente de conexão externa (CSS e JS embarcados)
- Cards informativos com badges de status (Enfileirado / Não Enfileirado / Excluído / Manual)
- Galeria de evidências com Modal Lightbox interativo (zoom das imagens)
- Links diretos clicáveis para cada chamado no IBM Control Desk
- Política de retenção automática: mantém estritamente os 10 últimos relatórios e remove os antigos
"""

from __future__ import annotations

import html
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def prune_old_reports(reports_dir: Path, keep: int = 10) -> list[Path]:
    """Mantém apenas os 'keep' relatórios mais recentes de cada tipo e remove os mais antigos."""
    deleted_files: list[Path] = []

    html_files = sorted(reports_dir.glob("icd_audit_*.html"), key=os.path.getmtime, reverse=True)
    for old_file in html_files[keep:]:
        try:
            old_file.unlink()
            deleted_files.append(old_file)
        except Exception:
            pass

    json_files = sorted(reports_dir.glob("icd_cleanup_*.json"), key=os.path.getmtime, reverse=True)
    for old_file in json_files[keep:]:
        try:
            old_file.unlink()
            deleted_files.append(old_file)
        except Exception:
            pass

    surviving_images: set[str] = set()
    surviving_htmls = sorted(reports_dir.glob("icd_audit_*.html"), key=os.path.getmtime, reverse=True)[:keep]
    for h in surviving_htmls:
        try:
            text = h.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "screenshots/" in line:
                    import re
                    matches = re.findall(r'screenshots/[^"\']+', line)
                    for m in matches:
                        surviving_images.add(Path(m).name)
        except Exception:
            pass

    screenshots_dir = reports_dir / "screenshots"
    if screenshots_dir.is_dir() and surviving_images:
        all_shots = sorted(screenshots_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
        for shot in all_shots[60:]:
            if shot.name not in surviving_images:
                try:
                    shot.unlink()
                    deleted_files.append(shot)
                except Exception:
                    pass

    return deleted_files


def classify_scenario_type(scenario: dict[str, Any]) -> tuple[str, str, bool]:
    """Retorna (codigo_tipo, label_tipo, is_chamado)."""
    sc_id = scenario.get("scenario_id", "").lower()
    sc_name = scenario.get("scenario_name", "").lower()
    flow = scenario.get("flow_name", "").lower()
    tickets = scenario.get("tickets", [])

    if len(tickets) > 0:
        return "chamado", "🎫 Abertura de Chamado", True

    keywords = ["abertura", "chamado", "cancelamento", "pagamentos", "orcamentarios", "solicitar"]
    if any(k in sc_id or k in sc_name or k in flow for k in keywords):
        return "chamado", "🎫 Abertura de Chamado", True

    return "consulta", "ℹ️ Consulta / Informativo", False


def generate_html_report(
    report_data: dict[str, Any],
    output_path: Path,
    keep_history: int = 10,
) -> Path:
    """Gera o arquivo HTML formatado e executa a política de retenção."""
    reports_dir = output_path.parent
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = report_data.get("timestamp_str") or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    total = report_data.get("total", 0)
    enfileirados = report_data.get("enfileirados_count", 0)
    nao_enfileirados = report_data.get("nao_enfileirados_count", 0)
    excluidos_sucesso = report_data.get("excluidos_count", 0)
    manuais = report_data.get("manual_count", 0)
    items = report_data.get("items", [])

    test_run = report_data.get("test_run")
    if not test_run and reports_dir.is_dir():
        test_run_files = sorted(reports_dir.glob("test_run_*.json"), key=os.path.getmtime, reverse=True)
        if test_run_files:
            try:
                test_run = json.loads(test_run_files[0].read_text(encoding="utf-8"))
            except Exception:
                test_run = None

    test_summary_html = ""
    scenarios_table_html = ""
    closure_banner_html = ""

    if test_run:
        test_total = test_run.get("total_scenarios", 0)
        test_passed = test_run.get("passed", 0)
        test_failed = test_run.get("failed", 0)
        test_duration_s = round(test_run.get("total_duration_ms", 0) / 1000.0, 1)
        test_rate = round((test_passed / test_total * 100.0), 1) if test_total > 0 else 0.0
        test_results = test_run.get("results", [])

        test_summary_html = f"""
    <div class="test-summary-card">
      <div class="test-summary-header">
        <div class="test-summary-title">
          <span>🧪 Resultado da Bateria de Testes Conversacionais E2E</span>
        </div>
        <p class="test-summary-desc">Métricas consolidadas de validação funcional dos fluxos do Assistente Virtual</p>
      </div>
      <div class="test-metrics-pills">
        <div class="test-pill">
          <span class="test-pill-label">Total de Cenários</span>
          <span class="test-pill-val">{test_total}</span>
        </div>
        <div class="test-pill pass">
          <span class="test-pill-label">Passaram no Teste</span>
          <span class="test-pill-val">{test_passed} ✅</span>
        </div>
        <div class="test-pill fail">
          <span class="test-pill-label">Falharam no Teste</span>
          <span class="test-pill-val">{test_failed} ❌</span>
        </div>
        <div class="test-pill rate">
          <span class="test-pill-label">Taxa de Sucesso</span>
          <span class="test-pill-val">{test_rate}%</span>
        </div>
        <div class="test-pill">
          <span class="test-pill-label">Duração Total</span>
          <span class="test-pill-val">{test_duration_s}s</span>
        </div>
      </div>
    </div>
"""

        items_by_ticket = {str(it.get("ticket_id", "")).strip(): it for it in items}

        rows_html = ""
        for idx, sc in enumerate(test_results, 1):
            sc_name = html.escape(sc.get("scenario_name") or sc.get("scenario_id") or f"Cenário {idx}")
            flow = html.escape(sc.get("flow_name") or "")
            sc_passed = sc.get("passed", False)
            tickets = sc.get("tickets", [])

            type_code, type_label, is_chamado = classify_scenario_type(sc)
            type_badge = f'<span class="badge-type {type_code}">{type_label}</span>'
            pass_badge = '<span class="badge-pill-pass">✅ PASS</span>' if sc_passed else '<span class="badge-pill-fail">❌ FAIL</span>'

            if tickets:
                tid = tickets[0].get("ticket_id", "")
                link = f"https://suporte.sp.senac.br/maximo/ui/?event=loadapp&value=sr&uniqueid={tid}"
                ticket_cell = f'<a href="{link}" target="_blank" class="ticket-link">#{tid} ↗</a>'
                
                audit = items_by_ticket.get(str(tid).strip())
                if audit:
                    if audit.get("ja_atendido"):
                        icd_status = f'<span class="badge-status success">👤 Já atendido ({audit.get("status", "")})</span>'
                    elif audit.get("reclassificado"):
                        icd_status = '<span class="badge-status success">✓ Excluído no ICD (Chamado Teste)</span>'
                    elif audit.get("manual_action_required"):
                        icd_status = '<span class="badge-status danger">🚨 Exclusão Manual Requerida</span>'
                    else:
                        icd_status = '<span class="badge-status warning">Pendente de Exclusão</span>'
                else:
                    icd_status = '<span class="badge-status success">✓ Registrado no ICD</span>'
            else:
                ticket_cell = '<span class="cell-muted">—</span>'
                if is_chamado:
                    icd_status = '<span class="cell-muted">Não gerado (Interrompido antes da abertura)</span>'
                else:
                    icd_status = '<span class="cell-muted">Fluxo informativo (Não gera chamado)</span>'

            rows_html += f"""
        <tr>
          <td style="color: var(--text-muted); text-align: center; font-weight: 600;">{idx}</td>
          <td>
            <div style="font-weight: 600; color: #fff;">{sc_name}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted); font-family: monospace;">fluxo: {flow}</div>
          </td>
          <td>{type_badge}</td>
          <td>{pass_badge}</td>
          <td>{ticket_cell}</td>
          <td>{icd_status}</td>
        </tr>
"""

        scenarios_table_html = f"""
    <div class="section-title">
      <span>📋 Matriz dos Cenários: Classificação de Chamados & Encerramento no ICD</span>
    </div>

    <div class="scenarios-table-container">
      <table class="scenarios-table">
        <thead>
          <tr>
            <th style="width: 50px; text-align: center;">#</th>
            <th>Cenário / Fluxo</th>
            <th style="width: 220px;">Tipo de Fluxo</th>
            <th style="width: 120px;">Resultado Teste</th>
            <th style="width: 140px;">Chamado ICD</th>
            <th style="width: 270px;">Status no ICD (Encerramento)</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
"""

    if total > 0 and excluidos_sucesso == total:
        closure_banner_html = f"""
    <div class="closure-banner">
      <div style="font-size: 1.6rem;">🛡️</div>
      <div>
        <strong style="color: #34d399; font-size: 1rem;">Garantia de Limpeza do Ambiente (100% dos Chamados Encerrados):</strong>
        <p style="color: #cbd5e1; font-size: 0.9rem; margin-top: 0.2rem;">
          Todos os <strong>{total} chamados</strong> gerados durante a bateria de testes foram auditados e <strong>devidamente encerrados/excluídos no IBM Control Desk</strong> (reclassificados como <em>'Excluir chamado teste'</em>). Nenhum chamado ficou pendente na fila de atendimento!
        </p>
      </div>
    </div>
"""
    elif manuais > 0:
        closure_banner_html = f"""
    <div class="closure-banner warning">
      <div style="font-size: 1.6rem;">⚠️</div>
      <div>
        <strong style="color: #fbbf24; font-size: 1rem;">Atenção: Intervenção Manual Necessária no ICD</strong>
        <p style="color: #cbd5e1; font-size: 0.9rem; margin-top: 0.2rem;">
          {manuais} chamado(s) precisam de cancelamento manual direto no Maximo. Utilize os links na tabela abaixo.
        </p>
      </div>
    </div>
"""

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório de Auditoria e Enfileiramento ICD | Senac</title>
  <style>
    :root {{
      --bg-main: #0f172a;
      --bg-card: #1e293b;
      --bg-card-hover: #334155;
      --border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #0284c7;
      --primary-light: #38bdf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --radius: 12px;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    body {{
      background: var(--bg-main);
      color: var(--text-main);
      padding: 2rem 1.5rem;
      line-height: 1.5;
    }}
    .container {{
      max-width: 1280px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .title-group h1 {{
      font-size: 1.8rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .title-group p {{
      color: var(--text-muted);
      font-size: 0.95rem;
    }}
    .badge-env {{
      background: rgba(2, 132, 199, 0.2);
      color: var(--primary-light);
      padding: 0.35rem 0.8rem;
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 600;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 2.5rem;
    }}
    .metric-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      transition: transform 0.2s;
    }}
    .metric-card:hover {{
      transform: translateY(-2px);
    }}
    .metric-label {{
      font-size: 0.85rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
    }}
    .metric-value {{
      font-size: 2rem;
      font-weight: 700;
      color: #fff;
    }}
    .metric-card.success .metric-value {{ color: var(--success); }}
    .metric-card.warning .metric-value {{ color: var(--warning); }}
    .metric-card.danger .metric-value {{ color: var(--danger); }}
    
    .alert-banner {{
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid var(--danger);
      border-radius: var(--radius);
      padding: 1.25rem 1.5rem;
      margin-bottom: 2rem;
      display: flex;
      align-items: flex-start;
      gap: 1rem;
    }}
    .alert-banner.hide {{
      display: none;
    }}
    .alert-icon {{
      font-size: 1.8rem;
    }}
    .alert-content h3 {{
      color: #fca5a5;
      font-size: 1.1rem;
      margin-bottom: 0.35rem;
    }}
    .alert-content p {{
      color: #cbd5e1;
      font-size: 0.95rem;
    }}

    .section-title {{
      font-size: 1.3rem;
      margin-bottom: 1rem;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .tickets-list {{
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }}
    .ticket-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}
    .ticket-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      padding-bottom: 1rem;
    }}
    .ticket-id-group {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .ticket-id {{
      font-size: 1.4rem;
      font-weight: 700;
      color: #fff;
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }}
    .ticket-id:hover {{
      color: var(--primary-light);
      text-decoration: underline;
    }}
    .ticket-subject {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }}
    .badge-status {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
    }}
    .badge-status.success {{
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.4);
    }}
    .badge-status.warning {{
      background: rgba(245, 158, 11, 0.2);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }}
    .badge-status.danger {{
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }}
    
    .ticket-details-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      background: rgba(15, 23, 42, 0.4);
      padding: 1rem;
      border-radius: 8px;
    }}
    .detail-item {{
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }}
    .detail-label {{
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }}
    .detail-val {{
      font-size: 0.95rem;
      color: #f1f5f9;
      font-weight: 500;
    }}
    
    .evidence-section {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .evidence-title {{
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
    }}
    .gallery-item {{
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      position: relative;
      transition: all 0.2s ease;
    }}
    .gallery-item:hover {{
      border-color: var(--primary-light);
      transform: translateY(-2px);
    }}
    .gallery-thumb {{
      width: 100%;
      height: 140px;
      object-fit: cover;
      display: block;
      background: #020617;
    }}
    .gallery-caption {{
      padding: 0.5rem 0.75rem;
      font-size: 0.8rem;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-card);
    }}
    .gallery-badge {{
      font-size: 0.7rem;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }}

    /* Lightbox Modal Interativo com Zoom e Pan */
    .lightbox {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(10, 15, 29, 0.95);
      backdrop-filter: blur(8px);
      display: none;
      flex-direction: column;
      z-index: 99999;
      user-select: none;
    }}
    .lightbox.active {{
      display: flex;
    }}
    .lightbox-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.85rem 1.5rem;
      background: rgba(15, 23, 42, 0.9);
      border-bottom: 1px solid var(--border);
      z-index: 10;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .lightbox-title-info {{
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }}
    .lightbox-title {{
      color: #fff;
      font-size: 1rem;
      font-weight: 600;
    }}
    .lightbox-hint {{
      color: var(--text-muted);
      font-size: 0.75rem;
    }}
    .lightbox-controls {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .lightbox-btn {{
      background: rgba(30, 41, 59, 0.8);
      color: #e2e8f0;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.4rem 0.75rem;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s;
    }}
    .lightbox-btn:hover {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary-light);
    }}
    .lightbox-btn.close-btn {{
      background: rgba(239, 68, 68, 0.2);
      border-color: rgba(239, 68, 68, 0.4);
      color: #fca5a5;
    }}
    .lightbox-btn.close-btn:hover {{
      background: var(--danger);
      color: #fff;
    }}
    .lightbox-zoom-val {{
      color: var(--primary-light);
      font-weight: 700;
      font-size: 0.85rem;
      min-width: 45px;
      text-align: center;
      font-family: monospace;
    }}
    .lightbox-viewport {{
      flex: 1;
      width: 100%;
      height: calc(100% - 60px);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: grab;
    }}
    .lightbox-viewport.grabbing {{
      cursor: grabbing;
    }}
    .lightbox-img-wrapper {{
      position: absolute;
      transform-origin: center center;
      transition: transform 0.08s ease-out;
      will-change: transform;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .lightbox-img {{
      max-width: 90vw;
      max-height: 85vh;
      border-radius: 6px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9);
      border: 1px solid #475569;
      pointer-events: none;
    }}

    /* Resumo Centralizado da Bateria de Testes */
    .test-summary-card {{
      background: linear-gradient(145deg, #1e293b, #0f172a);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      margin-bottom: 2rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 1.25rem;
    }}
    .test-summary-header {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.35rem;
    }}
    .test-summary-title {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .test-summary-desc {{
      font-size: 0.9rem;
      color: var(--text-muted);
      max-width: 700px;
    }}
    .test-metrics-pills {{
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
      width: 100%;
    }}
    .test-pill {{
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.85rem 1.25rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 150px;
      flex: 1 1 150px;
      max-width: 220px;
      transition: transform 0.2s;
    }}
    .test-pill:hover {{
      transform: translateY(-2px);
    }}
    .test-pill-label {{
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.05em;
    }}
    .test-pill-val {{
      font-size: 1.6rem;
      font-weight: 800;
      color: #fff;
      margin-top: 0.2rem;
    }}
    .test-pill.pass .test-pill-val {{ color: var(--success); }}
    .test-pill.fail .test-pill-val {{ color: var(--danger); }}
    .test-pill.rate .test-pill-val {{ color: var(--primary-light); }}

    /* Matriz dos Cenários */
    .scenarios-table-container {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow-x: auto;
      margin-bottom: 2.5rem;
    }}
    .scenarios-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.9rem;
    }}
    .scenarios-table th {{
      background: rgba(15, 23, 42, 0.95);
      padding: 0.9rem 1.1rem;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border);
    }}
    .scenarios-table td {{
      padding: 0.85rem 1.1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: #e2e8f0;
      vertical-align: middle;
    }}
    .scenarios-table tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .badge-type {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.3rem 0.65rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
    }}
    .badge-type.chamado {{
      background: rgba(2, 132, 199, 0.2);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.4);
    }}
    .badge-type.consulta {{
      background: rgba(148, 163, 184, 0.15);
      color: #cbd5e1;
      border: 1px solid rgba(148, 163, 184, 0.3);
    }}
    .badge-pill-pass {{
      display: inline-block;
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.4);
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.8rem;
      text-align: center;
    }}
    .badge-pill-fail {{
      display: inline-block;
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.4);
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.8rem;
      text-align: center;
    }}
    .ticket-link {{
      color: var(--primary-light);
      font-weight: 700;
      text-decoration: none;
      font-family: monospace;
      font-size: 0.95rem;
    }}
    .ticket-link:hover {{
      text-decoration: underline;
    }}
    .cell-muted {{
      color: var(--text-muted);
      font-size: 0.85rem;
    }}
    .closure-banner {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      border-radius: var(--radius);
      padding: 1.1rem 1.4rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .closure-banner.warning {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
    }}

    footer {{
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="title-group">
        <h1>📊 Auditoria e Enfileiramento no ICD (Senac)</h1>
        <p>Relatório integrado de testes conversacionais e validação de chamados no Maximo</p>
      </div>
      <div>
        <span class="badge-env">Gerado em: {timestamp_str}</span>
      </div>
    </header>

    {test_summary_html}

    {closure_banner_html}

    <div class="section-title">
      <span>🛡️ Métricas de Auditoria & Enfileiramento no ICD</span>
    </div>

    <div class="metrics-grid">
      <div class="metric-card">
        <span class="metric-label">Total de Chamados Gerados</span>
        <span class="metric-value">{total}</span>
      </div>
      <div class="metric-card success">
        <span class="metric-label">Enfileirados no Grupo</span>
        <span class="metric-value">{enfileirados}</span>
      </div>
      <div class="metric-card warning">
        <span class="metric-label">Não Enfileirados</span>
        <span class="metric-value">{nao_enfileirados}</span>
      </div>
      <div class="metric-card success">
        <span class="metric-label">Excluídos (Teste)</span>
        <span class="metric-value">{excluidos_sucesso}</span>
      </div>
      <div class="metric-card {'danger' if manuais > 0 else ''}">
        <span class="metric-label">Ação Manual Requerida</span>
        <span class="metric-value">{manuais}</span>
      </div>
    </div>

    <!-- Banner de Alerta para chamados pendentes -->
    <div class="alert-banner {'hide' if manuais == 0 else ''}">
      <div class="alert-icon">⚠️</div>
      <div class="alert-content">
        <h3>Intervenção Manual Necessária no ICD</h3>
        <p>{manuais} chamado(s) falharam na reclassificação automática após 3 tentativas. Utilize os links diretos abaixo para excluí-los manualmente.</p>
      </div>
    </div>

    {scenarios_table_html}

    <div class="section-title">
      <span>📋 Detalhamento dos Chamados Auditados (Evidências & Prints)</span>
    </div>

    <div class="tickets-list">
"""

    for item in items:
        ticket_id = item.get("ticket_id", "")
        flow_name = item.get("flow_name", "")
        subject = item.get("subject", "")
        grupo = item.get("grupo_atendimento", "")
        enfileirou = item.get("enfileirou", False)
        wait_seconds = item.get("wait_seconds", 0)
        reclassificado = item.get("reclassificado", False)
        attempts = item.get("attempts", 1)
        manual = item.get("manual_action_required", False)
        direct_link = item.get("direct_link") or f"https://suporte.sp.senac.br/maximo/ui/?event=loadapp&value=sr&uniqueid={ticket_id}"

        if enfileirou:
            enfileiramento_badge = f"""<span class="badge-status success">✓ Enfileirado ({wait_seconds}s)</span>"""
            grupo_display = grupo or "Grupo Identificado"
        else:
            enfileiramento_badge = f"""<span class="badge-status warning">⚠ Não Enfileirou (Timeout 4m)</span>"""
            grupo_display = '<span style="color: #f59e0b;">(Vazio / Não roteado)</span>'

        if item.get("ja_atendido"):
            exclusao_badge = f"""<span class="badge-status success">👤 Já atendido ({item.get("status", "")})</span>"""
        elif reclassificado:
            exclusao_badge = f"""<span class="badge-status success">✓ Excluído (Chamado Teste)</span>"""
        elif manual:
            exclusao_badge = f"""<span class="badge-status danger">🚨 Exclusão Manual Necessária</span>"""
        else:
            exclusao_badge = f"""<span class="badge-status warning">Em Aberto</span>"""

        shots_html = ""
        screenshots = item.get("screenshots", [])
        if screenshots:
            shots_html = '<div class="gallery-grid">'
            for s in screenshots:
                shot_path = s.get("path", "")
                caption = s.get("caption", "Evidência")
                stage = s.get("stage", "Print")
                rel_path = shot_path
                if "reports/" in rel_path:
                    rel_path = rel_path.split("reports/", 1)[1]
                elif "reports\\" in rel_path:
                    rel_path = rel_path.split("reports\\", 1)[1]

                # Normaliza para URL web com barras normais (evita \t de screenshots\ticket)
                rel_url = rel_path.replace("\\", "/")
                safe_caption = html.escape(caption, quote=True)
                safe_stage = html.escape(stage, quote=True)

                shots_html += f"""
                <div class="gallery-item" onclick="openLightbox(this)">
                  <img src="{rel_url}" alt="{safe_caption}" class="gallery-thumb" loading="lazy">
                  <div class="gallery-caption">
                    <span>{safe_caption}</span>
                    <span class="gallery-badge">{safe_stage}</span>
                  </div>
                </div>
                """
            shots_html += "</div>"
        else:
            shots_html = '<p style="color: var(--text-muted); font-size: 0.85rem;">Nenhuma captura registrada.</p>'

        html_content += f"""
      <div class="ticket-card">
        <div class="ticket-header">
          <div class="ticket-id-group">
            <div>
              <a href="{direct_link}" target="_blank" class="ticket-id" title="Abrir solicitação no Maximo">
                #{ticket_id} ↗
              </a>
              <div class="ticket-subject">{subject or flow_name}</div>
            </div>
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            {enfileiramento_badge}
            {exclusao_badge}
          </div>
        </div>

        <div class="ticket-details-grid">
          <div class="detail-item">
            <span class="detail-label">Grupo de Atendimento</span>
            <span class="detail-val">{grupo_display}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Tempo até Enfileirar</span>
            <span class="detail-val">{wait_seconds}s</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Fluxo do Assistente</span>
            <span class="detail-val">{flow_name or 'N/A'}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Tentativas de Exclusão</span>
            <span class="detail-val">{attempts} de 3</span>
          </div>
        </div>

        <div class="evidence-section">
          <span class="evidence-title">📸 Evidências Visuais (Clique para ampliar):</span>
          {shots_html}
        </div>
      </div>
"""

    html_content += """
    </div>

    <footer>
      <p>Robô de Auditoria e Enfileiramento IBM Control Desk (ICD) • Assistente Virtual Senac SP</p>
      <p style="margin-top: 0.25rem;">Política de retenção ativa: mantendo os 10 relatórios mais recentes em reports/</p>
    </footer>
  </div>

  <!-- Modal Lightbox com Zoom Interativo -->
  <div id="lightbox" class="lightbox">
    <div class="lightbox-toolbar">
      <div class="lightbox-title-info">
        <span id="lightbox-title" class="lightbox-title">Evidência</span>
        <span class="lightbox-hint">Dica: Use a rodinha do mouse ou clique duas vezes para dar zoom, e arraste para navegar</span>
      </div>
      <div class="lightbox-controls">
        <button type="button" class="lightbox-btn" onclick="zoomIn()" title="Aumentar zoom (+)">🔍+ Zoom In</button>
        <button type="button" class="lightbox-btn" onclick="zoomOut()" title="Diminuir zoom (-)">🔍- Zoom Out</button>
        <span id="lightbox-zoom-val" class="lightbox-zoom-val">100%</span>
        <button type="button" class="lightbox-btn" onclick="resetZoom()" title="Ajustar à tela">📐 Ajustar</button>
        <button type="button" class="lightbox-btn" onclick="setZoomReal()" title="Visualizar em tamanho real (1:1)">1:1 Real</button>
        <button type="button" class="lightbox-btn" onclick="openOriginal()" title="Abrir imagem isolada em nova aba">↗ Nova Aba</button>
        <button type="button" id="lightbox-close-btn" class="lightbox-btn close-btn" onclick="closeLightbox()" title="Fechar (Esc)">✕ Fechar</button>
      </div>
    </div>
    <div id="lightbox-viewport" class="lightbox-viewport">
      <div id="lightbox-img-wrapper" class="lightbox-img-wrapper">
        <img id="lightbox-img" class="lightbox-img" src="" alt="Zoom Evidência">
      </div>
    </div>
  </div>

  <script>
    let currentZoom = 1;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let currentImgUrl = '';

    function updateTransform() {
      const wrapper = document.getElementById('lightbox-img-wrapper');
      const zoomText = document.getElementById('lightbox-zoom-val');
      if (wrapper) {
        wrapper.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
      }
      if (zoomText) {
        zoomText.innerText = Math.round(currentZoom * 100) + '%';
      }
    }

    function resetZoom() {
      currentZoom = 1;
      panX = 0;
      panY = 0;
      updateTransform();
    }

    function zoomIn() {
      currentZoom = Math.min(Number((currentZoom + 0.25).toFixed(2)), 4.0);
      updateTransform();
    }

    function zoomOut() {
      currentZoom = Math.max(Number((currentZoom - 0.25).toFixed(2)), 0.4);
      updateTransform();
    }

    function setZoomReal() {
      currentZoom = 1.6;
      panX = 0;
      panY = 0;
      updateTransform();
    }

    function openOriginal() {
      if (currentImgUrl) {
        window.open(currentImgUrl, '_blank');
      }
    }

    function openLightbox(target, fallbackTitle) {
      const lightboxImg = document.getElementById('lightbox-img');
      const lightboxTitle = document.getElementById('lightbox-title');
      let src = '';
      let title = fallbackTitle || '';

      if (typeof target === 'string') {
        src = target.split('\\\\').join('/');
      } else if (target && target.querySelector) {
        const img = target.querySelector('img');
        if (img) {
          src = img.currentSrc || img.src || img.getAttribute('src');
          title = img.getAttribute('alt') || fallbackTitle || '';
        }
      }

      currentImgUrl = src;
      lightboxImg.src = src;
      lightboxTitle.innerText = title;

      resetZoom();
      document.getElementById('lightbox').classList.add('active');
    }

    function closeLightbox() {
      document.getElementById('lightbox').classList.remove('active');
      resetZoom();
    }

    // Inicialização de eventos interativos
    window.addEventListener('DOMContentLoaded', () => {
      const viewport = document.getElementById('lightbox-viewport');
      if (viewport) {
        viewport.addEventListener('wheel', (e) => {
          e.preventDefault();
          if (e.deltaY < 0) {
            currentZoom = Math.min(Number((currentZoom + 0.15).toFixed(2)), 4.0);
          } else {
            currentZoom = Math.max(Number((currentZoom - 0.15).toFixed(2)), 0.4);
          }
          updateTransform();
        }, { passive: false });

        viewport.addEventListener('mousedown', (e) => {
          if (e.button !== 0) return;
          isDragging = true;
          startX = e.clientX - panX;
          startY = e.clientY - panY;
          viewport.classList.add('grabbing');
        });

        window.addEventListener('mousemove', (e) => {
          if (!isDragging) return;
          panX = e.clientX - startX;
          panY = e.clientY - startY;
          updateTransform();
        });

        window.addEventListener('mouseup', () => {
          if (isDragging) {
            isDragging = false;
            viewport.classList.remove('grabbing');
          }
        });

        viewport.addEventListener('dblclick', () => {
          if (currentZoom > 1.2) {
            resetZoom();
          } else {
            currentZoom = 1.8;
            updateTransform();
          }
        });
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeLightbox();
      } else if (e.key === '+' || e.key === '=') {
        zoomIn();
      } else if (e.key === '-') {
        zoomOut();
      } else if (e.key === '0') {
        resetZoom();
      }
    });
  </script>
</body>
</html>
"""

    output_path.write_text(html_content, encoding="utf-8")

    prune_old_reports(reports_dir, keep=keep_history)

    return output_path
