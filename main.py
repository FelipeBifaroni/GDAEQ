import customtkinter as ctk
from views.main_view import MainView

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    app = MainView()
    app.mainloop()