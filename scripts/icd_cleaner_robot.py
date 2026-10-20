"""Robô de Automação de UI (Playwright) para Auditoria de Enfileiramento e Exclusão no ICD (Senac).

Fluxo Completo:
1. Login no IAM Keycloak do Senac (https://iam.sp.senac.br/auth/realms/administrativo/protocol/saml/clients/suporte)
2. Acesso à aplicação 'Requisição de Serviço'
3. Para cada chamado:
   a) Localiza e abre o chamado pelo campo 'Localizar Solicitação de'
   b) Captura Screenshot 1: Tela inicial de abertura antes de qualquer ação
   c) Aguarda até 4 minutos (240s) monitorando o campo 'Grupo de Atendimento':
      - Se preencher o grupo: captura Screenshot 2 (Enfileirado) e prossegue
      - Se expirar 4 minutos sem preencher: captura Screenshot 2 (Não Enfileirado) e prossegue
   d) Exclusão do chamado de teste (reclassificação) em até 3 tentativas com descarte automático de telas travadas
   e) Captura Screenshot 3: Tela final após salvar como 'Excluir chamado teste'
4. Geração de Relatório HTML moderno com Lightbox para visualização das imagens
5. Aplicação da Política de Retenção: mantém estritamente os 10 últimos relatórios em reports/
"""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
    PlaywrightError = Exception

logger = logging.getLogger("icd_cleaner_robot")

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

REPORTS_DIR = ROOT_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"

EXCLUIR_LABEL = "Excluir chamado teste"
MAXIMO_FIELD_LABELS = {
    "Solicitante", "Proprietário", "Status", "Anexos", "Tipo da Requisição",
    "Origem", "Meio de abertura", "Duplicado pai", "Grupo de Atendimento",
}


def _is_valid_grupo(value: str) -> bool:
    if len(value) < 3 or value.endswith(":"):
        return False
    return value not in MAXIMO_FIELD_LABELS

try:
    from scripts.icd_html_reporter import generate_html_report
except ModuleNotFoundError:
    from icd_html_reporter import generate_html_report


@dataclass
class TicketTarget:
    ticket_id: str
    flow_name: str = ""
    subject: str = ""
    user_name: str = ""
    chapa: str = ""


@dataclass
class TicketAuditResult:
    ticket_id: str
    flow_name: str
    subject: str
    grupo_atendimento: str = ""
    enfileirou: bool = False
    wait_seconds: int = 0
    reclassificado: bool = False
    attempts: int = 1
    manual_action_required: bool = False
    error_message: str = ""
    screenshots: list[dict[str, str]] = field(default_factory=list)
    direct_link: str = ""


