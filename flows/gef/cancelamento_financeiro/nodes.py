"""Runner — cancelamento de matrícula / cancelamento financeiro."""

from __future__ import annotations

from typing import Any

from core.orchestrate_client import create_orchestrate_client
from flows.kit import (
    buttons_screen,
    field_text,
    form_data_of,
    last_user_text,
    match_choice,
    pack,
    protocol_message,
    reject,
    select_form,
    session_block,
)
from flows.payload import anexo_texto, option_pairs
from flows.runtime import parse_boolean
from flows.session import acesso_relatorios, missing_fields, session_from_state
from flows.gef.cancelamento_financeiro import domain as d
from graph.state import MultiAgentState

STEP_TIPO = "tipo"
STEP_LOTE = "lote"
STEP_DESCRICAO = "descricao"
STEP_ID_ALUNO = "id_aluno"
STEP_REQUISICAO = "requisicao"
STEP_DATA = "data"
STEP_CAMPUS = "campus"
STEP_CONFIRM_CAMPUS = "confirm_campus"
STEP_ANEXO = "anexo"
STEP_ARQUIVO = "arquivo"
STEP_MOTIVO_MSG = "motivo_msg"
STEP_ID_CANCELAMENTO = "id_cancelamento"
STEP_ITEM_MOTIVO = "item_motivo"
STEP_ITEM_CONFIRM = "item_confirm"
STEP_ITEM_DESCRICAO = "item_descricao"
STEP_ITEM_ID = "item_id"
STEP_ITEM_REQ = "item_req"
STEP_ITEM_INSC = "item_insc"
STEP_ITEM_MOTIVO_AULA = "item_motivo_aula"
STEP_ITEM_OFERTA = "item_oferta"
STEP_ITEM_ANEXO = "item_anexo"
STEP_ITEM_ARQUIVO = "item_arquivo"


def _texto_form(name: str, title: str, key: str) -> dict[str, Any]:
    return {
        "component": "form",
        "title": title,
        "name": name,
        "fields": [{"key": key, "title": title, "widget": "text", "required": True}],
    }


def _data_form() -> dict[str, Any]:
    return {
        "component": "form",
        "title": d.ASK_DATA,
        "name": "gef_cancelamento_data",
        "fields": [
            {
                "key": "dataRelatorio",
                "title": d.ASK_DATA,
                "widget": "date",
                "required": True,
            }
        ],
    }


def _arquivo_form(name: str) -> dict[str, Any]:
    return {
        "component": "form",
        "title": "Adicione o arquivo desejado:",
        "name": name,
        "fields": [
            {
                "key": "anexo",
                "title": "Arquivo",
                "widget": "file",
                "required": True,
            }
        ],
    }


def _done(text: str, flow_data: dict[str, Any]) -> dict:
    return pack(
        flow_name=d.FLOW_NAME,
        step=None,
        flow_data=flow_data,
        texts=(text,),
        done=True,
    )


def _ask(
    step: str,
    flow_data: dict[str, Any],
    screen: dict[str, Any],
    texts: tuple[str, ...] = (),
) -> dict:
    return pack(
        flow_name=d.FLOW_NAME,
        step=step,
        flow_data=flow_data,
        texts=texts,
        screens=(screen,),
    )


def _nao_entendi(step: str, prompt: str, flow_data: dict[str, Any], screen: dict[str, Any]) -> dict:
    return reject(
        flow_name=d.FLOW_NAME,
        resume_step=step,
        prompt=prompt,
        flow_data=flow_data,
        service_label=d.SERVICE_LABEL,
        resume_ui=[screen],
    )


def _aplicar_linha(flow_data: dict[str, Any], linha: dict[str, str]) -> None:
    flow_data["idAluno"] = linha.get("idAluno") or ""
    flow_data["inscricao"] = linha.get("inscricao") or ""
    flow_data["motivo"] = linha.get("motivo") or ""
    flow_data["motivoDesligamento"] = linha.get("motivoAcao") or linha.get("motivo") or ""
    flow_data["IDRequisicao"] = linha.get("requisicao") or ""
    responsavel = linha.get("responsavel") or ""
    flow_data["responsavel"] = responsavel or flow_data["idAluno"]
    cancelamento = d.digitos_id(linha.get("cancelamento") or "")
    if cancelamento:
        flow_data["idCancelamento"] = cancelamento


