import pandas as pd
from datetime import datetime
from models.entidades import Experimento, Professor, Turma, Substancia, ExperimentoSubstancia, ParametroSimulacao

class ExperimentoController:
    def __init__(self):
        self.experimento = Experimento()
        self.historico_banco_memoria = []

    def iniciar_ensaio(self, dados_form: dict) -> float:
        self.experimento.nome = dados_form["nome_exp"]
        self.experimento.descricao = dados_form["descricao"]
        self.experimento.professor = Professor(1, dados_form["professor"], "prof@fatec.br")
        self.experimento.turma = Turma(1, dados_form["turma"])

        subst = Substancia(
            id_subst=1,
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
            volume_reator=dados_form["volume"]
        )
        self.experimento.conexao_serial.porta_com = dados_form["porta_com"]

        self.experimento.iniciar_ensaio()
        return self.experimento.delta_t_calculado

    def obter_proximo_ponto(self) -> dict | None:
        ponto = self.experimento.proximo_ponto()
        if ponto and ponto["status"] == "Finalizado":
            self.registrar_no_historico("Finalizado")
        return ponto

    def pausar_ensaio(self) -> str:
        self.experimento.pausar_ensaio()
        return self.experimento.status

    def interromper_emergencia(self) -> None:
        self.experimento.interromper_emergencia()
        self.registrar_no_historico("Interrompido/Finalizado")

    def calibrar_sensores(self) -> None:
        self.experimento.conexao_serial.executar_tara()

    def registrar_no_historico(self, status: str) -> None:
        self.historico_banco_memoria.append({
            "id": len(self.historico_banco_memoria) + 1,
            "nome": self.experimento.nome,
            "data": self.experimento.data_realizacao.strftime("%d/%m/%Y %H:%M:%S"),
            "professor": self.experimento.professor.nome if self.experimento.professor else "N/A",
            "status": status
        })

    def exportar_excel(self, caminho_arquivo: str) -> None:
        dados_para_tabela = [
            {"Tempo (s)": d.tempo, "Temperatura Real (°C)": d.temp_real, "Temperatura Gêmeo Digital (°C)": d.temp_simulada}
            for d in self.experimento.dados_grafico
        ]
        df_telemetria = pd.DataFrame(dados_para_tabela)

        with pd.ExcelWriter(caminho_arquivo, engine="openpyxl") as writer:
            info_geral = pd.DataFrame({
                "Parâmetro": [
                    "Nome do Experimento", "Descrição", "Professor", "Turma",
                    "Data/Hora", "Substância", "Fórmula", "Estado Físico",
                    "Massa Reagente (g)", "Volume Reator (mL)", "ΔT Teórico (°C)", "Porta COM"
                ],
                "Valor": [
                    self.experimento.nome,
                    self.experimento.descricao,
                    self.experimento.professor.nome,
                    self.experimento.turma.nome,
                    self.experimento.data_realizacao.strftime("%d/%m/%Y %H:%M:%S"),
                    self.experimento.experimento_substancia.substancia.nome,
                    self.experimento.experimento_substancia.substancia.formula,
                    self.experimento.experimento_substancia.substancia.estado_fisico,
                    self.experimento.parametro_simulacao.massa_inicial_a,
                    self.experimento.parametro_simulacao.volume_reator,
                    f"{self.experimento.delta_t_calculado:.2f}",
                    self.experimento.conexao_serial.porta_com
                ]
            })
            info_geral.to_excel(writer, sheet_name="Informações Gerais", index=False)
            df_telemetria.to_excel(writer, sheet_name="Dados de Telemetria", index=False)