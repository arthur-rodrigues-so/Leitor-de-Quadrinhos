from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

quadrinho_tags = Table(
    "quadrinho_tags",
    Base.metadata,
    Column("quadrinho_id", Integer, ForeignKey("quadrinhos.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

class Quadrinho(Base):
    __tablename__ = "quadrinhos"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    caminho_pasta = Column("caminho_pasta", String, unique=True, nullable=False, index=True) 
    caminho_capa = Column("caminho_capa", String) 
    titulo_limpo = Column("titulo_limpo", String, nullable=False, index=True)
    editora = Column("editora", String, nullable=False, index=True)
    ano = Column("ano", Integer, default=None, index=True)
    pagina_atual = Column("pagina_atual", Integer, default=0)
    total_paginas = Column("total_paginas", Integer, default=0)
    lido = Column("lido", Boolean, default=False)
    arquivado = Column("arquivado", Boolean, default=False)
    descompactada = Column("descompactada", Boolean, default=False)
    tem_imagens = Column("tem_imagens", Boolean, default=False)

    tags = relationship("Tag", secondary=quadrinho_tags, back_populates="quadrinhos", lazy="selectin")


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column("id", Integer, autoincrement=True, primary_key=True)
    nome_tag = Column("nome_tag", String, unique=True, nullable=False)

    quadrinhos = relationship("Quadrinho", secondary=quadrinho_tags, back_populates="tags", lazy="selectin")