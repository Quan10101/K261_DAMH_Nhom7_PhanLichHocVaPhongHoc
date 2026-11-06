const $=id=>document.getElementById(id);let instance=null,result=null;
const num=id=>Number($(id).value);const fmt=x=>x===null||x===undefined?'—':Number(x).toLocaleString('vi-VN',{maximumFractionDigits:3});
async function post(path,data){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),j=await r.json();if(!r.ok)throw Error(j.error||'Lỗi');return j}
function message(id,s){$(id).textContent=s}
const DAYS=['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ nhật'];
const periodName=t=>`${DAYS[Math.floor(t/5)]} · Ca ${t%5+1}`;
const roomCode=r=>`CS${r.campus}.${r.building}.${String(Math.floor(r.id/12)+1).padStart(2,'0')}.${String(r.id%12+1).padStart(2,'0')}`;
function renderRoomInventory(){
  if(!instance)return;
  $('roomRows').innerHTML=instance.rooms.map(r=>`<tr data-id="${r.id}">
    <td><b>${roomCode(r)}</b></td>
    <td><select data-field="campus" aria-label="Cơ sở của phòng ${r.id+1}">${[1,2,3].map(v=>`<option value="${v}" ${r.campus===v?'selected':''}>CS${v}</option>`).join('')}</select></td>
    <td><select data-field="building" aria-label="Tòa của phòng ${r.id+1}">${['A','B','C'].map(v=>`<option ${r.building===v?'selected':''}>${v}</option>`).join('')}</select></td>
    <td><input data-field="capacity" type="number" min="1" max="1000" value="${r.capacity}" aria-label="Sức chứa phòng ${r.id+1}"></td>
    <td><select data-field="kind" aria-label="Loại phòng ${r.id+1}"><option value="0" ${r.kind===0?'selected':''}>Lý thuyết</option><option value="1" ${r.kind===1?'selected':''}>Thực hành</option></select></td>
  </tr>`).join('');
}
function applyRooms(){
  if(liveJob){message('roomStatus','Hãy hoàn tất hoặc dừng GA trước khi sửa danh sách phòng.');return}
  if(!instance){message('roomStatus','Hãy tạo dữ liệu trước.');return}
  const draft=instance.rooms.map(r=>({...r}));
  try{
    for(const row of $('roomRows').querySelectorAll('tr[data-id]')){
      const r=draft[Number(row.dataset.id)];
      r.campus=Number(row.querySelector('[data-field="campus"]').value);
      r.building=row.querySelector('[data-field="building"]').value;
      r.capacity=Number(row.querySelector('[data-field="capacity"]').value);
      r.kind=Number(row.querySelector('[data-field="kind"]').value);
      if(!Number.isInteger(r.capacity)||r.capacity<1||r.capacity>1000)throw Error('Sức chứa phải là số nguyên từ 1 đến 1000.');
      r.code=roomCode(r);
    }
    instance.rooms=draft;
    result=null;
    $('metrics').innerHTML='';['greedyScore','gaScore','improvement'].forEach(id=>$(id).textContent='—');
    $('calendar').textContent='Đã đổi danh sách phòng. Nhấn Chạy Greedy & GA để xếp lịch lại.';
    $('calendarStatus').textContent='Kết quả cũ đã bị xóa vì dữ liệu phòng thay đổi.';
    renderRoomInventory();draw([]);
    message('roomStatus','✓ Đã áp dụng '+draft.length+' phòng. Chạy lại thuật toán để tính lịch mới.');
  }catch(e){message('roomStatus','Lỗi: '+e.message)}
}
$('applyRooms').onclick=applyRooms;
async function generate(){let btn=$('generate');btn.disabled=true;message('dataStatus','Đang tạo dữ liệu…');try{let x=await post('/api/generate',{classes:num('classes'),rooms:num('rooms'),slots:num('slots'),seed:num('seed'),preference_weight:num('preferenceWeight')});instance=x;result=null;$('count').textContent=x.courses.length+' / '+x.rooms.length;['greedyScore','gaScore','improvement'].forEach(k=>$(k).textContent='—');$('metrics').innerHTML='';$('calendar').innerHTML='Chạy thuật toán để tạo lịch.';renderRoomInventory();message('roomStatus',`Đã sinh ${x.rooms.length} phòng mô phỏng tại CS1, CS2, CS3.`);$('dataRows').innerHTML=x.courses.map(c=>`<tr><td>LHP${c.id+1}</td><td>${c.students}</td><td>GV${c.teacher+1}</td><td>N${c.group+1}</td><td>${c.kind?'Thực hành':'Lý thuyết'}</td><td>${periodName(Array.from({length:x.slots},(_,t)=>[t,((c.id*13+t*7+(c.id*t)%11)%19)]).sort((a,b)=>a[1]-b[1])[0][0])}</td></tr>`).join('');draw([]);$('dataPreview').innerHTML='<b>Xem nhanh dữ liệu vừa tạo:</b><br>'+x.courses.slice(0,4).map(c=>`LHP${c.id+1}: ${c.students} SV · GV${c.teacher+1}`).join('<br>')+`<br><span>… và ${Math.max(0,x.courses.length-4)} lớp khác. Bảng đầy đủ ở phía dưới.</span>`;message('dataStatus',`✓ Đã tạo ${x.courses.length} lớp, ${x.rooms.length} phòng, ${x.slots} ca (7 ngày × 5 ca) · mã tạo ngẫu nhiên ${x.seed}`);message('solveStatus','Đã có dữ liệu. Nhấn Chạy Greedy & GA.');autoGA=false;if(liveTimer){clearInterval(liveTimer);liveTimer=null}liveJob=null;liveButtons('completed');message('liveState','Chưa chạy trên bộ dữ liệu mới');$('liveRows').innerHTML='';$('liveProgress').style.width='0%';$('liveGeneration').textContent='0 / '+num('generations');['liveBest','liveMean','liveFeasible'].forEach(id=>$(id).textContent='—');}catch(e){message('dataStatus','Lỗi tạo dữ liệu: '+e.message)}finally{btn.disabled=false}}
async function solve(){if(!instance){await generate();if(!instance)return}let btn=$('solve');btn.disabled=true;message('solveStatus','Python đang giải bài toán…');try{result=await post('/api/solve',{instance,population:num('population'),generations:num('generations'),ga_seed:num('gaSeed'),mutation_probability:num('mutationProbability')});$('greedyScore').textContent=fmt(result.greedy.objective);$('gaScore').textContent=fmt(result.ga.objective);let gr=result.greedy.objective,ga=result.ga.objective;$('improvement').textContent=gr!==null&&ga!==null&&gr>0?((gr-ga)/gr*100).toFixed(2)+'%':'—';$('metrics').innerHTML=['greedy','ga'].map(n=>{let r=result[n];return `<tr><td>${n==='ga'?'Genetic Algorithm':'Greedy'}</td><td>${r.feasible?'Có':'Không'}</td><td>${fmt(r.objective)}</td><td>${fmt(r.runtime_ms)}</td></tr>`}).join('');showCalendar();draw(result.history.map(h=>h.best_objective));message('solveStatus','Hoàn thành. Python đã chạy cả hai thuật toán trên cùng một dữ liệu.')}catch(e){message('solveStatus','Lỗi: '+e.message)}finally{btn.disabled=false}}
function showCalendar(){
  if(!result||!instance)return;
  const algorithm=$('selectAlgorithm').value, r=result[algorithm];
  const status=$('calendarStatus');
  if(status)status.textContent=liveJob&&!liveFinished?(algorithm==='ga'?'Phương án GA tốt nhất hiện tại (chưa phải kết quả cuối cùng)':'Greedy đã xếp; GA vẫn đang chạy'):'Thời khóa biểu 7 ngày × 5 ca · '+algorithm.toUpperCase();
  if(!r||!r.feasible){$('calendar').textContent='Không tìm thấy lịch hợp lệ cho '+algorithm;return}
  let slots=instance.slots,html='<table><thead><tr><th>Ca</th>';
  for(let d=0;d<7;d++)html+=`<th>${DAYS[d]}</th>`;
  html+='</tr></thead><tbody>';
  const assignmentsBySlot=new Map();
  for(const a of r.assignments){if(!assignmentsBySlot.has(a.slot))assignmentsBySlot.set(a.slot,[]);assignmentsBySlot.get(a.slot).push(a)}
  for(let period=0;period<5;period++){
    html+=`<tr><th>Ca ${period+1}</th>`;
    for(let d=0;d<7;d++){
      let t=d*5+period;
      html+='<td>';
      if(t<slots){
        for(const a of assignmentsBySlot.get(t)||[]){
          let room=instance.rooms[a.room];
          html+=`<div class="course"><b>LHP${a.course+1} · ${room.code||roomCode(room)}</b><span>CS${room.campus} · Tòa ${room.building} · ${room.capacity} chỗ</span><span>${a.students} SV · GV${a.teacher+1} · Nhóm ${a.group+1}</span></div>`;
        }
      }else html+='<span class="empty-slot">—</span>';
      html+='</td>';
    }
    html+='</tr>';
  }
  html+='</tbody></table>';
  $('calendar').innerHTML=html;
}
function draw(values){let el=$('chart'),ctx=el.getContext('2d'),w=el.width,h=el.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#e1e9f2';for(let i=0;i<5;i++){let y=20+i*(h-45)/4;ctx.beginPath();ctx.moveTo(65,y);ctx.lineTo(w-15,y);ctx.stroke()}if(!values.length){ctx.fillStyle='#6a859d';ctx.font='17px Arial';ctx.fillText('Chạy GA để xem đường hội tụ',w/2-115,h/2);return}let mi=Math.min(...values),ma=Math.max(...values),range=Math.max(1,ma-mi);ctx.strokeStyle='#0ca78e';ctx.lineWidth=3;ctx.beginPath();values.forEach((v,i)=>{let x=65+i/Math.max(1,values.length-1)*(w-90),y=20+(ma-v)/range*(h-45);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();ctx.fillStyle='#425a74';ctx.font='14px Arial';ctx.fillText(fmt(ma),5,25);ctx.fillText(fmt(mi),5,h-25);ctx.fillText('1',65,h-7);ctx.fillText(''+values.length,w-36,h-7)}
function csvDownload(filename,txt,mime){let obj=new Blob([txt],{type:mime}),url=URL.createObjectURL(obj),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),500)}
$('exportCSV').onclick=()=>{if(!result){alert('Hãy chạy thuật toán trước');return}let r=result[$('selectAlgorithm').value];if(!r||!r.feasible){alert('Chưa có thời khóa biểu hợp lệ để xuất');return}let rows=['lop,ma_phong,co_so,toa_nha,suc_chua,thu,ca,slot_tuan,giang_vien,nhom,si_so'];for(let a of r.assignments){const room=instance.rooms[a.room];rows.push([a.course+1,room.code,room.campus,room.building,room.capacity,DAYS[Math.floor(a.slot/5)],a.slot%5+1,a.slot+1,a.teacher+1,a.group+1,a.students].join(','))}csvDownload('thoi_khoa_bieu_7_ngay.csv','\ufeff'+rows.join('\r\n'),'text/csv;charset=utf-8')};

