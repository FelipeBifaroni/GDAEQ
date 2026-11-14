
import sqlite3
import os
import tempfile
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime


# Diretório do usuário
DIRETORIO_USUARIO = Path.home() / ".gdaeq"
DIRETORIO_USUARIO.mkdir(parents=True, exist_ok=True)

# Caminho do banco principal
DB_FILE = str(DIRETORIO_USUARIO / "GDAEQ.db")


@contextmanager
def conectar_bd():
    """
    Abre uma conexão SQLite com chaves estrangeiras ativadas.
    Confirma a transação em caso de sucesso e desfaz em caso de erro.
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


def criar_backup(destino):
    """
    Cria uma cópia consistente do banco de dados no destino informado.
    Retorna o caminho do arquivo criado.
    """
    origem_path = Path(DB_FILE)
    destino_path = Path(destino)

    if not origem_path.exists():
        raise FileNotFoundError("O banco de dados do GDAEQ não foi encontrado.")

    if destino_path.resolve() == origem_path.resolve():
        raise ValueError("O destino não pode ser o próprio banco de dados.")

    destino_path.parent.mkdir(parents=True, exist_ok=True)

    origem = None
    copia = None

    try:
        origem = sqlite3.connect(str(origem_path))
        copia = sqlite3.connect(str(destino_path))

        origem.backup(copia)
        copia.commit()

        return destino_path

    finally:
        if copia:
            copia.close()

        if origem:
            origem.close()


def restaurar_backup(arquivo_backup):
    """
    Restaura um backup para o banco principal do GDAEQ.

    Antes da substituição, cria uma cópia de segurança
    do banco atual, caso ele exista.
    """
    backup_path = Path(arquivo_backup)
    banco_atual = Path(DB_FILE)

    if not backup_path.is_file():
        raise FileNotFoundError("O arquivo de backup não foi encontrado.")

    if backup_path.resolve() == banco_atual.resolve():
        raise ValueError("O arquivo selecionado já é o banco principal.")

    # Verifica se o arquivo é um banco válido do GDAEQ
    conexao_backup = sqlite3.connect(str(backup_path))

    try:
        resultado = conexao_backup.execute(
            "PRAGMA integrity_check;"
        ).fetchone()

        if not resultado or resultado[0] != "ok":
            raise ValueError("O arquivo de backup está danificado.")

        tabela = conexao_backup.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'Experimento'
        """).fetchone()

        if not tabela:
            raise ValueError("O arquivo não parece ser um banco do GDAEQ.")

    finally:
        conexao_backup.close()

    arquivo_temporario = None

    try:
        # Cria um arquivo temporário no mesmo diretório do banco
        descritor, caminho_temp = tempfile.mkstemp(
            suffix=".db",
            dir=str(DIRETORIO_USUARIO)
        )
        os.close(descritor)

        arquivo_temporario = Path(caminho_temp)

        # Copia o backup para o arquivo temporário usando SQLite
        origem = sqlite3.connect(str(backup_path))
        destino = sqlite3.connect(str(arquivo_temporario))

        try:
            origem.backup(destino)
            destino.commit()
        finally:
            destino.close()
            origem.close()

        # Preserva o banco atual antes da restauração
        if banco_atual.exists():
            horario = datetime.now().strftime("%Y%m%d_%H%M%S")

            copia_seguranca = (
                DIRETORIO_USUARIO /
                f"GDAEQ_antes_restauracao_{horario}.db"
            )

            criar_backup(copia_seguranca)

        # Substitui o banco principal pelo arquivo temporário
        os.replace(arquivo_temporario, banco_atual)

        return banco_atual

    finally:
        if arquivo_temporario and arquivo_temporario.exists():
            arquivo_temporario.unlink()
