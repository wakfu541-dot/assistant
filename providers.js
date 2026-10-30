(()=>{'use strict';
const MAP={
  'ASOS':{domain:'asos.com',url:'https://www.asos.com/fr/'},
  'Gap':{domain:'gap-france.fr',url:'https://www.gap-france.fr/'},
  'Promod':{domain:'promod.fr',url:'https://www.promod.fr/'},
  'Nike':{domain:'nike.com',url:'https://www.nike.com/fr/'},
  'SNIPES':{domain:'snipes.com',url:'https://www.snipes.com/fr-fr/'},
  'Courir':{domain:'courir.com',url:'https://www.courir.com/fr/'},
  'Foot Locker':{domain:'footlocker.fr',url:'https://www.footlocker.fr/'},
  'Spartoo':{domain:'spartoo.com',url:'https://www.spartoo.com/'},
  'Bonprix':{domain:'bonprix.fr',url:'https://www.bonprix.fr/'},
  'C&A':{domain:'c-and-a.com',url:'https://www.c-and-a.com/fr/fr/shop'},
  'Jules':{domain:'jules.com',url:'https://www.jules.com/fr-fr/'},
  'BSTN':{domain:'bstn.com',url:'https://www.bstn.com/eu_fr/'},
  'Size?':{domain:'sizeofficial.fr',url:'https://www.sizeofficial.fr/'},
  'boohooMAN':{domain:'boohooman.com',url:'https://www.boohooman.com/fr/'},
  'Boohoo':{domain:'boohoo.com',url:'https://fr.boohoo.com/'},
  'Celio':{domain:'celio.com',url:'https://www.celio.com/'},
  'Decathlon':{domain:'decathlon.fr',url:'https://www.decathlon.fr/'},
  'La Redoute':{domain:'laredoute.fr',url:'https://www.laredoute.fr/'},
  'Zalando':{domain:'zalando.fr',url:'https://www.zalando.fr/'}
};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const initials=name=>name.split(/\s+/).map(x=>x[0]).join('').replace(/[^A-Z0-9?&]/gi,'').slice(0,3).toUpperCase()||'?';
async function render(){
  const list=document.getElementById('providers-list'),title=document.getElementById('providers-title'),count=document.getElementById('providers-count');
  if(!list||!title||!count)return;
  try{
    const r=await fetch('products.json?v='+Date.now(),{cache:'no-store'}); if(!r.ok)throw new Error('catalogue');
    const products=await r.json(); const counts={};
    for(const p of products){const s=(p.store||'').trim();if(s)counts[s]=(counts[s]||0)+1;}
    const providers=Object.entries(counts).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'fr'));
    if(!providers.length)throw new Error('empty');
    title.textContent=`${providers.length} fournisseur${providers.length>1?'s':''} réellement actif${providers.length>1?'s':''}`;
    count.textContent=String(providers.length);
    list.classList.add('provider-cards');
    list.innerHTML=providers.map(([name,n])=>{
      const m=MAP[name]||{}; const domain=m.domain||''; const href=m.url||'#';
      const logo=domain?`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128`:'';
      return `<a class="provider-card" href="${esc(href)}" ${href==='#'?'':'target="_blank" rel="noopener noreferrer"'} aria-label="${esc(name)} — ${n} produits"><span class="provider-logo-wrap"><span class="provider-fallback">${esc(initials(name))}</span>${logo?`<img class="provider-logo" src="${esc(logo)}" alt="Logo ${esc(name)}" loading="lazy">`:''}</span><span class="provider-card-text"><strong>${esc(name)}</strong><span>${n.toLocaleString('fr-FR')} produit${n>1?'s':''}</span></span><span class="provider-active"><i></i>Actif</span></a>`;
    }).join('');
    list.querySelectorAll('.provider-logo').forEach(img=>{img.addEventListener('error',()=>{img.style.display='none'},{once:true})});
  }catch(e){
    list.classList.remove('provider-cards');
  }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',render);else render();
})();