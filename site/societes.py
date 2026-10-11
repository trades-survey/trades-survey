"""Noms de sociétés : regroupement des libellés déclarés, ISIN, SIREN, nature et secteur.

Partagé par site/build.py et par les scripts qui croisent les participations avec d'autres sources
(répertoire des représentants d'intérêts, amendements de l'Assemblée nationale).
"""
import re, unicodedata
def norm(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+',' ',s).strip()
ALIAS={'TOTAL ENERGIES':'TOTALENERGIES','TOTAL ENERGIES SE':'TOTALENERGIES','TOTALENERGIES SE':'TOTALENERGIES','TOTAL':'TOTALENERGIES','TOTAL SA':'TOTALENERGIES',
 'CAP GEMINI':'CAPGEMINI','CAPGEMINI SE':'CAPGEMINI','VEOLIA ENVIRONNEMENT':'VEOLIA','VEOLIA ENVIRONNEMENT SA':'VEOLIA','SCHNEIDER':'SCHNEIDER ELECTRIC','SCHNEIDER ELECTRIC SE':'SCHNEIDER ELECTRIC',
 'AIRBUS SE':'AIRBUS','AIRBUS GROUP':'AIRBUS','AIR FRANCE':'AIR FRANCE KLM','AIR LIQUIDE SA':'AIR LIQUIDE','AXA SA':'AXA','ENGIE SA':'ENGIE','ORANGE SA':'ORANGE','SANOFI SA':'SANOFI',
 'BNP':'BNP PARIBAS','BNP PARIBAS SA':'BNP PARIBAS','SOCIETE GENERALE SA':'SOCIETE GENERALE','LVMH MOET HENNESSY LOUIS VUITTON':'LVMH','MICHELIN CGDE':'MICHELIN','COMPAGNIE GENERALE DES ETABLISSEMENTS MICHELIN':'MICHELIN',
 'SOPRA STERIA GROUP':'SOPRA STERIA','HERMES INTERNATIONAL':'HERMES','STMICROELECTRONICS NV':'STMICROELECTRONICS','STELLANTIS NV':'STELLANTIS','THALES SA':'THALES','DANONE SA':'DANONE',
 'AEROPORTS DE PARIS':'ADP','GROUPE ADP':'ADP','FRANCAISE DES JEUX':'FDJ','LA FRANCAISE DES JEUX':'FDJ','FDJ UNITED':'FDJ','VINCI SA':'VINCI','KERING SA':'KERING','RENAULT SA':'RENAULT','SAFRAN SA':'SAFRAN',
 'TOTALENERGIE':'TOTALENERGIES','TOTAL ENERGIE':'TOTALENERGIES','ESSILOR LUXOTTICA':'ESSILORLUXOTTICA','ESSILOR INTL':'ESSILORLUXOTTICA','ESSILOR':'ESSILORLUXOTTICA',
 'LVMH MOET VUITTON':'LVMH','LVMH MOET HENNESSY':'LVMH','HERMES INTL':'HERMES','SAINT GOBAIN CIE':'SAINT GOBAIN','COMPAGNIE DE SAINT GOBAIN':'SAINT GOBAIN',
 'DASSAULT SYSTEM':'DASSAULT SYSTEMES','WORDLINE':'WORLDLINE','AIR LIQUIDE PRIME':'AIR LIQUIDE','AIR LIQUIDE PRIME FIDELITE':'AIR LIQUIDE','ASML':'ASML HOLDING',
 'PUBLICIS':'PUBLICIS GROUPE','UNIBAIL RODAMCO WESTFIELD':'UNIBAIL RODAMCO','UNIBAIL':'UNIBAIL RODAMCO','URW':'UNIBAIL RODAMCO','EUTELSAT':'EUTELSAT COMMUNICATIONS',
 'BNP PARIBAS ACTIONS A':'BNP PARIBAS','CREDIT AGRICOLE S A':'CREDIT AGRICOLE SA','CASA':'CREDIT AGRICOLE SA','ELECTRICITE DE FRANCE':'EDF',
 'CAISSE DEPARGNE':'CAISSE D EPARGNE','LMVH MOET HENESSY':'LVMH','LMVH':'LVMH','CAISSE EPARGNE':'CAISSE D EPARGNE'}
# ISIN rattachés à la main (code vérifié par sa clé de contrôle ; le rattachement au nom déclaré reste à vérifier)
ISIN={'AIR LIQUIDE':'FR0000120073','AXA':'FR0000120628','ENGIE':'FR0010208488','ORANGE':'FR0000133308','SANOFI':'FR0000120578','MICHELIN':'FR001400AJ45',
 'AIRBUS':'NL0000235190','BNP PARIBAS':'FR0000131104','RENAULT':'FR0000131906','SAFRAN':'FR0000073272','STELLANTIS':'NL00150001Q9','DANONE':'FR0000120644',
 'THALES':'FR0000121329','L OREAL':'FR0000120321',
 # ajoutés le 2026-10-08 : sociétés citées par au moins deux élus (clé de contrôle de l'ISIN vérifiée par le build)
 'EDF':'FR0010242511','ARKEMA':'FR0010313833','CREDIT AGRICOLE SA':'FR0000045072','TELEPERFORMANCE':'FR0000051807','ASML HOLDING':'NL0010273215',
 'RUBIS':'FR0013269123','NOKIA':'FI0009000681','EDENRED':'FR0010908533','ESSILORLUXOTTICA':'FR0000121667','GENFIT':'FR0004163111','UBISOFT':'FR0000054470',
 'SAP':'DE0007164600','NOVARTIS':'CH0012005267','PROSUS':'NL0013654783','ELIS':'FR0012435121','VALEO':'FR0013176526','BUREAU VERITAS':'FR0006174348',
 'PUBLICIS GROUPE':'FR0000130577','SOITEC':'FR0013227113','WORLDLINE':'FR00140182K6','INDITEX':'ES0148396007','EIFFAGE':'FR0000130452',
 'MICROSOFT':'US5949181045','BIOMERIEUX':'FR0013280286','PUMA':'DE0006969603','REXEL':'FR0010451203','LEGRAND':'FR0010307819','UNIBAIL RODAMCO':'FR0013326246',
 'SIEMENS':'DE0007236101','ENI':'IT0003132476','EURAZEO':'FR0000121121','BIC':'FR0000120966','GETLINK':'FR0010533075','NEOEN':'FR0011675362','TRIGANO':'FR0005691656',
 'VALNEVA':'FR0004056851','AMAZON':'US0231351067','EUTELSAT COMMUNICATIONS':'FR0010221234','ERAMET':'FR0000131757','FNAC DARTY':'FR0011476928','DERICHEBOURG':'FR0000053381',
 'AB SCIENCE':'FR0010557264','APPLE':'US0378331005','NVIDIA':'US67066G1040','TESLA':'US88160R1014','SPIE':'FR0012757854','IPSEN':'FR0010259150','SODEXO':'FR0000121220',
 'NEXANS':'FR0000044448','COVIVIO':'FR0000064578','KLEPIERRE':'FR0000121964','GECINA':'FR0010040865','JCDECAUX':'FR0000077919','IMERYS':'FR0000120859','SEB':'FR0000121709',
 'REMY COINTREAU':'FR0000130395','SCOR':'FR0010411983','COFACE':'FR0010667147','BOLLORE':'FR0000039299','DASSAULT AVIATION':'FR0014004L86','ALTEN':'FR0000071946',
 'NEXITY':'FR0010112524','WENDEL':'FR0000121204','VERALLIA':'FR0013447729','FORVIA':'FR0000121147','ICADE':'FR0000035081','VICAT':'FR0000031775','TECHNIP ENERGIES':'NL0014559478','VEOLIA':'FR0000124141','PERNOD RICARD':'FR0000120693','AIR FRANCE KLM':'FR001400J770','LVMH':'FR0000121014',
 'BOUYGUES':'FR0000120503','ALSTOM':'FR0010220475','SCHNEIDER ELECTRIC':'FR0000121972','SAINT GOBAIN':'FR0000125007','VINCI':'FR0000125486','FDJ':'FR0013451333',
 'STMICROELECTRONICS':'NL0000226223','TOTALENERGIES':'FR0000120271','ACCOR':'FR0000120404','CARREFOUR':'FR0000120172','SOCIETE GENERALE':'FR0000130809',
 'ADP':'FR0010340141','VALLOUREC':'FR0013506730','EUROAPI':'FR0014008VX5','DASSAULT SYSTEMES':'FR0014003TT8','CAPGEMINI':'FR0000125338','KERING':'FR0000121485',
 'VIVENDI':'FR0000127771','HERMES':'FR0000052292','AMUNDI':'FR0004125920','TF1':'FR0000054900','ARCELORMITTAL':'LU1598757687','SOPRA STERIA':'FR0000050809','ALLIANZ':'DE0008404005'}
# SIREN des sociétés cotées françaises, vérifiés dans l'annuaire des entreprises (recherche-entreprises.api.gouv.fr) le 2026-10-08
SIREN={'TOTALENERGIES':'542051180','AIR LIQUIDE':'552096281','AXA':'572093920','ORANGE':'380129866','SANOFI':'395030844','BNP PARIBAS':'662042449',
 'SOCIETE GENERALE':'552120222','LVMH':'775670417','ENGIE':'542107651','DANONE':'552032534','L OREAL':'632012100','RENAULT':'441639465','SAFRAN':'562082909',
 'THALES':'552059024','VINCI':'552037806','KERING':'552075020','HERMES':'572076396','MICHELIN':'855200887','CAPGEMINI':'330703844','CARREFOUR':'652014051',
 'BOUYGUES':'572015246','SAINT GOBAIN':'542039532','SCHNEIDER ELECTRIC':'542048574','VEOLIA':'403210032','PERNOD RICARD':'582041943','ACCOR':'602036444',
 'ALSTOM':'389058447','VIVENDI':'343134763','ADP':'552016628','FDJ':'315065292','AMUNDI':'314222902','TF1':'326300159','DASSAULT SYSTEMES':'322306440',
 'SOPRA STERIA':'326820065','AIR FRANCE KLM':'552043002','VALLOUREC':'552142200','EUROAPI':'890974413',
 'CREDIT AGRICOLE SA':'784608416'}
def isin_ok(c):
    s=''.join(str(int(x,36)) for x in c[:-1]); t=0
    for i,ch in enumerate(reversed(s)):
        d=int(ch)*(2 if i%2==0 else 1); t+=d-9 if d>9 else d
    return re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}\d',c) and (10-t%10)%10==int(c[-1])
