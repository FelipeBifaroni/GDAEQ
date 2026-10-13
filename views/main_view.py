from datetime import datetime
from tkinter import messagebox, filedialog
import customtkinter as ctk
from views.componentes.painel_parametros import PainelParametros
from views.componentes.dashboard_gui import DashboardGUI
from controllers.sensor_controller import SensorController
from controllers.experimento_controller import ExperimentoController
from tkinter import ttk
from models.log_repository import LogRepository

class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Monitoramento e Gêmeo Digital - Reator Químico")
        self.geometry("1380x800")
        self.minsize(1100, 650)

        self.sensor_controller = SensorController()
        self.controller = ExperimentoController()

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

        self.after(1000, self._loop_telemetria)

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
            self.lbl_delta_t.configure(text=f"ΔT Teórico: {delta_t:.2f} °C")
            self.lbl_estado.configure(text="ESTADO: REAGINDO", text_color="lightgreen")

            self.painel_esq.btn_iniciar.configure(state="disabled")
            self.painel_esq.btn_pausar.configure(state="normal")
            self.painel_esq.btn_parar.configure(state="normal")
            self.dashboard_gui.limpar()

        except Exception as e:
            messagebox.showerror("Erro ao Iniciar", f"Verifique os campos inseridos:\n{str(e)}")

    def _pausar_ensaio(self):
        novo_status = self.controller.pausar_ensaio()

        if novo_status == "Pausado":
            self.lbl_estado.configure(text="ESTADO: PAUSADO", text_color="orange")
            # Muda o texto do botão para indicar que agora ele serve para retomar
            self.painel_esq.btn_pausar.configure(text="Retomar", fg_color="#b28f00", hover_color="#8c7000")
        else:
            self.lbl_estado.configure(text="ESTADO: REAGINDO", text_color="lightgreen")
            # Retorna o botão ao estado normal de pausa
            self.painel_esq.btn_pausar.configure(text="Pausar", fg_color="orange", hover_color="#cc8400")

    def _interromper_emergencia(self):
        self.controller.interromper_emergencia()
        self.lbl_estado.configure(text="ESTADO: EMERGÊNCIA", text_color="red")
        self.painel_esq.btn_iniciar.configure(state="normal")
        self.painel_esq.btn_pausar.configure(state="disabled")
        self.painel_esq.btn_parar.configure(state="disabled")

    def _calibrar_sensores(self):
        """Executa a tara/calibração e preenche automaticamente o campo de Temp. Inicial."""
        porta = self.painel_esq.txt_porta_com.get()

        # 1. Executa a calibração e obtém a temperatura real lida pelo sensor
        temp_lida = self.sensor_controller.calibrar_sensores(porta_com=porta)

        # 2. Insere o valor automaticamente no campo de Temperatura Inicial do painel
        self.painel_esq.txt_temp_ini.delete(0, "end")
        self.painel_esq.txt_temp_ini.insert(0, f"{temp_lida:.2f}")

        messagebox.showinfo(
            "Calibração Concluída",
            f"Tara realizada com sucesso!\nTemperatura inicial capturada: {temp_lida:.2f}°C"
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
        janela_hist.geometry("780x500")
        janela_hist.grab_set()

        ctk.CTkLabel(janela_hist, text="Experimentos Gravados no Banco de Dados",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)

        # Cabeçalho da Tabela
        header_frame = ctk.CTkFrame(janela_hist, fg_color="gray25", height=35)
        header_frame.pack(padx=20, pady=(0, 5), fill="x")

        ctk.CTkLabel(header_frame, text="ID", width=40, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Nome do Ensaio", width=240, anchor="w", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Data", width=130, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Ação", width=120, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=10)

        # Área Scrollável corrigida
        frame_lista = ctk.CTkScrollableFrame(janela_hist, width=720, height=340)
        frame_lista.pack(padx=20, pady=5, fill="both", expand=True)

        historico = self.controller.listar_historico_banco()
        if not historico:
            ctk.CTkLabel(frame_lista, text="Nenhum experimento encontrado.", text_color="gray").pack(pady=20)
            return

        for exp in historico:
            item_frame = ctk.CTkFrame(frame_lista, fg_color="gray17", corner_radius=6)
            item_frame.pack(fill="x", pady=4, ipady=4)

            ctk.CTkLabel(item_frame, text=str(exp["id"]), width=40).pack(side="left", padx=5)
            ctk.CTkLabel(item_frame, text=exp["nome"], width=240, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(item_frame, text=str(exp["data"]), width=130).pack(side="left", padx=5)

            # --- BOTÃO DE EXCLUIR COM CONFIRMAÇÃO ---
            btn_excluir = ctk.CTkButton(
                item_frame, text="🗑️ Excluir", width=90, fg_color="#a83232", hover_color="#7a2222",
                command=lambda eid=exp["id"], nome=exp["nome"], j_hist=janela_hist: self._confirmar_e_excluir(eid, nome,
                                                                                                              j_hist)
            )
            btn_excluir.pack(side="right", padx=5)

            # Botão para carregar o experimento selecionado
            btn_carregar = ctk.CTkButton(
                item_frame, text="📂 Carregar", width=100, fg_color="#1f538d",
                command=lambda eid=exp["id"]: self._carregar_e_fechar_historico(eid, janela_hist)
            )
            btn_carregar.pack(side="right", padx=10)

    def _carregar_e_fechar_historico(self, experimento_id, janela):
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

            self.painel_esq.bloquear_parametros_fisicos()

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
        """Exibe um aviso de confirmação antes de excluir permanentemente o experimento."""
        resposta = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o experimento #{experimento_id} ('{nome_ensaio}')?\n\nEsta ação não pode ser desfeita!",
            icon="warning"
        )

        if resposta:
            sucesso = self.controller.excluir_experimento(experimento_id)
            if sucesso:
                messagebox.showinfo("Sucesso", f"Experimento #{experimento_id} excluído com sucesso.")
                janela_historico.destroy()
                self._abrir_historico()  # Reabre a janela de histórico atualizada
            else:
                messagebox.showerror("Erro", "Não foi possível excluir o experimento do banco de dados.")

    def _loop_telemetria(self):
        try:
            ponto = self.controller.obter_proximo_ponto()
            if ponto:
                self.lbl_temp_real.configure(text=f"Temp. Real: {ponto['temp_real']:.2f} °C")
                self.lbl_temp_sim.configure(text=f"Gêmeo Digital: {ponto['temp_simulada']:.2f} °C")

                status_atual = ponto.get("status", "")
                if status_atual == "Reagindo":
                    self.lbl_estado.configure(text="ESTADO: REAGINDO", text_color="lightgreen")
                elif status_atual == "Finalizado":
                    self.lbl_estado.configure(text="ESTADO: FINALIZADO", text_color="cyan")
                    self.painel_esq.btn_iniciar.configure(state="normal")
                    self.painel_esq.btn_pausar.configure(state="disabled")
                    self.painel_esq.btn_parar.configure(state="disabled")
                elif status_atual == "Emergência":
                    # Tratamento reativo limpo feito diretamente na View
                    self.acionar_emergencia_visual()

                if ponto.get("dado_obj"):
                    self.dashboard_gui.renderizar_ponto(ponto["dado_obj"])

        except Exception as e:
            print(f"⚠️ Erro capturado no loop de telemetria: {e}")

        self.after(1000, self._loop_telemetria)

    def acionar_emergencia_visual(self):
        """Atualiza a interface para o estado crítico de emergência e exibe um alerta visual."""
        # 1. Muda a cor e o texto do rótulo de status (ajuste o nome do seu widget se for diferente)
        self.lbl_estado.configure(text="ESTADO: EMERGÊNCIA", text_color="red")

        # 2. Controla os botões do painel lateral (ex: libera o iniciar, desativa pausar/parar)
        if hasattr(self, 'painel_esq'):
            self.painel_esq.btn_iniciar.configure(state="normal")
            self.painel_esq.btn_pausar.configure(state="disabled")
            self.painel_esq.btn_parar.configure(state="disabled")

        # 3. Exibe o pop-up de aviso na tela para o usuário
        messagebox.showwarning(
            "⚠️ Alerta de Emergência",
            "Temperatura fora da faixa segura (0°C a 100°C)! O experimento foi interrompido."
        )

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
        self.controller.experimento_id_db = None

        # Libera os campos físicos e o botão de tara que estavam bloqueados pelo histórico
        self.painel_esq.liberar_parametros_fisicos()

        # Limpa os campos do formulário
        campos_vazios = {
            "nome_exp": "", "professor": "", "turma": "",
            "subst_nome": "", "subst_formula": "",
            "massa_molar": "", "massa_reagente": "",
            "entalpia": "", "temp_ini": "", "massa_total": "",
            "porta_com": "COM3", "descricao": ""
        }
        self.painel_esq.preencher_formulario(campos_vazios)
        self.txt_exp_desc.delete("1.0", "end")

        # Limpa gráfico e status
        self.dashboard_gui.limpar()
        self.lbl_estado.configure(text="ESTADO: INATIVO", text_color="lightblue")
        self.lbl_delta_t.configure(text="ΔT Teórico: -- °C", text_color="yellow")
        self.lbl_temp_real.configure(text="Temp. Real: -- °C")
        self.lbl_temp_sim.configure(text="Gêmeo Digital: -- °C")

        # Restaura o botão de Iniciar ao estado original (VERDE)
        self.painel_esq.btn_iniciar.configure(
            text="Iniciar",
            fg_color="green",
            hover_color="#134f13",
            state="normal"
        )
        self.painel_esq.btn_pausar.configure(state="disabled")
        self.painel_esq.btn_parar.configure(state="disabled")

        messagebox.showinfo("Novo Ensaio", "Ambiente limpo! Insira os dados para iniciar um novo experimento.")

    def _abrir_janela_logs(self):
        """Abre uma janela pop-up estilizada com a tabela de logs de alerta."""
        janela_logs = ctk.CTkToplevel(self)
        janela_logs.title("Histórico de Alertas e Emergências")
        janela_logs.geometry("650x400")
        janela_logs.grab_set()  # Mantém o foco na janela

        # Título da janela
        lbl_titulo = ctk.CTkLabel(janela_logs, text="📋 Registros de Alerta do Sistema",
                                  font=ctk.CTkFont(size=16, weight="bold"))
        lbl_titulo.pack(pady=10)

        # Configuração da Tabela (Treeview)
        colunas = ("ID", "Tipo de Evento", "Descrição", "Horário")
        tabela = ttk.Treeview(janela_logs, columns=colunas, show="headings", height=12)

        tabela.heading("ID", text="ID")
        tabela.heading("Tipo de Evento", text="Tipo de Evento")
        tabela.heading("Descrição", text="Descrição do Ocorrido")
        tabela.heading("Horário", text="Horário")

        tabela.column("ID", width=40, anchor="center")
        tabela.column("Tipo de Evento", width=140, anchor="center")
        tabela.column("Descrição", width=300, anchor="w")
        tabela.column("Horário", width=130, anchor="center")

        # Puxa os dados do banco e insere na tabela
        dados_logs = LogRepository.listar_todos()
        for log in dados_logs:
            tabela.insert("", "end", values=log)

        tabela.pack(pady=10, padx=10, fill="both", expand=True)

        # Botão para fechar
        btn_fechar = ctk.CTkButton(janela_logs, text="Fechar", fg_color="gray40", command=janela_logs.destroy)
        btn_fechar.pack(pady=10)