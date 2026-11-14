
from pathlib import Path
from models.database import criar_backup, restaurar_backup


class BackupController:
    """Controla as operações de backup e restauração do GDAEQ."""

    def fazer_backup(self, destino: str) -> str:
        """
        Solicita ao Model a criação de um backup.

        Args:
            destino: Caminho onde o backup será salvo.

        Returns:
            Caminho do arquivo criado.
        """

        if not destino:
            raise ValueError("Selecione onde deseja salvar o backup.")

        caminho = criar_backup(destino)

        return str(caminho)

    def restaurar_backup(self, arquivo: str) -> str:
        """
        Solicita ao Model a restauração de um backup.

        Args:
            arquivo: Caminho do arquivo de backup selecionado.

        Returns:
            Caminho do banco restaurado.
        """

        if not arquivo:
            raise ValueError("Selecione um arquivo de backup.")

        caminho = restaurar_backup(arquivo)

        return str(caminho)
