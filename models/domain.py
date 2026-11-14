import math
import serial
import time
from datetime import datetime



class Professor:
    def __init__(self, id_prof: int, nome: str):
        self.id = id_prof
        self.nome = nome


class Turma:
    def __init__(self, id_turma: int, nome: str):
        self.id = id_turma
        self.nome = nome


class Substancia:
    def __init__(
        self,
        id_subst: int,
        nome: str,
        formula: str,
        estado_fisico: str,
        massa_molar: float
    ):
        self.id = id_subst
        self.nome = nome
        self.formula = formula
        self.estado_fisico = estado_fisico
        self.massa_molar = massa_molar



class ExperimentoSubstancia:
    def __init__(
        self,
        id_exp_subst: int | None,
        substancia: Substancia,
        coeficiente_estequiometrico: int = 1
    ):
        self.id = id_exp_subst
        self.substancia = substancia
        self.coeficiente_estequiometrico = coeficiente_estequiometrico




class ParametroSimulacao:
    def __init__(
        self,
        id_param: int | None,
        temp_inicial: float,
        massa_inicial_a: float,
        massa_total: float
    ):
        self.id = id_param
        self.temp_inicial = temp_inicial
        self.massa_inicial_a = massa_inicial_a
        self.massa_total = massa_total




class GemeoDigital:
    def __init__(self):
        self.tempo_atual: float = 0.0
        self.temp_simulada_atual: float = 25.0
        self.duracao_simulacao: int = 120

    def calcular_proximo_passo(self, dt: float, delta_t_teorico: float) -> float:
        self.tempo_atual += dt

        dT_dt = delta_t_teorico / self.duracao_simulacao

        self.temp_simulada_atual += dT_dt * dt

        return self.temp_simulada_atual


class ConexaoSerial:
    def __init__(self, porta_com: str = "COM3", baud_rate: int = 9600):
        self.porta_com = porta_com
        self.baud_rate = baud_rate
        self.conexao_ativa: bool = False
        self.offset_temperatura: float = 0.0
        self.ganho_temperatura: float = 1.0
        self.serial_conn = None

        # Modo temporário de simulação
        self.modo_simulacao = False
        self.temperatura_fixa = 25.0

    def conectar(self) -> bool:
        if self.modo_simulacao:
            self.conexao_ativa = True
            print("Modo de simulação ativado: temperatura fixa.")
            return True

        if (
            self.serial_conn is not None
            and self.serial_conn.is_open
        ):
            self.conexao_ativa = True
            return True

        try:
            self.serial_conn = serial.Serial(
                port=self.porta_com,
                baudrate=self.baud_rate,
                timeout=3
            )

            time.sleep(2)
            self.serial_conn.reset_input_buffer()

            self.conexao_ativa = True
            return True

        except serial.SerialException as erro:
            print(f"Erro ao conectar ao Arduino: {erro}")
            self.serial_conn = None
            self.conexao_ativa = False
            return False

    def desconectar(self) -> None:
        if self.serial_conn is not None:
            if self.serial_conn.is_open:
                self.serial_conn.close()

        self.serial_conn = None
        self.conexao_ativa = False

    def ler_dados_temp(self, temp_base: float = 25.0) -> float:
        if not self.conexao_ativa:
            raise ConnectionError("Conexão não está ativa.")

        # Retorna temperatura fixa no modo de simulação
        if self.modo_simulacao:
            leitura_bruta = self.temperatura_fixa
        else:
            if (
                self.serial_conn is None
                or not self.serial_conn.is_open
            ):
                raise ConnectionError("Arduino não está conectado.")

            try:

                ultima_leitura = None

                try:
                    while self.serial_conn.in_waiting > 0:
                        linha = self.serial_conn.readline().decode(
                            "utf-8", errors="ignore"
                        ).strip()

                        if linha:
                            try:
                                temperatura = float(linha)

                                if temperatura != -127.0 and math.isfinite(temperatura):
                                    ultima_leitura = temperatura

                            except ValueError:
                                continue

                    if ultima_leitura is None:
                        linha = self.serial_conn.readline().decode(
                            "utf-8", errors="ignore"
                        ).strip()

                        if not linha:
                            raise TimeoutError("O Arduino não enviou uma temperatura.")

                        ultima_leitura = float(linha)

                    leitura_bruta = ultima_leitura

                except (serial.SerialException, ValueError) as erro:
                    self.conexao_ativa = False
                    raise ConnectionError(
                        f"Erro na comunicação com o Arduino: {erro}"
                    ) from erro



            except serial.SerialException as erro:
                self.conexao_ativa = False
                raise ConnectionError(
                    f"Erro na comunicação com o Arduino: {erro}"
                ) from erro

            if not linha:
                raise TimeoutError(
                    "O Arduino não enviou uma temperatura."
                )

            try:
                leitura_bruta = float(linha)
            except ValueError as erro:
                raise ValueError(
                    f"Leitura inválida recebida do Arduino: {linha}"
                ) from erro

            if leitura_bruta == -127.0:
                raise ValueError(
                    "Sensor DS18B20 desconectado ou não encontrado."
                )

            if not math.isfinite(leitura_bruta):
                raise ValueError(
                    "Temperatura inválida recebida do Arduino."
                )

        return (
            leitura_bruta * self.ganho_temperatura
        ) + self.offset_temperatura

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
        self.timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")


