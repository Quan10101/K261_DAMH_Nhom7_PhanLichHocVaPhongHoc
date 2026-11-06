"""ScheduleLab: xếp lịch tuần 7 ngày x 5 ca, Greedy vs Genetic Algorithm.
Python 3.10+, chỉ sử dụng thư viện chuẩn. Phòng và tòa nhà là dữ liệu MÔ PHỎNG.
"""
import argparse
import csv
import json
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

DAYS = ('Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật')
PERIODS_PER_DAY = 5
WEEK_SLOTS = len(DAYS) * PERIODS_PER_DAY
MAX_TEACHER_PERIODS_PER_DAY = 3
CAMPUS_NAMES = {1: 'Cơ sở 1', 2: 'Cơ sở 2', 3: 'Cơ sở chính (CS3)'}
CAMPUS_ADDRESSES = {
    1: '45 Nguyễn Khắc Nhu, TP.HCM',
    2: '233A Phan Văn Trị, TP.HCM',
    3: '69/68 Đặng Thùy Trâm, TP.HCM',
}


@dataclass(frozen=True)
class Course:
    id: int
    students: int
    teacher: int
    group: int
    kind: int
    available: tuple
    preference_weight: float = 2.0


@dataclass(frozen=True)
class Room:
    id: int
    capacity: int
    kind: int
    campus: int = 3
    building: str = 'A'
    code: str = ''


def room_code(room_id, campus, building):
    """Mã minh họa; không khẳng định tồn tại trong danh mục phòng thật của VLU."""
    floor = room_id // 12 + 1
    number = room_id % 12 + 1
    return f'CS{campus}.{building}.{floor:02d}.{number:02d}'


