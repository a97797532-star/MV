// 한글 안내: 브라우저 검수 UI 또는 그 회귀 테스트입니다. 응답·좌표·로딩 오류와 사람의 명시적 확인을 구분합니다.
// Simulated DOM, not an actual browser. No real approval API or files are used.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const code=fs.readFileSync('scripts/crop_range_review.js','utf8');const elements={},draws=[],requests=[];let checks=0;
// check: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
function check(value){assert.ok(value);checks++;}
for(const id of ['c','approve','who','ack','reReview','previous','next','restore','retry','pending','reject','progress','progressText','counter','info','reviewState','reReviewLabel','coordinates','loading','message','error','preview','previewStatus','riskAck','riskAckLabel','keepFull','square','maskVisible','export','exportResult','jump','jumpTo','nextPending','gtCrop'])elements[id]={value:'',checked:false,disabled:false,textContent:'',hidden:false,events:{},addEventListener(k,f){this.events[k]=f;},click(){this.events.click?.();}};
elements.square.checked=true;
const ctx={clearRect(){},drawImage(){draws.push('image');},strokeRect(...r){draws.push(r);},setLineDash(){}};Object.assign(elements.c,{width:1024,height:1024,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:512,height:512}),setPointerCapture(){}});
const progress={total:1757,verified:0,remaining:1757,states:{PENDING:0,REJECTED:0}};
const item={case_id:'fake',category:'synthetic',view:'C1',status:'CROP_REVIEW_REQUIRED',split:'validation',product_id:'synthetic/product',total:1757,review_state:'PROPOSAL',current_crop:'[0,0,1024,1024]',proposal_bbox:'[100,100,900,900]',approved_bbox:[0,0,1024,1024],reference_product_bbox:process.env.CROP_UI_GT_TEST?'[100,100,900,900]':'',mask_available:false,review_reasons:'SIMULATION_ONLY',proposal_method:'NO_AUTO_PROPOSAL',progress,image_token:'fake',source_sha256:'fake',review_revision:'0'};
// fetch: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
async function fetch(url,options={}){
 requests.push(url);let result;
 if(url.startsWith('/item/'))result=item;
 else if(url.startsWith('/image/'))return {ok:true,status:200,headers:{get:()=> 'fake'},blob:async()=>new Blob(['fake'])};
 else if(url==='/preview_crop'){result={product:{status:'UNVERIFIED',area_recall:null},defect_mask:{status:'NOT_PROVIDED',retention:null},preview_receipt:'fake-preview',requires_risk_ack:true,observed_loss:false,area_equivalent_gain:1,annotation_assisted:false,review_split:'validation'};}
 else if(url==='/export')result={path:'/temporary/preprocessing_metadata_reviewed_v1.csv',rows:151050,human_approved_rows:0};
 else throw new Error('Unexpected endpoint '+url);
 return {ok:true,status:200,text:async()=>JSON.stringify(result)};
}
class FakeImage{constructor(){this.naturalWidth=1024;this.naturalHeight=1024;}set src(v){queueMicrotask(()=>this.onload());}}
vm.runInNewContext(code,{document:{getElementById:id=>elements[id]},fetch,Image:FakeImage,URL:{createObjectURL:()=> 'blob:fake',revokeObjectURL(){}},Blob,AbortController,setTimeout,clearTimeout,console,window:{prompt:()=>null}});
const settle=async()=>{for(let i=0;i<12;i++)await new Promise(r=>setTimeout(r,0));};
(async()=>{
 check(elements.approve.disabled);await settle();check(elements.counter.textContent==='1 / 1757');check(draws.includes('image'));check(elements.info.textContent.includes('SIMULATION_ONLY'));check(!elements.preview.disabled);if(process.env.CROP_UI_GT_TEST){check(elements.coordinates.textContent.includes('19.0, 19.0, 981.0, 981.0'));check(requests.includes('/preview_crop'));}
 elements.who.value='tester';elements.who.events.input();elements.ack.checked=true;elements.ack.events.input();check(elements.approve.disabled);
 elements.preview.events.click();await settle();check(elements.previewStatus.textContent.includes('UNVERIFIED'));check(elements.approve.disabled);elements.riskAck.checked=true;elements.riskAck.events.input();check(!elements.approve.disabled);
 elements.c.events.pointerdown({clientX:50,clientY:60,pointerId:1});elements.c.events.pointermove({clientX:200,clientY:220});elements.c.events.pointerup();check(elements.coordinates.textContent.includes('100.0, 120.0, 420.0, 440.0'));check(elements.approve.disabled);
 elements.keepFull.events.click();check(elements.coordinates.textContent.includes('0.0, 0.0, 1024.0, 1024.0'));check(!elements.ack.checked);
 elements.export.events.click();await settle();check(elements.exportResult.textContent.includes('preprocessing_metadata_reviewed_v1.csv'));check(!requests.includes('/approve'));
 console.log(JSON.stringify({passed:true,checks,actual_browser:'UNVERIFIED',scope:'Crop UI DOM simulation, no real ledger'}));
})().catch(e=>{console.error(e);process.exitCode=1;});