let observingExperiment=false;
$('toggleObservation').onclick=()=>{
  observingExperiment=!observingExperiment;
  $('experimentPanel').hidden=!observingExperiment;
  $('toggleObservation').setAttribute('aria-expanded', String(observingExperiment));
  $('toggleObservation').textContent=observingExperiment?'✕ Đóng quan sát':'👁 Quan sát quá trình';
  $('toggleObservation').classList.toggle('is-open',observingExperiment);
  if(observingExperiment) $('experimentPanel').scrollIntoView({behavior:'smooth',block:'start'});
};
const DEFAULT_SCENARIOS={A:{classes:12,rooms:8,slots:35},B:{classes:20,rooms:10,slots:35},C:{classes:30,rooms:15,slots:35}};
function getScenarios(){
  const scenarios={};
  for(const label of ['A','B','C']){
    const conf={};
    for(const [field,min,max] of [['classes',2,120],['rooms',2,50],['slots',35,35]]){
      const value=num('scenario'+label+field[0].toUpperCase()+field.slice(1));
      if(!Number.isInteger(value)||value<min||value>max)throw Error(`Kịch bản ${label}: ${field} phải từ ${min} đến ${max}.`);
      conf[field]=value;
    }
    scenarios[label]=conf;
  }
  return scenarios;
}
$('resetScenarios').onclick=()=>{
  for(const [label,conf] of Object.entries(DEFAULT_SCENARIOS))for(const [field,value] of Object.entries(conf))
    $('scenario'+label+field[0].toUpperCase()+field.slice(1)).value=String(value);
};
async function experiment(){
  if(!Number.isFinite(num('mutationProbability'))||num('mutationProbability')<0||num('mutationProbability')>1){message('experimentStatus','Xác suất đột biến (tỷ lệ thay đổi ngẫu nhiên) phải từ 0 đến 1');return}
  let btn=$('experiment');let scenarios;try{scenarios=getScenarios()}catch(e){message('experimentStatus',e.message);return}btn.disabled=true;
  const expConfig={trials:num('trials'),seed:num('gaSeed'),population:num('population'),generations:num('generations'),mutation_probability:num('mutationProbability'),preference_weight:num('preferenceWeight'),scenarios};
  $('experimentConfiguration').innerHTML=`<b>Cấu hình đợt thực nghiệm:</b><br>Số lượt: ${expConfig.trials} · Seed GA (mã tạo ngẫu nhiên, mục 2): ${expConfig.seed}<br>Quần thể (số phương án mỗi vòng): ${expConfig.population} · Số thế hệ (số vòng cải thiện): ${expConfig.generations} · Xác suất đột biến (tỷ lệ thay đổi ngẫu nhiên): ${expConfig.mutation_probability}<br>Trọng số ưu tiên giờ: ${expConfig.preference_weight}<br>Kịch bản: ${Object.entries(scenarios).map(([label,c])=>`${label} (${c.classes} lớp, ${c.rooms} phòng, ${c.slots} ca)`).join(" · ")}<br>Mã tạo dữ liệu lượt k = ${expConfig.seed} + k − 1; mã chạy GA lượt k = ${expConfig.seed} + 100000 + k − 1. <b>Thực nghiệm hàng loạt sử dụng cả bốn thông số ở mục 2, bao gồm Seed GA (mã tạo ngẫu nhiên).</b>`;
  $('progress').style.width='0%';$('trialRows').innerHTML='';$('summaryRows').innerHTML='';message('experimentOverallPhase','Đang chuẩn bị thực nghiệm Greedy & GA…');
  $('expGenerationRows').innerHTML='';$('expGenerationProgress').style.width='0%';drawExperiment([]);$('expGreedyRows').innerHTML='';$('expGreedyProgress').style.width='0%';drawExperiment([], 'expGreedyChart');
  let previous=0,lastTrial=0,lastGen=0,lastGreedyStep=-1;
  try{
    const j=await post('/api/experiment/start',{...expConfig,display_delay_ms:num('experimentSpeed')});
    // Observation is opt-in; do not auto-scroll or open the large panel.
    while(true){
      await new Promise(r=>setTimeout(r,num('experimentSpeed')===0?300:80));
      let resp=await fetch('/api/status/'+j.job_id,{cache:'no-store'}),x=await resp.json();
      if(!resp.ok)throw Error(x.error||'Không lấy được tiến trình');
      $('progress').style.width=(100*x.completed/x.total)+'%';
      message('experimentStatus',`Hoàn thành ${x.completed}/${x.total} lượt; đang xử lý ${x.current_trial||'—'}/${x.total}`);
      message('experimentOverallPhase',x.done?`Đã hoàn thành ${x.completed}/${x.total} lượt thực nghiệm Greedy & GA`:`Lượt ${x.current_trial||1}/${x.total} · Kịch bản ${x.current_scenario||'—'} · Đang thực nghiệm Greedy & GA`);
      if(observingExperiment){
      $('experimentPhase').textContent=x.done?'Đã hoàn thành toàn bộ thực nghiệm':`Lượt ${x.current_trial}/${x.total} · Kịch bản ${x.current_scenario} · ${x.current_phase}`;
      $('expTrial').textContent=(x.current_trial||'—')+' / '+(x.current_scenario||'—');
      $('expScores').textContent=fmt(x.current_greedy)+' / '+fmt(x.current_best);
      $('expGreedyStep').textContent=(x.current_greedy_step||0)+' / '+(x.current_greedy_total||0);
      $('expGreedyTotal').textContent=fmt(x.current_greedy_partial);
      $('expGreedyProgress').style.width=(x.current_greedy_total?100*(x.current_greedy_step||0)/x.current_greedy_total:0)+'%';
      $('expGreedyStatus').textContent=(x.current_phase||'').includes('Greedy')?x.current_phase:(x.current_greedy_step||0)?'Greedy hoàn thành; đang theo dõi GA':'Chưa thực hiện Greedy';
      if(lastTrial!==x.current_trial||lastGreedyStep!==x.current_greedy_step||x.done){
        let steps=x.current_greedy_steps||[];
        $('expGreedyRows').innerHTML=steps.slice(-45).reverse().map(r=>`<tr><td>${r.step}</td><td>LHP${r.course}</td><td>${r.room_code}</td><td>${r.day} · Ca ${r.period}</td><td>${fmt(r.increment)}</td><td>${fmt(r.cumulative)}</td><td>${fmt(r.runtime_ms)}</td></tr>`).join('');
        drawExperiment(steps.map(r=>r.cumulative),'expGreedyChart');lastGreedyStep=x.current_greedy_step;
      }
      $('expGeneration').textContent=x.current_generation+' / '+x.total_generations;
      $('expFeasible').textContent=x.current_feasible==null?'—':x.current_feasible+' / '+num('population');
      $('expGenerationProgress').style.width=(100*x.current_generation/x.total_generations)+'%';
      if(x.current_trial!==lastTrial||x.current_generation!==lastGen||x.done){
        let hist=x.current_history||[];
        $('expGenerationRows').innerHTML=hist.slice(-35).reverse().map(r=>`<tr><td>${r.generation}</td><td>${fmt(r.best)}</td><td>${fmt(r.mean)}</td><td>${r.feasible}</td><td>${r.evaluations}</td><td>${fmt(r.runtime_ms)}</td></tr>`).join('');
        drawExperiment(hist.map(r=>r.best));lastTrial=x.current_trial;lastGen=x.current_generation;
      }
      } // End optional observation updates.
      if(x.completed!==previous||x.done){
        $('trialRows').innerHTML=x.records.slice(-25).reverse().map(r=>`<tr><td>${r.trial}</td><td>${r.scenario}</td><td>${fmt(r.greedy_objective)}</td><td>${fmt(r.ga_objective)}</td><td>${fmt(r.greedy_ms)}</td><td>${fmt(r.ga_ms)}</td></tr>`).join('');previous=x.completed;
      }
      if(x.done){
        if(x.error)throw Error(x.error);
        // Summary stays available even when the observation drawer is closed.
        $('summaryRows').innerHTML=x.summary.map(r=>`<tr><td>${r.scenario}</td><td>${r.algorithm}</td><td>${fmt(r.mean_objective)}</td><td>${fmt(r.std_objective)}</td><td>${(100*r.feasible_rate).toFixed(1)}%</td><td>${fmt(r.mean_ms)}</td></tr>`).join('');
        message('experimentStatus','Hoàn tất! Kết quả tại '+x.result_folder+' (runs.csv, summary.csv, metadata.json).');break;
      }
    }
  }catch(e){message('experimentStatus','Lỗi: '+e.message);message('experimentOverallPhase','Thực nghiệm gặp lỗi');message('experimentPhase','Có lỗi trong quá trình thực nghiệm')}
  finally{btn.disabled=false}
}
function drawExperiment(values, targetId='expChart'){
  const target=$(targetId);
  // Reuse the existing plot renderer with the experiment canvas.
  let ctx=target.getContext('2d'),w=target.width,h=target.height;
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);
  ctx.strokeStyle='#e1e9f2';ctx.lineWidth=1;
  for(let i=0;i<5;i++){let y=20+i*(h-45)/4;ctx.beginPath();ctx.moveTo(65,y);ctx.lineTo(w-15,y);ctx.stroke()}
  const vv=values.filter(v=>v!==null && Number.isFinite(v));
  if(!vv.length){ctx.fillStyle='#6a859d';ctx.font='16px Arial';ctx.fillText(targetId==='expGreedyChart'?'Đang chờ Greedy xếp lớp…':'Đang chờ kết quả thế hệ GA…',w/2-120,h/2);return}
  let min=Math.min(...vv),max=Math.max(...vv),range=Math.max(1,max-min);
  ctx.strokeStyle='#0ca78e';ctx.lineWidth=3;ctx.beginPath();
  vv.forEach((v,i)=>{let x=65+i/Math.max(1,vv.length-1)*(w-90),y=20+(max-v)/range*(h-45);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});
  ctx.stroke();ctx.fillStyle='#425a74';ctx.font='14px Arial';ctx.fillText(fmt(max),5,25);ctx.fillText(fmt(min),5,h-25);
  ctx.fillText('1',65,h-7);ctx.fillText(String(vv.length),w-40,h-7);
}
$('generate').onclick=generate;$('experiment').onclick=experiment;$('selectAlgorithm').onchange=showCalendar;generate();
let liveJob=null, liveTimer=null,liveBusy=false,liveFinished=false,manualPause=false; let autoGA=false, autoTask=null, lastLiveGeneration=0; const STEP_VIEW_MS=320;
function liveButtons(state){let active=state&&!['completed','stopped','error'].includes(state);$('liveStep').disabled=!active;$('liveResume').disabled=!active;$('livePause').disabled=!active;$('liveStop').disabled=!active;}
async function liveControl(action){if(!liveJob)return;try{await post('/api/live/control/'+liveJob,{action});await pollLive()}catch(e){message('liveState','Lỗi điều khiển: '+e.message)}}
function presentResults(x){result={greedy:x.greedy||{feasible:false,objective:null,assignments:[]},ga:x.ga||x.best_so_far||{feasible:false,objective:null,assignments:[]},history:x.history||[]};$('greedyScore').textContent=fmt(result.greedy.objective);$('gaScore').textContent=fmt(result.ga.objective);let gr=result.greedy.objective,ga=result.ga.objective;$('improvement').textContent=gr!==null&&ga!==null&&gr>0?((gr-ga)/gr*100).toFixed(2)+'%':'—';$('metrics').innerHTML=['greedy','ga'].map(n=>{let r=result[n];return `<tr><td>${n==='ga'?'Genetic Algorithm':'Greedy'}</td><td>${r.feasible?'Có':'Không'}</td><td>${fmt(r.objective)}</td><td>${fmt(r.runtime_ms)}</td></tr>`}).join('');showCalendar();draw(result.history.map(h=>h.best_objective));}
async function pollLive(){if(!liveJob||liveBusy)return;liveBusy=true;try{let response=await fetch('/api/live/status/'+liveJob,{cache:'no-store'});let x=await response.json();if(!response.ok)throw Error(x.error||'Không lấy được tiến độ');$('liveState').textContent=(autoGA&&!x.done?'Đang tối ưu tự động — thế hệ '+x.current_generation+'/'+x.total_generations:( {starting:'Đang khởi tạo',running:'Đang tính toán',stepping:'Đang chạy một thế hệ',paused:manualPause?'Đã tạm dừng theo yêu cầu':'Sẵn sàng chạy tiếp',completed:'Đã hoàn thành',stopped:'Đã dừng',error:'Có lỗi'}[x.state]||x.state))+(x.error?' — '+x.error:'');$('liveGeneration').textContent=x.current_generation+' / '+x.total_generations;$('liveProgress').style.width=(100*x.current_generation/x.total_generations)+'%';lastLiveGeneration=x.current_generation;if(x.history.length){let r=x.history[x.history.length-1];$('liveBest').textContent=fmt(r.best_objective);$('liveMean').textContent=fmt(r.mean_objective);$('liveFeasible').textContent=r.feasible_count+' / '+num('population')};$('liveRows').innerHTML=x.log.slice(-60).reverse().map(r=>`<tr><td>${r.generation}</td><td>${fmt(r.objective)}</td><td>${fmt(r.mean)}</td><td>${r.feasible}</td><td>${r.evaluations}</td><td>${fmt(r.runtime_ms)}</td></tr>`).join('');if(x.greedy)presentResults(x);liveButtons(x.state);if(x.state==='completed'||x.state==='stopped'||x.state==='error'){liveFinished=true;showCalendar()}if(autoGA&&liveJob&&x.state==='paused'&&!autoTask)autoTask=driveGA();message('solveStatus',x.state==='completed'?'Hoàn thành GA. Đây là thời khóa biểu cuối cùng.':x.done?'Quá trình đã kết thúc.':'Đang tối ưu, thời khóa biểu GA chỉ là phương án tốt nhất hiện tại.');if(x.done){autoGA=false;clearInterval(liveTimer);liveTimer=null;liveJob=null;autoTask=null;$('solve').disabled=false}}catch(e){message('liveState','Lỗi: '+e.message)}finally{liveBusy=false}}
async function startLive(startPaused=true){autoGA=false;manualPause=false;liveFinished=false;if(!instance){await generate();if(!instance)return}if(liveTimer)clearInterval(liveTimer);try{let j=await post('/api/live/start',{instance,population:num('population'),generations:num('generations'),ga_seed:num('gaSeed'),mutation_probability:num('mutationProbability'),start_paused:startPaused});liveJob=j.job_id;$('liveRows').innerHTML='';$('liveProgress').style.width='0%';$('liveGeneration').textContent='0 / '+num('generations');message('liveState','Đang khởi tạo và chờ lệnh');liveButtons('starting');await pollLive();if(liveJob)liveTimer=setInterval(pollLive,180)}catch(e){message('liveState','Lỗi: '+e.message);$('solve').disabled=false}}
// The browser requests one REAL Python GA generation at a time, then shows its
// actual outcome. The interval is a presentation cadence, not algorithm runtime.
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function driveGA(){
  try{
    while(autoGA&&liveJob){
      let jobId=liveJob;
      let old=lastLiveGeneration;
      await liveControl('step');
      // A generation is computed server-side. Wait for its result before the next one.
      for(let k=0;k<150 && autoGA && liveJob===jobId && lastLiveGeneration<=old;k++){
        await sleep(60);await pollLive();
      }
      await sleep(STEP_VIEW_MS);
    }
  }finally{autoTask=null;}
}
$('liveStep').onclick=async()=>{autoGA=false;manualPause=true;await liveControl('step')};
$('liveResume').onclick=()=>{if(!liveJob)return;manualPause=false;autoGA=true;message('liveState','Đang chạy theo từng thế hệ (Python tính thật)');if(!autoTask)autoTask=driveGA()};
$('livePause').onclick=async()=>{manualPause=true;autoGA=false;message('liveState','Đã yêu cầu tạm dừng sau thế hệ đang tính')};
$('liveStop').onclick=async()=>{manualPause=false;autoGA=false;await liveControl('stop')};
// Main action starts a paused backend and then advances it incrementally.
$('solve').onclick=async()=>{
  let btn=$('solve');btn.disabled=true;
  result=null;['greedyScore','gaScore','improvement'].forEach(id=>$(id).textContent='—');
  $('metrics').innerHTML='';$('calendar').textContent='Đang chuẩn bị kết quả…';draw([]);
  await startLive(true);
  if(liveJob){$('livePanel').scrollIntoView({behavior:'smooth',block:'start'});$('liveResume').click()}
  else btn.disabled=false;
};
