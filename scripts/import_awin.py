#!/usr/bin/env python3
import csv,gzip,io,json,os,re,sys,urllib.request
from datetime import datetime,timezone

KEY=os.environ.get('AWIN_DATAFEED_API_KEY','').strip()
MERCHANTS=[x.strip().lower() for x in os.environ.get('AWIN_MERCHANTS','ASOS,JD Sports,Foot Locker,Nike,adidas,New Balance,La Redoute,boohoo,FARFETCH,SNIPES,Under Armour,Footpatrol,Sneakin,BSTN,Spartoo').split(',') if x.strip()]
MAX_TOTAL=int(os.environ.get('MAX_PRODUCTS','5000'))
MAX_FEED=int(os.environ.get('MAX_PRODUCTS_PER_FEED','400'))
UA='AssistantShoppingCatalog/1.0'
if not KEY:
    print('AWIN_DATAFEED_API_KEY missing; keeping current catalogue.')
    sys.exit(0)

def get(url,timeout=90):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Encoding':'gzip'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=r.read(); enc=(r.headers.get('Content-Encoding') or '').lower()
    if enc=='gzip' or data[:2]==b'\x1f\x8b': data=gzip.decompress(data)
    return data

def rows(data):
    for enc in ('utf-8-sig','utf-8','latin-1'):
        try:return list(csv.DictReader(io.StringIO(data.decode(enc))))
        except UnicodeDecodeError: pass
    raise RuntimeError('Cannot decode CSV')

def value(row,*keys):
    d={str(k).lower().strip():v for k,v in row.items() if k}
    for k in keys:
        v=d.get(k.lower())
        if v is not None and str(v).strip(): return str(v).strip()
    return ''

def price(s):
    if not s:return None
    m=re.search(r'\d+(?:[\.,]\d+)?',s.replace('\xa0',' ').replace('€',''))
    if not m:return None
    try:return float(m.group(0).replace(',','.'))
    except:return None

def text(*p):return ' '.join(x for x in p if x).lower()

def ptype(t):
    rules=[('hoodie',['hoodie','sweat à capuche','sweat capuche']),('sweatshirt',['sweatshirt','sweat-shirt','crewneck']),('cardigan',['cardigan','gilet']),('pull',['pullover','jumper','sweater','pull','maille','knit']),('polo',['polo']),('longsleeve',['long sleeve','manches longues','longsleeve']),('tshirt',['t-shirt','t shirt','tee shirt',' tee']),('shirt',['chemise','shirt']),('tank',['débardeur','debardeur','tank top','crop top']),('jean',['jean','denim trouser','denim pants']),('cargo',['cargo']),('jogger',['jogger','jogging','track pants','tracksuit bottom']),('short',['short','bermuda']),('skirt',['jupe','skirt']),('pants',['pantalon','trouser','pants','chino']),('denimjacket',['veste en jean','denim jacket']),('bomber',['bomber']),('blazer',['blazer']),('puffer',['doudoune','puffer','down jacket']),('parka',['parka']),('trench',['trench']),('coat',['manteau','overcoat',' coat']),('vest',['sans manches','bodywarmer']),('jacket',['veste','jacket']),('dress',['robe','dress']),('jumpsuit',['combinaison','jumpsuit','playsuit']),('set',['ensemble','co-ord','coord','tracksuit']),('sneakers',['sneaker','basket','trainer']),('boots',['boot','bottine','botte']),('loafers',['loafer','mocassin']),('sandals',['sandale','sandal']),('heels',['talon','heel','pump']),('bag',['sac','bag','backpack','pochette']),('cap',['casquette','bonnet','beanie',' cap','hat']),('belt',['ceinture','belt']),('sunglasses',['lunettes de soleil','sunglasses']),('jewelry',['bijou','jewellery','jewelry','bracelet','necklace','ring','earring'])]
    for typ,kws in rules:
        if any(k in t for k in kws):return typ
    return None

def gender(t,e=''):
    e=e.lower()
    if e in ('male','men','man','homme'):return 'homme'
    if e in ('female','women','woman','femme'):return 'femme'
    if 'unisex' in e:return 'unisex'
    if any(k in t for k in [' femme','women','woman','ladies']):return 'femme'
    if any(k in t for k in [' homme',' mens',' men ',' man ']):return 'homme'
    return 'unisex'

def colours(t):
    pairs=[('noir',['noir','black']),('blanc',['blanc','white']),('gris',['gris','grey','gray']),('bleu-marine',['navy','bleu marine']),('bleu',['bleu','blue']),('beige',['beige','cream','crème','ecru','écru']),('marron',['marron','brown','camel']),('vert',['vert','green']),('kaki',['kaki','khaki']),('rouge',['rouge','red']),('bordeaux',['bordeaux','burgundy']),('rose',['rose','pink']),('violet',['violet','purple']),('jaune',['jaune','yellow']),('orange',['orange']),('multicolore',['multicolor','multicolour','multicolore'])]
    return [n for n,k in pairs if any(x in t for x in k)][:3]

