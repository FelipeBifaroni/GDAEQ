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

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.eixo_x = []
        self.eixo_y_real = []
        self.eixo_y_sim = []

    def renderizar_ponto(self, dado) -> None:
        self.eixo_x.append(dado.tempo)
        self.eixo_y_real.append(dado.temp_real)
        self.eixo_y_sim.append(dado.temp_simulada)

        self.ax.clear()
        self.ax.set_facecolor("#1e1e1e")
        self.ax.grid(True, color="gray", linestyle="--", alpha=0.5)
        self.ax.plot(self.eixo_x, self.eixo_y_real, label="Sensor Físico (Arduino)", color="#00ffff", linewidth=2)
        self.ax.plot(self.eixo_x, self.eixo_y_sim, label="Gêmeo Digital (Simulado)", color="#ff007f", linestyle="--", linewidth=2)
        self.ax.set_title("Curva de Temperatura (°C) vs Tempo (s)", color="white")
        self.ax.tick_params(colors="white")
        self.ax.legend(loc="upper left", facecolor="#2b2b2b", edgecolor="none", labelcolor="white")
        self.canvas.draw()

    def limpar(self):
        self.eixo_x.clear()
        self.eixo_y_real.clear()
        self.eixo_y_sim.clear()
        self.ax.clear()
        self.canvas.draw()