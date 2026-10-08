import csv, json, re, sys, unicodedata, collections as C
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=os.path.join(ROOT,'data')+'/'
BUILT=sys.argv[1] if len(sys.argv)>1 else __import__('datetime').date.today().isoformat()
SCOPE={'depute','senateur','gouvernement','depute_europeen','elu_local'}
FN={'depute':'Député','senateur':'Sénateur','gouvernement':'Gouvernement','depute_europeen':'Député européen'}
LOCAL={'Elu départemental':'Élu départemental','Elu régional':'Élu régional','Collectivité à statut particulier':'Élu de collectivité à statut particulier','Maire ou adjoint municipal':'Maire ou adjoint'}
def fn(d):
    if d['categorie']!='elu_local': return FN[d['categorie']]
    t=d['type_mandat']
    return LOCAL.get(t,'Élu intercommunal' if 'EPCI' in t else 'Élu local')
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
# Département de l'élu, d'après le mandat retenu (code INSEE : 01-95, 2A, 2B, 971-988 ; 099 = Français de l'étranger)
DEP_RE=re.compile(r'\(\s*(0[1-9]|[1-8]\d|9[0-5]|2[AB]|9[78]\d|099)\s*\)')
# type_mandat de liste.csv correspondant à chaque fonction (les régions, le gouvernement et le Parlement européen n'ont pas de département)
LISTE_MANDAT={'depute':'depute','senateur':'senateur','Élu départemental':'departement','Maire ou adjoint':'commune','Élu intercommunal':'epci','Élu de collectivité à statut particulier':'ctsp'}
# collectivités sans code dans le libellé (la Corse et l'Alsace couvrent deux départements : pas de code)
ORG_DEP={'HORS DE FRANCE':'099','POLYNESIE':'987','NOUVELLE CALEDONIE':'988','GUYANE':'973','MARTINIQUE':'972','SAINT MARTIN':'978','SAINT BARTHELEMY':'977','SAINT PIERRE ET MIQUELON':'975','WALLIS':'986','MAYOTTE':'976'}
def departement(d,f,lrows):
    if f in ('Élu régional','Gouvernement','Député européen'): return ''
    m=DEP_RE.search(d['organe'] or '')
    if m: return m.group(1)
    o=norm(d['organe'])
    for k,v in ORG_DEP.items():
        if k in o: return v
    tm=LISTE_MANDAT.get(d['categorie'],LISTE_MANDAT.get(f))
    # 997 et 998 : les deux séries de sénateurs des Français de l'étranger
    deps=C.Counter('099' if r['departement'] in ('997','998') else r['departement'] for r in lrows if r['type_mandat']==tm and r['departement'])
    return deps.most_common(1)[0][0] if len(deps)==1 else ''
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
# Contrôle des ISIN avec la liste officielle d'Euronext (scripts/fetch_euronext.py), quand elle a pu être téléchargée :
# un ISIN présent sur Euronext sous un autre nom est retiré ; un ISIN absent (société étrangère, radiée) est gardé sans être marqué vérifié.
VERIFIES=set()
if os.path.exists(D+'raw/euronext.csv'):
    EUR={r['isin']:r['name'] for r in csv.DictReader(open(D+'raw/euronext.csv',encoding='utf-8'))}
    VIDES={'SA','SE','NV','AG','PLC','SCA','GROUP','GROUPE','HOLDING','HOLDINGS','CIE','COMPAGNIE','DE','DES','DU','LA','LE','LES','ET','INTERNATIONAL','INTL'}
    def meme(k,nom):
        e=norm(nom); et=set(e.split())-VIDES; ec=e.replace(' ','')
        for c in [k]+[a for a,v in ALIAS.items() if v==k]:
            cc=c.replace(' ','')
            if set(c.split())-VIDES & et or cc==ec or (len(cc)>=4 and (cc in ec or ec in cc)): return True
        return False
    for k,c in list(ISIN.items()):
        if c not in EUR: continue
        if meme(k,EUR[c]): VERIFIES.add(c)
        else: print(f"::warning::ISIN {c} retiré de {k} : Euronext le donne pour {EUR[c]}"); del ISIN[k]
    print(f'ISIN vérifiés sur Euronext : {len(VERIFIES)}/{len(ISIN)}')
