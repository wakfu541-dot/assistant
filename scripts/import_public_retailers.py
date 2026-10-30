#!/usr/bin/env python3
import json, os, re, time, html as htmlmod, hashlib
from collections import deque, defaultdict
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; AssistantShoppingCatalog/1.1; +https://github.com/wakfu541-dot/assistant)"
MAX_PER_SOURCE = int(os.environ.get("MAX_PER_SOURCE", "24"))
MAX_PAGES_PER_SOURCE = int(os.environ.get("MAX_PAGES_PER_SOURCE", "12"))
TIMEOUT = int(os.environ.get("FETCH_TIMEOUT", "7"))
SLEEP = float(os.environ.get("FETCH_SLEEP", "0.05"))

SOURCES = [
    {"store":"Nike","domain":"nike.com","gender":"unisex","seeds":["https://www.nike.com/fr/w/3sikpz8ufa6","https://www.nike.com/fr/w/32dxrz9b1o4"]},
    {"store":"Gap","domain":"gap-france.fr","gender":"unisex","seeds":["https://www.gap-france.fr/homme","https://www.gap-france.fr/femme"]},
    {"store":"Bonprix","domain":"bonprix.fr","gender":"unisex","seeds":["https://www.bonprix.fr/sitemap/"]},
    {"store":"C&A","domain":"c-and-a.com","gender":"unisex","seeds":["https://www.c-and-a.com/fr/fr/shop/homme","https://www.c-and-a.com/fr/fr/shop/femme"]},
    {"store":"Jules","domain":"jules.com","gender":"homme","seeds":["https://www.jules.com/fr-fr/plan-du-site.html"]},
    {"store":"Promod","domain":"promod.fr","gender":"femme","seeds":["https://www.promod.fr/fr-fr/vetements-femme--lpblt372d979321a5f6bc/"]},
    {"store":"BSTN","domain":"bstn.com","gender":"unisex","seeds":["https://www.bstn.com/eu_fr/men/all-products","https://www.bstn.com/eu_fr/women/all-products"]},
    {"store":"Size?","domain":"sizeofficial.fr","gender":"unisex","seeds":["https://www.sizeofficial.fr/homme/","https://www.sizeofficial.fr/femme/"]},
    {"store":"boohooMAN","domain":"boohooman.com","gender":"homme","seeds":["https://www.boohooman.com/fr/categories/vetements-hommes"]},
    {"store":"Boohoo","domain":"boohoo.com","gender":"femme","seeds":["https://fr.boohoo.com/categories/vetements-femmes"]},
    {"store":"SNIPES","domain":"snipes.com","gender":"unisex","seeds":["https://www.snipes.com/fr-fr/c/vetements-81","https://www.snipes.com/fr-fr/c/chaussures-70"]},
    {"store":"Celio","domain":"celio.com","gender":"homme","seeds":["https://www.celio.com/fr-fr/c/toute-la-collection"]},
    {"store":"Courir","domain":"courir.com","gender":"unisex","seeds":["https://www.courir.com/fr/c/homme/chaussures/sneakers/","https://www.courir.com/fr/c/femme/chaussures/sneakers/"]},
    {"store":"Decathlon","domain":"decathlon.fr","gender":"unisex","seeds":["https://www.decathlon.fr/homme/vetements","https://www.decathlon.fr/femme/vetements"]},
    {"store":"La Redoute","domain":"laredoute.fr","gender":"unisex","seeds":["https://www.laredoute.fr/pplp/100/157938/cat-244.aspx","https://www.laredoute.fr/pplp/100/157878/cat-201.aspx"]},
    {"store":"Zalando","domain":"zalando.fr","gender":"unisex","seeds":["https://www.zalando.fr/catalogue/","https://www.zalando.fr/homme/"]},
    {"store":"Foot Locker","domain":"footlocker.fr","gender":"unisex","seeds":["https://www.footlocker.fr/fr/sitemap.html"]},
    {"store":"Spartoo","domain":"spartoo.com","gender":"unisex","seeds":["https://www.spartoo.com/"]},
]

