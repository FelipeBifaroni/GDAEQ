import customtkinter as ctk
from views.main_view import MainView
from models.schema import criar_banco_e_tabelas


criar_banco_e_tabelas()
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


if __name__ == "__main__":
    app = MainView()

    def fechar_aplicacao():
        try:
            # Fecha figuras do Matplotlib
            import matplotlib.pyplot as plt
            plt.close("all")
        finally:
            app.destroy()

    app.protocol("WM_DELETE_WINDOW", fechar_aplicacao)
    app.mainloop()