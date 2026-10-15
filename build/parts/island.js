/* ================= ISLAND MAP =================
   The coastline is generated, not drawn. Every organisation contributes a
   smooth bump to a scalar field; marching squares traces the contour where
   that field crosses a threshold. So the land takes its shape from where the
   organisations actually are - a crowded province is genuinely wider, and a
   thinly-staffed one is genuinely a narrow spit.                            */
const SVGNS="http://www.w3.org/2000/svg";
const VW=1520, VH=1060;
const SPACING=30;   // distance between neighbouring organisations
const INF=66;       // how far one organisation's influence reaches
const SEA=0.40;     // field value at the waterline
const BR=13;        // organisation marker radius

const mk=(n,a)=>{const e=document.createElementNS(SVGNS,n);
  for(const k in a) e.setAttribute(k,a[k]); return e};
const rnd=s=>{const x=Math.sin(s*12.9898)*43758.5453; return x-Math.floor(x)};

/* Provinces: one per sub-category. `at` is hand-placed so the island reads
   west-to-east along the defence chain; `lab` is the direction the place name
   sits from the centre of its cluster. */
const PROV=[
 {cat:"Prevention", sub:"",                              name:"Treaty Cape",          at:[280,260], lab:[0,-1]},
 {cat:"Prevention", sub:"Preventing production & release",name:"Containment Coast",   at:[460,390], lab:[-1,0]},
 {cat:"Prevention", sub:"Controlling knowledge",          name:"Infohazard Bluff",    at:[255,500], lab:[-0.7,0.7]},
 {cat:"Detection",  sub:"Early warning",                  name:"Sentinel Watch",      at:[620,268], lab:[0,-1]},
 {cat:"Detection",  sub:"Diagnostics",                    name:"Assay Point",         at:[726,330], lab:[1,-0.4]},
 {cat:"Detection",  sub:"",                               name:"The Narrows",         at:[641,410], lab:[0,1]},
 {cat:"Response",   sub:"",                               name:"Readiness Plain",     at:[1180,240],lab:[0,-1]},
 {cat:"Response",   sub:"Medical countermeasures",        name:"Countermeasure Basin",at:[1010,460],lab:[1,0]},
 {cat:"Response",   sub:"Non-medical countermeasures",    name:"Clean Air Commons",   at:[820,478], lab:[-0.6,-0.8]},
 {cat:"Transversal",sub:"Education",                      name:"Fellows' Field",      at:[400,680], lab:[-1,0]},
 {cat:"Transversal",sub:"Information",                    name:"Signal Shore",        at:[680,790], lab:[0,1]},
 {cat:"Transversal",sub:"Financing",                      name:"Funders' Harbour",    at:[950,770], lab:[0,1]},
 {cat:"Transversal",sub:"Coordination",                   name:"Concord Table",       at:[1180,720],lab:[1,0.3]}
];
const CATMETA={
  Prevention:{v:"--prev", label:"PREVENTION", gloss:"stop it being made",      at:[360,180], size:38},
  Detection:{ v:"--det",  label:"DETECTION",  gloss:"catch it early",          at:[660,196], size:26},
  Response:{  v:"--resp", label:"RESPONSE",   gloss:"blunt it once it spreads",at:[1080,352],size:44},
  Transversal:{v:"--trans",label:"FOUNDATION",gloss:"what holds the rest up",  at:[740,930], size:40}
};

let islandBuilt=false, cam={k:1,x:0,y:0}, camG=null, PLACED=[];

/* ---- scalar field ---------------------------------------------------- */
function buildField(points, cell){
  const gw=Math.ceil(VW/cell)+1, gh=Math.ceil(VH/cell)+1;
  const val=new Float32Array(gw*gh);
  const r2=INF*INF;
  points.forEach(p=>{
    const i0=Math.max(0,Math.floor((p[0]-INF)/cell)), i1=Math.min(gw-1,Math.ceil((p[0]+INF)/cell));
    const j0=Math.max(0,Math.floor((p[1]-INF)/cell)), j1=Math.min(gh-1,Math.ceil((p[1]+INF)/cell));
    for(let j=j0;j<=j1;j++) for(let i=i0;i<=i1;i++){
      const dx=i*cell-p[0], dy=j*cell-p[1], d2=dx*dx+dy*dy;
      if(d2>=r2) continue;
      const t=1-d2/r2;            // smooth bump, 1 at the centre, 0 at INF
      val[j*gw+i]+=t*t;
    }
  });
  return {val:val, gw:gw, gh:gh, cell:cell};
}
function sample(F,x,y){
  const i=Math.round(x/F.cell), j=Math.round(y/F.cell);
  if(i<0||j<0||i>=F.gw||j>=F.gh) return 0;
  return F.val[j*F.gw+i];
}

