#include "extrator.h"
#include <windows.h>
#include <shlwapi.h>
#include <archive.h>
#include <archive_entry.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <dirent.h>
#include <direct.h>

#define MAX_PAGINAS 5000

ItemLista listaAtual[MAX_ITENS];
int totalItens = 0;
char diretorioAtual[MAX_CAMINHO];
char mensagemStatus[256] = "Pronto. Navegue e aperte ENTER para extrair.";
char paginas[MAX_PAGINAS][256];

char historicoExtraidos[MAX_ITENS][MAX_CAMINHO];
int totalHistorico = 0;

/* Padroniza todas as barras para '/' facilitando comparacoes */
void normalizarCaminho(char *destino, const char *origem) {
    int i = 0;
    while (origem[i] != '\0' && i < MAX_CAMINHO - 1) {
        destino[i] = (origem[i] == '\\') ? '/' : origem[i];
        i++;
    }
    destino[i] = '\0';
}

/* Cria toda a arvore de pastas recursivamente */
void criarDiretoriosRecursivo(const char *caminho) {
    char temp[MAX_CAMINHO];
    normalizarCaminho(temp, caminho);

    size_t len = strlen(temp);
    if (len == 0) return;
    if (temp[len - 1] == '/') temp[--len] = '\0';
    if (len == 0) return;

    for (char *p = temp + 1; *p; p++) {
        if (*p == '/') {
            if (*(p - 1) == ':') continue; /* Ignora a letra do disco */
            *p = '\0';
            _mkdir(temp);
            *p = '/';
        }
    }
    _mkdir(temp);
}

/* Verifica se o caminho ja esta dentro de D:/Emulador/HQ/CBR e retorna o subcaminho relativo */
int estaDentroDeCBR(const char *caminho, char *subcaminhoOut) {
    char camNorm[MAX_CAMINHO], baseCbrNorm[MAX_CAMINHO], raizNorm[MAX_CAMINHO];
    normalizarCaminho(camNorm, caminho);
    normalizarCaminho(raizNorm, PASTA_RAIZ);
    snprintf(baseCbrNorm, sizeof(baseCbrNorm), "%s/CBR", raizNorm);

    size_t lenBase = strlen(baseCbrNorm);
    if (_strnicmp(camNorm, baseCbrNorm, lenBase) == 0) {
        if (camNorm[lenBase] == '/' || camNorm[lenBase] == '\0') {
            const char *rel = camNorm + lenBase;
            if (*rel == '/') rel++;
            if (subcaminhoOut) strcpy(subcaminhoOut, rel);
            return 1;
        }
    }
    return 0;
}

/* Extrai o subcaminho relativo a partir de PASTA_RAIZ (D:/Emulador/HQ) */
int obterSubcaminhoRaiz(const char *caminho, char *subcaminhoOut) {
    char camNorm[MAX_CAMINHO], raizNorm[MAX_CAMINHO];
    normalizarCaminho(camNorm, caminho);
    normalizarCaminho(raizNorm, PASTA_RAIZ);

    size_t lenRaiz = strlen(raizNorm);
    if (_strnicmp(camNorm, raizNorm, lenRaiz) == 0 &&
        (camNorm[lenRaiz] == '/' || camNorm[lenRaiz] == '\0')) {
        const char *rel = camNorm + lenRaiz;
        if (*rel == '/') rel++;
        if (subcaminhoOut) strcpy(subcaminhoOut, rel);
        return 1;
    }
    return 0;
}

int foiExtraido(const char *caminho) {
    for (int i = 0; i < totalHistorico; i++) {
        if (strcmp(historicoExtraidos[i], caminho) == 0) return 1;
    }
    return 0;
}

void registrarExtraido(const char *caminho) {
    if (foiExtraido(caminho)) return;

    int livre = -1;
    for (int i = 0; i < totalHistorico; i++) {
        if (historicoExtraidos[i][0] == '\0') { livre = i; break; }
    }
    if (livre < 0) {
        if (totalHistorico >= MAX_ITENS) return;
        livre = totalHistorico++;
    }
    snprintf(historicoExtraidos[livre], MAX_CAMINHO, "%s", caminho);
}

