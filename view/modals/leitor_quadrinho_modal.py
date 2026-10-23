"""
==============================================================================
 LEITOR DE QUADRINHOS - Qt
==============================================================================
Mesmos controles do original:
  [Scroll] zoom no cursor | [Arrastar] mover | [Clique] próxima/anterior
  [Duplo clique] reset do zoom | [F11] tela cheia | [←/→/Espaço] páginas | [Esc] fecha
"""
import math

from PIL import Image
from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from database.sqlal import DatabaseGerenciador
from service.geometria_leitor import calcular_dimensao_base, calcular_ponto_zoom
from service.leitor_arquivos import obter_imagens_da_pasta
from service.sistema import abrir_arquivo_externo
from view.estilo import BTN_PADRAO, BTN_PADRAO_HOVER, cor_texto, fonte, qss_botao


def _pil_para_qimage(img: Image.Image) -> QImage:
    """Converte a imagem do PIL (qualquer formato que ele abra) para QImage."""
    if "A" in img.mode or "transparency" in img.info:
        img = img.convert("RGBA")
        formato, modo, bpp = QImage.Format.Format_RGBA8888, "RGBA", 4
    else:
        img = img.convert("RGB")
        formato, modo, bpp = QImage.Format.Format_RGB888, "RGB", 3
    largura, altura = img.size
    return QImage(img.tobytes("raw", modo), largura, altura, largura * bpp, formato).copy()


