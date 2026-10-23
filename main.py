"""
INICIALIZADOR DO APLICATIVO (versão Qt / PySide6)

Uso:   python main.py
"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from config.inicializar import inicializar_pastas
from view.estilo import aplicar_estilo
from view.app import ComicManagerApp


def main():
    inicializar_pastas()
    if sys.platform == "win32":
        import ctypes

        myappid = "letquadrinhos.comic.2.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(r"C:\Emulador\LetQuadrinhos_Qt\assets\icone.ico"))
    aplicar_estilo(app)

    try:
        janela = ComicManagerApp()
        janela.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n[INFO] Aplicação encerrada pelo usuário.")


if __name__ == "__main__":
    main()