static int compararNomes(const void *a, const void *b) {
    WCHAR str1[256] = {0}, str2[256] = {0};
    MultiByteToWideChar(CP_ACP, 0, (const char*)a, -1, str1, 256);
    MultiByteToWideChar(CP_ACP, 0, (const char*)b, -1, str2, 256);
    return StrCmpLogicalW(str1, str2);
}

int compararItensMenu(const void *a, const void *b) {
    ItemLista *itemA = (ItemLista *)a;
    ItemLista *itemB = (ItemLista *)b;

    if (itemA->tipo != itemB->tipo) {
        return itemA->tipo - itemB->tipo;
    }

    WCHAR str1[256], str2[256];
    MultiByteToWideChar(CP_ACP, 0, itemA->nome, -1, str1, 256);
    MultiByteToWideChar(CP_ACP, 0, itemB->nome, -1, str2, 256);
    return StrCmpLogicalW(str1, str2);
}

int obterProximoNumero(const char *pasta) {
    int maxNum = 0;
    DIR *dir = opendir(pasta);
    if (!dir) return 1;
    struct dirent *ent;
    while ((ent = readdir(dir)) != NULL) {
        int num = atoi(ent->d_name);
        if (num > maxNum) maxNum = num;
    }
    closedir(dir);
    return maxNum + 1;
}

static int montarCaminho(char *dst, size_t cap, const char *dir, const char *nome) {
    int n = snprintf(dst, cap, "%s/%s", dir, nome);
    return n > 0 && (size_t)n < cap;
}

static void limparPastaSegura(const char *pasta) {
    DIR *dir = opendir(pasta);
    if (!dir) return;
    struct dirent *ent;
    while ((ent = readdir(dir)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) continue;
        char arquivo[MAX_CAMINHO];
        if (!montarCaminho(arquivo, sizeof(arquivo), pasta, ent->d_name)) continue;
        remove(arquivo);
    }
    closedir(dir);
    rmdir(pasta);
}

static int extrairHQ(const char *caminhoArquivo, const char *pastaDestino) {
    struct archive *a = archive_read_new();
    struct archive *ext = archive_write_disk_new();
    struct archive_entry *entry;
    int ok = 0, r;

    criarDiretoriosRecursivo(pastaDestino);
    if (!a || !ext) goto fim;

    archive_read_support_format_all(a);
    archive_read_support_filter_all(a);
    archive_write_disk_set_options(ext, ARCHIVE_EXTRACT_TIME | ARCHIVE_EXTRACT_PERM |
                                        ARCHIVE_EXTRACT_SECURE_NODOTDOT |
                                        ARCHIVE_EXTRACT_SECURE_SYMLINKS);

    if (archive_read_open_filename(a, caminhoArquivo, 10240) != ARCHIVE_OK) goto fim;
    ok = 1;

    while ((r = archive_read_next_header(a, &entry)) == ARCHIVE_OK || r == ARCHIVE_WARN) {
        if (archive_entry_filetype(entry) != AE_IFREG) continue;

        const char *nomeFinal = archive_entry_pathname(entry);
        if (!nomeFinal) continue;

        const char *b1 = strrchr(nomeFinal, '/');
        const char *b2 = strrchr(nomeFinal, '\\');
        const char *sep = b1;
        if (b2 && (!sep || b2 > sep)) sep = b2;      /* ultimo separador de qualquer tipo */
        if (sep) nomeFinal = sep + 1;
        if (*nomeFinal == '\0') continue;

        const char *extensao = strrchr(nomeFinal, '.');
        if (extensao && (strcasecmp(extensao, ".jpg") == 0 ||
                         strcasecmp(extensao, ".jpeg") == 0 ||
                         strcasecmp(extensao, ".png") == 0)) {
            char caminhoFinal[MAX_CAMINHO];
            int n = snprintf(caminhoFinal, sizeof(caminhoFinal), "%s/%s", pastaDestino, nomeFinal);
            if (n < 0 || (size_t)n >= sizeof(caminhoFinal)) continue;
            archive_entry_set_pathname(entry, caminhoFinal);

            if (archive_write_header(ext, entry) == ARCHIVE_OK) {
                const void *buff; size_t size; int64_t offset;
                while (archive_read_data_block(a, &buff, &size, &offset) == ARCHIVE_OK) {
                    if (archive_write_data_block(ext, buff, size, offset) < ARCHIVE_WARN) break;
                }
                archive_write_finish_entry(ext);
            }
        }
    }

fim:
    if (a)   { archive_read_close(a);   archive_read_free(a); }
    if (ext) { archive_write_close(ext); archive_write_free(ext); }
    return ok;
}