TYPE_RULES = [
    ("hoodie", r"\b(hoodie|sweat.{0,12}capuche|sweatshirt.{0,12}capuche)\b"),
    ("polo", r"\bpolo\b"),
    ("cardigan", r"\b(cardigan|gilet)\b"),
    ("sweatshirt", r"\b(sweatshirt|sweat)\b"),
    ("longsleeve", r"(manches longues|long.?sleeve)"),
    ("tshirt", r"\b(t.?shirt|tee.?shirt)\b"),
    ("shirt", r"\b(chemise|blouse|shirt)\b"),
    ("tank", r"\b(d[ée]bardeur|tank top|top)\b"),
    ("jean", r"\b(jean|denim)\b"),
    ("cargo", r"\bcargo\b"),
    ("jogger", r"\b(jogger|jogging|surv[êe]tement|sweat.?pant)\b"),
    ("short", r"\b(short|bermuda)\b"),
    ("skirt", r"\b(jupe|skirt)\b"),
    ("blazer", r"\b(blazer|tailleur)\b"),
    ("puffer", r"\b(doudoune|puffer)\b"),
    ("parka", r"\bparka\b"),
    ("trench", r"\btrench\b"),
    ("coat", r"\b(manteau|coat)\b"),
    ("denimjacket", r"(veste.{0,8}jean|denim jacket)"),
    ("bomber", r"\b(bomber|blouson aviateur)\b"),
    ("jacket", r"\b(veste|jacket|blouson)\b"),
    ("dress", r"\b(robe|dress)\b"),
    ("jumpsuit", r"\b(combinaison|combishort|jumpsuit)\b"),
    ("set", r"\b(ensemble|coordonn[ée]|set|tracksuit)\b"),
    ("sneakers", r"\b(sneaker|basket|trainer)\b"),
    ("loafers", r"\b(mocassin|loafer)\b"),
    ("sandals", r"\b(sandale|sandal|claquette|slide)\b"),
    ("heels", r"\b(escarpin|talon|heel)\b"),
    ("boots", r"\b(boot|botte|bottine)\b"),
    ("bag", r"\b(sac|bag|backpack|sac.{0,5}dos)\b"),
    ("cap", r"\b(casquette|bonnet|cap|beanie)\b"),
    ("belt", r"\b(ceinture|belt)\b"),
    ("sunglasses", r"\b(lunettes.{0,10}soleil|sunglasses)\b"),
    ("jewelry", r"\b(bijou|collier|bracelet|boucle.{0,8}oreille|jewell?ery)\b"),
    ("pants", r"\b(pantalon|trouser|chino|track pant)\b"),
    ("pull", r"\b(pull|maille|sweater|knit)\b"),
]

