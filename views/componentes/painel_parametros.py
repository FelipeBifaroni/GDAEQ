import customtkinter as ctk

class PainelParametros(ctk.CTkScrollableFrame):
    def __init__(self, master, substancias_predefinidas: dict, on_selecionar_substancia):
        super().__init__(master, corner_radius=10)
        self.substancias_predefinidas = substancias_predefinidas
        self.on_selecionar_substancia = on_selecionar_substancia

        # 1. Identificação do Ensaio
        self._titulo("Identificação do Experimento")
        self.txt_nome_exp = self._entry("Nome do Ensaio")
        self.txt_professor = self._entry("Nome do Professor")
        self.txt_turma = self._entry("Turma / Disciplina")

        # 2. Dados da Substância
        self._divisor()
        self._titulo("Dados da Substância")
        self.combo_subst = ctk.CTkOptionMenu(
            self, values=list(substancias_predefinidas.keys()), command=self._ao_alterar_substancia
        )
        self.combo_subst.pack(fill="x", padx=10, pady=4)

        self.txt_subst_nome = self._entry("Nome da Substância")
        self.txt_subst_formula = self._entry("Fórmula Química")

        ctk.CTkLabel(self, text="Estado Físico:", anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", padx=10, pady=(4, 1))
        self.combo_estado = ctk.CTkOptionMenu(self, values=["Sólido", "Líquido", "Gasoso"])
        self.combo_estado.pack(fill="x", padx=10, pady=4)

        self.txt_massa_molar = self._entry("Massa Molar (g/mol)")
        self.txt_entalpia = self._entry("Entalpia ΔH (kJ/mol)")
        self.txt_coef_estequio = self._entry("Coef. Estequiométrico")

        # 3. Parâmetros Físicos
        self._divisor()
        self._titulo("Parâmetros Físicos")
        self.txt_temp_ini = self._entry("Temp. Inicial (°C)")
        self.txt_massa = self._entry("Massa do Reagente (g)")
        self.txt_volume = self._entry("Volume do Reator (mL)")

        # 4. Conexão Hardware
        self._divisor()
        self._titulo("Conexão Hardware (Arduino)")
        self.txt_porta_com = self._entry("Porta COM (ex: COM3)")

        # 5. Botões
        self._divisor()
        self.btn_historico = ctk.CTkButton(self, text="📁 Ver Histórico de Experimentos", fg_color="navy")
        self.btn_historico.pack(fill="x", padx=10, pady=4)

        self.btn_excel = ctk.CTkButton(self, text="📊 Exportar Relatório Excel", fg_color="#107c41")
        self.btn_excel.pack(fill="x", padx=10, pady=4)

        self.btn_calibrar = ctk.CTkButton(self, text="Calibrar Sensores (Tara)", fg_color="gray40")
        self.btn_calibrar.pack(fill="x", padx=10, pady=4)

        self.btn_iniciar = ctk.CTkButton(self, text="Iniciar Ensaio", fg_color="green")
        self.btn_iniciar.pack(fill="x", padx=10, pady=4)

        self.btn_pausar = ctk.CTkButton(self, text="Pausar / Retomar", fg_color="orange", state="disabled")
        self.btn_pausar.pack(fill="x", padx=10, pady=4)

        self.btn_parar = ctk.CTkButton(self, text="Interromper Emergência", fg_color="red", state="disabled")
        self.btn_parar.pack(fill="x", padx=10, pady=(4, 15))

    def _titulo(self, texto: str):
        ctk.CTkLabel(self, text=texto, font=ctk.CTkFont(size=16, weight="bold")).pack(padx=10, pady=(10, 5))

    def _divisor(self):
        ctk.CTkFrame(self, height=2, fg_color="gray30").pack(fill="x", padx=10, pady=10)

    def _entry(self, placeholder: str) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(self, placeholder_text=placeholder)
        entry.pack(fill="x", padx=10, pady=4)
        return entry

    def _ao_alterar_substancia(self, escolha: str):
        if escolha in self.substancias_predefinidas:
            subst = self.substancias_predefinidas[escolha]
            self._set_text(self.txt_subst_nome, subst["nome"])
            self._set_text(self.txt_subst_formula, subst["formula"])
            self.combo_estado.set(subst["estado"])
            self._set_text(self.txt_massa_molar, str(subst["massa_molar"]))
            self._set_text(self.txt_entalpia, str(subst["entalpia"]))
            self._set_text(self.txt_temp_ini, "25.0")
            self._set_text(self.txt_massa, "8.0")
            self._set_text(self.txt_volume, "100.0")
            self._set_text(self.txt_coef_estequio, "1")
            self.on_selecionar_substancia(escolha)

    def _set_text(self, entry: ctk.CTkEntry, valor: str):
        entry.delete(0, "end")
        entry.insert(0, valor)

    def obter_dados_formulario(self) -> dict:
        return {
            "nome_exp": self.txt_nome_exp.get(),
            "descricao": "",
            "professor": self.txt_professor.get(),
            "turma": self.txt_turma.get(),
            "subst_nome": self.txt_subst_nome.get(),
            "subst_formula": self.txt_subst_formula.get(),
            "estado_fisico": self.combo_estado.get(),
            "massa_molar": float(self.txt_massa_molar.get() or 0),
            "entalpia": float(self.txt_entalpia.get() or 0),
            "coef_estequio": int(self.txt_coef_estequio.get() or 1),
            "temp_ini": float(self.txt_temp_ini.get() or 0),
            "massa_reagente": float(self.txt_massa.get() or 0),
            "volume": float(self.txt_volume.get() or 0),
            "porta_com": self.txt_porta_com.get()
        }