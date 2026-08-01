import sys
import tkinter as tk

from gui import EmailCounterApp


def main() -> int:
    window = tk.Tk()
    EmailCounterApp(window)
    window.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
