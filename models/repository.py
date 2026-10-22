import sqlite3
from models.database import conectar_bd



class ExperimentoRepository:

    @staticmethod
    def salvar_experimento_completo(
            nome,
            tipo_reacao,
            turma_id,
            professor_id,
            descricao,
            temp_inicial,
            massa_inicial_a,
            massa_total,
            substancia_id,
            papel="Reagente",
            coeficiente=1
    ):
        """
        Salva o experimento, seus parâmetros e a associação
        com a substância em uma única transação.
        """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()

            # 1. Salvar o experimento principal
            cursor.execute(
                """
                INSERT INTO Experimento
                    (nome, tipo_reacao, turma_id, professor_id, descricao)
                VALUES (?, ?, ?, ?, ?);
                """,
                (nome, tipo_reacao, turma_id, professor_id, descricao)
            )

            experimento_id = cursor.lastrowid

            # 2. Salvar os parâmetros da simulação
            cursor.execute(
                """
                INSERT INTO Parametro_Simulacao
                    (experimento_id, temp_inicial, massa_inicial_a, massa_total)
                VALUES (?, ?, ?, ?);
                """,
                (experimento_id, temp_inicial, massa_inicial_a, massa_total)
            )

            # 3. Salvar a associação com a substância
            cursor.execute(
                """
                INSERT INTO Experimento_Substancia
                    (experimento_id, substancia_id, papel,
                     coeficiente_estequiometrico)
                VALUES (?, ?, ?, ?);
                """,
                (experimento_id, substancia_id, papel, coeficiente)
            )

            return experimento_id


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
        """Carrega os dados gerais, parâmetros, substância e telemetria de um experimento."""

        with conectar_bd() as conexao:
            cursor = conexao.cursor()

            # 1. Dados do cabeçalho, professor, turma e substância
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
                       es.coeficiente_estequiometrico,
                       e.professor_id,
                       e.turma_id,
                       s.id,
                       es.id
                FROM Experimento e
                LEFT JOIN Professor p ON e.professor_id = p.id
                LEFT JOIN Turma t ON e.turma_id = t.id
                LEFT JOIN Experimento_Substancia es
                    ON e.id = es.experimento_id
                LEFT JOIN Substancia s ON es.substancia_id = s.id
                WHERE e.id = ?;
            """, (experimento_id,))

            exp_info = cursor.fetchone()

            # 2. Parâmetros de simulação
            cursor.execute("""
                SELECT id, temp_inicial, massa_inicial_a, massa_total
                FROM Parametro_Simulacao
                WHERE experimento_id = ?;
            """, (experimento_id,))

            param_info = cursor.fetchone()

            # 3. Pontos de telemetria do gráfico
            cursor.execute("""
                SELECT id, tempo, temp_real, temp_simulada
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

    @staticmethod
    def excluir_experimento_banco(experimento_id: int) -> bool:
        """Remove um experimento e todos os seus dados associados do banco."""
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            try:
                cursor.execute("DELETE FROM Experimento WHERE id = ?;", (experimento_id,))
                conexao.commit()
                return True
            except Exception as e:
                print(f"Erro ao excluir experimento: {e}")
                conexao.rollback()
                return False

    @staticmethod
    def listar_todos():
        """Retorna todos os experimentos para o histórico."""
        sql = """
                  SELECT e.id, e.nome, e.data_realizacao, p.nome, t.nome
                  FROM Experimento e
                  LEFT JOIN Professor p ON e.professor_id = p.id
                  LEFT JOIN Turma t ON e.turma_id = t.id
                  ORDER BY e.id DESC;
                  """
        with conectar_bd() as conexao:
            cursor = conexao.cursor()
            cursor.execute(sql)
            return cursor.fetchall()


    @staticmethod
    def atualizar_cabecalho_experimento(experimento_id: int, nome_exp: str, professor_id: int, turma_id: int,
                                        descricao: str, substancia_id: int):
        """Atualiza a identificação, descrição e a substância associada do registo."""
        sql_experimento = """
                  UPDATE Experimento
                  SET nome         = ?, 
                      professor_id = ?, 
                      turma_id     = ?, 
                      descricao    = ?
                  WHERE id = ?;
                  """

        sql_substancia_relacao = """
                  UPDATE Experimento_Substancia
                  SET substancia_id = ?
                  WHERE experimento_id = ?;
                  """

        with conectar_bd() as conexao:
            cursor = conexao.cursor()

            # 1. Atualiza os dados principais do experimento
            cursor.execute(sql_experimento, (nome_exp, professor_id, turma_id, descricao, experimento_id))

            # 2. Atualiza a associação da substância do experimento
            cursor.execute(sql_substancia_relacao, (substancia_id, experimento_id))

            conexao.commit()
            return True
