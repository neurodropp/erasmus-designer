#!/usr/bin/env python3
"""Reviewed 2026 action taxonomy from the supplied Programme Guide TOC.

Ranges are PDF page numbers, one-based. Shared ranges deliberately do not
imply identical eligibility or award rules for accredited/non-accredited routes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT/'config/actions.json').exists() or (ROOT/'config/sources.json').exists():
    raise SystemExit('Catalog already exists; edit reviewed metadata explicitly. Do not overwrite sources or history.')
actions = []
def add(code, title, sectors, pages, expert=None, slug=None, agency=None, note=''):
    actions.append(dict(code=code, title=title, sectors=sectors.split(','),
                        programme_pages=pages, expert_pages=expert, web_slug=slug,
                        agency=agency, note=note))

add('KA131','Higher education mobility - internal policy funds','HED',[42,72],None,'higher-education-mobility','INDIRE','The expert guide specifies KA171 here; do not apply its assessment grid to KA131.')
add('KA171','Higher education mobility - external policy funds','HED',[42,72],[16,17],'higher-education-mobility','INDIRE')
for sector,title,pages,slug in [('VET','vocational education and training',[82,102],'mobility-vet'),('SCH','school education',[103,122],'mobility-school'),('ADU','adult education',[123,142],'mobility-adult')]:
    add('KA120-'+sector,'Erasmus accreditation - '+title,sector,[73,81],None,'erasmus-accreditation-vet-school-adult', 'INAPP' if sector=='VET' else 'INDIRE','Use the Erasmus Plan assessment grid in the Programme Guide; the attached expert guide contains no specific grid.')
    add('KA121-'+sector,'Accredited mobility - '+title,sector,pages,None,slug,'INAPP' if sector=='VET' else 'INDIRE','Accreditation is required; do not apply the KA122 assessment grid to the KA121 budget request.')
    add('KA122-'+sector,'Short-term mobility - '+title,sector,pages,[18,20],slug,'INAPP' if sector=='VET' else 'INDIRE')
add('KA150','Erasmus accreditation in the youth field','YOU',[144,148],None,'erasmus-accreditation-youth','AIG')
add('KA151','Mobility for accredited youth organisations','YOU',[149,151],None,'mobility-accredited-youth','AIG')
add('KA152','Youth exchanges','YOU',[152,164],[21,25],'youth-exchanges','AIG')
add('KA153','Mobility of youth workers','YOU',[165,179],[26,31],'mobility-youth-workers','AIG')
add('KA154','Youth participation activities','YOU',[180,195],[32,37],'youth-participation','AIG')
add('KA155','DiscoverEU inclusion action','YOU',[196,205],[38,41],'discovereu','AIG')
add('KA182','Staff mobility in the field of sport','SPO',[206,215],[42,44],'mobility-sport','AIG')
add('VIRTUAL-EXCHANGES','Erasmus+ virtual exchanges','HED,YOU',[216,223],None,'virtual-exchanges','EACEA')
for sector in ('SCH','ADU','VET','HED','YOU','SPO'):
    add('KA220-'+sector,'Cooperation partnerships - '+sector,sector,[235,243],[45,57] if sector!='SPO' else None,'cooperation-partnerships','EACEA' if sector=='SPO' else ('INAPP' if sector=='VET' else ('AIG' if sector=='YOU' else 'INDIRE')),'European NGOs in education, training or youth may fall under EACEA calls; verify the applicant type. The attached expert guide covers National Agency actions, not the EACEA Sport call.')
for sector in ('SCH','ADU','VET','YOU','SPO'):
    add('KA210-'+sector,'Small-scale partnerships - '+sector,sector,[244,250],[58,64] if sector!='SPO' else None,'small-scale-partnerships','EACEA' if sector=='SPO' else ('INAPP' if sector=='VET' else ('AIG' if sector=='YOU' else 'INDIRE')),'KA210 is not available in the HED field. Do not apply the National Agency expert guide to the EACEA Sport call.')
add('KA240','European partnerships for school development','SCH',[251,257],[65,71],'school-development-partnerships','INDIRE','New action type for 2026; verify national eligibility requirements for coordinators and partners.')
add('COVE','Centres of Vocational Excellence','VET',[259,273],None,'centres-vocational-excellence','EACEA')
add('ERASMUS-MUNDUS','Erasmus Mundus: joint masters and design measures','HED',[274,288],None,'erasmus-mundus','EACEA','Treat EMJM and EMDM separately in the application and use the relevant assessment grid.')
add('ALLIANCES-INNOVATION','Alliances for Innovation','HED,VET',[290,313],None,'alliances-innovation','EACEA','Select the call lot before extracting eligibility requirements and award criteria.')
add('CBHE','Capacity building in higher education','HED',[314,331],None,'capacity-building-higher-education','EACEA','Select the call strand and region.')
add('CBVET','Capacity building in vocational education and training','VET',[332,342],None,'capacity-building-vet','EACEA')
add('CBYOUTH','Capacity building in the field of youth','YOU',[343,351],None,'capacity-building-youth','EACEA')
add('CBSPORT','Capacity building in the field of sport','SPO',[352,357],None,'capacity-building-sport','EACEA')
add('SPORT-EVENTS','European not-for-profit sport events','SPO',[358,363],None,'not-for-profit-sport-events','EACEA')
add('EUROPEAN-YOUTH-TOGETHER','European Youth Together','YOU',[366,374],None,'european-youth-together','EACEA')
add('JEAN-MONNET-HED','Jean Monnet in higher education','HED',[376,391],None,'jean-monnet-higher-education','EACEA','Select Modules, Chairs or Centres of Excellence.')
add('JEAN-MONNET-SCH-VET','Jean Monnet in other fields of education and training','SCH,VET',[392,402],None,'jean-monnet-other-fields','EACEA','Select teacher training or Learning EU Initiatives.')
add('JEAN-MONNET-NETWORKS','Jean Monnet - policy debate and networks','HED,SCH,VET',[403,412],None,'jean-monnet-policy-debate','EACEA')
(ROOT/'config/actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2)+'\n')

sources = [
dict(id='programme-2026',title='Erasmus+ Programme Guide 2026 EN v1',path='raw/pdf/programme-guide-2026-en.pdf',kind='programme-guide',language='en',year=2026,version='1 - 12/11/2025',authority='European Commission',url='https://erasmus-plus.ec.europa.eu/sites/default/files/2025-11/programme-guide-2026_en.pdf',sectors=['ALL'],actions=['ALL']),
dict(id='expert-2026',title='Guide for Experts on Quality Assessment 2026 v1',path='raw/pdf/expert-guide-2026-v1.pdf',kind='expert-guide',language='en',year=2026,version='1 - 22/12/2025',authority='European Commission',url='https://erasmus-plus.ec.europa.eu/resources-and-tools/documents-and-guidelines',sectors=['ALL'],actions=['ALL'],scope_note='Covers actions managed by National Agencies; the URL is for discovery, and the attached PDF is the exact source.')]
remote = [
('indire-sch-adu-2026','Disposizioni nazionali INDIRE SCH ADU 2026','https://www.erasmusplus.it/wp-content/uploads/2026/02/Erasmus-Disposizioni-nazionali-SCH_ADU-2026.pdf','national-provisions','SCH,ADU','ALL','INDIRE'),
('indire-hed-2026','Disposizioni nazionali INDIRE HE 2026 v2 maggio','https://www.erasmusplus.it/wp-content/uploads/2026/05/Erasmus-Disposizioni-nazionali-HE_2026_v-2.pdf','national-provisions','HED','ALL','INDIRE'),
('inapp-priorities-2026','Priorità nazionali Erasmus VET 2026 - 24/02/2026','https://www.erasmusplus.it/wp-content/uploads/2026/02/Priorita_nazionali_Erasmus_VET_2026_24_02_26.pdf','national-priorities','VET','KA210,KA220','INAPP'),
('inapp-faq-ka2-2026','FAQ INAPP KA2 2026','https://www.erasmusplus.it/wp-content/uploads/2026/02/FAQ-KA2-2026-03_02_2026-DEF.pdf','national-guidance','VET','KA210,KA220','INAPP'),
('aig-priorities-2026','AIG - priorità nazionali KA220 Gioventù 2026','https://agenziagioventu.gov.it/priorita-europee-nel-contesto-nazionale-rilevanti-nel-processo-di-valutazione-dei-partenariati-di-cooperazione-ka220/','national-priorities','YOU','KA220','AIG'),
('indire-inclusion-2026','Strategia inclusione e diversità INDIRE marzo 2026','https://www.erasmusplus.it/wp-content/uploads/2021/06/Strategia-Inclusione-e-diversita_-INDIRE_marzo-2026.pdf','strategy','SCH,ADU,HED','ALL','INDIRE'),
('lump-sum-handbook-2026','Handbook on the lump sum funding model - Call 2026','https://www.erasmusplus.sk/erasmus_2021_2027/doc/vyzva/2026/Handbook_on_the_lump_sum_funding_model_2026.pdf','funding-handbook','SCH,ADU,VET,HED,YOU','KA210,KA220,KA240','European Commission - official national-agency mirror'),
('eu-programme-version','Erasmus+ - current Programme Guide version','https://erasmus-plus.ec.europa.eu/erasmus-programme-guide','version-discovery','ALL','ALL','European Commission'),
('italy-official-documents','Erasmus+ Italia - documenti ufficiali','https://www.erasmusplus.it/programma/documenti-ufficiali/','discovery','ALL','ALL','Italian national agencies'),
('italy-deadlines-2026','Erasmus+ Italia - scadenze 2026','https://www.erasmusplus.it/programma/scadenze/','deadlines','ALL','ALL','Italian national agencies'),
('eu-where-apply','Erasmus+ - where to apply','https://erasmus-plus.ec.europa.eu/resources-and-tools/how-to-apply/where-to-apply','routing','ALL','ALL','European Commission')]
for ident,title,url,kind,sectors,codes,agency in remote:
    path='raw/pdf/'+ident+'.pdf' if url.lower().endswith('.pdf') else 'raw/web/'+ident+'.html'
    sources.append(dict(id=ident,title=title,url=url,path=path,kind=kind,sectors=sectors.split(','),actions=codes.split(','),authority=agency,year=2026,language='en' if 'lump-sum' in ident or ident.startswith('eu-') else 'it',download=True))
(ROOT/'config/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
print(f'{len(actions)} action routes; {len(sources)} initial sources')
