/**
 * Conferencia Escolas x PDF (Fev/2025) — Rede Estadual MS
 *
 * Valida alinhamento entre Unidade Escolar, Municipio e CRE na planilha
 * usando como referencia o PDF "Contatos e Enderecos das Escolas Estaduais".
 *
 * Instalacao:
 * 1. Extensions > Apps Script — cole este arquivo (Code.gs)
 * 2. Salve e recarregue a planilha
 * 3. Menu "Conferencia Escolas" > Conferir planilha ativa
 *
 * Atualizar referencia (quando sair novo PDF):
 *   python scripts/gerar_referencia_conferencia_escolas.py
 *   Copie o conteudo gerado de ConferenciaEscolas.gs para o Apps Script
 */

var REFERENCIA_JSON = "[{\"i\":\"50027395\",\"e\":\"EE CHICO MENDES\",\"m\":\"\u00c1GUA CLARA\",\"c\":\"CRE 12\"},{\"i\":\"50011774\",\"e\":\"EE MAL. CASTELO BRANCO\",\"m\":\"\u00c1GUA CLARA\",\"c\":\"CRE 12\"},{\"i\":\"50002961\",\"e\":\"EE PROF\u00aa. ROMILDA COSTA CARNEIRO\",\"m\":\"ALCIN\u00d3POLIS\",\"c\":\"CRE 04\"},{\"i\":\"50015249\",\"e\":\"EE CEL. FELIPE DE BRUM\",\"m\":\"AMAMBAI\",\"c\":\"CRE 11\"},{\"i\":\"50015257\",\"e\":\"EE DOM AQUINO CORR\u00caA\",\"m\":\"AMAMBAI\",\"c\":\"CRE 11\"},{\"i\":\"50015168\",\"e\":\"EE DR. FERNANDO CORR\u00caA DA COSTA\",\"m\":\"AMAMBAI\",\"c\":\"CRE 11\"},{\"i\":\"50015176\",\"e\":\"EE VESPASIANO MARTINS\",\"m\":\"AMAMBAI\",\"c\":\"CRE 11\"},{\"i\":\"50030370\",\"e\":\"EE IND\u00cdGENA Mbo'eroy GUARANI KAIOW\u00c1\",\"m\":\"AMAMBAI\",\"c\":\"CRE 11\"},{\"i\":\"50001086\",\"e\":\"EE CARLOS DRUMMOND DE ANDRADE\",\"m\":\"ANAST\u00c1CIO\",\"c\":\"CRE 01\"},{\"i\":\"50001094\",\"e\":\"EE DEP. CARLOS SOUZA MEDEIROS\",\"m\":\"ANAST\u00c1CIO\",\"c\":\"CRE 01\"},{\"i\":\"50029819\",\"e\":\"EE IND\u00cdGENA GUILHERMINA DA SILVA\",\"m\":\"ANAST\u00c1CIO\",\"c\":\"CRE 01\"},{\"i\":\"50001116\",\"e\":\"EE C\u00cdVICO-MILITAR MARIA CORR\u00caA DIAS\",\"m\":\"ANAST\u00c1CIO\",\"c\":\"CRE 01\"},{\"i\":\"50001108\",\"e\":\"EE ROBERTO SCAFF\",\"m\":\"ANAST\u00c1CIO\",\"c\":\"CRE 01\"},{\"i\":\"50001124\",\"e\":\"EE ROMALINO ALVES DE ALBRES\",\"m\":\"ANAST\u00c1CIO\",\"c\":\"CRE 01\"},{\"i\":\"50012975\",\"e\":\"EE MARIA JOS\u00c9\",\"m\":\"ANAURIL\u00c2NDIA\",\"c\":\"CRE 09\"},{\"i\":\"50012550\",\"e\":\"EE PROF. EZEQUIEL BALBINO\",\"m\":\"ANAURIL\u00c2NDIA\",\"c\":\"CRE 09\"},{\"i\":\"50019503\",\"e\":\"EE DR. JOS\u00c9 MANOEL FONTANILLAS FRAGELLI\",\"m\":\"ANG\u00c9LICA\",\"c\":\"CRE 09\"},{\"i\":\"50019473\",\"e\":\"EE SEN. FILINTO M\u00dcLLER\",\"m\":\"ANG\u00c9LICA\",\"c\":\"CRE 09\"},{\"i\":\"50019520\",\"e\":\"EE LUIS VAZ DE CAM\u00d5ES\",\"m\":\"ANG\u00c9LICA\",\"c\":\"CRE 09\"},{\"i\":\"50015281\",\"e\":\"EE ARAL MOREIRA\",\"m\":\"ANT\u00d4NIO JO\u00c3O\",\"c\":\"CRE 11\"},{\"i\":\"50015290\",\"e\":\"EE PANTALE\u00c3O COELHO XAVIER\",\"m\":\"ANT\u00d4NIO JO\u00c3O\",\"c\":\"CRE 11\"},{\"i\":\"50011022\",\"e\":\"EE ERNESTO RODRIGUES\",\"m\":\"APARECIDA DO TABOADO\",\"c\":\"CRE 10\"},{\"i\":\"50011030\",\"e\":\"EE FREI VITAL DE GARIBALDI\",\"m\":\"APARECIDA DO TABOADO\",\"c\":\"CRE 10\"},{\"i\":\"50011049\",\"e\":\"EE GEORGINA DE OLIVEIRA ROCHA\",\"m\":\"APARECIDA DO TABOADO\",\"c\":\"CRE 10\"},{\"i\":\"50001655\",\"e\":\"EE C\u00c2NDIDO MARIANO\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50001663\",\"e\":\"EE CEL. JOS\u00c9 ALVES RIBEIRO\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50001590\",\"e\":\"EE FELIPE ORRO\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50021990\",\"e\":\"EE MAL. DEODORO DA FONSECA\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50001825\",\"e\":\"EE PROF. ANT\u00d4NIO SAL\u00daSTIO AREIAS\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50001698\",\"e\":\"EE PROF\u00aa. D\u00d3RIS MENDES TRINDADE\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50001671\",\"e\":\"EE PROF\u00aa. MARLY RUSSO RODRIGUES\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50001752\",\"e\":\"CENTRO DE EDUCA\u00c7\u00c3O PROFISSIONAL GERALDO AFONSO GARCIA FERREIRA (CEPA).\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50030396\",\"e\":\"EE IND\u00cdGENA DE EM PASCOAL LEITE DIAS\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50031112\",\"e\":\"EE IND\u00cdGENA DE EM PASTOR REGINALDO MIGUEL - HOYEN\u00d3'O\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50030400\",\"e\":\"EE IND\u00cdGENA DE EM PROF. DOMINGOS VER\u00cdSSIMO MARCOS - MUHI\",\"m\":\"AQUIDAUANA\",\"c\":\"CRE 01\"},{\"i\":\"50015354\",\"e\":\"EE DR. FERNANDO CORR\u00caA DA COSTA\",\"m\":\"ARAL MOREIRA\",\"c\":\"CRE 11\"},{\"i\":\"50015370\",\"e\":\"EE JO\u00c3O VITORINO MARQUES\",\"m\":\"ARAL MOREIRA\",\"c\":\"CRE 11\"},{\"i\":\"50015362\",\"e\":\"EE EUFR\u00c1ZIA FAGUNDES MARQUES\",\"m\":\"ARAL MOREIRA\",\"c\":\"CRE 11\"},{\"i\":\"50004700\",\"e\":\"EE ERNESTO S\u00d3LON BORGES\",\"m\":\"BANDEIRANTES\",\"c\":\"CRE 02\"},{\"i\":\"50013025\",\"e\":\"EE MANOEL DA COSTA LIMA\",\"m\":\"BATAGUASSU\",\"c\":\"CRE 09\"},{\"i\":\"50013033\",\"e\":\"EE PERI MARTINS\",\"m\":\"BATAGUASSU\",\"c\":\"CRE 09\"},{\"i\":\"50013050\",\"e\":\"EE PROF. BRAZ SINIG\u00c1GLIA\",\"m\":\"BATAGUASSU\",\"c\":\"CRE 09\"},{\"i\":\"50024019\",\"e\":\"EE PROF. LUIZ ALBERTO ABRAHAM\",\"m\":\"BATAGUASSU\",\"c\":\"CRE 09\"},{\"i\":\"50013149\",\"e\":\"EE PROF. LADISLAU GARCIA DE\u00c1K FILHO\",\"m\":\"BATAGUASSU\",\"c\":\"CRE 09\"},{\"i\":\"50013181\",\"e\":\"EE BRAZ SINIGAGLIA\",\"m\":\"BATAYPOR\u00c3\",\"c\":\"CRE 09\"},{\"i\":\"50013190\",\"e\":\"EE JAN ANTONIN BATA\",\"m\":\"BATAYPOR\u00c3\",\"c\":\"CRE 09\"},{\"i\":\"50013890\",\"e\":\"EE CASTELO BRANCO\",\"m\":\"BELA VISTA\",\"c\":\"CRE 07\"},{\"i\":\"50013904\",\"e\":\"EE DR. JOAQUIM MURTINHO\",\"m\":\"BELA VISTA\",\"c\":\"CRE 07\"},{\"i\":\"50013912\",\"e\":\"EE ESTER SILVA\",\"m\":\"BELA VISTA\",\"c\":\"CRE 07\"},{\"i\":\"50014048\",\"e\":\"EE PROF\u00aa. VERA GUIMAR\u00c3ES LOUREIRO\",\"m\":\"BELA VISTA\",\"c\":\"CRE 07\"},{\"i\":\"50014110\",\"e\":\"EE JO\u00c3O PEDRO PEDROSSIAN\",\"m\":\"BODOQUENA\",\"c\":\"CRE 01\"},{\"i\":\"50014102\",\"e\":\"EE JOAQUIM M\u00c1RIO BONFIM\",\"m\":\"BODOQUENA\",\"c\":\"CRE 01\"},{\"i\":\"50014200\",\"e\":\"EE BONIF\u00c1CIO CAMARGO GOMES\",\"m\":\"BONITO\",\"c\":\"CRE 07\"},{\"i\":\"50014196\",\"e\":\"EE LUIZ DA COSTA FALC\u00c3O\",\"m\":\"BONITO\",\"c\":\"CRE 07\"},{\"i\":\"50011847\",\"e\":\"EE ADILSON ALVES DA SILVA\",\"m\":\"BRASIL\u00c2NDIA\",\"c\":\"CRE 12\"},{\"i\":\"50011910\",\"e\":\"EE DEBRASA\",\"m\":\"BRASIL\u00c2NDIA\",\"c\":\"CRE 12\"},{\"i\":\"50015486\",\"e\":\"EE ARC\u00caNIO ROJAS\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50015567\",\"e\":\"EE PADRE JOS\u00c9 DE ANCHIETA\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50015460\",\"e\":\"EE PROF\u00aa. CLEUZA APARECIDA VARGAS GALHARDO\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50015478\",\"e\":\"EE PROF. JOAQUIM ALFREDO SOARES VIANNA\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50015451\",\"e\":\"EE TEN. AVIADOR ANT\u00d4NIO JO\u00c3O\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50015583\",\"e\":\"EE FREI JO\u00c3O DAMASCENO\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50030884\",\"e\":\"EE IND\u00cdGENA DE EM \\\"YVY POTY\\\"\",\"m\":\"CAARAP\u00d3\",\"c\":\"CRE 05\"},{\"i\":\"50031961\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O PROFISSIONAL MARCIO ELIAS NERY\",\"m\":\"CAMAPU\u00c3\",\"c\":\"CRE 02\"},{\"i\":\"50003097\",\"e\":\"EE CAMILO BONFIM\",\"m\":\"CAMAPU\u00c3\",\"c\":\"CRE 02\"},{\"i\":\"50003100\",\"e\":\"EE MIGUEL SUTIL\",\"m\":\"CAMAPU\u00c3\",\"c\":\"CRE 02\"},{\"i\":\"50022040\",\"e\":\"EE JOAQUIM MALAQUIAS DA SILVA\",\"m\":\"CAMAPU\u00c3\",\"c\":\"CRE 02\"},{\"i\":\"50005340\",\"e\":\"CENTRO DE EDUCA\u00c7\u00c3O DE JOVENS E ADULTOS PROF\u00aa IGN\u00caS DE LAM\u00d4NICA GUIMAR\u00c3ES - CEEJA-MS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50030272\",\"e\":\"CENTRO DE EDUCA\u00c7\u00c3O PROFISSIONAL EZEQUIEL FERREIRA LIMA - CEPEF\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50033069\",\"e\":\"CENTRO DE APOIO PEDAG\u00d3GICO AO DEFICIENTE VISUAL-CAP-DV\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005111\",\"e\":\"CENTRO ESTADUAL DE ATENDIMENTO AO DEFICIENTE DA AUDIOCOMUNICA\u00c7\u00c3O-CEADA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50031287\",\"e\":\"CENTRO DE CAPACITA\u00c7\u00c3O DE PROFISSIONAIS DA EDUCA\u00c7\u00c3O E DE ATENDIMENTO \u00c0S PESSOAS COM SURDEZ - CAS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50033433\",\"e\":\"CENTRO ESTADUAL DE ATENDIMENTO MULTIDISCIPLINAR PARA ALTAS HABILIDADES/SUPERDOTA\u00c7\u00c3O - CEAM/AHS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50031295\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O ESPECIAL E INCLUSIVA-CEESPI\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006126\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O PROFISSIONAL PROF\u00aa MARIA DE LOURDES WIDAL ROMA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006509\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O PROFISSIONAL H\u00c9RCULES MAYMONE\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50034600\",\"e\":\"CENTRO ESTADUAL DE FORMA\u00c7\u00c3O DE PROFESSORES IND\u00cdGENAS DE MS- CEFPI\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005588\",\"e\":\"CEI JOS\u00c9 EDUARDO MARTINS JALLAD - ZEDU\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50026658\",\"e\":\"CRECHE IRM\u00c3 IRMA ZORZI\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006355\",\"e\":\"EE 11 DE OUTUBRO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006363\",\"e\":\"EE 26 DE AGOSTO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006371\",\"e\":\"EE ADVENTOR DIVINO DE ALMEIDA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006380\",\"e\":\"EE AMANDO DE OLIVEIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005901\",\"e\":\"EE AM\u00c9LIO DE CARVALHO BA\u00cdS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006290\",\"e\":\"EE ANT\u00d4NIO DELFINO PEREIRA E CENTRO CULTURAL DE EDUCA\u00c7\u00c3O TIA EVA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005731\",\"e\":\"EE ARACY EUDOCIAK\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005910\",\"e\":\"EE ARLINDO DE ANDRADE GOMES\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006398\",\"e\":\"EE ARLINDO DE SAMPAIO JORGE\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005928\",\"e\":\"EE BLANCHE DOS SANTOS PEREIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006274\",\"e\":\"EE CORA\u00c7\u00c3O DE MARIA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005936\",\"e\":\"EE DOLOR FERREIRA DE ANDRADE\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005944\",\"e\":\"EE DONA CONSUELO MULLER\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005952\",\"e\":\"EE DR. ARTHUR DE VASCONCELLOS DIAS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005740\",\"e\":\"EE ELVIRA MATHIAS DE OLIVEIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006282\",\"e\":\"EE GENERAL MALAN\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005758\",\"e\":\"EE JO\u00c3O CARLOS FLORES\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006410\",\"e\":\"EE JOAQUIM MURTINHO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50022997\",\"e\":\"EE JOS\u00c9 ANT\u00d4NIO PEREIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005979\",\"e\":\"EE JOS\u00c9 BARBOSA RODRIGUES\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005766\",\"e\":\"EE JOS\u00c9 FERREIRA BARBOSA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005987\",\"e\":\"EE JOS\u00c9 MAMEDE DE AQUINO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005995\",\"e\":\"EE JOS\u00c9 MARIA HUGO RODRIGUES\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006002\",\"e\":\"EE LINO VILLACH\u00c1\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006010\",\"e\":\"EE L\u00daCIA MARTINS COELHO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005774\",\"e\":\"EE LUIZA VIDAL BORGES DANIEL\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006029\",\"e\":\"EE MAESTRO FREDERICO LIEBERMANN\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006037\",\"e\":\"EE MAESTRO HEITOR VILLA LOBOS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006436\",\"e\":\"EE MANOEL BONIF\u00c1CIO NUNES DA CUNHA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005782\",\"e\":\"EE C\u00cdVICO-MILITAR MAR\u00c7AL DE SOUZA TUP\u00c3-Y\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006444\",\"e\":\"EE MARIA CONSTAN\u00c7A BARROS MACHADO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006045\",\"e\":\"EE MARIA ELIZA BOCAY\u00daVA CORR\u00caA DA COSTA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006452\",\"e\":\"EE OLINDA CONCEI\u00c7\u00c3O TEIXEIRA BACHA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006312\",\"e\":\"EE ORC\u00cdRIO THIAGO DE OLIVEIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005804\",\"e\":\"EE PADRE FRANCO DELPIANO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006460\",\"e\":\"EE PADRE JOS\u00c9 SCAMPINI\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006061\",\"e\":\"EE PADRE M\u00c1RIO BLANDINO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006053\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O PROFISSIONAL Pe. JO\u00c3O GREINER\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50029371\",\"e\":\"CENTRO DE APOIO EDUCACIONAL DA SECRETARIA DE ESTADO DE EDUCA\u00c7\u00c3O - CAED/SED\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005812\",\"e\":\"EE PROF\u00aa. ADA TEIXEIRA DOS SANTOS PEREIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006088\",\"e\":\"EE PROF\u00aa. ALICE NUNES ZAMPIERE\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006207\",\"e\":\"EE PROF\u00aa. BRASILINA FERRAZ MANTERO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50034626\",\"e\":\"EE C\u00cdVICO-MILITAR PROF. ALBERTO ELP\u00cdDIO FERREIRA DIAS (PROF. TITO)\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006096\",\"e\":\"EE PROF\u00aa. C\u00c9LIA MARIA N\u00c1GLIS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50028880\",\"e\":\"EE PROF\u00aa. CLARINDA MENDES DE AQUINO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006479\",\"e\":\"EE PROF\u00aa. DELMIRA RAMOS DOS SANTOS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005871\",\"e\":\"EE PROF\u00aa. \u00c9LIA FRAN\u00c7A CARDOSO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006100\",\"e\":\"EE PROF. EMYGDIO CAMPOS WIDAL\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006320\",\"e\":\"EE PROF\u00aa. FAUSTA GARCIA BUENO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005839\",\"e\":\"EE PROF\u00aa. FLAVINA MARIA DA SILVA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005880\",\"e\":\"EE PROF. HENRIQUE CIRYLLO CORR\u00caA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006070\",\"e\":\"EE PROF\u00aa. IZAURA HIGA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005855\",\"e\":\"EE PROF\u00aa. JOELINA DE ALMEIDA XAVIER\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006118\",\"e\":\"EE PROF\u00aa. MARIA DE LOURDES TOLEDO AREIAS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50008463\",\"e\":\"EE PROF\u00aa. MARIA RITA DE C\u00c1SSIA PONTES TEIXEIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50023004\",\"e\":\"EE PROF\u00aa. NEYDER SUELLY COSTA VIEIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006169\",\"e\":\"EE PROF. SEVERINO DE QUEIROZ\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006177\",\"e\":\"EE PROF. SILVIO OLIVEIRA DOS SANTOS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50005863\",\"e\":\"EE PROF\u00aa. THEREZA NORONHA DE CARVALHO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006185\",\"e\":\"EE PROF. ULISSES SERRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50008501\",\"e\":\"EE PROF\u00aa. Z\u00c9LIA QUEVEDO CHAVES\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006215\",\"e\":\"EE RUI BARBOSA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006339\",\"e\":\"EE S\u00c3O FRANCISCO\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006347\",\"e\":\"EE S\u00c3O JOS\u00c9\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006223\",\"e\":\"EE SEBASTI\u00c3O SANTANA DE OLIVEIRA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006231\",\"e\":\"EE TEOT\u00d4NIO VILELA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006495\",\"e\":\"EE VESPASIANO MARTINS\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50006240\",\"e\":\"EE WALDEMIR BARROS DA SILVA\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50029827\",\"e\":\"EE P\u00d3LO FRANCISCO C\u00c2NDIDO DE REZENDE\",\"m\":\"CAMPO GRANDE\",\"c\":\"SED\"},{\"i\":\"50014366\",\"e\":\"EE DR. RUBENS DE CASTRO PINTO\",\"m\":\"CARACOL\",\"c\":\"CRE 07\"},{\"i\":\"50010115\",\"e\":\"EE HERMELINA BARBOSA LEAL\",\"m\":\"CASSIL\u00c2NDIA\",\"c\":\"CRE 10\"},{\"i\":\"50010158\",\"e\":\"EE RUI BARBOSA\",\"m\":\"CASSIL\u00c2NDIA\",\"c\":\"CRE 10\"},{\"i\":\"50010166\",\"e\":\"EE S\u00c3O JOS\u00c9\",\"m\":\"CASSIL\u00c2NDIA\",\"c\":\"CRE 10\"},{\"i\":\"50010670\",\"e\":\"EE AUGUSTO KRUG NETTO\",\"m\":\"CHAPAD\u00c3O DO SUL\",\"c\":\"CRE 10\"},{\"i\":\"50029053\",\"e\":\"EE JORGE AMADO\",\"m\":\"CHAPAD\u00c3O DO SUL\",\"c\":\"CRE 10\"},{\"i\":\"50034138\",\"e\":\"CEEP - CENTRO DE EDUCA\u00c7\u00c3O PROFISSIONAL ARLINDO NECKEL\",\"m\":\"CHAPAD\u00c3O DO SUL\",\"c\":\"CRE 10\"},{\"i\":\"50009290\",\"e\":\"EE JOS\u00c9 ALVES QUITO\",\"m\":\"CORGUINHO\",\"c\":\"CRE 02\"},{\"i\":\"50019554\",\"e\":\"EE CEL. SAPUCAIA\",\"m\":\"CORONEL SAPUCAIA\",\"c\":\"CRE 11\"},{\"i\":\"50019562\",\"e\":\"EE ENEIL VARGAS\",\"m\":\"CORONEL SAPUCAIA\",\"c\":\"CRE 11\"},{\"i\":\"50000179\",\"e\":\"EE CARLOS DE CASTRO BRASIL\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000187\",\"e\":\"EE DOM BOSCO\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000047\",\"e\":\"EE DR. GABRIEL VANDONI DE BARROS\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000195\",\"e\":\"EE DR. JO\u00c3O LEITE DE BARROS\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000209\",\"e\":\"EE J\u00daLIA GON\u00c7ALVES PASSARINHO\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000152\",\"e\":\"EE MARIA HELENA ALBANEZE\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000217\",\"e\":\"EE MARIA LEITE\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000225\",\"e\":\"EE NATH\u00c9RCIA POMPEO DOS SANTOS\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000233\",\"e\":\"EE OCTAC\u00cdLIO FAUSTINO DA SILVA\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50000160\",\"e\":\"EE ROTARY CLUB\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50029746\",\"e\":\"EE IND\u00cdGENA JO\u00c3O QUIRINO DE CARVALHO - TOGHOPAN\u00c3A\",\"m\":\"CORUMB\u00c1\",\"c\":\"CRE 03\"},{\"i\":\"50010700\",\"e\":\"EE JOS\u00c9 FERREIRA DA COSTA\",\"m\":\"COSTA RICA\",\"c\":\"CRE 04\"},{\"i\":\"50010719\",\"e\":\"EE SANTOS DUMONT\",\"m\":\"COSTA RICA\",\"c\":\"CRE 04\"},{\"i\":\"50003461\",\"e\":\"EE PADRE NUNES\",\"m\":\"COXIM\",\"c\":\"CRE 04\"},{\"i\":\"50003500\",\"e\":\"EE PEDRO MENDES FONTOURA\",\"m\":\"COXIM\",\"c\":\"CRE 04\"},{\"i\":\"50003518\",\"e\":\"EE PROF\u00aa. CLARICE RONDON DOS SANTOS\",\"m\":\"COXIM\",\"c\":\"CRE 04\"},{\"i\":\"50003526\",\"e\":\"EE SEMIRAMIS CARLOTA BENEVIDES DA ROCHA\",\"m\":\"COXIM\",\"c\":\"CRE 04\"},{\"i\":\"50003534\",\"e\":\"EE SILVIO FERREIRA\",\"m\":\"COXIM\",\"c\":\"CRE 04\"},{\"i\":\"50003542\",\"e\":\"EE VIRIATO BANDEIRA\",\"m\":\"COXIM\",\"c\":\"CRE 04\"},{\"i\":\"50019660\",\"e\":\"EE 13 DE MAIO\",\"m\":\"DEOD\u00c1POLIS\",\"c\":\"CRE 05\"},{\"i\":\"50019678\",\"e\":\"EE SCILA M\u00c9DICI\",\"m\":\"DEOD\u00c1POLIS\",\"c\":\"CRE 05\"},{\"i\":\"50019961\",\"e\":\"EE JO\u00c3O BAPTISTA PEREIRA\",\"m\":\"DEOD\u00c1POLIS\",\"c\":\"CRE 05\"},{\"i\":\"50019813\",\"e\":\"EE LAGOA BONITA\",\"m\":\"DEOD\u00c1POLIS\",\"c\":\"CRE 05\"},{\"i\":\"50019880\",\"e\":\"EE PORTO VILMA\",\"m\":\"DEOD\u00c1POLIS\",\"c\":\"CRE 05\"},{\"i\":\"50002155\",\"e\":\"EE PROF\u00aa ESTEFANA CENTURION GAMBARRA\",\"m\":\"DOIS IRM\u00c3OS DO BURITI\",\"c\":\"CRE 01\"},{\"i\":\"50037005\",\"e\":\"EE IND\u00cdGENA CACIQUE NDETY REGINALDO\",\"m\":\"DOIS IRM\u00c3OS DO BURITI\",\"c\":\"CRE 01\"},{\"i\":\"50082876\",\"e\":\"EE IND\u00cdGENA NATIVIDADE ALC\u00c2NTARA MARQUES\",\"m\":\"DOIS IRM\u00c3OS DO BURITI\",\"c\":\"CRE 01\"},{\"i\":\"50015591\",\"e\":\"EE BAR\u00c3O DO RIO BRANCO\",\"m\":\"DOURADINA\",\"c\":\"CRE 05\"},{\"i\":\"50015770\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O DE JOVENS E ADULTOS DE DOURADOS-CEEJA / MS\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50033700\",\"e\":\"CENTRO ESTADUAL DE EDUCA\u00c7\u00c3O PROFISSIONAL PROF\u00aa EVANILDE COSTA DA SILVA\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50015885\",\"e\":\"EE ABIGAIL BORRALHO\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016415\",\"e\":\"EE ANT\u00d4NIA DA SILVEIRA CAPIL\u00c9\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50015907\",\"e\":\"EE CASTRO ALVES\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50015940\",\"e\":\"EE FLORIANO VIEGAS MACHADO\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50015915\",\"e\":\"EE MARIA DA GL\u00d3RIA MUZZI FERREIRA\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016008\",\"e\":\"EE MENODORA FIALHO DE FIGUEIREDO\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016016\",\"e\":\"EE MIN. JO\u00c3O PAULO DOS REIS VELOSO\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50015958\",\"e\":\"EE PASTOR DANIEL BERG\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50017373\",\"e\":\"EE PRES. GET\u00daLIO VARGAS\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50015966\",\"e\":\"EE PRES. TANCREDO NEVES\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016024\",\"e\":\"EE PRESIDENTE VARGAS\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50026569\",\"e\":\"EE PROF. AL\u00cdCIO ARA\u00daJO\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50027581\",\"e\":\"EE PROF. CELSO M\u00dcLLER DO AMARAL\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50032860\",\"e\":\"EE PROF. JOS\u00c9 PEREIRA LINS\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016482\",\"e\":\"EE PROF\u00aa. FLORIANA LOPES\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016431\",\"e\":\"EE RAMONA DA SILVA PEDROSO\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50033646\",\"e\":\"EE RITA ANGELINA BARBOSA SILVEIRA\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016032\",\"e\":\"EE VILMAR VIEIRA MATOS\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50016873\",\"e\":\"EE ANT\u00d4NIO VICENTE AZAMBUJA\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50030388\",\"e\":\"EE IND\u00cdGENA INTERCULTURAL GUATEKA - MAR\u00c7AL DE SOUZA\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50033654\",\"e\":\"EE JOAQUIM VAZ DE OLIVEIRA\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50034251\",\"e\":\"EE VEREADOR MOACIR DJALMA BARROS\",\"m\":\"DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50020030\",\"e\":\"EE 13 DE MAIO\",\"m\":\"ELDORADO\",\"c\":\"CRE 08\"},{\"i\":\"50020021\",\"e\":\"EE ELDORADO\",\"m\":\"ELDORADO\",\"c\":\"CRE 08\"},{\"i\":\"50020323\",\"e\":\"EE SILO VARGAS BATISTA\",\"m\":\"ELDORADO\",\"c\":\"CRE 08\"},{\"i\":\"50017438\",\"e\":\"EE SEN. FILINTO M\u00dcLLER\",\"m\":\"F\u00c1TIMA DO SUL\",\"c\":\"CRE 05\"},{\"i\":\"50017497\",\"e\":\"EE VICENTE PALLOTTI\",\"m\":\"F\u00c1TIMA DO SUL\",\"c\":\"CRE 05\"},{\"i\":\"50017411\",\"e\":\"EE VILA BRASIL\",\"m\":\"F\u00c1TIMA DO SUL\",\"c\":\"CRE 05\"},{\"i\":\"50017560\",\"e\":\"EE JONAS BELARMINO DA SILVA\",\"m\":\"F\u00c1TIMA DO SUL\",\"c\":\"CRE 05\"},{\"i\":\"50003429\",\"e\":\"EE DR. ARNALDO ESTEV\u00c3O DE FIGUEIREDO\",\"m\":\"FIGUEIR\u00c3O\",\"c\":\"CRE 04\"},{\"i\":\"50020374\",\"e\":\"EE PROF\u00aa. EUFROSINA PINTO\",\"m\":\"GL\u00d3RIA DE DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50020382\",\"e\":\"EE PROF\u00aa. V\u00c2NIA MEDEIROS LOPES\",\"m\":\"GL\u00d3RIA DE DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50020609\",\"e\":\"EE WEIMAR TORRES\",\"m\":\"GL\u00d3RIA DE DOURADOS\",\"c\":\"CRE 05\"},{\"i\":\"50014420\",\"e\":\"EE ALZIRO LOPES\",\"m\":\"GUIA LOPES DA LAGUNA\",\"c\":\"CRE 07\"},{\"i\":\"50014439\",\"e\":\"EE SALOM\u00c9 DE MELO ROCHA\",\"m\":\"GUIA LOPES DA LAGUNA\",\"c\":\"CRE 07\"},{\"i\":\"50020650\",\"e\":\"EE 8 DE MAIO\",\"m\":\"IGUATEMI\",\"c\":\"CRE 08\"},{\"i\":\"50020668\",\"e\":\"EE MARC\u00cdLIO AUGUSTO PINTO\",\"m\":\"IGUATEMI\",\"c\":\"CRE 08\"},{\"i\":\"50011260\",\"e\":\"EE PROF. JO\u00c3O PEREIRA VALIM\",\"m\":\"INOC\u00caNCIA\",\"c\":\"CRE 10\"},{\"i\":\"50031910\",\"e\":\"EE JO\u00c3O PONCE DE ARRUDA\",\"m\":\"INOC\u00caNCIA\",\"c\":\"CRE 10\"},{\"i\":\"50017608\",\"e\":\"EE ANT\u00d4NIO JO\u00c3O RIBEIRO\",\"m\":\"ITAPOR\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50017616\",\"e\":\"EE EDSON BEZERRA\",\"m\":\"ITAPOR\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50022393\",\"e\":\"EE RODRIGUES ALVES\",\"m\":\"ITAPOR\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50017756\",\"e\":\"EE OLIVIA PAULA\",\"m\":\"ITAPOR\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50017772\",\"e\":\"EE PRINCESA IZABEL\",\"m\":\"ITAPOR\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50017730\",\"e\":\"EE SEN. SALDANHA DERZI\",\"m\":\"ITAPOR\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50020765\",\"e\":\"EE MANOEL GUILHERME DOS SANTOS\",\"m\":\"ITAQUIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50026259\",\"e\":\"EE PROF. JOS\u00c9 JUAREZ RIBEIRO DE OLIVEIRA\",\"m\":\"ITAQUIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50020854\",\"e\":\"EE ANGELINA JAIME TEBET\",\"m\":\"IVINHEMA\",\"c\":\"CRE 09\"},{\"i\":\"50020838\",\"e\":\"EE REYNALDO MASSI\",\"m\":\"IVINHEMA\",\"c\":\"CRE 09\"},{\"i\":\"50020846\",\"e\":\"EE SEN. FILINTO MULLER\",\"m\":\"IVINHEMA\",\"c\":\"CRE 09\"},{\"i\":\"50020986\",\"e\":\"EE JOAQUIM GON\u00c7ALVES LEDO\",\"m\":\"IVINHEMA\",\"c\":\"CRE 09\"},{\"i\":\"50021028\",\"e\":\"EE JAPOR\u00c3\",\"m\":\"JAPOR\u00c3\",\"c\":\"CRE 08\"},{\"i\":\"50034928\",\"e\":\"EE IND\u00cdGENA KU\u00d1A YRUKU - MARINA LOPES\",\"m\":\"JAPOR\u00c3\",\"c\":\"CRE 08\"},{\"i\":\"50009460\",\"e\":\"EE JOS\u00c9 SERAFIM RIBEIRO\",\"m\":\"JARAGUARI\",\"c\":\"CRE 02\"},{\"i\":\"50022377\",\"e\":\"EE ZUMBI DOS PALMARES\",\"m\":\"JARAGUARI\",\"c\":\"CRE 02\"},{\"i\":\"50014625\",\"e\":\"EE PROF. ANT\u00d4NIO PINTO PEREIRA\",\"m\":\"JARDIM\",\"c\":\"CRE 07\"},{\"i\":\"50014641\",\"e\":\"EE CEL. JUV\u00caNCIO\",\"m\":\"JARDIM\",\"c\":\"CRE 07\"},{\"i\":\"50014650\",\"e\":\"EE CEL. PEDRO JOS\u00c9 RUFINO\",\"m\":\"JARDIM\",\"c\":\"CRE 07\"},{\"i\":\"50021052\",\"e\":\"EE PROF\u00aa. BERNADETE DOS SANTOS LEITE\",\"m\":\"JATE\u00cd\",\"c\":\"CRE 05\"},{\"i\":\"50021060\",\"e\":\"EE PROF. JOAQUIM ALFREDO SOARES VIANNA\",\"m\":\"JATE\u00cd\",\"c\":\"CRE 05\"},{\"i\":\"50017799\",\"e\":\"EE 31 DE MAR\u00c7O\",\"m\":\"JUT\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50000675\",\"e\":\"EE 2 DE SETEMBRO\",\"m\":\"LAD\u00c1RIO\",\"c\":\"CRE 03\"},{\"i\":\"50000667\",\"e\":\"EE LEME DO PRADO\",\"m\":\"LAD\u00c1RIO\",\"c\":\"CRE 03\"},{\"i\":\"50017829\",\"e\":\"EE \u00c1LVARO MARTINS DOS SANTOS\",\"m\":\"LAGUNA CARAP\u00c3\",\"c\":\"CRE 05\"},{\"i\":\"50018116\",\"e\":\"EE CAMBARAI\",\"m\":\"MARACAJU\",\"c\":\"CRE 05\"},{\"i\":\"50018019\",\"e\":\"EE C\u00cdVICO-MILITAR CORONEL LIMA DE FIGUEIREDO\",\"m\":\"MARACAJU\",\"c\":\"CRE 05\"},{\"i\":\"50018027\",\"e\":\"EE MANOEL FERREIRA DE LIMA\",\"m\":\"MARACAJU\",\"c\":\"CRE 05\"},{\"i\":\"50018035\",\"e\":\"EE PADRE CONSTANTINO DE MONTE\",\"m\":\"MARACAJU\",\"c\":\"CRE 05\"},{\"i\":\"50002554\",\"e\":\"EE CAETANO PINTO\",\"m\":\"MIRANDA\",\"c\":\"CRE 01\"},{\"i\":\"50002546\",\"e\":\"EE CARMELITA CANALE REBU\u00c1\",\"m\":\"MIRANDA\",\"c\":\"CRE 01\"},{\"i\":\"50002562\",\"e\":\"EE DONA ROSA PEDROSSIAN\",\"m\":\"MIRANDA\",\"c\":\"CRE 01\"},{\"i\":\"50030850\",\"e\":\"EE IND\u00cdGENA CACIQUE TIM\u00d3TEO\",\"m\":\"MIRANDA\",\"c\":\"CRE 01\"},{\"i\":\"50082809\",\"e\":\"EE IND\u00cdGENA PROF. ATAN\u00c1SIO ALVES\",\"m\":\"MIRANDA\",\"c\":\"CRE 01\"},{\"i\":\"50033263\",\"e\":\"EE IND\u00cdGENA CACIQUE VICENTE DE ALMEIDA\",\"m\":\"MIRANDA\",\"c\":\"CRE 01\"},{\"i\":\"50021206\",\"e\":\"EE CASTELO BRANCO\",\"m\":\"MUNDO NOVO\",\"c\":\"CRE 08\"},{\"i\":\"50021214\",\"e\":\"EE MAL. RONDON\",\"m\":\"MUNDO NOVO\",\"c\":\"CRE 08\"},{\"i\":\"50021222\",\"e\":\"EE PROF\u00aa. IOLANDA ALLY\",\"m\":\"MUNDO NOVO\",\"c\":\"CRE 08\"},{\"i\":\"50021460\",\"e\":\"EE ANT\u00d4NIO FERNANDES\",\"m\":\"NAVIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50021346\",\"e\":\"EE EURICO GASPAR DUTRA\",\"m\":\"NAVIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50021354\",\"e\":\"EE JURACY ALVES CARDOSO\",\"m\":\"NAVIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50021370\",\"e\":\"EE PRESIDENTE M\u00c9DICI\",\"m\":\"NAVIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50021338\",\"e\":\"EE VIN\u00cdCIUS DE MORAES\",\"m\":\"NAVIRA\u00cd\",\"c\":\"CRE 08\"},{\"i\":\"50014889\",\"e\":\"EE ODETE IGN\u00caZ RESSTEL VILLAS BOAS\",\"m\":\"NIOAQUE\",\"c\":\"CRE 07\"},{\"i\":\"50030418\",\"e\":\"EE IND\u00cdGENA DE EM ANGELINA VICENTE\",\"m\":\"NIOAQUE\",\"c\":\"CRE 07\"},{\"i\":\"50014897\",\"e\":\"EE PADROEIRA DO BRASIL\",\"m\":\"NIOAQUE\",\"c\":\"CRE 07\"},{\"i\":\"50032569\",\"e\":\"EE UIRAPURU\",\"m\":\"NIOAQUE\",\"c\":\"CRE 07\"},{\"i\":\"50018230\",\"e\":\"EE ANT\u00d4NIO COELHO\",\"m\":\"NOVA ALVORADA DO SUL\",\"c\":\"CRE 02\"},{\"i\":\"50027646\",\"e\":\"EE DELFINA NOGUEIRA DE SOUZA\",\"m\":\"NOVA ALVORADA DO SUL\",\"c\":\"CRE 02\"},{\"i\":\"50013416\",\"e\":\"EE AUSTRILIO CAPIL\u00c9 CASTRO\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50013378\",\"e\":\"EE IRMAN RIBEIRO DE ALMEIDA SILVA\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50013424\",\"e\":\"EE LUIZ SOARES ANDRADE\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50013408\",\"e\":\"EE MAL. RONDON\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50013386\",\"e\":\"EE PADRE ANCHIETA\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50013394\",\"e\":\"EE PROF\u00aa. F\u00c1TIMA GAIOTTO SAMPAIO\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50013432\",\"e\":\"EE PROF\u00aa. NAIR PAL\u00c1CIO DE SOUZA\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50082884\",\"e\":\"EE PROF. LUIZ CARLOS SAMPAIO\",\"m\":\"NOVA ANDRADINA\",\"c\":\"CRE 09\"},{\"i\":\"50026852\",\"e\":\"EE DORCELINA DE OLIVEIRA FOLADOR\",\"m\":\"NOVO HORIZONTE DO SUL\",\"c\":\"CRE 09\"},{\"i\":\"50010972\",\"e\":\"EE VER. KENDI NAKAI\",\"m\":\"PARA\u00cdSO DAS \u00c1GUAS\",\"c\":\"CRE 10\"},{\"i\":\"50011383\",\"e\":\"EE ARACILDA C\u00cdCERO CORR\u00caA DA COSTA\",\"m\":\"PARANA\u00cdBA\",\"c\":\"CRE 10\"},{\"i\":\"50011391\",\"e\":\"EE DR. ERM\u00cdRIO LEAL GARCIA\",\"m\":\"PARANA\u00cdBA\",\"c\":\"CRE 10\"},{\"i\":\"50011405\",\"e\":\"EE JOS\u00c9 GARCIA LEAL\",\"m\":\"PARANA\u00cdBA\",\"c\":\"CRE 10\"},{\"i\":\"50011413\",\"e\":\"EE MANOEL GARCIA LEAL\",\"m\":\"PARANA\u00cdBA\",\"c\":\"CRE 10\"},{\"i\":\"50011421\",\"e\":\"EE WLADISLAU GARCIA GOMES\",\"m\":\"PARANA\u00cdBA\",\"c\":\"CRE 10\"},{\"i\":\"50021540\",\"e\":\"EE SANTIAGO BENITES\",\"m\":\"PARANHOS\",\"c\":\"CRE 11\"},{\"i\":\"50003852\",\"e\":\"EE FRANCISCO RIBEIRO SOARES\",\"m\":\"PEDRO GOMES\",\"c\":\"CRE 04\"},{\"i\":\"50003860\",\"e\":\"EE PROF\u00aa. CLEUZA TEODORO\",\"m\":\"PEDRO GOMES\",\"c\":\"CRE 04\"},{\"i\":\"50018345\",\"e\":\"EE AD\u00ca MARQUES\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018353\",\"e\":\"EE DEP. FERNANDO CL\u00c1UDIO CAPIBERIBE SALDANHA\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018361\",\"e\":\"EE DR. MIGUEL MARCONDES ARMANDO\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018388\",\"e\":\"EE JO\u00c3O BREMBATTI CALVOSO\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018744\",\"e\":\"EE JOAQUIM MURTINHO\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50022725\",\"e\":\"EE MENDES GON\u00c7ALVES\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018418\",\"e\":\"EE PROF\u00aa. GENI MARQUES MAGALH\u00c3ES\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018370\",\"e\":\"EE NOVA ITAMARATI\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50019120\",\"e\":\"EE PEDRO AFONSO PEREIRA GOLDONI\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50039806\",\"e\":\"EE PROF. CARLOS PEREIRA DA SILVA\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50018469\",\"e\":\"EE CORONEL RAMIRO NORONHA\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50028456\",\"e\":\"EE PROF. JOS\u00c9 EDSON DOMINGOS DOS SANTOS\",\"m\":\"PONTA POR\u00c3\",\"c\":\"CRE 11\"},{\"i\":\"50000799\",\"e\":\"EE JOS\u00c9 BONIF\u00c1CIO\",\"m\":\"PORTO MURTINHO\",\"c\":\"CRE 07\"},{\"i\":\"50034936\",\"e\":\"EE IND\u00cdGENA ANT\u00d4NIO ALVES DE BARROS\",\"m\":\"PORTO MURTINHO\",\"c\":\"CRE 07\"},{\"i\":\"50011936\",\"e\":\"EE DR. JO\u00c3O PONCE DE ARRUDA\",\"m\":\"RIBAS DO RIO PARDO\",\"c\":\"CRE 02\"},{\"i\":\"50011944\",\"e\":\"EE EDUARDO BATISTA AMORIM\",\"m\":\"RIBAS DO RIO PARDO\",\"c\":\"CRE 02\"},{\"i\":\"50019252\",\"e\":\"EE ETAL\u00cdVIO PEREIRA MARTINS\",\"m\":\"RIO BRILHANTE\",\"c\":\"CRE 05\"},{\"i\":\"50019260\",\"e\":\"EE FERNANDO CORR\u00caA DA COSTA\",\"m\":\"RIO BRILHANTE\",\"c\":\"CRE 05\"},{\"i\":\"50019295\",\"e\":\"EE PROF\u00aa. LIGIA TEREZINHA MARTINS\",\"m\":\"RIO BRILHANTE\",\"c\":\"CRE 05\"},{\"i\":\"50009672\",\"e\":\"EE LEONTINO ALVES DE OLIVEIRA\",\"m\":\"RIO NEGRO\",\"c\":\"CRE 04\"},{\"i\":\"50004077\",\"e\":\"EE THOMAZ BARBOSA RANGEL\",\"m\":\"RIO VERDE DE MATO GROSSO\",\"c\":\"CRE 04\"},{\"i\":\"50004085\",\"e\":\"EE VERGELINO MATEUS DE OLIVEIRA\",\"m\":\"RIO VERDE DE MATO GROSSO\",\"c\":\"CRE 04\"},{\"i\":\"50009788\",\"e\":\"EE JOS\u00c9 ALVES RIBEIRO\",\"m\":\"ROCHEDO\",\"c\":\"CRE 02\"},{\"i\":\"50012010\",\"e\":\"EE JOS\u00c9 FERREIRA LIMA\",\"m\":\"SANTA RITA DO PARDO\",\"c\":\"CRE 12\"},{\"i\":\"50004352\",\"e\":\"EE BERNARDINO FERREIRA DA CUNHA\",\"m\":\"S\u00c3O GABRIEL DO OESTE\",\"c\":\"CRE 04\"},{\"i\":\"50027638\",\"e\":\"EE PROF\u00aa. CREUZA APARECIDA DELLA COLETA\",\"m\":\"S\u00c3O GABRIEL DO OESTE\",\"c\":\"CRE 04\"},{\"i\":\"50004344\",\"e\":\"EE S\u00c3O GABRIEL\",\"m\":\"S\u00c3O GABRIEL DO OESTE\",\"c\":\"CRE 04\"},{\"i\":\"50028960\",\"e\":\"EE DORCELINA FOLADOR\",\"m\":\"S\u00c3O GABRIEL DO OESTE\",\"c\":\"CRE 04\"},{\"i\":\"50011618\",\"e\":\"EE ANA MARIA DE SOUZA\",\"m\":\"SELV\u00cdRIA\",\"c\":\"CRE 12\"},{\"i\":\"50021699\",\"e\":\"EE 13 DE MAIO\",\"m\":\"SETE QUEDAS\",\"c\":\"CRE 08\"},{\"i\":\"50021702\",\"e\":\"EE 4 DE ABRIL\",\"m\":\"SETE QUEDAS\",\"c\":\"CRE 08\"},{\"i\":\"50021710\",\"e\":\"EE GUIMAR\u00c3ES ROSA\",\"m\":\"SETE QUEDAS\",\"c\":\"CRE 08\"},{\"i\":\"50009850\",\"e\":\"EE PROF\u00aa. CATARINA DE ABREU\",\"m\":\"SIDROL\u00c2NDIA\",\"c\":\"CRE 02\"},{\"i\":\"50009869\",\"e\":\"EE SIDR\u00d4NIO ANTUNES DE ANDRADE\",\"m\":\"SIDROL\u00c2NDIA\",\"c\":\"CRE 02\"},{\"i\":\"50030760\",\"e\":\"EE KOPENOTI DE EM PROF. L\u00daCIO DIAS\",\"m\":\"SIDROL\u00c2NDIA\",\"c\":\"CRE 02\"},{\"i\":\"50023390\",\"e\":\"EE PAULO EDUARDO DE SOUZA FIRMO\",\"m\":\"SIDROL\u00c2NDIA\",\"c\":\"CRE 02\"},{\"i\":\"50009974\",\"e\":\"EE VESPASIANO MARTINS\",\"m\":\"SIDROL\u00c2NDIA\",\"c\":\"CRE 02\"},{\"i\":\"50004620\",\"e\":\"EE COMANDANTE MAUR\u00cdCIO COUTINHO DUTRA\",\"m\":\"SONORA\",\"c\":\"CRE 04\"},{\"i\":\"50021796\",\"e\":\"EE PROF. CLETO DE MORAES COSTA\",\"m\":\"TACURU\",\"c\":\"CRE 08\"},{\"i\":\"50034090\",\"e\":\"EE IND\u00cdGENA JASY RENDY\",\"m\":\"TACURU\",\"c\":\"CRE 08\"},{\"i\":\"50013610\",\"e\":\"EE DR. MARTINHO MARQUES\",\"m\":\"TAQUARUSSU\",\"c\":\"CRE 09\"},{\"i\":\"50010026\",\"e\":\"EE ANT\u00d4NIO VALADARES\",\"m\":\"TERENOS\",\"c\":\"CRE 02\"},{\"i\":\"50010034\",\"e\":\"EE EDUARDO PEREZ\",\"m\":\"TERENOS\",\"c\":\"CRE 02\"},{\"i\":\"50010018\",\"e\":\"EE ANT\u00d4NIO NOGUEIRA DA FONSECA\",\"m\":\"TERENOS\",\"c\":\"CRE 02\"},{\"i\":\"50012096\",\"e\":\"EE AFONSO PENA\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012100\",\"e\":\"EE BOM JESUS\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012118\",\"e\":\"EE DOM AQUINO CORR\u00caA\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012126\",\"e\":\"EE EDWARDS CORR\u00caA E SOUZA\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012134\",\"e\":\"EE FERNANDO CORR\u00caA\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012142\",\"e\":\"EE JO\u00c3O DANTAS FILGUEIRAS\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012177\",\"e\":\"EE JO\u00c3O PONCE DE ARRUDA\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012088\",\"e\":\"EE JOS\u00c9 FERREIRA\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50032089\",\"e\":\"EE LUIZ LOPES DE CARVALHO\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012150\",\"e\":\"EE PADRE JO\u00c3O TOMES\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012169\",\"e\":\"EE PROF. JO\u00c3O MAGIANO PINTO\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50012525\",\"e\":\"EE AFONSO FRANCISCO XAVIER TRANNIN\",\"m\":\"TR\u00caS LAGOAS\",\"c\":\"CRE 12\"},{\"i\":\"50019384\",\"e\":\"EE PADRE JOS\u00c9 DANIEL\",\"m\":\"VICENTINA\",\"c\":\"CRE 05\"},{\"i\":\"50019449\",\"e\":\"EE EMANNUEL PINHEIRO\",\"m\":\"VICENTINA\",\"c\":\"CRE 05\"},{\"i\":\"50019430\",\"e\":\"EE S\u00c3O JOS\u00c9\",\"m\":\"VICENTINA\",\"c\":\"CRE 05\"}]";

