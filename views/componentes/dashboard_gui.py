import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DashboardGUI:
    def __init__(self, master_frame):
        self.master_frame = master_frame
        self.fig, self.ax = plt.subplots(figsize=(6, 4), facecolor="#2b2b2b")
        self.ax.set_facecolor("#1e1e1e")
        self.ax.tick_params(colors="white")
        self.ax.xaxis.label.set_color("white")
        self.ax.yaxis.label.set_color("white")
        self.ax.title.set_color("white")
        self.ax.set_title("Curva de Temperatura (°C) vs Tempo (s)")
        self.ax.set_xlabel("Tempo (s)")
        self.ax.set_ylabel("Temperatura (°C)")
        self.ax.grid(True, color="gray", linestyle="--", alpha=0.5)

        # 1. Cria as linhas vazias UMA ÚNICA VEZ no construtor
        self.linha_real, = self.ax.plot([], [], label="Sensor Físico (Arduino)", color="#00ffff", linewidth=2)
        self.linha_sim, = self.ax.plot([], [], label="Gêmeo Digital (Simulado)", color="#ff007f", linestyle="--",
                                       linewidth=2)

        # Adiciona legenda fixa
        self.ax.legend(loc="upper left", facecolor="#2b2b2b", edgecolor="none", labelcolor="white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.eixo_x = []
        self.eixo_y_real = []
        self.eixo_y_sim = []

    def renderizar_ponto(self, dado) -> None:
        self.eixo_x.append(dado.tempo)
        self.eixo_y_real.append(dado.temp_real)
        self.eixo_y_sim.append(dado.temp_simulada)

        self.linha_real.set_xdata(self.eixo_x)
        self.linha_real.set_ydata(self.eixo_y_real)

        self.linha_sim.set_xdata(self.eixo_x)
        self.linha_sim.set_ydata(self.eixo_y_sim)

        self.ax.relim()
        self.ax.autoscale_view()

        # 4. Redesenha o canvas com os novos pontos
        self.canvas.draw()

    def limpar(self):
        self.eixo_x.clear()
        self.eixo_y_real.clear()
        self.eixo_y_sim.clear()

        # Limpa os dados das linhas para zerar o gráfico visualmente
        self.linha_real.set_xdata([])
        self.linha_real.set_ydata([])
        self.linha_sim.set_xdata([])
        self.linha_sim.set_ydata([])

        self.canvas.draw()