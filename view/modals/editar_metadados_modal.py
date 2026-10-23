"""
==============================================================================
 EDITAR METADADOS (TAGS) - Qt
==============================================================================
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from database.sqlal import DatabaseGerenciador
from view.estilo import BTN_PADRAO, BTN_PADRAO_HOVER, cor_texto, fonte, qss_botao, qss_entry
from view.modals.confirmar_exclusao_modal import ConfirmarExclusaoModal
from view.widgets import CheckBoxModerno, LineEditTecla, ScrollAreaRapida


class EditarMetadadosModal(QDialog):
    """Abra com .exec()."""

    def __init__(self, parent, quadrinho, db: DatabaseGerenciador, callback_atualizacao, callback_atualizar_tags):
        super().__init__(parent)
        self.parent_app = parent
        self.quadrinho = quadrinho
        self.db = db
        self.callback_atualizacao = callback_atualizacao
        self.callback_atualizar_tags = callback_atualizar_tags

        self.setWindowTitle("Gerenciar Quadrinho")
        self.setFixedSize(440, 510)
        self.setModal(True)

        tags_tuplas = self.db.buscar_tags_dinamicas_com_contagem()
        self.todas_tags = [t[0] for t in tags_tuplas]
        tags_atuais = set(self.db.buscar_tags_do_quadrinho(self.quadrinho.id))

        self.checkboxes = {}
        self.tag_frames = {}

        self.criar_widgets(tags_atuais)

    def criar_widgets(self, tags_atuais):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 8)
        layout.setSpacing(0)

        lbl_titulo = QLabel("Gerenciar Quadrinho")
        lbl_titulo.setFont(fonte(16, bold=True))
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)
        layout.addSpacing(2)

        lbl_sub = QLabel(self.quadrinho.titulo_limpo)
        lbl_sub.setFont(fonte(11, italic=True))
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cor_texto(lbl_sub, "gray")
        layout.addWidget(lbl_sub)
        layout.addSpacing(6)

        # ANO
        linha_ano = QHBoxLayout()
        linha_ano.setContentsMargins(0, 0, 0, 0)
        linha_ano.addWidget(QLabel("Ano:"))
        linha_ano.addSpacing(8)
        self.entry_ano = LineEditTecla()
        self.entry_ano.setFixedSize(90, 28)
        self.entry_ano.setStyleSheet(qss_entry())
        if self.quadrinho.ano:
            self.entry_ano.setText(str(self.quadrinho.ano))
        linha_ano.addWidget(self.entry_ano)
        linha_ano.addStretch(1)
        layout.addLayout(linha_ano)
        layout.addSpacing(6)

        # TAGS
        lbl_tags = QLabel("Tags Existentes:")
        lbl_tags.setFont(fonte(13, bold=True))
        layout.addSpacing(4)
        layout.addWidget(lbl_tags)
        layout.addSpacing(2)

        self.entry_busca_tag = LineEditTecla()
        self.entry_busca_tag.setPlaceholderText("🔍 Filtrar tags...")
        self.entry_busca_tag.setFixedHeight(28)
        self.entry_busca_tag.setStyleSheet(qss_entry())
        self.entry_busca_tag.tecla_solta.connect(self.filtrar_tags_ui)
        layout.addWidget(self.entry_busca_tag)
        layout.addSpacing(6)

        moldura = QFrame()
        moldura.setObjectName("molduraTags")
        moldura.setStyleSheet("QFrame#molduraTags { background-color: #181820; border-radius: 6px; }")
        lay_moldura = QVBoxLayout(moldura)
        lay_moldura.setContentsMargins(4, 4, 4, 4)

        self.scroll_tags_box = ScrollAreaRapida()
        self.scroll_tags_box.setMinimumHeight(140)
        conteudo = QWidget()
        self._lay_tags = QVBoxLayout(conteudo)
        self._lay_tags.setContentsMargins(0, 0, 0, 0)
        self._lay_tags.setSpacing(0)

        for t in self.todas_tags:
            frame_item = QWidget()
            lay_item = QHBoxLayout(frame_item)
            lay_item.setContentsMargins(5, 2, 0, 2)

            cb = CheckBoxModerno(t, tamanho_fonte=11)
            cb.setChecked(t in tags_atuais)
            lay_item.addWidget(cb)
            lay_item.addStretch(1)

            self._lay_tags.addWidget(frame_item)
            self.checkboxes[t] = cb
            self.tag_frames[t] = frame_item
        self._lay_tags.addStretch(1)

        self.scroll_tags_box.setWidget(conteudo)
        lay_moldura.addWidget(self.scroll_tags_box)
        layout.addWidget(moldura, 1)
        layout.addSpacing(10)

        btn_salvar = QPushButton("Salvar Alterações")
        btn_salvar.setFixedHeight(30)
        btn_salvar.setFont(fonte(13))
        btn_salvar.setStyleSheet(qss_botao(BTN_PADRAO, BTN_PADRAO_HOVER, "#ffffff", raio=6))
        btn_salvar.clicked.connect(self.salvar)
        layout.addWidget(btn_salvar)
        layout.addSpacing(8)

        if self.quadrinho.arquivado:
            lbl = QLabel("✓ Arquivos já excluídos")
            lbl.setFont(fonte(10))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cor_texto(lbl, "#2ec4b6")
            layout.addWidget(lbl)
        elif self.quadrinho.lido:
            btn_apagar_disco = QPushButton("🗑 Liberar Espaço no Disco e Manter no Histórico")
            btn_apagar_disco.setFixedHeight(30)
            btn_apagar_disco.setFont(fonte(13))
            btn_apagar_disco.setStyleSheet(qss_botao("#6c2225", "#8b262a", "#ffffff", raio=6))
            btn_apagar_disco.clicked.connect(self.solicitar_arquivamento)
            layout.addWidget(btn_apagar_disco)
            layout.addSpacing(2)
        else:
            lbl = QLabel("Quadrinho Não Lido Completamente")
            lbl.setFont(fonte(10))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cor_texto(lbl, "#d40e0e")
            layout.addWidget(lbl)

    def solicitar_arquivamento(self):
        ConfirmarExclusaoModal(
            parent=self,
            titulo_aviso="Liberar Espaço no Disco?",
            mensagem="Isso excluirá os arquivos de imagens desta HQ para economizar espaço no seu PC.\n\nA capa e o registro de leitura ficarão salvos no Histórico para sempre!",
            texto_btn="Excluir Arquivos",
            cor_btn="#d90429",
            callback_confirmar=self.executar_arquivamento
        ).exec()

    def executar_arquivamento(self):
        if self.db.arquivar_e_apagar_arquivos(self.quadrinho.id):
            self.callback_atualizacao()
            self.accept()

    def filtrar_tags_ui(self, event=None):
        busca = self.entry_busca_tag.text().strip().upper()
        for tag, frame in self.tag_frames.items():
            frame.setVisible(busca in tag)

    def salvar(self):
        ano_str = self.entry_ano.text().strip()
        ano_val = int(ano_str) if ano_str.isdigit() else None
        tags_escolhidas = [tag for tag, cb in self.checkboxes.items() if cb.isChecked()]

        self.db.atualizar_metadados(self.quadrinho.id, ano_val, tags_escolhidas)
        self.callback_atualizacao()

        self.callback_atualizar_tags()
        self.accept()