class ICDAuditAndCleanerRobot:
    """Robô Playwright para monitoramento de enfileiramento (4 min) e exclusão no ICD."""

    def __init__(
        self,
        login_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        headless: bool = False,
        slow_mo_ms: int = 150,
        timeout_ms: int = 35000,
        queue_timeout_s: int = 600,  # 10 minutos conforme especificado
        max_retries: int = 3,
        keep_history: int = 10,
    ) -> None:
        self.login_url = (
            login_url
            or os.getenv("ICD_LOGIN_URL")
            or "https://iam.sp.senac.br/auth/realms/administrativo/protocol/saml/clients/suporte"
        )
        self.username = username or os.getenv("ICD_USERNAME") or os.getenv("ICD_USER") or ""
        self.password = password or os.getenv("ICD_PASSWORD") or os.getenv("ICD_PASS") or ""
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.timeout_ms = timeout_ms
        self.queue_timeout_s = queue_timeout_s
        self.max_retries = max_retries
        self.keep_history = keep_history

        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def run(self, tickets: list[TicketTarget]) -> list[TicketAuditResult]:
        """Executa o ciclo completo de login, verificação de enfileiramento, exclusão e relatório."""
        if sync_playwright is None:
            print("❌ Playwright não está instalado.")
            print("Instale executando:")
            print("    pip install playwright")
            print("    playwright install chromium")
            return []

        if not self.username or not self.password:
            print("⚠️ ATENÇÃO: Credenciais do ICD não informadas!")
            print("Configure ICD_USERNAME e ICD_PASSWORD no seu arquivo .env.")
            if not sys.stdin.isatty():
                return []
            self.username = input("Informe o Usuário/Chapa do ICD: ").strip()
            self.password = getpass.getpass("Informe a Senha do ICD: ").strip()

        print("=" * 80)
        print("🤖 [ICD AUDIT & CLEANER ROBOT] Auditoria de Enfileiramento e Exclusão no ICD")
        print(f"🔑 Portal IAM/ICD:        {self.login_url}")
        print(f"👤 Usuário:               {self.username}")
        print(f"🖥️ Modo de Tela:          {'Headless (em segundo plano)' if self.headless else 'Headed (janela visível)'}")
        print(f"⏱️ Timeout Enfileiramento:{self.queue_timeout_s}s ({self.queue_timeout_s // 60} minutos)")
        print(f"🔄 Retries de Exclusão:   {self.max_retries} tentativas")
        print(f"📦 Política de Retenção:  Manter apenas {self.keep_history} últimos relatórios")
        print(f"📋 Total de Chamados:     {len(tickets)}")
        print("=" * 80)

        results: list[TicketAuditResult] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo_ms,
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
            )
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            try:
                self._login(page)
                self._open_requisicao_de_servico(page)

                for idx, ticket in enumerate(tickets, start=1):
                    print(f"\n[{idx}/{len(tickets)}] 🎯 Iniciando auditoria do chamado #{ticket.ticket_id} ({ticket.subject or ticket.flow_name})...")
                    res = self._audit_and_cleanup_ticket(page, ticket)
                    results.append(res)

            except Exception as exc:
                logger.exception("Erro fatal na sessão do navegador")
                print(f"💥 Erro fatal na sessão do navegador: {exc}")
            finally:
                context.close()
                browser.close()

        self._generate_reports_and_summary(results)
        return results

    def _login(self, page) -> None:
        """Autenticação no IAM Keycloak do Senac."""
        print("🔑 Acessando tela de autenticação IAM Senac...")
        page.goto(self.login_url)
        page.wait_for_load_state("domcontentloaded")

        if page.get_by_role("link", name="Requisição de Serviço").count() > 0:
            print("✨ Sessão ativa detectada.")
            return

        user_field = page.get_by_role("textbox", name="Nome de usuário ou e-mail")
        if user_field.count() == 0:
            user_field = page.locator("input#username, input[name='username']")
        user_field.first.fill(self.username)

        pass_field = page.get_by_role("textbox", name="Senha")
        if pass_field.count() == 0:
            pass_field = page.locator("input#password, input[name='password']")
        pass_field.first.fill(self.password)

        print("🚀 Submetendo credenciais...")
        pass_field.first.press("Enter")

        page.wait_for_load_state("networkidle")
        time.sleep(2)
        print("🎉 Login no portal do Senac concluído com sucesso!")

    def _open_requisicao_de_servico(self, page) -> None:
        """Acessa a aplicação Requisição de Serviço."""
        print("📂 Acessando aplicativo 'Requisição de Serviço'...")
        req_link = page.get_by_role("link", name="Requisição de Serviço")
        if req_link.count() > 0 and req_link.first.is_visible():
            req_link.first.click()
        else:
            page.locator("a:has-text('Requisição de Serviço')").first.click()

        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

    def _search_ticket(self, page, ticket_id: str) -> None:
        """Busca o chamado no campo 'Localizar Solicitação de'."""
        search_box = page.get_by_role("textbox", name="Localizar Solicitação de")
        if search_box.count() == 0:
            search_box = page.locator("input[title*='Localizar Solicitação'], input[placeholder*='Localizar Solicitação']")

        search_box.first.click()
        search_box.first.fill(ticket_id)
        search_box.first.press("Enter")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Trata possível modal de "Deseja salvar alterações pendentes?" clicando em Não
        no_btn = page.get_by_role("button", name="Não")
        if no_btn.count() > 0 and no_btn.first.is_visible():
            no_btn.first.click()
            time.sleep(1)

    def _get_grupo_atendimento(self, page) -> str:
        """Lê só o valor do input 'Grupo de Atendimento'.

        Busca por texto da página pega o rótulo vizinho ('Proprietário:') quando o campo está vazio.
        """
        candidates = [
            page.get_by_role("textbox", name="Grupo de Atendimento:"),
            page.locator("input[id*='ownergroup' i]"),
        ]
        for loc in candidates:
            if loc.count() == 0:
                continue
            try:
                value = (loc.first.input_value() or "").strip()
            except PlaywrightError:
                value = ""
            if _is_valid_grupo(value):
                return value
        return ""

    def _scroll_to_top(self, page) -> None:
        """O Maximo mantém a rolagem do chamado anterior; o cabeçalho (grupo/status) fica fora do print."""
        page.evaluate(
            """() => {
                window.scrollTo(0, 0);
                document.querySelectorAll('*').forEach(el => { if (el.scrollTop > 0) el.scrollTop = 0; });
            }"""
        )
        time.sleep(0.5)

    def _is_reclassificado(self, page) -> bool:
        """Confere na tela recarregada se a classificação virou 'Excluir chamado teste'."""
        return page.evaluate(
            """(alvo) => {
                const textos = [document.body ? document.body.innerText || '' : ''];
                document.querySelectorAll('input, textarea').forEach(el => textos.push(el.value || ''));
                return textos.some(t => t.includes(alvo));
            }""",
            EXCLUIR_LABEL,
        )

    def _click_save_ticket(self, page) -> bool:
        """Aciona o botão Salvar da Solicitação de Serviço no Maximo com máxima resiliência."""
        # 1. Aguarda fechamento do modal de classificação
        time.sleep(2)

        save_selectors = [
            "#toolactions_save",
            "[id*='toolactions_save']",
            "[id*='toolactions_SAVE']",
            "[id*='SAVE-tbb']",
            "[id*='toolbar_save']",
            "a[title*='Salvar Solicitação de Serviço']",
            "[title*='Salvar Solicitação de Serviço']",
            "img[alt*='Salvar Solicitação de Serviço']",
            "img[title*='Salvar Solicitação de Serviço']",
            "[title*='Salvar']",
            "[aria-label*='Salvar']",
            "button[title*='Salvar Solicitação de Serviço']",
            "button[title*='Salvar']",
        ]

        saved = False
        for sel in save_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                try:
                    print(f"      💾 Clicando no botão Salvar via seletor: '{sel}'...")
                    loc.first.click(force=True)
                    saved = True
                    break
                except PlaywrightError as e:
                    print(f"      ⚠️ Tentativa com {sel} falhou: {e}")

        if not saved:
            try:
                alt_btn = page.get_by_alt_text("Salvar Solicitação de Serviço")
                if alt_btn.count() > 0 and alt_btn.first.is_visible():
                    print("      💾 Clicando em Salvar via alt_text...")
                    alt_btn.first.click(force=True)
                    saved = True
            except PlaywrightError as e:
                print(f"      ⚠️ Salvar via alt_text falhou: {e}")

        if not saved:
            print("      ⌨️ Acionando atalho de teclado do Maximo (Ctrl+S)...")
            page.keyboard.press("Control+s")
            saved = True

        page.wait_for_load_state("networkidle")
        time.sleep(2)

        ok_candidates = [
            "button:has-text('OK')",
            "input[type='button'][value='OK']",
            "button[name='ok']",
            "[id*='dialog_ok']",
            "button:has-text('Sim')",
        ]
        for ok_sel in ok_candidates:
            ok_loc = page.locator(ok_sel)
            if ok_loc.count() > 0 and ok_loc.first.is_visible():
                print(f"      👌 Confirmando modal de mensagem com '{ok_sel}'...")
                ok_loc.first.click()
                time.sleep(1)
                break

        return saved

    def _audit_and_cleanup_ticket(self, page, ticket: TicketTarget) -> TicketAuditResult:
        """Executa a auditoria completa: print inicial, polling de enfileiramento (4m), print e exclusão."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        direct_link = f"https://suporte.sp.senac.br/maximo/ui/?event=loadapp&value=sr&uniqueid={ticket.ticket_id}"
        screenshots: list[dict[str, str]] = []

        print(f"   [1/3] 🔎 Abrindo solicitação #{ticket.ticket_id}...")
        self._search_ticket(page, ticket.ticket_id)

        initial_shot = SCREENSHOTS_DIR / f"ticket_{ticket.ticket_id}_1_abertura_{ts}.png"
        self._scroll_to_top(page)
        page.screenshot(path=str(initial_shot), full_page=True)
        screenshots.append({
            "stage": "1. Abertura",
            "caption": "Tela inicial do chamado (Antes de reclassificar)",
            "path": str(initial_shot),
        })
        print(f"   📸 Screenshot inicial capturado: {initial_shot.name}")

        print(f"   [2/3] ⏳ Monitorando Grupo de Atendimento (timeout máximo: {self.queue_timeout_s}s / {self.queue_timeout_s // 60} min)...")
        enfileirou = False
        grupo_atendimento = ""
        t0 = time.time()
        poll_interval = 15  # segundos entre verificações

        while True:
            elapsed = int(time.time() - t0)
            grupo_atendimento = self._get_grupo_atendimento(page)

            if grupo_atendimento:
                enfileirou = True
                print(f"   ✨ ENFILEIRADO! Grupo de Atendimento: '{grupo_atendimento}' (tempo: {elapsed}s)")
                break

            if elapsed >= self.queue_timeout_s:
                print(f"   ⚠️ TIMEOUT de {self.queue_timeout_s}s ({self.queue_timeout_s // 60} min) atingido. Chamado NÃO enfileirou grupo de atendimento.")
                break

            print(f"      ... aguardando roteamento ({elapsed}s/{self.queue_timeout_s}s). Próxima checagem em {poll_interval}s...")
            time.sleep(poll_interval)

            # Recarrega a tela para capturar atualizações assíncronas do Maximo
            self._search_ticket(page, ticket.ticket_id)

        wait_seconds = int(time.time() - t0)
        stage_name = "2. Enfileirado" if enfileirou else "2. Não Enfileirado"
        caption_name = (
            f"Enfileirado no grupo: {grupo_atendimento} ({wait_seconds}s)"
            if enfileirou
            else f"Não enfileirou após {wait_seconds}s (Timeout {self.queue_timeout_s // 60} min)"
        )
        queue_shot = SCREENSHOTS_DIR / f"ticket_{ticket.ticket_id}_2_enfileiramento_{ts}.png"
        self._scroll_to_top(page)
        page.screenshot(path=str(queue_shot), full_page=True)
        screenshots.append({
            "stage": stage_name,
            "caption": caption_name,
            "path": str(queue_shot),
        })
        print(f"   📸 Screenshot de enfileiramento capturado: {queue_shot.name}")

        print("   [3/3] 🗑️ Iniciando exclusão do chamado teste (Reclassificar -> 'Excluir chamado teste')...")
        reclassificado = False
        attempts_used = 1
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            attempts_used = attempt
            try:
                print(f"      ▶️ Tentativa de exclusão {attempt}/{self.max_retries}...")

                if attempt > 1:
                    self._search_ticket(page, ticket.ticket_id)

                details_menus = page.get_by_role("img", name="Menu Detalhes")
                if details_menus.count() >= 5:
                    details_menus.nth(4).click()
                elif details_menus.count() > 0:
                    details_menus.first.click()
                else:
                    page.locator("img[title*='Menu Detalhes']").nth(4).click()

                time.sleep(0.8)

                classify_item = page.get_by_role("menuitem", name="Classificar")
                if classify_item.count() == 0:
                    classify_item = page.locator("text='Classificar'")
                classify_item.first.click()
                time.sleep(1.5)

                sg_tree = page.get_by_role("treeitem", name="Solicitações Gerais")
                if sg_tree.count() > 0 and sg_tree.first.is_visible():
                    sg_tree.first.click()
                    time.sleep(0.8)

                chamado_teste_tree = page.get_by_role("treeitem", name="Chamado Teste")
                if chamado_teste_tree.count() > 0 and chamado_teste_tree.first.is_visible():
                    chamado_teste_tree.first.click()
                    time.sleep(0.8)

                excluir_link = page.get_by_role("link", name="Excluir chamado teste")
                if excluir_link.count() > 0 and excluir_link.first.is_visible():
                    excluir_link.first.click()
                else:
                    page.locator("text='Excluir chamado teste'").first.click()

                time.sleep(1)

                self._click_save_ticket(page)

                self._search_ticket(page, ticket.ticket_id)
                if not self._is_reclassificado(page):
                    raise RuntimeError(f"Classificação não virou '{EXCLUIR_LABEL}' após salvar")

                reclassificado = True
                print(f"      ✅ Chamado #{ticket.ticket_id} EXCLUÍDO (Reclassificado com sucesso na tentativa {attempt})!")
                break

            except (PlaywrightError, RuntimeError) as err:
                last_error = str(err)
                print(f"      ⚠️ Falha ao salvar reclassificação na tentativa {attempt}: {last_error}")
                try:
                    no_btn = page.get_by_role("button", name="Não")
                    if no_btn.count() > 0 and no_btn.first.is_visible():
                        no_btn.first.click()
                except PlaywrightError as modal_err:
                    print(f"      ⚠️ Falha ao fechar modal pendente: {modal_err}")
                time.sleep(2)

        final_shot = SCREENSHOTS_DIR / f"ticket_{ticket.ticket_id}_3_exclusao_{ts}.png"
        page.screenshot(path=str(final_shot), full_page=True)
        screenshots.append({
            "stage": "3. Exclusão",
            "caption": "Reclassificado como 'Excluir chamado teste'" if reclassificado else "Falha na exclusão (Ação Manual)",
            "path": str(final_shot),
        })

        manual_action_required = not reclassificado

        return TicketAuditResult(
            ticket_id=ticket.ticket_id,
            flow_name=ticket.flow_name,
            subject=ticket.subject,
            grupo_atendimento=grupo_atendimento,
            enfileirou=enfileirou,
            wait_seconds=wait_seconds,
            reclassificado=reclassificado,
            attempts=attempts_used,
            manual_action_required=manual_action_required,
            error_message=last_error if manual_action_required else "",
            screenshots=screenshots,
            direct_link=direct_link,
        )

    def _generate_reports_and_summary(self, results: list[TicketAuditResult]) -> None:
        """Gera os relatórios HTML e JSON, expurga antigos mantendo apenas 10, e exibe o resumo."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_report_path = REPORTS_DIR / f"icd_audit_{ts}.html"
        json_report_path = REPORTS_DIR / f"icd_cleanup_{ts}.json"

        enfileirados_count = sum(1 for r in results if r.enfileirou)
        nao_enfileirados_count = sum(1 for r in results if not r.enfileirou)
        excluidos_count = sum(1 for r in results if r.reclassificado)
        manual_count = sum(1 for r in results if r.manual_action_required)

        test_run_data = None
        latest_test_json = find_latest_report()
        if latest_test_json and latest_test_json.exists():
            try:
                test_run_data = json.loads(latest_test_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as err:
                logger.warning("Relatório de testes ilegível em %s: %s", latest_test_json, err)

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "timestamp_str": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "total": len(results),
            "enfileirados_count": enfileirados_count,
            "nao_enfileirados_count": nao_enfileirados_count,
            "excluidos_count": excluidos_count,
            "manual_count": manual_count,
            "test_run": test_run_data,
            "items": [
                {
                    "ticket_id": r.ticket_id,
                    "flow_name": r.flow_name,
                    "subject": r.subject,
                    "grupo_atendimento": r.grupo_atendimento,
                    "enfileirou": r.enfileirou,
                    "wait_seconds": r.wait_seconds,
                    "reclassificado": r.reclassificado,
                    "attempts": r.attempts,
                    "manual_action_required": r.manual_action_required,
                    "error_message": r.error_message,
                    "direct_link": r.direct_link,
                    "screenshots": r.screenshots,
                }
                for r in results
            ],
        }

        json_report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

        try:
            generate_html_report(report_data, html_report_path, keep_history=self.keep_history)
        except Exception as err:
            logger.exception("Erro ao gerar relatório HTML")
            print(f"⚠️ Erro ao gerar relatório HTML: {err}")

        print("\n" + "=" * 80)
        print("📊 RESUMO FINAL DA AUDITORIA NO ICD:")
        print(f" • Total de Chamados Processados:  {len(results)}")
        print(f" • Enfileirados com Sucesso:       {enfileirados_count} ✅")
        print(f" • Não Enfileirados (Timeout 5m):  {nao_enfileirados_count} ⚠️")
        print(f" • Excluídos ('Chamado Teste'):    {excluidos_count} 🗑️")
        print(f" • Ação Manual Requerida:          {manual_count} 🚨")
        print("=" * 80)

        for r in results:
            status_enfileiramento = f"✅ Enfileirou: '{r.grupo_atendimento}' ({r.wait_seconds}s)" if r.enfileirou else f"⚠️ Não Enfileirou ({r.wait_seconds}s)"
            status_exclusao = "🗑️ Excluído" if r.reclassificado else "🚨 FALHA NA EXCLUSÃO"
            print(f" • #{r.ticket_id} | {status_enfileiramento} | {status_exclusao}")

        if manual_count > 0:
            print("\n" + "!" * 80)
            print("🚨 ATENÇÃO: OS SEGUINTES CHAMADOS DEVEM SER EXCLUÍDOS MANUALMENTE NO ICD:")
            print("!" * 80)
            for r in results:
                if r.manual_action_required:
                    print(f" • 🔴 Protocolo #{r.ticket_id}")
                    print(f"      Link Direto: {r.direct_link}")
                    print(f"      Erro:        {r.error_message}")
            print("!" * 80)

        print("\n🌐 RELATÓRIO HTML DISPONÍVEL (Abra no navegador):")
        print(f"👉 {html_report_path.resolve()}")
        print(f"📄 Relatório JSON: {json_report_path.resolve()}")
        print(f"🧹 Política de retenção executada: mantidos os {self.keep_history} últimos relatórios.")
        print("=" * 80)