def make_instance(nclasses, nrooms, nslots, seed, preference_weight=2.0):
    if nslots < 1 or nslots > WEEK_SLOTS:
        raise ValueError(f'Số ca phải từ 1 đến {WEEK_SLOTS}')
    rng = random.Random(seed)
    rooms = []
    for j in range(nrooms):
        campus = 1 + j % 3
        building = ('A', 'B', 'C')[(j // 3) % 3]
        rooms.append(Room(j, rng.choice([30, 40, 50, 65, 80]), int(j % 5 == 0),
                          campus, building, room_code(j, campus, building)))
    courses = []
    for i in range(nclasses):
        kind = int(i % 8 == 0)
        students = rng.randint(18, 42 if kind else 65)
        students = min(students, max((r.capacity for r in rooms if r.kind == kind), default=students))
        courses.append(Course(i, students, i % max(3, nclasses // 6),
                              i % max(3, nclasses // 5), kind, tuple(range(nslots)),
                              float(preference_weight)))
    return courses, rooms


def teacher_location_allowed(existing, slot, room):
    """Kiểm tra giáo viên theo NGÀY, không phụ thuộc thứ tự thuật toán xét lớp.

    - Tối đa 3 ca/ngày.
    - Đổi cơ sở trong cùng ngày chỉ khi từ buổi sáng (ca 1–2) sang
      buổi chiều (ca 3–5). Như vậy chỉ qua ranh giới nghỉ trưa ca 2/3.
    - Cùng cơ sở nhưng khác tòa: không được đi giữa hai ca liên tiếp
      ngoại trừ từ ca 2 sang ca 3 (nghỉ trưa).
    """
    day, period = divmod(slot, PERIODS_PER_DAY)
    same_day = [(old_slot, old_room) for old_slot, old_room in existing
                if old_slot // PERIODS_PER_DAY == day]
    if len(same_day) >= MAX_TEACHER_PERIODS_PER_DAY:
        return False
    for old_slot, old_room in same_day:
        old_period = old_slot % PERIODS_PER_DAY
        if old_room.campus != room.campus:
            # Hai ca thuộc hai cơ sở khác nhau phải nằm ở hai phía giờ nghỉ trưa.
            if (old_period < 2) == (period < 2):
                return False
        elif old_room.building != room.building:
            # Di chuyển giữa tòa A/B trong cùng cơ sở cần có khoảng trống,
            # trừ khoảng nghỉ giữa ca 2 và ca 3.
            if abs(old_period - period) == 1 and {old_period, period} != {1, 2}:
                return False
    return True


def decode(order, courses, rooms, nslots, on_assignment=None):
    """Xếp mỗi buổi đúng một lần; mọi ràng buộc cứng được áp dụng khi gán."""
    used_rooms, used_teachers, used_groups = set(), set(), set()
    teacher_daily = {}  # teacher -> [(slot, Room)]
    assignments = {}
    total = 0.0
    for cid in order:
        c = courses[cid]
        choices = []
        for t in c.available:
            if t < 0 or t >= nslots:
                continue
            if (c.teacher, t) in used_teachers or (c.group, t) in used_groups:
                continue
            day = t // PERIODS_PER_DAY
            for room in rooms:
                if room.kind != c.kind or room.capacity < c.students or (room.id, t) in used_rooms:
                    continue
                if not teacher_location_allowed(teacher_daily.get(c.teacher, ()), t, room):
                    continue
                # Chi phí hiện hành, thêm điều kiện địa điểm như ràng buộc cứng.
                cost = (room.capacity - c.students
                        + (4.0 if t % PERIODS_PER_DAY == PERIODS_PER_DAY - 1 else 0.0)
                        + c.preference_weight * ((c.id * 13 + t * 7 + (c.id * t) % 11) % 19))
                choices.append((cost, t, room.id))
        if not choices:
            return None
        cost, t, rid = min(choices)
        room = rooms[rid]
        assignments[cid] = (rid, t)
        total += cost
        used_rooms.add((rid, t))
        used_teachers.add((c.teacher, t))
        used_groups.add((c.group, t))
        teacher_daily.setdefault(c.teacher, []).append((t, room))
        if on_assignment is not None:
            on_assignment({
                'step': len(assignments), 'course': cid + 1, 'room': rid + 1,
                'room_code': room.code or room_code(room.id, room.campus, room.building),
                'campus': room.campus, 'building': room.building,
                'slot': t + 1, 'day': DAYS[t // PERIODS_PER_DAY], 'period': t % PERIODS_PER_DAY + 1,
                'increment': round(cost, 4), 'cumulative': round(total, 4),
                'students': c.students, 'teacher': c.teacher + 1, 'group': c.group + 1,
            })
    return {'objective': total, 'assignments': assignments}


def check_schedule(result, courses, rooms, nslots):
    """Bộ kiểm tra độc lập: kiểm tra cả giới hạn/ngày lẫn quy tắc di chuyển."""
    if result is None:
        return False, 'Chưa có lịch'
    assignments = result.get('assignments', {})
    if set(assignments) != {c.id for c in courses}:
        return False, 'Thiếu hoặc thừa lớp'
    room_map = {r.id: r for r in rooms}
    occupied_rooms, occupied_teachers, occupied_groups = set(), set(), set()
    teacher_schedule = {}
    for c in courses:
        rid, slot = assignments[c.id]
        if rid not in room_map or slot not in c.available or not 0 <= slot < nslots:
            return False, 'Phòng hoặc ca không khả dụng'
        r = room_map[rid]
        if r.capacity < c.students or r.kind != c.kind:
            return False, 'Sức chứa hoặc loại phòng không hợp lệ'
        for key, used in [((rid, slot), occupied_rooms), ((c.teacher, slot), occupied_teachers),
                          ((c.group, slot), occupied_groups)]:
            if key in used:
                return False, 'Trùng phòng, giảng viên hoặc nhóm'
            used.add(key)
        teacher_schedule.setdefault(c.teacher, []).append((slot, r))
    for entries in teacher_schedule.values():
        for idx, (slot, room) in enumerate(entries):
            if not teacher_location_allowed(entries[:idx] + entries[idx + 1:], slot, room):
                return False, 'Giảng viên vượt 3 ca/ngày hoặc đổi địa điểm sai quy tắc'
    return True, 'Hợp lệ'


def genetic(courses, rooms, slots, seed, population=35, generations=65,
            on_generation=None, checkpoint=None, mutation_probability=0.4):
    rng = random.Random(seed)
    n = len(courses)
    base = list(range(n))
    pop = [base[:]] + [rng.sample(base, n) for _ in range(population - 1)]
    cache = {}

    def score(order):
        key = tuple(order)
        if key not in cache:
            result = decode(order, courses, rooms, slots)
            cache[key] = result['objective'] if result else 1e9
        return cache[key]

    best = None
    history = []
    for g in range(generations):
        if checkpoint is not None:
            checkpoint()
        pop.sort(key=score)
        if best is None or score(pop[0]) < score(best):
            best = pop[0][:]
        values = [score(item) for item in pop]
        record = {'generation': g + 1, 'best_objective': score(best),
                  'mean_objective': sum(values) / len(values),
                  'feasible_count': sum(v < 1e9 for v in values),
                  'evaluations': len(cache)}
        history.append(record)
        if on_generation is not None:
            on_generation(record, decode(best, courses, rooms, slots))
        elites = [p[:] for p in pop[:max(2, population // 5)]]
        offspring = elites[:]
        while len(offspring) < population:
            p1 = rng.choice(pop[:max(3, population // 2)])
            p2 = rng.choice(pop[:max(3, population // 2)])
            a, b = sorted(rng.sample(range(n), 2))
            child = [None] * n
            child[a:b] = p1[a:b]
            rest = (v for v in p2 if v not in child)
            child = [next(rest) if v is None else v for v in child]
            if rng.random() < mutation_probability:
                u, v = rng.sample(range(n), 2)
                child[u], child[v] = child[v], child[u]
            offspring.append(child)
        pop = offspring
    pop.sort(key=score)
    if score(pop[0]) < score(best):
        best = pop[0][:]
    return decode(best, courses, rooms, slots), history


def save_schedule(path, result, courses, rooms):
    if result is None:
        return
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['course', 'students', 'teacher', 'group', 'room_code',
                         'campus', 'building', 'capacity', 'day', 'period', 'slot'])
        for c in courses:
            rid, t = result['assignments'][c.id]
            r = rooms[rid]
            writer.writerow([c.id + 1, c.students, c.teacher + 1, c.group + 1,
                             r.code, r.campus, r.building, r.capacity,
                             DAYS[t // PERIODS_PER_DAY], t % PERIODS_PER_DAY + 1, t + 1])


def main():
    parser = argparse.ArgumentParser(description='Demo tối ưu lịch học 7 ngày x 5 ca')
    parser.add_argument('--classes', type=int, default=30)
    parser.add_argument('--rooms', type=int, default=10)
    parser.add_argument('--slots', type=int, default=WEEK_SLOTS)
    parser.add_argument('--trials', type=int, default=10)
    parser.add_argument('--seed', type=int, default=20261022)
    parser.add_argument('--population', type=int, default=35)
    parser.add_argument('--generations', type=int, default=65)
    parser.add_argument('--mutation-probability', type=float, default=0.4)
    parser.add_argument('--output', default='results_schedule')
    parser.add_argument('--preference-weight', type=float, default=2.0)
    a = parser.parse_args()
    if not 0 <= a.mutation_probability <= 1:
        parser.error('Xác suất đột biến phải từ 0 đến 1')
    if min(a.classes, a.rooms, a.slots, a.trials, a.population, a.generations) < 1 \
            or a.population < 3 or a.classes < 2 or a.slots > WEEK_SLOTS:
        parser.error('Cần classes>=2, population>=3; 1<=slots<=35')
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for trial in range(a.trials):
        courses, rooms = make_instance(a.classes, a.rooms, a.slots,
                                       a.seed + trial, a.preference_weight)
        t0 = time.perf_counter()
        greedy = decode(list(range(len(courses))), courses, rooms, a.slots)
        greedy_time = time.perf_counter() - t0
        t1 = time.perf_counter()
        ga, history = genetic(courses, rooms, a.slots, a.seed + 10000 + trial,
                              a.population, a.generations, mutation_probability=a.mutation_probability)
        ga_time = time.perf_counter() - t1
        row = {'trial': trial + 1, 'instance_seed': a.seed + trial,
               'greedy_objective': greedy['objective'] if greedy else None,
               'ga_objective': ga['objective'] if ga else None,
               'greedy_feasible': int(greedy is not None), 'ga_feasible': int(ga is not None),
               'greedy_seconds': round(greedy_time, 6), 'ga_seconds': round(ga_time, 6)}
        rows.append(row)
        if trial == 0:
            save_schedule(out / 'greedy_schedule.csv', greedy, courses, rooms)
            save_schedule(out / 'ga_schedule.csv', ga, courses, rooms)
            with open(out / 'ga_convergence.csv', 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=['generation', 'best_objective'])
                w.writeheader()
                w.writerows({'generation': h['generation'], 'best_objective': h['best_objective']}
                            for h in history)
        print(f"Trial {trial+1}/{a.trials}: Greedy={row['greedy_objective']} GA={row['ga_objective']}")
    with open(out / 'trials.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {}
    for alg in ['greedy', 'ga']:
        vals = [r[alg + '_objective'] for r in rows if r[alg + '_objective'] is not None]
        summary[alg] = {'success_rate': len(vals)/len(rows),
                        'mean_objective': statistics.mean(vals) if vals else None,
                        'std_objective': statistics.stdev(vals) if len(vals)>1 else 0 if vals else None,
                        'mean_seconds': statistics.mean(r[alg+'_seconds'] for r in rows)}
    (out / 'summary.json').write_text(json.dumps({'parameters': vars(a), 'metrics': summary},
                                                 indent=2, ensure_ascii=False), encoding='utf-8')
    print('Đã lưu CSV/JSON tại:', out.resolve())
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
