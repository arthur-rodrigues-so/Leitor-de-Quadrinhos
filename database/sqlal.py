import os

from typing import List, Tuple, Optional

from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, not_, and_, event

from database.modals import Base, Quadrinho, Tag
from config.constantes import BANCO_DADOS

from service.arquivamento import processar_arquivamento_fisico

class DatabaseGerenciador:
    def __init__(self, editoras_fixas, db_path: str = BANCO_DADOS):
        self.EDITORAS_FIXAS = editoras_fixas
        
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"timeout": 30.0, "check_same_thread": False},
            poolclass=QueuePool
        )

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = -64000")
            cursor.execute("PRAGMA temp_store = MEMORY")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)


    def salvar_ou_migrar_quadrinho(self, caminho: str, caminho_capa: Optional[str], titulo: str, editora: str, ano: Optional[int], total_pags: int, descompactada: bool, tem_imagens: bool):
        """
        Cadastra um novo quadrinho no banco ou atualiza/migra um registro preexistente.

        Comportamento dual:
        1. MODO ATUALIZAÇÃO (Mesmo Caminho):
           - Se a pasta já estiver cadastrada e ativa, sincroniza metadados físicos 
             (capa, páginas, status de compactação e presença de imagens) preservando 
             dados de leitura e tags manuais.
           - Se o quadrinho já estiver arquivado, aborta a operação sem sobrescrever nada.
        
        2. MODO MIGRAÇÃO/RECONEXÃO (Pasta Movida ou Renomeada):
           - Se o caminho não for achado, procura por registros órfãos que possuam o mesmo 
             título e editora mas cuja pasta antiga não exista mais no disco.
           - Caso encontre, 'reconecta' o histórico e o progresso daquele quadrinho 
             ao novo caminho de pasta sem criar itens duplicados.
        
        3. MODO CRIAÇÃO (Novo Registro):
           - Se nenhuma das condições anteriores for atendida, cria um novo quadrinho do zero.

        :param caminho: Caminho absoluto da pasta física do quadrinho.
        :param caminho_capa: Caminho da primeira imagem encontrada para servir de miniatura.
        :param titulo: Nome limpo deduzido da pasta (sem sufixos como '(descompactada)').
        :param editora: Tag da editora mapeada.
        :param ano: Ano detectado pelo regex no nome da pasta ou None.
        :param total_pags: Quantidade de páginas/imagens válidas encontradas.
        :param descompactada: Flag indicando se a pasta está pronta para leitura imediata.
        :param tem_imagens: Flag indicando se há imagens válidas para exibição.
        """
        with self.SessionLocal() as session:
            quadrinho = session.query(Quadrinho).filter_by(caminho_pasta=caminho).first()

            if quadrinho:
                if quadrinho.arquivado:
                    return
                
                quadrinho.caminho_capa = caminho_capa
                quadrinho.titulo_limpo = titulo
                quadrinho.editora = editora

                if quadrinho.ano is None:
                    quadrinho.ano = ano

                quadrinho.total_paginas = total_pags
                quadrinho.descompactada = descompactada
                quadrinho.tem_imagens = tem_imagens

                session.commit()
                return
            
            candidatos = session.query(Quadrinho).filter_by(editora=editora, titulo_limpo=titulo).all()
            for cand in candidatos:
                if not cand.arquivado and not os.path.exists(cand.caminho_pasta):
                    cand.caminho_pasta = caminho
                    cand.caminho_capa = caminho_capa
                    cand.total_paginas = total_pags
                    cand.descompactada = descompactada
                    cand.tem_imagens = tem_imagens
                    session.commit()
                    return

            novo_hq = Quadrinho(
                caminho_pasta=caminho,
                caminho_capa=caminho_capa,
                titulo_limpo=titulo,
                editora=editora,
                ano=ano,
                total_paginas=total_pags,
                descompactada=descompactada,
                tem_imagens=tem_imagens
            )

            session.add(novo_hq)
            session.commit()

    def arquivar_e_apagar_arquivos(self, quadrinho_id: int) -> bool:
        """
        Executa a rotina permanente de finalização e liberação de espaço em disco.

        Comportamento dual:
        1. MANIPULAÇÃO DE ARQUIVOS (Disco):
           - Copia e converte a capa atual para uma pasta estática permanente (`PASTA_HISTORICO`)
             usando um hash seguro, garantindo que o visual do card não seja perdido.
           - Remove fisicamente do disco toda a pasta descompactada para liberar espaço.
        
        2. ATUALIZAÇÃO DE REGISTRO (Banco de Dados):
           - Marca o quadrinho como lido (`lido = True`) e arquivado (`arquivado = True`).
           - Redefine flags de leitura imediata (`descompactada = False`, `tem_imagens = False`)
             e aponta a capa para a nova miniatura estática salva no histórico.

        :param quadrinho_id: ID primário do quadrinho a ser arquivado.
        :return: True se a operação foi concluída com sucesso; False se o ID não existir.
        """
        with self.SessionLocal() as session:
            quadrinho = session.get(Quadrinho, quadrinho_id)
            if not quadrinho:
                return False

            caminho_pasta = quadrinho.caminho_pasta
            caminho_capa = quadrinho.caminho_capa
            nova_capa_permanente = None

            
            processar_arquivamento_fisico(quadrinho_id, caminho_capa, caminho_pasta)

            quadrinho.arquivado = True
            quadrinho.lido = True
            quadrinho.caminho_capa = nova_capa_permanente
            quadrinho.descompactada = False
            quadrinho.tem_imagens = False
            
            session.commit()
            return True

    def limpar_pastas_obsoletas(self, caminhos_validos: set):
        """
        LIMPA QUADRINHOS QUE JÁ FORAM ARQUIVADOS 
        """
        with self.SessionLocal() as session:
            todos = session.query(Quadrinho).all()
            for row in todos:
                if not row.arquivado and row.caminho_pasta not in caminhos_validos:
                    session.delete(row)
            session.commit()

    def criar_tag_manual(self, nome_tag: str):
        """
        CRIA A TAG DINAMICA
        """
        nome_tag = nome_tag.strip().upper()
        if not nome_tag:
            return
        with self.SessionLocal() as session:
            existe = session.query(Tag).filter_by(nome_tag=nome_tag).first()
            if not existe:
                session.add(Tag(nome_tag=nome_tag))
                session.commit()

    def deletar_tag_manual(self, nome_tag: str):
        """
        APAGA A TAG DINAMICA
        """
        with self.SessionLocal() as session:
            tag = session.query(Tag).filter_by(nome_tag=nome_tag).first()
            if tag:
                session.delete(tag)
                session.commit()

    def atualizar_metadados(self, quadrinho_id: int, ano: Optional[int], tags_selecionadas: List[str]):
        with self.SessionLocal() as session:
            quadrinho = session.get(Quadrinho, quadrinho_id)
            if not quadrinho:
                return

            quadrinho.ano = ano
            tags_objs = session.query(Tag).filter(Tag.nome_tag.in_(tags_selecionadas)).all()
            quadrinho.tags = tags_objs
            session.commit()

    def atualizar_progresso_leitura(self, quadrinho_id: int, pagina: int, total_paginas: int):
        """
        ATUALIZA A PAGINA QUE ESTÁ LENDO
        """
        with self.SessionLocal() as session:
            quadrinho = session.get(Quadrinho, quadrinho_id)
            if not quadrinho:
                return

            quadrinho.pagina_atual = pagina
            quadrinho.total_paginas = total_paginas
            
            if total_paginas > 0 and pagina >= total_paginas:
                quadrinho.lido = True
            
            session.commit()

    def buscar_tags_dinamicas_com_contagem(self) -> List[Tuple[str, int]]:
        with self.SessionLocal() as session:
            
            resultado = (
                session.query(Tag.nome_tag, func.count(Quadrinho.id).label("total"))
                .outerjoin(Tag.quadrinhos)
                .filter(not_(Tag.nome_tag.in_(self.EDITORAS_FIXAS)))
                .group_by(Tag.id, Tag.nome_tag)
                .order_by(Tag.nome_tag.asc())
                .all()
            )
            return [(row.nome_tag, row.total) for row in resultado]

    def buscar_tags_do_quadrinho(self, quadrinho_id: int) -> List[str]:
        with self.SessionLocal() as session:
            quadrinho = session.get(Quadrinho, quadrinho_id)
            if not quadrinho:
                return []
            return [tag.nome_tag for tag in quadrinho.tags]

    def filtrar_quadrinhos(self, 
                           editora_filtro: str = "TODAS", 
                           tags_selecionadas: Optional[List[str]] = None, 
                           filtro_leitura: str = "TODOS", 
                           ano_de: Optional[int] = None, 
                           ano_ate: Optional[int] = None, 
                           termo_busca: str = "", 
                           apenas_sem_tags: bool = False,
                           pagina: int = 1,
                           itens_por_pagina: int = 24) -> List[Quadrinho]:
        """
        Executa a filtragem combinada de quadrinhos com paginação nativa em nível SQL.

        Comportamento dual de filtragem de tags:
        - Se `apenas_sem_tags=True`: Isola quadrinhos que não possuem nenhum vínculo com a tabela de tags 
          (útil para identificar aquisições novas não catalogadas).
        - Se `tags_selecionadas` tiver itens: Executa JOIN e busca itens que contenham as tags informadas.

        Comportamento de paginação:
        - Executa internamente duas operações em uma única chamada:
          1. `COUNT(*)` com os filtros aplicados (rápido, sem carregar instâncias ORM na memória).
          2. Consulta paginada usando `LIMIT` e `OFFSET` para trazer apenas os objetos visíveis no grid.

        :param editora_filtro: Nome da editora fixa ou 'TODAS'.
        :param tags_selecionadas: Lista de nomes de tags dinâmicas para filtrar.
        :param filtro_leitura: Estado de leitura ('TODOS', 'LENDO' ou 'LIDOS').
        :param ano_de: Ano mínimo de lançamento (inclusivo).
        :param ano_ate: Ano máximo de lançamento (inclusivo).
        :param termo_busca: Texto para busca parcial (case-insensitive) no título.
        :param apenas_sem_tags: Se True, ignora `tags_selecionadas` e traz apenas itens sem tags.
        :param pagina: Página atual solicitada pela UI (base 1).
        :param itens_por_pagina: Limite de registros retornados por página.
        :return: Tupla contendo: (Lista de instâncias Quadrinho da página, Total absoluto de registros encontrados).
        """
        with self.SessionLocal() as session:
            query = session.query(Quadrinho)
            
            # EDITORA
            if editora_filtro != "TODAS":
                query = query.filter(Quadrinho.editora == editora_filtro)

            # FILTRO LEITURA
            if filtro_leitura == "LENDO":
                query = query.filter(and_(Quadrinho.lido == False, Quadrinho.arquivado == False, Quadrinho.pagina_atual > 0))
            elif filtro_leitura == "LIDOS":
                query = query.filter(Quadrinho.lido == True)

            # FILTROS DE TAGS DINAMICAS
            if apenas_sem_tags:
                query = query.filter(~Quadrinho.tags.any())
            elif tags_selecionadas:
                query = query.join(Quadrinho.tags).filter(Tag.nome_tag.in_(tags_selecionadas)).distinct()

            # FILTRO POR ANO
            if ano_de is not None:
                query = query.filter(Quadrinho.ano >= ano_de)
            if ano_ate is not None:
                query = query.filter(Quadrinho.ano <= ano_ate)

            # FILTRO POR BUSCA
            if termo_busca:
                query = query.filter(Quadrinho.titulo_limpo.like(f"%{termo_busca}%"))

            total_registros = query.count()

            offset_val = (pagina - 1) * itens_por_pagina
            
            quadrinhos_pagina = (
                query.order_by(Quadrinho.titulo_limpo.asc())
                .offset(offset_val)
                .limit(itens_por_pagina)
                .all()
            )

            return quadrinhos_pagina, total_registros