def _depois_da_linha(flow_data: dict[str, Any]) -> dict:
    return _ask(STEP_ANEXO, flow_data, buttons_screen(d.ASK_ANEXO, d.SIM_NAO))


def _abrir(info: dict[str, str], flow_data: dict[str, Any]) -> dict:
    situacao = str(flow_data.get("situacao") or "")
    detalhe = str(flow_data.get("descricao") or "").strip()
    fixa = d.descricao_fixa(situacao)
    descricao = f"{fixa}\n\n{detalhe}" if detalhe else fixa
    body = {
        "nome": info.get("nome") or "",
        "email": info.get("email") or "",
        "classificationId": d.CLASSIFICACAO,
        "descricao": descricao,
        "idAluno": str(flow_data.get("idAluno") or ""),
        "responsavel": str(flow_data.get("responsavel") or ""),
        "inscricao": str(flow_data.get("inscricao") or ""),
        "IDRequisicao": str(flow_data.get("IDRequisicao") or ""),
        "motivoDesligamento": str(flow_data.get("motivoDesligamento") or ""),
        "motivoMsg": str(flow_data.get("motivoMsg") or flow_data.get("motivo") or ""),
        "situacaoSolicitacao": situacao,
        "idCancelamento": str(flow_data.get("idCancelamento") or ""),
    }
    anexo = str(flow_data.get("anexo") or "").strip()
    if anexo:
        body["anexo"] = anexo
    result = create_orchestrate_client().post_json("/gef/abertura-chamado", body)
    if result.ticket_id:
        return _done(
            f"Ok, segue protocolo da abertura de chamado.\n\nProtocolo: {result.ticket_id}.",
            flow_data,
        )
    return _done(protocol_message(None, result.error_detail), flow_data)


def _id_do_formulario(user_text: str) -> str:
    data = form_data_of(user_text)
    bruto = ""
    if data:
        bruto = str(data.get("idCancelamento") or data.get(d.ASK_ID_CANCELAMENTO) or "")
    else:
        bruto = field_text(user_text, "idCancelamento") or ""
    return d.digitos_id(bruto)


def _campos_faltantes(info: dict[str, str], flow_data: dict[str, Any]) -> dict:
    tipo = str(flow_data.get("tipo") or "")
    motivo_preenchido = bool(str(flow_data.get("motivo") or "").strip())
    if tipo == "Não processados" and not motivo_preenchido:
        return _ask(
            STEP_MOTIVO_MSG,
            flow_data,
            _texto_form("gef_cancelamento_motivo_msg", d.ASK_MOTIVO_MSG, "motivoMsg"),
        )
    if tipo == "Revisão de Cálculo" and not str(flow_data.get("idCancelamento") or "").strip():
        return _ask(
            STEP_ID_CANCELAMENTO,
            flow_data,
            _texto_form("gef_cancelamento_id", d.ASK_ID_CANCELAMENTO, "idCancelamento"),
        )
    return _abrir(info, flow_data)


def _consultar_por_id(flow_data: dict[str, Any], emplid: str) -> dict:
    result = create_orchestrate_client().get_json(
        "/gef/cancelamento-financeiro",
        {"emplid": emplid},
    )
    linhas = d.linhas_de(result.payload)
    if not result.ok or not linhas:
        detalhe = result.error_detail or "Nenhum registro encontrado"
        return _done(f"Não consultei o cancelamento. {detalhe}", flow_data)
    flow_data["linhas"] = linhas
    if len(linhas) > 1:
        options = [(linha["requisicao"], linha["requisicao"]) for linha in linhas if linha["requisicao"]]
        flow_data["requisicao_options"] = options
        return _ask(
            STEP_REQUISICAO,
            flow_data,
            select_form(
                title=d.ASK_REQUISICAO,
                name="gef_cancelamento_requisicao",
                key="requisicao",
                field_title=d.ASK_REQUISICAO,
                options=options,
            ),
        )
    _aplicar_linha(flow_data, linhas[0])
    return _depois_da_linha(flow_data)


def _tela_campus(flow_data: dict[str, Any]) -> dict[str, Any]:
    options = [tuple(item) for item in flow_data.get("campus_options") or []]
    return select_form(
        title=d.ASK_CAMPUS,
        name="gef_cancelamento_campus",
        key="campus",
        field_title=d.ASK_CAMPUS,
        options=options,
    )