/* ---- marching squares ------------------------------------------------ */
function contour(F,T){
  const segs=[], c=F.cell, gw=F.gw, v=F.val;
  const lerp=(p,q,a,b)=>{const t=(T-a)/(b-a); return [p[0]+(q[0]-p[0])*t, p[1]+(q[1]-p[1])*t]};
  for(let j=0;j<F.gh-1;j++) for(let i=0;i<gw-1;i++){
    const a=v[j*gw+i], b=v[j*gw+i+1], d=v[(j+1)*gw+i+1], e=v[(j+1)*gw+i];
    const idx=(a>T?8:0)|(b>T?4:0)|(d>T?2:0)|(e>T?1:0);
    if(idx===0||idx===15) continue;
    const x0=i*c, y0=j*c, x1=x0+c, y1=y0+c;
    const TL=[x0,y0], TR=[x1,y0], BR_=[x1,y1], BL=[x0,y1];
    const top=()=>lerp(TL,TR,a,b), right=()=>lerp(TR,BR_,b,d),
          bot=()=>lerp(BL,BR_,e,d), left=()=>lerp(TL,BL,a,e);
    switch(idx){
      case 1:  segs.push([left(),bot()]); break;
      case 2:  segs.push([bot(),right()]); break;
      case 3:  segs.push([left(),right()]); break;
      case 4:  segs.push([right(),top()]); break;
      case 5:  segs.push([left(),top()]); segs.push([bot(),right()]); break;
      case 6:  segs.push([bot(),top()]); break;
      case 7:  segs.push([left(),top()]); break;
      case 8:  segs.push([top(),left()]); break;
      case 9:  segs.push([top(),bot()]); break;
      case 10: segs.push([top(),right()]); segs.push([left(),bot()]); break;
      case 11: segs.push([top(),right()]); break;
      case 12: segs.push([right(),left()]); break;
      case 13: segs.push([right(),bot()]); break;
      case 14: segs.push([bot(),left()]); break;
    }
  }
  // join the loose segments into closed rings
  const K=p=>Math.round(p[0]*2)+","+Math.round(p[1]*2);
  const byStart=new Map();
  segs.forEach((s,i)=>{
    const k=K(s[0]);
    if(!byStart.has(k)) byStart.set(k,[]);
    byStart.get(k).push(i);
  });
  const used=new Array(segs.length).fill(false), rings=[];
  for(let i=0;i<segs.length;i++){
    if(used[i]) continue;
    used[i]=true;
    const pts=[segs[i][0],segs[i][1]];
    for(let guard=0; guard<60000; guard++){
      const cand=(byStart.get(K(pts[pts.length-1]))||[]).filter(j=>!used[j]);
      if(!cand.length) break;
      const j=cand[0]; used[j]=true;
      pts.push(segs[j][1]);
      if(K(pts[pts.length-1])===K(pts[0])) break;
    }
    if(pts.length>8) rings.push(pts);
  }
  return rings;
}
function chaikin(pts,iters){
  for(let n=0;n<iters;n++){
    const out=[];
    for(let i=0;i<pts.length;i++){
      const p=pts[i], q=pts[(i+1)%pts.length];
      out.push([p[0]*.75+q[0]*.25, p[1]*.75+q[1]*.25]);
      out.push([p[0]*.25+q[0]*.75, p[1]*.25+q[1]*.75]);
    }
    pts=out;
  }
  return pts;
}
const ringPath=r=>"M"+chaikin(r,2).map(p=>p[0].toFixed(1)+" "+p[1].toFixed(1)).join("L")+"Z";
const ringsPath=rs=>rs.map(ringPath).join(" ");

