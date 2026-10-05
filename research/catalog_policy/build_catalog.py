"""One-time authored extension; refuses to overwrite an already versioned bank."""
import json
from pathlib import Path

PATH = Path('app/static/data/catalog-v2.json')


def check(value, expected):
    return {'args': [value], 'expected': expected}


def main():
    bank = json.loads(PATH.read_text(encoding='utf-8'))
    if len(bank['exercises']) != 8:
        raise SystemExit('Expected original eight exercises; not modifying this catalog.')
    bank['skills'] = [
        {'id': 'selection', 'title': 'Lọc và tích lũy', 'description': 'Duyệt danh sách, kiểm tra điều kiện, cộng hoặc đếm.'},
        {'id': 'collections', 'title': 'Bộ nhớ và cấu trúc dữ liệu', 'description': 'Dùng tập hợp hoặc từ điển để ghi nhớ các giá trị đã gặp.'},
        {'id': 'state', 'title': 'Cập nhật trạng thái', 'description': 'Duy trì biến trạng thái qua từng bước của vòng lặp.'},
    ]
    bank['provenance'] = 'Authored Python tasks and primary-skill labels. No human log, expert validation or calibrated difficulty. Existing eight task IDs/tests preserved.'
    bank['exercises'] += [
        dict(id='first-repeat', title='Số đầu tiên gặp lại', concept='Tập hợp & thứ tự', level='Vận dụng',
             functionName='so_gap_lai', description='Viết hàm so_gap_lai(numbers) trả về số đầu tiên được gặp lần thứ hai khi duyệt từ trái sang phải. Không có số lặp thì trả về None.',
             rules=['Chọn theo thời điểm gặp lần thứ hai, không theo giá trị nhỏ nhất.', 'Danh sách rỗng cho kết quả None.'],
             starter='def so_gap_lai(numbers):\n    return None\n',
             examples=[check([3, 1, 1, 3], 1), check([1, 2], None)],
             hints=['Tạo một tập hợp các số đã gặp.', 'Nếu số đang xét đã có trong tập hợp, trả về số đó ngay.', 'Nếu chưa có, thêm vào tập hợp; hết vòng lặp thì trả về None.'],
             takeaway='Bạn đã phân biệt thứ tự xuất hiện và thứ tự lặp lại.',
             tests=[check([3,1,1,3],1),check([],None),check([1,2],None),check([0,0],0),check([-1,2,-1],-1),check([2,2,2],2),check([4,3,2,4,2],4),check([7],None)],
             support='unique', challenge='word-lengths'),
        dict(id='word-lengths', title='Nhóm từ theo độ dài', concept='Từ điển & danh sách', level='Thử thách',
             functionName='nhom_tu', description='Viết hàm nhom_tu(words) trả về từ điển: khóa là chuỗi biểu diễn độ dài từ, giá trị là danh sách các từ có độ dài đó, giữ nguyên thứ tự đầu vào.',
             rules=['Giữ nguyên chữ hoa, chữ thường và các từ trùng.', 'Chuỗi rỗng có độ dài 0. Danh sách rỗng cho kết quả {}.', "Ví dụ: khóa của từ có 2 chữ là chuỗi '2', dùng str(len(word))."],
             starter='def nhom_tu(words):\n    return {}\n',
             examples=[check(['ai','a','to'], {'2':['ai','to'],'1':['a']}), check([], {})],
             hints=['Dùng len(word) để tính độ dài.', 'Mỗi khóa trong từ điển cần chứa một danh sách.', 'Tạo danh sách nếu khóa chưa có, rồi append từ hiện tại.'],
             takeaway='Bạn đã tổ chức các từ thành nhóm và giữ nguyên thứ tự.',
             tests=[check(['ai','a','to'],{'2':['ai','to'],'1':['a']}),check([],{}),check([''],{'0':['']}),check(['A','a'],{'1':['A','a']}),check(['hi','hi'],{'2':['hi','hi']}),check(['abc','d'],{'3':['abc'],'1':['d']}),check(['học','AI'],{'3':['học'],'2':['AI']}),check(['x','','yy'],{'1':['x'],'0':[''],'2':['yy']})],
             support='words', challenge='first-repeat'),
        dict(id='fibonacci', title='Số Fibonacci', concept='Trạng thái trong vòng lặp', level='Thử thách',
             functionName='fibonacci', description='Viết hàm fibonacci(n) trả về số Fibonacci thứ n. Quy ước F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2).',
             rules=['n là số nguyên từ 0 đến 30.', 'Trả về một số nguyên; không in cả dãy.'],
             starter='def fibonacci(n):\n    return 0\n',
             examples=[check(0,0),check(7,13)],
             hints=['Giữ hai số liên tiếp của dãy, khởi đầu là 0 và 1.', 'Mỗi bước cập nhật đồng thời a, b = b, a + b.', 'Sau n bước, a chính là F(n).'],
             takeaway='Bạn đã cập nhật hai trạng thái mà không làm mất giá trị cũ.',
             tests=[check(0,0),check(1,1),check(2,1),check(3,2),check(7,13),check(10,55),check(20,6765),check(30,832040)],
             support='prefix-sums', challenge='streak'),
        dict(id='prefix-sums', title='Tổng đến từng vị trí', concept='Trạng thái & danh sách', level='Vận dụng',
             functionName='tong_tich_luy', description='Viết hàm tong_tich_luy(numbers) trả về danh sách các tổng tính từ đầu đến từng vị trí.',
             rules=['Kết quả có cùng số phần tử với đầu vào.', 'Tính cả số âm; danh sách rỗng cho kết quả [].'],
             starter='def tong_tich_luy(numbers):\n    return []\n',
             examples=[check([2,3,-1],[2,5,4]),check([],[])],
             hints=['Giữ một biến tổng đang chạy, ban đầu bằng 0.', 'Cộng số hiện tại vào tổng.', 'Thêm tổng mới vào danh sách kết quả ở mỗi bước.'],
             takeaway='Bạn đã lưu lại trạng thái tổng sau mỗi bước.',
             tests=[check([2,3,-1],[2,5,4]),check([],[]),check([0],[0]),check([-1,-2],[-1,-3]),check([5],[5]),check([1,1,1],[1,2,3]),check([4,-4,2],[4,0,2]),check([0,0],[0,0])],
             support='sum-positive', challenge='fibonacci'),
    ]
    mapping = {'sum-positive':(0,0), 'count-positive':(0,0), 'sum-even':(0,1), 'count-even':(0,1),
               'maximum':(2,0), 'unique':(1,0), 'words':(1,1), 'streak':(2,2),
               'first-repeat':(1,1), 'word-lengths':(1,2), 'fibonacci':(2,2), 'prefix-sums':(2,1)}
    for exercise in bank['exercises']:
        skill, difficulty = mapping[exercise['id']]
        exercise.update(skill=skill, difficulty=difficulty, cost=1+.2*difficulty)
    PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
