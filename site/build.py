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
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from societes import *
import societes
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
societes.reindex()
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
    for r in csv.DictReader(open(D+'raw/groupes.csv',encoding='utf-8')): GRP[(r['chambre'],norm(r['prenom']),norm(r['nom']),r['date_naissance'])]=(r['sigle'],r['groupe'],r)
# instantané sans date de naissance (sénateurs, quand data.senat.fr ne répond pas) : rapprochement sur le seul nom, s'il est unique
GRP_NOM=C.Counter(k[:3] for k in GRP)
def groupe(cat,k):
    return GRP.get((cat,)+k) or (GRP.get((cat,k[0],k[1],'')) if GRP_NOM[(cat,k[0],k[1])]==1 else None)
import croisements as X
# activités, fonctions et mandats déclarés (déclarations d'intérêts) : intitulé, organisme et dates seulement
act=C.defaultdict(list)
for r in (csv.DictReader(open(D+'out/activites.csv')) if os.path.exists(D+'out/activites.csv') else []): act[r['declaration_id']].append(r)
# dates de dépôt des déclarations d'intérêts de député (liste HATVP, y compris celles dont la publication est à venir)
DEPOTS=C.defaultdict(list)
for rows in liste.values():
    for r in rows:
        if r['type_mandat']=='depute' and r['type_document'] in ('di','dia') and r['date_depot']: DEPOTS[(norm(r['prenom']),norm(r['nom']))].append(r['date_depot'])
