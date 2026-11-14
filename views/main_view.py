import webbrowser
from urllib.parse import urlencode
from tkinter import messagebox, filedialog
import customtkinter as ctk
from views.componentes.painel_parametros import PainelParametros
from views.componentes.dashboard_gui import DashboardGUI
from controllers.sensor_controller import SensorController
from controllers.experimento_controller import ExperimentoController
from controllers.backup_controller import BackupController
from tkinter import ttk
import os
import tempfile
from datetime import datetime


class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Monitoramento e Gêmeo Digital - Reator Químico")
        self.geometry("1380x800")
        self.minsize(1100, 650)

        self.controller = ExperimentoController()
        self.sensor_controller = SensorController(self.controller)
        self.backup_controller = BackupController()

        self.substancias = self.controller.listar_substancias()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.painel_esq = PainelParametros(
            self,
            self.substancias,
            lambda s: None,
            cmd_historico=self._abrir_historico,
            cmd_excel=self._exportar_excel,
            cmd_logs=self._abrir_janela_logs
        )
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

        # Backup
        self.btn_backup = ctk.CTkButton(
            self.frame_status,
            text="💾 Backup",
            width=100,
            height=32,
            fg_color="#1F6AA5",
            hover_color="#144870",
            command=self._abrir_opcoes_backup
        )
        self.btn_backup.pack(side="right", padx=5, pady=5)

        # Restaurar backup
        self.btn_restaurar = ctk.CTkButton(
            self.frame_status,
            text="📂 Restaurar",
            width=110,
            height=32,
            fg_color="#238636",
            hover_color="#19692c",
            command=self._restaurar_backup
        )
        self.btn_restaurar.pack(side="right", padx=5, pady=5)

        # Contato
        self.btn_fale_conosco = ctk.CTkButton(
            self.frame_status,
            text="✉ Fale Conosco",
            width=130,
            height=32,
            fg_color="#555555",
            hover_color="#3d3d3d",
            command=self._abrir_fale_conosco
        )
        self.btn_fale_conosco.pack(side="right", padx=5, pady=5)

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
        self.painel_esq.btn_excluir_substancia.configure(
            command=self._confirmar_e_excluir_substancia
        )

    def _confirmar_e_excluir_substancia(self):
        substancia_id = self.painel_esq.substancia_selecionada_id

        if substancia_id is None:
            messagebox.showwarning(
                "Atenção",
                "Selecione uma substância para excluir."
            )
            return

        nome = self.painel_esq.txt_subst_nome.get().strip()

        confirmar = messagebox.askyesno(
            "Confirmar exclusão",
            f"Tem certeza que deseja excluir a substância '{nome}'?\n\n"
            "Essa ação não poderá ser desfeita."
        )

        if not confirmar:
            return

        try:
            self.controller.excluir_substancia(substancia_id)

            # Atualiza a lista de substâncias
            substancias = self.controller.listar_substancias()
            self.painel_esq.atualizar_lista_substancias(substancias)



            messagebox.showinfo(
                "Sucesso",
                f"A substância '{nome}' foi excluída com sucesso."
            )

        except ValueError as e:
            messagebox.showwarning("Não foi possível excluir", str(e))

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Não foi possível excluir a substância:\n{str(e)}"
            )

    def _iniciar_ensaio(self):
        if self.painel_esq.btn_iniciar.cget("text") == "✨ Novo Experimento":
            self._novo_experimento()
            return
        try:
            self.painel_esq.liberar_parametros_fisicos()
            dados = self.painel_esq.obter_dados_formulario()

            dados["substancia_id"] = self.painel_esq.substancia_selecionada_id
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
            self.painel_esq.atualizar_lista_substancias(
                self.controller.listar_substancias()
            )

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

    def _abrir_fale_conosco(self):
        """Abre o formulário de contato da equipe GDAEQ."""

        janela = ctk.CTkToplevel(self)
        janela.title("Fale Conosco - GDAEQ")
        janela.geometry("500x590")
        janela.resizable(False, False)
        janela.transient(self)
        janela.grab_set()

        # Cabeçalho
        ctk.CTkLabel(
            janela,
            text="✉ Fale Conosco",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(25, 5))

        ctk.CTkLabel(
            janela,
            text="Envie suas dúvidas, sugestões ou relate um problema.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(pady=(0, 20))

        # Tipo de mensagem
        ctk.CTkLabel(
            janela,
            text="Tipo de mensagem:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=30, pady=(5, 5))

        combo_tipo = ctk.CTkComboBox(
            janela,
            values=["Dúvida", "Sugestão", "Relatar problema"],
            width=440,
            state="readonly"
        )
        combo_tipo.pack(padx=30, pady=(0, 12))
        combo_tipo.set("Dúvida")

        # Nome
        ctk.CTkLabel(
            janela,
            text="Seu nome:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=30, pady=(5, 5))

        entrada_nome = ctk.CTkEntry(
            janela,
            placeholder_text="Digite seu nome",
            width=440
        )
        entrada_nome.pack(padx=30, pady=(0, 12))

        # E-mail
        ctk.CTkLabel(
            janela,
            text="Seu e-mail:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=30, pady=(5, 5))

        entrada_email = ctk.CTkEntry(
            janela,
            placeholder_text="seuemail@exemplo.com",
            width=440
        )
        entrada_email.pack(padx=30, pady=(0, 12))

        # Mensagem
        ctk.CTkLabel(
            janela,
            text="Mensagem:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=30, pady=(5, 5))

        campo_mensagem = ctk.CTkTextbox(
            janela,
            width=440,
            height=120
        )
        campo_mensagem.pack(padx=30, pady=(0, 15))

        def enviar_mensagem():
            nome = entrada_nome.get().strip()
            email = entrada_email.get().strip()
            tipo = combo_tipo.get()
            mensagem = campo_mensagem.get("1.0", "end-1c").strip()

            if not nome or not email or not mensagem:
                messagebox.showwarning(
                    "Campos obrigatórios",
                    "Preencha seu nome, e-mail e mensagem.",
                    parent=janela
                )
                return

            if "@" not in email or "." not in email.split("@")[-1]:
                messagebox.showwarning(
                    "E-mail inválido",
                    "Informe um endereço de e-mail válido.",
                    parent=janela
                )
                return

            destinatario = "gdaeqoficial@gmail.com"

            assunto = f"[GDAEQ] {tipo}"

            corpo = (
                f"Tipo de mensagem: {tipo}\n\n"
                f"Nome: {nome}\n"
                f"E-mail para resposta: {email}\n\n"
                f"Mensagem:\n{mensagem}"
            )

            parametros = urlencode({
                "subject": assunto,
                "body": corpo
            })

            link_email = f"mailto:{destinatario}?{parametros}"

            try:
                abriu = webbrowser.open(link_email)

                if abriu:
                    messagebox.showinfo(
                        "Mensagem preparada",
                        "Seu programa de e-mail foi aberto com a mensagem "
                        "preenchida.\n\nRevise e clique em Enviar para "
                        "concluir o envio.",
                        parent=janela
                    )
                    janela.destroy()
                else:
                    messagebox.showerror(
                        "Erro",
                        "Não foi possível abrir o programa de e-mail. "
                        "Verifique se existe um aplicativo de e-mail "
                        "configurado no computador.",
                        parent=janela
                    )

            except Exception as erro:
                messagebox.showerror(
                    "Erro ao preparar mensagem",
                    f"Não foi possível abrir o e-mail:\n{erro}",
                    parent=janela
                )

        # Botão enviar
        ctk.CTkButton(
            janela,
            text="✉ Preparar e-mail",
            width=440,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=enviar_mensagem
        ).pack(padx=30, pady=(5, 20))

        # Rodapé
        ctk.CTkLabel(
            janela,
            text="Equipe GDAEQ | gdaeqoficial@gmail.com",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(0, 10))

    def _fazer_backup(self):
        caminho = filedialog.asksaveasfilename(
            title="Salvar backup do GDAEQ",
            defaultextension=".db",
            filetypes=[("Banco de dados SQLite", "*.db")],
            initialfile="Backup_GDAEQ.db"
        )

        if not caminho:
            return

        try:
            arquivo = self.backup_controller.fazer_backup(caminho)

            messagebox.showinfo(
                "Backup concluído",
                f"Backup salvo com sucesso!\n\nLocal:\n{arquivo}"
            )

        except Exception as e:
            messagebox.showerror(
                "Erro no backup",
                f"Não foi possível criar o backup:\n{e}"
            )

        def _restaurar_backup(self):
            # Impede a restauração durante um experimento em execução
            if self.controller.executando:
                messagebox.showwarning(
                    "Experimento em andamento",
                    "Finalize ou interrompa o experimento antes de restaurar um backup."
                )
                return

            caminho = filedialog.askopenfilename(
                title="Selecionar backup do GDAEQ",
                filetypes=[("Banco de dados SQLite", "*.db")]
            )

            if not caminho:
                return

            confirmar = messagebox.askyesno(
                "Confirmar restauração",
                "A restauração substituirá os dados atuais pelos dados do backup.\n\n"
                "Uma cópia de segurança do banco atual será criada antes da substituição.\n\n"
                "Deseja continuar?"
            )

            if not confirmar:
                return

            try:
                self.backup_controller.restaurar_backup(caminho)

                messagebox.showinfo(
                    "Restauração concluída",
                    "O backup foi restaurado com sucesso!\n\n"
                    "Feche e abra novamente o GDAEQ para carregar os dados restaurados."
                )

            except Exception as e:
                messagebox.showerror(
                    "Erro na restauração",
                    f"Não foi possível restaurar o backup:\n{e}"
                )

    def _restaurar_backup(self):
        # Impede a restauração durante um experimento em execução
        if self.controller.executando:
            messagebox.showwarning(
                "Experimento em andamento",
                "Finalize ou interrompa o experimento antes de restaurar um backup."
            )
            return

        caminho = filedialog.askopenfilename(
            title="Selecionar backup do GDAEQ",
            filetypes=[("Banco de dados SQLite", "*.db")]
        )

        if not caminho:
            return

        confirmar = messagebox.askyesno(
            "Confirmar restauração",
            "A restauração substituirá os dados atuais pelos dados do backup.\n\n"
            "Uma cópia de segurança do banco atual será criada antes da substituição.\n\n"
            "Deseja continuar?"
        )

        if not confirmar:
            return

        try:
            self.backup_controller.restaurar_backup(caminho)

            messagebox.showinfo(
                "Restauração concluída",
                "O backup foi restaurado com sucesso!\n\n"
                "Feche e abra novamente o GDAEQ para carregar os dados restaurados."
            )

        except Exception as e:
            messagebox.showerror(
                "Erro na restauração",
                f"Não foi possível restaurar o backup:\n{e}"
            )

    def _abrir_opcoes_backup(self):
        """Exibe as opções para salvar ou enviar um backup."""

        janela = ctk.CTkToplevel(self)
        janela.title("Backup do GDAEQ")
        janela.geometry("430x300")
        janela.resizable(False, False)
        janela.transient(self)
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="💾 Backup do GDAEQ",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(22, 5))

        ctk.CTkLabel(
            janela,
            text="Escolha como deseja guardar seus dados.",
            text_color="gray"
        ).pack(pady=(0, 15))

        entrada_email = ctk.CTkEntry(
            janela,
            width=360,
            placeholder_text="E-mail de destino (para envio)"
        )
        entrada_email.pack(pady=(0, 15))

        def enviar_backup():
            email = entrada_email.get().strip()

            if not email or "@" not in email or "." not in email.split("@")[-1]:
                messagebox.showwarning(
                    "E-mail inválido",
                    "Informe um endereço de e-mail válido.",
                    parent=janela
                )
                return

            try:
                # Gera o backup na pasta temporária do computador
                from pathlib import Path

                pasta_backup = Path.home() / ".gdaeq"
                pasta_backup.mkdir(parents=True, exist_ok=True)

                nome_arquivo = (
                    f"Backup_GDAEQ_{datetime.now():%Y%m%d_%H%M%S}.db"
                )

                caminho = pasta_backup / nome_arquivo

                arquivo = self.backup_controller.fazer_backup(str(caminho))

                assunto = "[GDAEQ] Backup do banco de dados"
                corpo = (
                    "Olá!\n\n"
                    "Estou enviando o backup do banco de dados do GDAEQ.\n\n"
                    "O arquivo de backup deve ser anexado a este e-mail.\n\n"
                    "Atenciosamente."
                )

                parametros = urlencode({
                    "subject": assunto,
                    "body": corpo
                })

                link_email = f"mailto:{email}?{parametros}"

                abriu = webbrowser.open(link_email)

                # Abre a pasta onde o backup foi salvo
                os.startfile(str(pasta_backup))

                janela.destroy()

                if abriu:
                    messagebox.showinfo(
                        "E-mail preparado",
                        "O backup foi gerado com sucesso!\n\n"
                        "O programa de e-mail foi solicitado para abertura.\n\n"
                        "O que fazer agora:\n"
                        "1. Verifique se o e-mail abriu.\n"
                        "2. Caso necessário, entre na sua conta.\n"
                        "3. Anexe o arquivo de backup.\n"
                        "4. Clique em Enviar.\n\n"
                        f"Local do backup:\n{arquivo}\n\n"
                        "Atenção: o GDAEQ não consegue confirmar "
                        "se o e-mail foi enviado."
                    )
                else:
                    messagebox.showwarning(
                        "E-mail não aberto",
                        "O backup foi gerado, mas não foi possível "
                        "solicitar a abertura do programa de e-mail.\n\n"
                        "Verifique se existe um programa de e-mail "
                        "configurado no computador.\n\n"
                        f"O backup está salvo em:\n{arquivo}"
                    )

            except Exception as e:
                messagebox.showerror(
                    "Erro",
                    f"Não foi possível preparar o backup:\n{e}",
                    parent=janela
                )

        # Salvar no computador
        ctk.CTkButton(
            janela,
            text="💾 Salvar no computador",
            width=360,
            height=40,
            fg_color="#1F6AA5",
            hover_color="#144870",
            command=lambda: (janela.destroy(), self._fazer_backup())
        ).pack(pady=5)

        # Enviar por e-mail
        ctk.CTkButton(
            janela,
            text="✉ Preparar envio por e-mail",
            width=360,
            height=40,
            fg_color="#238636",
            hover_color="#19692c",
            command=enviar_backup
        ).pack(pady=5)