def _item_atual(flow_data: dict[str, Any]) -> dict[str, str]:
    lote = flow_data.get("lote") or []
    index = int(flow_data.get("lote_i") or 0)
    if index >= len(lote):
        return {}
    item = lote[index]
    return item if isinstance(item, dict) else {}


def _proximo_item(info: dict[str, str], flow_data: dict[str, Any], texto: str) -> dict:
    protocolos = list(flow_data.get("protocolos") or [])
    if texto:
        protocolos.append(texto)
    flow_data["protocolos"] = protocolos
    flow_data["lote_i"] = int(flow_data.get("lote_i") or 0) + 1
    if flow_data["lote_i"] >= len(flow_data.get("lote") or []):
        corpo = "\n\n".join(protocolos) or "Consulta do lote encerrada."
        return _done(corpo, flow_data)
    return _pedir_motivo_item(flow_data)


def _pedir_motivo_item(flow_data: dict[str, Any]) -> dict:
    item = _item_atual(flow_data)
    motivos = []
    vistos = set()
    for linha in flow_data.get("lote") or []:
        if not isinstance(linha, dict):
            continue
        motivo = str(linha.get("motivoAcao") or linha.get("motivo") or "").strip()
        if motivo and motivo not in vistos:
            vistos.add(motivo)
            motivos.append((motivo, motivo))
    if not motivos:
        return _ask(
            STEP_ITEM_MOTIVO,
            flow_data,
            _texto_form("gef_cancelamento_motivo_item", d.ASK_MOTIVO, "motivo"),
        )
    flow_data["motivo_options"] = motivos
    flow_data["item_idAluno"] = item.get("idAluno") or ""
    return _ask(
        STEP_ITEM_MOTIVO,
        flow_data,
        select_form(
            title=d.ASK_MOTIVO,
            name="gef_cancelamento_motivo_item",
            key="motivo",
            field_title=d.ASK_MOTIVO,
            options=motivos,
        ),
    )


def _faltantes_item(flow_data: dict[str, Any]) -> dict:
    item = _item_atual(flow_data)
    if not str(flow_data.get("item_idAluno") or item.get("idAluno") or "").strip():
        return _ask(
            STEP_ITEM_ID,
            flow_data,
            _texto_form("gef_cancelamento_item_id", d.ASK_ID_ALUNO_ITEM, "idAluno"),
        )
    if not str(item.get("requisicao") or flow_data.get("item_requisicao") or "").strip():
        return _ask(
            STEP_ITEM_REQ,
            flow_data,
            _texto_form("gef_cancelamento_item_req", d.ASK_REQUISICAO_ITEM, "requisicao"),
        )
    if not str(item.get("inscricao") or flow_data.get("item_inscricao") or "").strip():
        return _ask(
            STEP_ITEM_INSC,
            flow_data,
            _texto_form("gef_cancelamento_item_insc", d.ASK_INSCRICAO, "inscricao"),
        )
    if not str(flow_data.get("item_motivo") or "").strip():
        return _ask(
            STEP_ITEM_MOTIVO_AULA,
            flow_data,
            _texto_form("gef_cancelamento_motivo_aula", d.ASK_MOTIVO_AULA, "motivoAula"),
        )
    if not str(item.get("oferta") or flow_data.get("item_oferta") or "").strip():
        return _ask(
            STEP_ITEM_OFERTA,
            flow_data,
            _texto_form("gef_cancelamento_item_oferta", d.ASK_OFERTA, "oferta"),
        )
    return _consultar_item(flow_data)


