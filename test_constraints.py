"""Kiểm thử độc lập ràng buộc lịch và thuộc tính phòng (python test_constraints.py)."""
from schedule_optimizer import (Course, Room, make_instance, decode, genetic,
                                check_schedule, teacher_location_allowed, WEEK_SLOTS)
from server import serialize, from_data, result_json


def course(i, teacher=0, group=None, students=20, kind=0):
    return Course(i, students, teacher, i if group is None else group, kind,
                  tuple(range(WEEK_SLOTS)))


def test_teacher_cap():
    rooms = [Room(0, 40, 0, 3, 'A', 'CS3.A.01.01')]
    courses = [course(i) for i in range(4)]
    invalid = {'objective': 0, 'assignments': {i: (0, i) for i in range(4)}}
    assert not check_schedule(invalid, courses, rooms, WEEK_SLOTS)[0], '4 ca/ngày phải bị loại'
    valid = {'objective': 0, 'assignments': {i: (0, i) for i in range(3)}}
    assert check_schedule(valid, courses[:3], rooms, WEEK_SLOTS)[0]
    invalid_days = {'objective':0,'assignments':{i:(0,i) for i in range(3)} | {3:(0,5)}}
    assert check_schedule(invalid_days, courses, rooms, WEEK_SLOTS)[0]


def test_campus_midday():
    a, b = Room(0, 40, 0, 1, 'A', 'CS1.A.01.01'), Room(1, 40, 0, 3, 'A', 'CS3.A.01.01')
    courses=[course(0),course(1)]
    for earlier,later,expected in [(0,1,False),(1,2,True),(0,4,True),(2,3,False),(1,6,True)]:
        assignment = {'objective': 0, 'assignments': {0: (0, earlier), 1: (1, later)}}
        valid,_ = check_schedule(assignment,courses,[a,b],WEEK_SLOTS)
        assert valid==expected,(earlier,later,valid,expected)


def test_building_movement():
    a,b=Room(0,40,0,3,'A','CS3.A.01.01'),Room(1,40,0,3,'B','CS3.B.01.02')
    courses=[course(0),course(1)]
    for period_a,period_b,expected in [(0,1,False),(1,2,True),(2,3,False),(0,2,True),(3,4,False)]:
        res={'objective':0,'assignments':{0:(0,period_a),1:(1,period_b)}}
        valid,_=check_schedule(res,courses,[a,b],WEEK_SLOTS)
        assert valid==expected,(period_a,period_b,valid,expected)


def test_room_group_clash():
    a,b=Room(0,40,0,3,'A','CS3.A.01.01'),Room(1,40,0,3,'A','CS3.A.01.02')
    courses=[course(0,0,0),course(1,1,0)]
    assert not check_schedule({'objective':0,'assignments':{0:(0,0),1:(1,0)}},courses,[a,b],WEEK_SLOTS)[0]
    courses=[course(0,0,0),course(1,1,1)]
    assert not check_schedule({'objective':0,'assignments':{0:(0,0),1:(0,0)}},courses,[a,b],WEEK_SLOTS)[0]


def test_room_capacity():
    a=Room(0,25,0,3,'A','CS3.A.01.01')
    assert not check_schedule({'objective':0,'assignments':{0:(0,0)}},[course(0,students=40)],[a],WEEK_SLOTS)[0]


def test_generated_and_algorithms():
    for n,r,seed in ((18,8,2026),(30,8,2027),(35,10,2028),(50,15,2029)):
        courses,rooms=make_instance(n,r,WEEK_SLOTS,seed)
        instance=serialize(courses,rooms,WEEK_SLOTS,seed)
        courses2,rooms2,slots=from_data(instance)
        assert rooms2==rooms
        gr=decode(list(range(n)),courses2,rooms2,slots)
        if gr:
            assert check_schedule(gr,courses2,rooms2,slots)[0]
            assert result_json(gr,courses2,rooms2,slots)['feasible']
        ga,history=genetic(courses2,rooms2,slots,seed+10000,population=8,generations=4)
        if ga:assert check_schedule(ga,courses2,rooms2,slots)[0]
        assert len(history)==4
        print(f'{n} lớp/{r} phòng: Greedy={gr is not None}, GA={ga is not None}')


def main():
    test_teacher_cap()
    test_campus_midday()
    test_building_movement()
    test_room_group_clash()
    test_room_capacity()
    test_generated_and_algorithms()
    print('PASS: ràng buộc ngày/giờ/đổi cơ sở/đổi tòa/phòng/sức chứa/Greedy/GA')


if __name__ == '__main__':
    main()