BY_ISIN={v:k for k,v in ISIN.items()}
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
def slug(s): return re.sub(r'[^a-z0-9]+','-',norm(s).lower()).strip('-')
NEANT={'NEANT','','AUCUNE','AUCUN','NON','NA','N A','0','X'}
decl={r['declaration_id']:r for r in csv.DictReader(open(D+'out/declarations.csv'))}
def pkey(r): return (norm(r['prenom']),norm(r['nom']),r['date_naissance'])
# liens HATVP
liste=C.defaultdict(list)
for r in csv.DictReader(open(D+'raw/liste.csv'),delimiter=';'):
    liste[(norm(r['prenom']),norm(r['nom']))].append(r)
persons={}
for d in decl.values():
    if d['categorie'] not in SCOPE: continue
    k=pkey(d); p=persons.setdefault(k,{'prenom':d['prenom'],'nom':d['nom'],'cats':set(),'decls':[]})
    p['cats'].add(d['categorie']); p['decls'].append(d)
parts=[r for r in csv.DictReader(open(D+'out/participations.csv')) if r['categorie'] in SCOPE]
# garde-fou juridique : aucune DSP hors gouvernement
assert not [r for r in parts if r['type_declaration'].startswith('DSP') and r['categorie']!='gouvernement']
# activité professionnelle du conjoint (déclarations d'intérêts) : activité et employeur, jamais le nom
conj=C.defaultdict(list)
for r in (csv.DictReader(open(D+'out/conjoints.csv')) if os.path.exists(D+'out/conjoints.csv') else []): conj[r['declaration_id']].append(r)
bydecl=C.defaultdict(list)
for r in parts: bydecl[r['declaration_id']].append(r)
# groupe politique des députés et sénateurs en exercice (scripts/fetch_groupes.py), rapproché sur le nom et la date de naissance
GRP={}
if os.path.exists(D+'raw/groupes.csv'):
    for r in csv.DictReader(open(D+'raw/groupes.csv',encoding='utf-8')): GRP[(r['chambre'],norm(r['prenom']),norm(r['nom']),r['date_naissance'])]=(r['sigle'],r['groupe'])
# instantané sans date de naissance (sénateurs, quand data.senat.fr ne répond pas) : rapprochement sur le seul nom, s'il est unique
GRP_NOM=C.Counter(k[:3] for k in GRP)
def groupe(cat,k):
    return GRP.get((cat,)+k) or (GRP.get((cat,k[0],k[1],'')) if GRP_NOM[(cat,k[0],k[1])]==1 else None)
elus=[]; soc=C.defaultdict(lambda:{'names':C.Counter(),'holders':[]}); ids={}; taken=set()
for k,p in sorted(persons.items()):
    ds=sorted(p['decls'],key=lambda d:d['date_depot'])
    last=ds[-1]
    eid=slug(p['prenom']+' '+p['nom']); 
    # homonymes : suffixe numérique (jamais l'année de naissance, donnée non publiée par le site)
    base,n=eid,1
    while eid in taken: n+=1; eid=f'{base}-{n}'
    taken.add(eid); ids[k]=eid
    lrows=liste.get((k[0],k[1]),[])
    page=next((('https://www.hatvp.fr'+r['url_dossier']) for r in lrows if r['url_dossier']),'')
    def pdf(d):
        for r in lrows:
            if r['date_depot']==d['date_depot'] and r['nom_fichier'] and r['type_document'].upper()==d['type_declaration']:
                return 'https://www.hatvp.fr/livraison/dossiers/'+r['nom_fichier']
        return ''
    holds=[]; masked=0
    for fam,pred in (('interets',lambda d:not d['type_declaration'].startswith('DSP')),('patrimoine',lambda d:d['type_declaration'].startswith('DSP'))):
        cand=[d for d in ds if pred(d) and d['section_presente']=='oui']
        if not cand: continue
        d=cand[-1]
        for r in bydecl[d['declaration_id']]:
            if r['societe_masquee']=='oui': masked+=1; continue
            if norm(r['societe']) in NEANT: continue
            sk=ca_split(skey(r['societe']),r['nb_parts'],r['valeur_eur'],r['societe']+' '+r['commentaire'])
            h={'s':sk,'n':r['societe'],'f':fam,'nl':r['nature_ligne'],'v':int(r['valeur_eur']) if r['valeur_eur'].isdigit() else None,
               'q':r['nb_parts'] or None,'c':r['capital_detenu_pct'] or None,'d':d['date_depot'],'t':d['type_declaration']}
            holds.append(h)
            if r['nature_ligne']=='participation' or fam=='patrimoine':
                soc[sk]['names'][r['societe']]+=1
                soc[sk]['holders'].append({'e':eid,'v':h['v'],'q':h['q'],'d':h['d'],'f':fam})
    dc=next((d for d in reversed(ds) if not d['type_declaration'].startswith('DSP') and conj[d['declaration_id']]),None)
    cj={'d':dc['date_depot'],'t':dc['type_declaration'],'l':[{'a':r['activite'],'e':r['employeur']} for r in conj[dc['declaration_id']] if r['neant']=='non']} if dc else None
    cats=p['cats']; cat='gouvernement' if 'gouvernement' in cats and last['categorie']=='gouvernement' else last['categorie']
    dcat=next(d for d in reversed(ds) if d['categorie']==cat); f=fn(dcat)
    elus.append({'id':eid,'p':p['prenom'].title(),'n':p['nom'].upper(),'cat':cat,'fn':f,'dep':departement(dcat,f,lrows),'cats':sorted(cats),'org':last['organe'] or ('Parlement européen' if cat=='depute_europeen' else ''),'mandat':last['mandat'],
      'page':page,'masked':masked,'h':holds,'cj':cj,**({'g':g[0],'gl':g[1]} if (g:=groupe(cat,k)) else {}),
      'decls':[{'t':d['type_declaration'],'d':d['date_depot'],'m':d['modificative']=='oui','u':pdf(d)} for d in ds]})
