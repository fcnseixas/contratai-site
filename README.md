# contratai — site

Landing page e política de privacidade do **contrataí**, plataforma de entrevistas
de candidatos por áudio no WhatsApp conduzidas por um agente de IA.

🔗 [contratai.net](https://contratai.net)

## O que tem aqui

| Arquivo | |
|---|---|
| `index.html` | Landing page |
| `privacidade.html` | Política de privacidade (LGPD) |
| `hero-1.mp4` · `hero-2.mp4` · `hero-3.mp4` · `poster.jpg` | Os três clipes que se revezam na hero e o pôster do primeiro |
| `onda.svg` | Onda de voz do fundo — entra como máscara, não como imagem |
| `promo.mp4` · `promo-poster.jpg` | Filme promocional de 1 min, aberto em modal |
| `recrutadora.jpg` | Foto da seção do painel |
| `logo-claro.png` · `logo-escuro.png` | Logo, uma versão por tema |
| `mic.png` | Favicon |
| `og.jpg` | Imagem de compartilhamento (1200×630) |

Site estático, sem build. HTML, CSS e JavaScript escritos à mão, sem dependências
além das fontes do Google Fonts.

## Rodar localmente

```bash
python3 -m http.server 8000
```

E abrir <http://localhost:8000>.

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
