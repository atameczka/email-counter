import tkinter as tk

from gui import EmailCounterApp


def main():
    window = tk.Tk()
    app = EmailCounterApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()