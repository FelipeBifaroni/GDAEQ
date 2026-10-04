from models.entidades import ConexaoSerial

class SensorController:
    def __init__(self):
        # Instancia a classe de ConexaoSerial baseada no domínio
        self.conexao_serial = ConexaoSerial()

    def calibrar_sensores(self, porta_com: str = None) -> float:
        """Orquestra a conexão, a tara (calibração) e a leitura inicial do sensor."""
        try:
            if porta_com:
                self.conexao_serial.porta_com = porta_com

            # 1. Conecta caso não esteja ativa
            if not self.conexao_serial.conexao_ativa:
                sucesso = self.conexao_serial.conectar()
                if not sucesso:
                    raise Exception("Não foi possível estabelecer conexão com a porta serial.")

            # 2. Executa a tara (conforme o diagrama de classes)
            self.conexao_serial.executar_tara()

            # 3. Lê os dados de temperatura atuais do sensor integrado
            temp_lida = self.conexao_serial.ler_dados_temp()

            return float(temp_lida)

        except Exception as e:
            print(f"⚠️ Erro ao calibrar sensores no SensorController: {e}")
            return 25.0

    def desconectar_sensor(self) -> None:
        """Encerra a ligação com a porta serial de forma segura."""
        if self.conexao_serial:
            self.conexao_serial.desconectar()