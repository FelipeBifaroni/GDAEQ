import sqlite3
from models.database import conectar_bd



class ExperimentoRepository:

    @staticmethod
    def salvar_experimento_inicial(nome, tipo_reacao, turma_id, professor_id, descricao=None):
        """
        Insere o registo principal do experimento e retorna o ID gerado.
        """
        sql = """
              INSERT INTO Experimento (nome, tipo_reacao, turma_id, professor_id, descricao)
              VALUES (?, ?, ?, ?, ?); \
              """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql, (nome, tipo_reacao, turma_id, professor_id, descricao))
            conexao.commit()
            return cursor.lastrowid

    @staticmethod
    def salvar_parametros(experimento_id, temp_inicial, massa_inicial_a, massa_total):
        """
        Grava as condições e parâmetros iniciais de simulação.
        """
        sql = """
              INSERT INTO Parametro_Simulacao (experimento_id, temp_inicial, massa_inicial_a, massa_total)
              VALUES (?, ?, ?, ?); \
              """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql, (experimento_id, temp_inicial, massa_inicial_a, massa_total))
            conexao.commit()

    @staticmethod
    def salvar_dado_telemetria(experimento_id, tempo, temp_real, temp_simulada):
        """
        Insere ponto a ponto a leitura contínua (massa de dados/série temporal).
        Gera exceção caso a Trigger de segurança (0°C - 100°C) seja acionada.
        """
        sql = """
              INSERT INTO Dado_Grafico (experimento_id, tempo, temp_real, temp_simulada)
              VALUES (?, ?, ?, ?); \
              """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql, (experimento_id, tempo, temp_real, temp_simulada))
            conexao.commit()

    @staticmethod
    def salvar_experimento_substancia(experimento_id, substancia_id, papel="Reagente", coeficiente=1):
        """
        Insere a associação entre o experimento e a substância escolhida.
        """
        sql = """
              INSERT INTO Experimento_Substancia (experimento_id, substancia_id, papel, coeficiente_estequiometrico)
              VALUES (?, ?, ?, ?); \
              """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql, (experimento_id, substancia_id, papel, coeficiente))
            conexao.commit()

    @staticmethod
    def obter_ou_criar_substancia(nome, formula, estado_fisico, massa_molar, entalpia):
        """Busca a substância pelo nome ou insere-a se não existir, retornando o ID."""
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            # Tenta encontrar pelo nome
            cursor.execute("SELECT id FROM Substancia WHERE nome = ?;", (nome,))
            resultado = cursor.fetchone()

            if resultado:
                return resultado[0]

            # Se não existe, insere
            sql = """
                  INSERT INTO Substancia (nome, formula, estado_fisico, massa_molar, entalpia_formacao)
                  VALUES (?, ?, ?, ?, ?); \
                  """
            cursor.execute(sql, (nome, formula, estado_fisico, massa_molar, entalpia))
            conexao.commit()
            return cursor.lastrowid

    @staticmethod
    def obter_ou_criar_professor(nome):
        """Busca o professor pelo nome ou insere-o se não existir, retornando o ID."""
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute("SELECT id FROM Professor WHERE nome = ?;", (nome,))
            resultado = cursor.fetchone()
            if resultado:
                return resultado[0]

            cursor.execute("INSERT INTO Professor (nome) VALUES (?);", (nome,))
            conexao.commit()
            return cursor.lastrowid

    @staticmethod
    def obter_ou_criar_turma(nome):
        """Busca a turma pelo nome ou insere-a se não existir, retornando o ID."""
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute("SELECT id FROM Turma WHERE nome = ?;", (nome,))
            resultado = cursor.fetchone()
            if resultado:
                return resultado[0]

            cursor.execute("INSERT INTO Turma (nome) VALUES (?);", (nome,))
            conexao.commit()
            return cursor.lastrowid

    @staticmethod
    def descartar_experimento_emergencia(experimento_id):
        """
        Em caso de Parada de Emergência, apaga o experimento e os dados do gráfico.
        """
        sql = "DELETE FROM Experimento WHERE id = ?;"
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql, (experimento_id,))
            conexao.commit()

    @staticmethod
    def buscar_dados_para_exportacao(experimento_id):
        """
        Consulta os dados acumulados de telemetria para gerar o ficheiro Excel.
        """
        sql = """
              SELECT tempo, temp_real, temp_simulada
              FROM Dado_Grafico
              WHERE experimento_id = ?
              ORDER BY tempo ASC; \
              """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql, (experimento_id,))
            return cursor.fetchall()

    @staticmethod
    def carregar_experimento_completo(experimento_id):
        """Carrega os dados gerais, parâmetros, substância e a telemetria completa de um experimento do banco."""
        with conectar_bd() as conexao:
            cursor = conexao.cursor()

            # 1. Dados do Cabeçalho, Professor, Turma e Substância associada
            cursor.execute("""
                           SELECT e.nome,
                                  e.tipo_reacao,
                                  e.descricao,
                                  p.nome,
                                  t.nome,
                                  s.nome,
                                  s.formula,
                                  s.massa_molar,
                                  s.entalpia_formacao,
                                  es.coeficiente_estequiometrico
                           FROM Experimento e
                                    LEFT JOIN Professor p ON e.professor_id = p.id
                                    LEFT JOIN Turma t ON e.turma_id = t.id
                                    LEFT JOIN Experimento_Substancia es ON e.id = es.experimento_id
                                    LEFT JOIN Substancia s ON es.substancia_id = s.id
                           WHERE e.id = ?;
                           """, (experimento_id,))
            exp_info = cursor.fetchone()

            # 2. Parâmetros de Simulação
            cursor.execute("""
                           SELECT temp_inicial, massa_inicial_a, massa_total
                           FROM Parametro_Simulacao
                           WHERE experimento_id = ?;
                           """, (experimento_id,))
            param_info = cursor.fetchone()

            # 3. Pontos de Telemetria (Gráfico)
            cursor.execute("""
                           SELECT tempo, temp_real, temp_simulada
                           FROM Dado_Grafico
                           WHERE experimento_id = ?
                           ORDER BY tempo ASC;
                           """, (experimento_id,))
            pontos = cursor.fetchall()

        return exp_info, param_info, pontos

    @staticmethod
    def existe_experimento_igual(
            nome,
            professor_id,
            turma_id,
            descricao
    ):
        sql = """
              SELECT id
              FROM Experimento
              WHERE nome = ?
                AND professor_id = ?
                AND turma_id = ?
                AND descricao = ? LIMIT 1; \
              """

        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                sql,
                (nome, professor_id, turma_id, descricao)
            )

            return cursor.fetchone() is not None