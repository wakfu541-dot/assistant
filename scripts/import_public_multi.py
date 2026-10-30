#!/usr/bin/env python3
import json, os, re, time, html as htmlmod
from collections import deque, defaultdict
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; AssistantShoppingCatalog/1.0; +https://github.com/wakfu541-dot/assistant)"
MAX_PER_SOURCE = int(os.environ.get("MAX_PER_SOURCE", "35"))
MAX_PAGES_PER_SOURCE = int(os.environ.get("MAX_PAGES_PER_SOURCE", "40"))
TIMEOUT = int(os.environ.get("FETCH_TIMEOUT", "18"))
SLEEP = float(os.environ.get("FETCH_SLEEP", "0.12"))

SOURCES = [
    {"store":"Foot Locker","domain":"footlocker.fr","gender":"unisex","seeds":["https://www.footlocker.fr/fr/sitemap.html"]},
    {"store":"Nike","domain":"nike.com","gender":"unisex","seeds":["https://www.nike.com/fr/w/3sikpz8ufa6","https://www.nike.com/fr/w/32dxrz9b1o4"]},
    {"store":"adidas","domain":"adidas.fr","gender":"unisex","seeds":["https://www.adidas.fr/glass/sitemaps/adidas/FR/fr/html-sitemap/index.html"]},
    {"store":"New Balance","domain":"newbalance.fr","gender":"unisex","seeds":["https://www.newbalance.fr/fr/sitemap/"]},
    {"store":"H&M","domain":"hm.com","gender":"unisex","seeds":["https://www2.hm.com/fr_fr/men/shop-by-product/view-all.html","https://www2.hm.com/fr_fr/femme/shop-by-product/view-all.html"]},
    {"store":"UNIQLO","domain":"uniqlo.com","gender":"unisex","seeds":["https://www.uniqlo.com/fr/fr/men_home","https://www.uniqlo.com/fr/fr/women_home"]},
    {"store":"ZARA","domain":"zara.com","gender":"unisex","seeds":["https://www.zara.com/fr/fr/homme-mkt534.html","https://www.zara.com/fr/fr/femme-mkt1000.html"]},
    {"store":"Bershka","domain":"bershka.com","gender":"unisex","seeds":["https://www.bershka.com/fr/homme/nouvelle-collection-c1010903178.html","https://www.bershka.com/fr/femme/nouvelle-collection-c1010874670.html"]},
    {"store":"Stradivarius","domain":"stradivarius.com","gender":"femme","seeds":["https://www.stradivarius.com/fr/sitemap.html"]},
    {"store":"Spartoo","domain":"spartoo.com","gender":"unisex","seeds":["https://www.spartoo.com/produits-seconde-main-vetements.php"]},
    {"store":"SNIPES","domain":"snipes.com","gender":"unisex","seeds":["https://www.snipes.com/fr-fr/","https://www.snipes.com/fr-fr/c/vetements-81"]},
    {"store":"Celio","domain":"celio.com","gender":"homme","seeds":["https://www.celio.com/fr-fr","https://www.celio.com/fr-fr/c/toute-la-collection"]},
    {"store":"Courir","domain":"courir.com","gender":"unisex","seeds":["https://www.courir.com/fr/c/homme/chaussures/sneakers/"]},
    {"store":"Decathlon","domain":"decathlon.fr","gender":"unisex","seeds":["https://www.decathlon.fr/homme/vetements","https://www.decathlon.fr/femme/vetements"]},
    {"store":"La Redoute","domain":"laredoute.fr","gender":"unisex","seeds":["https://www.laredoute.fr/pplp/100/157938/cat-244.aspx","https://www.laredoute.fr/pplp/100/157878/cat-201.aspx"]},
    {"store":"Zalando","domain":"zalando.fr","gender":"unisex","seeds":["https://www.zalando.fr/catalogue/","https://www.zalando.fr/homme/"]},
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
    ("jogger", r"\b(jogger|jogging|surv[êe]tement)\b"),
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
    ("set", r"\b(ensemble|coordonn[ée]|set)\b"),
    ("sneakers", r"\b(sneaker|basket|trainer)\b"),
    ("loafers", r"\b(mocassin|loafer)\b"),
    ("sandals", r"\b(sandale|sandal)\b"),
    ("heels", r"\b(escarpin|talon|heel)\b"),
    ("boots", r"\b(boot|botte|bottine)\b"),
    ("bag", r"\b(sac|bag|backpack|sac.{0,5}dos)\b"),
    ("cap", r"\b(casquette|bonnet|cap|beanie)\b"),
    ("belt", r"\b(ceinture|belt)\b"),
    ("sunglasses", r"\b(lunettes.{0,10}soleil|sunglasses)\b"),
    ("jewelry", r"\b(bijou|collier|bracelet|boucle.{0,8}oreille|jewell?ery)\b"),
    ("pants", r"\b(pantalon|trouser|chino)\b"),
    ("pull", r"\b(pull|maille|sweater|knit)\b"),
]

