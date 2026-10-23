"""
==============================================================================
CARD DE QUADRINHO (RESPONSIVO) - versão Qt
==============================================================================
"""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from database.sqlal import DatabaseGerenciador
from service.miniaturas import carregar_miniatura_otimizada
from view.estilo import cor_texto, fonte
from view.modals.editar_metadados_modal import EditarMetadadosModal
from config.constantes import MARGEM_HORIZONTAL, PROPORCAO_CAPA


class ComicCard(QFrame):
    """
    CRIA O CARD DO QUADRINHO.

    A largura do card é fixa (`largura`) e a capa ocupa `largura - MARGEM_HORIZONTAL`,
    por isso o método `redimensionar(largura)` basta para escalar o card todo.
    """
    COR_FUNDO, COR_BORDA = "#181820", "#262633"
    COR_FUNDO_HOVER, COR_BORDA_HOVER = "#20202e", "#3a86ff"

    def __init__(self, parent, quadrinho, db: DatabaseGerenciador, callback_refresh,
                 callback_tags, abrir_leitor_callback, largura: int = 180):
        super().__init__(parent)
        self.quadrinho = quadrinho
        self.db = db
        self.callback_refresh = callback_refresh
        self.callback_tags = callback_tags
        self.abrir_leitor_callback = abrir_leitor_callback

        self.largura = largura
        self._pix_capa = None   # miniatura original, reescalada a cada mudança de tamanho
        self._hover = False

        self.is_arquivado = bool(quadrinho.arquivado)
        self.is_lido = bool(quadrinho.lido)
        self.pode_ler = not self.is_arquivado and bool(quadrinho.descompactada) and bool(quadrinho.tem_imagens)
        self.criar_card()

    # ------------------------------------------------------------------
    # MEDIDAS
    # ------------------------------------------------------------------
    def _medidas(self, largura: int):
        """Retorna (largura_capa, altura_capa) a partir da largura total do card."""
        img_w = max(60, largura - MARGEM_HORIZONTAL)
        return img_w, round(img_w * PROPORCAO_CAPA)

    def criar_card(self):
        """
        Cria e renderiza o card visual de um quadrinho na interface.

        Faz:
            - Carrega a miniatura e a encaixa na área da capa.
            - Altera o cursor do mouse para indicar interatividade (clique).
            - Mostra o status de leitura.
            - Mostra título, ano e número de páginas.
        """
        img_w, box_h = self._medidas(self.largura)
        self.setFixedWidth(self.largura)
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.pode_ler else Qt.CursorShape.ArrowCursor)

        layout = QVBoxLayout(self)
        # borda (2) + padding do original (4) em cima e dos lados; embaixo só a borda
        layout.setContentsMargins(6, 6, 6, 2)
        layout.setSpacing(0)

        # CAPA
        self._pix_capa = carregar_miniatura_otimizada(f"card_{self.quadrinho.id}", self.quadrinho.caminho_capa)
        self.lbl_capa = QLabel()
        self.lbl_capa.setFixedSize(img_w, box_h)
        self.lbl_capa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_capa.setStyleSheet("background-color: #111116; border-radius: 4px;")
        if self._pix_capa:
            self._ajustar_imagem(img_w, box_h)
        else:
            self.lbl_capa.setText("Sem Capa")
            self.lbl_capa.setFont(fonte(13))
        layout.addWidget(self.lbl_capa, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(2)

        # INDICADOR DE STATUS
        self._fonte_status = fonte(10, bold=True)
        if self.is_arquivado:
            texto_status, cor_status = "✓ LIDO (ARQUIVADO)", "#2ec4b6"
        elif self.is_lido:
            texto_status, cor_status = "✓ LIDO", "#20bf6b"
        elif self.pode_ler:
            texto_status, cor_status = "▶ CLIQUE P/ LER", "#3a86ff"
        else:
            texto_status, cor_status = "🔒 COMPACTADO", "#555566"
        self._status_completo = texto_status
        self.lbl_hover_indicator = self._criar_label(self._fonte_status, cor_status, altura=14)
        layout.addWidget(self.lbl_hover_indicator)
        layout.addSpacing(2)

        # TÍTULO (truncado conforme a largura real disponível)
        self._titulo_completo = self.quadrinho.titulo_limpo or ""
        self._fonte_titulo = fonte(11, bold=True)
        self.lbl_titulo = self._criar_label(self._fonte_titulo, None, altura=28)
        layout.addWidget(self.lbl_titulo)
        layout.addSpacing(1)

        # TEXTO DE PROGRESSO / ANO
        if self.is_arquivado:
            info_txt = "Espaço Liberado"
        elif self.is_lido:
            info_txt = "Completo"
        else:
            pag = self.quadrinho.pagina_atual or 0
            total = self.quadrinho.total_paginas or 0
            info_txt = f"Pág: {pag}/{total}" if total > 0 else ("Novo" if pag == 0 else f"Pág: {pag}")

        if self.quadrinho.ano:
            info_txt += f" • {self.quadrinho.ano}"

        self._info_completo = info_txt
        self._fonte_info = fonte(10)
        self.lbl_info = self._criar_label(self._fonte_info, "#777788", altura=28)
        layout.addWidget(self.lbl_info)
        layout.addSpacing(5)

        # corta título, status e info conforme a largura real do card
        self._aplicar_textos(img_w)

    def _criar_label(self, fonte_label, cor, altura: int) -> QLabel:
        label = QLabel()
        label.setFont(fonte_label)
        label.setFixedHeight(altura)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # o card recebe os cliques
        if cor:
            cor_texto(label, cor)
        return label

    # ------------------------------------------------------------------
    # REDIMENSIONAMENTO
    # ------------------------------------------------------------------
    def redimensionar(self, largura: int):
        """Escala o card inteiro (capa, título) para a nova largura, sem recriá-lo."""
        if largura == self.largura:
            return
        self.largura = largura
        img_w, box_h = self._medidas(largura)

        self.setFixedWidth(largura)
        self.lbl_capa.setFixedSize(img_w, box_h)
        self._ajustar_imagem(img_w, box_h)
        self._aplicar_textos(img_w)

    def atualizar_dpi(self):
        """Reescala a capa para a densidade de pixels atual (ex.: janela movida para outro monitor)."""
        img_w, box_h = self._medidas(self.largura)
        self._ajustar_imagem(img_w, box_h)

    def _ajustar_imagem(self, img_w: int, box_h: int):
        """Encaixa a capa na área (img_w x box_h) mantendo a proporção original, nítida em qualquer DPI."""
        if not self._pix_capa:
            return
        dpr = self.devicePixelRatioF()
        alvo = QSize(max(1, int(img_w * dpr)), max(1, int(box_h * dpr)))
        escalada = self._pix_capa.scaled(alvo, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
        escalada.setDevicePixelRatio(dpr)
        self.lbl_capa.setPixmap(escalada)

    @staticmethod
    def _ajustar_texto(label: QLabel, fonte_label, texto: str, limite: int):
        """Coloca `texto` no label; se não couber em `limite` px, corta com reticências."""
        fm = QFontMetrics(fonte_label)
        if fm.horizontalAdvance(texto) > limite:
            while texto and fm.horizontalAdvance(texto + "...") > limite:
                texto = texto[:-1]
            texto = texto.rstrip() + "..."
        label.setText(texto)

    def _aplicar_textos(self, largura_capa: int):
        """Evita que um texto longo alargue o card além da largura calculada pela grade."""
        limite = largura_capa - 4
        self._ajustar_texto(self.lbl_titulo, self._fonte_titulo, self._titulo_completo, limite)
        self._ajustar_texto(self.lbl_hover_indicator, self._fonte_status, self._status_completo, limite)
        self._ajustar_texto(self.lbl_info, self._fonte_info, self._info_completo, limite)

    # ------------------------------------------------------------------
    # DESENHO (fundo/borda mudam com o mouse em cima)
    # ------------------------------------------------------------------
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self.COR_FUNDO_HOVER if self._hover else self.COR_FUNDO))
        p.setPen(QPen(QColor(self.COR_BORDA_HOVER if self._hover else self.COR_BORDA), 2))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)

    # ------------------------------------------------------------------
    # EVENTOS
    # ------------------------------------------------------------------
    def mousePressEvent(self, ev):
        """
        BOTÃO DIREITO ABRE O MENU DE EDIÇÃO

        BOTÃO ESQUERDO ABRE O QUADRINHO SE PUDER SER LIDO
        """
        if ev.button() == Qt.MouseButton.RightButton:
            self.abrir_menu_edicao()
        elif ev.button() == Qt.MouseButton.LeftButton and self.pode_ler:
            self.abrir_leitor_callback(self.quadrinho)

    def enterEvent(self, ev):
        if self.pode_ler:
            self.ao_entrar_mouse()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        if self.pode_ler:
            self.ao_sair_mouse()
        super().leaveEvent(ev)

    def ao_entrar_mouse(self, event=None):
        """COR DA BORDA E DO TEXTO QUANDO O MOUSE ESTÁ SOBRE O CARD"""
        self._hover = True
        self.update()
        if not self.is_lido and not self.is_arquivado:
            cor_texto(self.lbl_hover_indicator, "#00f5d4")

    def ao_sair_mouse(self, event=None):
        """COR DA BORDA E DO TEXTO QUANDO O MOUSE SAI DO CARD"""
        self._hover = False
        self.update()
        if not self.is_lido and not self.is_arquivado:
            cor_texto(self.lbl_hover_indicator, "#3a86ff")

    def abrir_menu_edicao(self):
        """ABRE O MENU DE EDITAR TAGS"""
        EditarMetadadosModal(
            parent=self.window(),
            quadrinho=self.quadrinho,
            db=self.db,
            callback_atualizacao=self.callback_refresh,
            callback_atualizar_tags=self.callback_tags
        ).exec()
