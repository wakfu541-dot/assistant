#!/usr/bin/env python3
import json, os, random, re, time
from datetime import datetime, timezone

try:
    from curl_cffi import requests
except Exception:
    import requests

API='https://www.asos.com/api/product/search/v2/categories/{cid}'
LIMIT=int(os.environ.get('ASOS_LIMIT_PER_CATEGORY','48'))
MAX_TOTAL=int(os.environ.get('MAX_PRODUCTS','1800'))

CATEGORIES=[
    (5668,'hoodie','homme'),(7617,'pull','homme'),(7616,'tshirt','homme'),(4616,'polo','homme'),(3602,'shirt','homme'),
    (4910,'pants','homme'),(4208,'jean','homme'),(14274,'jogger','homme'),(7078,'short','homme'),
    (3606,'jacket','homme'),(28291,'set','homme'),
    (5775,'sneakers','homme'),(5774,'boots','homme'),(11247,'loafers','homme'),(6593,'sandals','homme'),
    (9265,'bag','homme'),(6517,'cap','homme'),(6474,'belt','homme'),(6519,'sunglasses','homme'),
    (11321,'hoodie','femme'),(2637,'pull','femme'),(4718,'tshirt','femme'),(15200,'shirt','femme'),
    (2640,'pants','femme'),(3630,'jean','femme'),(9263,'short','femme'),(2639,'skirt','femme'),
    (2641,'jacket','femme'),(8799,'dress','femme'),(7618,'jumpsuit','femme'),(19632,'set','femme'),
    (6456,'sneakers','femme'),(6455,'boots','femme'),(6458,'sandals','femme'),(6461,'heels','femme'),
    (8730,'bag','femme'),(25407,'cap','femme'),(6448,'belt','femme'),(4545,'sunglasses','femme'),
]

COLOR_MAP=[('bleu-marine',('navy','marine')),('noir',('black','noir')),('blanc',('white','blanc','ivory')),('gris',('grey','gray','gris','charcoal')),('bleu',('blue','bleu','denim')),('beige',('beige','cream','crème','stone','ecru','écru','sand')),('marron',('brown','marron','chocolate','tan','camel')),('vert',('green','vert','olive')),('kaki',('khaki','kaki')),('rouge',('red','rouge')),('bordeaux',('burgundy','bordeaux','wine')),('rose',('pink','rose')),('violet',('purple','violet','lilac')),('jaune',('yellow','jaune','gold')),('orange',('orange',)),('multicolore',('multi','multicolour','multicolor','print'))]

def txt(v): return str(v or '').strip()

def norm_image(v):
    v=txt(v)
    if not v: return ''
    if v.startswith('//'): return 'https:'+v
    if v.startswith('http://') or v.startswith('https://'): return v.replace('http://','https://',1)
    return 'https://'+v.lstrip('/')

def norm_url(v):
    v=txt(v)
    if not v: return ''
    if v.startswith('http://') or v.startswith('https://'): return v
    if v.startswith('/'): return 'https://www.asos.com'+v
    return 'https://www.asos.com/fr/'+v.lstrip('/')

def price_value(p):
    if isinstance(p,(int,float)): return float(p)
    if not isinstance(p,dict): return None
    cur=p.get('current',p)
    if isinstance(cur,(int,float)): return float(cur)
    if isinstance(cur,dict):
        for k in ('value','price','amount'):
            try:
                if cur.get(k) is not None: return float(cur[k])
            except Exception: pass
        s=txt(cur.get('text'))
    else: s=txt(cur)
    m=re.search(r'(\d+[\.,]?\d*)',s.replace('\u00a0',''))
    return float(m.group(1).replace(',','.')) if m else None

def canonical_colors(colour,name=''):
    s=(txt(colour)+' '+txt(name)).lower(); out=[]
    for label,keys in COLOR_MAP:
        if any(k in s for k in keys): out.append(label)
    return out[:2] or ([txt(colour).lower()] if txt(colour) else [])

def fits(name):
    s=txt(name).lower(); out=[]
    checks=[('baggy',('baggy',)),('oversize',('oversized','oversize')),('relaxed',('relaxed',)),('slim',('slim','skinny','fitted')),('wide',('wide leg','wide-leg','wide fit')),('straight',('straight leg','straight-leg','straight fit')),('tapered',('tapered',)),('flare',('flare','flared','bootcut')),('cropped',('cropped','crop '))]
    for label,keys in checks:
        if any(k in s for k in keys): out.append(label)
    return out or ['regular']