def find_latest_report() -> Path | None:
    """Retorna o caminho do relatório JSON mais recente."""
    json_reports = sorted(REPORTS_DIR.glob("test_run_*.json"), key=os.path.getmtime, reverse=True)
    return json_reports[0] if json_reports else None


def load_tickets_from_report(report_path: Path) -> list[TicketTarget]:
    """Extrai lista de tickets a partir do relatório gerado pelo runner."""
    content = json.loads(report_path.read_text(encoding="utf-8"))
    tickets: list[TicketTarget] = []
    seen = set()

    for item in content.get("results", []):
        for t in item.get("tickets", []):
            tid = str(t.get("ticket_id") or "").strip()
            if tid and tid not in seen:
                seen.add(tid)
                tickets.append(
                    TicketTarget(
                        ticket_id=tid,
                        flow_name=t.get("flow_name", ""),
                        subject=t.get("subject", ""),
                        user_name=t.get("user_name", ""),
                        chapa=t.get("chapa", ""),
                    )
                )
    return tickets


def main():
    parser = argparse.ArgumentParser(description="Robô Playwright para auditoria de enfileiramento (10m) e exclusão no ICD Senac")
    parser.add_argument("--latest", action="store_true", help="Usa automaticamente os chamados do último relatório de testes")
    parser.add_argument("--report", type=str, help="Caminho de um relatório JSON de testes específico")
    parser.add_argument("--tickets", nargs="+", help="Lista de IDs de tickets para auditar (ex: --tickets 6438504 6438505)")
    parser.add_argument("--url", type=str, help="URL de login IAM do Senac")
    parser.add_argument("--headed", action="store_true", help="Executa com navegador visível na tela")
    parser.add_argument("--headless", action="store_true", help="Executa em segundo plano sem janela de navegador")
    parser.add_argument("--queue-timeout", type=int, default=600, help="Tempo máximo de espera pelo enfileiramento em segundos (padrão: 600 / 10 minutos)")
    parser.add_argument("--retries", type=int, default=3, help="Número máximo de tentativas de exclusão (padrão: 3)")
    parser.add_argument("--keep", type=int, default=10, help="Quantidade de relatórios mais recentes para manter no histórico (padrão: 10)")

    args = parser.parse_args()

    tickets: list[TicketTarget] = []

    if args.tickets:
        tickets = [TicketTarget(ticket_id=tid) for tid in args.tickets]
    else:
        target_report: Path | None = None
        if args.report:
            target_report = Path(args.report)
        else:
            target_report = find_latest_report()

        if target_report and target_report.is_file():
            print(f"📄 Carregando chamados do relatório: {target_report}")
            tickets = load_tickets_from_report(target_report)
        else:
            print("⚠️ Nenhum relatório encontrado e nenhum ticket especificado.")
            sys.exit(1)

    if not tickets:
        print("ℹ️ Nenhum chamado encontrado no relatório informado.")
        sys.exit(0)

    headless = False
    if args.headless:
        headless = True
    elif args.headed:
        headless = False

    robot = ICDAuditAndCleanerRobot(
        login_url=args.url,
        headless=headless,
        queue_timeout_s=args.queue_timeout,
        max_retries=args.retries,
        keep_history=args.keep,
    )
    robot.run(tickets)


if __name__ == "__main__":
    main()