def _consultar_item(flow_data: dict[str, Any]) -> dict:
    item = _item_atual(flow_data)
    id_aluno = str(flow_data.get("item_idAluno") or item.get("idAluno") or "")
    responsavel = str(item.get("responsavel") or id_aluno)
    body = {
        "classStructureId": d.CLASSIFICACAO,
        "idAluno": id_aluno,
        "responsavel": responsavel,
        "inscricao": str(flow_data.get("item_inscricao") or item.get("inscricao") or ""),
        "IDRequisicao": str(flow_data.get("item_requisicao") or item.get("requisicao") or ""),
        "motivoDesligamento": str(flow_data.get("item_motivo") or ""),
    }
    result = create_orchestrate_client().post_json(
        "/gef/cancelamento-financeiro/consulta-chamado",
        body,
    )
    ticket = result.ticket_id
    if result.ok and ticket:
        aviso = (
            "Já existe(m) chamado(s) para essa solicitação. "
            f"Para maiores informações, acompanhe o status do(s) chamado(s) {ticket}."
        )
        flow_data["item_ticket"] = ticket
    else:
        aviso = ""
        flow_data["item_ticket"] = ""
    mensagem = (
        "Anexar documento\n\n"
        "Deseja anexar um arquivo para o aluno com o seguinte identificador?\n\n"
        f"ID do aluno: {id_aluno}\n\n"
        "Você poderá enviar um documento relacionado a este aluno "
        "ou seguir sem anexar nenhum arquivo."
    )
    texts = tuple(part for part in (aviso, mensagem) if part)
    return _ask(STEP_ITEM_ANEXO, flow_data, buttons_screen(d.ASK_ANEXO_ITEM, d.SIM_NAO), texts)


def _fechar_item(info: dict[str, str], flow_data: dict[str, Any]) -> dict:
    ticket = str(flow_data.get("item_ticket") or "").strip()
    if ticket:
        return _proximo_item(
            info,
            flow_data,
            f"Já existe chamado para o aluno {flow_data.get('item_idAluno') or ''}. Protocolo: {ticket}.",
        )
    item = _item_atual(flow_data)
    flow_data["tipo"] = "Não processados"
    flow_data["situacao"] = d.situacao_de("Não processados")
    flow_data["descricao"] = str(flow_data.get("item_descricao") or "")
    flow_data["idAluno"] = str(flow_data.get("item_idAluno") or item.get("idAluno") or "")
    flow_data["responsavel"] = str(item.get("responsavel") or flow_data["idAluno"])
    flow_data["inscricao"] = str(flow_data.get("item_inscricao") or item.get("inscricao") or "")
    flow_data["IDRequisicao"] = str(flow_data.get("item_requisicao") or item.get("requisicao") or "")
    flow_data["motivoDesligamento"] = str(flow_data.get("item_motivo") or "")
    flow_data["motivo"] = str(flow_data.get("item_motivo") or "")
    flow_data["motivoMsg"] = str(flow_data.get("item_motivo") or "")
    flow_data["idCancelamento"] = str(item.get("cancelamento") or "")
    flow_data["anexo"] = str(flow_data.get("item_anexo") or "")
    aberto = _abrir(info, flow_data)
    mensagem = ""
    messages = aberto.get("messages") or []
    if messages:
        mensagem = str(getattr(messages[0], "content", "") or "")
    return _proximo_item(info, flow_data, mensagem)