var CONFIG = {
  abaReferencia: '_Referencia',
  colStatus: 'Status Conferencia',
  colObs: 'Observacao Conferencia',
  limiarNucleo: 0.72,
  cores: {
    ok: '#d9ead3',           // match 100%
    parcial: '#fff2cc',      // nucleo coincide, nome difere
    creErrada: '#fce5cd',    // escola/municipio ok, CRE errada
    municipioErrado: '#f4cccc', // municipio nao bate com referencia
    naoEncontrada: '#e6b8af',   // escola ausente no PDF
    vazia: '#efefef',
    cabecalho: '#cfe2f3'
  }
};

var _cacheRef = null;

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Conferencia Escolas')
    .addItem('Conferir planilha ativa', 'conferirPlanilhaAtiva')
    .addItem('Popular aba _Referencia', 'popularAbaReferencia')
    .addItem('Limpar marcacoes', 'limparMarcacoes')
    .addSeparator()
    .addItem('Ver legenda de cores', 'mostrarLegenda')
    .addToUi();
}

function mostrarLegenda() {
  var msg = [
    'Verde: escola, municipio e CRE conferem (match 100%)',
    'Amarelo: nucleo do nome coincide, mas grafia difere; municipio e CRE ok',
    'Laranja: escola e municipio ok mas CRE divergente, ou municipio associado a CRE errada',
    'Vermelho: municipio errado (escola existe em outro municipio no PDF)',
    'Marrom: escola nao encontrada no PDF de referencia',
    'Cinza: linha vazia'
  ].join('\n');
  SpreadsheetApp.getUi().alert('Legenda', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

// --- Normalizacao -----------------------------------------------------------

function normalizarTexto(texto) {
  if (texto === null || texto === undefined || texto === '') return '';
  var s = String(texto).trim().toUpperCase();
  s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  s = s.replace(/[^A-Z0-9 ]+/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}

function normalizarNomeEscola(texto) {
  var s = normalizarTexto(texto);
  if (!s) return '';

  s = s.replace(/\bPROF A\b|\bPROF O\b/g, 'PROF');
  s = s.replace(/\bPROFAS?\b|\bPROFS?\b/g, 'PROF');
  s = s.replace(/\bESCOLA CIVICO MILITAR\b/g, 'ECIM');
  s = s.replace(/\bESCOLA CIVICO\b\s+\bMILITAR\b/g, 'ECIM');
  s = s.replace(/\bCIVICO MILITAR\b/g, 'ECIM');
  s = s.replace(/\bEE\s*CM\b/g, 'ECIM');
  s = s.replace(/\bEECM\b/g, 'ECIM');

  var subs = [
    [/\bESCOLA ESTADUAL\b/g, 'EE'],
    [/\bE\s*\.\s*E\s*\./g, 'EE'],
    [/\bE\s+E\b/g, 'EE'],
    [/\bESC EST\b/g, 'EE'],
    [/\bESCOLA\b/g, 'EE'],
    [/\bCENTRO ESTADUAL DE EDUCACAO PROFISSIONAL\b/g, 'CEEP'],
    [/\bCENTRO DE EDUCACAO PROFISSIONAL\b/g, 'CEEP'],
    [/\bCENTRO ESTADUAL DE EDUCACAO DE JOVENS E ADULTOS\b/g, 'CEEJA'],
    [/\bCENTRO DE EDUCACAO DE JOVENS E ADULTOS\b/g, 'CEEJA'],
    [/\bPROFESSORA\b/g, 'PROF'],
    [/\bPROFESSOR\b/g, 'PROF'],
    [/\bPROFA\b/g, 'PROF'],
    [/\bPROF\b/g, 'PROF'],
    [/\bPADRE\b/g, 'PE'],
    [/\bPRESIDENTE\b/g, 'PRES'],
    [/\bDEPUTADO\b/g, 'DEP'],
    [/\bCORONEL\b/g, 'CEL'],
    [/\bMARECHAL\b/g, 'MAL'],
    [/\bDOUTORA\b/g, 'DRA'],
    [/\bDOUTOR\b/g, 'DR'],
    [/\bIRMA\b/g, 'IRMA'],
    [/\bIRMAO\b/g, 'IRMA'],
    [/\bDONA\b/g, 'DONA']
  ];
  subs.forEach(function (par) { s = s.replace(par[0], par[1]); });

  s = s.replace(/\bEE\s+EE\b/g, 'EE');
  s = s.replace(/\bECIM\b/g, 'EE');
  s = s.replace(/\bEXTENSAO\b.*$/, '');
  s = s.replace(/\bANEXO\b.*$/, '');
  s = s.replace(/\bSALA\b.*$/, '');
  s = s.replace(/\bMS\b$/, '');
  s = s.replace(/\bDE\b|\bDO\b|\bDA\b|\bDOS\b|\bDAS\b/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}

function normalizarCre(cre) {
  if (cre === null || cre === undefined || cre === '') return '';
  var s = String(cre).trim().toUpperCase();
  if (s.indexOf('SED') >= 0 || s.indexOf('CAMPO GRANDE CAPITAL') >= 0) return 'SED';
  var m = s.match(/CRE\s*\d+/);
  if (m) return m[0].replace(/\s+/g, ' ');
  return s;
}

function chaveEscolaMunicipio(escola, municipio) {
  return normalizarNomeEscola(escola) + '|' + normalizarTexto(municipio);
}

// --- Referencia -------------------------------------------------------------

function parseReferenciaEmbutida_() {
  if (Array.isArray(REFERENCIA_JSON)) {
    return REFERENCIA_JSON;
  }
  if (typeof REFERENCIA_JSON === 'string' && REFERENCIA_JSON.length) {
    return JSON.parse(REFERENCIA_JSON);
  }
  throw new Error('Referencia embutida invalida. Regenere o script.');
}

function carregarReferencia() {
  if (_cacheRef) return _cacheRef;

  var dados = null;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(CONFIG.abaReferencia);
  if (sh && sh.getLastRow() > 1) {
    dados = lerReferenciaDaAba_(sh);
  }
  if (!dados || !dados.length) {
    try {
      dados = parseReferenciaEmbutida_();
    } catch (e) {
      throw new Error('Referencia indisponivel. Execute popularAbaReferencia() ou regenere o script.');
    }
  }

  _cacheRef = indexarReferencia_(dados);
  return _cacheRef;
}

function lerReferenciaDaAba_(sh) {
  var vals = sh.getDataRange().getValues();
  if (vals.length < 2) return [];
  var hdr = vals[0].map(function (h) { return normalizarTexto(h); });
  var ixInep = hdr.indexOf('INEP');
  var ixEsc = hdr.indexOf('UNIDADE ESCOLAR') >= 0 ? hdr.indexOf('UNIDADE ESCOLAR') : hdr.indexOf('ESCOLA');
  var ixMun = hdr.indexOf('MUNICIPIO');
  var ixCre = hdr.indexOf('CRE');
  if (ixInep < 0) ixInep = 0;
  if (ixEsc < 0) ixEsc = 1;
  if (ixMun < 0) ixMun = 2;
  if (ixCre < 0) ixCre = 3;

  var out = [];
  for (var r = 1; r < vals.length; r++) {
    var row = vals[r];
    if (!row[ixEsc] && !row[ixInep]) continue;
    out.push({
      i: String(row[ixInep] || '').trim(),
      e: String(row[ixEsc] || '').trim(),
      m: String(row[ixMun] || '').trim(),
      c: String(row[ixCre] || '').trim()
    });
  }
  return out;
}

function indexarReferencia_(dados) {
  var porInep = {};
  var porChave = {};
  var porMunicipio = {};
  var lista = [];

  dados.forEach(function (item) {
    var ref = {
      inep: String(item.i || item.inep || '').trim(),
      escola: String(item.e || item.escola || '').trim(),
      municipio: String(item.m || item.municipio || '').trim(),
      cre: String(item.c || item.cre || '').trim(),
      escolaNorm: normalizarNomeEscola(item.e || item.escola),
      municipioNorm: normalizarTexto(item.m || item.municipio),
      creNorm: normalizarCre(item.c || item.cre)
    };
    lista.push(ref);
    if (ref.inep) porInep[ref.inep] = ref;
    var chave = ref.escolaNorm + '|' + ref.municipioNorm;
    if (!porChave[chave]) porChave[chave] = ref;
    if (!porMunicipio[ref.municipioNorm]) porMunicipio[ref.municipioNorm] = [];
    porMunicipio[ref.municipioNorm].push(ref);
  });

  var crePorMunicipio = {};
  lista.forEach(function (ref) {
    if (ref.municipioNorm && ref.creNorm) {
      crePorMunicipio[ref.municipioNorm] = ref.creNorm;
    }
  });

  return {
    lista: lista,
    porInep: porInep,
    porChave: porChave,
    porMunicipio: porMunicipio,
    crePorMunicipio: crePorMunicipio
  };
}

function popularAbaReferencia() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(CONFIG.abaReferencia);
  if (!sh) {
    sh = ss.insertSheet(CONFIG.abaReferencia);
  }
  sh.clear();
  sh.getRange(1, 1, 1, 4).setValues([['INEP', 'Unidade Escolar', 'Municipio', 'CRE']]);
  var dados = parseReferenciaEmbutida_();
  var rows = dados.map(function (d) { return [d.i, d.e, d.m, d.c]; });
  if (rows.length) {
    sh.getRange(2, 1, 1 + rows.length, 4).setValues(rows);
  }
  sh.setFrozenRows(1);
  _cacheRef = null;
  SpreadsheetApp.getUi().alert('Aba _Referencia populada com ' + rows.length + ' escolas.');
}

// --- Matching ---------------------------------------------------------------

var TOKENS_STOP = {
  'EE': 1, 'CEEP': 1, 'CEEJA': 1, 'PROF': 1, 'PE': 1, 'PRES': 1, 'DEP': 1,
  'CEL': 1, 'MAL': 1, 'DR': 1, 'DRA': 1, 'IRMA': 1, 'DONA': 1, 'MS': 1, 'ECIM': 1
};

function tokensNucleo(escolaNorm) {
  return escolaNorm.split(' ').filter(function (t) {
    return t.length > 1 && !TOKENS_STOP[t];
  });
}

function similaridadeNucleo(aNorm, bNorm) {
  if (!aNorm || !bNorm) return 0;
  if (aNorm === bNorm) return 1;

  var ta = tokensNucleo(aNorm);
  var tb = tokensNucleo(bNorm);
  if (!ta.length || !tb.length) return 0;

  var setB = {};
  tb.forEach(function (t) { setB[t] = true; });
  var inter = 0;
  ta.forEach(function (t) { if (setB[t]) inter++; });

  var union = {};
  ta.concat(tb).forEach(function (t) { union[t] = true; });
  var jaccard = inter / Object.keys(union).length;

  var minSize = Math.min(ta.length, tb.length);
  var subset = inter >= Math.max(2, minSize - 1) && inter >= minSize * 0.85;

  return Math.max(jaccard, subset ? 0.86 : 0);
}

function buscarReferencia(refIdx, escola, municipio, inepOpt) {
  if (inepOpt) {
    var direto = refIdx.porInep[String(inepOpt).trim()];
    if (direto) {
      return { ref: direto, score: 1, modo: 'inep' };
    }
  }

  var escNorm = normalizarNomeEscola(escola);
  var munNorm = normalizarTexto(municipio);
  if (!escNorm) return null;

  var chave = escNorm + '|' + munNorm;
  if (refIdx.porChave[chave]) {
    return { ref: refIdx.porChave[chave], score: 1, modo: 'exato' };
  }

  var candidatos = refIdx.porMunicipio[munNorm] || [];
  var melhor = null;
  candidatos.forEach(function (c) {
    var sc = similaridadeNucleo(escNorm, c.escolaNorm);
    if (!melhor || sc > melhor.score) melhor = { ref: c, score: sc, modo: 'fuzzy_municipio' };
  });
  if (melhor && melhor.score >= CONFIG.limiarNucleo) return melhor;

  // Busca global para detectar municipio errado
  var global = null;
  refIdx.lista.forEach(function (c) {
    var sc = similaridadeNucleo(escNorm, c.escolaNorm);
    if (!global || sc > global.score) global = { ref: c, score: sc, modo: 'fuzzy_global' };
  });
  if (global && global.score >= CONFIG.limiarNucleo) return global;

  return null;
}

function avaliarLinha(refIdx, escola, municipio, cre, inepOpt) {
  if (!escola && !municipio && !cre) {
    return { status: 'VAZIA', obs: '', cor: CONFIG.cores.vazia };
  }

  var munPlan = normalizarTexto(municipio);
  var crePlan = normalizarCre(cre);
  var creEsperadaMuni = munPlan ? refIdx.crePorMunicipio[munPlan] : '';

  if (munPlan && crePlan && creEsperadaMuni && crePlan !== creEsperadaMuni) {
    return {
      status: 'CRE/MUNICIPIO INCOMPATIVEL',
      obs: 'Municipio "' + municipio + '" pertence a ' + creEsperadaMuni +
        ' (planilha: ' + (cre || '(vazio)') + ')',
      cor: CONFIG.cores.creErrada
    };
  }

  var match = buscarReferencia(refIdx, escola, municipio, inepOpt);

  if (!match) {
    return {
      status: 'NAO ENCONTRADA',
      obs: 'Escola nao localizada no PDF de referencia (Fev/2025)',
      cor: CONFIG.cores.naoEncontrada
    };
  }

  var ref = match.ref;
  var nomeExato = match.score >= 1 && normalizarNomeEscola(escola) === ref.escolaNorm;
  var munOk = munPlan === ref.municipioNorm;
  var creOk = crePlan === ref.creNorm;

  if (!munOk) {
    return {
      status: 'MUNICIPIO ERRADO',
      obs: 'No PDF: ' + ref.municipio + ' / CRE ' + ref.cre + ' (INEP ' + ref.inep + ')',
      cor: CONFIG.cores.municipioErrado,
      ref: ref
    };
  }

  if (!creOk) {
    return {
      status: 'CRE ERRADA',
      obs: 'CRE esperada: ' + ref.cre + ' | Planilha: ' + (cre || '(vazio)') + ' | INEP ' + ref.inep,
      cor: CONFIG.cores.creErrada,
      ref: ref
    };
  }

  if (nomeExato || match.modo === 'exato' || match.modo === 'inep') {
    return {
      status: 'OK',
      obs: 'Conferido com PDF (INEP ' + ref.inep + ')',
      cor: CONFIG.cores.ok,
      ref: ref
    };
  }

  return {
    status: 'OK PARCIAL',
    obs: 'Nucleo coincide; PDF: "' + ref.escola + '" | INEP ' + ref.inep,
    cor: CONFIG.cores.parcial,
    ref: ref
  };
}

// --- Planilha ---------------------------------------------------------------

function detectarColunas_(headerRow) {
  var cols = { escola: -1, municipio: -1, cre: -1, inep: -1 };
  for (var c = 0; c < headerRow.length; c++) {
    var h = normalizarTexto(headerRow[c]);
    if (cols.escola < 0 && (h.indexOf('UNIDADE ESCOLAR') >= 0 || h === 'ESCOLA' || h.indexOf('NOME ESCOLA') >= 0)) {
      cols.escola = c;
    } else if (cols.municipio < 0 && h.indexOf('MUNICIPIO') >= 0) {
      cols.municipio = c;
    } else if (cols.cre < 0 && (h === 'CRE' || /^CRE(\s|$)/.test(h))) {
      cols.cre = c;
    } else if (cols.inep < 0 && (h.indexOf('INEP') >= 0 || h.indexOf('COD INEP') >= 0 || h.indexOf('CODIGO INEP') >= 0)) {
      cols.inep = c;
    }
  }
  return cols;
}

function encontrarLinhaCabecalho_(sheet) {
  var maxScan = Math.min(15, sheet.getLastRow());
  var width = Math.max(sheet.getLastColumn(), 10);
  for (var r = 1; r <= maxScan; r++) {
    var row = sheet.getRange(r, 1, 1, width).getValues()[0];
    var cols = detectarColunas_(row);
    if (cols.escola >= 0 && cols.municipio >= 0) {
      return { row: r, cols: cols, header: row };
    }
  }
  throw new Error('Cabecalho nao encontrado. Colunas necessarias: Unidade Escolar e Municipio.');
}

function conferirPlanilhaAtiva() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  if (sheet.getName() === CONFIG.abaReferencia) {
    SpreadsheetApp.getUi().alert('Selecione a aba de dados (nao _Referencia).');
    return;
  }

  var refIdx = carregarReferencia();
  var cab = encontrarLinhaCabecalho_(sheet);
  var header = cab.header.slice();
  var cols = cab.cols;

  var ixStatus = header.map(function (h) { return String(h); }).indexOf(CONFIG.colStatus);
  var ixObs = header.map(function (h) { return String(h); }).indexOf(CONFIG.colObs);
  var nextCol = header.length;

  if (ixStatus < 0) {
    ixStatus = nextCol++;
    sheet.getRange(cab.row, ixStatus + 1).setValue(CONFIG.colStatus);
  }
  if (ixObs < 0) {
    ixObs = nextCol++;
    sheet.getRange(cab.row, ixObs + 1).setValue(CONFIG.colObs);
  }

  var lastRow = sheet.getLastRow();
  if (lastRow <= cab.row) {
    SpreadsheetApp.getUi().alert('Nenhuma linha de dados abaixo do cabecalho.');
    return;
  }

  var numRows = lastRow - cab.row;
  var width = Math.max(sheet.getLastColumn(), ixObs + 1);
  var data = sheet.getRange(cab.row + 1, 1, numRows, width).getValues();

  var resumo = { ok: 0, parcial: 0, cre: 0, mun: 0, ne: 0, vazia: 0 };
  var backgrounds = [];
  var statusCol = [];
  var obsCol = [];

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var escola = row[cols.escola];
    var municipio = row[cols.municipio];
    var cre = cols.cre >= 0 ? row[cols.cre] : '';
    var inep = cols.inep >= 0 ? row[cols.inep] : '';

    var av = avaliarLinha(refIdx, escola, municipio, cre, inep);
    statusCol.push([av.status]);
    obsCol.push([av.obs]);

    var bgRow = [];
    for (var j = 0; j < width; j++) bgRow.push(null);
    bgRow[cols.escola] = av.cor;
    if (cols.municipio >= 0) bgRow[cols.municipio] = av.cor;
    if (cols.cre >= 0) bgRow[cols.cre] = av.cor;
    backgrounds.push(bgRow);

    switch (av.status) {
      case 'OK': resumo.ok++; break;
      case 'OK PARCIAL': resumo.parcial++; break;
      case 'CRE ERRADA':
      case 'CRE/MUNICIPIO INCOMPATIVEL': resumo.cre++; break;
      case 'MUNICIPIO ERRADO': resumo.mun++; break;
      case 'NAO ENCONTRADA': resumo.ne++; break;
      default: resumo.vazia++;
    }
  }

  var dataRange = sheet.getRange(cab.row + 1, 1, numRows, width);
  dataRange.setBackgrounds(backgrounds);
  sheet.getRange(cab.row + 1, ixStatus + 1, numRows, 1).setValues(statusCol);
  sheet.getRange(cab.row + 1, ixObs + 1, numRows, 1).setValues(obsCol);
  sheet.getRange(cab.row, ixStatus + 1, 1, 2).setBackground(CONFIG.cores.cabecalho);

  var msg = [
    'Conferencia concluida — ' + sheet.getName(),
    '',
    'OK (100%): ' + resumo.ok,
    'OK parcial (nome): ' + resumo.parcial,
    'CRE errada: ' + resumo.cre,
    'Municipio errado: ' + resumo.mun,
    'Nao encontrada: ' + resumo.ne,
    'Linhas vazias: ' + resumo.vazia,
    '',
    'Verifique linhas em vermelho, laranja e marrom.'
  ].join('\n');

  SpreadsheetApp.getUi().alert('Conferencia Escolas', msg, SpreadsheetApp.getUi().ButtonSet.OK);
}

function limparMarcacoes() {
  var sheet = SpreadsheetApp.getActiveSheet();
  if (sheet.getName() === CONFIG.abaReferencia) return;

  var cab = encontrarLinhaCabecalho_(sheet);
  var lastRow = sheet.getLastRow();
  if (lastRow <= cab.row) return;

  var width = sheet.getLastColumn();
  sheet.getRange(cab.row + 1, 1, lastRow - cab.row, width).setBackground(null);

  var header = sheet.getRange(cab.row, 1, 1, width).getValues()[0];
  [CONFIG.colStatus, CONFIG.colObs].forEach(function (nome) {
    for (var c = 0; c < header.length; c++) {
      if (String(header[c]) === nome) {
        sheet.getRange(cab.row + 1, c + 1, lastRow - cab.row, 1).clearContent();
      }
    }
  });
}
