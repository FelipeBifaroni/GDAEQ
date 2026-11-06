import pandas as pd
from datetime import datetime
import math
from models.domain import ConexaoSerial, Experimento, Professor, Turma, Substancia, ExperimentoSubstancia, ParametroSimulacao, DadoGrafico
from models.repository import ExperimentoRepository
from models.domain import LogAlerta
from models.log_repository import LogRepository

class ExperimentoController:
    def __init__(self):
        self.experimento = Experimento()
        self.experimento_id_db = None
        self.executando = False

    def iniciar_ensaio(self, dados_form: dict) -> float:
        self.experimento.nome = dados_form["nome_exp"]
        self.experimento.descricao = dados_form.get("descricao", "")

        # 1. Obter ou criar IDs reais para Professor, Turma e Substância
        prof_id_real = ExperimentoRepository.obter_ou_criar_professor(dados_form["professor"])
        turma_id_real = ExperimentoRepository.obter_ou_criar_turma(dados_form["turma"])

        # === VERIFICAR DUPLICIDADE ANTES DE INICIAR QUALQUER COISA ===
        if ExperimentoRepository.existe_experimento_igual(
                nome=self.experimento.nome,
                professor_id=prof_id_real,
                turma_id=turma_id_real,
                descricao=self.experimento.descricao
        ):
            raise ValueError(
                "Já existe um experimento com esses mesmos dados."
            )
        # ======================================================================

        subst_id_real = ExperimentoRepository.obter_ou_criar_substancia(
            nome=dados_form["subst_nome"],
            formula=dados_form["subst_formula"],
            estado_fisico=dados_form["estado_fisico"],
            massa_molar=dados_form["massa_molar"],
            entalpia=dados_form["entalpia"]
        )

        # Atualiza os objetos da memória
        self.experimento.professor = Professor(prof_id_real, dados_form["professor"])
        self.experimento.turma = Turma(turma_id_real, dados_form["turma"])

        subst = Substancia(
            id_subst=subst_id_real,
            nome=dados_form["subst_nome"],
            formula=dados_form["subst_formula"],
            estado_fisico=dados_form["estado_fisico"],
            massa_molar=dados_form["massa_molar"],
            entalpia_formacao=dados_form["entalpia"]
        )

        self.experimento.experimento_substancia = ExperimentoSubstancia(
            id_exp_subst=None,
            coeficiente_estequiometrico=dados_form["coef_estequio"],
            substancia=subst
        )

        self.experimento.parametro_simulacao = ParametroSimulacao(
            id_param=None,
            temp_inicial=dados_form["temp_ini"],
            massa_inicial_a=dados_form["massa_reagente"],
            massa_total=dados_form["massa_total"]
        )

        # Configura a porta COM
        self.experimento.conexao_serial.porta_com = dados_form["porta_com"]

        # Inicia o experimento e estabelece a conexão serial

        try:
            temperatura_inicial = self.experimento.temperatura_inicial_sensor

            if temperatura_inicial is None:
                raise ValueError(
                    "Realize a tara do sensor antes de iniciar o experimento."
                )

            self.experimento.iniciar_ensaio(temperatura_inicial)

            (
                self.experimento_id_db,
                parametro_id_real,
                exp_subst_id_real
            ) = ExperimentoRepository.salvar_experimento_completo(
                nome=self.experimento.nome,
                tipo_reacao=self.experimento.tipo_reacao,
                turma_id=turma_id_real,
                professor_id=prof_id_real,
                descricao=self.experimento.descricao,
                temp_inicial=self.experimento.parametro_simulacao.temp_inicial,
                massa_inicial_a=self.experimento.parametro_simulacao.massa_inicial_a,
                massa_total=self.experimento.parametro_simulacao.massa_total,
                substancia_id=subst_id_real,
                papel="Reagente",
                coeficiente=self.experimento.experimento_substancia.coeficiente_estequiometrico
            )

            # Atualiza os objetos com os IDs reais gerados pelo banco
            self.experimento.parametro_simulacao.id = parametro_id_real
            self.experimento.experimento_substancia.id = exp_subst_id_real


        except Exception:
            self.experimento.conexao_serial.desconectar()
            self.experimento.status = "Inativo"
            self.experimento_id_db = None
            raise

        self.executando = True

        return self.experimento.delta_t_calculado

    def obter_proximo_ponto(self) -> dict | None:
        try:
            ponto = self.experimento.proximo_ponto()


        except (ConnectionError, TimeoutError, ValueError) as e:

            print(f"Erro na leitura do sensor: {e}")

            # Registra a falha associada ao experimento atual

            if self.experimento_id_db:

                try:

                    from models.domain import LogAlerta

                    from models.log_repository import LogRepository

                    novo_log = LogAlerta(

                        id_log=None,

                        tipo_evento="FALHA_COMUNICACAO",

                        descricao=f"Falha na leitura do sensor: {e}"

                    )

                    LogRepository.salvar(

                        novo_log,

                        self.experimento_id_db

                    )


                except Exception as log_err:

                    print(f"Erro ao salvar alerta: {log_err}")

            # Interrompe sem excluir os dados já registrados

            self.interromper_emergencia(

                motivo=f"Falha na leitura do sensor: {e}",

                descartar_registro=False

            )

            return {
                "tempo": self.experimento.tempo_decorrido,
                "temp_real": None,
                "temp_simulada": None,
                "status": "Emergência",
                "motivo": f"Falha na leitura do sensor: {e}"
            }

        if ponto:
            # Salva cada ponto de telemetria gerado no SQLite em tempo real
            if self.experimento_id_db:
                try:
                    ExperimentoRepository.salvar_dado_telemetria(
                        experimento_id=self.experimento_id_db,
                        tempo=ponto["tempo"],
                        temp_real=ponto["temp_real"],
                        temp_simulada=ponto["temp_simulada"]
                    )

                except Exception as e:
                    erro_str = str(e)
                    print(
                        f"⚠️ Alerta da Trigger de Segurança do Banco: {erro_str}"
                    )

                    if (
                            "fora da faixa operacional" in erro_str
                            or "ABORT" in erro_str
                    ):
                        # 1. Grava o alerta na tabela LogAlerta
                        try:
                            from models.domain import LogAlerta
                            from models.log_repository import LogRepository

                            novo_log = LogAlerta(
                                id_log=None,
                                tipo_evento="EMERGENCIA_TEMPERATURA",
                                descricao=(
                                    f"Temperatura crítica "
                                    f"({ponto['temp_real']:.2f}°C) "
                                    f"bloqueada pela Trigger."
                                )
                            )

                            LogRepository.salvar(
                                novo_log,
                                self.experimento_id_db
                            )

                        except Exception as log_err:
                            print(
                                f"❌ Erro ao salvar log no banco: {log_err}"
                            )

                        self.interromper_emergencia(
                            motivo="Temperatura crítica detectada pela proteção do banco de dados.",
                            descartar_registro=True
                        )

                        return {
                            "tempo": self.experimento.tempo_decorrido,
                            "temp_real": None,
                            "temp_simulada": None,
                            "status": "Emergência",
                            "motivo": "Temperatura crítica detectada pela proteção do banco de dados."
                        }

            if ponto["status"] == "Finalizado":
                self.experimento.conexao_serial.desconectar()

        return ponto

    def pausar_ensaio(self) -> str:
        self.experimento.pausar_ensaio()
        return self.experimento.status

    def interromper_emergencia(
            self,
            motivo: str = "Parada de emergência acionada pelo operador.",
            descartar_registro: bool = True
    ) -> None:

        self.executando = False

        self.experimento.interromper_emergencia(motivo)

        self.experimento.conexao_serial.desconectar()

        if descartar_registro and self.experimento_id_db:
            try:
                ExperimentoRepository.descartar_experimento_emergencia(
                    self.experimento_id_db
                )
                self.experimento_id_db = None

            except Exception as e:
                print(f"⚠️ Erro ao descartar experimento de emergência: {e}")

    def listar_historico_banco(self) -> list:
        """Busca o histórico utilizando estritamente o Repositório."""
        linhas = ExperimentoRepository.listar_todos()
        historico = []
        for linha in linhas:
            historico.append({
                "id": linha[0],
                "nome": linha[1],
                "data": linha[2],
                "professor": linha[3] or "N/A",
                "turma": linha[4] if len(linha) > 4 and linha[4] else "N/A"
            })
        return historico

    def listar_logs_alerta(self) -> list:
        """Retorna os registros de alerta para a interface."""
        return LogRepository.listar_todos()

    def obter_dados_experimento_ativo(self) -> dict:
        """
        Retorna um dicionário limpo com os dados do experimento atual,
        evitando que a View precise mexer diretamente nos objetos de domínio.
        """
        exp = self.experimento
        param = exp.parametro_simulacao
        subst_obj = exp.experimento_substancia.substancia if exp.experimento_substancia else None

        return {
            "nome_exp": exp.nome,
            "professor": exp.professor.nome if exp.professor else "",
            "turma": exp.turma.nome if exp.turma else "",
            "subst_nome": subst_obj.nome if subst_obj else "",
            "subst_formula": subst_obj.formula if subst_obj else "",
            "massa_molar": subst_obj.massa_molar if subst_obj else 0.0,
            "massa_reagente": param.massa_inicial_a if param else 0.0,
            "entalpia": subst_obj.entalpia_formacao if subst_obj else 0.0,
            "temp_ini": param.temp_inicial if param else 25.0,
            "massa_total": param.massa_total if param else 100.0,
            "porta_com": exp.conexao_serial.porta_com if exp.conexao_serial else "COM3",
            "descricao": exp.descricao or ""
        }

    def carregar_experimento_por_id(self, experimento_id: int):
        """Carrega um experimento gravado do banco para a memória atual do controller."""
        exp_info, param_info, pontos_db = ExperimentoRepository.carregar_experimento_completo(experimento_id)
        print("DADOS BRUTOS DO BANCO:", exp_info)
        if not exp_info:
            return False

        # exp_info: [nome, tipo_reacao, descricao, prof_nome, turma_nome, subst_nome, subst_formula, massa_molar, entalpia, coeficiente]
        self.experimento = Experimento(id_exp=experimento_id, nome=exp_info[0], tipo_reacao=exp_info[1],
                                       descricao=exp_info[2] or "")
        prof_id = exp_info[10] if exp_info[10] is not None else 1
        turma_id = exp_info[11] if exp_info[11] is not None else 1

        self.experimento.professor = Professor(prof_id, exp_info[3] or "Professor Padrão")
        self.experimento.turma = Turma(turma_id, exp_info[4] or "Turma Padrão")

        # Reconstrói a substância se existir registo associado
        if exp_info[5]:
            subst = Substancia(
                id_subst=exp_info[12],
                nome=exp_info[5],
                formula=exp_info[6],
                estado_fisico="Líquido",
                massa_molar=exp_info[7],
                entalpia_formacao=exp_info[8]
            )
            self.experimento.experimento_substancia = ExperimentoSubstancia(
                id_exp_subst=exp_info[13],
                substancia=subst,
                coeficiente_estequiometrico=(
                    exp_info[9] if exp_info[9] is not None else 1
                )
            )

        if param_info:
            self.experimento.parametro_simulacao = ParametroSimulacao(
                id_param=param_info[0],
                temp_inicial=param_info[1],
                massa_inicial_a=param_info[2],
                massa_total=param_info[3]
            )

        # Reconstrói os pontos do gráfico
        self.experimento.dados_grafico = []
        for p in pontos_db:
            dado = DadoGrafico(
                id_dado=p[0],
                tempo=p[1],
                temp_real=p[2],
                temp_simulada=p[3]
            )
            self.experimento.dados_grafico.append(dado)

        self.experimento.status = "Finalizado"
        self.experimento_id_db = experimento_id
        try:
            self.experimento.calcular_calorimetria()
        except Exception as e:
            print(f"⚠️ Aviso ao recalcular ΔT: {e}")

        return True

    def atualizar_experimento_atual(self, dados_form: dict) -> bool:
        """Atualiza o cabeçalho e a substância do experimento ativo no banco."""
        if not self.experimento_id_db:
            return False

        # 1. Obtém ou cria os IDs para Professor, Turma e a nova Substância informada na tela
        prof_id_real = ExperimentoRepository.obter_ou_criar_professor(dados_form["professor"])
        turma_id_real = ExperimentoRepository.obter_ou_criar_turma(dados_form["turma"])

        subst_id_real = ExperimentoRepository.obter_ou_criar_substancia(
            nome=dados_form["subst_nome"],
            formula=dados_form["subst_formula"],
            estado_fisico=dados_form.get("estado_fisico", "Líquido"),
            massa_molar=dados_form["massa_molar"],
            entalpia=dados_form["entalpia"]
        )

        # 2. Executa a atualização completa aproveitando a função unificada
        sucesso = ExperimentoRepository.atualizar_cabecalho_experimento(
            experimento_id=self.experimento_id_db,
            nome_exp=dados_form["nome_exp"],
            professor_id=prof_id_real,
            turma_id=turma_id_real,
            descricao=dados_form.get("descricao", ""),
            substancia_id=subst_id_real
        )

        if sucesso:
            # Atualiza os dados na memória RAM local do controller
            self.experimento.nome = dados_form["nome_exp"]
            self.experimento.descricao = dados_form.get("descricao", "")
            self.experimento.professor = Professor(prof_id_real, dados_form["professor"])
            self.experimento.turma = Turma(turma_id_real, dados_form["turma"])

            subst_atualizada = Substancia(
                id_subst=subst_id_real,
                nome=dados_form["subst_nome"],
                formula=dados_form["subst_formula"],
                estado_fisico="Líquido",
                massa_molar=dados_form["massa_molar"],
                entalpia_formacao=dados_form["entalpia"]
            )
            if self.experimento.experimento_substancia:
                self.experimento.experimento_substancia.substancia = subst_atualizada

        return sucesso


    def excluir_experimento(self, experimento_id: int) -> bool:
        """Exclui um experimento do banco e limpa a memória se for o ativo."""
        sucesso = ExperimentoRepository.excluir_experimento_banco(experimento_id)

        if sucesso and self.experimento_id_db == experimento_id:
            # Se o utilizador apagou o experimento que estava aberto na tela, limpa o ID ativo
            self.experimento_id_db = None

        return sucesso

    def verificar_e_processar_temperatura(self, temp_atual: float):
        """Verifica se a temperatura está na faixa segura (0°C a 100°C)."""

        if not math.isfinite(temp_atual):
            raise ValueError("Temperatura inválida.")

        if temp_atual < 0.0 or temp_atual > 100.0:
            msg_erro = (
                f"Temperatura crítica detectada: {temp_atual}°C "
                "(Fora da faixa 0-100°C)"
            )

            novo_log = LogAlerta(
                id_log=None,
                tipo_evento="EMERGENCIA_TEMPERATURA",
                descricao=msg_erro
            )

            try:
                LogRepository.salvar(
                    novo_log,
                    self.experimento_id_db
                )
            except Exception as log_err:
                print(f"Erro ao salvar log no banco: {log_err}")

            self.interromper_emergencia()

    def exportar_excel(self, caminho: str) -> None:
        """Exporta um relatório técnico completo do experimento para Excel."""

        from openpyxl.styles import (
            Font,
            PatternFill,
            Alignment,
            Border,
            Side
        )
        from openpyxl.chart import ScatterChart, Reference, Series

        # ---------------------------------------------------------
        # 1. RECUPERAÇÃO DOS DADOS
        # ---------------------------------------------------------

        if not self.experimento_id_db:
            raise ValueError("Nenhum experimento carregado para exportação.")

        exp_info, param_info, pontos_db = (
            ExperimentoRepository.carregar_experimento_completo(
                self.experimento_id_db
            )
        )

        if not exp_info:
            raise ValueError("Experimento não encontrado no banco.")

        pontos_db = pontos_db or []

        # Dados gerais
        informacoes = [
            ("ID do experimento", self.experimento_id_db),
            ("Nome do experimento", exp_info[0]),
            ("Tipo de reação", exp_info[1]),
            ("Data de realização", exp_info[14] or "Não informada"),
            ("Professor", exp_info[3] or "Não informado"),
            ("Turma", exp_info[4] or "Não informada"),
            ("Substância", exp_info[5] or "Não informada"),
            ("Fórmula química", exp_info[6] or "Não informada"),
            ("Massa molar", exp_info[7]),
            ("Entalpia de formação", exp_info[8]),
        ]

        if param_info:
            informacoes.extend([
                ("Temperatura inicial (°C)", param_info[1]),
                ("Massa inicial do reagente", param_info[2]),
                ("Massa total", param_info[3]),
            ])

        descricao = exp_info[2] or "Nenhuma descrição informada."

        # Dados de telemetria
        df_telemetria = pd.DataFrame(
            [(p[1], p[2], p[3]) for p in pontos_db],
            columns=[
                "Tempo (s)",
                "Temperatura real (°C)",
                "Temperatura simulada (°C)"
            ]
        )

        # ---------------------------------------------------------
        # 2. CÁLCULO DOS INDICADORES
        # ---------------------------------------------------------

        def numero_valido(valor):
            return (
                    isinstance(valor, (int, float))
                    and not isinstance(valor, bool)
                    and math.isfinite(valor)
            )

        temperaturas_reais = [
            p[2] for p in pontos_db
            if numero_valido(p[2])
        ]

        temperaturas_simuladas = [
            p[3] for p in pontos_db
            if numero_valido(p[3])
        ]

        pares_validos = [
            (p[2], p[3]) for p in pontos_db
            if numero_valido(p[2]) and numero_valido(p[3])
        ]

        if pares_validos:
            erros = [
                abs(real - simulada)
                for real, simulada in pares_validos
            ]

            erro_medio = sum(erros) / len(erros)
            erro_maximo = max(erros)

            diferenca_final = (
                    pares_validos[-1][0] - pares_validos[-1][1]
            )

            diferenca_final_absoluta = abs(diferenca_final)
        else:
            erro_medio = None
            erro_maximo = None
            diferenca_final = None
            diferenca_final_absoluta = None

        ultima_leitura = pontos_db[-1] if pontos_db else None

        temperatura_final_real = (
            ultima_leitura[2]
            if ultima_leitura and numero_valido(ultima_leitura[2])
            else None
        )

        temperatura_final_simulada = (
            ultima_leitura[3]
            if ultima_leitura and numero_valido(ultima_leitura[3])
            else None
        )

        indicadores_telemetria = [
            ("Quantidade de registros", len(pontos_db)),
            (
                "Temperatura real máxima (°C)",
                max(temperaturas_reais) if temperaturas_reais else None
            ),
            (
                "Temperatura real mínima (°C)",
                min(temperaturas_reais) if temperaturas_reais else None
            ),
            ("Temperatura final real (°C)", temperatura_final_real),
            ("Temperatura final simulada (°C)", temperatura_final_simulada),
        ]

        indicadores_analise = [
            ("Registros comparados", len(pares_validos)),
            ("Temperatura final real (°C)", temperatura_final_real),
            ("Temperatura final simulada (°C)", temperatura_final_simulada),
            ("Diferença final (real - simulada) (°C)", diferenca_final),
            ("Diferença final absoluta (°C)", diferenca_final_absoluta),
            ("Erro médio absoluto (°C)", erro_medio),
            ("Erro máximo absoluto (°C)", erro_maximo),
        ]

        # ---------------------------------------------------------
        # 3. ESTILOS
        # ---------------------------------------------------------

        azul_escuro = "1F4E78"
        azul_claro = "D9EAF7"
        azul_muito_claro = "F2F6FA"
        branco = "FFFFFF"
        cinza = "F2F2F2"
        texto = "333333"

        borda_fina = Border(
            bottom=Side(style="thin", color="D9E1F2")
        )

        borda_completa = Border(
            left=Side(style="thin", color="D9E1F2"),
            right=Side(style="thin", color="D9E1F2"),
            top=Side(style="thin", color="D9E1F2"),
            bottom=Side(style="thin", color="D9E1F2")
        )

        def formatar_titulo(ws, intervalo, titulo):
            ws.merge_cells(intervalo)
            celula = ws[intervalo.split(":")[0]]
            celula.value = titulo
            celula.font = Font(
                name="Arial",
                bold=True,
                size=16,
                color=branco
            )
            celula.fill = PatternFill("solid", fgColor=azul_escuro)
            celula.alignment = Alignment(
                horizontal="center",
                vertical="center"
            )
            ws.row_dimensions[1].height = 34

        def formatar_cabecalho(ws, linha, colunas):
            for coluna in range(1, colunas + 1):
                celula = ws.cell(row=linha, column=coluna)
                celula.font = Font(
                    name="Arial",
                    bold=True,
                    color=branco,
                    size=10
                )
                celula.fill = PatternFill(
                    "solid",
                    fgColor=azul_escuro
                )
                celula.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True
                )

        def formatar_tabela(ws, linha_inicial, quantidade, colunas):
            for linha in range(linha_inicial, linha_inicial + quantidade):
                ws.row_dimensions[linha].height = 22

                for coluna in range(1, colunas + 1):
                    celula = ws.cell(row=linha, column=coluna)

                    celula.font = Font(
                        name="Arial",
                        size=10,
                        color=texto
                    )

                    celula.fill = PatternFill(
                        "solid",
                        fgColor=branco if linha % 2 == 0 else cinza
                    )

                    celula.alignment = Alignment(
                        horizontal="left" if coluna == 1 else "center",
                        vertical="center",
                        wrap_text=True
                    )

                    celula.border = borda_fina

        # ---------------------------------------------------------
        # 4. CRIAÇÃO DAS ABAS
        # ---------------------------------------------------------

        with pd.ExcelWriter(caminho, engine="openpyxl") as writer:

            # Aba 1: Informações Gerais
            pd.DataFrame(
                informacoes,
                columns=["INFORMAÇÃO", "VALOR"]
            ).to_excel(
                writer,
                sheet_name="Informações Gerais",
                index=False,
                startrow=2
            )

            # Aba 2: Telemetria
            df_telemetria.to_excel(
                writer,
                sheet_name="Telemetria",
                index=False,
                startrow=2
            )

            # Aba 3: Análise dos Resultados
            pd.DataFrame(
                indicadores_analise,
                columns=["INDICADOR", "RESULTADO"]
            ).to_excel(
                writer,
                sheet_name="Análise dos Resultados",
                index=False,
                startrow=2
            )

            ws_geral = writer.sheets["Informações Gerais"]
            ws_telemetria = writer.sheets["Telemetria"]
            ws_analise = writer.sheets["Análise dos Resultados"]

            # =====================================================
            # ABA 1 - INFORMAÇÕES GERAIS
            # =====================================================

            formatar_titulo(
                ws_geral,
                "A1:B1",
                "RELATÓRIO DO EXPERIMENTO"
            )

            formatar_cabecalho(ws_geral, 3, 2)
            formatar_tabela(ws_geral, 4, len(informacoes), 2)

            # Destaque para os rótulos
            for linha in range(4, 4 + len(informacoes)):
                celula = ws_geral.cell(row=linha, column=1)
                celula.font = Font(
                    name="Arial",
                    bold=True,
                    size=10,
                    color=azul_escuro
                )
                celula.fill = PatternFill(
                    "solid",
                    fgColor=azul_claro
                )
                celula.alignment = Alignment(
                    horizontal="left",
                    vertical="center",
                    indent=1
                )

            ws_geral.column_dimensions["A"].width = 34
            ws_geral.column_dimensions["B"].width = 55
            ws_geral.freeze_panes = "A4"

            # Campo separado para descrição
            linha_descricao = 4 + len(informacoes) + 1

            ws_geral.merge_cells(
                start_row=linha_descricao,
                start_column=1,
                end_row=linha_descricao,
                end_column=2
            )

            celula_titulo = ws_geral.cell(
                row=linha_descricao,
                column=1
            )

            celula_titulo.value = "DESCRIÇÃO DO EXPERIMENTO"
            celula_titulo.font = Font(
                name="Arial",
                bold=True,
                size=11,
                color=branco
            )
            celula_titulo.fill = PatternFill(
                "solid",
                fgColor=azul_escuro
            )
            celula_titulo.alignment = Alignment(
                horizontal="left",
                vertical="center",
                indent=1
            )

            ws_geral.row_dimensions[linha_descricao].height = 25

            linha_campo = linha_descricao + 1
            ultima_linha_campo = linha_campo + 4

            ws_geral.merge_cells(
                start_row=linha_campo,
                start_column=1,
                end_row=ultima_linha_campo,
                end_column=2
            )

            celula_descricao = ws_geral.cell(
                row=linha_campo,
                column=1
            )

            celula_descricao.value = descricao
            celula_descricao.font = Font(
                name="Arial",
                size=11,
                color=texto
            )
            celula_descricao.fill = PatternFill(
                "solid",
                fgColor=azul_muito_claro
            )
            celula_descricao.alignment = Alignment(
                horizontal="left",
                vertical="top",
                wrap_text=True,
                indent=1
            )
            celula_descricao.border = borda_completa

            for linha in range(linha_campo, ultima_linha_campo + 1):
                ws_geral.row_dimensions[linha].height = 25

            # =====================================================
            # ABA 2 - TELEMETRIA
            # =====================================================

            formatar_titulo(
                ws_telemetria,
                "A1:C1",
                "REGISTROS DE TELEMETRIA"
            )

            formatar_cabecalho(ws_telemetria, 3, 3)
            formatar_tabela(
                ws_telemetria,
                4,
                len(df_telemetria),
                3
            )

            ws_telemetria.column_dimensions["A"].width = 18
            ws_telemetria.column_dimensions["B"].width = 28
            ws_telemetria.column_dimensions["C"].width = 32
            ws_telemetria.freeze_panes = "A4"

            # Indicadores resumidos da telemetria
            ws_telemetria["E2"] = "RESUMO DA TELEMETRIA"
            ws_telemetria["E2"].font = Font(
                name="Arial",
                bold=True,
                color=branco,
                size=11
            )
            ws_telemetria["E2"].fill = PatternFill(
                "solid",
                fgColor=azul_escuro
            )

            ws_telemetria.merge_cells("E2:F2")

            for indice, (nome, valor) in enumerate(
                    indicadores_telemetria,
                    start=3
            ):
                ws_telemetria.cell(indice, 5, nome)
                ws_telemetria.cell(
                    indice,
                    6,
                    valor if valor is not None else "Sem dados"
                )

                ws_telemetria.cell(indice, 5).font = Font(
                    name="Arial",
                    bold=True,
                    color=azul_escuro,
                    size=10
                )
                ws_telemetria.cell(indice, 5).fill = PatternFill(
                    "solid",
                    fgColor=azul_claro
                )

                ws_telemetria.cell(indice, 6).font = Font(
                    name="Arial",
                    color=texto,
                    size=10
                )
                ws_telemetria.cell(indice, 6).fill = PatternFill(
                    "solid",
                    fgColor=branco if indice % 2 else cinza
                )

                for coluna in (5, 6):
                    ws_telemetria.cell(indice, coluna).alignment = Alignment(
                        horizontal="left",
                        vertical="center",
                        wrap_text=True
                    )
                    ws_telemetria.cell(indice, coluna).border = borda_fina

            ws_telemetria.column_dimensions["E"].width = 34
            ws_telemetria.column_dimensions["F"].width = 20

            # Gráfico de temperatura
            if not df_telemetria.empty:
                grafico = ScatterChart()
                grafico.title = "Variação de Temperatura"
                grafico.style = 13
                grafico.x_axis.title = "Tempo (s)"
                grafico.y_axis.title = "Temperatura (°C)"
                grafico.height = 12
                grafico.width = 22
                grafico.scatterStyle = "lineMarker"
                grafico.legend = None

                tempos = Reference(
                    ws_telemetria,
                    min_col=1,
                    min_row=4,
                    max_row=3 + len(df_telemetria)
                )

                # Série real
                valores_reais = Reference(
                    ws_telemetria,
                    min_col=2,
                    min_row=4,
                    max_row=3 + len(df_telemetria)
                )

                serie_real = Series(
                    valores_reais,
                    tempos,
                    title="Temperatura real"
                )

                serie_real.graphicalProperties.line.solidFill = "0070C0"
                serie_real.graphicalProperties.line.width = 28575
                serie_real.marker.symbol = "circle"
                serie_real.marker.size = 5
                serie_real.marker.graphicalProperties.solidFill = "0070C0"
                serie_real.marker.graphicalProperties.line.solidFill = "0070C0"

                # Série simulada
                valores_simulados = Reference(
                    ws_telemetria,
                    min_col=3,
                    min_row=4,
                    max_row=3 + len(df_telemetria)
                )

                serie_simulada = Series(
                    valores_simulados,
                    tempos,
                    title="Temperatura simulada"
                )

                serie_simulada.graphicalProperties.line.solidFill = "ED7D31"
                serie_simulada.graphicalProperties.line.width = 28575
                serie_simulada.marker.symbol = "circle"
                serie_simulada.marker.size = 5
                serie_simulada.marker.graphicalProperties.solidFill = "ED7D31"
                serie_simulada.marker.graphicalProperties.line.solidFill = "ED7D31"

                grafico.series.append(serie_real)
                grafico.series.append(serie_simulada)

                # Legenda externa personalizada
                ws_telemetria["E10"] = "● Temperatura real"
                ws_telemetria["E10"].font = Font(
                    name="Arial",
                    bold=True,
                    color="0070C0",
                    size=11
                )

                ws_telemetria["H10"] = "● Temperatura simulada"
                ws_telemetria["H10"].font = Font(
                    name="Arial",
                    bold=True,
                    color="ED7D31",
                    size=11
                )

                ws_telemetria.add_chart(grafico, "E12")

            # =====================================================
            # ABA 3 - ANÁLISE DOS RESULTADOS
            # =====================================================

            formatar_titulo(
                ws_analise,
                "A1:B1",
                "ANÁLISE DOS RESULTADOS"
            )

            formatar_cabecalho(ws_analise, 3, 2)
            formatar_tabela(
                ws_analise,
                4,
                len(indicadores_analise),
                2
            )

            # Destaque para os indicadores
            for linha in range(4, 4 + len(indicadores_analise)):
                celula = ws_analise.cell(row=linha, column=1)
                celula.font = Font(
                    name="Arial",
                    bold=True,
                    size=10,
                    color=azul_escuro
                )
                celula.fill = PatternFill(
                    "solid",
                    fgColor=azul_claro
                )
                celula.alignment = Alignment(
                    horizontal="left",
                    vertical="center",
                    indent=1,
                    wrap_text=True
                )

            ws_analise.column_dimensions["A"].width = 45
            ws_analise.column_dimensions["B"].width = 30
            ws_analise.freeze_panes = "A4"

            # Nota explicativa
            linha_nota = 4 + len(indicadores_analise) + 2

            ws_analise.merge_cells(
                start_row=linha_nota,
                start_column=1,
                end_row=linha_nota + 2,
                end_column=2
            )

            nota = ws_analise.cell(linha_nota, 1)

            nota.value = (
                "NOTA: O erro médio absoluto representa a média das "
                "diferenças absolutas entre as temperaturas reais e "
                "simuladas em cada registro correspondente. O erro "
                "máximo absoluto representa a maior dessas diferenças. "
                "Valores menores indicam maior proximidade entre as curvas."
            )

            nota.font = Font(
                name="Arial",
                size=10,
                italic=True,
                color=texto
            )
            nota.fill = PatternFill(
                "solid",
                fgColor=azul_muito_claro
            )
            nota.alignment = Alignment(
                horizontal="left",
                vertical="center",
                wrap_text=True,
                indent=1
            )
            nota.border = borda_completa

            for linha in range(linha_nota, linha_nota + 3):
                ws_analise.row_dimensions[linha].height = 25

    def novo_experimento(self) -> None:
        """Reinicializa completamente o experimento atual."""

        if self.experimento.conexao_serial.conexao_ativa:
            self.experimento.conexao_serial.desconectar()

        self.experimento = Experimento()
        self.experimento_id_db = None
        self.executando = False