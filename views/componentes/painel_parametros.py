import customtkinter as ctk
import re


class PainelParametros(ctk.CTkFrame):
    def __init__(self, master, substancias_predefinidas: dict, on_selecionar_substancia, cmd_historico=None,
                 cmd_excel=None, cmd_logs=None):
        super().__init__(master, corner_radius=10)
        self.substancias_predefinidas = substancias_predefinidas
        self.on_selecionar_substancia = on_selecionar_substancia

        self.grid_rowconfigure(0, weight=0)  # Barra Superior
        self.grid_rowconfigure(1, weight=1)  # Conteúdo em Grid (expande para ocupar a tela)
        self.grid_rowconfigure(2, weight=0)  # Rodapé Fixo
        self.grid_columnconfigure(0, weight=1)

        # ----------------------------------------------------
        # 1. BARRA SUPERIOR DE AÇÕES GLOBAIS (Com fontes maiores)
        # ----------------------------------------------------
        self.frame_topo_acoes = ctk.CTkFrame(self, fg_color="gray20", corner_radius=6)
        self.frame_topo_acoes.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        self.btn_historico = ctk.CTkButton(
            self.frame_topo_acoes, text="📁 Histórico", fg_color="navy",
            width=100, height=32, font=ctk.CTkFont(size=13, weight="bold"), command=cmd_historico
        )
        self.btn_historico.pack(side="left", padx=5, pady=6)

        self.btn_excel = ctk.CTkButton(
            self.frame_topo_acoes, text="📊 Exportar", fg_color="#107c41",
            width=100, height=32, font=ctk.CTkFont(size=13, weight="bold"), command=cmd_excel
        )
        self.btn_excel.pack(side="right", padx=5, pady=6)

        self.btn_logs = ctk.CTkButton(
            self.frame_topo_acoes, text="📋 Alertas", fg_color="#b22222", hover_color="#8b0000",
            width=100, height=32, font=ctk.CTkFont(size=13, weight="bold"), command=cmd_logs
        )
        self.btn_logs.pack(side="left", expand=True, padx=5, pady=6)

        # ----------------------------------------------------
        # 2. CONTEÚDO PRINCIPAL (GRID EXPANSÍVEL)
        # ----------------------------------------------------
        self.frame_grid = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_grid.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.frame_grid.grid_columnconfigure(0, weight=1)
        self.frame_grid.grid_columnconfigure(1, weight=1)

        # Faz as linhas do grid expandirem proporcionalmente para preencher a tela cheia
        for i in range(12):
            self.frame_grid.grid_rowconfigure(i, weight=1)

        r = 0

        # --- Identificação do Ensaio ---
        self._lbl_secao(self.frame_grid, "Identificação do Experimento", row=r, columnspan=2)
        r += 1
        self.txt_nome_exp = self._entry_grid(self.frame_grid, "Nome do Ensaio", row=r, col=0, columnspan=2)
        r += 1
        self.txt_professor = self._entry_grid(self.frame_grid, "Nome do Professor", row=r, col=0)
        self.txt_turma = self._entry_grid(self.frame_grid, "Turma / Disciplina", row=r, col=1)
        r += 1

        # --- Dados da Substância ---
        self._lbl_secao(self.frame_grid, "Dados da Substância & Parâmetros", row=r, columnspan=2)
        r += 1

        self.combo_subst = ctk.CTkOptionMenu(
            self.frame_grid, values=list(substancias_predefinidas.keys()), command=self._ao_alterar_substancia,
            height=32, font=ctk.CTkFont(size=13)
        )
        self.combo_subst.grid(row=r, column=0, columnspan=2, padx=5, pady=4, sticky="ew")
        r += 1

        self.txt_subst_nome = self._entry_grid(self.frame_grid, "Nome da Substância", row=r, col=0)
        self.txt_subst_formula = self._entry_grid(self.frame_grid, "Fórmula Química", row=r, col=1)
        r += 1

        self.txt_massa_molar = self._entry_grid(self.frame_grid, "Massa Molar (g/mol)", row=r, col=0)
        self.txt_massa = self._entry_grid(self.frame_grid, "Massa Reagente (g)", row=r, col=1)
        r += 1

        self.txt_entalpia = self._entry_grid(self.frame_grid, "Entalpia ΔH (kJ/mol)", row=r, col=0)
        self.txt_temp_ini = self._entry_grid(self.frame_grid, "Temp. Inicial (°C)", row=r, col=1)
        r += 1

        self.txt_massa_total = self._entry_grid(self.frame_grid, "Massa Total (g)", row=r, col=0)
        self.txt_porta_com = self._entry_grid(self.frame_grid, "Porta COM", row=r, col=1)
        r += 1

        # ----------------------------------------------------
        # 3. RODAPÉ FIXO COM BOTAIS GRANDES E DESTACADOS
        # ----------------------------------------------------
        self.frame_rodape = ctk.CTkFrame(self, fg_color="gray20", corner_radius=6)
        self.frame_rodape.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        btn_font = ctk.CTkFont(size=14, weight="bold")

        self.btn_calibrar = ctk.CTkButton(self.frame_rodape, text="Calibrar Sensores (Tara)", fg_color="gray40",
                                          height=36, font=btn_font)
        self.btn_calibrar.pack(fill="x", padx=10, pady=(8, 4))

        self.btn_iniciar = ctk.CTkButton(self.frame_rodape, text="Iniciar", fg_color="green", height=36, font=btn_font)
        self.btn_iniciar.pack(fill="x", padx=10, pady=4)

        self.btn_pausar = ctk.CTkButton(self.frame_rodape, text="Pausar / Retomar", fg_color="orange",
                                        state="disabled", command=self._ao_clicar_pausa, height=36, font=btn_font)
        self.btn_pausar.pack(fill="x", padx=10, pady=4)

        self.btn_parar = ctk.CTkButton(self.frame_rodape, text="Interromper Emergência", fg_color="red",
                                       state="disabled", height=36, font=btn_font)
        self.btn_parar.pack(fill="x", padx=10, pady=4)

        self.btn_atualizar = ctk.CTkButton(
            self.frame_rodape, text="💾 Salvar Alterações (Atualizar)", fg_color="#1f538d", hover_color="#14375e",
            height=36, font=btn_font
        )
        self.btn_atualizar.pack(fill="x", padx=10, pady=(4, 8))

    def _lbl_secao(self, parent, texto: str, row: int, columnspan: int = 1):
        lbl = ctk.CTkLabel(parent, text=texto, font=ctk.CTkFont(size=15, weight="bold"))
        lbl.grid(row=row, column=0, columnspan=columnspan, padx=5, pady=(10, 4), sticky="w")

    def _entry_grid(self, parent, label_text, row, col, columnspan=1):
        frame_campo = ctk.CTkFrame(parent, fg_color="transparent")
        frame_campo.grid(row=row, column=col, columnspan=columnspan, padx=5, pady=4, sticky="nsew")

        lbl = ctk.CTkLabel(
            frame_campo,
            text=label_text,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")  # Fonte bem legível para aulas
        )
        lbl.pack(fill="x", padx=2, pady=(0, 2))

        entry = ctk.CTkEntry(frame_campo, height=32, font=ctk.CTkFont(size=13))  # Caixas de texto maiores
        entry.pack(fill="x")

        return entry

    def _limpar_espacos(self, texto: str) -> str:
        """Remove espaços excessivos nas extremidades e compacta múltiplos espaços internos."""
        if not texto:
            return ""
        return re.sub(r'\s+', ' ', texto).strip()

    def _ao_alterar_substancia(self, escolha: str):
        if escolha in self.substancias_predefinidas:
            subst = self.substancias_predefinidas[escolha]
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

    def _ao_clicar_pausa(self):
        if hasattr(self.master, "alternar_pausa_experimento"):
            self.master.alternar_pausa_experimento()

    def atualizar_estado_botao_pausa(self, pausado: bool):
        """Altera o texto e a cor do botão de pausa visualmente para o utilizador."""
        if pausado:
            self.btn_pausar.configure(text="Retomar Ensaio", fg_color="#28a745")
        else:
            self.btn_pausar.configure(text="Pausar Ensaio", fg_color="orange")

    def atualizar_estado_botoes(self, status: str):
        """
        Controla a interatividade dos botões e campos com base no estado do experimento.
        """
        todos_campos = [
            self.txt_nome_exp, self.txt_professor, self.txt_turma,
            self.txt_subst_nome, self.txt_subst_formula,
            self.txt_massa_molar, self.txt_massa, self.txt_entalpia,
            self.txt_temp_ini, self.txt_massa_total, self.txt_porta_com
        ]

        self.btn_historico.configure(state="normal")
        self.btn_excel.configure(state="normal")

        if status in ["Pausado", "Reagindo"]:
            for campo in todos_campos:
                campo.configure(state="disabled", fg_color="gray25", text_color="#FFFFFF")

            self.combo_subst.configure(state="disabled")
            self.btn_calibrar.configure(state="disabled", fg_color="gray30")
            self.btn_atualizar.configure(state="disabled")

            if status == "Pausado":
                self.btn_pausar.configure(state="normal")
                self.btn_parar.configure(state="normal")
            else:
                self.btn_iniciar.configure(state="disabled")
                self.btn_pausar.configure(state="normal")
                self.btn_parar.configure(state="normal")

        elif status == "Finalizado":
            campos_fisicos_e_tecnicos = [
                self.txt_massa_molar, self.txt_massa, self.txt_entalpia,
                self.txt_temp_ini, self.txt_massa_total, self.txt_porta_com
            ]
            for campo in campos_fisicos_e_tecnicos:
                campo.configure(state="disabled", fg_color="gray25", text_color="#FFFFFF")

            campos_permitidos_pos_ensaio = [
                self.txt_nome_exp, self.txt_professor, self.txt_turma,
                self.txt_subst_nome, self.txt_subst_formula
            ]
            for campo in campos_permitidos_pos_ensaio:
                campo.configure(state="normal", fg_color=("#F9F9F9", "#343638"), text_color=("#000000", "#FFFFFF"))

            self.combo_subst.configure(state="normal")
            self.btn_atualizar.configure(state="normal")
            self.btn_iniciar.configure(state="normal")

            self.btn_calibrar.configure(state="disabled", fg_color="gray30")
            self.btn_pausar.configure(state="disabled")
            self.btn_parar.configure(state="disabled")

        elif status == "Inativo":
            for campo in todos_campos:
                campo.configure(state="normal", fg_color=("#F9F9F9", "#343638"), text_color=("#000000", "#FFFFFF"))

            self.combo_subst.configure(state="normal")
            self.btn_calibrar.configure(state="normal", fg_color="gray40")
            self.btn_atualizar.configure(state="normal")
            self.btn_iniciar.configure(state="normal")
            self.btn_pausar.configure(state="disabled")
            self.btn_parar.configure(state="disabled")

    def _set_text(self, entry: ctk.CTkEntry, valor: str):
        entry.configure(state="normal", fg_color=("#F9F9F9", "#343638"))
        entry.delete(0, "end")

        if valor is not None and str(valor).strip() != "" and str(valor).strip() != "0.0":
            entry.insert(0, str(valor))
        else:
            entry.focus_set()
            entry.selection_clear()

        self.focus_set()

    def obter_dados_formulario(self) -> dict:
        return {
            "nome_exp": self._limpar_espacos(self.txt_nome_exp.get()),
            "descricao": "",
            "professor": self._limpar_espacos(self.txt_professor.get()),
            "turma": self._limpar_espacos(self.txt_turma.get()),
            "subst_nome": self._limpar_espacos(self.txt_subst_nome.get()),
            "subst_formula": self._limpar_espacos(self.txt_subst_formula.get()),
            "estado_fisico": "Líquido",
            "massa_molar": float(self.txt_massa_molar.get() or 0),
            "entalpia": float(self.txt_entalpia.get() or 0),
            "coef_estequio": 1,
            "temp_ini": float(self.txt_temp_ini.get() or 0),
            "massa_reagente": float(self.txt_massa.get() or 0),
            "massa_total": float(self.txt_massa_total.get() or 0),
            "porta_com": self._limpar_espacos(self.txt_porta_com.get())
        }

    def preencher_formulario(self, dados: dict):
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
        self._set_text(self.txt_porta_com, str(dados.get("porta_com", "")))

    def bloquear_parametros_fisicos(self):
        campos_para_bloquear = [
            self.txt_massa_molar, self.txt_massa, self.txt_entalpia,
            self.txt_temp_ini, self.txt_massa_total
        ]
        for campo in campos_para_bloquear:
            campo.configure(state="normal")
            campo.configure(state="disabled", fg_color="gray25", text_color="#FFFFFF")
        self.btn_calibrar.configure(state="disabled", fg_color="gray30")

    def liberar_parametros_fisicos(self):
        campos_para_liberar = [
            self.txt_massa_molar, self.txt_massa, self.txt_entalpia,
            self.txt_temp_ini, self.txt_massa_total
        ]
        for campo in campos_para_liberar:
            campo.configure(state="normal", fg_color=("#F9F9F9", "#343638"), text_color=("#000000", "#FFFFFF"))
        self.btn_calibrar.configure(state="normal", fg_color="gray40")