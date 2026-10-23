"""
==============================================================================
 APLICAÇÃO PRINCIPAL - Qt (PySide6)
==============================================================================
"""
import os
import sys
import threading

from json import JSONDecodeError

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QVBoxLayout, QWidget
)

from config.inicializar import caminho_absoluto_pasta_executando
from config.constantes import *

from view.comic_card import ComicCard
from view.estilo import (
    FAMILIA_SIDEBAR, cor_texto, fonte, qss_botao, qss_entry,
)
from view.widgets import (
    CheckBoxModerno, LineEditTecla, ScrollAreaRapida, SegmentedButton, ToggleSwitch,
)
from view.modals.configuracao_modal import ConfiguracoesModal
from view.modals.leitor_quadrinho_modal import LeitorQuadrinhoModal
from view.modals.confirmar_exclusao_modal import ConfirmarExclusaoModal

from database.sqlal import DatabaseGerenciador

from service.escaneador import sincronizar_acervo_disco_com_banco
from service.matematica_grade import calcular_grade
from service.descompactador import abrir_descompactador
from service.configuracoes import carregar_configuracoes, salvar_configuracoes, carregar_config_grade


class _SinaisEscaneamento(QObject):
    """Ponte thread -> interface: o sinal é entregue na thread principal (fila de eventos do Qt)."""
    concluido = Signal()


class ComicManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.carregar_ou_configurar_inicial()
        self.config_grade = carregar_config_grade()

        self.setWindowTitle("Gerenciador & Leitor de Quadrinhos")
        self.resize(1300, 700)
        self.setMinimumSize(1050, 560)

        caminho_absoluto_pasta_executandoe = caminho_absoluto_pasta_executando(os.path.join("assets", "icone.ico"))
        if os.path.exists(caminho_absoluto_pasta_executandoe):
            self.setWindowIcon(QIcon(caminho_absoluto_pasta_executandoe))
        else:
            print(f"[ERRO ICON] Não foi possível carregar o ícone da janela: {caminho_absoluto_pasta_executandoe} não existe")

        self.editora_selecionada = "TODAS"
        self.filtro_leitura = "TODOS"
        self.tag_checkboxes = {}
        self.pagina_atual_grid = 1
        self.total_paginas_grid = 1
        self.quadrinhos_filtrados_cache = []
        self.quadrinhos_exibidos = []

        self.db = DatabaseGerenciador(self.EDITORAS)

        # debounce da busca por texto (400 ms) e do redimensionamento da janela
        self._timer_digitar = QTimer(self)
        self._timer_digitar.setSingleShot(True)
        self._timer_digitar.timeout.connect(self.resetar_e_filtrar)

        self._timer_resize = QTimer(self)
        self._timer_resize.setSingleShot(True)
        self._timer_resize.timeout.connect(self._reajustar_grade)

        self.cards_grade = []
        self.container_grade = None
        self._grid_cards = None
        self._cols_atual = 0
        self._card_w_atual = 0
        self.itens_por_pagina = ITENS_POR_PAGINA
        self._grade_atual = (1, 1, LARGURA_ALVO_CARD)
        self._extra_card_h = EXTRA_ALTURA_CARD
        self._extra_medido = False
        self._leitores = []
        self._janela_conectada = False

        self.configurar_layout()

        self.right_container.installEventFilter(self)

        # varredura do acervo em outra thread: ela só lê o disco e grava no banco,
        # nunca toca na interface. Ao terminar, a thread principal atualiza a tela.
        self._sinais_scan = _SinaisEscaneamento()
        self._sinais_scan.concluido.connect(self._aguardar_escaneamento)
        threading.Thread(target=self._escanear_em_plano_de_fundo, daemon=True).start()

    # ------------------------------------------------------------------
    # EVENTOS DA JANELA
    # ------------------------------------------------------------------
    def eventFilter(self, obj, ev):
        if obj is self.right_container and ev.type() == QEvent.Type.Resize:
            self._ao_redimensionar_area()
        return super().eventFilter(obj, ev)

    def showEvent(self, ev):
        super().showEvent(ev)
        # trocar de monitor (outra escala de DPI): só reescala as capas, é instantâneo
        if not self._janela_conectada and self.windowHandle() is not None:
            self.windowHandle().screenChanged.connect(self._ao_trocar_monitor)
            self._janela_conectada = True

    def _ao_trocar_monitor(self, *_):
        for card in self.cards_grade:
            card.atualizar_dpi()

    # ------------------------------------------------------------------
    # VARREDURA EM SEGUNDO PLANO
    # ------------------------------------------------------------------
    def _escanear_em_plano_de_fundo(self):
        """Roda em OUTRA thread: só lê o disco e grava no banco. Nunca toca em widgets."""
        try:
            self.escanear_acervo(True)
        finally:
            self._sinais_scan.concluido.emit()

    def _aguardar_escaneamento(self):
        """Roda na thread principal: a varredura terminou, então atualiza a tela."""
        self.carregar_tags_dinamicas()
        self.resetar_e_filtrar()

    def digitar(self, *_):
        self._timer_digitar.start(400)

    # ------------------------------------------------------------------
    # LAYOUT
    # ------------------------------------------------------------------
    def configurar_layout(self):
        # TIPOGRAFIA
        f_brand = fonte(20, bold=True, familia=FAMILIA_SIDEBAR)
        f_section = fonte(10, bold=True, familia=FAMILIA_SIDEBAR)
        f_body = fonte(12, familia=FAMILIA_SIDEBAR)
        f_bold = fonte(12, bold=True, familia=FAMILIA_SIDEBAR)

        def criar_card(nome: str) -> QFrame:
            card = QFrame()
            card.setObjectName(nome)
            card.setStyleSheet(f"""QFrame#{nome} {{ background-color: {BG_CARD}; border: 1px solid {BORDER};
                                                    border-radius: {RADIUS}px; }}""")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(PAD_C, 0, PAD_C, 0)
            lay.setSpacing(0)
            return card

        def criar_secao(lay: QVBoxLayout, texto: str, topo: int = 10, base: int = 4):
            lbl = QLabel(texto)
            lbl.setFont(f_section)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; border: none; background: transparent;")
            lay.addSpacing(topo)
            lay.addWidget(lbl)
            lay.addSpacing(base)

        def estilo_entry(entry: QLineEdit, altura: int = 32):
            entry.setFixedHeight(altura)
            entry.setFont(f_body)
            entry.setStyleSheet(qss_entry())

        # ------------------------------------------------------------------
        # GRID PRINCIPAL
        # ------------------------------------------------------------------
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QHBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # ------------------------------------------------------------------
        # BARRA LATERAL
        # ------------------------------------------------------------------
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebar")
        self.sidebar_frame.setFixedWidth(LARGURA_SIDEBAR)
        self.sidebar_frame.setStyleSheet(f"QFrame#sidebar {{ background-color: {BG_SIDEBAR}; }}")
        side = QVBoxLayout(self.sidebar_frame)
        side.setContentsMargins(PAD_X, 0, PAD_X, 0)
        side.setSpacing(0)

        # Cabeçalho
        lbl_marca = QLabel("LetQuadrinhos")
        lbl_marca.setFont(f_brand)
        lbl_marca.setStyleSheet(f"color: {ACCENT};")
        lbl_marca.setContentsMargins(2, 0, 0, 0)
        side.addSpacing(18)
        side.addWidget(lbl_marca)
        side.addSpacing(12)

        btn_scan = QPushButton("🔄  Sincronizar Pastas")
        btn_scan.setFixedHeight(34)
        btn_scan.setFont(f_bold)
        btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_scan.setStyleSheet(qss_botao(BG_INPUT, BG_INPUT_HOV, TEXT, borda=BORDER, raio=RADIUS))
        btn_scan.clicked.connect(lambda: self.sincronizar_pastas())
        side.addWidget(btn_scan)
        side.addSpacing(10)

        self.entry_busca = LineEditTecla()
        self.entry_busca.setPlaceholderText("🔍  Buscar título...")
        estilo_entry(self.entry_busca, 34)
        self.entry_busca.tecla_solta.connect(self.digitar)       # <KeyRelease>
        self.entry_busca.textEdited.connect(self.digitar)        # colar/recortar com o mouse
        side.addWidget(self.entry_busca)
        side.addSpacing(14)

        # ------------------------------------------------------------------
        # CARD: FILTROS
        # ------------------------------------------------------------------
        card_filtros = criar_card("cardFiltros")
        lay_f = card_filtros.layout()

        # Status de leitura
        criar_secao(lay_f, "STATUS DE LEITURA", topo=12)
        self.seg_leitura = SegmentedButton(["TODOS", "LENDO", "LIDOS"], command=self.mudar_filtro_leitura)
        self.seg_leitura.set("TODOS")
        lay_f.addWidget(self.seg_leitura)
        lay_f.addSpacing(4)

        # Editoras
        criar_secao(lay_f, "EDITORAS")
        self.seg_editora = SegmentedButton(["TODAS"] + self.EDITORAS, command=self.mudar_editora)
        self.seg_editora.set("TODAS")
        lay_f.addWidget(self.seg_editora)
        lay_f.addSpacing(4)

        # Filtro de Ano
        criar_secao(lay_f, "ANO")
        linha_ano = QHBoxLayout()
        linha_ano.setContentsMargins(0, 0, 0, 0)
        linha_ano.setSpacing(8)
        self.entry_ano_de = LineEditTecla()
        self.entry_ano_de.setPlaceholderText("De")
        estilo_entry(self.entry_ano_de)
        self.entry_ano_ate = LineEditTecla()
        self.entry_ano_ate.setPlaceholderText("Até")
        estilo_entry(self.entry_ano_ate)
        linha_ano.addWidget(self.entry_ano_de, 1)
        linha_ano.addWidget(self.entry_ano_ate, 1)
        lay_f.addLayout(linha_ano)
        lay_f.addSpacing(4)

        # Switch TAGS
        self.switch_sem_tags = ToggleSwitch("Apenas Sem Tags")
        self.switch_sem_tags.clicked.connect(lambda: self.resetar_e_filtrar())
        lay_f.addSpacing(10)
        lay_f.addWidget(self.switch_sem_tags, 0, Qt.AlignmentFlag.AlignLeft)
        lay_f.addSpacing(12)

        # Switch DESCOMPACTAR
        self.switch_descompactador = ToggleSwitch("Descompactador")
        self.switch_descompactador.clicked.connect(lambda: self.validar_descompactador(self.switch_descompactador.isChecked())) #abrir_descompactador()
        lay_f.addSpacing(10)
        lay_f.addWidget(self.switch_descompactador, 0, Qt.AlignmentFlag.AlignLeft)
        lay_f.addSpacing(12)

        side.addWidget(card_filtros)
        side.addSpacing(10)

        # ------------------------------------------------------------------
        # CARD: TAGS DINÂMICAS
        # ------------------------------------------------------------------
        card_tags = criar_card("cardTags")
        lay_t = card_tags.layout()
        criar_secao(lay_t, "TAGS DINÂMICAS", topo=12, base=6)

        linha_tag = QHBoxLayout()
        linha_tag.setContentsMargins(0, 0, 0, 0)
        linha_tag.setSpacing(6)

        self.entry_nova_tag = LineEditTecla()
        self.entry_nova_tag.setPlaceholderText("Nova tag...")
        estilo_entry(self.entry_nova_tag)
        linha_tag.addWidget(self.entry_nova_tag, 1)

        btn_add_tag = QPushButton("+")
        btn_add_tag.setFixedSize(32, 32)
        btn_add_tag.setFont(fonte(16, bold=True, familia=FAMILIA_SIDEBAR))
        btn_add_tag.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_tag.setStyleSheet(qss_botao(ACCENT, ACCENT_HOV, "#ffffff", raio=6).replace("padding: 0px 10px", "padding: 0px"))
        btn_add_tag.clicked.connect(lambda: self.adicionar_nova_tag())
        linha_tag.addWidget(btn_add_tag)

        btn_config = QPushButton("@")
        btn_config.setFixedSize(32, 32)
        btn_config.setFont(f_bold)
        btn_config.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_config.setStyleSheet(qss_botao(BG_INPUT, BG_INPUT_HOV, TEXT, raio=6).replace("padding: 0px 10px", "padding: 0px"))
        btn_config.clicked.connect(lambda: self.abrir_modal_configuracoes())
        linha_tag.addWidget(btn_config)

        lay_t.addLayout(linha_tag)
        lay_t.addSpacing(8)

        moldura_tags = QFrame()
        moldura_tags.setObjectName("molduraTags")
        moldura_tags.setStyleSheet(f"QFrame#molduraTags {{ background-color: {BG_SIDEBAR}; border: none; border-radius: 6px; }}")
        lay_m = QVBoxLayout(moldura_tags)
        lay_m.setContentsMargins(2, 2, 2, 2)
        self.scroll_tags = ScrollAreaRapida()
        self.scroll_tags.setMinimumHeight(100)
        self.conteudo_tags = QWidget()
        self._lay_tags = QVBoxLayout(self.conteudo_tags)
        self._lay_tags.setContentsMargins(6, 4, 2, 4)
        self._lay_tags.setSpacing(2)
        self.scroll_tags.setWidget(self.conteudo_tags)
        lay_m.addWidget(self.scroll_tags)
        lay_t.addWidget(moldura_tags, 1)
        lay_t.addSpacing(PAD_C)

        side.addWidget(card_tags, 1)
        side.addSpacing(10)

        # Botão Filtrar fixo na base
        btn_aplicar = QPushButton("Aplicar Filtros")
        btn_aplicar.setFixedHeight(38)
        btn_aplicar.setFont(f_bold)
        btn_aplicar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_aplicar.setStyleSheet(qss_botao(ACCENT, ACCENT_HOV, "#ffffff", raio=RADIUS))
        btn_aplicar.clicked.connect(lambda: self.resetar_e_filtrar())
        side.addSpacing(4)
        side.addWidget(btn_aplicar)
        side.addSpacing(16)

        raiz.addWidget(self.sidebar_frame)

        # ------------------------------------------------------------------
        # ÁREA PRINCIPAL
        # ------------------------------------------------------------------
        self.right_container = QFrame()
        self.right_container.setObjectName("areaPrincipal")
        self.right_container.setStyleSheet(f"QFrame#areaPrincipal {{ background-color: {BG_APP}; }}")
        dir_lay = QVBoxLayout(self.right_container)
        dir_lay.setContentsMargins(0, 0, 0, 0)
        dir_lay.setSpacing(0)

        moldura_cards = QWidget()
        lay_mc = QVBoxLayout(moldura_cards)
        lay_mc.setContentsMargins(8, 8, 0, 0)    # padx=(8,0), pady=(8,0) do original
        self.main_scroll_area = ScrollAreaRapida()
        self.main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        lay_mc.addWidget(self.main_scroll_area)
        dir_lay.addWidget(moldura_cards, 1)

        # ------------------------------------------------------------------
        # BARRA DE PAGINAÇÃO
        # ------------------------------------------------------------------
        self.barra_paginacao = QFrame()
        self.barra_paginacao.setObjectName("barraPaginacao")
        self.barra_paginacao.setFixedHeight(48)
        self.barra_paginacao.setStyleSheet(f"QFrame#barraPaginacao {{ background-color: {BG_SIDEBAR}; }}")
        lay_p = QHBoxLayout(self.barra_paginacao)
        lay_p.setContentsMargins(16, 9, 16, 9)

        estilo_pag = qss_botao(BG_INPUT, BG_INPUT_HOV, TEXT, borda=BORDER, raio=6)

        self.btn_pag_ant = QPushButton("◀  Anterior")
        self.btn_pag_ant.setFixedSize(96, 30)
        self.btn_pag_ant.setFont(f_bold)
        self.btn_pag_ant.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pag_ant.setStyleSheet(estilo_pag)
        self.btn_pag_ant.clicked.connect(lambda: self.voltar_pagina())
        lay_p.addWidget(self.btn_pag_ant)

        self.lbl_paginacao = QLabel("Página 1 de 1")
        self.lbl_paginacao.setFont(f_bold)
        self.lbl_paginacao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cor_texto(self.lbl_paginacao, TEXT_MUTED)
        lay_p.addWidget(self.lbl_paginacao, 1)

        self.btn_pag_prox = QPushButton("Próxima  ▶")
        self.btn_pag_prox.setFixedSize(96, 30)
        self.btn_pag_prox.setFont(f_bold)
        self.btn_pag_prox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pag_prox.setStyleSheet(estilo_pag)
        self.btn_pag_prox.clicked.connect(lambda: self.avancar_pagina())
        lay_p.addWidget(self.btn_pag_prox)

        dir_lay.addWidget(self.barra_paginacao)
        raiz.addWidget(self.right_container, 1)

    # ------------------------------------------------------------------
    # FILTROS
    # ------------------------------------------------------------------
    def mudar_editora(self, valor):
        self.editora_selecionada = valor
        self.resetar_e_filtrar()

    def mudar_filtro_leitura(self, valor):
        self.filtro_leitura = valor
        self.resetar_e_filtrar()

    # ------------------------------------------------------------------
    # TAGS DINAMICAS
    # ------------------------------------------------------------------
    def adicionar_nova_tag(self):
        """
        CRIA UMA NOVA TAG DINAMICA
        """
        nome = self.entry_nova_tag.text().strip()
        if nome:
            self.db.criar_tag_manual(nome)
            self.entry_nova_tag.clear()
            self.carregar_tags_dinamicas()
            self.resetar_e_filtrar()

    def solicitar_exclusao_tag(self, nome_tag: str):
        ConfirmarExclusaoModal(
            parent=self,
            titulo_aviso="Excluir Tag Dinâmica?",
            mensagem=f"Tem certeza que deseja apagar a tag '{nome_tag}'?\nEla será desvinculada de todos os quadrinhos.",
            texto_btn="Excluir Tag",
            cor_btn="#d90429",
            callback_confirmar=lambda: self.deletar_tag(nome_tag)
        ).exec()

    def deletar_tag(self, nome_tag: str):
        """
        Faz o apagamento da tag dinamica no banco.
        Chama a função de carregar tags dinamicas para recarregar as tags dinamicas.
        Chama o restar e filtrar para recarregar tudo.
        """
        self.db.deletar_tag_manual(nome_tag)
        self.carregar_tags_dinamicas()
        self.resetar_e_filtrar()

    @staticmethod
    def _esvaziar_layout(layout):
        """Remove (e agenda a destruição de) tudo que está dentro de um layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def carregar_tags_dinamicas(self):
        """
        CRIA A PARTE DE TAGS DINAMICAS SEM ELE NENHUMA TAG APARECE NA ABA.

        Server para carregar as tags e pode ser usado para recarregar elas atualizando a contagem sempre que adicionar um novo
        """
        self._esvaziar_layout(self._lay_tags)

        self.tag_checkboxes.clear()
        tags_com_contagem = self.db.buscar_tags_dinamicas_com_contagem()

        if not tags_com_contagem:
            lbl = QLabel("Nenhuma tag criada.")
            lbl.setFont(fonte(10))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cor_texto(lbl, "#666677")
            self._lay_tags.addSpacing(6)
            self._lay_tags.addWidget(lbl)
            self._lay_tags.addStretch(1)
            return

        for tag, total in tags_com_contagem:
            linha = QWidget()
            lay = QHBoxLayout(linha)
            lay.setContentsMargins(0, 1, 0, 1)
            lay.setSpacing(0)

            cb = CheckBoxModerno(tag, tamanho_fonte=11)
            cb.clicked.connect(lambda: self.resetar_e_filtrar())
            lay.addWidget(cb, 1)

            lbl_qtd = QLabel(str(total))
            lbl_qtd.setMinimumWidth(22)
            lbl_qtd.setFixedHeight(16)
            lbl_qtd.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_qtd.setFont(fonte(10, bold=True))
            lbl_qtd.setStyleSheet("background-color: #22222b; border-radius: 5px; color: #888899; padding: 0px 4px;")
            lay.addWidget(lbl_qtd)
            lay.addSpacing(6)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(18, 18)
            btn_del.setFont(fonte(12))
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(qss_botao("transparent", "#331515", "#ff4d4d", raio=4).replace("padding: 0px 10px", "padding: 0px"))
            btn_del.clicked.connect(lambda _c=False, t=tag: QTimer.singleShot(0, lambda: self.solicitar_exclusao_tag(t)))
            lay.addWidget(btn_del)

            self._lay_tags.addWidget(linha)
            self.tag_checkboxes[tag] = cb
        self._lay_tags.addStretch(1)

    # ------------------------------------------------------------------
    # ACERVO / PAGINAÇÃO
    # ------------------------------------------------------------------
    def escanear_acervo(self, silencioso=False):
        """
        Le todo a pasta raiz e atualiza o banco.
        """
        sincronizar_acervo_disco_com_banco(self.db, self.RAIZ_ACERVO, self.MAPA_PASTAS_EDITORAS)
        if not silencioso:  
            # silencioso=True vem da thread de fundo, que não pode mexer na interface
            self.atualizar_lista_filtrada()

    def sincronizar_pastas(self):
        """Botão "Sincronizar Pastas": Lê todas as pasta definidias no mapa de pastas e atualiza o banco."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.escanear_acervo()
        finally:
            QApplication.restoreOverrideCursor()

    def resetar_e_filtrar(self):
        """
        Usado para atualizar os filtros e mostrar os quadrinhos certos
        reseta para a primeira pagina sempre.

        ESSE É O DIFERENCIAL DELE VOLTAR A PAGINA 1
        """
        self.pagina_atual_grid = 1
        self.atualizar_lista_filtrada()

    def voltar_pagina(self):
        if self.pagina_atual_grid > 1:
            self.pagina_atual_grid -= 1
            self.atualizar_lista_filtrada()

    def avancar_pagina(self):
        if self.pagina_atual_grid < self.total_paginas_grid:
            self.pagina_atual_grid += 1
            self.atualizar_lista_filtrada()


    # ------------------------------------------------------------------
    # LEITOR DE QUADRINHOS
    # ------------------------------------------------------------------
    def abrir_leitor(self, quadrinho):
        leitor = LeitorQuadrinhoModal(self, quadrinho, self.db, self.atualizar_lista_filtrada)
        self._leitores.append(leitor)
        leitor.destroyed.connect(lambda *_: self._leitores.remove(leitor) if leitor in self._leitores else None)
        leitor.abrir()


    # ------------------------------------------------------------------
    # GRADE
    # ------------------------------------------------------------------
    def _calcular_grade(self):
        """Calcula espaço que vai ficar os cards dos quadrinhos (o Qt já trabalha em pixels lógicos)."""
        largura = self.right_container.width()
        altura = self.right_container.height()
        if largura <= 1:  # janela ainda não desenhada
            largura = max(self.width() - LARGURA_SIDEBAR, 600)
        if altura <= 1:
            altura = max(self.height(), 500)
        cfg = self.config_grade
        return calcular_grade(
            largura, altura, self._extra_card_h,
            modo=cfg["modo"], linhas_fixas=cfg["linhas"], colunas_fixas=cfg["colunas"]
        )

    def atualizar_lista_filtrada(self):
        """
        RECARREGA OS QUADRINHOS e TAGS

        A função mais geral de recarregar os quadrinhos.
        """
        colunas, linhas, largura = self._calcular_grade()
        self._grade_atual = (colunas, linhas, largura)
        self.itens_por_pagina = colunas * linhas

        tags_selecionadas = [tag for tag, cb in self.tag_checkboxes.items() if cb.isChecked()]
        ano_de_txt = self.entry_ano_de.text().strip()
        ano_ate_txt = self.entry_ano_ate.text().strip()
        ano_de = int(ano_de_txt) if ano_de_txt.isdigit() else None
        ano_ate = int(ano_ate_txt) if ano_ate_txt.isdigit() else None
        termo = self.entry_busca.text().strip()
        apenas_sem_tags = self.switch_sem_tags.isChecked()

        def consultar():
            return self.db.filtrar_quadrinhos(
                editora_filtro=self.editora_selecionada,
                tags_selecionadas=tags_selecionadas,
                filtro_leitura=self.filtro_leitura,
                ano_de=ano_de,
                ano_ate=ano_ate,
                termo_busca=termo,
                apenas_sem_tags=apenas_sem_tags,
                pagina=self.pagina_atual_grid,
                itens_por_pagina=self.itens_por_pagina
            )

        itens_pagina, total_itens = consultar()
        self.total_paginas_grid = max(1, (total_itens + self.itens_por_pagina - 1) // self.itens_por_pagina)

        # a janela encolheu/cresceu e a página pedida deixou de existir
        if self.pagina_atual_grid > self.total_paginas_grid:
            self.pagina_atual_grid = self.total_paginas_grid
            itens_pagina, total_itens = consultar()

        self.quadrinhos_exibidos = itens_pagina
        self.carregar_grid_quadrinhos(total_itens)

    def _distribuir_cards(self, colunas: int):
        """Posiciona os cards já criados em `colunas` colunas (sem recriá-los)."""
        grade = self._grid_cards
        while grade.count():
            grade.takeAt(0)      # só solta do layout; os widgets continuam vivos
        for i in range(max(colunas, self._cols_atual)):
            grade.setColumnStretch(i, 1 if i < colunas else 0)

        for idx, card in enumerate(self.cards_grade):
            grade.addWidget(card, idx // colunas, idx % colunas,
                            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._cols_atual = colunas

    def _ao_redimensionar_area(self, event=None):
        """Debounce: só recalcula quando a janela para de mudar de tamanho."""
        self._timer_resize.start(DEBOUNCE_MS)

    def _reajustar_grade(self):
        colunas, linhas, largura = self._calcular_grade()
        novos_itens = colunas * linhas

        # Mudou quantos cards cabem na página: refaz a consulta mantendo na tela o primeiro quadrinho que o usuário estava vendo.
        if novos_itens != self.itens_por_pagina:
            primeiro = (self.pagina_atual_grid - 1) * self.itens_por_pagina
            self.pagina_atual_grid = primeiro // novos_itens + 1
            self.atualizar_lista_filtrada()
            return

        self._grade_atual = (colunas, linhas, largura)
        if self.container_grade is None or not self.cards_grade:
            return

        if colunas != self._cols_atual:
            self._distribuir_cards(colunas)
        if abs(largura - self._card_w_atual) >= 2:
            for card in self.cards_grade:
                card.redimensionar(largura)
            self._card_w_atual = largura

    def carregar_grid_quadrinhos(self, total_itens: int):
        antigo = self.main_scroll_area.takeWidget()   # devolve a posse do widget antigo
        if antigo is not None:
            antigo.hide()
            antigo.deleteLater()
        self.cards_grade = []
        self.container_grade = None
        self._grid_cards = None
        self._cols_atual = 0

        self.lbl_paginacao.setText(
            f"Página {self.pagina_atual_grid} de {self.total_paginas_grid} ({total_itens} HQs)"
        )
        self.btn_pag_ant.setEnabled(self.pagina_atual_grid > 1)
        self.btn_pag_prox.setEnabled(self.pagina_atual_grid < self.total_paginas_grid)

        if not self.quadrinhos_exibidos:
            vazio = QWidget()
            lay = QVBoxLayout(vazio)
            lay.setContentsMargins(0, 60, 0, 0)
            lbl = QLabel("Nenhum quadrinho encontrado.")
            lbl.setFont(fonte(14))
            cor_texto(lbl, "#777788")
            lay.addWidget(lbl, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            lay.addStretch(1)
            self.main_scroll_area.setWidget(vazio)
            return

        colunas, _, largura_card = self._grade_atual
        self._card_w_atual = largura_card

        self.container_grade = QWidget()
        self._grid_cards = QGridLayout(self.container_grade)
        self._grid_cards.setContentsMargins(PAD_GRADE, 6 + PAD_GRADE, PAD_GRADE, 6 + PAD_GRADE)
        self._grid_cards.setHorizontalSpacing(2 * PAD_GRADE)
        self._grid_cards.setVerticalSpacing(2 * PAD_GRADE)

        for hq in self.quadrinhos_exibidos:
            card = ComicCard(
                parent=self.container_grade,
                quadrinho=hq,
                db=self.db,
                callback_refresh=self.atualizar_lista_filtrada,
                callback_tags=self.carregar_tags_dinamicas,
                abrir_leitor_callback=self.abrir_leitor,
                largura=largura_card
            )
            self.cards_grade.append(card)

        self._distribuir_cards(colunas)

        # o container ocupa só a altura dos cards; o resto da área fica vazio embaixo
        pagina = QWidget()
        lay_pagina = QVBoxLayout(pagina)
        lay_pagina.setContentsMargins(0, 0, 0, 0)
        lay_pagina.setSpacing(0)
        lay_pagina.addWidget(self.container_grade)
        lay_pagina.addStretch(1)
        self.main_scroll_area.setWidget(pagina)

        # Mede UMA vez a altura real dos textos do card para o cálculo de linhas ficar exato.
        if not self._extra_medido:
            self._extra_medido = True
            altura_capa = round((largura_card - MARGEM_HORIZONTAL) * PROPORCAO_CAPA)
            medido = self.cards_grade[0].sizeHint().height() - altura_capa
            if abs(medido - self._extra_card_h) > 3:
                self._extra_card_h = medido
                QTimer.singleShot(50, self._reajustar_grade)

    # ------------------------------------------------------------------
    # CONFIGURAÇÕES
    # ------------------------------------------------------------------
    def carregar_ou_configurar_inicial(self):
        """Tenta carregar as configs; se não existirem, abre o modal de configuração."""
        try:
            self.RAIZ_ACERVO, self.EDITORAS, self.MAPA_PASTAS_EDITORAS = carregar_configuracoes()
        except (FileNotFoundError, JSONDecodeError):
            print("[AVISO] Configurações não encontradas. Abrindo modal inicial...")

            modal = ConfiguracoesModal(parent=self, funcao_salvar_callback=salvar_configuracoes)
            modal.exec()

            try:
                self.RAIZ_ACERVO, self.EDITORAS, self.MAPA_PASTAS_EDITORAS = carregar_configuracoes()
            except Exception as e:
                print(f"[ERRO CRÍTICO] Falha ao carregar as configurações após salvar: {e}")
                sys.exit(1)

    def abrir_modal_configuracoes(self):
        """Método reutilizável para abrir o modal de configurações por um botão no app."""
        configs_atuais = {
            "pasta_raiz": self.RAIZ_ACERVO,
            "editoras": self.EDITORAS,
            "mapa_pastas_editoras": self.MAPA_PASTAS_EDITORAS,
            "grade": self.config_grade
        }

        modal = ConfiguracoesModal(
            parent=self,
            funcao_salvar_callback=salvar_configuracoes,
            configs_atuais=configs_atuais
        )
        modal.exec()

        try:
            self.RAIZ_ACERVO, self.EDITORAS, self.MAPA_PASTAS_EDITORAS = carregar_configuracoes()
        except Exception:
            pass


        self.config_grade = carregar_config_grade()
        self.escanear_acervo()
        self._reajustar_grade()

    def validar_descompactador(self, ligar):
        """
        Se o switch estiver ligado(azul) ele abre o descompactador, se estiver desligado(cinza) ele fecha.
        Se for fechado pelo X ele atualiza o switch para cinza sem bugar.        
        """
        
        abrir_descompactador(ligar, self.switch_descompactador)

        self.escanear_acervo()