assert all(isin_ok(v) for v in ISIN.values()), [k for k,v in ISIN.items() if not isin_ok(v)]
BY_ISIN={}
def reindex():
    """À rappeler après une modification de ISIN (vérification Euronext)."""
    BY_ISIN.clear(); BY_ISIN.update({v:k for k,v in ISIN.items()})
reindex()
# formes juridiques en fin de nom, retirées avant le regroupement (« Arkema SA » = « Arkema »)
SUFFIX=re.compile(r'( (SA|SE|NV|AG|PLC|SCA|INC|CORP|CORPORATION|S A|N V))+$')
def skey(name):
    n=norm(name)
    # un ISIN connu écrit dans le libellé (« CREDIT AGRICOLE - FR0000045072 ») désigne la société
    for c in re.findall(r'\b[A-Z]{2}[A-Z0-9]{9}\d\b',n):
        if c in BY_ISIN: return BY_ISIN[c]
    if n in ALIAS: return ALIAS[n]
    if re.fullmatch(r'CREDIT AGRICOLE (S ?A|SA ACTIONS?|ACTIONS?)',n): return 'CREDIT AGRICOLE SA'
    m=SUFFIX.sub('',n)
    return ALIAS.get(m,m) if m else n
# « Crédit Agricole » sans précision : actions de Crédit Agricole SA (cotée) ou parts sociales d'une caisse régionale.
# Tranché ligne par ligne d'après le prix unitaire déclaré : l'action CASA a valu de 7 à 20 € depuis 2019, la part sociale
# d'une caisse locale vaut le plus souvent 1,50 €. Sinon la ligne reste « sans précision ».
def ca_split(sk,q,v,txt=''):
    if sk!='CREDIT AGRICOLE': return sk
    if re.search(r'PARTS? SOCIAL|SOCIETAIRE|CAISSE LOCALE',norm(txt)): return 'CREDIT AGRICOLE PARTS SOCIALES'
    try: u=float(v)/float(q)
    except (TypeError,ValueError,ZeroDivisionError): return sk
    if 7<=u<=20: return 'CREDIT AGRICOLE SA'
    if 0<u<=5: return 'CREDIT AGRICOLE PARTS SOCIALES'
    return sk