void processarQuadrinho(const char *caminhoCBZ) {
    char pastaOrigem[MAX_CAMINHO];
    normalizarCaminho(pastaOrigem, caminhoCBZ);
    
    char nomeDoArquivo[256] = "";
    char *ultimaBarraArq = strrchr(pastaOrigem, '/');
    if (ultimaBarraArq) {
        snprintf(nomeDoArquivo, sizeof(nomeDoArquivo), "%s", ultimaBarraArq + 1);
        *ultimaBarraArq = '\0';
    } else {
        snprintf(nomeDoArquivo, sizeof(nomeDoArquivo), "%s", caminhoCBZ);
    }

    char nomeSemExtensao[256];
    snprintf(nomeSemExtensao, sizeof(nomeSemExtensao), "%s", nomeDoArquivo);
    char *ponto = strrchr(nomeSemExtensao, '.');
    if (ponto) *ponto = '\0';

    /* Define onde os JPGs serao colocados */
    char pastaBase[MAX_CAMINHO];
    char subcaminhoCBR[MAX_CAMINHO];

    /* Se o arquivo ja estiver dentro de D:/Emulador/HQ/CBR/..., extrai direto para D:/Emulador/HQ/... (Descompactada) */
    if (estaDentroDeCBR(pastaOrigem, subcaminhoCBR) && strlen(subcaminhoCBR) > 0) {
        char raizNorm[MAX_CAMINHO];
        normalizarCaminho(raizNorm, PASTA_RAIZ);
        
        if (strstr(subcaminhoCBR, "(Descompactada)") != NULL || strstr(subcaminhoCBR, "(Descompactado)") != NULL) {
            snprintf(pastaBase, sizeof(pastaBase), "%s/%s", raizNorm, subcaminhoCBR);
        } else {
            snprintf(pastaBase, sizeof(pastaBase), "%s/%s (Descompactada)", raizNorm, subcaminhoCBR);
        }
        criarDiretoriosRecursivo(pastaBase);
    } else {
        strcpy(pastaBase, pastaOrigem);
    }

    char pastaTemp[MAX_CAMINHO];
    snprintf(pastaTemp, sizeof(pastaTemp), "%s/.temp_ext", pastaBase);

    limparPastaSegura(pastaTemp);
    if (!extrairHQ(caminhoCBZ, pastaTemp)) {
        strcpy(mensagemStatus, "Erro ao extrair: O arquivo pode estar corrompido.");
        limparPastaSegura(pastaTemp);
        return;      
    }
    int numAtual = obterProximoNumero(pastaBase);

    DIR *diretorio = opendir(pastaTemp);
    if (!diretorio) {
        strcpy(mensagemStatus, "Erro ao extrair: O arquivo pode estar corrompido.");
        limparPastaSegura(pastaTemp); 
        return;
    }

    int qtd = 0;
    struct dirent *entrada;
    while ((entrada = readdir(diretorio)) != NULL) {
        if (strcmp(entrada->d_name, ".") == 0 || strcmp(entrada->d_name, "..") == 0) continue;
        if (qtd < MAX_PAGINAS) {
            strcpy(paginas[qtd], entrada->d_name);
            qtd++;
        }
    }
    int renomeados = 0;
    for (int i = 0; i < qtd; i++) {
        char caminhoAntigo[MAX_CAMINHO], caminhoNovo[MAX_CAMINHO];
        if (!montarCaminho(caminhoAntigo, sizeof(caminhoAntigo), pastaTemp, paginas[i])) continue;

        const char *extPag = strrchr(paginas[i], '.');
        if (!extPag) extPag = ".jpg";

        int n = snprintf(caminhoNovo, sizeof(caminhoNovo), "%s/%03d - %s%s",
                         pastaBase, numAtual, nomeSemExtensao, extPag);
        if (n < 0 || (size_t)n >= sizeof(caminhoNovo)) continue;

        if (rename(caminhoAntigo, caminhoNovo) == 0) { numAtual++; renomeados++; }
    }
    limparPastaSegura(pastaTemp);
    registrarExtraido(caminhoCBZ);
    snprintf(mensagemStatus, sizeof(mensagemStatus), "Sucesso! '%s' -> %d paginas.", nomeDoArquivo, renomeados);
    closedir(diretorio);

    qsort(paginas, qtd, sizeof(paginas[0]), compararNomes);

    for (int i = 0; i < qtd; i++) {
        char caminhoAntigo[MAX_CAMINHO], caminhoNovo[MAX_CAMINHO];
        snprintf(caminhoAntigo, sizeof(caminhoAntigo), "%s/%s", pastaTemp, paginas[i]);
        char *ext = strrchr(paginas[i], '.');
        if (!ext) ext = ".jpg"; 
        
        snprintf(caminhoNovo, sizeof(caminhoNovo), "%s/%03d - %s%s", pastaBase, numAtual, nomeSemExtensao, ext);
        
        if (rename(caminhoAntigo, caminhoNovo) == 0) numAtual++;
    }
    
    limparPastaSegura(pastaTemp); 
    registrarExtraido(caminhoCBZ);

    snprintf(mensagemStatus, sizeof(mensagemStatus), "Sucesso! '%s' -> %d paginas.", nomeDoArquivo, qtd);
}

