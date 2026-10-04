import pandas as pd
from datetime import datetime
from models.entidades import ConexaoSerial, Experimento, Professor, Turma, Substancia, ExperimentoSubstancia, ParametroSimulacao, DadoGrafico
from models.repository import ExperimentoRepository




class ExperimentoController:
    def __init__(self):
        self.experimento = Experimento()
        self.experimento.conexao_serial = ConexaoSerial()
        self.experimento_id_db = None  # Armazena o ID gerado no SQLite

    def iniciar_ensaio(self, dados_form: dict) -> float:
        self.experimento.nome = dados_form["nome_exp"]
        self.experimento.descricao = dados_form.get("descricao", "")

        # 1. Obter ou criar IDs reais para Professor, Turma e Substância
        prof_id_real = ExperimentoRepository.obter_ou_criar_professor(dados_form["professor"])
        turma_id_real = ExperimentoRepository.obter_ou_criar_turma(dados_form["turma"])

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
        self.experimento.conexao_serial.conectar()

        # Inicia o cálculo
        self.experimento.iniciar_ensaio()

        if ExperimentoRepository.existe_experimento_igual(
                nome=self.experimento.nome,
                professor_id=prof_id_real,
                turma_id=turma_id_real,
                descricao=self.experimento.descricao
        ):
            raise ValueError(
                "Já existe um experimento com esses mesmos dados."
            )

        # 2. PERSISTÊNCIA COM OS IDS REAIS
        self.experimento_id_db = ExperimentoRepository.salvar_experimento_inicial(
            nome=self.experimento.nome,
            tipo_reacao=self.experimento.tipo_reacao if hasattr(self.experimento, 'tipo_reacao') else "Exotérmica",
            turma_id=turma_id_real,      # <--- Usa o ID retornado do banco
            professor_id=prof_id_real,  # <--- Usa o ID retornado do banco
            descricao=self.experimento.descricao
        )

        ExperimentoRepository.salvar_parametros(
            experimento_id=self.experimento_id_db,
            temp_inicial=self.experimento.parametro_simulacao.temp_inicial,
            massa_inicial_a=self.experimento.parametro_simulacao.massa_inicial_a,
            massa_total=self.experimento.parametro_simulacao.massa_total
        )

        if self.experimento.experimento_substancia and self.experimento.experimento_substancia.substancia:
            subst_id = self.experimento.experimento_substancia.substancia.id
            coef = self.experimento.experimento_substancia.coeficiente_estequiometrico
            ExperimentoRepository.salvar_experimento_substancia(
                experimento_id=self.experimento_id_db,
                substancia_id=subst_id,
                papel="Reagente",
                coeficiente=coef
            )

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
                    print(f"⚠️ Alerta da Trigger de Segurança do Banco: {e}")

                    if "fora da faixa operacional" in str(e):
                        # 1. Executa a rotina de emergência interna
                        self.interromper_emergencia()

                        # 2. Desliga a flag para o loop gráfico parar
                        self.executando = False

                        # 3. Manda a interface atualizar o texto e a cor para vermelho
                        if hasattr(self, 'view') and self.view:
                            # Se o controller tiver uma referência para a view, chama diretamente
                            self.view.acionar_emergencia_visual()

                        return None

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
        """Busca todos os experimentos salvos no SQLite para exibir no histórico da View."""

        from models.database import conectar_bd

        sql = """
              SELECT e.id, \
                     e.nome, \
                     e.data_realizacao, \
                     p.nome
              FROM Experimento e
                       LEFT JOIN Professor p ON e.professor_id = p.id
              ORDER BY e.id DESC; \
              """

        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql)
            linhas = cursor.fetchall()

        # Formata para o formato que a View espera
        historico = []

        for linha in linhas:
            historico.append({
                "id": linha[0],
                "nome": linha[1],
                "data": linha[2],
                "professor": linha[3] or "N/A"
            })

        return historico

    def carregar_experimento_por_id(self, experimento_id: int):
        """Carrega um experimento gravado do banco para a memória atual do controller."""
        exp_info, param_info, pontos_db = ExperimentoRepository.carregar_experimento_completo(experimento_id)
        print("DADOS BRUTOS DO BANCO:", exp_info)
        if not exp_info:
            return False

        # exp_info: [nome, tipo_reacao, descricao, prof_nome, turma_nome, subst_nome, subst_formula, massa_molar, entalpia, coeficiente]
        self.experimento = Experimento(id_exp=experimento_id, nome=exp_info[0], tipo_reacao=exp_info[1],
                                       descricao=exp_info[2] or "")
        self.experimento.professor = Professor(1, exp_info[3] or "Professor Padrão")
        self.experimento.turma = Turma(1, exp_info[4] or "Turma Padrão")

        # Reconstrói a substância se existir registo associado
        if exp_info[5]:
            subst = Substancia(
                id_subst=1,
                nome=exp_info[5],
                formula=exp_info[6],
                estado_fisico="Líquido",
                massa_molar=exp_info[7],
                entalpia_formacao=exp_info[8]
            )
            self.experimento.experimento_substancia = ExperimentoSubstancia(
                id_exp_subst=1,
                substancia=subst,
                coeficiente_estequiometrico=exp_info[9] if exp_info[9] is not None else 1
            )

        if param_info:
            self.experimento.parametro_simulacao = ParametroSimulacao(
                id_param=1, temp_inicial=param_info[0], massa_inicial_a=param_info[1], massa_total=param_info[2]
            )

        # Reconstrói os pontos do gráfico
        self.experimento.dados_grafico = []
        for p in pontos_db:
            dado = DadoGrafico(id_dado=0, tempo=p[0], temp_real=p[1], temp_simulada=p[2])
            self.experimento.dados_grafico.append(dado)

        self.experimento.status = "Finalizado"
        self.experimento_id_db = experimento_id
        return True