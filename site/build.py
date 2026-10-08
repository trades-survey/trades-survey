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
 'AEROPORTS DE PARIS':'ADP','GROUPE ADP':'ADP','FRANCAISE DES JEUX':'FDJ','LA FRANCAISE DES JEUX':'FDJ','FDJ UNITED':'FDJ','VINCI SA':'VINCI','KERING SA':'KERING','RENAULT SA':'RENAULT','SAFRAN SA':'SAFRAN'}
# ISIN rattachés à la main pour la maquette (à vérifier avant publication)
ISIN={'AIR LIQUIDE':'FR0000120073','AXA':'FR0000120628','ENGIE':'FR0010208488','ORANGE':'FR0000133308','SANOFI':'FR0000120578','MICHELIN':'FR001400AJ45',
 'AIRBUS':'NL0000235190','BNP PARIBAS':'FR0000131104','RENAULT':'FR0000131906','SAFRAN':'FR0000073272','STELLANTIS':'NL00150001Q9','DANONE':'FR0000120644',
 'THALES':'FR0000121329','L OREAL':'FR0000120321','VEOLIA':'FR0000124141','PERNOD RICARD':'FR0000120693','AIR FRANCE KLM':'FR001400J770','LVMH':'FR0000121014',
 'BOUYGUES':'FR0000120503','ALSTOM':'FR0010220475','SCHNEIDER ELECTRIC':'FR0000121972','SAINT GOBAIN':'FR0000125007','VINCI':'FR0000125486','FDJ':'FR0013451333',
 'STMICROELECTRONICS':'NL0000226223','TOTALENERGIES':'FR0000120271','ACCOR':'FR0000120404','CARREFOUR':'FR0000120172','SOCIETE GENERALE':'FR0000130809',
 'ADP':'FR0010340141','VALLOUREC':'FR0013506730','EUROAPI':'FR0014008VX5','DASSAULT SYSTEMES':'FR0014003TT8','CAPGEMINI':'FR0000125338','KERING':'FR0000121485',
 'VIVENDI':'FR0000127771','HERMES':'FR0000052292','AMUNDI':'FR0004125920','TF1':'FR0000054900','ARCELORMITTAL':'LU1598757687','SOPRA STERIA':'FR0000050809','ALLIANZ':'DE0008404005'}
def skey(name):
    n=norm(name); return ALIAS.get(n,n)
def slug(s): return re.sub(r'[^a-z0-9]+','-',norm(s).lower()).strip('-')
NEANT={'NEANT','','AUCUNE','AUCUN','NON','NA','N A'}
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
bydecl=C.defaultdict(list)
for r in parts: bydecl[r['declaration_id']].append(r)
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
            sk=skey(r['societe'])
            h={'s':sk,'n':r['societe'],'f':fam,'nl':r['nature_ligne'],'v':int(r['valeur_eur']) if r['valeur_eur'].isdigit() else None,
               'q':r['nb_parts'] or None,'c':r['capital_detenu_pct'] or None,'d':d['date_depot'],'t':d['type_declaration']}
            holds.append(h)
            if r['nature_ligne']=='participation' or fam=='patrimoine':
                soc[sk]['names'][r['societe']]+=1
                soc[sk]['holders'].append({'e':eid,'v':h['v'],'q':h['q'],'d':h['d'],'f':fam})
    cats=p['cats']; cat='gouvernement' if 'gouvernement' in cats and last['categorie']=='gouvernement' else last['categorie']
    elus.append({'id':eid,'p':p['prenom'].title(),'n':p['nom'].upper(),'cat':cat,'fn':fn(next(d for d in reversed(ds) if d['categorie']==cat)),'cats':sorted(cats),'org':last['organe'] or ('Parlement européen' if cat=='depute_europeen' else ''),'mandat':last['mandat'],
      'page':page,'masked':masked,'h':holds,
      'decls':[{'t':d['type_declaration'],'d':d['date_depot'],'m':d['modificative']=='oui','u':pdf(d)} for d in ds]})
