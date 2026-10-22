import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# Cria uma pasta oculta segura no perfil do utilizador (ex: C:\Users\NomeDoUsuario\.gdaeq)
DIRETORIO_USUARIO = Path.home() / ".gdaeq"
DIRETORIO_USUARIO.mkdir(parents=True, exist_ok=True)

# Define o caminho completo e seguro para o banco de dados
DB_FILE = str(DIRETORIO_USUARIO / "GDAEQ.db")

@contextmanager
def conectar_bd():
    """
    Abre uma conexão SQLite com chaves estrangeiras ativadas.
    Confirma a transação em caso de sucesso, desfaz em caso de erro
    e sempre fecha a conexão.
    """
    conexao = sqlite3.connect(DB_FILE)

    try:
        conexao.execute("PRAGMA foreign_keys = ON;")
        yield conexao
        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()