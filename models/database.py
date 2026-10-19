import sqlite3
import os
from pathlib import Path

# Cria uma pasta oculta segura no perfil do utilizador (ex: C:\Users\NomeDoUsuario\.gdaeq)
DIRETORIO_USUARIO = Path.home() / ".gdaeq"
DIRETORIO_USUARIO.mkdir(parents=True, exist_ok=True)

# Define o caminho completo e seguro para o banco de dados
DB_FILE = str(DIRETORIO_USUARIO / "GDAEQ.db")

def conectar_bd():
    """
    Retorna uma nova conexão ativa com o SQLite,
    garantindo obrigatoriamente que as chaves estrangeiras estejam ativadas.
    """
    conexao = sqlite3.connect(DB_FILE)
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao