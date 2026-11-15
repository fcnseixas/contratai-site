# contratai — site

Landing page e política de privacidade do **contrataí**, plataforma de entrevistas
de candidatos por áudio no WhatsApp conduzidas por um agente de IA.

🔗 [contratai.net](https://contratai.net)

## O que tem aqui

| Arquivo | |
|---|---|
| `index.html` | Landing page |
| `privacidade.html` | Política de privacidade (LGPD) |
| `blog/*.html` | Guias — **gerados**, não editar à mão |
| `conteudo/*.md` | Os posts, em Markdown. É daqui que se escreve |
| `gerar-blog.py` | O gerador |
| `hero-1.mp4` · `hero-2.mp4` · `hero-3.mp4` · `poster.jpg` | Os três clipes que se revezam na hero e o pôster do primeiro |
| `onda.svg` | Onda de voz do fundo — entra como máscara, não como imagem |
| `promo.mp4` · `promo-poster.jpg` | Filme promocional de 1 min, aberto em modal |
| `recrutadora.jpg` | Foto da seção do painel |
| `logo-claro.png` · `logo-escuro.png` | Logo, uma versão por tema |
| `mic.png` | Favicon |
| `og.jpg` | Imagem de compartilhamento (1200×630) |

Site estático. HTML, CSS e JavaScript escritos à mão, sem dependências além das
fontes do Google Fonts. O blog tem um passo de geração, descrito abaixo, mas a
saída dele é HTML puro como o resto.

## Rodar localmente

```bash
python3 -m http.server 8000
```

E abrir <http://localhost:8000>.

## Blog

São guias perenes agrupados em três categorias, **sem data**. Escrever um texto
é criar um arquivo em `conteudo/`, com o nome virando a URL:

```
conteudo/candidato-que-nao-aparece.md   →   /blog/candidato-que-nao-aparece
```

Com este cabeçalho:

```markdown
---
titulo: "Candidato que não aparece: por que remarcar não resolve"
resumo: Uma frase. Vira a descrição na busca e o texto do item no índice.
categoria: Triagem e seleção
ordem: 1
---
```

`titulo`, `resumo` e `categoria` são obrigatórios; `ordem` posiciona dentro da
categoria (sem ela, vai para o fim). Título com `:` precisa de aspas, que o
gerador remove. Categoria fora da lista de `CATEGORIAS` **para a geração** — é
erro de digitação, não categoria nova. Para criar uma de verdade, editar
`CATEGORIAS` no gerador. Depois:

```bash
python3 gerar-blog.py
```

Isso reescreve `blog/index.html`, `blog/<slug>.html` e o `sitemap.xml`, e apaga
do `blog/` o que não tem mais fonte. **Os arquivos gerados são commitados** — a
Vercel não roda nada, só serve. O `.vercelignore` mantém os fontes e o gerador
fora do deploy.

**Por que sem data:** são guias, não notícia. Datar no passado para simular
cadência seria prova social inventada — a mesma regra que mantém número de
cliente fictício fora da landing — e o `datePublished` do schema é lido pelo
buscador, que cobra data real. Sem data, a biblioteca nunca parece abandonada
e nada é falso. O schema é `Article`, sem data de publicação.

O Markdown aceito é um subconjunto deliberado: `##`/`###`, parágrafo, `**negrito**`,
`*itálico*`, `` `código` ``, `[link](url)`, listas com `-` ou `1.`, `>` para citação,
`---` para linha e tabela com cabeçalho. É o que um post de texto precisa, e evita
que o site ganhe a primeira dependência de instalação — não há biblioteca de
Markdown na máquina, e a saída tem que continuar sendo HTML estático.

## Deploy

Publicado na Vercel a partir da branch `main`. O `vercel.json` cuida das URLs
limpas (`/privacidade` em vez de `/privacidade.html`) e do cache das mídias.

O painel da aplicação vive separado, em `app.contratai.net`.

## Detalhes que não são acidentais

- **Tema claro é o padrão**, independente do sistema do visitante. O switch no
  cabeçalho alterna, e a escolha fica no `localStorage`. O script que lê a
  preferência roda antes da primeira pintura, para o tema errado não piscar.
- **O player da hero** toca um áudio real e acende a transcrição palavra por
  palavra, em sincronia. O texto fica inteiro e legível mesmo com o áudio parado.
- **São três pessoas no quadro da hero, não uma.** Um rosto só contava um caso;
  três contam a regra — e todos no mesmo gesto, falando no WhatsApp. Eles se
  revezam em crossfade de 1,1 s, e quem comanda a troca é o `timeupdate` do
  próprio clipe: um relógio à parte se desencontra do vídeo e corta a cena no
  meio. Só o primeiro vem com `src`; os outros dois entram na rede depois do
  `load`, para não disputar banda com a primeira pintura. Os três somados
  pesam **1 MB** — o vídeo único de antes pesava 5,6 MB sozinho.
- **O fundo é todo CSS, e pertence só à primeira tela.** Uma aura verde no alto,
  uma malha de pontos que some antes do fim da hero e a onda de voz no rodapé —
  essa num SVG de 4 KB usado como *máscara*, para a cor sair da variável do tema
  e o mesmo arquivo servir claro e escuro. As camadas são ancoradas no topo do
  documento, não na viewport: presas à tela elas acompanhariam a rolagem e o
  site inteiro ficaria pontilhado. O painel da hero ficou translúcido com
  `backdrop-filter` para a aura atravessá-lo, com recuo para o opaco de antes
  onde o navegador não tiver suporte.
- **O âmbar é exclusivo da voz** — onda de áudio e etiqueta de transcrição. Em dois
  tons, porque o que funciona sobre a bolha verde não tem contraste sobre branco.
- **A paleta sai do logo**, com os verdes extraídos dos pixels do arquivo original.
- **O filme é self-hosted, não embed do YouTube.** Um embed carregaria
  rastreamento de terceiros antes de qualquer consentimento, o que contradiz a
  política de privacidade e teria que ser declarado lá.
- **São 13 MB, então ele só entra na rede depois do clique** (`preload="none"`
  e `src` vazio). Carregar antes seria peso morto em toda visita, e boa parte do
  público abre no celular com dados móveis. O modal também pausa o vídeo da hero
  enquanto está aberto: dois vídeos juntos competem por atenção e por CPU.
