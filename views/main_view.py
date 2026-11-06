from datetime import datetime
from tkinter import messagebox, filedialog
import customtkinter as ctk
from views.componentes.painel_parametros import PainelParametros
from views.componentes.dashboard_gui import DashboardGUI
from controllers.sensor_controller import SensorController
from controllers.experimento_controller import ExperimentoController
from tkinter import ttk


class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Monitoramento e Gêmeo Digital - Reator Químico")
        self.geometry("1380x800")
        self.minsize(1100, 650)

        self.controller = ExperimentoController()
        self.sensor_controller = SensorController(self.controller)

        self.substancias_predefinidas = {
            "Nitrato de Amônio (NH4NO3 - Endotérmica)": {"nome": "Nitrato de Amônio", "formula": "NH4NO3", "estado": "Sólido", "massa_molar": 80.04, "entalpia": 25.7},
            "Hidróxido de Sódio (NaOH - Exotérmica)": {"nome": "Hidróxido de Sódio", "formula": "NaOH", "estado": "Sólido", "massa_molar": 39.99, "entalpia": -44.51},
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.painel_esq = PainelParametros(
            self,
            self.substancias_predefinidas,
            lambda s: None,
            cmd_historico=self._abrir_historico,
            cmd_excel=self._exportar_excel,
            cmd_logs=self._abrir_janela_logs)
        self.painel_esq.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self._criar_painel_direito()
        self._vincular_eventos()

        self.after_telemetria_id = None

    def _criar_painel_direito(self):
        self.frame_direito = ctk.CTkFrame(self, corner_radius=10)
        self.frame_direito.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.frame_direito.grid_rowconfigure(0, weight=0)
        self.frame_direito.grid_rowconfigure(1, weight=3)
        self.frame_direito.grid_rowconfigure(2, weight=1)
        self.frame_direito.grid_columnconfigure(0, weight=1)

        # Status Bar
        self.frame_status = ctk.CTkFrame(self.frame_direito, fg_color="gray20")
        self.frame_status.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        self.lbl_estado = ctk.CTkLabel(self.frame_status, text="ESTADO: INATIVO", font=ctk.CTkFont(size=13, weight="bold"), text_color="lightblue")
        self.lbl_estado.pack(side="left", padx=10, pady=10)

        self.lbl_delta_t = ctk.CTkLabel(self.frame_status, text="ΔT Teórico: -- °C", font=ctk.CTkFont(size=13, weight="bold"), text_color="yellow")
        self.lbl_delta_t.pack(side="left", padx=10, pady=10)

        self.lbl_temp_real = ctk.CTkLabel(self.frame_status, text="Temp. Real: -- °C", font=ctk.CTkFont(size=13))
        self.lbl_temp_real.pack(side="left", padx=10, pady=10)

        self.lbl_temp_sim = ctk.CTkLabel(self.frame_status, text="Gêmeo Digital: -- °C", font=ctk.CTkFont(size=13))
        self.lbl_temp_sim.pack(side="left", padx=10, pady=10)

        # Matplotlib Frame
        self.frame_grafico = ctk.CTkFrame(self.frame_direito, fg_color="#1e1e1e")
        self.frame_grafico.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        self.dashboard_gui = DashboardGUI(self.frame_grafico)

        # Painel Descrição
        self.frame_descricao = ctk.CTkFrame(self.frame_direito, fg_color="gray20", corner_radius=8)
        self.frame_descricao.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="nsew")

        ctk.CTkLabel(self.frame_descricao, text="📝 Descrição e Observações do Experimento:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))

        self.txt_exp_desc = ctk.CTkTextbox(self.frame_descricao, height=80)
        self.txt_exp_desc.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _vincular_eventos(self):
        self.painel_esq.btn_iniciar.configure(command=self._iniciar_ensaio)
        self.painel_esq.btn_pausar.configure(command=self._pausar_ensaio)
        self.painel_esq.btn_parar.configure(command=self._interromper_emergencia)
        self.painel_esq.btn_calibrar.configure(command=self._calibrar_sensores)
        self.painel_esq.btn_excel.configure(command=self._exportar_excel)
        self.painel_esq.btn_historico.configure(command=self._abrir_historico)
        self.painel_esq.btn_atualizar.configure(command=self._ao_clicar_atualizar)

    def _iniciar_ensaio(self):
        if self.painel_esq.btn_iniciar.cget("text") == "✨ Novo Experimento":
            self._novo_experimento()
            return
        try:
            self.painel_esq.liberar_parametros_fisicos()
            dados = self.painel_esq.obter_dados_formulario()
            dados["descricao"] = self.txt_exp_desc.get("1.0", "end-1c").strip()

            # --- VALIDAÇÃO DE CAMPOS DE TEXTO OBRIGATÓRIOS ---
            if not dados.get("nome_exp", "").strip():
                raise ValueError("O Nome do Ensaio é obrigatório.")
            if not dados.get("professor", "").strip():
                raise ValueError("O Nome do Professor é obrigatório.")
            if not dados.get("turma", "").strip():
                raise ValueError("A Turma / Disciplina é obrigatória.")

            # --- VALIDAÇÃO CONTRA DIVISÃO POR ZERO E VALORES INVÁLIDOS ---
            if dados["massa_molar"] <= 0:
                raise ValueError("A Massa Molar deve ser maior que zero.")
            if dados["massa_total"] <= 0:
                raise ValueError("A massa total do Reator deve ser maior que zero.")
            if dados["massa_reagente"] <= 0:
                raise ValueError("A Massa do Reagente deve ser maior que zero.")

            # Inicia o ensaio apenas se todas as validações passarem
            delta_t = self.controller.iniciar_ensaio(dados)

            self.dashboard_gui.limpar()

            self.lbl_delta_t.configure(text=f"ΔT Teórico: {delta_t:.2f} °C")
            self.lbl_estado.configure(text="ESTADO: REAGINDO", text_color="lightgreen")

            self.painel_esq.atualizar_estado_botoes("Reagindo")
            self.painel_esq.btn_iniciar.configure(state="disabled")
            self.painel_esq.btn_pausar.configure(state="normal")
            self.painel_esq.btn_parar.configure(state="normal")

            self._loop_telemetria()

        except Exception as e:
            messagebox.showerror("Erro ao Iniciar", f"Verifique os campos inseridos:\n{str(e)}")

    def _pausar_ensaio(self):
        # Verifica o estado atual do experimento antes de alternar
        status_atual_exp = getattr(self.controller.experimento, "status", "")

        # Se o utilizador está a tentar despausar, mas o experimento já terminou por trás dos panos:
        if self.dashboard_gui.pausado and status_atual_exp == "Finalizado":
            # Força o gráfico a sair do pause e renderizar tudo agora que foi retomado
            self.dashboard_gui.alternar_pausa()

            # Atualiza a interface diretamente para o estado Finalizado
            self.lbl_estado.configure(text="ESTADO: FINALIZADO", text_color="cyan")
            self.painel_esq.atualizar_estado_botao_pausa(False)
            self.painel_esq.atualizar_estado_botoes("Finalizado")
            return

        # Comportamento normal de Pausa / Retomar durante o ensaio ativo
        self.dashboard_gui.alternar_pausa()
        esta_pausado = self.dashboard_gui.pausado
        novo_status = self.controller.pausar_ensaio()

        if esta_pausado:
            self.lbl_estado.configure(text="ESTADO: PAUSADO", text_color="orange")
            self.painel_esq.atualizar_estado_botao_pausa(True)
            self.painel_esq.atualizar_estado_botoes("Pausado")
        else:
            self.lbl_estado.configure(text="ESTADO: REAGINDO", text_color="lightgreen")
            self.painel_esq.atualizar_estado_botao_pausa(False)
            self.painel_esq.atualizar_estado_botoes("Reagindo")

    def _interromper_emergencia(self):
        # 1. Executa a rotina de interrupção no controller
        self.controller.interromper_emergencia()

        # 2. Atualiza a barra de status visual
        self.lbl_estado.configure(text="ESTADO: EMERGÊNCIA", text_color="red")

        # 3. Libera o botão de iniciar no formato "✨ Novo Experimento"
        self.painel_esq.btn_iniciar.configure(
            text="✨ Novo Experimento",
            fg_color="#1f538d",  # Azul estilo histórico
            hover_color="#14375e",
            state="normal"
        )

        # 4. Desativa os botões de controle direto do ensaio
        self.painel_esq.btn_pausar.configure(state="disabled")
        self.painel_esq.btn_parar.configure(state="disabled")

    def _calibrar_sensores(self):
        """Executa a tara e captura a temperatura inicial do sensor."""
        try:
            porta = self.painel_esq.txt_porta_com.get().strip()

            if not porta:
                raise ValueError("Informe a porta COM do Arduino.")

            temp_lida = self.sensor_controller.calibrar_sensores(porta_com=porta)

            self.painel_esq.txt_temp_ini.delete(0, "end")
            self.painel_esq.txt_temp_ini.insert(0, f"{temp_lida:.2f}")

            messagebox.showinfo(
                "Calibração Concluída",
                f"Leitura realizada com sucesso!\n"
                f"Temperatura inicial capturada: {temp_lida:.2f}°C"
            )

        except Exception as e:
            messagebox.showerror(
                "Erro na Calibração",
                f"Não foi possível realizar a leitura do sensor:\n{str(e)}"
            )

    def _exportar_excel(self):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Arquivos Excel", "*.xlsx")],
            title="Salvar Relatório"
        )
        if caminho:
            try:
                self.controller.exportar_excel(caminho)
                messagebox.showinfo("Sucesso", "Relatório salvo com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")

    def _abrir_historico(self):
        janela_hist = ctk.CTkToplevel(self)
        janela_hist.title("Histórico de Experimentos")
        janela_hist.geometry("850x550")
        janela_hist.grab_set()

        ctk.CTkLabel(janela_hist, text="Histórico de Experimentos Gravados",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        # --- BARRA DE PESQUISA ---
        frame_busca = ctk.CTkFrame(janela_hist, fg_color="transparent")
        frame_busca.pack(padx=20, pady=5, fill="x")

        ctk.CTkLabel(frame_busca, text="🔍 Filtrar:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)

        entry_pesquisa = ctk.CTkEntry(frame_busca,
                                      placeholder_text="Digite o nome do experimento, professor ou turma...", width=450)
        entry_pesquisa.pack(side="left", padx=5, fill="x", expand=True)

        # Cabeçalho da Tabela
        header_frame = ctk.CTkFrame(janela_hist, fg_color="gray25", height=35)
        header_frame.pack(padx=20, pady=(10, 5), fill="x")

        ctk.CTkLabel(header_frame, text="ID", width=30, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Nome do Ensaio", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Professor", width=140, anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Turma", width=100, anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Ação", width=190, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=10)

        # Área Scrollável onde ficam os itens
        frame_lista = ctk.CTkScrollableFrame(janela_hist, width=790, height=340)
        frame_lista.pack(padx=20, pady=5, fill="both", expand=True)

        todos_experimentos = self.controller.listar_historico_banco()

        def popular_tabela(dados_filtrados):
            for widget in frame_lista.winfo_children():
                widget.destroy()

            if not dados_filtrados:
                ctk.CTkLabel(frame_lista, text="Nenhum experimento encontrado.", text_color="gray").pack(pady=20)
                return

            for exp in dados_filtrados:
                item_frame = ctk.CTkFrame(frame_lista, fg_color="gray17", corner_radius=6)
                item_frame.pack(fill="x", pady=4, ipady=4)

                ctk.CTkLabel(item_frame, text=str(exp["id"]), width=30).pack(side="left", padx=5)
                ctk.CTkLabel(item_frame, text=exp["nome"], width=200, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(item_frame, text=exp["professor"], width=140, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(item_frame, text=exp["turma"], width=100, anchor="w").pack(side="left", padx=5)

                # Botão de Excluir
                btn_excluir = ctk.CTkButton(
                    item_frame, text="🗑️ Excluir", width=80, fg_color="#a83232", hover_color="#7a2222",
                    command=lambda eid=exp["id"], nome=exp["nome"], j_hist=janela_hist: self._confirmar_e_excluir(eid,
                                                                                                                  nome,
                                                                                                                  j_hist)
                )
                btn_excluir.pack(side="right", padx=5)

                # Botão para Carregar
                btn_carregar = ctk.CTkButton(
                    item_frame, text="📂 Carregar", width=90, fg_color="#1f538d",
                    command=lambda eid=exp["id"]: self._carregar_e_fechar_historico(eid, janela_hist)
                )
                btn_carregar.pack(side="right", padx=5)

        def filtrar(*args):
            termo = entry_pesquisa.get().strip().lower()
            if not termo:
                popular_tabela(todos_experimentos)
                return

            filtrados = [
                exp for exp in todos_experimentos
                if termo in exp["nome"].lower()
                   or termo in exp["professor"].lower()
                   or termo in exp["turma"].lower()
            ]
            popular_tabela(filtrados)

        entry_pesquisa.bind("<KeyRelease>", filtrar)
        popular_tabela(todos_experimentos)

    def _carregar_e_fechar_historico(self, experimento_id, janela):
        self.painel_esq.liberar_parametros_fisicos()
        sucesso = self.controller.carregar_experimento_por_id(experimento_id)
        if sucesso:
            # 1. Limpa e plota o gráfico
            self.dashboard_gui.limpar()
            for dado in self.controller.experimento.dados_grafico:
                self.dashboard_gui.renderizar_ponto(dado)

            # 2. Atualiza a barra de status
            self.lbl_estado.configure(text="ESTADO: HISTÓRICO CARREGADO", text_color="cyan")

            # 3. Pede os dados formatados diretamente ao controller (Sem acoplamento profundo)
            dados_formulario = self.controller.obter_dados_experimento_ativo()
            self.painel_esq.preencher_formulario(dados_formulario)

            # 4. Ajusta estados e o visual do botão para o modo Histórico Carregado
            self.painel_esq.bloquear_parametros_fisicos()

            self.painel_esq.btn_iniciar.configure(
                text="✨ Novo Experimento",
                fg_color="#1f538d",  # Azul
                hover_color="#14375e",
                state="normal"
            )
            self.painel_esq.btn_pausar.configure(state="disabled")
            self.painel_esq.btn_parar.configure(state="disabled")

            # Atualiza o campo de descrição separadamente
            self.txt_exp_desc.delete("1.0", "end")
            self.txt_exp_desc.insert("1.0", dados_formulario["descricao"])

            param = self.controller.experimento.parametro_simulacao
            if param and self.controller.experimento.dados_grafico:
                delta_t_estimado = self.controller.experimento.dados_grafico[-1].temp_simulada - param.temp_inicial
                self.lbl_delta_t.configure(text=f"ΔT Teórico/Real: {delta_t_estimado:.2f} °C")

            janela.destroy()
            messagebox.showinfo("Sucesso", f"Experimento #{experimento_id} carregado com sucesso!")
        else:
            messagebox.showerror("Erro", "Não foi possível carregar os dados deste experimento.")

    def _confirmar_e_excluir(self, experimento_id, nome_ensaio, janela_historico):
        """Exibe uma confirmação personalizada antes de excluir o experimento."""

        janela = ctk.CTkToplevel(janela_historico)
        janela.title("Confirmar Exclusão")
        janela.geometry("460x240")
        janela.resizable(False, False)
        janela.configure(fg_color="#1e1e1e")

        janela.transient(janela_historico)
        janela.grab_set()
        janela.lift()
        janela.focus_force()

        ctk.CTkLabel(
            janela,
            text="⚠  Confirmar exclusão",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ff5555"
        ).pack(pady=(22, 12))

        ctk.CTkLabel(
            janela,
            text=(
                f"Tem certeza que deseja excluir o experimento "
                f"#{experimento_id} ('{nome_ensaio}')?\n\n"
                "Esta ação não pode ser desfeita!"
            ),
            font=ctk.CTkFont(size=13),
            text_color="#eeeeee",
            wraplength=420,
            justify="center"
        ).pack(padx=20, pady=5)

        frame_botoes = ctk.CTkFrame(
            janela,
            fg_color="transparent"
        )
        frame_botoes.pack(fill="x", padx=25, pady=(20, 18))

        resposta = {"confirmado": False}

        def cancelar():
            janela.destroy()

        def confirmar():
            resposta["confirmado"] = True
            janela.destroy()

        # Botão NÃO em destaque
        ctk.CTkButton(
            frame_botoes,
            text="Não, voltar",
            height=44,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=cancelar
        ).pack(side="left", padx=(0, 10), expand=True, fill="x")

        # Botão SIM em vermelho
        ctk.CTkButton(
            frame_botoes,
            text="Sim, excluir",
            height=40,
            fg_color="#991b1b",
            hover_color="#7f1d1d",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=confirmar
        ).pack(side="left", expand=True, fill="x")

        janela.update_idletasks()
        x = janela_historico.winfo_rootx() + (
                janela_historico.winfo_width() - janela.winfo_width()
        ) // 2
        y = janela_historico.winfo_rooty() + (
                janela_historico.winfo_height() - janela.winfo_height()
        ) // 2
        janela.geometry(f"+{max(0, x)}+{max(0, y)}")

        janela.wait_window()

        if not resposta["confirmado"]:
            return

        if resposta:
            sucesso = self.controller.excluir_experimento(experimento_id)
            if sucesso:
                messagebox.showinfo("Sucesso", f"Experimento #{experimento_id} excluído com sucesso.")
                janela_historico.destroy()
                self._abrir_historico()  # Reabre a janela de histórico atualizada
            else:
                messagebox.showerror("Erro", "Não foi possível excluir o experimento do banco de dados.")

    def _loop_telemetria(self):
        self.after_telemetria_id = None
        try:
            ponto = self.controller.obter_proximo_ponto()

            if ponto:
                status_atual = ponto.get("status", "")

                if status_atual == "Emergência":
                    motivo = ponto.get("motivo", "")
                    self.acionar_emergencia_visual(motivo)

                else:
                    self.lbl_temp_real.configure(
                        text=f"Temp. Real: {ponto['temp_real']:.2f} °C"
                    )

                    self.lbl_temp_sim.configure(
                        text=f"Gêmeo Digital: {ponto['temp_simulada']:.2f} °C"
                    )

                    if status_atual == "Reagindo":
                        self.lbl_estado.configure(
                            text="ESTADO: REAGINDO",
                            text_color="lightgreen"
                        )

                    elif status_atual == "Finalizado":
                        self.lbl_estado.configure(
                            text="ESTADO: FINALIZADO",
                            text_color="cyan"
                        )

                        self.painel_esq.btn_iniciar.configure(
                            text="Novo Experimento",
                            command=self._novo_experimento,
                            fg_color="#1F6AA5",
                            hover_color="#144870",
                            state="normal"
                        )

                        if not self.dashboard_gui.pausado:
                            self.painel_esq.atualizar_estado_botao_pausa(False)
                            self.painel_esq.atualizar_estado_botoes("Finalizado")

                    if ponto.get("dado_obj"):
                        self.dashboard_gui.renderizar_ponto(ponto["dado_obj"])


        except Exception as e:

            print(f"⚠️ Erro capturado no loop de telemetria: {e}")

            self.parar_loop_telemetria()

            return

        if self.controller.executando:
            self.after_telemetria_id = self.after(
                1000,
                self._loop_telemetria
            )

    def acionar_emergencia_visual(self, motivo: str = ""):
        """Atualiza a interface para o estado crítico de emergência."""

        self.lbl_estado.configure(
            text="ESTADO: EMERGÊNCIA",
            text_color="#ff3333"
        )

        if hasattr(self, 'painel_esq'):
            self.painel_esq.liberar_parametros_fisicos()
            self.painel_esq.atualizar_estado_botoes("Inativo")

            self.painel_esq.btn_iniciar.configure(
                text="✨ Novo Experimento",
                fg_color="#1f538d",
                hover_color="#14375e",
                state="normal"
            )
            self.painel_esq.btn_pausar.configure(state="disabled")
            self.painel_esq.btn_parar.configure(state="disabled")
            self.painel_esq.btn_historico.configure(state="normal")
            self.painel_esq.btn_excel.configure(state="normal")

        # Janela personalizada de emergência
        janela = ctk.CTkToplevel(self)
        janela.title("Alerta de Emergência")
        janela.geometry("500x320")
        janela.resizable(False, False)
        janela.configure(fg_color="#181818")

        janela.transient(self)
        janela.grab_set()
        janela.lift()
        janela.focus_force()

        # Cabeçalho vermelho
        cabecalho = ctk.CTkFrame(
            janela,
            fg_color="#b91c1c",
            corner_radius=0,
            height=85
        )
        cabecalho.pack(fill="x")
        cabecalho.pack_propagate(False)

        ctk.CTkLabel(
            cabecalho,
            text="⚠  EMERGÊNCIA",
            font=ctk.CTkFont(size=27, weight="bold"),
            text_color="#ffffff"
        ).pack(expand=True)

        # Identifica o tipo de emergência
        motivo_lower = motivo.lower()

        if "arduino" in motivo_lower or "sensor" in motivo_lower or "comunicação" in motivo_lower:
            titulo_alerta = "FALHA NA CONEXÃO COM ARDUINO"
            mensagem_alerta = (
                "O experimento foi interrompido por falha na leitura do sensor.\n\n"
                "Verifique a conexão do Arduino, o cabo USB e o sensor de temperatura.\n"
                "Reconecte o dispositivo antes de iniciar um novo ensaio."
            )

        elif "temperatura" in motivo_lower or "°c" in motivo_lower:
            titulo_alerta = "TEMPERATURA FORA DA FAIXA SEGURA"
            mensagem_alerta = (
                "O experimento foi interrompido por segurança.\n\n"
                "Faixa de temperatura permitida: 0 °C a 100 °C.\n"
                "Verifique as condições antes de iniciar um novo ensaio."
            )

        else:
            titulo_alerta = "EMERGÊNCIA NO EXPERIMENTO"
            mensagem_alerta = (
                "O experimento foi interrompido por segurança.\n\n"
                f"Motivo: {motivo or 'Não informado.'}"
            )

        # Título do alerta
        ctk.CTkLabel(
            janela,
            text=titulo_alerta,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ff4d4d",
            wraplength=450
        ).pack(padx=20, pady=(22, 10))

        # Mensagem
        ctk.CTkLabel(
            janela,
            text=mensagem_alerta,
            font=ctk.CTkFont(size=13),
            text_color="#eeeeee",
            justify="center",
            wraplength=440
        ).pack(padx=25, pady=5)

        # Botão de confirmação
        ctk.CTkButton(
            janela,
            text="ENTENDI — FECHAR ALERTA",
            height=42,
            fg_color="#b91c1c",
            hover_color="#7f1d1d",
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=janela.destroy
        ).pack(fill="x", padx=30, pady=(22, 18))

        # Centraliza a janela em relação à interface principal
        janela.update_idletasks()

        x = self.winfo_rootx() + (
                self.winfo_width() - janela.winfo_width()
        ) // 2
        y = self.winfo_rooty() + (
                self.winfo_height() - janela.winfo_height()
        ) // 2

        janela.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _ao_clicar_atualizar(self):
        """Recolhe os dados editados da tela e atualiza o registo ativo no banco."""
        if not getattr(self.controller, 'experimento_id_db', None):
            messagebox.showwarning("Aviso", "Nenhum experimento carregado ou ativo para atualizar. Carregue um do histórico primeiro.")
            return

        try:
            dados = self.painel_esq.obter_dados_formulario()
            dados["descricao"] = self.txt_exp_desc.get("1.0", "end-1c").strip()

            # Validações básicas
            if not dados.get("nome_exp", "").strip():
                raise ValueError("O Nome do Ensaio é obrigatório.")
            if not dados.get("professor", "").strip():
                raise ValueError("O Nome do Professor é obrigatório.")
            if not dados.get("turma", "").strip():
                raise ValueError("A Turma é obrigatória.")

            # Executa a atualização via controller
            sucesso = self.controller.atualizar_experimento_atual(dados)

            if sucesso:
                messagebox.showinfo("Sucesso", f"Experimento #{self.controller.experimento_id_db} atualizado com sucesso!")
            else:
                messagebox.showerror("Erro", "Não foi possível atualizar o registo no banco de dados.")

        except Exception as e:
            messagebox.showerror("Erro de Validação", f"Erro ao atualizar:\n{str(e)}")

    def _novo_experimento(self):
        """Reseta a interface e o controller para permitir criar um novo ensaio do zero."""
        self.controller.novo_experimento()

        # 1. DESTRAVA OS PARÂMETROS E ATUALIZA O ESTADO DOS BOTÕES
        self.painel_esq.liberar_parametros_fisicos()
        self.painel_esq.atualizar_estado_botoes("Inativo")  # <--- ADICIONE ESTA LINHA!

        # 2. Libera também os campos de identificação e substância
        campos_parametros = [
            self.painel_esq.txt_nome_exp, self.painel_esq.txt_professor, self.painel_esq.txt_turma,
            self.painel_esq.txt_subst_nome, self.painel_esq.txt_subst_formula, self.painel_esq.txt_porta_com
        ]
        for campo in campos_parametros:
            campo.configure(state="normal", fg_color=("#F9F9F9", "#343638"), text_color=("#000000", "#FFFFFF"))

        self.painel_esq.combo_subst.configure(state="normal")

        # 3. Limpa os campos do formulário
        campos_vazios = {
            "nome_exp": "", "professor": "", "turma": "",
            "subst_nome": "", "subst_formula": "",
            "massa_molar": "", "massa_reagente": "",
            "entalpia": "", "temp_ini": "", "massa_total": "",
            "porta_com": "COM3", "descricao": ""
        }
        self.painel_esq.preencher_formulario(campos_vazios)
        self.txt_exp_desc.delete("1.0", "end")

        # 4. Limpa gráfico e status
        self.dashboard_gui.limpar()
        self.lbl_estado.configure(text="ESTADO: INATIVO", text_color="lightblue")
        self.lbl_delta_t.configure(text="ΔT Teórico: -- °C", text_color="yellow")
        self.lbl_temp_real.configure(text="Temp. Real: -- °C")
        self.lbl_temp_sim.configure(text="Gêmeo Digital: -- °C")

        # 5. Restaura o botão de Iniciar ao estado original (VERDE)
        # 5. Restaura o botão de Iniciar ao estado original
        self.painel_esq.btn_iniciar.configure(
            text="Iniciar",
            command=lambda: self._iniciar_ensaio(),
            fg_color="green",
            hover_color="#134f13",
            state="normal"
        )

        self.painel_esq.btn_pausar.configure(state="disabled")
        self.painel_esq.btn_parar.configure(state="disabled")

        messagebox.showinfo(
            "Novo Ensaio",
            "Ambiente limpo! Insira os dados para iniciar um novo experimento."
        )

    def _abrir_janela_logs(self):
        """Abre uma janela estilizada com o histórico de alertas e emergências."""

        janela_logs = ctk.CTkToplevel(self)
        janela_logs.title("Histórico de Alertas e Emergências")
        janela_logs.geometry("950x520")
        janela_logs.minsize(750, 400)
        janela_logs.configure(fg_color="#1e1e1e")
        janela_logs.grab_set()

        # Centraliza a janela em relação à janela principal
        janela_logs.update_idletasks()
        largura = 950
        altura = 520
        x = self.winfo_x() + (self.winfo_width() - largura) // 2
        y = self.winfo_y() + (self.winfo_height() - altura) // 2
        janela_logs.geometry(f"{largura}x{altura}+{x}+{y}")

        # =========================
        # CABEÇALHO
        # =========================
        frame_topo = ctk.CTkFrame(
            janela_logs,
            fg_color="#2b2b2b",
            corner_radius=10
        )
        frame_topo.pack(fill="x", padx=15, pady=(15, 10))

        lbl_icone = ctk.CTkLabel(
            frame_topo,
            text="⚠",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#ff4d4d"
        )
        lbl_icone.pack(side="left", padx=(15, 10), pady=12)

        frame_titulos = ctk.CTkFrame(
            frame_topo,
            fg_color="transparent"
        )
        frame_titulos.pack(side="left", fill="y", pady=10)

        ctk.CTkLabel(
            frame_titulos,
            text="Histórico de Alertas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame_titulos,
            text="Registro de ocorrências e emergências do sistema",
            font=ctk.CTkFont(size=12),
            text_color="#b0b0b0"
        ).pack(anchor="w", pady=(2, 0))

        # =========================
        # ÁREA DA TABELA
        # =========================
        frame_tabela = ctk.CTkFrame(
            janela_logs,
            fg_color="#252525",
            corner_radius=10
        )
        frame_tabela.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 10)
        )

        colunas = ("ID", "Tipo de Evento", "Descrição", "Data e Hora")

        tabela = ttk.Treeview(
            frame_tabela,
            columns=colunas,
            show="headings",
            height=12
        )

        # Estilo escuro da tabela
        estilo = ttk.Style(janela_logs)
        estilo.theme_use("clam")

        estilo.configure(
            "Alertas.Treeview",
            background="#252525",
            foreground="#f0f0f0",
            fieldbackground="#252525",
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0
        )

        estilo.configure(
            "Alertas.Treeview.Heading",
            background="#383838",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(8, 8)
        )

        estilo.map(
            "Alertas.Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "#ffffff")]
        )

        estilo.map(
            "Alertas.Treeview.Heading",
            background=[("active", "#4a4a4a")]
        )

        tabela.configure(style="Alertas.Treeview")

        # Cabeçalhos
        tabela.heading("ID", text="ID")
        tabela.heading("Tipo de Evento", text="Tipo de Evento")
        tabela.heading("Descrição", text="Descrição do Ocorrido")
        tabela.heading("Data e Hora", text="Data e Hora")

        # Largura e alinhamento das colunas
        tabela.column("ID", width=55, minwidth=45, anchor="center", stretch=False)
        tabela.column(
            "Tipo de Evento", width=190, minwidth=140,
            anchor="center", stretch=False
        )
        tabela.column(
            "Descrição", width=420, minwidth=200,
            anchor="w", stretch=True
        )
        tabela.column(
            "Data e Hora", width=175, minwidth=155,
            anchor="center", stretch=False
        )

        # Barras de rolagem
        scrollbar_y = ttk.Scrollbar(
            frame_tabela,
            orient="vertical",
            command=tabela.yview
        )
        scrollbar_x = ttk.Scrollbar(
            frame_tabela,
            orient="horizontal",
            command=tabela.xview
        )

        tabela.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        tabela.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        scrollbar_y.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(8, 0))
        scrollbar_x.grid(row=1, column=0, sticky="ew", padx=(8, 0), pady=(0, 8))

        frame_tabela.grid_rowconfigure(0, weight=1)
        frame_tabela.grid_columnconfigure(0, weight=1)

        # =========================
        # CORES POR GRAVIDADE
        # =========================
        tabela.tag_configure(
            "emergencia",
            background="#5c2020",
            foreground="#ffffff"
        )

        tabela.tag_configure(
            "aviso",
            background="#59421d",
            foreground="#ffffff"
        )

        tabela.tag_configure(
            "normal",
            background="#2d3e35",
            foreground="#ffffff"
        )

        # Busca os registros existentes no banco
        dados_logs = self.controller.listar_logs_alerta()

        for log in dados_logs:
            # Esperado: (id, tipo_evento, descricao, timestamp)
            id_log, experimento_id, tipo_evento, descricao, timestamp = log

            tipo = str(tipo_evento).upper()

            if "EMERGENCIA" in tipo or "EMERGÊNCIA" in tipo or "CRITIC" in tipo:
                gravidade = "emergencia"
            elif "AVISO" in tipo or "ALERTA" in tipo or "WARNING" in tipo:
                gravidade = "aviso"
            else:
                gravidade = "normal"

            tabela.insert(
                "",
                "end",
                values=(id_log, tipo_evento, descricao, timestamp),
                tags=(gravidade,)
            )

        # =========================
        # RODAPÉ
        # =========================
        frame_rodape = ctk.CTkFrame(
            janela_logs,
            fg_color="transparent"
        )
        frame_rodape.pack(fill="x", padx=15, pady=(0, 12))

        total_logs = len(dados_logs)

        lbl_total = ctk.CTkLabel(
            frame_rodape,
            text=f"Total de registros: {total_logs}",
            font=ctk.CTkFont(size=12),
            text_color="#b0b0b0"
        )
        lbl_total.pack(side="left", padx=5)

        btn_fechar = ctk.CTkButton(
            frame_rodape,
            text="Fechar",
            width=120,
            height=36,
            fg_color="#444444",
            hover_color="#5a5a5a",
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=janela_logs.destroy
        )
        btn_fechar.pack(side="right", padx=5)