static int pertenceAPasta(const char *caminho, const char *pasta) {
    size_t n = strlen(pasta);
    if (n == 0 || _strnicmp(caminho, pasta, n) != 0) return 0;
    return caminho[n] == '/' || caminho[n] == '\\' || caminho[n] == '\0';
}

void concluirPasta(char *caminhoPasta) {
    char camNorm[MAX_CAMINHO], raizNorm[MAX_CAMINHO];
    normalizarCaminho(camNorm, caminhoPasta);
    normalizarCaminho(raizNorm, PASTA_RAIZ);

    if (_stricmp(camNorm, raizNorm) == 0) {
        strcpy(mensagemStatus, "Erro: Voce nao pode alterar a pasta raiz!");
        return;
    }

    /* CASO 1: O usuario ja esta dentro da pasta D:/Emulador/HQ/CBR/... */
    char subcaminhoCBR[MAX_CAMINHO];
    if (estaDentroDeCBR(camNorm, subcaminhoCBR)) {
        if (strlen(subcaminhoCBR) == 0) {
            strcpy(mensagemStatus, "Erro: Voce esta na raiz da pasta CBR!");
            return;
        }

        /* Se houver arquivos CBR/CBZ ainda nao extraidos nessa pasta, extrai todos para HQ/... (Descompactada) */
        int extraidosAgora = 0;
        DIR *dir = opendir(caminhoPasta);
        if (dir) {
            struct dirent *ent;
            while ((ent = readdir(dir)) != NULL) {
                char *ext = strrchr(ent->d_name, '.');
                if (ext && (strcasecmp(ext, ".cbr") == 0 || strcasecmp(ext, ".cbz") == 0)) {
                    char arqCaminho[MAX_CAMINHO];
                    snprintf(arqCaminho, sizeof(arqCaminho), "%s/%s", caminhoPasta, ent->d_name);
                    if (!foiExtraido(arqCaminho)) {
                        processarQuadrinho(arqCaminho);
                        extraidosAgora++;
                    }
                }
            }
            closedir(dir);
        }

        /* Limpa o historico dessa pasta mantendo os CBRs intactos */
        for (int i = 0; i < totalHistorico; i++) {
            if (historicoExtraidos[i][0] != '\0' && pertenceAPasta(historicoExtraidos[i], caminhoPasta)) {
                historicoExtraidos[i][0] = '\0';
            }
        }

        snprintf(mensagemStatus, sizeof(mensagemStatus), "CBR mantido! Extraido em HQ/%s (Descompactada).", subcaminhoCBR);
        return;
    }

    /* CASO 2: Pasta comum dentro de D:/Emulador/HQ/... */
    if (strstr(caminhoPasta, "(Descompactada)") != NULL || strstr(caminhoPasta, "(Descompactado)") != NULL) {
        strcpy(mensagemStatus, "Esta pasta ja foi marcada como (Descompactada).");
        return;
    }

    char subcaminhoRelativo[MAX_CAMINHO] = "";
    char pastaDestinoCBR[MAX_CAMINHO] = "";

    if (obterSubcaminhoRaiz(camNorm, subcaminhoRelativo) && strlen(subcaminhoRelativo) > 0) {
        snprintf(pastaDestinoCBR, sizeof(pastaDestinoCBR), "%s/CBR/%s", raizNorm, subcaminhoRelativo);
    } else {
        /* Fallback caso esteja no Workspace Downloads */
        char *nomePasta = strrchr(camNorm, '/');
        nomePasta = nomePasta ? nomePasta + 1 : camNorm;
        snprintf(pastaDestinoCBR, sizeof(pastaDestinoCBR), "%s/CBR/%s", raizNorm, nomePasta);
    }

    criarDiretoriosRecursivo(pastaDestinoCBR);

    int movidos = 0;
    for (int i = 0; i < totalHistorico; i++) {
        if (historicoExtraidos[i][0] != '\0' && pertenceAPasta(historicoExtraidos[i], caminhoPasta)) {
            char *nomeArq = strrchr(historicoExtraidos[i], '/');
            if (!nomeArq) nomeArq = strrchr(historicoExtraidos[i], '\\');
            nomeArq = nomeArq ? nomeArq + 1 : historicoExtraidos[i];

            char destinoFinalArq[MAX_CAMINHO];
            snprintf(destinoFinalArq, sizeof(destinoFinalArq), "%s/%s", pastaDestinoCBR, nomeArq);

            /* Move o arquivo compactado para a arvore CBR sem apaga-lo */
            if (MoveFileExA(historicoExtraidos[i], destinoFinalArq, MOVEFILE_REPLACE_EXISTING | MOVEFILE_COPY_ALLOWED)) {
                movidos++;
            }
            historicoExtraidos[i][0] = '\0';
        }
    }

    char novoCaminho[MAX_CAMINHO];
    snprintf(novoCaminho, sizeof(novoCaminho), "%s (Descompactada)", caminhoPasta);

    if (rename(caminhoPasta, novoCaminho) == 0) {
        strcpy(caminhoPasta, novoCaminho);
        snprintf(mensagemStatus, sizeof(mensagemStatus), "Concluido! %d CBRs movidos para a pasta CBR e pasta renomeada.", movidos);
    } else {
        snprintf(mensagemStatus, sizeof(mensagemStatus), "%d CBRs movidos para CBR, mas houve erro ao renomear a pasta.", movidos);
    }
}