COLORS={
"noir":["noir","black"],"blanc":["blanc","white","ecru","écru"],"gris":["gris","grey","gray"],
"bleu":["bleu","blue"],"bleu-marine":["marine","navy"],"beige":["beige","creme","crème","cream"],
"marron":["marron","brown","camel"],"vert":["vert","green"],"kaki":["kaki","khaki"],"rouge":["rouge","red"],
"bordeaux":["bordeaux","burgundy"],"rose":["rose","pink"],"violet":["violet","purple"],"jaune":["jaune","yellow"],
"orange":["orange"],"multicolore":["multicolore","multicolor","multi-colour"]}
FIT_WORDS={"oversize":["oversize","oversized"],"baggy":["baggy"],"wide":["wide","large"],"slim":["slim","ajusté","ajuste"],"relaxed":["relaxed","décontracté","decontracte"],"straight":["straight","droit","droite"],"tapered":["tapered","fuselé","fusele"],"flare":["flare","évasé","evase"],"cropped":["cropped","court","courte"],"regular":["regular","standard","classique"]}
STYLE_WORDS={"streetwear":["streetwear","baggy","oversize","sneaker","cargo"],"sport":["sport","running","training","basketball","football","dri-fit","dryfit"],"outdoor":["outdoor","trail","randonnée","randonnee","parka"],"workwear":["workwear","utility","utilitaire"],"formal":["costume","tailleur","formel","habillé","habille"],"chic":["chic","blazer","satin","laine"],"vintage":["vintage","retro"],"minimal":["minimal","basic","basique"],"casual":["casual","regular","relaxed","coton"],"preppy":["preppy","polo","mocassin"],"y2k":["y2k"],"techwear":["techwear"]}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ld=[]; self.meta={}; self._ld=False; self._buf=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs); t=tag.lower()
        if t=="a" and d.get("href"): self.links.append(d["href"])
        if t=="meta" and d.get("content"):
            k=(d.get("property") or d.get("name") or "").lower()
            if k:self.meta[k]=d["content"]
        if t=="link" and "canonical" in (d.get("rel") or "").lower() and d.get("href"):self.meta["canonical"]=d["href"]
        if t=="script" and "ld+json" in (d.get("type") or "").lower():self._ld=True;self._buf=[]
    def handle_data(self,data):
        if self._ld:self._buf.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="script" and self._ld:self.ld.append("".join(self._buf));self._ld=False;self._buf=[]

