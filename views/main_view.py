from datetime import datetime
from tkinter import messagebox, filedialog
import customtkinter as ctk
from views.componentes.painel_parametros import PainelParametros
from views.componentes.dashboard_gui import DashboardGUI
from controllers.sensor_controller import SensorController
from controllers.experimento_controller import ExperimentoController

class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Monitoramento e Gêmeo Digital - Reator Químico")
        self.geometry("1380x800")
        self.minsize(1100, 650)

        self.sensor_controller = SensorController()
        self.controller = ExperimentoController()
        self.controller.view = self

        self.substancias_predefinidas = {
            "Nitrato de Amônio (NH4NO3 - Endotérmica)": {"nome": "Nitrato de Amônio", "formula": "NH4NO3", "estado": "Sólido", "massa_molar": 80.04, "entalpia": 25.7},
            "Hidróxido de Sódio (NaOH - Exotérmica)": {"nome": "Hidróxido de Sódio", "formula": "NaOH", "estado": "Sólido", "massa_molar": 39.99, "entalpia": -44.51},
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.painel_esq = PainelParametros(self, self.substancias_predefinidas, lambda s: None)
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

    def _iniciar_ensaio(self):
        try:
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
        cor = "orange" if novo_status == "Pausado" else "lightgreen"
        self.lbl_estado.configure(text=f"ESTADO: {novo_status.upper()}", text_color=cor)

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
        # (Certifique-se de que o nome 'txt_temp_inicial' corresponde ao atributo no seu PainelParametros)
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

            # 2. Atualiza a barra de status e o campo de descrição
            self.lbl_estado.configure(text="ESTADO: HISTÓRICO CARREGADO", text_color="cyan")

            self.txt_exp_desc.delete("1.0", "end")
            self.txt_exp_desc.insert("1.0", self.controller.experimento.descricao or "")

            # 3. Preenche a barra lateral esquerda com os dados recuperados do banco
            exp = self.controller.experimento
            param = exp.parametro_simulacao
            subst_obj = exp.experimento_substancia.substancia if exp.experimento_substancia else None

            dados_formulario = {
                "nome_exp": exp.nome,
                "professor": exp.professor.nome if exp.professor else "",
                "turma": exp.turma.nome if exp.turma else "",
                "subst_nome": subst_obj.nome if subst_obj else "",
                "subst_formula": subst_obj.formula if subst_obj else "",
                "massa_molar": subst_obj.massa_molar if subst_obj else 0.0,
                "massa_reagente": param.massa_inicial_a if param else 0.0,
                "entalpia": subst_obj.entalpia_formacao if subst_obj else 0.0,
                "temp_ini": param.temp_inicial if param else 25.0,
                "massa_total": param.massa_total if param else 100.0,
                "porta_com": "COM3"
            }
            self.painel_esq.preencher_formulario(dados_formulario)

            if param:
                delta_t_estimado = (
                            exp.dados_grafico[-1].temp_simulada - param.temp_inicial) if exp.dados_grafico else 0.0
                self.lbl_delta_t.configure(text=f"ΔT Teórico/Real: {delta_t_estimado:.2f} °C")

            # 4. Ajusta estados dos botões
            self.painel_esq.btn_iniciar.configure(state="normal")
            self.painel_esq.btn_pausar.configure(state="disabled")
            self.painel_esq.btn_parar.configure(state="disabled")

            janela.destroy()
            messagebox.showinfo("Sucesso", f"Experimento #{experimento_id} carregado com sucesso!")
        else:
            messagebox.showerror("Erro", "Não foi possível carregar os dados deste experimento.")

    def _loop_telemetria(self):
        try:
            ponto = self.controller.obter_proximo_ponto()
            if ponto:
                self.lbl_temp_real.configure(text=f"Temp. Real: {ponto['temp_real']:.2f} °C")
                self.lbl_temp_sim.configure(text=f"Gêmeo Digital: {ponto['temp_simulada']:.2f} °C")

                if "status" in ponto and ponto["status"]:
                    status_atual = ponto["status"]
                    if status_atual == "Reagindo":
                        self.lbl_estado.configure(text="ESTADO: REAGINDO", text_color="lightgreen")
                    elif status_atual == "Finalizado":
                        self.lbl_estado.configure(text="ESTADO: FINALIZADO", text_color="cyan")
                        self.painel_esq.btn_iniciar.configure(state="normal")
                        self.painel_esq.btn_pausar.configure(state="disabled")
                        self.painel_esq.btn_parar.configure(state="disabled")

                if ponto.get("dado_obj"):
                    self.dashboard_gui.renderizar_ponto(ponto["dado_obj"])

        except Exception as e:
            erro_str = str(e)
            print(f"⚠️ Erro capturado no loop de telemetria: {erro_str}")

            # 🔴 SE O ERRO FOR DA TRIGGER DE SEGURANÇA, MUDA IMEDIATAMENTE A INTERFACE
            if "fora da faixa operacional" in erro_str:
                self.acionar_emergencia_visual()

        self.after(1000, self._loop_telemetria)

    def acionar_emergencia_visual(self):
        """Atualiza a interface para o estado crítico de emergência detetado pelo banco/trigger."""
        self.lbl_estado.configure(text="ESTADO: EMERGÊNCIA", text_color="red")
        self.painel_esq.btn_iniciar.configure(state="normal")
        self.painel_esq.btn_pausar.configure(state="disabled")
        self.painel_esq.btn_parar.configure(state="disabled")

