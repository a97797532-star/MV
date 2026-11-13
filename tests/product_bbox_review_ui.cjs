// 한글 안내: 브라우저 검수 UI 또는 그 회귀 테스트입니다. 응답·좌표·로딩 오류와 사람의 명시적 확인을 구분합니다.
// Node VM tests simulate DOM/image events; these are NOT a real browser test.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {parseBBox,fetchJSON}=require('../scripts/product_bbox_review.js');
const code=fs.readFileSync('scripts/product_bbox_review.js','utf8');let checks=0;
// check: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
function check(v){assert.ok(v);checks++;}
const tick=()=>new Promise(r=>setTimeout(r,0));
// settle: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
async function settle(){for(let i=0;i<12;i++)await tick();}
// boot: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
function boot(mode='good'){
 const elements={},draws=[],requests=[];let serial=0,firstResolve;
 for(const id of ['c','approve','who','ack','reReview','previous','next','restore','retry','pending','reject','progress','progressText','counter','info','reviewState','reReviewLabel','coordinates','loading','message','error'])elements[id]={value:'',checked:false,disabled:false,hidden:false,textContent:'',events:{},addEventListener(name,handler){this.events[name]=handler;}};
 const ctx={clearRect(){},drawImage(){draws.push('image');},strokeRect(...v){draws.push(v);},setLineDash(){}};
 Object.assign(elements.c,{width:1024,height:1024,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:512,height:512}),setPointerCapture(){}});
 const item=n=>({total:600,category:n?'new-category':'audiojack',view:'C1',status:'NG',product_id:'synthetic/product',case_id:'synthetic'+n,proposal_bbox:'[132, 244, 896, 732]',review_state:'PROPOSAL',image_token:'token'+n,review_revision:'0',source_sha256:'synthetic',progress:{total:600,verified:0,remaining:600,states:{PENDING:0,REJECTED:0}}});
 const fetch=async(url,opts={})=>{
  requests.push(url);
  if(url.startsWith('/item/')){
   const n=serial++;
   if(mode==='race'&&n===0)return new Promise(resolve=>{firstResolve=()=>resolve({ok:true,status:200,text:async()=>JSON.stringify(item(0))});});
   return {ok:true,status:200,text:async()=>mode==='badjson'?'{"reviewer":NaN}':JSON.stringify(item(n))};
  }
  if(url.startsWith('/image/'))return {ok:mode!=='httpimage',status:mode==='httpimage'?404:200,headers:{get:()=>url.includes('token1')?'token1':'token0'},blob:async()=>new Blob(['fake-image'])};
  throw new Error('Unexpected endpoint '+url);
 };
 class FakeImage{constructor(){this.naturalWidth=1024;this.naturalHeight=1024;}set src(v){queueMicrotask(()=>mode==='badimage'?this.onerror():this.onload());}}
 const sandbox={document:{getElementById:id=>elements[id]},fetch,Image:FakeImage,URL:{createObjectURL:()=> 'blob:synthetic',revokeObjectURL(){}},AbortController,setTimeout,clearTimeout,console,window:{prompt:()=>null},Blob};
 vm.runInNewContext(code,sandbox,{filename:'product_bbox_review.js'});
 return {elements,draws,requests,releaseFirst:()=>firstResolve()};
}
(async()=>{
 assert.deepEqual(parseBBox('[132,244,896,732]'),[132,244,896,732]);checks++;
 assert.deepEqual(parseBBox([1,2,3,4]),[1,2,3,4]);checks++;
 for(const bad of [null,'[0,0,NaN,20]',[0,0,Infinity,5],[1,1,1,5],[0,0,1025,5]]){assert.throws(()=>parseBBox(bad));checks++;}
 const original=global.fetch;
 global.fetch=async()=>({ok:false,status:404,text:async()=>'{"error":"missing"}'});await assert.rejects(fetchJSON('/'),/HTTP 404/);checks++;
 global.fetch=async()=>({ok:true,status:200,text:async()=>'{"reviewer":NaN}'});await assert.rejects(fetchJSON('/'),/JSON/);checks++;global.fetch=original;
 const b=boot();check(b.elements.approve.disabled);await settle();check(b.elements.counter.textContent==='1 / 600');check(b.elements.info.textContent.includes('audiojack'));check(b.draws.includes('image'));check(b.draws.some(x=>Array.isArray(x)&&x.join(',')==='132,244,764,488'));check(b.elements.approve.disabled);
 b.elements.who.value='tester';b.elements.who.events.input();b.elements.ack.checked=true;b.elements.ack.events.input();check(!b.elements.approve.disabled);
 b.elements.c.events.pointerdown({clientX:50,clientY:60,pointerId:1});b.elements.c.events.pointermove({clientX:200,clientY:220});b.elements.c.events.pointerup();check(b.elements.coordinates.textContent.includes('100.0, 120.0, 400.0, 440.0'));check(b.elements.approve.disabled);b.elements.restore.events.click();check(b.elements.coordinates.textContent.includes('132.0, 244.0, 896.0, 732.0'));
 for(const mode of ['badjson','badimage','httpimage']){const x=boot(mode);await settle();check(x.elements.approve.disabled);check(x.elements.error.textContent.length>0);check(x.elements.loading.textContent.includes('실패'));}
 const race=boot('race');race.elements.retry.events.click();await settle();check(race.elements.info.textContent.includes('new-category'));race.releaseFirst();await settle();check(race.elements.info.textContent.includes('new-category'));check(!race.elements.info.textContent.includes('audiojack'));
 console.log(JSON.stringify({checks,passed:true,scope:'Node DOM/image simulation; real browser UNVERIFIED'}));
})().catch(e=>{console.error(e);process.exitCode=1;});
