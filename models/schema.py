import sqlite3
from models.database import conectar_bd, DB_FILE

# Script DDL completo (tabelas e triggers)
DDL_SCRIPT = """
CREATE TABLE IF NOT EXISTS Turma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Professor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Substancia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    formula TEXT NOT NULL,
    estado_fisico TEXT NOT NULL,
    massa_molar REAL NOT NULL,
    entalpia_formacao REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS Experimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo_reacao TEXT NOT NULL,
    data_realizacao TEXT,
    turma_id INTEGER NOT NULL,
    professor_id INTEGER NOT NULL,
    descricao TEXT,
    FOREIGN KEY (turma_id) REFERENCES Turma(id) ON DELETE RESTRICT,
    FOREIGN KEY (professor_id) REFERENCES Professor(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Experimento_Substancia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experimento_id INTEGER NOT NULL,
    substancia_id INTEGER NOT NULL,
    papel TEXT NOT NULL,
    coeficiente_estequiometrico INTEGER NOT NULL,
    FOREIGN KEY (experimento_id) REFERENCES Experimento(id) ON DELETE CASCADE,
    FOREIGN KEY (substancia_id) REFERENCES Substancia(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Parametro_Simulacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experimento_id INTEGER UNIQUE NOT NULL,
    temp_inicial REAL NOT NULL,
    massa_inicial_a REAL NOT NULL,
    massa_total REAL NOT NULL,
    FOREIGN KEY (experimento_id) REFERENCES Experimento(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Dado_Grafico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experimento_id INTEGER NOT NULL,
    tempo REAL NOT NULL,
    temp_real REAL NOT NULL,
    temp_simulada REAL NOT NULL,
    FOREIGN KEY (experimento_id) REFERENCES Experimento(id) ON DELETE CASCADE
);

-- Triggers de Segurança e Negócio
CREATE TRIGGER IF NOT EXISTS trg_validar_temp_sensor
BEFORE INSERT ON Dado_Grafico
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Erro de Leitura: Temperatura fora da faixa operacional segura (0°C a 100°C).')
    WHERE NEW.temp_real < 0 OR NEW.temp_real > 100;
END;

CREATE TRIGGER IF NOT EXISTS trg_validar_coeficiente
BEFORE INSERT ON Experimento_Substancia
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.coeficiente_estequiometrico <= 0 THEN
            RAISE(ABORT, 'Erro de Validação: O coeficiente estequiométrico deve ser maior que zero.')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_auto_data_experimento
AFTER INSERT ON Experimento
FOR EACH ROW
WHEN NEW.data_realizacao IS NULL
BEGIN
    UPDATE Experimento
    SET data_realizacao = DATE('now')
    WHERE id = NEW.id;
END;
"""

def criar_banco_e_tabelas():
    """Executa o script DDL para criar todas as tabelas e triggers."""
    try:
        with conectar_bd() as conexao:
            conexao.executescript(DDL_SCRIPT)

            conexao.execute("INSERT OR IGNORE INTO Turma (id, nome) VALUES (1, 'Turma Padrão');")
            conexao.execute("INSERT OR IGNORE INTO Professor (id, nome) VALUES (1, 'Professor Padrão');")
            conexao.commit()

        print(f"✅ Estrutura do banco de dados criada/atualizada com sucesso em '{DB_FILE}'.")
    except sqlite3.Error as erro:
        print(f"❌ Erro ao criar o esquema do banco de dados: {erro}")

if __name__ == "__main__":
    criar_banco_e_tabelas()