# mouvements
mv=[]
for r in csv.DictReader(open(D+'out/mouvements.csv')):
    if r['mouvement']=='position_initiale' or norm(r['societe']) in NEANT: continue
    d=decl.get(r['declaration_apres']) or decl.get(r['declaration_avant'])
    if not d or d['categorie'] not in SCOPE: continue
    k=pkey(d)
    if k not in ids: continue
    def i(x): 
        try: return int(float(x))
        except: return None
    qa,qp,va,vp=i(r['nb_parts_avant']),i(r['nb_parts_apres']),i(r['valeur_avant']),i(r['valeur_apres'])
    sk=ca_split(skey(r['societe']),qp or qa,vp or va)
    # même nombre de titres avant et après : seul le cours a changé, ce n'est ni un achat ni une vente
    m=r['mouvement']
    if m in ('hausse','baisse') and qa is not None and qa==qp: m='valeur'
    mv.append({'e':ids[k],'s':sk,'n':r['societe'],'f':r['famille'],'m':m,'da':r['date_avant'],'dp':r['date_apres'],'qa':qa,'qp':qp,'va':va,'vp':vp})
    soc[sk]['names'][r['societe']]+=0
DISP={'CREDIT AGRICOLE':'Crédit Agricole (sans précision)','CREDIT AGRICOLE SA':'Crédit Agricole SA','CREDIT AGRICOLE PARTS SOCIALES':'Crédit Agricole (parts sociales)',
 'EDF':'EDF','ESSILORLUXOTTICA':'EssilorLuxottica','ASML HOLDING':'ASML','SAP':'SAP','BIOMERIEUX':'bioMérieux','ENI':'ENI','BIC':'BIC','SPIE':'SPIE','SEB':'SEB','SCOR':'SCOR',
 'JCDECAUX':'JCDecaux','UNIBAIL RODAMCO':'Unibail-Rodamco-Westfield','FNAC DARTY':'Fnac Darty','AB SCIENCE':'AB Science','REMY COINTREAU':'Rémy Cointreau','BOLLORE':'Bolloré',
 'KLEPIERRE':'Klépierre','EUTELSAT COMMUNICATIONS':'Eutelsat','NVIDIA':'Nvidia','PUBLICIS GROUPE':'Publicis','CREDIT MUTUEL':'Crédit Mutuel','CAISSE D EPARGNE':"Caisse d'Épargne",
 'L OREAL':"L'Oréal",'TOTALENERGIES':'TotalEnergies','AIR FRANCE KLM':'Air France-KLM','SAINT GOBAIN':'Saint-Gobain','SOCIETE GENERALE':'Société Générale','HERMES':'Hermès','DASSAULT SYSTEMES':'Dassault Systèmes','STMICROELECTRONICS':'STMicroelectronics','ARCELORMITTAL':'ArcelorMittal','EUROAPI':'EuroAPI','TF1':'TF1','FDJ':'FDJ','ADP':'ADP','LVMH':'LVMH','AXA':'AXA','BNP PARIBAS':'BNP Paribas'}
def disp(k,v):
    if k in DISP: return DISP[k]
    if k in ISIN: return k.title()
    return v['names'].most_common(1)[0][0] if v['names'] else k
