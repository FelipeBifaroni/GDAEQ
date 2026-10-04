import customtkinter as ctk


class PainelParametros(ctk.CTkFrame):
    def __init__(self, master, substancias_predefinidas: dict, on_selecionar_substancia, cmd_historico=None,
                 cmd_excel=None):
        super().__init__(master, corner_radius=10)
        self.substancias_predefinidas = substancias_predefinidas
        self.on_selecionar_substancia = on_selecionar_substancia

        # Configurar grid principal deste painel (Linha 0: Barra de Topo / Linha 1: Scroll com parâmetros)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ----------------------------------------------------
        # 1. BARRA SUPERIOR DE AÇÕES GLOBAIS (Histórico e Excel)
        # ----------------------------------------------------
        self.frame_topo_acoes = ctk.CTkFrame(self, fg_color="gray20", corner_radius=6)
        self.frame_topo_acoes.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        self.btn_historico = ctk.CTkButton(
            self.frame_topo_acoes, text="📁 Histórico", fg_color="navy",
            width=100, height=28, command=cmd_historico
        )
        self.btn_historico.pack(side="left", padx=5, pady=8)

        self.btn_excel = ctk.CTkButton(
            self.frame_topo_acoes, text="📊 Exportar", fg_color="#107c41",
            width=90, height=28, command=cmd_excel
        )
        self.btn_excel.pack(side="right", padx=5, pady=8)

        # ----------------------------------------------------
        # 2. ÁREA SCROLLÁVEL DE PARÂMETROS E CONTROLOS DO ENSAIO
        # ----------------------------------------------------
        self.scroll_params = ctk.CTkScrollableFrame(self, corner_radius=6)
        self.scroll_params.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # 1. Identificação do Ensaio
        self._titulo(self.scroll_params, "Identificação do Experimento")
        self.txt_nome_exp = self._entry(self.scroll_params, "Nome do Ensaio")
        self.txt_professor = self._entry(self.scroll_params, "Nome do Professor")
        self.txt_turma = self._entry(self.scroll_params, "Turma / Disciplina")

        # 2. Dados da Substância
        self._divisor(self.scroll_params)
        self._titulo(self.scroll_params, "Dados da Substância")
        self.combo_subst = ctk.CTkOptionMenu(
            self.scroll_params, values=list(substancias_predefinidas.keys()), command=self._ao_alterar_substancia
        )
        self.combo_subst.pack(fill="x", padx=10, pady=4)

        self.txt_subst_nome = self._entry(self.scroll_params, "Nome da Substância")
        self.txt_subst_formula = self._entry(self.scroll_params, "Fórmula Química")

        self.txt_massa_molar = self._entry(self.scroll_params, "Massa Molar do Reagente Limitante (g/mol)")
        self.txt_massa = self._entry(self.scroll_params, "Massa do Reagente (g)")
        self.txt_entalpia = self._entry(self.scroll_params, "Entalpia ΔH (kJ/mol)")

        # 3. Parâmetros Físicos
        self._divisor(self.scroll_params)
        self._titulo(self.scroll_params, "Parâmetros Físicos")
        self.txt_temp_ini = self._entry(self.scroll_params, "Temp. Inicial (°C)")
        self.txt_massa_total = self._entry(self.scroll_params, "Massa Total")

        # 4. Conexão Hardware
        self._divisor(self.scroll_params)
        self._titulo(self.scroll_params, "Conexão Hardware (Arduino)")
        self.txt_porta_com = self._entry(self.scroll_params, "Porta COM (ex: COM3)")

        # 5. Botões de Ação Direta do Ensaio
        self._divisor(self.scroll_params)

        self.btn_calibrar = ctk.CTkButton(self.scroll_params, text="Calibrar Sensores (Tara)", fg_color="gray40")
        self.btn_calibrar.pack(fill="x", padx=10, pady=4)

        self.btn_iniciar = ctk.CTkButton(self.scroll_params, text="Iniciar", fg_color="green")
        self.btn_iniciar.pack(fill="x", padx=10, pady=4)

        self.btn_pausar = ctk.CTkButton(self.scroll_params, text="Pausar / Retomar", fg_color="orange",
                                        state="disabled")
        self.btn_pausar.pack(fill="x", padx=10, pady=4)

        self.btn_parar = ctk.CTkButton(self.scroll_params, text="Interromper Emergência", fg_color="red",
                                       state="disabled")
        self.btn_parar.pack(fill="x", padx=10, pady=(4, 15))

    def _titulo(self, master, texto: str):
        ctk.CTkLabel(master, text=texto, font=ctk.CTkFont(size=16, weight="bold")).pack(padx=10, pady=(10, 5))

    def _divisor(self, master):
        ctk.CTkFrame(master, height=2, fg_color="gray30").pack(fill="x", padx=10, pady=10)

    def _entry(self, master, placeholder: str) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(master, placeholder_text=placeholder)
        entry.pack(fill="x", padx=10, pady=4)
        return entry

    def _ao_alterar_substancia(self, escolha: str):
        if escolha in self.substancias_predefinidas:
            subst = self.substancias_predefinidas[escolha]
            # Compatibilidade caso o preset seja objeto ou dicionário (sem mexer em combo_estado)
            if isinstance(subst, dict):
                self._set_text(self.txt_subst_nome, subst["nome"])
                self._set_text(self.txt_subst_formula, subst["formula"])
                self._set_text(self.txt_massa_molar, str(subst["massa_molar"]))
                self._set_text(self.txt_entalpia, str(subst["entalpia"]))
            else:
                self._set_text(self.txt_subst_nome, subst.nome)
                self._set_text(self.txt_subst_formula, subst.formula)
                self._set_text(self.txt_massa_molar, str(subst.massa_molar))
                self._set_text(self.txt_entalpia, str(subst.entalpia_formacao))

            self._set_text(self.txt_temp_ini, "25.0")
            self._set_text(self.txt_massa, "8.0")
            self._set_text(self.txt_massa_total, "100.0")
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
            "estado_fisico": "Líquido",
            "massa_molar": float(self.txt_massa_molar.get() or 0),
            "entalpia": float(self.txt_entalpia.get() or 0),
            "coef_estequio": 1,
            "temp_ini": float(self.txt_temp_ini.get() or 0),
            "massa_reagente": float(self.txt_massa.get() or 0),
            "massa_total": float(self.txt_massa_total.get() or 0),
            "porta_com": self.txt_porta_com.get()
        }

    def preencher_formulario(self, dados: dict):
        """Preenche todos os campos do painel com os dados de um experimento carregado."""
        self._set_text(self.txt_nome_exp, dados.get("nome_exp", ""))
        self._set_text(self.txt_professor, dados.get("professor", ""))
        self._set_text(self.txt_turma, dados.get("turma", ""))

        self._set_text(self.txt_subst_nome, dados.get("subst_nome", ""))
        self._set_text(self.txt_subst_formula, dados.get("subst_formula", ""))
        self._set_text(self.txt_massa_molar, str(dados.get("massa_molar", "")))
        self._set_text(self.txt_massa, str(dados.get("massa_reagente", "")))
        self._set_text(self.txt_entalpia, str(dados.get("entalpia", "")))

        self._set_text(self.txt_temp_ini, str(dados.get("temp_ini", "")))
        self._set_text(self.txt_massa_total, str(dados.get("massa_total", "")))
        self._set_text(self.txt_porta_com, dados.get("porta_com", ""))