// 한글 안내: 브라우저 검수 UI 또는 그 회귀 테스트입니다. 응답·좌표·로딩 오류와 사람의 명시적 확인을 구분합니다.
'use strict';
// parseBBox: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
function parseBBox(value, width=1024, height=1024) {
  const b=typeof value==='string'?JSON.parse(value):value;
  if(!Array.isArray(b)||b.length!==4||!b.every(v=>typeof v==='number'&&Number.isFinite(v))||!(0<=b[0]&&b[0]<b[2]&&b[2]<=width&&0<=b[1]&&b[1]<b[3]&&b[3]<=height))throw new Error('Crop 좌표가 올바르지 않습니다. 원본 범위 안의 [x0,y0,x1,y1]이 필요합니다.');
  return [...b];
}
// gtCropFromBox: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
function gtCropFromBox(value) {
 const b=parseBBox(value),cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;
 const side=Math.min(1024,Math.ceil(Math.max(b[2]-b[0],b[3]-b[1])*1.2)+2);
 const left=Math.max(0,Math.min(1024-side,Math.floor(cx-side/2))),top=Math.max(0,Math.min(1024-side,Math.floor(cy-side/2)));
 return [left,top,left+side,top+side];
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
if(typeof module!=='undefined')module.exports={parseBBox,fetchJSON,gtCropFromBox};
if(typeof document!=='undefined'){
 // humanReasons: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function humanReasons(value){const names={IMAGE_ONLY_GATE_RISK:'기존 이미지 Gate 위험 신호',REVIEWED_PRODUCT_BBOX_LOSS_IN_A:'GrabCut 후보가 검수 제품 BBox를 자름',REVIEWED_PRODUCT_BBOX_LOSS_IN_CENTER896:'Center896이 검수 제품 BBox를 자름',REVIEWED_PRODUCT_BBOX_LOSS_IN_OLD_GATE:'기존 Gate 후보에서 제품 BBox 손실',OPTIONAL_SECOND_CENTER_CROP_MASK_LOSS_NOT_CURRENT_FULL_FRAME_LOSS:'추가 CenterCrop 시 결함 손실 위험 (현재 원본 유지의 손실은 아님)',PRIORITY_SAMPLE_FROM_PREVIOUS_AUDIT:'기존 위험 또는 미계산 구간 대표 검수 표본'};return String(value).split(';').map(x=>names[x]||x).join(' / ');}
 const el=id=>document.getElementById(id),c=el('c'),ctx=c.getContext('2d');
 const state={index:0,total:0,row:null,box:null,image:null,ready:false,busy:false,saving:false,sequence:0,controller:null,start:null};
 // error: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function error(message){el('error').textContent=message;}
 // validBox: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function validBox(){try{parseBBox(state.box);return true;}catch{return false;}}
 // controls: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function controls(){
  el('approve').disabled=state.busy||state.saving||!state.ready||!validBox()||!state.previewToken||state.previewBox!==JSON.stringify(state.box)||(state.previewRequiresRisk&&!el('riskAck').checked)||el('who').value.trim().length<2||!el('ack').checked||(state.row?.review_state==='APPROVED_CROP'&&!el('reReview').checked);
  el('previous').disabled=state.busy||state.saving||state.index<=0;
  el('next').disabled=state.busy||state.saving||!state.total||state.index>=state.total-1;
  el('restore').disabled=!state.ready||state.saving;el('keepFull').disabled=!state.ready||state.saving;let hasGT=false;try{parseBBox(state.row?.reference_product_bbox);hasGT=true;}catch{}el('gtCrop').disabled=!state.ready||state.saving||!hasGT;el('preview').disabled=!state.ready||!validBox()||state.busy||state.saving;el('export').disabled=state.saving;el('nextPending').disabled=state.busy||state.saving;el('jump').disabled=state.busy||state.saving;el('retry').disabled=state.saving;
  for(const key of ['pending','reject'])el(key).disabled=state.busy||state.saving||!state.ready||el('who').value.trim().length<2;
 }
 // progress: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function progress(p){el('progress').max=p.total;el('progress').value=p.verified;el('progressText').textContent=`승인 완료 ${p.verified} / ${p.total} · 미완료 ${p.remaining} · 보류 ${p.states.PENDING} · 거부 ${p.states.REJECTED}`;}
 // render: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function render(){
  try{
   if(!ctx)throw new Error('이 브라우저에서 Canvas 2D를 사용할 수 없습니다.');
   ctx.clearRect(0,0,c.width,c.height);ctx.drawImage(state.image,0,0,c.width,c.height);if(state.maskImage&&el('maskVisible').checked)ctx.drawImage(state.maskImage,0,0,c.width,c.height);
   try{const p=parseBBox(state.row.proposal_bbox);ctx.strokeStyle='#1476ca';ctx.lineWidth=2;ctx.setLineDash([10,7]);ctx.strokeRect(p[0],p[1],p[2]-p[0],p[3]-p[1]);}catch{}
   ctx.setLineDash([]);try{const ref=parseBBox(state.row.reference_product_bbox);ctx.strokeStyle='#00d4df';ctx.lineWidth=2;ctx.strokeRect(ref[0],ref[1],ref[2]-ref[0],ref[3]-ref[1]);}catch{}
   if(validBox()){const b=state.box;ctx.strokeStyle='#00a54f';ctx.lineWidth=3;ctx.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1]);}
   el('coordinates').textContent=state.box?'Crop XYXY: ['+state.box.map(x=>x.toFixed(1)).join(', ')+']':'Crop가 없습니다. 제품 전체를 드래그하여 지정하세요.';
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
  const timer=setTimeout(()=>controller.abort(),25000);state.index=index;state.autoGTPrepared=false;state.maskImage=null;state.previewToken=null;el('riskAck').checked=false;el('riskAckLabel').hidden=true;el('previewStatus').textContent='범위를 정한 뒤 보존 점검을 실행하세요.';state.busy=true;state.ready=false;state.row=null;state.box=null;state.image=null;state.start=null;
  el('ack').checked=false;el('reReview').checked=false;error('');if(!preserveMessage)el('message').textContent='';el('loading').textContent='항목과 원본 이미지를 불러오는 중…';el('coordinates').textContent='Crop: —';el('info').textContent='';el('reviewState').textContent='로딩 중';
  if(ctx)ctx.clearRect(0,0,c.width,c.height);controls();
  try{
   const row=await fetchJSON('/item/'+index,{signal:controller.signal});if(sequence!==state.sequence)return;
   state.row=row;state.total=row.total;el('counter').textContent=`${index+1} / ${row.total}`;el('info').textContent=`품목: ${row.category}\n시점: ${row.view}\n상태: ${row.status}\n제품 ID: ${row.product_id}\n이미지 ID: ${row.case_id}\nSplit: ${row.split}\n검수 이유: ${humanReasons(row.review_reasons)}\n자동 후보: ${row.proposal_method}\n기준 CSV 정책: ${row.current_policy}\n기준 Crop: ${row.current_crop}`;el('reviewState').textContent=row.review_state==='APPROVED_CROP'?'검수 완료 · APPROVED_CROP':`미완료 · ${row.review_state}`;el('reReviewLabel').hidden=row.review_state!=='APPROVED_CROP';progress(row.progress);
   try{state.box=parseBBox(row.approved_bbox??row.proposal_bbox);if(row.review_state==='PROPOSAL'&&row.reference_product_bbox){state.box=gtCropFromBox(row.reference_product_bbox);state.autoGTPrepared=true;}}catch(e){error(e.message);state.box=null;}
   const loaded=await decodeImage('/image/'+index+'?token='+encodeURIComponent(row.image_token),controller.signal);if(sequence!==state.sequence)return;
   if(loaded.image.naturalWidth!==1024||loaded.image.naturalHeight!==1024)throw new Error('원본 이미지 크기가 1024×1024가 아닙니다.');
   state.image=loaded.image;state.receipt=loaded.receipt;render();state.ready=true;if(row.mask_available){const overlay=new Image();overlay.onload=()=>{if(sequence===state.sequence){state.maskImage=overlay;try{render();}catch{}}};overlay.onerror=()=>{if(sequence===state.sequence)error('마스크 표시 실패: 보존 점검 결과도 확인하세요.');};overlay.src='/mask_overlay/'+index;}el('loading').textContent='원본 로딩 완료 · Crop을 조절하고 보존 점검을 실행하세요';
  }catch(e){if(sequence!==state.sequence)return;state.ready=false;error(e.name==='AbortError'?'요청 시간 초과 또는 취소. 다시 불러오기를 누르세요.':e.message);el('loading').textContent='로딩 실패 · 승인 불가';}
  finally{clearTimeout(timer);if(sequence===state.sequence){state.busy=false;controls();if(state.ready&&state.autoGTPrepared){state.autoGTPrepared=false;el('reviewState').textContent='제품 GT 확인됨 · Crop 후보 점검/승인 대기';el('previewStatus').textContent='이미 승인된 제품 GT +10% Crop 후보를 계산했습니다. 저장 전 보존 점검 중…';el('preview').click();}}}
 }
 // point: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 function point(e){const r=c.getBoundingClientRect();return [Math.max(0,Math.min(c.width,(e.clientX-r.left)*c.width/r.width)),Math.max(0,Math.min(c.height,(e.clientY-r.top)*c.height/r.height))];}
 c.addEventListener('pointerdown',e=>{if(!state.ready||state.saving)return;state.start=point(e).map(Math.round);state.beforeDrag=state.box?[...state.box]:null;el('ack').checked=false;c.setPointerCapture(e.pointerId);controls();});
 c.addEventListener('pointermove',e=>{if(!state.start)return;let p=point(e);if(el('square').checked){const dx=p[0]-state.start[0],dy=p[1]-state.start[1],sx=dx>=0?1:-1,sy=dy>=0?1:-1;const side=Math.min(Math.max(Math.abs(dx),Math.abs(dy)),sx>0?1024-state.start[0]:state.start[0],sy>0?1024-state.start[1]:state.start[1]);p=[state.start[0]+sx*side,state.start[1]+sy*side];}state.box=[Math.min(state.start[0],p[0]),Math.min(state.start[1],p[1]),Math.max(state.start[0],p[0]),Math.max(state.start[1],p[1])];state.box=state.box.map((v,i)=>i<2?Math.floor(v):Math.ceil(v));try{render();}catch{}controls();});
 c.addEventListener('pointerup',()=>{state.start=null;controls();});
 c.addEventListener('pointercancel',()=>{if(state.start){state.box=state.beforeDrag;state.start=null;try{render();}catch{}controls();}});
 el('restore').addEventListener('click',()=>{try{state.box=parseBBox(state.row.proposal_bbox);el('ack').checked=false;render();error('');}catch(e){error(e.message);}controls();});
 el('previous').addEventListener('click',()=>load(Math.max(0,state.index-1)));el('next').addEventListener('click',()=>load(Math.min(state.total-1,state.index+1)));el('retry').addEventListener('click',()=>load());
 for(const key of ['who','ack','reReview','riskAck'])el(key).addEventListener('input',controls);
 // save: 검수 화면의 상태·표시·요청을 처리하는 함수입니다. 오류와 최신 요청 순서를 확인합니다.
 async function save(reviewState='APPROVED_CROP'){
  if(state.saving||!state.ready||state.busy)return;
  if(reviewState==='APPROVED_CROP'&&el('approve').disabled)return;
  const notes=reviewState==='APPROVED_CROP'?'':window.prompt('보류/거부 이유를 입력하세요.');if(reviewState!=='APPROVED_CROP'&&!notes?.trim())return;
  state.saving=true;controls();error('');el('message').textContent='저장 중…';
  try{
   const result=await fetchJSON('/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:state.index,case_id:state.row.case_id,source_sha256:state.row.source_sha256,image_receipt:state.receipt,image_rendered:true,expected_revision:state.row.review_revision,review_state:reviewState,preview_receipt:state.previewToken,risk_ack:el('riskAck').checked,bbox:state.box,reviewer:el('who').value.trim(),human_ack:el('ack').checked,re_review_ack:el('reReview').checked,notes:notes})});
   el('message').textContent=`${result.duplicate?'중복 요청 확인 · 추가 기록 없음':'저장 완료'}: ${result.status} (${result.saved})`;progress(result.progress);state.saving=false;await load(state.index,true);
  }catch(e){error(e.message);el('message').textContent='저장 확인에 실패했습니다. 같은 요청을 다시 보내도 동일한 승인 기록은 중복 추가하지 않습니다.';}
  finally{state.saving=false;controls();}
 }

 el('jump').addEventListener('click',()=>{const n=Number(el('jumpTo').value);if(Number.isInteger(n)&&n>=1&&n<=state.total)load(n-1);else error('1부터 전체 항목 수 사이의 번호를 입력하세요.');});
 el('nextPending').addEventListener('click',async()=>{const sequence=state.sequence;try{const r=await fetchJSON('/next_pending/'+state.index);if(sequence!==state.sequence)return;if(r.index===null)el('message').textContent='우선 검수 목록의 모든 항목이 승인됐습니다.';else load(r.index);}catch(e){error(e.message);}});
 el('gtCrop').addEventListener('click',()=>{try{state.box=gtCropFromBox(state.row.reference_product_bbox);el('ack').checked=false;render();controls();el('preview').click();}catch(e){error(e.message);}});
 el('keepFull').addEventListener('click',()=>{state.box=[0,0,1024,1024];el('ack').checked=false;try{render();}catch{}controls();});
 el('maskVisible').addEventListener('input',()=>{if(state.ready)try{render();}catch{}});
 el('preview').addEventListener('click',async()=>{
  if(!state.ready||!validBox())return;state.previewToken=null;el('previewStatus').textContent='현재 범위의 제품·결함 보존을 점검 중…';controls();
  const requested=JSON.stringify(state.box),seq=state.sequence;
  try{const result=await fetchJSON('/preview_crop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:state.index,case_id:state.row.case_id,source_sha256:state.row.source_sha256,image_receipt:state.receipt,image_rendered:true,bbox:state.box})});
   if(seq!==state.sequence||requested!==JSON.stringify(state.box))return;state.previewToken=result.preview_receipt;state.previewBox=requested;state.previewRequiresRisk=result.requires_risk_ack;el('riskAck').checked=false;el('riskAckLabel').hidden=!result.requires_risk_ack;
   el('previewStatus').textContent='제품 BBox 참조: '+result.product.status+(result.product.area_recall===null?'':` / 면적 보존 ${(result.product.area_recall*100).toFixed(4)}%`)+ '\n결함 마스크: '+result.defect_mask.status+(result.defect_mask.retention===null?'':` / 픽셀 보존 ${(result.defect_mask.retention*100).toFixed(4)}%`)+`\n관측 손실: ${result.observed_loss?'있음':'없음 (GT 미제공 영역은 미확인)'} / 면적 기준 선형 확대 ${result.area_equivalent_gain.toFixed(3)}배`+(result.review_split==='test'&&result.annotation_assisted?'\nTest 정답 참조 Crop 수정은 평가 오염 검토 대상으로 기록됩니다.':'');
  }catch(e){error(e.message);}finally{controls();}
 });
 el('export').addEventListener('click',async()=>{if(state.saving)return;state.saving=true;controls();el('exportResult').textContent='승인 이력만 반영한 새 CSV를 만드는 중…';
  try{const r=await fetchJSON('/export',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});el('exportResult').textContent=`${r.path}\n전체 ${r.rows}행 / 수동 승인 ${r.human_approved_rows}행 반영. 기존 CSV는 보존됐습니다.`;}catch(e){error(e.message);}finally{state.saving=false;controls();}
 });
 el('approve').addEventListener('click',()=>save());el('pending').addEventListener('click',()=>save('PENDING'));el('reject').addEventListener('click',()=>save('REJECTED'));
 load();
}
