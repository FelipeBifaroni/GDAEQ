import random
import time
from datetime import datetime


class Professor:
    def __init__(self, id_prof: int, nome: str, email: str):
        self.id = id_prof
        self.nome = nome
        self.email = email


class Turma:
    def __init__(self, id_turma: int, nome: str):
        self.id = id_turma
        self.nome = nome


class Substancia:
    def __init__(self, id_subst: int, nome: str, formula: str, estado_fisico: str,
                 massa_molar: float, entalpia_formacao: float):
        self.id = id_subst
        self.nome = nome
        self.formula = formula
        self.estado_fisico = estado_fisico
        self.massa_molar = massa_molar
        self.entalpia_formacao = entalpia_formacao


class ExperimentoSubstancia:
    def __init__(self, id_exp_subst: int, coeficiente_estequiometrico: int, substancia: Substancia):
        self.id = id_exp_subst
        self.coeficiente_estequiometrico = coeficiente_estequiometrico
        self.substancia = substancia


class ParametroSimulacao:
    def __init__(self, id_param: int, temp_inicial: float, massa_inicial_a: float, volume_reator: float):
        self.id = id_param
        self.temp_inicial = temp_inicial
        self.massa_inicial_a = massa_inicial_a
        self.volume_reator = volume_reator


class GemeoDigital:
    def __init__(self):
        self.tempo_atual: float = 0.0
        self.temp_simulada_atual: float = 25.0

    def calcular_proximo_passo(self, dt: float, delta_t_teorico: float) -> float:
        self.tempo_atual += dt
        dT_dt = delta_t_teorico / 20.0
        self.temp_simulada_atual += dT_dt * dt
        return self.temp_simulada_atual


class ConexaoSerial:
    def __init__(self, porta_com: str = "COM3", baud_rate: int = 9600):
        self.porta_com = porta_com
        self.baud_rate = baud_rate
        self.conexao_ativa: bool = False
        self.offset_temperatura: float = 0.0
        self.ganho_temperatura: float = 1.0

    def conectar(self) -> bool:
        self.conexao_ativa = True
        return self.conexao_ativa

    def desconectar(self) -> None:
        self.conexao_ativa = False

    def ler_dados_temp(self, temp_base: float) -> float:
        leitura_bruta = temp_base + random.uniform(-0.2, 0.2)
        return (leitura_bruta * self.ganho_temperatura) + self.offset_temperatura

    def executar_tara(self) -> None:
        self.offset_temperatura = 0.0


class DadoGrafico:
    def __init__(self, id_dado: int, tempo: float, temp_real: float, temp_simulada: float):
        self.id = id_dado
        self.tempo = tempo
        self.temp_real = temp_real
        self.temp_simulada = temp_simulada


class LogAlerta:
    def __init__(self, id_log: int, tipo_evento: str, descricao: str):
        self.id = id_log
        self.tipo_evento = tipo_evento
        self.descricao = descricao
        self.timestamp = datetime.now().strftime("%H:%M:%S")


class Experimento:
    def __init__(self, id_exp: int = 1, nome: str = "Ensaio Calorimétrico", tipo_reacao: str = "Dissolução",
                 descricao: str = ""):
        self.id = id_exp
        self.nome = nome
        self.tipo_reacao = tipo_reacao
        self.data_realizacao = datetime.now()
        self.status = "Inativo"
        self.descricao = descricao

        self.professor = None
        self.turma = None
        self.parametro_simulacao = None
        self.experimento_substancia = None
        self.gemeo_digital = GemeoDigital()
        self.conexao_serial = ConexaoSerial()
        self.dados_grafico = []
        self.logs_alerta = []

        self.tempo_decorrido = 0
        self.delta_t_calculado = 0.0

    def calcular_calorimetria(self) -> float:
        massa_g = self.parametro_simulacao.massa_inicial_a
        massa_molar = self.experimento_substancia.substancia.massa_molar
        entalpia_kj_mol = self.experimento_substancia.substancia.entalpia_formacao
        volume_ml = self.parametro_simulacao.volume_reator

        n_mols = massa_g / massa_molar
        q_joules = (n_mols * abs(entalpia_kj_mol)) * 1000.0
        delta_t = q_joules / (volume_ml * 4.184)
        self.delta_t_calculado = -delta_t if entalpia_kj_mol > 0 else delta_t
        return self.delta_t_calculado

    def iniciar_ensaio(self) -> None:
        # 1. Calcula a calorimetria primeiro (se der erro/divisão por zero, para aqui!)
        self.calcular_calorimetria()

        # 2. Só altera o status e limpa se o cálculo acima funcionar
        self.status = "Reagindo"
        self.tempo_decorrido = 0
        self.dados_grafico.clear()
        self.gemeo_digital.tempo_atual = 0.0
        self.gemeo_digital.temp_simulada_atual = self.parametro_simulacao.temp_inicial
        self.conexao_serial.conectar()

    def pausar_ensaio(self) -> None:
        if self.status == "Reagindo":
            self.status = "Pausado"
        elif self.status == "Pausado":
            self.status = "Reagindo"

    def finalizar_ensaio(self) -> None:
        self.status = "Finalizado"

    def interromper_emergencia(self) -> None:
        self.status = "Emergência"
        alerta = LogAlerta(len(self.logs_alerta) + 1, "EMERGÊNCIA", "Parada de emergência acionada pelo operador.")
        self.logs_alerta.append(alerta)

    def proximo_ponto(self) -> dict | None:
        if self.status != "Reagindo":
            return None

        self.tempo_decorrido += 1
        delta_t_passo = self.delta_t_calculado if self.tempo_decorrido <= 20 else 0.0
        base_temp = self.parametro_simulacao.temp_inicial + (
                    (self.delta_t_calculado / 20.0) * min(self.tempo_decorrido, 20))

        temp_fisica = self.conexao_serial.ler_dados_temp(base_temp)
        temp_modelo = self.gemeo_digital.calcular_proximo_passo(dt=1.0, delta_t_teorico=delta_t_passo)

        dado = DadoGrafico(len(self.dados_grafico) + 1, float(self.tempo_decorrido), temp_fisica, temp_modelo)
        self.dados_grafico.append(dado)

        if temp_fisica > 80.0:
            alerta = LogAlerta(len(self.logs_alerta) + 1, "ALERTA_TEMP", "Temperatura acima de 80°C")
            self.logs_alerta.append(alerta)

        if self.tempo_decorrido >= 40:
            self.finalizar_ensaio()

        return {
            "tempo": float(self.tempo_decorrido),
            "temp_real": temp_fisica,
            "temp_simulada": temp_modelo,
            "status": self.status,
            "dado_obj": dado
        }