// 한글 안내: 브라우저 검수 UI 또는 그 회귀 테스트입니다. 응답·좌표·로딩 오류와 사람의 명시적 확인을 구분합니다.
'use strict';
// parseBBox: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
function parseBBox(value, width=1024, height=1024) {
  const b=typeof value==='string'?JSON.parse(value):value;
  if(!Array.isArray(b)||b.length!==4||!b.every(v=>typeof v==='number'&&Number.isFinite(v))||!(0<=b[0]&&b[0]<b[2]&&b[2]<=width&&0<=b[1]&&b[1]<b[3]&&b[3]<=height))throw new Error('BBox 좌표가 올바르지 않습니다. 원본 범위 안의 [x0,y0,x1,y1]이 필요합니다.');
  return [...b];
}
// fetchJSON: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
async function fetchJSON(url,options={}) {
  let response;
  try {response=await fetch(url,options);}catch(e){if(e.name==='AbortError')throw e;throw new Error('서버 응답이 없습니다. 서버 실행 상태와 주소를 확인한 뒤 다시 시도하세요.');}
  const text=await response.text();let data;
  try{data=JSON.parse(text);}catch(e){throw new Error(`JSON 파싱 실패 (HTTP ${response.status}). 서버 로그를 확인하세요.`);}
  if(!response.ok)throw new Error(`HTTP ${response.status}: ${data.error||'요청 실패'}`);
  if(!data||typeof data!=='object'||data.error)throw new Error(data?.error||'서버 JSON 형식 오류');
  return data;
}
if(typeof module!=='undefined')module.exports={parseBBox,fetchJSON};
if(typeof document!=='undefined'){
 const el=id=>document.getElementById(id),c=el('c'),ctx=c.getContext('2d');
 const state={index:0,total:0,row:null,box:null,image:null,ready:false,busy:false,saving:false,sequence:0,controller:null,start:null};
 // error: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function error(message){el('error').textContent=message;}
 // validBox: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function validBox(){try{parseBBox(state.box);return true;}catch{return false;}}
 // controls: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function controls(){
  el('approve').disabled=state.busy||state.saving||!state.ready||!validBox()||el('who').value.trim().length<2||!el('ack').checked||(state.row?.review_state==='VERIFIED_GT'&&!el('reReview').checked);
  el('previous').disabled=state.busy||state.saving||state.index<=0;
  el('next').disabled=state.busy||state.saving||!state.total||state.index>=state.total-1;
  el('restore').disabled=!state.ready||state.saving;el('retry').disabled=state.saving;
  for(const key of ['pending','reject'])el(key).disabled=state.busy||state.saving||!state.ready||el('who').value.trim().length<2;
 }
 // progress: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function progress(p){el('progress').max=p.total;el('progress').value=p.verified;el('progressText').textContent=`승인 완료 ${p.verified} / ${p.total} · 미완료 ${p.remaining} · 보류 ${p.states.PENDING} · 거부 ${p.states.REJECTED}`;}
 // render: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function render(){
  try{
   if(!ctx)throw new Error('이 브라우저에서 Canvas 2D를 사용할 수 없습니다.');
   ctx.clearRect(0,0,c.width,c.height);ctx.drawImage(state.image,0,0,c.width,c.height);
   try{const p=parseBBox(state.row.proposal_bbox);ctx.strokeStyle='#1476ca';ctx.lineWidth=2;ctx.setLineDash([10,7]);ctx.strokeRect(p[0],p[1],p[2]-p[0],p[3]-p[1]);}catch{}
   ctx.setLineDash([]);
   if(validBox()){const b=state.box;ctx.strokeStyle='#00a54f';ctx.lineWidth=3;ctx.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);}
   el('coordinates').textContent=state.box?'BBox XYXY: ['+state.box.map(x=>x.toFixed(1)).join(', ')+']':'BBox가 없습니다. 제품 전체를 드래그하여 지정하세요.';
  }catch(e){state.ready=false;error('Canvas 렌더링 실패: '+e.message);controls();throw e;}
 }
 // decodeImage: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 async function decodeImage(url,signal){
  let response;
  try{response=await fetch(url,{signal});}catch(e){if(e.name==='AbortError')throw e;throw new Error('이미지 서버 연결 실패. 다시 불러오기를 누르세요.');}
  if(!response.ok)throw new Error(`이미지 로딩 실패 (HTTP ${response.status}). 데이터 경로와 파일 권한을 확인하세요.`);
  const receipt=response.headers.get('X-Review-Receipt');if(!receipt)throw new Error('이미지 확인 토큰이 없습니다. 서버를 최신 코드로 재실행하세요.');
  const objectURL=URL.createObjectURL(await response.blob());const image=new Image();
  try{await new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(new Error('이미지 디코딩 시간 초과')),20000);
   image.onload=()=>{clearTimeout(timer);resolve();};
   image.onerror=()=>{clearTimeout(timer);reject(new Error('이미지 디코딩 실패: 손상 파일 또는 브라우저 이미지 형식을 확인하세요.'));};
   image.src=objectURL;
  });return {image,receipt};}finally{URL.revokeObjectURL(objectURL);}
 }
 // load: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 async function load(index=state.index,preserveMessage=false){
  if(state.saving)return;
  const sequence=++state.sequence;state.controller?.abort();const controller=new AbortController();state.controller=controller;
  const timer=setTimeout(()=>controller.abort(),25000);state.index=index;state.busy=true;state.ready=false;state.row=null;state.box=null;state.image=null;state.start=null;
  el('ack').checked=false;el('reReview').checked=false;error('');if(!preserveMessage)el('message').textContent='';el('loading').textContent='항목과 원본 이미지를 불러오는 중…';el('coordinates').textContent='BBox: —';el('info').textContent='';el('reviewState').textContent='로딩 중';
  if(ctx)ctx.clearRect(0,0,c.width,c.height);controls();
  try{
   const row=await fetchJSON('/item/'+index,{signal:controller.signal});if(sequence!==state.sequence)return;
   state.row=row;state.total=row.total;el('counter').textContent=`${index+1} / ${row.total}`;el('info').textContent=`품목: ${row.category}\n시점: ${row.view}\n상태: ${row.status}\n제품 ID: ${row.product_id}\n이미지 ID: ${row.case_id}`;el('reviewState').textContent=row.review_state==='VERIFIED_GT'?'검수 완료 · VERIFIED_GT':`미완료 · ${row.review_state}`;el('reReviewLabel').hidden=row.review_state!=='VERIFIED_GT';progress(row.progress);
   try{state.box=parseBBox(row.approved_bbox??row.proposal_bbox);}catch(e){error(e.message);state.box=null;}
   const loaded=await decodeImage('/image/'+index+'?token='+encodeURIComponent(row.image_token),controller.signal);if(sequence!==state.sequence)return;
   if(loaded.image.naturalWidth!==1024||loaded.image.naturalHeight!==1024)throw new Error('원본 이미지 크기가 1024×1024가 아닙니다.');
   state.image=loaded.image;state.receipt=loaded.receipt;render();state.ready=true;el('loading').textContent='원본 이미지 로딩 완료 · BBox를 검수하세요';
  }catch(e){if(sequence!==state.sequence)return;state.ready=false;error(e.name==='AbortError'?'요청 시간 초과 또는 취소. 다시 불러오기를 누르세요.':e.message);el('loading').textContent='로딩 실패 · 승인 불가';}
  finally{clearTimeout(timer);if(sequence===state.sequence){state.busy=false;controls();}}
 }
 // point: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function point(e){const r=c.getBoundingClientRect();return [Math.max(0,Math.min(c.width,(e.clientX-r.left)*c.width/r.width)),Math.max(0,Math.min(c.height,(e.clientY-r.top)*c.height/r.height))];}
 c.addEventListener('pointerdown',e=>{if(!state.ready||state.saving)return;state.start=point(e);state.beforeDrag=state.box?[...state.box]:null;el('ack').checked=false;c.setPointerCapture(e.pointerId);controls();});
 c.addEventListener('pointermove',e=>{if(!state.start)return;const p=point(e);state.box=[Math.min(state.start[0],p[0]),Math.min(state.start[1],p[1]),Math.max(state.start[0],p[0]),Math.max(state.start[1],p[1])];try{render();}catch{}controls();});
 c.addEventListener('pointerup',()=>{state.start=null;controls();});
 c.addEventListener('pointercancel',()=>{if(state.start){state.box=state.beforeDrag;state.start=null;try{render();}catch{}controls();}});
 el('restore').addEventListener('click',()=>{try{state.box=parseBBox(state.row.proposal_bbox);el('ack').checked=false;render();error('');}catch(e){error(e.message);}controls();});
 el('previous').addEventListener('click',()=>load(Math.max(0,state.index-1)));el('next').addEventListener('click',()=>load(Math.min(state.total-1,state.index+1)));el('retry').addEventListener('click',()=>load());
 for(const key of ['who','ack','reReview'])el(key).addEventListener('input',controls);
 // save: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 async function save(reviewState='VERIFIED_GT'){
  if(state.saving||!state.ready||state.busy)return;
  if(reviewState==='VERIFIED_GT'&&el('approve').disabled)return;
  const notes=reviewState==='VERIFIED_GT'?'':window.prompt('보류/거부 이유를 입력하세요.');if(reviewState!=='VERIFIED_GT'&&!notes?.trim())return;
  state.saving=true;controls();error('');el('message').textContent='저장 중…';
  try{
   const result=await fetchJSON('/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:state.index,case_id:state.row.case_id,source_sha256:state.row.source_sha256,image_receipt:state.receipt,image_rendered:true,expected_revision:state.row.review_revision,review_state:reviewState,bbox:state.box,reviewer:el('who').value.trim(),human_ack:el('ack').checked,re_review_ack:el('reReview').checked,notes:notes})});
   el('message').textContent=`${result.duplicate?'중복 요청 확인 · 추가 기록 없음':'저장 완료'}: ${result.status} (${result.saved})`;progress(result.progress);state.saving=false;await load(state.index,true);
  }catch(e){error(e.message);el('message').textContent='저장 확인에 실패했습니다. 같은 요청을 다시 보내도 동일한 승인 기록은 중복 추가하지 않습니다.';}
  finally{state.saving=false;controls();}
 }
 el('approve').addEventListener('click',()=>save());el('pending').addEventListener('click',()=>save('PENDING'));el('reject').addEventListener('click',()=>save('REJECTED'));
 load();
}
