import pandas as pd
from datetime import datetime
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
            id_exp_subst=1,
            coeficiente_estequiometrico=dados_form["coef_estequio"],
            substancia=subst
        )

        self.experimento.parametro_simulacao = ParametroSimulacao(
            id_param=1,
            temp_inicial=dados_form["temp_ini"],
            massa_inicial_a=dados_form["massa_reagente"],
            massa_total=dados_form["massa_total"]
        )

        # Configura a porta COM
        self.experimento.conexao_serial.porta_com = dados_form["porta_com"]

        # Inicia o experimento e estabelece a conexão serial

        try:
            self.experimento.iniciar_ensaio()

            self.experimento_id_db = ExperimentoRepository.salvar_experimento_completo(
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
                coeficiente=(
                    self.experimento.experimento_substancia
                    .coeficiente_estequiometrico
                )
            )

        except Exception:
            self.experimento.conexao_serial.desconectar()
            self.experimento.status = "Inativo"
            self.experimento_id_db = None
            raise

        return self.experimento.delta_t_calculado

    def obter_proximo_ponto(self) -> dict | None:
        ponto = self.experimento.proximo_ponto()

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
                    print(f"⚠️ Alerta da Trigger de Segurança do Banco: {erro_str}")

                    if "fora da faixa operacional" in erro_str or "ABORT" in erro_str:

                        # 1. GRAVA O ALERTA NA TABELA LogAlerta DO BANCO
                        try:
                            from models.domain import LogAlerta
                            from models.log_repository import LogRepository

                            novo_log = LogAlerta(
                                id_log=None,
                                tipo_evento="EMERGENCIA_TEMPERATURA",
                                descricao=f"Temperatura crítica ({ponto['temp_real']}°C) bloqueada pela Trigger."
                            )
                            LogRepository.salvar(novo_log)
                        except Exception as log_err:
                            print(f"❌ Erro ao salvar log no banco: {log_err}")

                        # 2. Executa a rotina de emergência interna
                        self.interromper_emergencia()

                        # 3. Desliga a flag para o loop gráfico parar
                        self.executando = False

                        return {
                            "tempo": self.experimento.tempo_decorrido,
                            "temp_real": 0.0,
                            "temp_simulada": 0.0,
                            "status": "Emergência"
                        }

            if ponto["status"] == "Finalizado":
                self.experimento.conexao_serial.desconectar()

        return ponto

    def pausar_ensaio(self) -> str:
        self.experimento.pausar_ensaio()
        return self.experimento.status

    def interromper_emergencia(self) -> None:
        # 1. Sinaliza para o sistema que a execução parou
        self.executando = False  # Ajuste para a flag que controla o seu loop de telemetria/execução

        # 2. Interrompe a lógica interna do experimento
        self.experimento.interromper_emergencia()

        # 3. Desconecta o hardware físico / serial
        if self.experimento.conexao_serial:
            self.experimento.conexao_serial.desconectar()

        # 4. Remove ou trata o registo corrompido/emergencial no banco de dados
        if self.experimento_id_db:
            try:
                ExperimentoRepository.descartar_experimento_emergencia(self.experimento_id_db)
            except Exception as e:
                print(f"⚠️ Erro ao descartar experimento de emergência no banco: {e}")

    def exportar_excel(self, caminho_arquivo: str) -> None:
        dados_para_tabela = [
            {
                "Tempo (s)": d[0],
                "Temperatura Real (°C)": d[1],
                "Temperatura Gêmeo Digital (°C)": d[2]
            }
            for d in ExperimentoRepository.buscar_dados_para_exportacao(
                self.experimento_id_db
            )
        ]

        df_telemetria = pd.DataFrame(dados_para_tabela)

        with pd.ExcelWriter(caminho_arquivo, engine="openpyxl") as writer:
            info_geral = pd.DataFrame({
                "Parâmetro": [
                    "Nome do Experimento", "Descrição", "Professor", "Turma",
                    "Data/Hora", "Substância", "Fórmula", "Estado Físico",
                    "Massa Reagente (g)", "Volume Reator (mL)",
                    "ΔT Teórico (°C)", "Porta COM"
                ],
                "Valor": [
                    self.experimento.nome,
                    self.experimento.descricao,
                    self.experimento.professor.nome,
                    self.experimento.turma.nome,
                    self.experimento.data_realizacao.strftime(
                        "%d/%m/%Y %H:%M:%S"
                    ) if self.experimento.data_realizacao else datetime.now().strftime(
                        "%d/%m/%Y %H:%M:%S"
                    ),
                    self.experimento.experimento_substancia.substancia.nome,
                    self.experimento.experimento_substancia.substancia.formula,
                    self.experimento.experimento_substancia.substancia.estado_fisico,
                    self.experimento.parametro_simulacao.massa_inicial_a,
                    self.experimento.parametro_simulacao.massa_total,
                    f"{self.experimento.delta_t_calculado:.2f}",
                    self.experimento.conexao_serial.porta_com
                ]
            })

            info_geral.to_excel(
                writer,
                sheet_name="Informações Gerais",
                index=False
            )

            df_telemetria.to_excel(
                writer,
                sheet_name="Dados de Telemetria",
                index=False
            )

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

        if temp_atual < 0.0 or temp_atual > 100.0:
            # 1. Define o texto descritivo do problema
            msg_erro = f"Temperatura crítica detectada: {temp_atual}°C (Fora da faixa 0-100°C)"

            # 2. Cria o objeto usando a sua classe LogAlerta
            novo_log = LogAlerta(
                id_log=None,
                tipo_evento="EMERGENCIA_TEMPERATURA",
                descricao=msg_erro
            )

            # 3. Salva no banco de dados SQLite via repositório
            try:
                LogRepository.salvar(novo_log)
            except Exception as log_err:
                print(f"❌ Erro ao salvar log no banco: {log_err}")

            # 4. Aciona a rotina de interrupção de emergência estruturada no Controller
            self.interromper_emergencia()

        else:
            # Fluxo normal de funcionamento
            pass

    def novo_experimento(self) -> None:
        """Reinicializa completamente o experimento atual."""

        if self.experimento.conexao_serial.conexao_ativa:
            self.experimento.conexao_serial.desconectar()

        self.experimento = Experimento()
        self.experimento_id_db = None
        self.executando = False