AN=X.assemblee(D)
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
    da=next((d for d in reversed(ds) if not d['type_declaration'].startswith('DSP') and act[d['declaration_id']]),None)
    ac={'d':da['date_depot'],'t':da['type_declaration'],'l':[{'r':r['rubrique'],'i':r['intitule'],'o':r['organisme'],'db':r['debut'],'fi':r['fin']} for r in act[da['declaration_id']]]} if da else None
    cats=p['cats']; cat='gouvernement' if 'gouvernement' in cats and last['categorie']=='gouvernement' else last['categorie']
    dcat=next(d for d in reversed(ds) if d['categorie']==cat); f=fn(dcat)
    elus.append({'id':eid,'p':p['prenom'].title(),'n':p['nom'].upper(),'cat':cat,'fn':f,'dep':departement(dcat,f,lrows),'cats':sorted(cats),'org':last['organe'] or ('Parlement européen' if cat=='depute_europeen' else ''),'mandat':last['mandat'],
      'page':page,'masked':masked,'h':holds,'cj':cj,**({'ac':ac} if ac else {}),**({'g':g[0],'gl':g[1]} if (g:=groupe(cat,k)) else {}),
      **({'com':g[2]['commission']} if g and g[2].get('commission') else {}),**({'comf':g[2]['fonction_commission']} if g and g[2].get('fonction_commission','Membre') not in ('','Membre') else {}),
      **({'dl':dl} if g and cat=='depute' and (dl:=X.delai_depot(g[2].get('debut_mandat',''),DEPOTS[(k[0],k[1])])) else {}),
      '_an':g[2].get('acteur','') if g and cat=='depute' else '',
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
def disp(k,v):
    if k in DISP: return DISP[k]
    if k in ISIN: return k.title()
    return v['names'].most_common(1)[0][0] if v['names'] else k
socs=[{'k':k,'id':slug(k) or 'x','name':disp(k,v),'isin':ISIN.get(k),'iv':ISIN.get(k) in VERIFIES,'siren':SIREN.get(k),'nat':nature(k,v['names']),'holders':v['holders']} for k,v in soc.items()]
LABELS={k:[n for n,c in v['names'].most_common()] for k,v in soc.items()}
# --- croisements (sources facultatives, voir site/croisements.py) ---
COURS=X.cours(D); LOB=X.lobbying(D); DECP=X.json_facultatif(D,'raw/decp.json',{}); DEPORTS=X.json_facultatif(D,'ref/deports.json',[])
SK={s_['k']:s_ for s_ in socs}
for s_ in socs:
    k=s_['k']
    if k in SECTEUR: s_['sec']=SECTEUR[k]
    if s_['isin'] in COURS and s_['iv']: s_['cours']={'c':COURS[s_['isin']][0],'d':COURS[s_['isin']][1]}
    if LOB.get(k): s_['lob']=LOB[k]
    if DECP.get(k): s_['decp']=DECP[k]
    dp=[d for d in DEPORTS if k in d.get('societes',[])]
    if dp: s_['dep']=[{'u':d['id'],'d':d['date'],'t':d['titre'],'m':d.get('ministere','')} for d in dp]
# valeur au dernier cours : nombre de titres déclaré × cours de clôture (sociétés cotées dont l'ISIN est vérifié)
for e in elus:
    for h in e['h']:
        c=(SK.get(h['s']) or {}).get('cours')
        try: q=float(h['q']) if h['q'] else None
        except ValueError: q=None
        if c and q and h['nl']=='participation': h['vc']=round(q*c['c'])
# commission permanente et secteur des sociétés détenues : lien à examiner, sans qualification
for e in elus:
    if not e.get('com'): continue
    secs=X.secteurs_commission(e['cat'],e['com'])
    lk=sorted({h['s'] for h in e['h'] if h['f']=='interets' and SECTEUR.get(h['s']) in secs})
    if lk: e['lk']=[{'s':x,'sec':SECTEUR[x]} for x in lk]
# amendements et votes des députés sur les sociétés qu'ils déclarent détenir
AMD={a['uid']:a for a in AN['amendements']}
for e in elus:
    acteur=e.pop('_an','')
    if not acteur: continue
    held={h['s'] for h in e['h'] if h['f']=='interets'}
    L=[]
    for a in AN['amendements']:
        r='auteur' if a['auteur']==acteur else ('cosignataire' if acteur in a['cosign'] else '')
        if r and held & set(a['societes']):
            L.append({'k':'amendement','u':a['uid'],'n':a['num'],'o':a['organe'],'tx':a['texte'],'ti':a['titre'],'ar':a['article'],'d':a['date'],'so':a['sort'],'r':r,'s':sorted(held&set(a['societes']))})
    for sc in AN['scrutins']:
        if acteur in sc['positions'] and held & set(sc['societes']):
            L.append({'k':'vote','n':sc['numero'],'ti':sc['titre'],'d':sc['date'],'so':sc['sort'],'p':sc['positions'][acteur],'s':sorted(held&set(sc['societes']))})
    if L: e['an']=sorted(L,key=lambda x:x['d'],reverse=True)
for e in elus: e.pop('_an',None)
NA=C.Counter(x for a in AN['amendements'] for x in a['societes']); NS=C.Counter(x for sc in AN['scrutins'] for x in sc['societes'])
for s_ in socs:
    if NA[s_['k']] or NS[s_['k']]: s_['an']={'a':NA[s_['k']],'v':NS[s_['k']]}
# déclarations que la HATVP signale comme non déposées (liste.csv, statut publié tel quel)
NONDEP=[{'p':r['prenom'].title(),'n':r['nom'].upper(),'q':r['qualite'],'t':r['type_document'].upper(),'u':'https://www.hatvp.fr'+r['url_dossier'] if r['url_dossier'] else ''}
        for rows in liste.values() for r in rows if r['statut_publication']=='Déclaration non déposée']
# mentions légales : renseignées par les variables du dépôt (voir docs/CONFORMITE.md)
HEBERGEUR_DEFAUT="GitHub, Inc. (service GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis."
legal={'editeur':os.environ.get('EDITEUR_NOM','').strip(),'contact':os.environ.get('EDITEUR_CONTACT','').strip(),
       'hebergeur':os.environ.get('HEBERGEUR','').strip() or HEBERGEUR_DEFAUT,
       # éditeur non professionnel anonyme (LCEN art. 6 III 2) : nom absent du site, identité connue de l'hébergeur
       'anonyme':os.environ.get('EDITEUR_ANONYME','').strip().lower() in ('1','oui','true')}
SITE_URL=(os.environ.get('SITE_URL','').strip() or 'https://trades-survey.github.io/trades-survey/').rstrip('/')+'/'
out={'built':BUILT,'legal':legal,'elus':sorted(elus,key=lambda e:(e['n'],e['p'])),'socs':socs,'mv':sorted(mv,key=lambda m:(m['dp'],m['e'],m['s']),reverse=True),'nd':NONDEP}
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
# vue d'ensemble (page « Chiffres ») : agrégats des dernières déclarations d'intérêts
def agg(L):
    return {'n':len({e['id'] for e,h in L}),'l':len(L),'v':sum(h['v'] or 0 for e,h in L),'vc':sum(h.get('vc') or 0 for e,h in L)}
IH=[(e,h) for e in out['elus'] for h in e['h'] if h['f']=='interets' and h['nl']=='participation']
LIST=[(e,h) for e,h in IH if (SK.get(h['s']) or {}).get('nat')=='cotee']
sect=C.defaultdict(list); grp=C.defaultdict(list); fon=C.defaultdict(list); val=C.defaultdict(list)
for e,h in LIST:
    if SECTEUR.get(h['s']): sect[SECTEUR[h['s']]].append((e,h))
    val[h['s']].append((e,h))
for e,h in IH:
    fon[e['fn']].append((e,h))
    if e.get('g'): grp[(e['cat'],e['g'])].append((e,h))
NG=C.Counter((e['cat'],e['g']) for e in out['elus'] if e.get('g'))
stats={'sect':sorted(({'sec':k,**agg(v)} for k,v in sect.items()),key=lambda x:-x['v']),
       'grp':sorted(({'c':k[0],'g':k[1],'m':NG[k],**agg(v)} for k,v in grp.items()),key=lambda x:(x['c'],-x['n'])),
       'fn':sorted(({'fn':k,'m':sum(1 for e in out['elus'] if e['fn']==k),**agg(v)} for k,v in fon.items()),key=lambda x:-x['n']),
       'top':[{'k':k,**agg(v)} for k,v in sorted(val.items(),key=lambda kv:-sum(h['v'] or 0 for e,h in kv[1]))[:20]],
       'lob':[{'k':s_['k'],'nh':len({h['e'] for h in s_['holders']}),'np':sum(o['np'] for o in s_['lob'])} for s_ in sorted(socs,key=lambda s_:-sum(o['np'] for o in s_.get('lob',[]))) if s_.get('lob') and s_['holders']][:20],
       'tot':{**agg(LIST),'cours':max((s_['cours']['d'] for s_ in socs if s_.get('cours')),default='')}}
idx={'built':BUILT,'legal':legal,
     'elus':[{'id':e['id'],'p':e['p'],'n':e['n'],'cat':e['cat'],'fn':e['fn'],'dep':e['dep'],'org':e['org'],'g':e.get('g',''),
              'nh':len(e['h']),'v':sum(h['v'] or 0 for h in e['h'])} for e in out['elus']],
     'socs':[{'k':s['k'],'id':s['id'],'name':s['name'],'isin':s['isin'],'siren':s['siren'],'nat':s['nat'],'nh':len({h['e'] for h in s['holders']}),'nm':nm[s['k']],**({'sec':s['sec']} if s.get('sec') else {})}
             for s in socs if s['holders'] or nm[s['k']]],
     'mv':out['mv'],'stats':stats,'nd':NONDEP}
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
