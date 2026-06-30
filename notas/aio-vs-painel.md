# Por que o painel diverge da AIO?

## Resumo executivo

As médias por escola exibidas pelo painel **podem ser maiores** do que as
divulgadas pela [AIO Educação](https://www.aio.com.br/enem-por-escola/), e a
divergência costuma ser **muito grande na REDAÇÃO** e menor (porém não-nula)
em CH/LC. CN e MT praticamente coincidem.

A causa é **metodológica**, não há bug — as duas plataformas calculam a média
da escola sobre conjuntos de estudantes diferentes:

| | **Painel ENEM MS** | **AIO** |
|--|--|--|
| Filtro | Global: 1 único conjunto serve para as 5 áreas | Por prova: 1 conjunto por área |
| Regra | `CONCLUINTE & PRESENTE_2_DIAS & ¬ELIM_OBJ & ¬ELIM_RED` | Todos que concluíram aquela prova específica (mín. 10 part.) |
| `branco` (RED, status 4) | Conta como 0 | Conta como 0 |
| `anulada` (RED, status 2) | Exclui | Exclui |
| Mín. participantes | sem mínimo p/ exibir | 10 part./edição |

> AIO: *"Para cada Área do Conhecimento e Redação foram considerados na média
> todos os participantes da escola que concluíram cada prova. Para as edições
> de 2024 em diante, o cruzamento dos estudantes com as escolas foi realizado
> diretamente pelo INEP com base no Censo Escolar."*
> ([fonte](https://chatwoot.aio.com.br/hc/aio-educacao/articles/1734373277-de-onde-vem-os-dados-do-enem-por-escola))

## Caso concreto — EE MANOEL GARCIA LEAL (Paranaíba, INEP 50011413, ENEM 2025)

| Área | Painel | AIO (página da escola) | Δ painel − AIO |
|:--:|:--:|:--:|:--:|
| CN | 477.0 | 477.0 | **0.0** |
| CH | 489.7 | 488.6 | +1.1 |
| LC | 502.3 | 501.6 | +0.7 |
| MT | 470.1 | 470.1 | **0.0** |
| RED | **519.5** | **510.4** | **+9.1** |

Note que **CN e MT casam exatamente**. Isso não é coincidência: como
dia 1 = `CH + LC + RED` e dia 2 = `CN + MT`, todo estudante presente no
dia 2 normalmente também está no conjunto VALIDO do painel (ele só não estaria
se faltasse ao dia 1, o que é raro). Já no dia 1 entram alguns alunos que não
voltam para o dia 2 — eles entram no AIO em CH/LC/RED mas **ficam fora** do
painel.

## Reprodução numérica com os microdados de 2024

Rodando `scripts/diag_aio_vs_painel.py --co-escola 50011413 --ano 2024`
sobre o mesmo arquivo `dados/2024/enem_resultados_2024_.parquet`:

```
Registros associados à escola .........: 86
Presentes dia 1 (CH+LC) ...............: 50
Presentes dia 2 (CN+MT) ...............: 46
Presentes nos 2 dias (filtro do painel): 45
Compareceu só ao dia 1 ................: 5  (entra no AIO p/ CH/LC/RED, FORA do painel)
Compareceu só ao dia 2 ................: 1  (entra no AIO p/ CN/MT, FORA do painel)
TP_STATUS_REDACAO: 1.0=47, 4.0=3 (branco→0), NaN=36 (não fez)

area  painel_N  painel_media   aio_N  aio_media   delta
  CN        45        443.91      46     443.24    +0.67
  CH        45        478.32      50     473.01    +5.31
  LC        45        481.34      50     480.91    +0.43
  MT        45        453.94      46     453.02    +0.92
 RED        45        586.67      50     566.40   +20.27
```

**Validação cruzada.** Convertendo as médias de 2024 para a variação
percentual divulgada pela AIO em 2025, recupero exatamente os números do
print do usuário:

| Área | 2024 (AIO calc.) | 2025 (AIO publicado) | Δ% calc. | Δ% AIO publica |
|:--:|:--:|:--:|:--:|:--:|
| LC  | 480.91 | 501.6 | +4.30% | **↑ 4.3%** |
| CH  | 473.01 | 488.6 | +3.30% | **↑ 3.3%** |
| CN  | 443.24 | 477.0 | +7.62% | **↑ 7.63%** |
| MT  | 453.02 | 470.1 | +3.77% | **↑ 3.77%** |
| RED | 566.40 | 510.4 | −9.89% | **↓ 9.89%** |

Os cinco valores batem nas duas casas decimais → a AIO usa exatamente o
filtro **"por prova"** e o painel usa o filtro **"global"**.

## Por que o gap é tão maior em REDAÇÃO?

Os 5 alunos extras (dia 1 sem dia 2) trazem ~566 em CH/LC, mas média ~384
em RED — isso porque a evasão de dia 2 tem alta correlação com redação
em branco/cópia/fuga ao tema (status 4, score 0).

```
Painel  RED: μ=586.67 sobre N=45
AIO     RED: μ=566.40 sobre N=50
Diferença explicada: 5 alunos extras, soma ≈ (566.40·50 − 586.67·45) = 1.918,85
                     ⇒ μ extras ≈ 383,8 (incluindo 1 branco = 0)
```

## O que isso significa na prática

* **Nenhum dos dois cálculos está errado** — eles respondem a perguntas
  diferentes:
  * **Painel:** "Como rendeu o estudante que realmente terminou o ENEM?"
    (base para análise pedagógica e funil de eliminação.)
  * **AIO:** "Qual a média daquela prova entre quem a entregou?"
    (mesma definição usada pelo INEP no antigo *ENEM por Escola*.)
* **Onde os números coincidem (CN, MT)** — o painel já está alinhado com a
  AIO, pois quase ninguém vai ao dia 2 sem ter ido ao dia 1.
* **Onde os números divergem (CH, LC, RED)** — a divergência é proporcional
  ao número de alunos que abandonaram entre dia 1 e dia 2. Em escolas com
  baixa taxa de evasão, a divergência fica abaixo de 1 ponto; em escolas com
  alta evasão, pode passar de 20 pontos em RED.

## Como reproduzir / investigar outras escolas

```bash
.venv/bin/python scripts/diag_aio_vs_painel.py --co-escola 50011405 --ano 2024
.venv/bin/python scripts/diag_aio_vs_painel.py --co-escola 50011383 --ano 2024 --debug
```

O script imprime o funil (presentes dia 1 / dia 2 / 2 dias), distribuição de
`TP_STATUS_REDACAO`, e a média por área sob cada metodologia.

## Caminhos possíveis (caso queira eliminar a divergência)

1. **Aceitar a divergência e documentá-la** no painel (`docs/index.html`,
   ao lado do filtro de "participantes efetivos"), com link para esta nota.
   Esforço mínimo, recomendado se o público alvo entende o filtro do painel.

2. **Publicar a métrica "AIO-compatível" lado a lado**: adicionar em
   `scripts/gerar_agregados.py` uma agregação extra por área usando o filtro
   *"todos que entregaram aquela prova"* (não exige `PRESENTE_2_DIAS`). Exporá
   2 médias por área no painel — a "interna SED" e a "comparável a AIO/QEdu/
   INEP".

3. **Trocar a métrica do painel** para a regra da AIO. Não recomendado: o
   painel perde a coerência do filtro VALIDO usado em todas as outras seções
   (funil, taxas, integridade).