/* ---- layout ---------------------------------------------------------- */
function layout(){
  PLACED=[];
  PROV.forEach((pv,pi)=>{
    const members=ORGS.filter(o=>o.cat===pv.cat && (o.sub||"")===pv.sub);
    pv.n=members.length;
    // phyllotaxis: even, organic-looking packing with no overlaps
    members.forEach((o,i)=>{
      const r=SPACING*Math.sqrt(i+0.55), th=i*2.399963;
      const x=pv.at[0]+r*Math.cos(th)+(rnd(o.id)-0.5)*7;
      const y=pv.at[1]+r*Math.sin(th)+(rnd(o.id+31)-0.5)*7;
      PLACED.push({o:o,x:x,y:y,prov:pi});
    });
    pv.r=SPACING*Math.sqrt(Math.max(members.length,1))+10;
  });
}

/* ---- draw ------------------------------------------------------------ */
function buildIsland(){
  const svg=$("atlas");
  svg.textContent="";
  const defs=mk("defs",{}); svg.appendChild(defs);
  camG=mk("g",{id:"cam"}); svg.appendChild(camG);

  layout();
  const pts=PLACED.map(p=>[p.x,p.y]);
  const F=buildField(pts,6);

  svg.appendChild(mk("rect",{x:0,y:0,width:VW,height:VH,fill:"var(--sea)"}));
  svg.insertBefore(svg.lastChild,camG);   // sea sits behind the camera group

  // bathymetric rings out to sea, then the coast, then the highlands
  [0.12,0.20,0.30].forEach(t=>{
    camG.appendChild(mk("path",{d:ringsPath(contour(F,SEA*t)),class:"sea-c"}));
  });
  const coast=contour(F,SEA);
  const landD=ringsPath(coast);
  camG.appendChild(mk("path",{d:landD,class:"land"}));
  camG.appendChild(mk("path",{d:ringsPath(contour(F,SEA*1.55)),class:"beach"}));
  camG.appendChild(mk("path",{d:ringsPath(contour(F,SEA*3.2)),class:"high"}));

  // clip everything that follows to the land itself
  const clip=mk("clipPath",{id:"landclip"});
  clip.appendChild(mk("path",{d:landD}));
  defs.appendChild(clip);
  const onLand=mk("g",{"clip-path":"url(#landclip)",class:"terr"});
  camG.appendChild(onLand);

  // province tint: a soft wash of the category colour over its own territory
  PROV.forEach((pv,i)=>{
    if(!pv.n) return;
    const gid="g"+i, v=CATMETA[pv.cat].v;
    const g=mk("radialGradient",{id:gid});
    g.appendChild(mk("stop",{offset:"0%","stop-color":"var("+v+")","stop-opacity":".55"}));
    g.appendChild(mk("stop",{offset:"100%","stop-color":"var("+v+")","stop-opacity":"0"}));
    defs.appendChild(g);
    onLand.appendChild(mk("circle",{cx:pv.at[0],cy:pv.at[1],r:pv.r+70,fill:"url(#"+gid+")"}));
  });

  // terrain glyphs, only where there is land and no organisation nearby
  const glyphs=mk("g",{class:"glyph"});
  let seed=0;
  for(let y=90;y<VH-70;y+=34) for(let x=90;x<VW-70;x+=34){
    seed++;
    if(sample(F,x,y)<SEA*1.9) continue;
    if(rnd(seed*7.3)>0.34) continue;
    let near=false;
    for(let i=0;i<pts.length;i++){
      const dx=pts[i][0]-x, dy=pts[i][1]-y;
      if(dx*dx+dy*dy < 40*40){ near=true; break }
    }
    if(near) continue;
    const jx=x+(rnd(seed)-0.5)*14, jy=y+(rnd(seed+5)-0.5)*14;
    if(rnd(seed*3.1)<0.5){          // hill
      glyphs.appendChild(mk("path",{d:"M"+(jx-9)+" "+(jy+5)+"L"+jx+" "+(jy-7)+
        "L"+(jx+9)+" "+(jy+5)+"Z"}));
    }else{                          // conifer
      glyphs.appendChild(mk("path",{d:"M"+jx+" "+(jy-8)+"L"+(jx+5)+" "+(jy+4)+
        "L"+(jx-5)+" "+(jy+4)+"Z"}));
      glyphs.appendChild(mk("rect",{x:jx-1,y:jy+4,width:2,height:3}));
    }
  }
  onLand.appendChild(glyphs);

  // large, faint province-group names, sitting under everything else
  Object.keys(CATMETA).forEach(k=>{
    const m=CATMETA[k];
    const t=mk("text",{x:m.at[0],y:m.at[1],class:"catlab","text-anchor":"middle",
      "font-size":m.size,fill:"var("+m.v+")"});
    t.textContent=m.label; camG.appendChild(t);
    const s=mk("text",{x:m.at[0],y:m.at[1]+m.size*0.62,class:"catsub","text-anchor":"middle",
      fill:"var("+m.v+")"});
    s.textContent=m.gloss; camG.appendChild(s);
  });

  // the open sea to the north-west, and the threat arriving from it
  const sl=mk("text",{x:170,y:830,class:"sealab",transform:"rotate(-24 170 830)"});
  sl.textContent="THE OPEN SEA"; camG.appendChild(sl);
  camG.appendChild(mk("path",{class:"threat-line",d:"M96 168 L232 286"}));
  camG.appendChild(mk("path",{class:"threat-line","stroke-dasharray":"none",
    d:"M210 268 L236 290 L206 296"}));
  const tl=mk("text",{class:"threat",transform:"translate(104,150) rotate(41)"});
  tl.textContent="A threat makes landfall"; camG.appendChild(tl);

  // compass rose
  const rx=1400, ry=940;
  camG.appendChild(mk("circle",{cx:rx,cy:ry,r:26,class:"rose"}));
  camG.appendChild(mk("path",{class:"rose",d:"M"+rx+" "+(ry-34)+"L"+(rx+8)+" "+ry+
    "L"+rx+" "+(ry+34)+"L"+(rx-8)+" "+ry+"Z"}));
  camG.appendChild(mk("path",{class:"rose",d:"M"+(rx-34)+" "+ry+"L"+rx+" "+(ry-8)+
    "L"+(rx+34)+" "+ry+"L"+rx+" "+(ry+8)+"Z"}));
  const nn=mk("text",{x:rx,y:ry-40,class:"rose-n"}); nn.textContent="N";
  camG.appendChild(nn);

  // organisation markers
  const nodesG=mk("g",{});
  PLACED.forEach(p=>nodesG.appendChild(node(p.o,p.x,p.y)));
  camG.appendChild(nodesG);

  // province names, offset clear of their own cluster
  PROV.forEach(pv=>{
    if(!pv.n) return;
    const d=Math.hypot(pv.lab[0],pv.lab[1])||1;
    const lx=pv.at[0]+pv.lab[0]/d*(pv.r+26), ly=pv.at[1]+pv.lab[1]/d*(pv.r+26);
    const t=mk("text",{x:lx.toFixed(0),y:ly.toFixed(0),class:"plab"});
    t.textContent=pv.name; camG.appendChild(t);
    const c=mk("text",{x:lx.toFixed(0),y:(ly+13).toFixed(0),class:"pnum"});
    c.textContent=pv.n+(pv.n===1?" ORG":" ORGS"); camG.appendChild(c);
  });

  islandBuilt=true;
  applyCam();
}