# Nature de la société, pour distinguer un portefeuille d'actions cotées de parts sociales bancaires ou d'une SCI
MUTU=re.compile(r'\b(CREDIT MUTUEL|CAISSE D EPARGNE|BANQUE POPULAIRE|CREDIT COOPERATIF|CASDEN|BRED|CRCAM|CRCA|CAISSES? (LOCALE|REGIONALE)S?|PARTS? SOCIALES?|SOCIETAIRES?|BPCE|ENERCOOP|SCIC|SCOP|COOPERATIVE|CMB)\b')
FONDS=re.compile(r'\b(PEA|PEE|PERCO|PERP|PER|COMPTES? TITRES?|CTO|SCPI|OPCVM|OPCI|FCP|FCPI|FCPR|FCPE|FIP|SICAV|ASSURANCE VIE|FONDS|ETF|TRACKER|PORTEFEUILLE|EPARGNE SALARIALE)\b')
NONCOT=re.compile(r'\b(SCI|SARL|SAS|SASU|EURL|SCEA|GFA|GAEC|SNC|SCP|SELARL|SELAS|SELAFA|SCM|EARL|GFR|GFV|SC|SPFPL|HOLDING|S A S|S A R L|SRL|S R L|GMBH|SARLU)\b')
def nature(k,names):
    if k in ISIN: return 'cotee'
    if k=='CREDIT AGRICOLE PARTS SOCIALES': return 'mutualiste'
    t=' '.join([k]+list(names))
    if MUTU.search(t): return 'mutualiste'
    if FONDS.search(t): return 'fonds'
    if NONCOT.search(t): return 'non_cotee'
    return ''