def gef_cancelamento_financeiro_node(state: MultiAgentState) -> dict:
    step = state.get("flow_step")
    flow_data: dict[str, Any] = dict(state.get("flow_data") or {})
    user_text = last_user_text(state.get("messages") or [])
    info = session_from_state(state)

    if step is None:
        missing = missing_fields(info, ("nome", "email"))
        if missing:
            return _done(session_block(missing), {})
        acesso = acesso_relatorios(state)
        status = str(acesso.get("status") or "")
        if acesso.get("acessoTotal") is True:
            return _ask(STEP_TIPO, {}, buttons_screen(d.ASK_TIPO, d.TIPOS))
        if status != "200":
            return _done(d.UNAVAILABLE, {})
        return _done(d.NO_ACCESS, {})

    if step == STEP_TIPO:
        choice = match_choice(user_text, d.TIPOS)
        if choice is None:
            return _nao_entendi(STEP_TIPO, d.ASK_TIPO, flow_data, buttons_screen(d.ASK_TIPO, d.TIPOS))
        flow_data["tipo"] = choice
        flow_data["situacao"] = d.situacao_de(choice)
        if choice == "Não processados":
            return _ask(STEP_LOTE, flow_data, buttons_screen(d.ASK_LOTE, d.SIM_NAO))
        return _ask(
            STEP_DESCRICAO,
            flow_data,
            _texto_form("gef_cancelamento_descricao", d.ASK_DESCRICAO, "descricao"),
        )

    if step == STEP_LOTE:
        choice = parse_boolean(user_text)
        if choice is None:
            choice_value = match_choice(user_text, d.SIM_NAO)
            choice = True if choice_value == "sim" else False if choice_value == "nao" else None
        if choice is None:
            return _nao_entendi(STEP_LOTE, d.ASK_LOTE, flow_data, buttons_screen(d.ASK_LOTE, d.SIM_NAO))
        if choice is False:
            return _ask(
                STEP_DESCRICAO,
                flow_data,
                _texto_form("gef_cancelamento_descricao", d.ASK_DESCRICAO, "descricao"),
            )
        return _ask(STEP_DATA, flow_data, _data_form())

    if step == STEP_DESCRICAO:
        texto = field_text(user_text, "descricao")
        if not texto:
            return _nao_entendi(
                STEP_DESCRICAO,
                d.ASK_DESCRICAO,
                flow_data,
                _texto_form("gef_cancelamento_descricao", d.ASK_DESCRICAO, "descricao"),
            )
        flow_data["descricao"] = texto
        return _ask(
            STEP_ID_ALUNO,
            flow_data,
            _texto_form("gef_cancelamento_id_aluno", d.ASK_ID_ALUNO, "idAluno"),
        )

    if step == STEP_ID_ALUNO:
        emplid = field_text(user_text, "idAluno")
        if not emplid:
            return _nao_entendi(
                STEP_ID_ALUNO,
                d.ASK_ID_ALUNO,
                flow_data,
                _texto_form("gef_cancelamento_id_aluno", d.ASK_ID_ALUNO, "idAluno"),
            )
        flow_data["emplid"] = emplid
        return _consultar_por_id(flow_data, emplid)

    if step == STEP_REQUISICAO:
        options = [tuple(item) for item in flow_data.get("requisicao_options") or []]
        chosen = field_text(user_text, "requisicao") or match_choice(user_text, options)
        linha = next(
            (
                item
                for item in flow_data.get("linhas") or []
                if isinstance(item, dict) and str(item.get("requisicao") or "") == str(chosen or "")
            ),
            None,
        )
        if linha is None:
            return _nao_entendi(
                STEP_REQUISICAO,
                d.ASK_REQUISICAO,
                flow_data,
                select_form(
                    title=d.ASK_REQUISICAO,
                    name="gef_cancelamento_requisicao",
                    key="requisicao",
                    field_title=d.ASK_REQUISICAO,
                    options=options,
                ),
            )
        _aplicar_linha(flow_data, linha)
        return _depois_da_linha(flow_data)

    if step == STEP_DATA:
        raw = field_text(user_text, "dataRelatorio") or ""
        day = d.parse_date(raw)
        if day is None:
            return _nao_entendi(STEP_DATA, d.ASK_DATA, flow_data, _data_form())
        flow_data["data_lote"] = day.isoformat()
        if not info.get("chapa"):
            return _done(session_block(["chapa"]), flow_data)
        result = create_orchestrate_client().get_json(
            "/gef/listar-campus",
            {"chapa": info["chapa"]},
        )
        options = option_pairs(result.payload)
        if not result.ok or not options:
            return _done(d.UNAVAILABLE, flow_data)
        flow_data["campus_options"] = options
        return _ask(STEP_CAMPUS, flow_data, _tela_campus(flow_data))

    if step == STEP_CAMPUS:
        options = [tuple(item) for item in flow_data.get("campus_options") or []]
        chosen = field_text(user_text, "campus") or match_choice(user_text, options)
        label = next((item[0] for item in options if item[1] == chosen or item[0] == chosen), "")
        if not chosen:
            return _nao_entendi(STEP_CAMPUS, d.ASK_CAMPUS, flow_data, _tela_campus(flow_data))
        flow_data["campus"] = chosen
        flow_data["campus_label"] = label or chosen
        return _ask(
            STEP_CONFIRM_CAMPUS,
            flow_data,
            buttons_screen(d.ASK_CONFIRM, d.SIM_NAO),
            (f"Selecionado o campus {flow_data['campus_label']}",),
        )

    if step == STEP_CONFIRM_CAMPUS:
        choice = parse_boolean(user_text)
        if choice is None:
            picked = match_choice(user_text, d.SIM_NAO)
            choice = True if picked == "sim" else False if picked == "nao" else None
        if choice is None:
            return _nao_entendi(
                STEP_CONFIRM_CAMPUS,
                d.ASK_CONFIRM,
                flow_data,
                buttons_screen(d.ASK_CONFIRM, d.SIM_NAO),
            )
        if choice is False:
            return _ask(STEP_CAMPUS, flow_data, _tela_campus(flow_data))
        result = create_orchestrate_client().get_json(
            "/gef/cancelamento-financeiro/lote",
            {
                "campus": flow_data.get("campus"),
                "startDate": flow_data.get("data_lote"),
                "endDate": flow_data.get("data_lote"),
            },
        )
        linhas = d.linhas_de(result.payload)
        if not result.ok or not linhas:
            detalhe = result.error_detail or "Nenhum registro encontrado"
            return _done(f"Não consultei o lote. {detalhe}", flow_data)
        flow_data["lote"] = linhas
        flow_data["lote_i"] = 0
        flow_data["protocolos"] = []
        return _pedir_motivo_item(flow_data)

    if step == STEP_ANEXO:
        choice = parse_boolean(user_text)
        if choice is None:
            picked = match_choice(user_text, d.SIM_NAO)
            choice = True if picked == "sim" else False if picked == "nao" else None
        if choice is None:
            return _nao_entendi(STEP_ANEXO, d.ASK_ANEXO, flow_data, buttons_screen(d.ASK_ANEXO, d.SIM_NAO))
        if choice is True:
            return _ask(STEP_ARQUIVO, flow_data, _arquivo_form("gef_cancelamento_arquivo"))
        return _campos_faltantes(info, flow_data)

    if step == STEP_ARQUIVO:
        anexo = anexo_texto(form_data_of(user_text))
        if not anexo:
            return _nao_entendi(STEP_ARQUIVO, "Adicione o arquivo desejado:", flow_data, _arquivo_form("gef_cancelamento_arquivo"))
        flow_data["anexo"] = anexo
        return _campos_faltantes(info, flow_data)

    if step == STEP_MOTIVO_MSG:
        texto = field_text(user_text, "motivoMsg")
        if not texto:
            return _nao_entendi(
                STEP_MOTIVO_MSG,
                d.ASK_MOTIVO_MSG,
                flow_data,
                _texto_form("gef_cancelamento_motivo_msg", d.ASK_MOTIVO_MSG, "motivoMsg"),
            )
        flow_data["motivoMsg"] = texto
        flow_data["motivo"] = texto
        return _abrir(info, flow_data)

    if step == STEP_ID_CANCELAMENTO:
        valor = _id_do_formulario(user_text)
        if not valor:
            return _ask(
                STEP_ID_CANCELAMENTO,
                flow_data,
                _texto_form("gef_cancelamento_id", d.ASK_ID_CANCELAMENTO, "idCancelamento"),
                (d.ID_INVALID,),
            )
        flow_data["idCancelamento"] = valor
        return _abrir(info, flow_data)

    if step == STEP_ITEM_MOTIVO:
        options = [tuple(item) for item in flow_data.get("motivo_options") or []]
        chosen = field_text(user_text, "motivo") or match_choice(user_text, options)
        if not chosen:
            screen = (
                select_form(
                    title=d.ASK_MOTIVO,
                    name="gef_cancelamento_motivo_item",
                    key="motivo",
                    field_title=d.ASK_MOTIVO,
                    options=options,
                )
                if options
                else _texto_form("gef_cancelamento_motivo_item", d.ASK_MOTIVO, "motivo")
            )
            return _nao_entendi(STEP_ITEM_MOTIVO, d.ASK_MOTIVO, flow_data, screen)
        flow_data["item_motivo"] = chosen
        return _ask(
            STEP_ITEM_CONFIRM,
            flow_data,
            buttons_screen(d.ASK_MOTIVO_OK, d.SIM_NAO),
            (f"Motivo: {chosen}",),
        )

    if step == STEP_ITEM_CONFIRM:
        choice = parse_boolean(user_text)
        if choice is None:
            picked = match_choice(user_text, d.SIM_NAO)
            choice = True if picked == "sim" else False if picked == "nao" else None
        if choice is None:
            return _nao_entendi(
                STEP_ITEM_CONFIRM,
                d.ASK_MOTIVO_OK,
                flow_data,
                buttons_screen(d.ASK_MOTIVO_OK, d.SIM_NAO),
            )
        if choice is False:
            return _pedir_motivo_item(flow_data)
        return _ask(
            STEP_ITEM_DESCRICAO,
            flow_data,
            _texto_form("gef_cancelamento_item_desc", d.ASK_DESCRICAO_CURTA, "descricao"),
        )

    if step == STEP_ITEM_DESCRICAO:
        texto = field_text(user_text, "descricao")
        if not texto:
            return _nao_entendi(
                STEP_ITEM_DESCRICAO,
                d.ASK_DESCRICAO_CURTA,
                flow_data,
                _texto_form("gef_cancelamento_item_desc", d.ASK_DESCRICAO_CURTA, "descricao"),
            )
        flow_data["item_descricao"] = texto
        return _faltantes_item(flow_data)

    if step == STEP_ITEM_ID:
        valor = field_text(user_text, "idAluno")
        if not valor:
            return _nao_entendi(
                STEP_ITEM_ID,
                d.ASK_ID_ALUNO_ITEM,
                flow_data,
                _texto_form("gef_cancelamento_item_id", d.ASK_ID_ALUNO_ITEM, "idAluno"),
            )
        flow_data["item_idAluno"] = valor
        return _faltantes_item(flow_data)

    if step == STEP_ITEM_REQ:
        valor = field_text(user_text, "requisicao")
        if not valor:
            return _nao_entendi(
                STEP_ITEM_REQ,
                d.ASK_REQUISICAO_ITEM,
                flow_data,
                _texto_form("gef_cancelamento_item_req", d.ASK_REQUISICAO_ITEM, "requisicao"),
            )
        flow_data["item_requisicao"] = valor
        return _faltantes_item(flow_data)

    if step == STEP_ITEM_INSC:
        valor = field_text(user_text, "inscricao")
        if not valor:
            return _nao_entendi(
                STEP_ITEM_INSC,
                d.ASK_INSCRICAO,
                flow_data,
                _texto_form("gef_cancelamento_item_insc", d.ASK_INSCRICAO, "inscricao"),
            )
        flow_data["item_inscricao"] = valor
        return _faltantes_item(flow_data)

    if step == STEP_ITEM_MOTIVO_AULA:
        valor = field_text(user_text, "motivoAula")
        if not valor:
            return _nao_entendi(
                STEP_ITEM_MOTIVO_AULA,
                d.ASK_MOTIVO_AULA,
                flow_data,
                _texto_form("gef_cancelamento_motivo_aula", d.ASK_MOTIVO_AULA, "motivoAula"),
            )
        flow_data["item_motivo"] = valor
        return _faltantes_item(flow_data)

    if step == STEP_ITEM_OFERTA:
        valor = field_text(user_text, "oferta")
        if not valor:
            return _nao_entendi(
                STEP_ITEM_OFERTA,
                d.ASK_OFERTA,
                flow_data,
                _texto_form("gef_cancelamento_item_oferta", d.ASK_OFERTA, "oferta"),
            )
        flow_data["item_oferta"] = valor
        return _faltantes_item(flow_data)

    if step == STEP_ITEM_ANEXO:
        choice = parse_boolean(user_text)
        if choice is None:
            picked = match_choice(user_text, d.SIM_NAO)
            choice = True if picked == "sim" else False if picked == "nao" else None
        if choice is None:
            return _nao_entendi(
                STEP_ITEM_ANEXO,
                d.ASK_ANEXO_ITEM,
                flow_data,
                buttons_screen(d.ASK_ANEXO_ITEM, d.SIM_NAO),
            )
        if choice is True:
            return _ask(STEP_ITEM_ARQUIVO, flow_data, _arquivo_form("gef_cancelamento_item_arquivo"))
        flow_data["item_anexo"] = ""
        return _fechar_item(info, flow_data)

    if step == STEP_ITEM_ARQUIVO:
        anexo = anexo_texto(form_data_of(user_text))
        if not anexo:
            return _nao_entendi(
                STEP_ITEM_ARQUIVO,
                "Adicione o arquivo desejado:",
                flow_data,
                _arquivo_form("gef_cancelamento_item_arquivo"),
            )
        flow_data["item_anexo"] = anexo
        return _fechar_item(info, flow_data)

    return _ask(STEP_TIPO, {}, buttons_screen(d.ASK_TIPO, d.TIPOS))