function node(o,x,y){
  const g=mk("g",{class:"node","data-id":o.id,tabindex:"0",role:"button",
    style:"--nc:"+colorOf(o.cat),
    "data-tip":"<b>"+esc(o.name)+"</b><br>"+esc(layerName(o.cat))+
      (o.sub?" &middot; "+esc(o.sub):"")});
  const ttl=mk("title",{}); ttl.textContent=o.name; g.appendChild(ttl);
  g.appendChild(mk("circle",{cx:x.toFixed(1),cy:y.toFixed(1),r:BR,class:"halo"}));
  const src=LOGOS[o.dom];
  if(src){
    g.appendChild(mk("image",{href:src,x:(x-9).toFixed(1),y:(y-9).toFixed(1),
      width:18,height:18,preserveAspectRatio:"xMidYMid meet"}));
  }else{
    g.appendChild(mk("circle",{cx:x.toFixed(1),cy:y.toFixed(1),r:BR-1.3,
      fill:colorOf(o.cat),opacity:".92"}));
    const t=mk("text",{x:x.toFixed(1),y:(y+3.2).toFixed(1),class:"mono"});
    t.textContent=initials(o.name); g.appendChild(t);
  }
  if(o.gcbr) g.appendChild(mk("circle",{cx:(x+BR-3).toFixed(1),cy:(y-BR+3).toFixed(1),
    r:2.8,class:"gdot"}));
  return g;
}
function paintIsland(){
  if(!islandBuilt) return;
  const f=filtering();
  $("atlas").querySelectorAll(".node").forEach(n=>{
    n.classList.toggle("dim", f && !match(byId[+n.getAttribute("data-id")]));
  });
}
function applyCam(){
  if(camG) camG.setAttribute("transform",
    "translate("+cam.x.toFixed(2)+","+cam.y.toFixed(2)+") scale("+cam.k.toFixed(3)+")");
}
function zoomAt(factor,px,py){
  const k=Math.max(.6,Math.min(6,cam.k*factor)), s=k/cam.k;
  cam.x=px-(px-cam.x)*s; cam.y=py-(py-cam.y)*s; cam.k=k;
  applyCam();
}
function svgPoint(ev){
  const svg=$("atlas"), r=svg.getBoundingClientRect(), vb=svg.viewBox.baseVal;
  return [(ev.clientX-r.left)/r.width*vb.width,(ev.clientY-r.top)/r.height*vb.height];
}
function wireAtlas(){
  const svg=$("atlas");
  svg.addEventListener("wheel",e=>{
    e.preventDefault();
    const p=svgPoint(e);
    zoomAt(e.deltaY<0?1.14:1/1.14,p[0],p[1]);
  },{passive:false});
  let drag=null;
  svg.addEventListener("pointerdown",e=>{
    drag={x:e.clientX,y:e.clientY,cx:cam.x,cy:cam.y,moved:false};
    svg.classList.add("drag");
    try{svg.setPointerCapture(e.pointerId)}catch(_){}
  });
  svg.addEventListener("pointermove",e=>{
    if(!drag) return;
    const r=svg.getBoundingClientRect(), vb=svg.viewBox.baseVal;
    const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
    if(Math.abs(dx)+Math.abs(dy)>3) drag.moved=true;
    cam.x=drag.cx+dx/r.width*vb.width;
    cam.y=drag.cy+dy/r.height*vb.height;
    applyCam();
  });
  const stop=()=>{
    if(drag) svg.dataset.moved=drag.moved?"1":"0";
    drag=null; svg.classList.remove("drag");
  };
  svg.addEventListener("pointerup",stop);
  svg.addEventListener("pointercancel",stop);
  $("zIn").onclick=()=>zoomAt(1.3,VW/2,VH/2);
  $("zOut").onclick=()=>zoomAt(1/1.3,VW/2,VH/2);
  $("zRe").onclick=()=>{cam={k:1,x:0,y:0}; applyCam()};
  svg.addEventListener("keydown",e=>{
    const n=e.target.closest && e.target.closest(".node");
    if(n && (e.key==="Enter"||e.key===" ")){e.preventDefault(); openOrg(n.getAttribute("data-id"))}
  });
}
function renderKey(){
  const order=["Prevention","Detection","Response","Transversal"];
  const blurb={
    Prevention:"The western shore, where a threat makes landfall. Stopping an agent being made or released at all.",
    Detection:"The narrows. Spotting an outbreak while containing it is still cheap.",
    Response:"The eastern interior. Blunting an outbreak already spreading.",
    Transversal:"The southern plain. Funders, teachers, coordinators and reporters — not a stage, but what the rest stands on."
  };
  const html=order.map(k=>{
    const n=ORGS.filter(o=>o.cat===k).length;
    const provs=PROV.filter(p=>p.cat===k && p.n).map(p=>p.name).join(" · ");
    return '<div class="kitem"><span class="sw" style="background:var('+CATMETA[k].v+
      ')"></span><div><div class="kt">'+esc(CATMETA[k].label.charAt(0)+
      CATMETA[k].label.slice(1).toLowerCase())+'</div>'+
      '<div class="kd"><b>'+n+' orgs</b> &middot; '+esc(blurb[k])+
      '<br><span style="opacity:.8">'+esc(provs)+'</span></div></div></div>';
  }).join("");
  const det=ORGS.filter(o=>o.cat==="Detection").length;
  const res=ORGS.filter(o=>o.cat==="Response").length;
  $("atlasKey").innerHTML=html+
    '<div class="keynote">The coastline is generated from the organisations themselves, so '+
    'area means something: <b>Detection</b> is a narrow isthmus because only <b>'+det+
    '</b> organisations hold it, against <b>'+res+'</b> in the Response interior. It is the '+
    'cheapest place to stop a pandemic and the thinnest stretch of the map. A small coloured '+
    'dot marks work on worst-case pandemic risk. Position <em>within</em> a province carries '+
    'no meaning.</div>';
}