DISP={'CREDIT AGRICOLE':'Crédit Agricole (sans précision)','CREDIT AGRICOLE SA':'Crédit Agricole SA','CREDIT AGRICOLE PARTS SOCIALES':'Crédit Agricole (parts sociales)',
 'EDF':'EDF','ESSILORLUXOTTICA':'EssilorLuxottica','ASML HOLDING':'ASML','SAP':'SAP','BIOMERIEUX':'bioMérieux','ENI':'ENI','BIC':'BIC','SPIE':'SPIE','SEB':'SEB','SCOR':'SCOR',
 'JCDECAUX':'JCDecaux','UNIBAIL RODAMCO':'Unibail-Rodamco-Westfield','FNAC DARTY':'Fnac Darty','AB SCIENCE':'AB Science','REMY COINTREAU':'Rémy Cointreau','BOLLORE':'Bolloré',
 'KLEPIERRE':'Klépierre','EUTELSAT COMMUNICATIONS':'Eutelsat','NVIDIA':'Nvidia','PUBLICIS GROUPE':'Publicis','CREDIT MUTUEL':'Crédit Mutuel','CAISSE D EPARGNE':"Caisse d'Épargne",
 'L OREAL':"L'Oréal",'TOTALENERGIES':'TotalEnergies','AIR FRANCE KLM':'Air France-KLM','SAINT GOBAIN':'Saint-Gobain','SOCIETE GENERALE':'Société Générale','HERMES':'Hermès','DASSAULT SYSTEMES':'Dassault Systèmes','STMICROELECTRONICS':'STMicroelectronics','ARCELORMITTAL':'ArcelorMittal','EUROAPI':'EuroAPI','TF1':'TF1','FDJ':'FDJ','ADP':'ADP','LVMH':'LVMH','AXA':'AXA','BNP PARIBAS':'BNP Paribas'}
# Secteur des sociétés cotées, attribué à la main d'après l'activité principale du groupe ; sert à rapprocher une
# participation des commissions parlementaires compétentes (voir COMMISSION_SECTEURS).
SECTEURS={'energie':'Énergie','banque':'Banque, assurance, gestion d\'actifs','defense':'Défense, aéronautique, spatial','sante':'Santé, pharmacie',
 'numerique':'Numérique, télécoms, électronique','btp':'BTP, immobilier, concessions','transport':'Automobile, transport','conso':'Luxe, consommation, distribution',
 'agro':'Agroalimentaire, boissons','industrie':'Industrie, chimie, matériaux','medias':'Médias, publicité, jeux','environnement':'Eau, déchets, services à l\'environnement',
 'services':'Services aux entreprises'}
