
import sqlite3
from models.database import conectar_bd


class LogRepository:

    @staticmethod
    def salvar(log, experimento_id: int) -> bool:
        """Insere um alerta associado ao experimento correspondente."""
        try:
            with conectar_bd() as conexao:
                cursor = conexao.cursor()

                cursor.execute("""
                    INSERT INTO LogAlerta (
                        experimento_id,
                        tipo_evento,
                        descricao,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    experimento_id,
                    log.tipo_evento,
                    log.descricao,
                    log.timestamp
                ))

                conexao.commit()

            return True

        except sqlite3.Error as e:
            print(f"Erro ao salvar log no banco: {e}")
            return False

    @staticmethod
    def listar_todos() -> list:
        """Retorna todos os alertas registrados."""
        try:
            with conectar_bd() as conexao:
                cursor = conexao.cursor()

                cursor.execute("""
                    SELECT
                        id,
                        experimento_id,
                        tipo_evento,
                        descricao,
                        timestamp
                    FROM LogAlerta
                    ORDER BY id DESC
                """)

                return cursor.fetchall()

        except sqlite3.Error as e:
            print(f"Erro ao buscar logs: {e}")
            return []

    @staticmethod
    def listar_por_experimento(experimento_id: int) -> list:
        """Retorna os alertas de um experimento específico."""
        try:
            with conectar_bd() as conexao:
                cursor = conexao.cursor()

                cursor.execute("""
                    SELECT id, tipo_evento, descricao, timestamp
                    FROM LogAlerta
                    WHERE experimento_id = ?
                    ORDER BY id DESC
                """, (experimento_id,))

                return cursor.fetchall()

        except sqlite3.Error as e:
            print(f"Erro ao buscar alertas do experimento: {e}")
            return []
