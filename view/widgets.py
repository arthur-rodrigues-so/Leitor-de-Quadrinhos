"""
==============================================================================
 WIDGETS PERSONALIZADOS
==============================================================================
"""

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QLayout, QLineEdit,
    QPushButton, QScrollArea,
)

from config.constantes import (
    ACCENT, ACCENT_HOV, BG_INPUT, BG_INPUT_HOV, TEXT, VELOCIDADE_SCROLL,
)
from view.estilo import FAMILIA_SIDEBAR, TEXTO_PADRAO, fonte


# ======================================================================
# FlowLayout (quebra de linha com justificação)
# ======================================================================
class FlowLayout(QLayout):
    """
    Distribui os itens em linhas. Cada linha é "justificada": a sobra de largura
    é dividida igualmente entre os itens dela, então uma linha única ocupa toda a
    largura (como o CTkSegmentedButton) e, quando não cabe, quebra para a de baixo.
    """

    def __init__(self, parent=None, h_spacing: int = 0, v_spacing: int = 2):
        super().__init__(parent)
        self._itens = []
        self._hs = h_spacing
        self._vs = v_spacing

    # --- API obrigatória do QLayout ---
    def addItem(self, item):
        self._itens.append(item)

    def count(self):
        return len(self._itens)

    def itemAt(self, indice):
        return self._itens[indice] if 0 <= indice < len(self._itens) else None

    def takeAt(self, indice):
        return self._itens.pop(indice) if 0 <= indice < len(self._itens) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largura):
        return self._organizar(QRect(0, 0, largura, 0), somente_medir=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._organizar(rect, somente_medir=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        tamanho = QSize()
        for item in self._itens:
            tamanho = tamanho.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return tamanho + QSize(m.left() + m.right(), m.top() + m.bottom())

    # --- cálculo das linhas ---
    def _organizar(self, rect, somente_medir):
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())

        linhas, atual, largura_atual = [], [], 0
        for item in self._itens:
            w = item.sizeHint().width()
            if atual and largura_atual + self._hs + w > area.width():
                linhas.append((atual, largura_atual))
                atual, largura_atual = [item], w
            else:
                largura_atual = w if not atual else largura_atual + self._hs + w
                atual.append(item)
        if atual:
            linhas.append((atual, largura_atual))

        y = area.y()
        for itens, largura_linha in linhas:
            altura = max(i.sizeHint().height() for i in itens)
            sobra = max(0, area.width() - largura_linha) / len(itens)
            x = float(area.x())
            for item in itens:
                w = item.sizeHint().width() + sobra
                if not somente_medir:
                    inicio = round(x)
                    fim = round(x + w)
                    item.setGeometry(QRect(inicio, y, max(1, fim - inicio), altura))
                x += w + self._hs
            y += altura + self._vs

        total = (y - self._vs) - rect.y() if linhas else 0
        return total + m.bottom()


# ======================================================================
# SegmentedButton (CTkSegmentedButton)
# ======================================================================
class SegmentedButton(QFrame):
    """
    Seletor de opção única. API parecida com a do CTkSegmentedButton:
    set(valor), get() e o callback `command(valor)` disparado a cada clique.
    """

    def __init__(self, values, command=None, altura: int = 30, raio: int = 6,
                 largura_fixa: int | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("segmentado")
        self._command = command
        self._botoes: dict[str, QPushButton] = {}

        self.setStyleSheet(f"""
            QFrame#segmentado {{ background-color: {BG_INPUT}; border-radius: {raio}px; }}
            QFrame#segmentado QPushButton {{
                background-color: transparent; color: {TEXT}; border: none;
                border-radius: {raio}px; padding: 0px 7px;
            }}
            QFrame#segmentado QPushButton:hover {{ background-color: {BG_INPUT_HOV}; }}
            QFrame#segmentado QPushButton:checked {{ background-color: {ACCENT}; }}
            QFrame#segmentado QPushButton:checked:hover {{ background-color: {ACCENT_HOV}; }}
        """)

        layout = FlowLayout(self, h_spacing=0, v_spacing=2)
        layout.setContentsMargins(0, 0, 0, 0)

        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)

        for valor in values:
            botao = QPushButton(valor)
            botao.setCheckable(True)
            botao.setFixedHeight(altura)
            botao.setFont(fonte(12, familia=FAMILIA_SIDEBAR))
            botao.setCursor(Qt.CursorShape.PointingHandCursor)
            botao.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            botao.clicked.connect(lambda _checked=False, v=valor: self._ao_clicar(v))
            self._grupo.addButton(botao)
            layout.addWidget(botao)
            self._botoes[valor] = botao

        if largura_fixa:
            self.setFixedWidth(largura_fixa)

    def _ao_clicar(self, valor: str):
        if self._command:
            self._command(valor)

    def set(self, valor: str):
        botao = self._botoes.get(valor)
        if botao:
            botao.setChecked(True)

    def get(self) -> str:
        for valor, botao in self._botoes.items():
            if botao.isChecked():
                return valor
        return ""


# ======================================================================
# ToggleSwitch (CTkSwitch)
# ======================================================================
class ToggleSwitch(QCheckBox):
    """Interruptor com texto. `clicked` dispara quando o usuário alterna."""

    LARGURA, ALTURA, FOLGA = 36, 18, 8

    def __init__(self, texto: str, parent=None):
        super().__init__(texto, parent)
        self.setFont(fonte(12, familia=FAMILIA_SIDEBAR))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def sizeHint(self):
        fm = self.fontMetrics()
        return QSize(self.LARGURA + self.FOLGA + fm.horizontalAdvance(self.text()) + 2,
                     max(self.ALTURA, fm.height()) + 4)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def enterEvent(self, ev):
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self.update()
        super().leaveEvent(ev)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cy = self.height() / 2
        trilho = QRectF(0, cy - self.ALTURA / 2, self.LARGURA, self.ALTURA)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(ACCENT if self.isChecked() else BG_INPUT_HOV))
        p.drawRoundedRect(trilho, self.ALTURA / 2, self.ALTURA / 2)

        d = self.ALTURA - 4
        x = self.LARGURA - 2 - d if self.isChecked() else 2
        p.setBrush(QColor("#ffffff" if self.underMouse() else TEXT))
        p.drawEllipse(QRectF(x, cy - d / 2, d, d))

        p.setPen(QColor(TEXT))
        p.setFont(self.font())
        p.drawText(QRectF(self.LARGURA + self.FOLGA, 0, self.width() - self.LARGURA - self.FOLGA, self.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.text())


# ======================================================================
# CheckBoxModerno (CTkCheckBox)
# ======================================================================
class CheckBoxModerno(QCheckBox):
    """Caixa de seleção arredondada, com o mesmo visual do tema do customtkinter."""

    TAMANHO, FOLGA = 20, 8
    COR_BORDA = "#565b5e"
    COR_MARCADO = "#1f6aa5"
    COR_MARCADO_HOVER = "#14375e"

    def __init__(self, texto: str, tamanho_fonte: int = 11, parent=None):
        super().__init__(texto, parent)
        self.setFont(fonte(tamanho_fonte))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def sizeHint(self):
        fm = self.fontMetrics()
        return QSize(self.TAMANHO + self.FOLGA + fm.horizontalAdvance(self.text()) + 4,
                     max(self.TAMANHO, fm.height()) + 4)

    def minimumSizeHint(self):
        return QSize(self.TAMANHO + 4, self.sizeHint().height())

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def enterEvent(self, ev):
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self.update()
        super().leaveEvent(ev)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.TAMANHO
        caixa = QRectF(1, (self.height() - t) / 2 + 1, t - 2, t - 2)

        if self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.COR_MARCADO_HOVER if self.underMouse() else self.COR_MARCADO))
            p.drawRoundedRect(caixa, 5, 5)
            caneta = QPen(QColor("#ffffff"), 2.2)
            caneta.setCapStyle(Qt.PenCapStyle.RoundCap)
            caneta.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(caneta)
            p.setBrush(Qt.BrushStyle.NoBrush)
            x, y = caixa.x(), caixa.y()
            p.drawPolyline([QPointF(x + t * 0.25, y + t * 0.50),
                            QPointF(x + t * 0.43, y + t * 0.67),
                            QPointF(x + t * 0.74, y + t * 0.32)])
        else:
            p.setPen(QPen(QColor(self.COR_BORDA), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(caixa, 5, 5)

        p.setPen(QColor(TEXTO_PADRAO if self.isEnabled() else "#6b7080"))
        p.setFont(self.font())
        p.drawText(QRectF(t + self.FOLGA, 0, self.width() - t - self.FOLGA, self.height()),
                   int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.text())


# ======================================================================
# ScrollAreaRapida (VELOCIDADE_SCROLL)
# ======================================================================
class ScrollAreaRapida(QScrollArea):
    """
    QScrollArea cuja roda do mouse rola VELOCIDADE_SCROLL * 20 px por "clique"
    (o mesmo cálculo do projeto original: 8 -> 160px), em vez do padrão do sistema.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def wheelEvent(self, ev):
        barra = self.verticalScrollBar()
        delta = ev.angleDelta().y()
        if delta == 0 or barra.maximum() == barra.minimum():
            ev.ignore()  # nada para rolar (igual ao original: só rola se há conteúdo escondido)
            return
        passos = delta / 120.0
        barra.setValue(int(barra.value() - passos * VELOCIDADE_SCROLL * 20))
        ev.accept()


# ======================================================================
# LineEditTecla (<KeyRelease>)
# ======================================================================
class LineEditTecla(QLineEdit):
    """QLineEdit que emite `tecla_solta` ao soltar qualquer tecla (equivale ao <KeyRelease> do Tk)."""
    tecla_solta = Signal()

    def keyReleaseEvent(self, ev):
        super().keyReleaseEvent(ev)
        self.tecla_solta.emit()