def refined_type(base,name):
    s=txt(name).lower()
    if base=='hoodie': return 'hoodie' if ('hood' in s or 'zip-through' in s or 'zip through' in s) else 'sweatshirt'
    if base=='pull': return 'cardigan' if 'cardigan' in s else 'pull'
    if base=='tshirt':
        if any(k in s for k in ('long sleeve','long-sleeve','longsleeve')): return 'longsleeve'
        if any(k in s for k in ('vest','tank top','tank-top')): return 'tank'
        return 'tshirt'
    if base=='pants': return 'cargo' if 'cargo' in s else 'pants'
    if base=='jacket':
        if any(k in s for k in ('denim jacket','jean jacket')): return 'denimjacket'
        if 'bomber' in s: return 'bomber'
        if any(k in s for k in ('puffer','padded jacket','down jacket')): return 'puffer'
        if 'parka' in s: return 'parka'
        if 'trench' in s: return 'trench'
        if any(k in s for k in ('gilet','vest jacket','sleeveless jacket')): return 'vest'
        return 'jacket'
    return base

def styles(name,brand,ptype):
    s=(txt(name)+' '+txt(brand)).lower(); out=['casual']
    if ptype in ('hoodie','sweatshirt','cargo','jogger','sneakers','bomber','denimjacket','cap'): out.append('streetwear')
    if any(k in s for k in ('nike','adidas','puma','new balance','under armour','running','training','sport')): out.append('sport')
    if any(k in s for k in ('plain','minimal','clean','basic','essential')): out.append('minimal')
    if ptype in ('dress','heels','loafers') or any(k in s for k in ('smart','tailored','satin','formal')): out.append('chic')
    if any(k in s for k in ('vintage','retro','90s','y2k')): out.append('vintage')
    if any(k in s for k in ('workwear','utility','carhartt')): out.append('workwear')
    return list(dict.fromkeys(out))[:4]

def get_session():
    try: return requests.Session(impersonate='chrome124')
    except TypeError: return requests.Session()

def fetch_category(session,cid):
    params={'channel':'desktop-web','country':'FR','currency':'EUR','lang':'fr-FR','store':'FR','offset':'0','limit':str(LIMIT),'rowlength':'4'}
    headers={'Accept':'application/json,text/plain,*/*','Accept-Language':'fr-FR,fr;q=0.9,en;q=0.7','Referer':'https://www.asos.com/fr/','User-Agent':'Mozilla/5.0'}
    url=API.format(cid=cid); last=None
    for attempt in range(5):
        try:
            r=session.get(url,params=params,headers=headers,timeout=35)
            if r.status_code==200:
                data=r.json(); return data.get('products',[]) if isinstance(data,dict) else []
            last=f'HTTP {r.status_code}'
        except Exception as e: last=repr(e)
        time.sleep(1.4*(attempt+1)+random.random())
    print(f'category {cid} failed: {last}')
    return []

def pick(obj,*keys):
    for k in keys:
        if isinstance(obj,dict) and obj.get(k) not in (None,''): return obj.get(k)
    return None

def normalize(raw,base_type,gender):
    name=txt(pick(raw,'name','productName','title'))
    if not name: return None
    brand=txt(pick(raw,'brandName','brand','manufacturer')) or 'ASOS'
    colour=txt(pick(raw,'colour','color','colourName'))
    image=norm_image(pick(raw,'imageUrl','image','primaryImageUrl'))
    url=norm_url(pick(raw,'url','productUrl','dpUrl'))
    if not image or not url: return None
    ptype=refined_type(base_type,name)
    product_id=txt(pick(raw,'id','productId','productCode')) or re.sub(r'\W+','-',name.lower())[:80]
    return {'id':f'asos-{product_id}','name':name,'brand':brand,'store':'ASOS','type':ptype,'gender':gender,'price':price_value(pick(raw,'price','currentPrice')),'quality':7,'deliveryDays':4,'styles':styles(name,brand,ptype),'colors':canonical_colors(colour,name),'fits':fits(name),'sizes':[],'image':image,'url':url,'verified':'Donnée publique ASOS'}

def main():
    s=get_session(); products={}; ok=0
    for cid,ptype,gender in CATEGORIES:
        rows=fetch_category(s,cid)
        if rows: ok+=1
        for raw in rows:
            p=normalize(raw,ptype,gender)
            if p: products[p['id']]=p
            if len(products)>=MAX_TOTAL: break
        print(f'{cid} {ptype}/{gender}: {len(rows)} rows; total {len(products)}')
        if len(products)>=MAX_TOTAL: break
        time.sleep(0.35+random.random()*0.35)
    out=list(products.values())
    if len(out)<25:
        print(f'Only {len(out)} products fetched from {ok} categories; keeping existing catalogue.')
        return 0
    out.sort(key=lambda p:(p['type'],p['gender'],p['brand'],p['name']))
    with open('products.json','w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,separators=(',',':'))
    meta={'source':'ASOS France · données publiques (non affiliées)','generated_at':datetime.now(timezone.utc).isoformat(),'count':len(out),'categories_ok':ok,'affiliate':False}
    with open('products-meta.json','w',encoding='utf-8') as f: json.dump(meta,f,ensure_ascii=False,indent=2)
    print(f'Wrote {len(out)} ASOS products from {ok}/{len(CATEGORIES)} categories.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