def fetch(url):
    req=Request(url,headers={"User-Agent":UA,"Accept-Language":"fr-FR,fr;q=0.9,en;q=0.4","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    with urlopen(req,timeout=TIMEOUT) as r:
        data=r.read(3_000_000);ct=(r.headers.get("content-type") or "").lower()
    enc="utf-8";m=re.search(r"charset=([-\w]+)",ct)
    if m:enc=m.group(1)
    return data.decode(enc,errors="replace"),ct

def clean_url(u,base):
    u=htmlmod.unescape(u or "").strip()
    if not u or u.startswith(("javascript:","mailto:","tel:","#")):return None
    return urldefrag(urljoin(base,u))[0]

def same_domain(url,domain):
    h=(urlparse(url).hostname or "").lower();return h==domain or h.endswith("."+domain)

def iter_nodes(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from iter_nodes(v)
    elif isinstance(x,list):
        for v in x:yield from iter_nodes(v)

def image_url(v):
    if isinstance(v,str):return v
    if isinstance(v,list):
        for x in v:
            y=image_url(x)
            if y:return y
    if isinstance(v,dict):return v.get("url") or v.get("contentUrl")
    return None

def price_of(v):
    offers=v if isinstance(v,list) else [v] if isinstance(v,dict) else []
    vals=[];cur=None
    for o in offers:
        if not isinstance(o,dict):continue
        cur=cur or o.get("priceCurrency")
        for k in ("price","lowPrice","highPrice"):
            try:
                if o.get(k) not in (None,""):vals.append(float(str(o[k]).replace(",",".")));break
            except:pass
    return (min(vals) if vals else None),cur

def detect_type(text):
    s=(text or "").lower()
    for typ,pat in TYPE_RULES:
        if re.search(pat,s,re.I):return typ
    return None

def detect_list(text,mapping,limit):
    s=(text or "").lower();out=[]
    for k,words in mapping.items():
        if any(w in s for w in words):out.append(k)
    return out[:limit]

def gender(text,default):
    s=(text or "").lower()
    if re.search(r"\b(femme|women|woman)\b",s):return "femme"
    if re.search(r"\b(homme|men|man)\b",s):return "homme"
    return default or "unisex"

def parse(text):
    p=Parser()
    try:p.feed(text)
    except:pass
    nodes=[]
    for raw in p.ld:
        raw=htmlmod.unescape(raw).strip()
        if not raw:continue
        try:data=json.loads(raw)
        except:continue
        for n in iter_nodes(data):
            t=n.get("@type");types=[t] if isinstance(t,str) else t if isinstance(t,list) else []
            if "Product" in types or (n.get("name") and n.get("offers") and n.get("image")):nodes.append(n)
    return nodes,p.links,p.meta

def make_id(store,url):
    return store.lower().replace(" ","-").replace("?","")+"-"+hashlib.sha1(url.encode()).hexdigest()[:16]

def normalize_node(n,page,src):
    name=str(n.get("name") or "").strip();img=image_url(n.get("image"));url=clean_url(n.get("url") or page,page)
    if not name or not img or not url:return None
    if img.startswith("//"):img="https:"+img
    img=urljoin(page,img);price,cur=price_of(n.get("offers"))
    if cur and str(cur).upper() not in ("EUR","€"):price=None
    brand=n.get("brand");brand=brand if isinstance(brand,str) else (brand or {}).get("name") if isinstance(brand,dict) else None
    context=" ".join([name,str(n.get("description") or ""),str(n.get("category") or ""),str(n.get("color") or ""),url]);typ=detect_type(context)
    if not typ:return None
    return {"id":make_id(src["store"],url),"name":name,"brand":brand or src["store"],"store":src["store"],"type":typ,"gender":gender(context,src.get("gender")),"price":round(price,2) if isinstance(price,(int,float)) else None,"quality":7,"deliveryDays":4,"styles":detect_list(context,STYLE_WORDS,4) or ["casual"],"colors":detect_list(context,COLORS,3),"fits":detect_list(context,FIT_WORDS,3) or ["regular"],"sizes":[],"image":img,"url":url,"verified":f"Donnée publique {src['store']}"}

def normalize_meta(meta,page,src):
    name=(meta.get("og:title") or meta.get("twitter:title") or "").strip();img=meta.get("og:image") or meta.get("twitter:image");url=clean_url(meta.get("og:url") or meta.get("canonical") or page,page)
    is_product="product" in (meta.get("og:type") or "").lower() or any(k in meta for k in ("product:price:amount","product:price","og:price:amount"))
    if not is_product or not name or not img or not url:return None
    price=None
    for k in ("product:price:amount","product:price","og:price:amount"):
        try:
            if meta.get(k):price=float(str(meta[k]).replace(",",".").replace("€","").strip());break
        except:pass
    context=" ".join([name,url]);typ=detect_type(context)
    if not typ:return None
    return {"id":make_id(src["store"],url),"name":name,"brand":meta.get("product:brand") or src["store"],"store":src["store"],"type":typ,"gender":gender(context,src.get("gender")),"price":round(price,2) if isinstance(price,(int,float)) else None,"quality":7,"deliveryDays":4,"styles":detect_list(context,STYLE_WORDS,4) or ["casual"],"colors":detect_list(context,COLORS,3),"fits":detect_list(context,FIT_WORDS,3) or ["regular"],"sizes":[],"image":urljoin(page,img),"url":url,"verified":f"Page publique {src['store']}"}

PATTERNS={
"nike.com":["/t/"],"gap-france.fr":["/sweat-","/jean-","/pantalon-","/veste-","/t-shirt-","/robe-","/pull-","/chemise-"],
"bonprix.fr":["/produit/","-p-"],"c-and-a.com":["/p/","/product"],"jules.com":["/p/","-p"],"promod.fr":["--pbl","/p/"],
"bstn.com":["/p/","/product","/eu_fr/"],"sizeofficial.fr":["/product/","-product"],"boohooman.com":["/product/","/fr/"],
"boohoo.com":["/product/","/fr/"],"snipes.com":["/p/","/product"],"celio.com":["/p/","product"],"courir.com":["/product","/p/"],
"decathlon.fr":["/p/","product"],"laredoute.fr":["/ppdp/","product"],"zalando.fr":[".html","/p/"],"footlocker.fr":["/product/"],"spartoo.com":["-p","product"]}

def score_url(url,src):
    u=url.lower();s=0
    for p in PATTERNS.get(src["domain"],[]):
        if p in u:s+=5
    if any(k in u for k in ("product","produit","article","prd")):s+=3
    if "sitemap" in u or u.endswith(".xml"):s+=1
    if any(k in u for k in ("login","privacy","cookie","help","aide","career","magasin","store-locator")):s-=10
    return s

def xml_links(text,base):
    return [x for x in (clean_url(v,base) for v in re.findall(r"<loc>\s*(.*?)\s*</loc>",text,re.I|re.S)) if x]

def crawl(src):
    q=deque((u,0) for u in src["seeds"]);seen=set();products={};errors=[];fetched=0
    while q and fetched<MAX_PAGES_PER_SOURCE and len(products)<MAX_PER_SOURCE:
        url,depth=q.popleft()
        if url in seen or not same_domain(url,src["domain"]):continue
        seen.add(url)
        try:text,ct=fetch(url);fetched+=1;time.sleep(SLEEP)
        except Exception as e:errors.append(f"{url}: {type(e).__name__}");continue
        if "xml" in ct or url.lower().endswith(".xml"):
            links=sorted(set(xml_links(text,url)),key=lambda x:score_url(x,src),reverse=True)
            for v in links[:100]:
                if v not in seen:q.append((v,depth+1))
            continue
        nodes,links,meta=parse(text)
        for n in nodes:
            p=normalize_node(n,url,src)
            if p and same_domain(p["url"],src["domain"]):products[p["url"]]=p
            if len(products)>=MAX_PER_SOURCE:break
        if len(products)<MAX_PER_SOURCE:
            p=normalize_meta(meta,url,src)
            if p and same_domain(p["url"],src["domain"]):products[p["url"]]=p
        if depth<2 and len(products)<MAX_PER_SOURCE:
            candidates=[]
            for href in links:
                v=clean_url(href,url)
                if v and same_domain(v,src["domain"]) and v not in seen:candidates.append(v)
            candidates=sorted(set(candidates),key=lambda x:score_url(x,src),reverse=True)
            for v in candidates[:60 if depth==0 else 35]:q.append((v,depth+1))
    return list(products.values()),{"fetched_pages":fetched,"errors":errors[:6]}

def main():
    try:
        with open("products.json",encoding="utf-8") as f:existing=json.load(f)
        if not isinstance(existing,list):existing=[]
    except:existing=[]
    merged={p.get("url"):p for p in existing if isinstance(p,dict) and p.get("url")}
    diagnostics={};run_counts={}
    for src in SOURCES:
        print(f"[{src['store']}] checking public catalogue…",flush=True)
        items,diag=crawl(src);diagnostics[src["store"]]=diag;run_counts[src["store"]]=len(items)
        if items:
            for u,p in list(merged.items()):
                if p.get("store")==src["store"]:del merged[u]
            for p in items:merged[p["url"]]=p
        print(f"[{src['store']}] {len(items)} usable products / {diag['fetched_pages']} pages",flush=True)
    products=list(merged.values());products.sort(key=lambda p:(p.get("store",""),p.get("type",""),p.get("name","")))
    with open("products.json","w",encoding="utf-8") as f:json.dump(products,f,ensure_ascii=False,indent=2)
    totals=defaultdict(int)
    for p in products:totals[p.get("store","Unknown")]+=1
    meta={"source":"catalogue public multi-marchands 0 €","updated_at":datetime.now(timezone.utc).isoformat(),"count":len(products),"providers_tried":["ASOS"]+[s["store"] for s in SOURCES],"providers_with_products":[k for k,v in totals.items() if v>0],"provider_counts":dict(totals),"last_run_counts":run_counts,"diagnostics":diagnostics,"note":"Aucun compte, aucune clé API, aucune image inventée. Les sites qui refusent les requêtes publiques sont laissés de côté."}
    with open("products-meta.json","w",encoding="utf-8") as f:json.dump(meta,f,ensure_ascii=False,indent=2)
    print(json.dumps({"total":len(products),"last_run":run_counts},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
