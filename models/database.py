import sqlite3

DB_FILE = "GDAEQ.db"

def conectar_bd():
    """
    Retorna uma nova conexão ativa com o SQLite,
    garantindo obrigatoriamente que as chaves estrangeiras estejam ativadas.
    """
    conexao = sqlite3.connect(DB_FILE)
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao