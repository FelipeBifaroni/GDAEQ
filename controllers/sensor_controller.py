
class SensorController:
    def __init__(self, experimento_controller):
        self.experimento_controller = experimento_controller

    @property
    def conexao_serial(self):
        return self.experimento_controller.experimento.conexao_serial

    def calibrar_sensores(self, porta_com: str = None) -> float:
        """Realiza a conexão, tara e leitura inicial do sensor."""
        try:
            if porta_com:
                self.conexao_serial.porta_com = porta_com

            sucesso = self.conexao_serial.conectar()

            if not sucesso:
                raise ConnectionError(
                    "Não foi possível conectar ao Arduino."
                )

            self.conexao_serial.executar_tara()

            temperatura = float(
                self.conexao_serial.ler_dados_temp()
            )

            # Armazena a temperatura inicial no experimento
            self.experimento_controller.experimento.temperatura_inicial_sensor = temperatura

            return temperatura

        except Exception as e:
            print(f"Erro ao calibrar sensores: {e}")
            raise