class Experimento:
    def __init__(
        self,
        id_exp: int = 1,
        nome: str = "Ensaio Calorimétrico",
        tipo_reacao: str = "Dissolução",
        descricao: str = "",
        entalpia_reacao: float = 0.0
    ):
        self.id = id_exp
        self.nome = nome
        self.tipo_reacao = tipo_reacao
        self.data_realizacao = datetime.now()
        self.status = "Inativo"
        self.descricao = descricao
        self.entalpia_reacao = entalpia_reacao


        self.professor = None
        self.turma = None
        self.parametro_simulacao = None
        self.experimento_substancia = None
        self.temperatura_inicial_sensor = None
        self.gemeo_digital = GemeoDigital()
        self.conexao_serial = ConexaoSerial()
        self.dados_grafico = []
        self.logs_alerta = []

        self.tempo_decorrido = 0
        self.delta_t_calculado = 0.0


    def calcular_calorimetria(self) -> float:
        massa_g = self.parametro_simulacao.massa_inicial_a
        massa_molar = self.experimento_substancia.substancia.massa_molar
        entalpia_kj_mol = self.entalpia_reacao
        massa_total = self.parametro_simulacao.massa_total

        # Proteção contra divisão por zero (caso o volume ou massa molar sejam 0)
        if massa_total <= 0 or massa_molar <= 0:
            raise ValueError("A Massa total do reator e a massa molar devem ser maiores que zero.")

        n_mols = massa_g / massa_molar
        q_joules = (n_mols * abs(entalpia_kj_mol)) * 1000.0
        delta_t = q_joules / (massa_total * 4.184)
        self.delta_t_calculado = -delta_t if entalpia_kj_mol > 0 else delta_t
        return self.delta_t_calculado

    def iniciar_ensaio(self, temperatura_inicial_sensor: float) -> None:
        # 1. Calcula a calorimetria
        self.calcular_calorimetria()

        # 2. Verifica a conexão serial
        if not self.conexao_serial.conexao_ativa:
            sucesso = self.conexao_serial.conectar()

            if sucesso is False:
                raise ConnectionError(
                    "Não foi possível estabelecer a conexão serial."
                )

        # 3. Inicializa o experimento
        self.status = "Reagindo"
        self.tempo_decorrido = 0
        self.dados_grafico.clear()

        # 4. Inicializa o Gêmeo Digital com a temperatura do sensor
        self.gemeo_digital.tempo_atual = 0.0
        self.gemeo_digital.temp_simulada_atual = temperatura_inicial_sensor

    def pausar_ensaio(self) -> None:
        if self.status == "Reagindo":
            self.status = "Pausado"
        elif self.status == "Pausado":
            self.status = "Reagindo"

    def finalizar_ensaio(self) -> None:
        self.status = "Finalizado"

    def interromper_emergencia(self, motivo: str = "Parada de emergência acionada pelo operador.") -> None:
        self.status = "Emergência"

        alerta = LogAlerta(
            len(self.logs_alerta) + 1,
            "EMERGÊNCIA",
            motivo
        )

        self.logs_alerta.append(alerta)

    def proximo_ponto(self) -> dict | None:
        # Permite continuar gerando os cálculos e pontos mesmo com o ensaio pausado
        if self.status not in ["Reagindo", "Pausado"]:
            return None

        temp_fisica = self.conexao_serial.ler_dados_temp()
        self.tempo_decorrido += 1
        delta_t_passo = (
            self.delta_t_calculado
            if self.tempo_decorrido <= self.gemeo_digital.duracao_simulacao
            else 0.0
        )

        temp_modelo = self.gemeo_digital.calcular_proximo_passo(
            dt=1.0,
            delta_t_teorico=delta_t_passo
        )

        dado = DadoGrafico(len(self.dados_grafico) + 1, float(self.tempo_decorrido), temp_fisica, temp_modelo)
        self.dados_grafico.append(dado)

        if temp_fisica > 80.0:
            alerta = LogAlerta(len(self.logs_alerta) + 1, "ALERTA_TEMP", "Temperatura acima de 80°C")
            self.logs_alerta.append(alerta)

        if self.tempo_decorrido >= 120:
            self.finalizar_ensaio()

        return {
            "tempo": float(self.tempo_decorrido),
            "temp_real": temp_fisica,
            "temp_simulada": temp_modelo,
            "status": self.status,
            "dado_obj": dado
        }