# mouvements
mv=[]
for r in csv.DictReader(open(D+'out/mouvements.csv')):
    if r['mouvement']=='position_initiale' or norm(r['societe']) in NEANT: continue
    d=decl.get(r['declaration_apres']) or decl.get(r['declaration_avant'])
    if not d or d['categorie'] not in SCOPE: continue
    k=pkey(d)
    if k not in ids: continue
    sk=skey(r['societe'])
    def i(x): 
        try: return int(float(x))
        except: return None
    mv.append({'e':ids[k],'s':sk,'n':r['societe'],'f':r['famille'],'m':r['mouvement'],'da':r['date_avant'],'dp':r['date_apres'],
      'qa':i(r['nb_parts_avant']),'qp':i(r['nb_parts_apres']),'va':i(r['valeur_avant']),'vp':i(r['valeur_apres'])})
    soc[sk]['names'][r['societe']]+=0
DISP={'L OREAL':"L'Oréal",'TOTALENERGIES':'TotalEnergies','AIR FRANCE KLM':'Air France-KLM','SAINT GOBAIN':'Saint-Gobain','SOCIETE GENERALE':'Société Générale','HERMES':'Hermès','DASSAULT SYSTEMES':'Dassault Systèmes','STMICROELECTRONICS':'STMicroelectronics','ARCELORMITTAL':'ArcelorMittal','EUROAPI':'EuroAPI','TF1':'TF1','FDJ':'FDJ','ADP':'ADP','LVMH':'LVMH','AXA':'AXA','BNP PARIBAS':'BNP Paribas'}
def disp(k,v):
    if k in DISP: return DISP[k]
    if k in ISIN: return k.title()
    return v['names'].most_common(1)[0][0] if v['names'] else k
socs=[{'k':k,'id':slug(k) or 'x','name':disp(k,v),'isin':ISIN.get(k),'holders':v['holders']} for k,v in soc.items()]
# mentions légales : renseignées par les variables du dépôt (voir docs/CONFORMITE.md)
HEBERGEUR_DEFAUT="GitHub, Inc. (service GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis."
legal={'editeur':os.environ.get('EDITEUR_NOM','').strip(),'contact':os.environ.get('EDITEUR_CONTACT','').strip(),
       'hebergeur':os.environ.get('HEBERGEUR','').strip() or HEBERGEUR_DEFAUT,
       # éditeur non professionnel anonyme (LCEN art. 6 III 2) : nom absent du site, identité connue de l'hébergeur
       'anonyme':os.environ.get('EDITEUR_ANONYME','').strip().lower() in ('1','oui','true'),
       # lien de don (PayPal) affiché en bouton « Soutenir », seulement s'il est renseigné
       'soutenir':os.environ.get('SOUTENIR_URL','').strip()}
out={'built':BUILT,'legal':legal,'elus':sorted(elus,key=lambda e:(e['n'],e['p'])),'socs':socs,'mv':sorted(mv,key=lambda m:m['dp'],reverse=True)}
data=json.dumps(out,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
os.makedirs(os.path.join(ROOT,'public'),exist_ok=True)
import shutil
shutil.copytree(os.path.join(ROOT,'site','fonts'),os.path.join(ROOT,'public','fonts'),dirs_exist_ok=True)
tpl=open(os.path.join(ROOT,'site','template.html'),encoding='utf-8').read()
head='<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
open(os.path.join(ROOT,'public','index.html'),'w',encoding='utf-8').write(head+tpl.replace('__DATA__',data).replace('<header class="top">','</head>\n<body>\n<header class="top">',1)+'\n</body>\n</html>\n')
print(len(elus),C.Counter(e['cat'] for e in elus),len(socs),len(mv),C.Counter(m['m'] for m in mv),sum(len(e['h']) for e in elus))
print(sum(1 for e in elus if e['page']), sum(1 for e in elus for d in e['decls'] if d['u']), sum(len(e['decls']) for e in elus))
top=sorted(socs,key=lambda s:-len(s['holders']))[:25]; print([(s['name'],len(s['holders']),s['isin']) for s in top])
