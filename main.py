"""точка входа. Запускайте этот файл в PyCharm."""

import tkinter as tk

from application import Application


def main() -> None:
    root = tk.Tk()
    Application(root)
    root.mainloop()


if __name__ == '__main__':
    main()
