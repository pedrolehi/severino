"""Ponto de entrada CLI para executar a suíte de testes E2E dos fluxos."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import httpx

from tests.reporter import TestReporter
from tests.runner import FlowTestRunner
from tests.scenarios import ALL_SCENARIOS, SCENARIOS_BY_FLOW, SCENARIOS_BY_ID
from tests.scenarios.base import load_scenarios_from_json, save_scenarios_to_json


def _check_backend_available(url: str) -> bool:
    if not url:
        return False
    try:
        resp = httpx.get(url, timeout=5.0, follow_redirects=True)
        return resp.status_code < 500
    except Exception:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa testes conversacionais E2E dos fluxos do Senac"
    )
    parser.add_argument(
        "--dataset",
        metavar="JSON_FILE",
        help="Caminho para arquivo JSON de cenários de teste reais para execução (ex: tests/fixtures/real_test_scenarios.json)",
    )
    parser.add_argument(
        "--export-dataset",
        metavar="JSON_FILE",
        help="Exporta todos os cenários registrados para um arquivo JSON estruturado e sai",
    )
    parser.add_argument(
        "--flow",
        help="Filtra cenários por nome de fluxo (ex: gep_abertura_chamado_crachas, centro_de_custo)",
    )
    parser.add_argument(
        "--scenario",
        help="Executa apenas um cenário específico por ID (ex: gep_saldo_de_horas)",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Executa contra o cluster de PRODUÇÃO do senac-orchestrate",
    )
    parser.add_argument(
        "--audit-icd",
        action="store_true",
        help="Dispara automaticamente o robô Playwright ao final para auditar enfileiramento (10m) e excluir os chamados de teste",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Executa o robô Playwright com navegador visível na tela (padrão é headless)",
    )
    parser.add_argument(
        "--queue-timeout",
        type=int,
        default=600,
        help="Tempo máximo de espera pelo enfileiramento em segundos no ICD (padrão: 600 / 10 minutos)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Força uso do MockOrchestrateClient (não faz chamadas HTTP para o senac-orchestrate)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Limpa relatórios e screenshots de execuções anteriores antes de iniciar os testes",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista todos os cenários disponíveis e sai",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.clean:
        from scripts.clean_reports import clean
        clean()

    if args.export_dataset:
        save_scenarios_to_json(ALL_SCENARIOS, args.export_dataset)
        print(f"✅ Sucesso: {len(ALL_SCENARIOS)} cenários exportados para '{args.export_dataset}'.")
        return 0

    if args.dataset:
        try:
            active_scenarios = load_scenarios_from_json(args.dataset)
            print(f"📦 Dataset carregado de '{args.dataset}': {len(active_scenarios)} cenários.")
        except Exception as exc:
            print(f"❌ Erro ao carregar dataset de '{args.dataset}': {exc}")
            return 1
    else:
        active_scenarios = ALL_SCENARIOS

    scenarios_by_id = {s.id: s for s in active_scenarios}

    if args.list:
        print("\n📋 Cenários de Teste Disponíveis:")
        print("=" * 60)
        for s in active_scenarios:
            print(f" • [{s.id}] {s.name} (fluxo: {s.flow_name}) - {len(s.turns)} turnos")
        print("=" * 60)
        print(f"Total: {len(active_scenarios)} cenários cadastrados.\n")
        return 0

    prod_orchestrate_url = "https://prod-senac-orquestrator-chatbotx.ocp-senac-11f45abbd458185944dd806416f75c34-0000.us-south.containers.appdomain.cloud/v2"
    if args.prod:
        os.environ["SENAC_ORCHESTRATE_URL"] = prod_orchestrate_url
        orchestrate_url = prod_orchestrate_url
    else:
        orchestrate_url = os.getenv("SENAC_ORCHESTRATE_URL", "").strip()

    if args.mock:
        os.environ["ORCHESTRATE_USE_MOCK"] = "true"
        print("🔧 Modo Mock ATIVADO manualmente via --mock.")
    else:
        os.environ["ORCHESTRATE_USE_MOCK"] = "false"
        if not orchestrate_url:
            print("❌ Erro: SENAC_ORCHESTRATE_URL não configurada no .env.")
            print("Para rodar contra homologação, configure SENAC_ORCHESTRATE_URL. Para testes locais offline, use '--mock'.")
            return 1

        if args.prod:
            print("=" * 70)
            print("🚨 [ATENÇÃO: MODO PRODUÇÃO ATIVADO]")
            print(f"🌐 Backend senac-orchestrate PROD: {orchestrate_url}")
            print("⚡ Os chamados serão abertos no ambiente REAL de PRODUÇÃO do ICD!")
            print("=" * 70)
        else:
            print(f"🌐 Backend senac-orchestrate REAL conectado em: {orchestrate_url}")
            print("⚡ Execução 100% real: chamadas serão enviadas ao cluster de homologação e ao ICD (IBM Control Desk).")

    scenarios_to_run = active_scenarios
    if args.scenario:
        if args.scenario not in scenarios_by_id:
            print(f"❌ Erro: Cenário '{args.scenario}' não encontrado no catálogo ativo.")
            return 1
        scenarios_to_run = [scenarios_by_id[args.scenario]]
    elif args.flow:
        scenarios_to_run = [
            s for s in active_scenarios if args.flow.lower() in s.flow_name.lower() or args.flow.lower() in s.id.lower()
        ]
        if not scenarios_to_run:
            print(f"❌ Erro: Nenhum cenário encontrado para o filtro '--flow {args.flow}'.")
            return 1

    print("\n🚀 Iniciando Bateria de Testes E2E dos Fluxos Conversacionais...")
    print(f"Total de cenários a executar: {len(scenarios_to_run)}")
    print("-" * 60)

    runner = FlowTestRunner()
    results = []

    for idx, scn in enumerate(scenarios_to_run, start=1):
        print(f"[{idx}/{len(scenarios_to_run)}] Executando '{scn.name}'...", end=" ", flush=True)
        res = runner.run_scenario(scn)
        results.append(res)
        if res.passed:
            print(f"✅ PASS ({res.duration_ms:.0f}ms)")
        else:
            print(f"❌ FAIL ({res.duration_ms:.0f}ms)")
            for tr in res.turn_results:
                for err in tr.errors:
                    print(f"    🔴 Turno {tr.turn_index}: {err}")

    print("-" * 60)
    reporter = TestReporter(results)
    md_path, json_path = reporter.save()

    print("\n📊 Resumo da Execução:")
    print(f" • Total de Cenários: {reporter.total_scenarios}")
    print(f" • Passaram: {reporter.passed_scenarios} ✅")
    print(f" • Falharam: {reporter.failed_scenarios} ❌")
    print(f" • Tempo Total: {reporter.total_duration_ms / 1000:.2f}s")

    tickets = reporter.all_tickets
    if tickets:
        if args.audit_icd:
            print("\n" + "=" * 70)
            print("🤖 [AUTOMAÇÃO ICD ATIVADA via --audit-icd]")
            print(f"Disparando auditoria de enfileiramento e exclusão para {len(tickets)} chamado(s)...")
            print("=" * 70)
            from scripts.icd_cleaner_robot import ICDAuditAndCleanerRobot, TicketTarget
            targets = [
                TicketTarget(
                    ticket_id=t.ticket_id,
                    flow_name=t.flow_name,
                    subject=t.subject,
                    user_name=t.user_name,
                    chapa=t.chapa,
                )
                for t in tickets
            ]
            robot = ICDAuditAndCleanerRobot(
                headless=not args.headed,
                queue_timeout_s=args.queue_timeout,
            )
            robot.run(targets)
        else:
            print("\n⚠️ CHAMADOS ABERTOS NO ICD:")
            print("=" * 60)
            for t in tickets:
                print(f" • Protocolo: {t.ticket_id} | Fluxo: {t.flow_name} | Assunto: {t.subject}")
            print("=" * 60)
            print("💡 DICA: Para auditar o enfileiramento e excluir automaticamente:")
            print("   python scripts/icd_cleaner_robot.py --latest --headed")
            print("   Ou adicione a flag '--audit-icd' ao rodar os testes.")

    print(f"\n📄 Relatório Markdown salvo em: {md_path}")
    print(f"📄 Relatório JSON salvo em: {json_path}\n")

    return 0 if reporter.failed_scenarios == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
