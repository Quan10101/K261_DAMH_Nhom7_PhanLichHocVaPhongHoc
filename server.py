import math
"""ScheduleLab: local Python backend with UI. Python 3.10+ standard library only."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, threading, uuid, time, csv, statistics, platform, webbrowser, os, datetime
from schedule_optimizer import (make_instance, decode, genetic, check_schedule,
    room_code, WEEK_SLOTS, PERIODS_PER_DAY, DAYS, CAMPUS_NAMES, CAMPUS_ADDRESSES, Room, Course)

BASE=Path(__file__).resolve().parent
os.chdir(BASE)
JOBS={}
LOCK=threading.Lock()

def serialize(courses, rooms, slots, seed):
    return {
        'seed': seed, 'slots': slots, 'days': list(DAYS),
        'periods_per_day': PERIODS_PER_DAY, 'max_teacher_periods_per_day': 3,
        'campus_names': CAMPUS_NAMES, 'campus_addresses': CAMPUS_ADDRESSES,
        'courses': [dict(id=c.id, students=c.students, teacher=c.teacher, group=c.group,
                         kind=c.kind, available=list(c.available),
                         preference_weight=c.preference_weight) for c in courses],
        'rooms': [dict(id=r.id, code=r.code, campus=r.campus, building=r.building,
                       capacity=r.capacity, kind=r.kind) for r in rooms],
    }


def from_data(data):
    courses = [Course(int(c['id']), int(c['students']), int(c['teacher']), int(c['group']),
                      int(c['kind']), tuple(map(int, c['available'])),
                      float(c.get('preference_weight', 2.0))) for c in data['courses']]
    rooms = []
    for r in data['rooms']:
        rid = int(r['id'])
        campus = int(r.get('campus', 3))
        building = str(r.get('building', 'A')).upper()
        if campus not in CAMPUS_NAMES or building not in ('A', 'B', 'C'):
            raise ValueError('Cơ sở phải từ CS1–CS3; tòa nhà là A, B hoặc C')
        # Code được sinh lại từ ID, cơ sở, tòa nhà; không tin chuỗi từ trình duyệt.
        rooms.append(Room(rid, int(r['capacity']), int(r['kind']), campus,
                          building, room_code(rid, campus, building)))
    slots = int(data['slots'])
    if not (2 <= len(courses) <= 120 and 2 <= len(rooms) <= 50 and slots == WEEK_SLOTS):
        raise ValueError('Cần 2–120 lớp, 2–50 phòng, lịch 35 ca/tuần (7 ngày × 5 ca)')
    if [c.id for c in courses] != list(range(len(courses))) or [r.id for r in rooms] != list(range(len(rooms))):
        raise ValueError('ID lớp/phòng phải liên tiếp từ 0')
    if any(not math.isfinite(c.preference_weight) or c.preference_weight < 0 or c.preference_weight > 20 for c in courses):
        raise ValueError('Trọng số ưu tiên giờ phải từ 0 đến 20')
    if any(c.students < 1 or c.teacher < 0 or c.group < 0 or c.kind not in (0, 1)
           or not c.available or any(t < 0 or t >= slots for t in c.available) for c in courses):
        raise ValueError('Dữ liệu lớp không hợp lệ')
    if any(r.capacity < 1 or r.capacity > 1000 or r.kind not in (0, 1) for r in rooms):
        raise ValueError('Sức chứa hoặc loại phòng không hợp lệ')
    return courses, rooms, slots


def result_json(res, courses, rooms, slots):
    if res is None:
        return {'feasible': False, 'objective': None, 'assignments': []}
    valid, reason = check_schedule(res, courses, rooms, slots)
    if not valid:
        return {'feasible': False, 'objective': None, 'assignments': [], 'reason': reason}
    rows = []
    for c in courses:
        rid, t = res['assignments'][c.id]
        r = rooms[rid]
        rows.append({'course': c.id, 'room': rid, 'room_code': r.code,
                     'campus': r.campus, 'building': r.building, 'capacity': r.capacity,
                     'slot': t, 'day': t // PERIODS_PER_DAY, 'period': t % PERIODS_PER_DAY + 1,
                     'students': c.students, 'teacher': c.teacher, 'group': c.group,
                     'kind': c.kind})
    return {'feasible': True, 'objective': res['objective'], 'assignments': rows}


def mutation_value(data):
    value=float(data.get('mutation_probability',0.4))
    if not math.isfinite(value) or not 0<=value<=1:
        raise ValueError('Xác suất đột biến phải trong khoảng 0 đến 1')
    return value

def solve(data):
    courses,rooms,slots=from_data(data['instance'])
    pop=int(data.get('population',35));gens=int(data.get('generations',65));seed=int(data.get('ga_seed',42));mutation=mutation_value(data)
    if not 3<=pop<=150 or not 2<=gens<=250:raise ValueError('Quần thể 3–150, thế hệ 2–250')
    t=time.perf_counter(); gr=decode(list(range(len(courses))),courses,rooms,slots); grms=(time.perf_counter()-t)*1000
    t=time.perf_counter();ga,history=genetic(courses,rooms,slots,seed,pop,gens,mutation_probability=mutation);gams=(time.perf_counter()-t)*1000
    return {'greedy':dict(result_json(gr,courses,rooms,slots),runtime_ms=round(grms,3)),'ga':dict(result_json(ga,courses,rooms,slots),runtime_ms=round(gams,3)),'history':history,'parameters':{'population':pop,'generations':gens,'ga_seed':seed,'mutation_probability':mutation}}


def interactive_solve(job_id, data):
    job = JOBS[job_id]
    try:
        courses, rooms, slots = from_data(data['instance'])
        pop = int(data.get('population', 35)); gens = int(data.get('generations', 65)); seed = int(data.get('ga_seed', 42)); mutation=mutation_value(data)
        if not 3 <= pop <= 150 or not 2 <= gens <= 250: raise ValueError('Quần thể 3–150, thế hệ 2–250')
        start = time.perf_counter()
        greedy = decode(list(range(len(courses))), courses, rooms, slots)
        greedy_ms = (time.perf_counter() - start) * 1000
        with LOCK:
            job.update(greedy=dict(result_json(greedy, courses, rooms, slots), runtime_ms=round(greedy_ms, 3)), state='running')
        start = time.perf_counter()
        def checkpoint():
            # Pause and step only at generation boundaries, without artificially delaying calculations.
            while True:
                with LOCK:
                    stopped = job['stop_requested']
                    paused = job['paused']
                    steps = job['step_tokens']
                    if stopped: raise InterruptedError('Đã dừng theo yêu cầu')
                    if steps > 0:
                        job['step_tokens'] -= 1
                        job['state'] = 'stepping'
                        return
                    if not paused:
                        job['state'] = 'running'
                        return
                    job['state'] = 'paused'
                if stopped: raise InterruptedError('Đã dừng theo yêu cầu')
                time.sleep(.06)
        def update(record, best):
            elapsed = (time.perf_counter() - start) * 1000
            with LOCK:
                job['history'].append(record)
                job['current_generation'] = record['generation']
                job['best_so_far'] = dict(result_json(best, courses, rooms, slots), runtime_ms=round(elapsed, 3))
                job['log'].append({'generation':record['generation'], 'objective':record['best_objective'], 'mean':round(record['mean_objective'], 2), 'feasible':record['feasible_count'], 'evaluations':record['evaluations'], 'runtime_ms':round(elapsed, 2)})
        ga, history = genetic(courses, rooms, slots, seed, pop, gens, on_generation=update, checkpoint=checkpoint, mutation_probability=mutation)
        elapsed=(time.perf_counter()-start)*1000
        with LOCK:
            job.update(ga=dict(result_json(ga,courses,rooms,slots),runtime_ms=round(elapsed,3)),state='completed',done=True)
    except InterruptedError:
        with LOCK: job.update(state='stopped',done=True)
    except Exception as exc:
        with LOCK: job.update(state='error',error=str(exc),done=True)


def run_job(job_id,config):
    try:
        trials=int(config['trials']);seed=int(config['seed']);pop=int(config['population']);gens=int(config['generations']);mutation=mutation_value(config)
        scenario_config=config['scenarios']
        scenarios=[tuple(scenario_config[label][field] for field in ('classes','rooms','slots')) for label in 'ABC']
        folder=BASE/'results'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        folder.mkdir(parents=True,exist_ok=True)
        records=[];histories=[]
        delay_ms=max(0,min(250,int(config.get('display_delay_ms',45))))
        for k in range(trials):
            with LOCK:
                JOBS[job_id].update(current_trial=k+1,current_scenario=('A','B','C')[k%3],
                    current_phase='Đang tạo dữ liệu',current_generation=0,total_generations=gens,
                    current_greedy=None,current_best=None,current_mean=None,
                    current_feasible=None,current_evaluations=0,current_history=[],
                    current_elapsed_ms=0,current_greedy_steps=[],current_greedy_step=0,current_greedy_total=scenarios[k%3][0],current_greedy_partial=0)

            label=('A','B','C')[k%3];a,b,c=scenarios[k%3];instance_seed=seed+k
            courses,rooms=make_instance(a,b,c,instance_seed,float(config.get('preference_weight',2.0)))
            # Theo dõi Greedy thật theo từng phép gán; chỉ đo thời gian tính, không tính thời gian hiển thị.
            greedy_start=time.perf_counter(); greedy_delay=[0.0]
            greedy_trace=[]
            def on_greedy_assignment(step):
                elapsed=(time.perf_counter()-greedy_start-greedy_delay[0])*1000
                entry=dict(step, runtime_ms=round(elapsed,4))
                greedy_trace.append(entry)
                with LOCK:
                    JOBS[job_id].update(current_phase='Đang tính Greedy',
                        current_greedy_step=step['step'],current_greedy_partial=step['cumulative'],
                        current_greedy_steps=greedy_trace[-120:])
                if delay_ms:
                    before=time.perf_counter()
                    time.sleep(delay_ms/1000)
                    greedy_delay[0]+=time.perf_counter()-before
            gr=decode(list(range(a)),courses,rooms,c,on_assignment=on_greedy_assignment)
            gmt=(time.perf_counter()-greedy_start-greedy_delay[0])*1000
            with LOCK: JOBS[job_id].update(current_phase='Greedy hoàn thành, bắt đầu GA',current_greedy=gr['objective'] if gr else None)
            # Duration excludes presentation delay so experimental runtime remains measurable.
            ga_started=time.perf_counter()
            last_generation=[ga_started]
            excluded_delay=[0.0]
            def on_generation(rec, best):
                now=time.perf_counter()
                runtime=(now-ga_started-excluded_delay[0])*1000
                with LOCK:
                    j=JOBS[job_id]
                    j['current_generation']=rec['generation']
                    j['current_phase']='Đang tính GA'
                    j['current_best']=rec['best_objective'] if rec['best_objective']<1e9 else None
                    j['current_mean']=round(rec['mean_objective'],3)
                    j['current_feasible']=rec['feasible_count']
                    j['current_evaluations']=rec['evaluations']
                    j['current_elapsed_ms']=round(runtime,3)
                    j['current_history'].append({'generation':rec['generation'], 'best':j['current_best'],
                        'mean':j['current_mean'], 'feasible':rec['feasible_count'],
                        'evaluations':rec['evaluations'], 'runtime_ms':j['current_elapsed_ms']})
                if delay_ms:
                    began=time.perf_counter()
                    time.sleep(delay_ms/1000)
                    excluded_delay[0]+=time.perf_counter()-began
            ga,history=genetic(courses,rooms,c,seed+100000+k,pop,gens,on_generation=on_generation,mutation_probability=mutation)
            gam=(time.perf_counter()-ga_started-excluded_delay[0])*1000
            row={'trial':k+1,'scenario':label,'instance_seed':instance_seed,'classes':a,'rooms':b,'slots':c,
                 'experiment_seed':seed,'ga_seed':seed+100000+k,'population':pop,'generations':gens,'mutation_probability':mutation,'preference_weight':float(config.get('preference_weight',2.0)),
                 'greedy_objective':gr['objective'] if gr else '', 'ga_objective':ga['objective'] if ga else '',
                 'greedy_feasible':int(gr is not None),'ga_feasible':int(ga is not None),
                 'greedy_ms':round(gmt,3),'ga_ms':round(gam,3)}
            records.append(row)
            if k==0:histories=history
            with LOCK:JOBS[job_id].update(completed=k+1,last=row,records=records[-60:], current_phase='Hoàn tất lượt '+str(k+1))
        with (folder/'runs.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        summary=[]
        for label in 'ABC':
            subset=[r for r in records if r['scenario']==label]
            for alg in ('greedy','ga'):
                v=[float(r[alg+'_objective']) for r in subset if r[alg+'_objective']!='']
                summary.append({'scenario':label,'algorithm':alg,'runs':len(subset),'feasible_rate':len(v)/len(subset) if subset else 0,
                  'mean_objective':statistics.mean(v) if v else None,'std_objective':statistics.stdev(v) if len(v)>1 else 0 if v else None,
                  'mean_ms':statistics.mean(r[alg+'_ms'] for r in subset) if subset else None})
        with (folder/'summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
        with (folder/'cau_hinh_thuc_nghiem.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.writer(f);writer.writerow(['Tham so','Gia tri']);
            for key,value in [(f'kich_ban_{label}',f'{a} lop, {b} phong, {c} ca') for label,(a,b,c) in zip('ABC',scenarios)]+[('so_luot',trials),('seed_thuc_nghiem',seed),('quan_the_GA',pop),('so_the_he_GA',gens),('xac_suat_dot_bien',mutation),('trong_so_uu_tien_gio',float(config.get('preference_weight',2.0))),('seed_du_lieu_luot_k','seed_thuc_nghiem + k - 1'),('seed_GA_luot_k','seed_thuc_nghiem + 100000 + k - 1')]:writer.writerow([key,value])
        metadata={'config':config,'scenarios':scenarios,'python':platform.python_version(),'platform':platform.platform(),'notes':'Synthetic rooms and capacity. Fixed 7 days x 5 periods; teacher max 3/day; campus switches only across lunch boundary 2/3; building switches between adjacent periods only across lunch. Sunday is simulated and not VLU regular schedule. Times are algorithm-only.'}
        (folder/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        (folder/'convergence_first_trial.json').write_text(json.dumps(histories,ensure_ascii=False,indent=2),encoding='utf-8')
        with LOCK:JOBS[job_id].update(done=True,current_phase='Hoàn thành toàn bộ',summary=summary,result_folder=str(folder.relative_to(BASE)).replace('\\','/'))
    except Exception as exc:
        with LOCK:JOBS[job_id].update(done=True,error=str(exc))

class Handler(SimpleHTTPRequestHandler):
    def json_reply(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith('/api/live/status/'):
            jid=path.rsplit('/',1)[-1]
            with LOCK:
                job=JOBS.get(jid)
                item={k:v for k,v in job.items() if k not in ('stop_requested','paused','step_tokens')} if job and job.get('type')=='live' else None
            return self.json_reply(item if item else {'error':'Không tìm thấy'},200 if item else 404)
        if path.startswith('/api/status/'):
            jid=path.rsplit('/',1)[-1]
            with LOCK:item=dict(JOBS[jid]) if jid in JOBS else None
            return self.json_reply(item if item else {'error':'Không tìm thấy'},200 if item else 404)
        return super().do_GET()
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length',0))
            if length>200000:raise ValueError('Dữ liệu quá lớn')
            data=json.loads(self.rfile.read(length))
            path=urlparse(self.path).path
            if path=='/api/generate':
                n=int(data.get('classes',18));m=int(data.get('rooms',8));s=int(data.get('slots',WEEK_SLOTS));seed=int(data.get('seed',2026))
                if not (2<=n<=120 and 2<=m<=50 and s==WEEK_SLOTS):raise ValueError('Cần 2–120 lớp, 2–50 phòng, cố định 35 ca (7 ngày × 5 ca)')
                weight=float(data.get('preference_weight',2.0))
                if not 0<=weight<=20:raise ValueError('Ưu tiên giờ phải từ 0 đến 20')
                c,r=make_instance(n,m,s,seed,weight);return self.json_reply(serialize(c,r,s,seed))
            if path=='/api/solve':return self.json_reply(solve(data))
            if path=='/api/live/start':
                courses,rooms,slots=from_data(data['instance'])
                pop=int(data.get('population',35));gens=int(data.get('generations',65))
                if not 3<=pop<=150 or not 2<=gens<=250:raise ValueError('Quần thể 3–150, thế hệ 2–250')
                jid=uuid.uuid4().hex
                with LOCK: JOBS[jid]={'type':'live','done':False,'state':'starting','paused':bool(data.get('start_paused', True)), 'step_tokens':0,'stop_requested':False, 'current_generation':0,'total_generations':gens,'history':[], 'log':[], 'greedy':None, 'ga':None, 'best_so_far':None, 'error':None}
                threading.Thread(target=interactive_solve,args=(jid,data),daemon=True).start()
                return self.json_reply({'job_id':jid})
            if path.startswith('/api/live/control/'):
                jid=path.rsplit('/',1)[-1];action=data.get('action')
                if action not in ('pause','resume','step','stop'):raise ValueError('Điều khiển không hợp lệ')
                with LOCK:
                    j=JOBS.get(jid)
                    if not j or j.get('type')!='live':raise ValueError('Không tìm thấy tiến trình')
                    if action=='pause':j['paused']=True
                    if action=='resume':j['paused']=False;j['step_tokens']=0
                    if action=='step':j['paused']=True;j['step_tokens']+=1
                    if action=='stop':j['stop_requested']=True;j['paused']=False
                return self.json_reply({'ok':True})
            if path=='/api/experiment/start':
                tr=int(data.get('trials',120));pop=int(data.get('population',25));gens=int(data.get('generations',40))
                mutation_value(data)
                if not (1<=tr<=500 and 3<=pop<=150 and 2<=gens<=250):raise ValueError('Số lượt 1–500, quần thể 3–150, thế hệ 2–250')
                data['trials']=tr;data['population']=pop;data['generations']=gens;data['seed']=int(data.get('seed',2026))
                configs=data.get('scenarios',{'A':{'classes':12,'rooms':8,'slots':35},'B':{'classes':20,'rooms':10,'slots':35},'C':{'classes':30,'rooms':15,'slots':35}})
                if not isinstance(configs,dict) or set(configs)!=set('ABC'):raise ValueError('Cần đủ các kịch bản A, B, C')
                normalized={}
                for label in 'ABC':
                    source=configs[label]
                    if not isinstance(source,dict):raise ValueError('Cấu hình kịch bản không hợp lệ')
                    vals={}
                    for field,low,high in [('classes',2,120),('rooms',2,50),('slots',WEEK_SLOTS,WEEK_SLOTS)]:
                        raw=source.get(field)
                        if isinstance(raw,bool) or not isinstance(raw,int) or not low<=raw<=high:raise ValueError(f'Kịch bản {label}: {field} phải từ {low} đến {high}')
                        vals[field]=raw
                    normalized[label]=vals
                data['scenarios']=normalized
                jid=uuid.uuid4().hex
                with LOCK:JOBS[jid]={'done':False,'completed':0,'total':tr,'last':None,'records':[],'error':None,'summary':None,'current_trial':0,'current_scenario':None,'current_phase':'Chuẩn bị','current_generation':0,'total_generations':gens,'current_history':[],'current_greedy':None,'current_best':None,'current_mean':None,'current_feasible':None,'current_evaluations':0,'current_elapsed_ms':0,'current_greedy_steps':[],'current_greedy_step':0,'current_greedy_total':0,'current_greedy_partial':0}
                threading.Thread(target=run_job,args=(jid,data),daemon=True).start()
                return self.json_reply({'job_id':jid})
            return self.json_reply({'error':'Không tìm thấy API'},404)
        except (ValueError,KeyError,TypeError) as exc:return self.json_reply({'error':str(exc)},400)
        except Exception as exc:return self.json_reply({'error':repr(exc)},500)
    def log_message(self,fmt,*args):pass

if __name__=='__main__':
    port=8765; url=f'http://127.0.0.1:{port}'
    try:server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    except OSError as exc:raise SystemExit(f'Không mở được cổng {port}: {exc}')
    print('ScheduleLab:',url,flush=True)
    threading.Timer(.7,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