socs=[{'k':k,'id':slug(k) or 'x','name':disp(k,v),'isin':ISIN.get(k),'iv':ISIN.get(k) in VERIFIES,'siren':SIREN.get(k),'nat':nature(k,v['names']),'holders':v['holders']} for k,v in soc.items()]
LABELS={k:[n for n,c in v['names'].most_common()] for k,v in soc.items()}
# mentions légales : renseignées par les variables du dépôt (voir docs/CONFORMITE.md)
HEBERGEUR_DEFAUT="GitHub, Inc. (service GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis."
legal={'editeur':os.environ.get('EDITEUR_NOM','').strip(),'contact':os.environ.get('EDITEUR_CONTACT','').strip(),
       'hebergeur':os.environ.get('HEBERGEUR','').strip() or HEBERGEUR_DEFAUT,
       # éditeur non professionnel anonyme (LCEN art. 6 III 2) : nom absent du site, identité connue de l'hébergeur
       'anonyme':os.environ.get('EDITEUR_ANONYME','').strip().lower() in ('1','oui','true')}
SITE_URL=(os.environ.get('SITE_URL','').strip() or 'https://trades-survey.github.io/trades-survey/').rstrip('/')+'/'
out={'built':BUILT,'legal':legal,'elus':sorted(elus,key=lambda e:(e['n'],e['p'])),'socs':socs,'mv':sorted(mv,key=lambda m:(m['dp'],m['e'],m['s']),reverse=True)}
PUB=os.path.join(ROOT,'public')
import shutil
for d in ('elus','societes','donnees'): shutil.rmtree(os.path.join(PUB,d),ignore_errors=True); os.makedirs(os.path.join(PUB,d))
shutil.copytree(os.path.join(ROOT,'site','fonts'),os.path.join(PUB,'fonts'),dirs_exist_ok=True)
def write(rel,txt):
    with open(os.path.join(PUB,rel),'w',encoding='utf-8',newline='') as f: f.write(txt)
tpl=open(os.path.join(ROOT,'site','template.html'),encoding='utf-8').read()
# feuille de style commune à l'accueil et aux fiches, mise en cache d'une page à l'autre
css=re.search(r'<style>(.*?)</style>',tpl,re.S)
write('style.css',css.group(1).strip()+'\n')
tpl=tpl[:css.start()]+'<link rel="stylesheet" href="style.css">'+tpl[css.end():]
HEAD='<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
# 1. données complètes (contrôlées par site/check_conformite.py et téléchargeables)
write('donnees/registre.json',json.dumps(out,ensure_ascii=False,separators=(',',':')))
# 2. accueil : seulement ce qu'il faut aux listes, aux filtres et à la recherche ; le détail est dans les fiches statiques
nm=C.Counter(m['s'] for m in mv)
idx={'built':BUILT,'legal':legal,
     'elus':[{'id':e['id'],'p':e['p'],'n':e['n'],'cat':e['cat'],'fn':e['fn'],'dep':e['dep'],'org':e['org'],'g':e.get('g',''),
              'nh':len(e['h']),'v':sum(h['v'] or 0 for h in e['h'])} for e in out['elus']],
     'socs':[{'k':s['k'],'id':s['id'],'name':s['name'],'isin':s['isin'],'siren':s['siren'],'nat':s['nat'],'nh':len({h['e'] for h in s['holders']}),'nm':nm[s['k']]}
             for s in socs if s['holders'] or nm[s['k']]],
     'mv':out['mv']}