void carregarDiretorio(const char *pasta) {
    totalItens = 0;
    DIR *diretorio = opendir(pasta);

    if (strcmp(pasta, PASTA_RAIZ) != 0) {
        ItemLista *v = &listaAtual[totalItens++];
        snprintf(v->nome, sizeof(v->nome), "%s", ".. (Voltar para pasta anterior)");
        v->caminho[0] = '\0';
        v->tipo = ITEM_VOLTAR;
    }
    if (!diretorio) {
        strcpy(mensagemStatus, "Erro: nao foi possivel abrir a pasta.");
        return;
    }

    struct dirent *entrada;
    while (totalItens < MAX_ITENS && (entrada = readdir(diretorio)) != NULL) {
        if (strcmp(entrada->d_name, ".") == 0 || strcmp(entrada->d_name, "..") == 0) continue;
        if (strstr(entrada->d_name, "(Descompactada)") || strstr(entrada->d_name, "(Descompactado)")) continue;

        char caminhoCompleto[MAX_CAMINHO];
        if (!montarCaminho(caminhoCompleto, sizeof(caminhoCompleto), pasta, entrada->d_name)) continue;

        struct stat info;
        if (stat(caminhoCompleto, &info) != 0) continue;

        int ehPasta = S_ISDIR(info.st_mode);
        if (!ehPasta) {
            const char *ext = strrchr(entrada->d_name, '.');
            if (!ext || (strcasecmp(ext, ".cbz") != 0 && strcasecmp(ext, ".cbr") != 0)) continue;
        }

        ItemLista *it = &listaAtual[totalItens++];
        snprintf(it->nome, sizeof(it->nome), "%s", entrada->d_name);
        snprintf(it->caminho, sizeof(it->caminho), "%s", caminhoCompleto);
        it->tipo = ehPasta ? ITEM_PASTA : ITEM_ARQUIVO;
    }
    closedir(diretorio);

    qsort(listaAtual, totalItens, sizeof(ItemLista), compararItensMenu);
}