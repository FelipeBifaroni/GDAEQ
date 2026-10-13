import sqlite3
from models.database import conectar_bd

class LogRepository:
    @staticmethod
    def salvar(log) -> bool:
        """Insere o objeto LogAlerta na tabela LogAlerta do banco."""
        try:
            with conectar_bd() as conexao:
                cursor = conexao.cursor()
                cursor.execute("""
                    INSERT INTO LogAlerta (tipo_evento, descricao, timestamp)
                    VALUES (?, ?, ?)
                """, (log.tipo_evento, log.descricao, log.timestamp))
                conexao.commit()
            return True
        except sqlite3.Error as e:
            print(f"❌ Erro ao salvar log no banco: {e}")
            return False

    @staticmethod
    def listar_todos() -> list:
        """Retorna todos os logs de alerta salvos no banco de dados."""
        try:
            with conectar_bd() as conexao:
                cursor = conexao.cursor()
                cursor.execute("SELECT id, tipo_evento, descricao, timestamp FROM LogAlerta ORDER BY id DESC")
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"❌ Erro ao buscar logs: {e}")
            return []