COLORS = {
    "noir":["noir","black"], "blanc":["blanc","white","écru","ecru"],
    "gris":["gris","grey","gray"], "bleu":["bleu","blue"], "bleu-marine":["marine","navy"],
    "beige":["beige","crème","creme","cream"], "marron":["marron","brown","camel"],
    "vert":["vert","green"], "kaki":["kaki","khaki"], "rouge":["rouge","red"],
    "bordeaux":["bordeaux","burgundy"], "rose":["rose","pink"], "violet":["violet","purple"],
    "jaune":["jaune","yellow"], "orange":["orange"], "multicolore":["multicolore","multi-colour","multicolor"]
}
FIT_WORDS = {
    "oversize":["oversize","oversized"], "baggy":["baggy"], "wide":["wide","large"],
    "slim":["slim","ajusté","ajustee"], "relaxed":["relaxed","décontracté","decontracte"],
    "straight":["straight","droit","droite"], "tapered":["tapered","fuselé","fuselee"],
    "flare":["flare","évasé","evase"], "cropped":["cropped","court","courte"], "regular":["regular","standard","classique"]
}
STYLE_WORDS = {
    "streetwear":["streetwear","baggy","oversize","sneaker","cargo"],
    "sport":["sport","running","training","basketball","football","dryfit","dri-fit"],
    "outdoor":["outdoor","trail","randonnée","randonnee","parka"],
    "workwear":["workwear","utility","utilitaire"],
    "formal":["costume","tailleur","formel","habillé","habille"],
    "chic":["chic","blazer","satin","laine"],
    "vintage":["vintage","retro"],
    "minimal":["minimal","basic","basique"],
    "casual":["casual","regular","relaxed","coton"],
    "preppy":["preppy","polo","mocassin"],
    "y2k":["y2k"],
    "techwear":["techwear"],
}

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ld=[]; self.meta={}; self._ld=False; self._buf=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag.lower()=="a" and d.get("href"): self.links.append(d["href"])
        if tag.lower()=="meta" and d.get("content"):
            k=(d.get("property") or d.get("name") or "").lower()
            if k: self.meta[k]=d.get("content")
        if tag.lower()=="link" and (d.get("rel") or "").lower()=="canonical" and d.get("href"):
            self.meta["canonical"]=d.get("href")
        if tag.lower()=="script" and "ld+json" in (d.get("type") or "").lower(): self._ld=True; self._buf=[]
    def handle_data(self, data):
        if self._ld: self._buf.append(data)
    def handle_endtag(self, tag):
        if tag.lower()=="script" and self._ld:
            self.ld.append("".join(self._buf)); self._ld=False; self._buf=[]

def fetch(url):
    req=Request(url, headers={"User-Agent":UA,"Accept-Language":"fr-FR,fr;q=0.9,en;q=0.5","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Cache-Control":"no-cache"})
    with urlopen(req, timeout=TIMEOUT) as r:
        data=r.read(3_000_000); ct=(r.headers.get("content-type") or "").lower()
    enc="utf-8"; m=re.search(r"charset=([-\w]+)",ct)
    if m: enc=m.group(1)
    return data.decode(enc,errors="replace"), ct

def clean_url(u, base):
    u=htmlmod.unescape(u or "").strip()
    if not u or u.startswith(("javascript:","mailto:","tel:","#")): return None
    return urldefrag(urljoin(base,u))[0]

def same_domain(url, domain):
    h=(urlparse(url).hostname or "").lower(); return h==domain or h.endswith("."+domain)

def image_url(v):
    if isinstance(v,str): return v
    if isinstance(v,list):
        for x in v:
            y=image_url(x)
            if y:return y
    if isinstance(v,dict): return v.get("url") or v.get("contentUrl")
    return None

def brand_name(v):
    if isinstance(v,str): return v
    if isinstance(v,dict): return v.get("name") or ""
    return ""

def offer_price(v):
    offers=v if isinstance(v,list) else [v] if isinstance(v,dict) else []; vals=[]; currency=None
    for o in offers:
        if not isinstance(o,dict): continue
        currency=currency or o.get("priceCurrency")
        for k in ("price","lowPrice","highPrice"):
            try:
                if o.get(k) not in (None,""):
                    vals.append(float(str(o[k]).replace(",", "."))); break
            except: pass
    return (min(vals) if vals else None), currency