data=json.dumps(idx,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
write('index.html',HEAD+tpl.replace('__DATA__',data).replace('<header class="top">','</head>\n<body>\n<header class="top">',1)+'\n</body>\n</html>\n')
# 3. une page statique par élu et par société
sys.path.insert(0,os.path.join(ROOT,'site'))
from pages import Site, NAT, MV as MVL, date as pdate
site=Site(tpl,out)
for e in out['elus']: write(f"elus/{e['id']}.html",site.elu(e))
for s_ in socs: write(f"societes/{s_['id']}.html",site.societe(s_,LABELS[s_['k']]))
# 4. exports CSV (mêmes données que le site, sans date de naissance ni identifiant HATVP)
def csv_out(rel,head,rows):
    import io
    b=io.StringIO(); w=csv.writer(b); w.writerow(head); w.writerows(rows); write(rel,'﻿'+b.getvalue())
EN={e['id']:e for e in out['elus']}; SN={s_['k']:s_ for s_ in socs}
csv_out('donnees/elus.csv',['id','prenom','nom','fonction','circonscription_ou_ministere','departement','groupe','groupe_libelle','lignes_declarees','valeur_declaree_eur','fiche_hatvp','url'],
  [[e['id'],e['p'],e['n'],e['fn'],e['org'],e['dep'],e.get('g',''),e.get('gl',''),len(e['h']),sum(h['v'] or 0 for h in e['h']),e['page'],f"{SITE_URL}elus/{e['id']}.html"] for e in out['elus']])
csv_out('donnees/participations.csv',['elu_id','prenom','nom','fonction','societe','libelle_declare','isin','nature','famille','nombre_titres','capital_pct','valeur_declaree_eur','type_declaration','date_declaration'],
  [[e['id'],e['p'],e['n'],e['fn'],SN[h['s']]['name'] if h['s'] in SN else '',h['n'],(SN.get(h['s']) or {}).get('isin') or '',NAT[(SN.get(h['s']) or {}).get('nat','')],h['f'],h['q'] or '',h['c'] or '',
    '' if h['v'] is None else h['v'],h['t'],h['d']] for e in out['elus'] for h in e['h']])
csv_out('donnees/mouvements.csv',['elu_id','prenom','nom','societe','libelle_declare','isin','ecart','date_declaration_avant','date_declaration_apres','titres_avant','titres_apres','valeur_avant_eur','valeur_apres_eur'],
  [[m['e'],EN[m['e']]['p'],EN[m['e']]['n'],SN[m['s']]['name'] if m['s'] in SN else m['n'],m['n'],(SN.get(m['s']) or {}).get('isin') or '',MVL[m['m']],m['da'],m['dp'],
    '' if m['qa'] is None else m['qa'],'' if m['qp'] is None else m['qp'],'' if m['va'] is None else m['va'],'' if m['vp'] is None else m['vp']] for m in out['mv']])
# 5. flux RSS des derniers mouvements (hors simples variations de cours), sitemap et robots.txt
from xml.sax.saxutils import escape as xe
from email.utils import format_datetime
import datetime as DT
def rfc(d): return format_datetime(DT.datetime.fromisoformat(d+'T12:00:00+00:00'))
items=[]
for m in [m for m in out['mv'] if m['m']!='valeur'][:100]:
    e=EN[m['e']]; s_=SN.get(m['s']); sn=s_['name'] if s_ else m['n']
    t=f"{e['p']} {e['n']} ({e['fn']}) : {MVL[m['m']].lower()} {sn}"
    d=(f"Entre la déclaration du {pdate(m['da'])} et celle du {pdate(m['dp'])} : titres {m['qa'] if m['qa'] is not None else '—'} → {m['qp'] if m['qp'] is not None else '—'}, "
       f"valeur déclarée {m['va'] if m['va'] is not None else '—'} → {m['vp'] if m['vp'] is not None else '—'} €. Écart entre deux déclarations à la HATVP, pas une transaction datée.")
    items.append(f"<item><title>{xe(t)}</title><link>{SITE_URL}elus/{e['id']}.html</link><guid isPermaLink=\"false\">{xe('|'.join([m['e'],m['s'],m['m'],m['da'] or '',m['dp']]))}</guid>"
                 f"<pubDate>{rfc(m['dp'])}</pubDate><description>{xe(d)}</description></item>")
write('flux.xml','<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel><title>Registre des élus actionnaires : derniers mouvements</title>'
      f'<link>{SITE_URL}</link><description>Écarts entre deux déclarations successives des élus à la HATVP (hors simples variations de cours).</description><language>fr</language>'
      f'<lastBuildDate>{rfc(BUILT)}</lastBuildDate>\n'+'\n'.join(items)+'\n</channel></rss>\n')
urls=[SITE_URL]+[f"{SITE_URL}elus/{e['id']}.html" for e in out['elus']]+[f"{SITE_URL}societes/{s_['id']}.html" for s_ in socs]
write('sitemap.xml','<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join(f'<url><loc>{xe(u)}</loc><lastmod>{BUILT}</lastmod></url>' for u in urls)+'\n</urlset>\n')
write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n')
print(len(elus),C.Counter(e['cat'] for e in elus),len(socs),len(mv),C.Counter(m['m'] for m in mv),sum(len(e['h']) for e in elus))
print('groupes',sum(1 for e in elus if e.get('g')),'natures',C.Counter(s_['nat'] for s_ in socs if s_['holders']))
print('index',os.path.getsize(os.path.join(PUB,'index.html')),'octets')
top=sorted(socs,key=lambda s:-len({h['e'] for h in s['holders']}))[:25]; print([(s['name'],len({h['e'] for h in s['holders']}),s['nat']) for s in top])