def fits(t):
    pairs=[('oversize',['oversize','oversized']),('baggy',['baggy']),('wide',['wide leg','wide-leg']),('slim',['slim']),('relaxed',['relaxed','décontractée','decontractee']),('straight',['straight','droite']),('tapered',['tapered','fusel']),('flare',['flare','évas','evas']),('cropped',['cropped']),('regular',['regular','classique'])]
    out=[n for n,k in pairs if any(x in t for x in k)]
    return out[:3] or ['regular']

def styles(t):
    pairs=[('streetwear',['streetwear','street','skate']),('sport',['sport','training','running','football','basketball','gym']),('minimal',['minimal','basic','essential','plain']),('chic',['chic','smart','tailored','élégant','elegant']),('formal',['formal','costume','suit','business']),('workwear',['workwear','utility','carpenter','cargo']),('vintage',['vintage','retro','90s','80s']),('techwear',['techwear','technical']),('preppy',['preppy','college','varsity']),('outdoor',['outdoor','hiking','trail','gore-tex']),('y2k',['y2k','2000s']),('casual',['casual','everyday'])]
    out=[n for n,k in pairs if any(x in t for x in k)]
    return out[:4] or ['casual']

def sizes(s):
    out=[]
    for token in re.split(r'[|,;/]+',s or ''):
        x=token.strip().upper()
        if re.fullmatch(r'(XXS|XS|S|M|L|XL|XXL|XXXL|3XL|4XL)',x):out.append('3XL' if x=='XXXL' else x)
        elif re.fullmatch(r'(?:EU\s*)?\d{2}',x):
            n=int(re.sub(r'\D','',x))
            if 30<=n<=60:out.append(f'EU {n}')
        elif re.fullmatch(r'W\s*\d{2}',x):out.append('W'+re.sub(r'\D','',x))
    return list(dict.fromkeys(out))[:20]

def allowed(name):
    n=name.lower();return any(m in n or n in m for m in MERCHANTS)

def out_of_stock(r):
    s=value(r,'stock_status','in_stock','is_for_sale').lower()
    return s in ('0','false','no','out of stock','out_of_stock','sold out','not for sale')

feedlist=rows(get(f'https://productdata.awin.com/datafeed/list/apikey/{KEY}'))
feeds=[]
for r in feedlist:
    name=value(r,'Advertiser Name','merchant_name','advertiser_name');url=value(r,'URL','url')
    if not name or not url or not allowed(name):continue
    lang=value(r,'Language','language').lower();region=value(r,'Primary Region','primary_region').lower()
    pref=(2 if 'fr' in region or 'france' in region else 0)+(2 if 'french' in lang or lang=='fr' else 0)+(1 if 'english' in lang or lang=='en' else 0)
    feeds.append((pref,name,url))
feeds.sort(reverse=True)
products=[];seen=set();stats=[]
for _,merchant,url in feeds:
    if len(products)>=MAX_TOTAL:break
    try:data=rows(get(url,120))
    except Exception as e:
        print('WARN',merchant,e);continue
    kept=0
    for r in data:
        if kept>=MAX_FEED or len(products)>=MAX_TOTAL:break
        if out_of_stock(r):continue
        name=value(r,'product_name','title','name');desc=value(r,'product_short_description','description');cat=value(r,'category_name','merchant_category','product_type','merchant_product_category_path')
        typ=ptype(text(name,desc,cat))
        if not typ:continue
        image=value(r,'large_image','merchant_image_url','aw_image_url','image_link','merchant_thumb_url');deep=value(r,'aw_deep_link','merchant_deep_link','link')
        if not image or not deep:continue
        currency=value(r,'currency')
        if currency and currency.upper() not in ('EUR','EURO','€'):continue
        pid=value(r,'aw_product_id','merchant_product_id','product_id','ean','mpn') or deep;key=(merchant.lower(),pid)
        if key in seen:continue
        seen.add(key);full=text(name,desc,cat,value(r,'keywords'));brand=value(r,'brand_name','brand') or merchant;rating=price(value(r,'average_rating','rating','number_stars'))
        products.append({'id':f'awin-{value(r,"merchant_id","advertiser_id") or merchant}-{pid}','name':name,'brand':brand,'store':merchant,'type':typ,'gender':gender(full,value(r,'gender')),'price':price(value(r,'search_price','store_price','price')),'quality':max(5,min(10,round((rating/5)*10))) if rating and rating<=5 else 7,'deliveryDays':4,'styles':styles(full),'colors':colours(text(value(r,'colour','color'),name,desc)),'fits':fits(full),'sizes':sizes(value(r,'size_stock_status','size','sizes','specifications')),'image':image,'url':deep,'verified':'Flux Awin'})
        kept+=1
    stats.append({'merchant':merchant,'kept':kept});print(merchant,kept)
if not products:
    print('No products imported; keeping existing catalogue.');sys.exit(0)
products.sort(key=lambda p:(p['type'],p['store'].lower(),p['name'].lower()))
with open('products.json','w',encoding='utf-8') as f:json.dump(products,f,ensure_ascii=False,indent=2)
with open('products-meta.json','w',encoding='utf-8') as f:json.dump({'source':'Awin product feeds','updated_at':datetime.now(timezone.utc).isoformat(),'count':len(products),'merchants':stats},f,ensure_ascii=False,indent=2)
print('Wrote',len(products),'products')