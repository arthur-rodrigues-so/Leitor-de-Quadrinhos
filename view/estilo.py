"""
==============================================================================
 ESTILOS
==============================================================================
"""
import os

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from config.constantes import (
    BG_APP, BG_CARD, BG_INPUT, BG_INPUT_HOV, BORDER,
    ACCENT, TEXT, TEXT_MUTED, FONT_FAMILY,
)
from config.inicializar import caminho_absoluto_pasta_executando

# Fundo das janelas de diálogo 
BG_MODAL = "#1c1d24"

# Cor de texto padrão dos widgets "comuns"
TEXTO_PADRAO = "#dce4ee"
TEXTO_DESABILITADO = "#6b7080"

# Cor padrão dos botões nos diálogos
BTN_PADRAO = "#1f6aa5"
BTN_PADRAO_HOVER = "#144870"

FAMILIA_PADRAO = "Roboto"

FAMILIA_SIDEBAR = FONT_FAMILY


def carregar_fontes() -> str:
    """Registra as fontes Roboto de assets/fonts. Devolve a família padrão a usar."""
    global FAMILIA_PADRAO
    pasta = caminho_absoluto_pasta_executando(os.path.join("assets", "fonts"))
    for arquivo in ("Roboto-Regular.ttf", "Roboto-Medium.ttf"):
        caminho = os.path.join(pasta, arquivo)
        if os.path.exists(caminho):
            QFontDatabase.addApplicationFont(caminho)
    if "Roboto" not in QFontDatabase.families():
        FAMILIA_PADRAO = FAMILIA_SIDEBAR
    return FAMILIA_PADRAO


def cor_texto(widget, cor: str) -> None:
    """Muda a cor do texto de um QLabel pela paleta (bem mais leve que um QSS por widget)."""
    paleta = widget.palette()
    paleta.setColor(QPalette.ColorRole.WindowText, QColor(cor))
    widget.setPalette(paleta)


def fonte(px: int, bold: bool = False, italic: bool = False, familia: str | None = None) -> QFont:
    """QFont em pixels (o customtkinter também usava pixels)."""
    familia = familia or FAMILIA_PADRAO
    f = QFont(familia)
    f.setPixelSize(px)
    f.setItalic(italic)
    if bold:
        # Roboto "negrito" = Roboto Medium (a que o customtkinter embute)
        f.setWeight(QFont.Weight.Medium if familia == "Roboto" else QFont.Weight.Bold)
    return f


# ----------------------------------------------------------------------
# Fragmentos de QSS reutilizáveis
# ----------------------------------------------------------------------
def qss_botao(bg: str, hover: str, fg: str = TEXT, borda: str | None = None, raio: int = 8,
              pressionado: str | None = None) -> str:
    borda_css = f"border: 1px solid {borda};" if borda else "border: none;"
    return f"""
        QPushButton {{ background-color: {bg}; color: {fg}; {borda_css}
                       border-radius: {raio}px; padding: 0px 10px; }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:pressed {{ background-color: {pressionado or hover}; }}
        QPushButton:disabled {{ background-color: {bg}; color: {TEXTO_DESABILITADO}; }}
    """


def qss_entry(raio: int = 6) -> str:
    return f"""
        QLineEdit {{ background-color: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER};
                     border-radius: {raio}px; padding: 0px 8px;
                     selection-background-color: {ACCENT}; placeholder-text-color: {TEXT_MUTED}; }}
        QLineEdit:disabled {{ color: {TEXTO_DESABILITADO}; }}
    """


def _qss_global() -> str:
    return f"""
        QToolTip {{ background-color: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}

        QDialog {{ background-color: {BG_MODAL}; }}

        QScrollArea {{ background: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}

        QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {BG_INPUT_HOV}; min-height: 30px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

        QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
        QScrollBar::handle:horizontal {{ background: {BG_INPUT_HOV}; min-width: 30px; border-radius: 4px; }}
        QScrollBar::handle:horizontal:hover {{ background: {TEXT_MUTED}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

        QPlainTextEdit {{ background-color: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER};
                          border-radius: 6px; padding: 4px; selection-background-color: {ACCENT}; }}
    """


def aplicar_estilo(app: QApplication) -> None:
    """Tema escuro + fonte padrão para toda a aplicação."""
    app.setStyle("Fusion")
    carregar_fontes()
    app.setFont(fonte(13))

    paleta = QPalette()
    paleta.setColor(QPalette.ColorRole.Window, QColor(BG_APP))
    paleta.setColor(QPalette.ColorRole.WindowText, QColor(TEXTO_PADRAO))
    paleta.setColor(QPalette.ColorRole.Base, QColor(BG_INPUT))
    paleta.setColor(QPalette.ColorRole.AlternateBase, QColor(BG_CARD))
    paleta.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    paleta.setColor(QPalette.ColorRole.Button, QColor(BG_INPUT))
    paleta.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    paleta.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    paleta.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    paleta.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    paleta.setColor(QPalette.ColorRole.ToolTipBase, QColor(BG_INPUT))
    paleta.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    paleta.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(TEXTO_DESABILITADO))
    paleta.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(TEXTO_DESABILITADO))
    app.setPalette(paleta)

    app.setStyleSheet(_qss_global())