SECTEUR={
 'TOTALENERGIES':'energie','ENGIE':'energie','EDF':'energie','RUBIS':'energie','NEOEN':'energie','ENI':'energie','TECHNIP ENERGIES':'energie',
 'AXA':'banque','BNP PARIBAS':'banque','SOCIETE GENERALE':'banque','CREDIT AGRICOLE SA':'banque','AMUNDI':'banque','SCOR':'banque','COFACE':'banque','ALLIANZ':'banque','EURAZEO':'banque','WENDEL':'banque','EDENRED':'banque','WORLDLINE':'banque',
 'AIRBUS':'defense','SAFRAN':'defense','THALES':'defense','DASSAULT AVIATION':'defense','EUTELSAT COMMUNICATIONS':'defense',
 'SANOFI':'sante','GENFIT':'sante','NOVARTIS':'sante','BIOMERIEUX':'sante','VALNEVA':'sante','AB SCIENCE':'sante','IPSEN':'sante','EUROAPI':'sante','ESSILORLUXOTTICA':'sante',
 'ORANGE':'numerique','CAPGEMINI':'numerique','SOPRA STERIA':'numerique','DASSAULT SYSTEMES':'numerique','STMICROELECTRONICS':'numerique','SOITEC':'numerique','ASML HOLDING':'numerique','NOKIA':'numerique',
 'SAP':'numerique','MICROSOFT':'numerique','APPLE':'numerique','NVIDIA':'numerique','PROSUS':'numerique','ALTEN':'numerique','UBISOFT':'medias','TELEPERFORMANCE':'services',
 'VINCI':'btp','BOUYGUES':'btp','EIFFAGE':'btp','SAINT GOBAIN':'btp','UNIBAIL RODAMCO':'btp','COVIVIO':'btp','KLEPIERRE':'btp','GECINA':'btp','ICADE':'btp','NEXITY':'btp','VICAT':'btp','SPIE':'btp','ADP':'btp','GETLINK':'transport',
 'RENAULT':'transport','STELLANTIS':'transport','MICHELIN':'transport','VALEO':'transport','FORVIA':'transport','TESLA':'transport','AIR FRANCE KLM':'transport','ALSTOM':'transport','TRIGANO':'transport',
 'LVMH':'conso','KERING':'conso','HERMES':'conso','L OREAL':'conso','INDITEX':'conso','PUMA':'conso','CARREFOUR':'conso','FNAC DARTY':'conso','AMAZON':'conso','SEB':'conso','BIC':'conso','ACCOR':'conso','SODEXO':'services',
 'DANONE':'agro','PERNOD RICARD':'agro','REMY COINTREAU':'agro',
 'AIR LIQUIDE':'industrie','ARKEMA':'industrie','SCHNEIDER ELECTRIC':'industrie','LEGRAND':'industrie','SIEMENS':'industrie','NEXANS':'industrie','REXEL':'industrie','ERAMET':'industrie','IMERYS':'industrie',
 'ARCELORMITTAL':'industrie','VALLOUREC':'industrie','VERALLIA':'industrie','DERICHEBOURG':'environnement','VEOLIA':'environnement','ELIS':'services','BUREAU VERITAS':'services','BOLLORE':'medias',
 'PUBLICIS GROUPE':'medias','JCDECAUX':'medias','VIVENDI':'medias','TF1':'medias','FDJ':'medias'}

# Recherche des sociétés cotées citées dans un texte libre (amendements, décrets) : nom exact, mot entier, sans accents ni casse.
# noms seuls trop ambigus (mot courant, ville, nom de famille fréquent) : remplacés par des formes explicites
AMBIGUS = {'ORANGE', 'CARREFOUR', 'SAFRAN', 'LEGRAND', 'RUBIS', 'BIC', 'SEB', 'SAP', 'ENI', 'SCOR', 'ELIS', 'PUMA', 'SPIE', 'ALTEN',
           'VICAT', 'TOTAL', 'CREDIT AGRICOLE', 'APPLE', 'WENDEL', 'HERMES', 'ICADE'}
EXPLICITES = {'ORANGE': ['GROUPE ORANGE', 'ORANGE SA', 'OPERATEUR ORANGE'], 'CARREFOUR': ['GROUPE CARREFOUR', 'CARREFOUR SA'],
              'SAFRAN': ['GROUPE SAFRAN', 'SAFRAN SA'], 'APPLE': ['APPLE INC', 'SOCIETE APPLE', 'ENTREPRISE APPLE', 'GROUPE APPLE'],
              'HERMES': ['HERMES INTERNATIONAL', 'MAISON HERMES', 'GROUPE HERMES'], 'CREDIT AGRICOLE SA': ['CREDIT AGRICOLE SA', 'CREDIT AGRICOLE S A'],
              'TOTALENERGIES': ['TOTAL ENERGIES', 'TOTALENERGIES']}


def motifs():
    """(expression régulière sur un texte passé par norm(), {forme trouvée: clé de la société})."""
    m = {}
    for k in ISIN:
        noms = {k, norm(DISP.get(k, ''))} | {a for a, v in ALIAS.items() if v == k}
        noms = {n for n in noms if n and len(n) >= 3 and n not in AMBIGUS} | set(EXPLICITES.get(k, []))
        if k in AMBIGUS:
            noms -= {k}
        for n in noms:
            m[n] = k
    alt = '|'.join(sorted(map(re.escape, m), key=len, reverse=True))
    return re.compile(r'(?<![A-Z0-9])(' + alt + r')(?![A-Z0-9])'), m


