"""
==============================================================================
 MODAL DE CONFIRMAÇÃO DE EXCLUSÃO (Qt)
==============================================================================
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from view.estilo import cor_texto, fonte, qss_botao


class ConfirmarExclusaoModal(QDialog):
    """Abra com .exec(). O callback roda ao confirmar, antes de fechar (igual ao original)."""

    def __init__(self, parent, titulo_aviso: str, mensagem: str, texto_btn: str, cor_btn: str, callback_confirmar):
        super().__init__(parent)
        self.callback_confirmar = callback_confirmar

        self.setWindowTitle("Confirmação")
        self.setFixedSize(400, 190)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(0)

        lbl_titulo = QLabel(titulo_aviso)
        lbl_titulo.setFont(fonte(16, bold=True))
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)
        layout.addSpacing(6)

        lbl_msg = QLabel(mensagem)
        lbl_msg.setFont(fonte(12))
        lbl_msg.setWordWrap(True)
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        lbl_msg.setMaximumWidth(350)
        cor_texto(lbl_msg, "#c0c0c0")
        layout.addWidget(lbl_msg, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

        botoes = QHBoxLayout()
        botoes.setContentsMargins(0, 0, 0, 0)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedSize(120, 32)
        btn_cancelar.setFont(fonte(13))
        btn_cancelar.setStyleSheet(qss_botao("#33333e", "#444452", "#ffffff", raio=6))
        btn_cancelar.clicked.connect(self.reject)

        btn_acao = QPushButton(texto_btn)
        btn_acao.setFixedSize(140, 32)
        btn_acao.setFont(fonte(13))
        btn_acao.setStyleSheet(qss_botao(cor_btn, "#b00020", "#ffffff", raio=6))
        btn_acao.clicked.connect(self.confirmar)

        # cada botão centralizado na sua metade (o `expand=True` do pack original)
        botoes.addStretch(1)
        botoes.addWidget(btn_cancelar)
        botoes.addStretch(2)
        botoes.addWidget(btn_acao)
        botoes.addStretch(1)
        layout.addLayout(botoes)

    def confirmar(self):
        self.callback_confirmar()
        self.accept()
