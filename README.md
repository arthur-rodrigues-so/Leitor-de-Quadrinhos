# Gerenciador & Leitor de Quadrinhos
Gerenciador e leitor local de quadrinhos focado em **COLETÂNEAS DE VARÍOS QUADRINHOS**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://wiki.qt.io/Qt_for_Python)
[![C](https://img.shields.io/badge/Engine-C%20%2B%20Raylib-00599C?style=for-the-badge&logo=c&logoColor=white)](https://www.raylib.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

*Gerenciador e Leitor de Quadrinhos* feito para **grandes quantidades de edições**. O sistema lê suas bibliotecas em massa, cataloga pasta por editoras e permite descompactar, ler, categorizar e até mesmo liberar espaço em disco mantendo um registro visual permanente de tudo o que já foi lido.

> [!IMPORTANT]
> Não foi feito para Linux funciona somente para Windows.

## Principais Funcionalidades

- **Organização por Coletâneas:**
  - O sistema detecta dinamicamente qualquer pasta determinada no mapeamente de pastas `NOME_PASTA_DISCO:EDITORA` e adiciona como uma *Tag Fixa*.
- **Tags Dinâmicas com Contagem em Tempo Real:**
  - Crie tags personalizadas (*Batman*, *Frank Miller*, *Clássicos*, *Sagas*) e filtre instantaneamente. Um contador visual ao lado da tag mostra quantas edições pertencem àquela categoria.
- **Descompactador Dedicado em C:**
  - Integração com um aplicativo escrito em **C com Raylib e Libarchive** para descompactar arquivos **cbz e cbr**, trazendo somente as imagens organizadas em sequência numérica. O Python compila o código fonte em C automaticamente na primeira execução do descompactador!
- **Migração Inteligente de Descompactação:**
  - Ao descompactar uma edição e o Windows renomear a pasta para `(Descompactada)`, o sistema reconhece a mudança e **preserva 100% das suas tags, ano e a página onde você parou**, sem duplicar o quadrinho.
- **Leitor Nativo:**
  - Desenvolvido para eliminar distorções de DPI do Windows em monitores tamanhos diferentes permitindo varias resoluções e milhares de paginas sem travamento.
  - **Zoom no Cursor:** Usa a roda do mouse (`Scroll`) para aproximar balões de fala minúsculos diretamente onde o ponteiro estiver, arraste a página com o botão esquerdo e resete com duplo clique.
- **Histórico Permanente & "Economia de Disco":**
  - Quando terminar um quadrinho, use a opção **Liberar Espaço**. O app salva a capa no cofre permanente de histórico, apaga os gigabytes de imagens brutas do HD e mantém o quadrinho na sua galeria com o selo **`✓ LIDO (ARQUIVADO)`**.
- **Performance Instantânea:**
  - As capas são indexadas no banco local (`SQLite3` em modo WAL) e cacheadas em disco (`.cache_hqs/`). Zero congelamentos ou leituras repetidas do disco rígido.

## 📁 Estrutura de Pastas Recomendada

O LetQuadrinhos espera que suas HQs estejam agrupadas dentro de uma estrutura parecida com essa:

```text
D:\Emulador\HQ\
├── COLETANIA DC\
│   ├── 1987 - Batman Ano Um (Descompactada)\
│   │   ├── 001.jpg
│   │   └── 002.jpg
│   └── 1993 - A Queda do Morcego\
│       └── A Queda do Morcego.cbz
├── COLETANIA MARVEL\
│   └── 1984 - Guerras Secretas (Descompactada)\
│       ├── 01.png
│       └── 02.png
```

- A pasta raiz (`D:\Emulador\HQ\`) e o mapa de pastas (`COLETANIA DC`) são modificáveis na parte de configurações do aplicativo. 
- O ano (`0000 - `) é opcional e serve apenas para que já venha pré-definido no quadrinho. `Descompactada` no nome da pasta é obrigatório para o leitor ser desbloqueado e aparecer a opção de ler. 

> [!IMPORTANT]
> Evite arquivos de imagens diretamente no *mapa de pastas* ou elas serão carregas como se fossem um quadrinho com o nome da pasta por conta de considerar qualquer pasta com imagem dentro como um quadrinho.

# Como Rodar o Projeto

## Pré-requisitos
- Python 3.10 ou superior instalado.
- GCC (MinGW-w64) instalado no Windows e adicionado ao PATH (necessário apenas para a compilação automática do descompactador em C na primeira execução).

##  Passo a Passo
1. Clone o Repositório:
```Bash
git clone https://github.com/arthur-rodrigues-so/Leitor-de-Quadrinhos.git
cd Leitor-de-Quadrinhos
```

2. Crie e Ative um Ambiente Virtual (Opcional, mas recomendado):
```python
python -m venv venv

.\venv\Scripts\Activate.ps1
```

3. Instale as Dependências Python:
```Bash
pip install -r requirements.txt
```
(Dependências principais: `PySide6`, `Pillow`)

### Rodar via terminal
4. Rode no terminal dentro da pasta.
```Bash
python main.py
```
> [!NOTE] 
Na primeira vez que executar o programa e abrir o descompactador, o script detectará automaticamente o código-fonte dentro de `C/`, invocará o `gcc` silenciosamente e criará o executável dentro da pasta `.local_files/`.

### Compilar para rodar via executavel
4. Rode no terminal dentro da pasta.
```Bash
pyinstaller --noconsole --add-data "./assets:assets" --add-data "./c:c" --name="LetQuadrinhos" -i assets/icone.ico main.py
``` 

#### O que cada argumento faz?
 - `--noconsole`: Oculta a janela do terminal.
 - `--add-data`: Inclui pastas/arquivos extras necessários para rodar o projeto(no formato *origem_arquivo:destino_arquivo*).
 - `--name`: Define o nome da pasta/executável gerado.
 - `i`: Define o ícone personalizado do aplicativo.

> [!TIP]
> Dica: Não utilze `--onefile` por sempre após finalizar ele apagar a pasta temporaria os dados não ficam salvos. 


## Arquivos
### Local
O sistema gera a pasta automaticamente `.local_files` nela são guardado: 
- O `.cache_hqs` pastas para salvar as capas dos quadrinhos.
- O `historico_permanente` pasta para salvar as capas dos quadrinhos arquivados.    
- O `banco.db` pequeno banco de dados para as tags e quadrinhos. 
- O `config.json` arquivo de configuração com o caminho da pasta raiz, mapa de pastas, editoras e disposição da grade de exibição dos quadrinhos.

### Assets
Caso que modificar as imagens dos icones é necessário manter os exatos mesmo nomes.
- Aplicativo Principal:
  - `icone.ico`: Icone para o aplicativo principal
- Aplicativo Descompactador:
  - `icone_descompactador.ico` 
  - `icone_descompactador.png`

## Planos futuros
- [ ] Versão Web/Local Server com FastAPI + Uvicorn para leitura remota via computador, celular ou tablet no Wi-Fi.
- [ ] Modo multi-usuário com perfis independentes de leitura e tags excluisvas.

## Licença
**O aplicativo não fornece nenhum quadrinho só serve para organizar. Pode usar e mexer tranquilo.**