def detect_type(text):
    s=(text or "").lower()
    for typ,pat in TYPE_RULES:
        if re.search(pat,s,re.I): return typ
    return None

def detect_colors(text):
    s=(text or "").lower(); out=[]
    for c,words in COLORS.items():
        if any(w in s for w in words): out.append(c)
    return out[:3]

def detect_fits(text):
    s=(text or "").lower(); out=[k for k,ws in FIT_WORDS.items() if any(w in s for w in ws)]
    return out[:3] or ["regular"]

def detect_styles(text):
    s=(text or "").lower(); out=[k for k,ws in STYLE_WORDS.items() if any(w in s for w in ws)]
    return out[:4] or ["casual"]

def detect_gender(text, default):
    s=(text or "").lower()
    if re.search(r"\b(femme|women|woman)\b",s): return "femme"
    if re.search(r"\b(homme|men|man)\b",s): return "homme"
    return default or "unisex"

def iter_nodes(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from iter_nodes(v)
    elif isinstance(x,list):
        for v in x: yield from iter_nodes(v)

def parse_jsonld(text):
    out=[]; p=LinkParser()
    try:p.feed(text)
    except:pass
    for raw in p.ld:
        raw=htmlmod.unescape(raw).strip()
        if not raw:continue
        try:data=json.loads(raw)
        except:
            try:data=json.loads(re.sub(r"^\s*<!--|-->\s*$","",raw))
            except:continue
        for node in iter_nodes(data):
            t=node.get("@type"); types=[t] if isinstance(t,str) else t if isinstance(t,list) else []
            if "Product" in types or ("name" in node and "offers" in node and ("image" in node or "sku" in node)): out.append(node)
    return out,p.links,p.meta

def normalize(node,page_url,source):
    name=str(node.get("name") or "").strip()
    if len(name)<3:return None
    img=image_url(node.get("image"))
    if img and img.startswith("//"):img="https:"+img
    if img:img=urljoin(page_url,img)
    url=clean_url(node.get("url") or page_url,page_url)
    if not img or not url:return None
    price,currency=offer_price(node.get("offers"))
    if currency and str(currency).upper() not in ("EUR","€"):price=None
    brand=brand_name(node.get("brand")) or source["store"]
    cat=" ".join(str(node.get(k) or "") for k in ("category","description","color")); context=" ".join([name,cat,url])
    typ=detect_type(context)
    if not typ:return None
    return {"id":f"{source['store'].lower().replace(' ','-')}-{node.get('sku') or node.get('productID') or abs(hash(url))}","name":name,"brand":brand,"store":source["store"],"type":typ,"gender":detect_gender(context,source.get("gender")),"price":round(price,2) if isinstance(price,(int,float)) else None,"quality":7,"deliveryDays":4,"styles":detect_styles(context),"colors":detect_colors(" ".join([name,str(node.get("color") or ""),cat])),"fits":detect_fits(context),"sizes":[],"image":img,"url":url,"verified":f"Donnée publique {source['store']}"}

def normalize_meta(meta,page_url,source):
    if not isinstance(meta,dict): return None
    is_product=("product" in (meta.get("og:type") or "").lower()) or ("product:price:amount" in meta) or ("product:price" in meta)
    if not is_product: return None
    name=(meta.get("og:title") or meta.get("twitter:title") or "").strip()
    img=meta.get("og:image") or meta.get("twitter:image")
    url=clean_url(meta.get("og:url") or meta.get("canonical") or page_url,page_url)
    if not name or not img or not url: return None
    img=urljoin(page_url,img)
    price=None
    for k in ("product:price:amount","product:price","og:price:amount"):
        try:
            if meta.get(k):
                price=float(str(meta[k]).replace(",",".").replace("€","").strip()); break
        except: pass
    context=" ".join([name,url]); typ=detect_type(context)
    if not typ:return None
    return {"id":f"{source['store'].lower().replace(' ','-')}-{abs(hash(url))}","name":name,"brand":meta.get("product:brand") or source["store"],"store":source["store"],"type":typ,"gender":detect_gender(context,source.get("gender")),"price":round(price,2) if isinstance(price,(int,float)) else None,"quality":7,"deliveryDays":4,"styles":detect_styles(context),"colors":detect_colors(context),"fits":detect_fits(context),"sizes":[],"image":img,"url":url,"verified":f"Page publique {source['store']}"}

def candidate_score(url,source):
    u=url.lower(); score=0
    patterns={"footlocker.fr":["/product/","product/"],"nike.com":["/fr/t/","/t/"],"adidas.fr":[".html","/product/"],"newbalance.fr":["/pd/","/fr/pd/"],"hm.com":[".html","/productpage."],"uniqlo.com":["/products/","/product/"],"zara.com":["-p","/product/"],"bershka.com":["-c0p","-p"],"stradivarius.com":["-c0p","-p"],"spartoo.com":["-p","-x","product"],"snipes.com":["/p/","/product","-"],"celio.com":["/p/","product"],"courir.com":["/product","-"],"decathlon.fr":["/p/","product"],"laredoute.fr":["/ppdp/","product"],"zalando.fr":[".html","/p/"]}
    for pat in patterns.get(source["domain"],[]):
        if pat in u:score+=5
    if any(k in u for k in ["product","produit","prd","article"]):score+=3
    if u.endswith(".xml") or "sitemap" in u:score+=2
    if any(k in u for k in ["login","help","aide","privacy","cookie","store","magasin","career","careers"]):score-=8
    return score

def extract_xml_links(text,base):
    return [u for u in (clean_url(loc,base) for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>",text,re.I|re.S)) if u]

def crawl(source):
    products={}; q=deque((u,0) for u in source["seeds"]); seen=set(); errors=[]; fetched=0
    while q and fetched<MAX_PAGES_PER_SOURCE and len(products)<MAX_PER_SOURCE:
        url,depth=q.popleft()
        if url in seen:continue
        seen.add(url)
        if not same_domain(url,source["domain"]):continue
        try:text,ct=fetch(url); fetched+=1; time.sleep(SLEEP)
        except Exception as e:
            errors.append(f"{url}: {type(e).__name__}"); continue
        if "xml" in ct or url.lower().endswith(".xml"):
            links=sorted(set(extract_xml_links(text,url)),key=lambda x:candidate_score(x,source),reverse=True)
            for v in links[:80]:
                if v not in seen:q.append((v,depth+1))
            continue
        nodes,links,meta=parse_jsonld(text)
        for n in nodes:
            p=normalize(n,url,source)
            if p and same_domain(p["url"],source["domain"]):products[p["url"]]=p
            if len(products)>=MAX_PER_SOURCE:break
        if len(products)<MAX_PER_SOURCE:
            p=normalize_meta(meta,url,source)
            if p and same_domain(p["url"],source["domain"]):products[p["url"]]=p
        if len(products)>=MAX_PER_SOURCE:break
        if depth<2:
            resolved=[]
            for href in links:
                v=clean_url(href,url)
                if v and same_domain(v,source["domain"]) and v not in seen:resolved.append(v)
            resolved=sorted(set(resolved),key=lambda x:candidate_score(x,source),reverse=True)
            for v in resolved[:55 if depth==0 else 30]:q.append((v,depth+1))
    return list(products.values()),{"fetched_pages":fetched,"errors":errors[:8]}

def main():
    try:
        with open("products.json","r",encoding="utf-8") as f:existing=json.load(f)
        if not isinstance(existing,list):existing=[]
    except:existing=[]
    merged={p.get("url"):p for p in existing if isinstance(p,dict) and p.get("url")}; counts=defaultdict(int)
    for p in merged.values():counts[p.get("store","Existing")]+=1
    diagnostics={}
    for s in SOURCES:
        print(f"[{s['store']}] crawl…",flush=True); items,diag=crawl(s); diagnostics[s["store"]]=diag
        for p in items:merged[p["url"]]=p
        counts[s["store"]]=len(items); print(f"[{s['store']}] {len(items)} products from {diag['fetched_pages']} pages",flush=True)
    products=list(merged.values()); products.sort(key=lambda p:(p.get("store",""),p.get("type",""),p.get("name","")))
    with open("products.json","w",encoding="utf-8") as f:json.dump(products,f,ensure_ascii=False,indent=2)
    successful=[k for k,v in counts.items() if v>0]
    meta={"source":"ASOS + import public multi-marchands (0 €)","updated_at":datetime.now(timezone.utc).isoformat(),"count":len(products),"providers_tried":["ASOS"]+[s["store"] for s in SOURCES],"providers_with_products":successful,"provider_counts":dict(counts),"diagnostics":diagnostics,"note":"Best effort: aucune clé API, aucun compte, aucune image inventée. Les sources qui bloquent les requêtes sont ignorées."}
    with open("products-meta.json","w",encoding="utf-8") as f:json.dump(meta,f,ensure_ascii=False,indent=2)
    print(json.dumps({"total":len(products),"providers":dict(counts)},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