class CanvasLeitor(QWidget):
    """Área onde a página é desenhada. Só repassa os eventos para o leitor."""

    def __init__(self, leitor):
        super().__init__(leitor)
        self.leitor = leitor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(100, 100)

    def paintEvent(self, _ev):
        p = QPainter(self)
        self.leitor.desenhar(p, self)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.leitor.recalcular_tamanho_base()

    def wheelEvent(self, ev):
        self.leitor.ao_rolar_mouse_zoom(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.leitor.ao_iniciar_arrasto(ev)

    def mouseMoveEvent(self, ev):
        self.leitor.ao_arrastar_imagem(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.leitor.ao_soltar_mouse(ev)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.leitor.ao_duplo_clique()


class LeitorQuadrinhoModal(QWidget):
    """Janela do leitor (não modal, como no original). Use .abrir() para mostrá-la maximizada."""

    def __init__(self, parent, quadrinho, db: DatabaseGerenciador, callback_refresh):
        super().__init__(parent, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.quadrinho = quadrinho
        self.db = db
        self.callback_refresh = callback_refresh

        self.setWindowTitle(f"Lendo: {self.quadrinho.titulo_limpo}")
        self.resize(1100, 520)
        self.move(40, 10)

        # Usa a função utilitária do backend
        self.imagens = obter_imagens_da_pasta(self.quadrinho.caminho_pasta)
        self.total_paginas = len(self.imagens)

        pag_salva = self.quadrinho.pagina_atual or 1
        self.pagina_atual = pag_salva if (1 <= pag_salva <= self.total_paginas) else 1

        self.is_fullscreen = False
        self._estava_maximizada = True
        self.img_original: QImage | None = None
        self._erro: str | None = None

        self.zoom_level = 1.0
        self.img_center_x = 0
        self.img_center_y = 0
        self.base_w = 0
        self.base_h = 0
        self.drag_x = 0
        self.drag_y = 0
        self.foi_arrastado = False
        self._ignorar_soltar = False   # soltar do botão que terminou um duplo clique

        # caches de desenho
        self._pix_base = None
        self._pix_base_chave = None
        self._niveis: dict[int, QImage] = {}

        self.criar_interface()

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------
    def criar_interface(self):
        self.setStyleSheet("QFrame#barraLeitor { background-color: #101014; }")
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # --- barra superior ---
        self.barra_superior = QFrame()
        self.barra_superior.setObjectName("barraLeitor")
        self.barra_superior.setFixedHeight(28)
        lay_sup = QHBoxLayout(self.barra_superior)
        lay_sup.setContentsMargins(12, 0, 10, 0)
        lay_sup.setSpacing(10)

        self.lbl_info = QLabel("")
        self.lbl_info.setFont(fonte(11, bold=True))
        lay_sup.addWidget(self.lbl_info)

        self.lbl_zoom_status = QLabel("Zoom: 1.0x")
        self.lbl_zoom_status.setFont(fonte(10))
        cor_texto(self.lbl_zoom_status, "#3a86ff")
        lay_sup.addWidget(self.lbl_zoom_status)
        lay_sup.addStretch(1)

        btn_externo = QPushButton("Abrir no Windows")
        btn_externo.setFixedSize(100, 20)
        btn_externo.setFont(fonte(10))
        btn_externo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_externo.setStyleSheet(qss_botao("#2b2d42", "#3d3f5a", "#ffffff", raio=4))
        btn_externo.clicked.connect(self.abrir_no_windows)
        lay_sup.addWidget(btn_externo)
        raiz.addWidget(self.barra_superior)

        # --- canvas ---
        self.canvas = CanvasLeitor(self)
        raiz.addWidget(self.canvas, 1)

        # --- barra inferior ---
        self.barra_inferior = QFrame()
        self.barra_inferior.setObjectName("barraLeitor")
        self.barra_inferior.setFixedHeight(28)
        lay_inf = QHBoxLayout(self.barra_inferior)
        lay_inf.setContentsMargins(12, 2, 12, 2)

        estilo = qss_botao(BTN_PADRAO, BTN_PADRAO_HOVER, "#ffffff", raio=4)

        self.btn_ant = QPushButton("◀ Anterior")
        self.btn_ant.setFixedSize(80, 20)
        self.btn_ant.setFont(fonte(11))
        self.btn_ant.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_ant.setStyleSheet(estilo)
        self.btn_ant.clicked.connect(self.pagina_anterior)
        lay_inf.addWidget(self.btn_ant)
        lay_inf.addStretch(1)

        self.lbl_aviso = QLabel("[Scroll] Zoom no Cursor | [Arrastar] Mover | [Duplo Clique] Reset | [F11] Tela Cheia")
        self.lbl_aviso.setFont(fonte(10))
        cor_texto(self.lbl_aviso, "#888899")
        lay_inf.addWidget(self.lbl_aviso)
        lay_inf.addStretch(1)

        self.btn_prox = QPushButton("Próxima ▶")
        self.btn_prox.setFixedSize(80, 20)
        self.btn_prox.setFont(fonte(11))
        self.btn_prox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_prox.setStyleSheet(estilo)
        self.btn_prox.clicked.connect(self.proxima_pagina)
        lay_inf.addWidget(self.btn_prox)
        raiz.addWidget(self.barra_inferior)

    def abrir(self):
        """Mostra maximizado e carrega a página (o original esperava 20 ms e 80 ms)."""
        self.showMaximized()
        QTimer.singleShot(80, self.carregar_nova_pagina)

    # ------------------------------------------------------------------
    # TECLADO / JANELA
    # ------------------------------------------------------------------
    def keyPressEvent(self, ev):
        tecla = ev.key()
        if tecla in (Qt.Key.Key_Right, Qt.Key.Key_Space):
            self.proxima_pagina()
        elif tecla == Qt.Key.Key_Left:
            self.pagina_anterior()
        elif tecla == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif tecla == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(ev)

    def closeEvent(self, ev):
        self.fechar_leitor()
        ev.accept()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self._estava_maximizada = self.isMaximized()
            self.showFullScreen()
        elif self._estava_maximizada:
            self.showMaximized()
        else:
            self.showNormal()

    # ------------------------------------------------------------------
    # TAMANHO / PÁGINAS
    # ------------------------------------------------------------------
    def recalcular_tamanho_base(self):
        if self.img_original is None:
            return
        disp_w = self.canvas.width()
        disp_h = self.canvas.height()
        if disp_w < 50 or disp_h < 50:
            return

        self.base_w, self.base_h = calcular_dimensao_base(
            self.img_original.width(), self.img_original.height(), disp_w, disp_h
        )

        if self.zoom_level == 1.0:
            self.img_center_x = disp_w // 2
            self.img_center_y = disp_h // 2
        self.redesenhar_canvas()

    def carregar_nova_pagina(self):
        if not self.imagens:
            return

        caminho_img = self.imagens[self.pagina_atual - 1]
        self.lbl_info.setText(f"{self.quadrinho.titulo_limpo} | Pág {self.pagina_atual}/{self.total_paginas}")

        try:
            with Image.open(caminho_img) as pil:
                imagem = _pil_para_qimage(pil)
            self.img_original = imagem
            self._erro = None
            self._limpar_caches()
            self.zoom_level = 1.0
            self.lbl_zoom_status.setText("Zoom: 1.0x")
            self.recalcular_tamanho_base()
        except Exception as e:
            self.img_original = None
            self._erro = f"Erro: {e}"
            self.canvas.update()

        self.db.atualizar_progresso_leitura(self.quadrinho.id, self.pagina_atual, self.total_paginas)

    def proxima_pagina(self):
        if self.pagina_atual < self.total_paginas:
            self.pagina_atual += 1
            self.carregar_nova_pagina()

    def pagina_anterior(self):
        if self.pagina_atual > 1:
            self.pagina_atual -= 1
            self.carregar_nova_pagina()

    # ------------------------------------------------------------------
    # MOUSE
    # ------------------------------------------------------------------
    def ao_rolar_mouse_zoom(self, ev):
        delta = ev.angleDelta().y()
        if self.img_original is None or self.base_w == 0 or delta == 0:
            return

        fator = 1.2 if delta > 0 else (1 / 1.2)
        novo_zoom = max(1.0, min(4.0, self.zoom_level * fator))
        if novo_zoom == self.zoom_level:
            return

        mx, my = int(ev.position().x()), int(ev.position().y())
        curr_w = self.base_w * self.zoom_level
        curr_h = self.base_h * self.zoom_level

        self.zoom_level = novo_zoom
        new_w = self.base_w * self.zoom_level
        new_h = self.base_h * self.zoom_level

        if self.zoom_level == 1.0:
            self.img_center_x = self.canvas.width() // 2
            self.img_center_y = self.canvas.height() // 2
        else:
            self.img_center_x, self.img_center_y = calcular_ponto_zoom(
                mx, my, self.img_center_x, self.img_center_y, curr_w, curr_h, new_w, new_h
            )

        self.lbl_zoom_status.setText(f"Zoom: {self.zoom_level:.1f}x")
        self.redesenhar_canvas()

    def ao_iniciar_arrasto(self, ev):
        self._ignorar_soltar = False   # um novo clique sempre começa "limpo"
        self.drag_x = int(ev.position().x())
        self.drag_y = int(ev.position().y())
        self.foi_arrastado = False

    def ao_arrastar_imagem(self, ev):
        x, y = int(ev.position().x()), int(ev.position().y())
        dx = x - self.drag_x
        dy = y - self.drag_y

        if abs(dx) > 3 or abs(dy) > 3:
            self.foi_arrastado = True

        if self.zoom_level > 1.0:
            self.img_center_x += dx
            self.img_center_y += dy
            self.drag_x = x
            self.drag_y = y
            self.redesenhar_canvas()

    def ao_soltar_mouse(self, ev):
        if self._ignorar_soltar:
            self._ignorar_soltar = False
            return
        if not self.foi_arrastado and self.zoom_level == 1.0:
            largura = self.canvas.width()
            if ev.position().x() > (largura / 2):
                self.proxima_pagina()
            else:
                self.pagina_anterior()

    def ao_duplo_clique(self):
        self._ignorar_soltar = True   # o clique que fecha o duplo clique não deve virar página
        self.resetar_zoom()

    def resetar_zoom(self):
        self.zoom_level = 1.0
        self.lbl_zoom_status.setText("Zoom: 1.0x")
        self.recalcular_tamanho_base()

    # ------------------------------------------------------------------
    # DESENHO
    # ------------------------------------------------------------------
    def _limpar_caches(self):
        self._pix_base = None
        self._pix_base_chave = None
        self._niveis = {}

    def redesenhar_canvas(self):
        self.canvas.update()

    def _imagem_para(self, largura_fisica: float) -> QImage:
        """
        Devolve a versão da imagem mais adequada para desenhar com `largura_fisica` px:
        reduzir de uma vez só uma imagem enorme serrilha, então usa-se uma "pirâmide"
        (original, 1/2, 1/4...) até que a redução restante seja menor que 2x.
        """
        razao = self.img_original.width() / max(1.0, largura_fisica)
        if razao < 2:
            return self.img_original
        nivel = int(math.floor(math.log2(razao)))
        if nivel not in self._niveis:
            fator = 2 ** nivel
            self._niveis[nivel] = self.img_original.scaled(
                max(1, self.img_original.width() // fator), max(1, self.img_original.height() // fator),
                Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return self._niveis[nivel]

    def desenhar(self, p: QPainter, canvas: QWidget):
        p.fillRect(canvas.rect(), QColor("#050505"))

        if self._erro:
            p.setPen(QColor("white"))
            p.setFont(fonte(13))
            p.drawText(canvas.rect(), int(Qt.AlignmentFlag.AlignCenter), self._erro)
            return
        if self.img_original is None or self.base_w == 0:
            return

        w_alvo = max(1, int(self.base_w * self.zoom_level))
        h_alvo = max(1, int(self.base_h * self.zoom_level))
        x = self.img_center_x - w_alvo // 2
        y = self.img_center_y - h_alvo // 2
        dpr = canvas.devicePixelRatioF()

        if self.zoom_level == 1.0:
            # tamanho "encaixado": uma versão pré-reduzida com a melhor qualidade, em cache
            chave = (w_alvo, h_alvo, dpr)
            if self._pix_base_chave != chave:
                reduzida = self.img_original.scaled(
                    max(1, int(w_alvo * dpr)), max(1, int(h_alvo * dpr)),
                    Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._pix_base = QPixmap.fromImage(reduzida)
                self._pix_base.setDevicePixelRatio(dpr)
                self._pix_base_chave = chave
            p.drawPixmap(QPoint(x, y), self._pix_base)
        else:
            # com zoom, só os pixels visíveis são amostrados (nada de bitmap gigante em memória)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            fonte_img = self._imagem_para(w_alvo * dpr)
            p.drawImage(QRectF(x, y, w_alvo, h_alvo), fonte_img)

    # ------------------------------------------------------------------
    # AÇÕES
    # ------------------------------------------------------------------
    def abrir_no_windows(self):
        if self.imagens:
            abrir_arquivo_externo(self.imagens[self.pagina_atual - 1])

    def fechar_leitor(self):
        self.db.atualizar_progresso_leitura(self.quadrinho.id, self.pagina_atual, self.total_paginas)
        try:
            self.callback_refresh()
        except RuntimeError:
            pass  # a janela principal já está sendo destruída
