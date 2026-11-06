# ScheduleLab — Tối ưu lịch học & phân phòng (Python + web)

## Bản cập nhật: 7 ngày, 5 ca/ngày, cơ sở và tòa nhà (06/11/2026)

- **Thời khóa biểu:** hiển thị cố định Thứ Hai đến Chủ nhật, 5 ca/ngày = **35 ca/tuần**. Trong giao diện web, số ca được khóa ở 35 cho tất cả kịch bản A/B/C.
- **Giới hạn giảng viên:** không trùng ca và tối đa **3 ca dạy trong cùng một ngày** (cộng cả 3 cơ sở).
- **Di chuyển giữa các cơ sở:** một giảng viên chỉ được đổi cơ sở tại ranh giới nghỉ trưa **ca 2 → ca 3**. Cụ thể, các ca 1–2 cùng ngày phải ở cùng một cơ sở, các ca 3–5 cùng ngày ở cùng một cơ sở; giữa hai nhóm có thể đổi. Không chuyển cơ sở từ ca 1→2 hoặc ca 3→4→5.
- **Di chuyển giữa tòa nhà trong cùng cơ sở:** nếu hai ca liền nhau thì phải cùng tòa; ngoại lệ duy nhất là giữa ca 2→3. Nếu có ít nhất một ca trống thì có thể đổi tòa trong cùng cơ sở.
- **Phòng học:** danh sách có mã, cơ sở CS1/CS2/CS3, tòa A/B/C, sức chứa và loại phòng. Có thể chỉnh các giá trị trong **Danh sách phòng học** rồi nhấn **Áp dụng thay đổi phòng**. Chạy lại Greedy & GA để áp dụng. Các đợt **Thực nghiệm hàng loạt** sử dụng danh sách phòng mô phỏng được sinh riêng theo cấu hình từng kịch bản, không dùng bảng phòng đã sửa của lần chạy đơn.
- **Đúng ràng buộc:** ngoài kiểm tra của bộ giải mã Greedy/GA, server còn chạy một bộ kiểm tra lịch độc lập trước khi trả trạng thái hợp lệ.
- **Chủ nhật:** Văn Lang thông thường tổ chức giảng dạy từ Thứ Hai đến Thứ Bảy theo quy chế đào tạo; Chủ nhật trong app là **ngày giả lập để thỏa yêu cầu mô hình 7 ngày**, không khẳng định lịch dạy chính thức.
- **5 ca/ngày:** đây là **đơn vị mô hình hóa**, không phải bảng tiết/giờ được xác nhận của VLU. Ranh giới ca 2/ca 3 được giả định là giờ nghỉ trưa cho phép chuyển cơ sở.
- **Địa chỉ cơ sở tham khảo từ VLU:** CS1: 45 Nguyễn Khắc Nhu; CS2: 233A Phan Văn Trị; CS3 (cơ sở chính): 69/68 Đặng Thùy Trâm, TP.HCM. **Tên tòa, mã phòng, số ghế là dữ liệu mô phỏng, không phải danh mục thật**.
- **So sánh số liệu:** sửa ràng buộc và chuyển sang 35 ca khiến các kết quả mới **không thể đem đối chiếu trực tiếp** với 240 lượt thực nghiệm cũ trong báo cáo. Cần chạy lại nếu báo cáo muốn sử dụng luật xếp lịch mới.

**Cách tự kiểm thử:** chạy `python test_constraints.py` (không cần cài thư viện ngoài). Đã có các trường hợp giảng viên dạy 4 ca/ngày, đổi cơ sở trái quy tắc, đổi tòa liền ca, thiếu chỗ ngồi và xung đột lịch.

**Nguồn tham khảo:**
- Quy chế đào tạo: https://vhub.vlu.edu.vn/quy-che-dao-tao
- Địa chỉ Văn Lang: https://tuyensinh.vlu.edu.vn/ho-so/cap-nhat-dia-chi

## Chạy trên Windows

Nhấp đúp `MO_SCHEDULELAB.bat`, hoặc mở terminal tại thư mục này và chạy:

```bat
python server.py
```

Trình duyệt tự mở tại http://127.0.0.1:8765/. Python 3.10+; không cần pip. Nhấn Ctrl+C ở cửa sổ lệnh để tắt.

## Kiến trúc

- `server.py`: server HTTP và API Python, xử lý tạo dữ liệu, chạy Greedy/GA, batch experiments.
- `schedule_optimizer.py`: **thuật toán chạy thực sự bằng Python**, có thể chạy độc lập bằng CMD.
- `index.html`, `static/style.css`, `static/app.js`: chỉ có chức năng UI, hiển thị lịch và biểu đồ, không chạy thuật toán tối ưu.
- `results/`: tự sinh thư mục theo mốc chạy, chứa `runs.csv`, `summary.csv`, `metadata.json`, `convergence_first_trial.json`.

## Mô hình

Biến nhị phân x[i,r,t] ứng với lớp i, phòng r, ca t. Ràng buộc cứng: lớp được xếp đúng một lần; không đụng phòng, giảng viên hoặc nhóm; đúng loại phòng và đủ chỗ. Objective: min chỗ ngồi dư + phạt ca cuối + phạt ưu tiên khung giờ riêng mỗi lớp (dữ liệu giả lập, xác định theo ID lớp/ca, trọng số cấu hình).

Greedy duyệt lớp theo thứ tự và chọn vị trí hợp lệ rẻ nhất. GA tối ưu hoán vị thứ tự lớp, giải mã bằng Greedy; do vậy GA tìm kiếm **trên thứ tự ưu tiên**, không phải toàn bộ không gian gán phòng/ca. Đây là giới hạn quan trọng của prototype.

## Thực nghiệm

Web có nút **Chạy thực nghiệm** (không gắn số lượt cố định) và cho phép khởi chạy tối đa 500 lượt, luân phiên A/B/C, cùng instance theo seed cho hai phương pháp, log mean/std/tỷ lệ khả thi/runtime. Vì thuật toán GA stochastic, cần nhiều seed. Không khẳng định GA luôn tốt hơn Greedy, hoặc hội tụ tối ưu toàn cục. Runtime của GA lớn và không thể coi số thế hệ là số lượt thí nghiệm độc lập.

## Chú ý

- Mỗi lớp được biểu diễn thành một buổi; 35 slot cố định, chia thành 7 ngày x 5 ca trong giao diện web.
- Chương trình dùng dữ liệu giả lập, chưa có quản lý tài khoản/đăng nhập, và chưa kết nối dữ liệu thật của trường.
- Kết quả thực nghiệm từ dự án này cần chạy lại, không trộn với dữ liệu của ứng dụng HTML tĩnh cũ.

## Giao diện và chế độ theo dõi GA (bản cập nhật)
- Ở mục 1, nhấn **Tạo bộ dữ liệu mới** để cập nhật tóm tắt số lớp/phòng/ca và xem nhanh 4 lớp đầu tiên ngay bên dưới nút. Cùng seed và tham số sinh cùng dữ liệu; đổi seed để có dữ liệu khác.
- Ở mục 2, nhấn duy nhất **Chạy Greedy & GA** để khởi chạy và hiện tiến độ ở mục “Quá trình tính toán GA trực tiếp”. Không còn nút khởi tạo GA thứ hai.
- Khi GA đang chạy có thể dùng điều khiển phụ **Tạm dừng**, **Chạy 1 thế hệ**, **Tiếp tục** và **Dừng**. Vì dataset nhỏ có thể chạy hết rất nhanh nên điều khiển phụ đôi khi không kịp dùng. Vẫn có thể xem nhật ký từng thế hệ.
- Bảng log hiển thị best/mean objective, số nghiệm hợp lệ, số phương án duy nhất đã đánh giá (cache), thời gian trôi qua; biểu đồ lấy từ Python.
- Muốn thay bản cũ: đóng CMD/server cũ, giải nén ZIP mới vào thư mục riêng, mở `MO_SCHEDULELAB.bat` và tải lại trang bằng Ctrl+F5.

## Xem quá trình GA từng thế hệ

Bấm **Chạy Greedy & GA** một lần. Trình duyệt sẽ yêu cầu Python tính lần lượt từng thế hệ và cập nhật bảng, thời khóa biểu hiện tại, biểu đồ hội tụ. Mỗi thế hệ được hiển thị trong khoảng 320 ms để dễ quan sát (đây là **khoảng nghỉ trình bày**, không phải thời gian tính toán).

- **Tạm dừng**: ngừng yêu cầu thế hệ mới; thế hệ đang tính sẽ kết thúc trước.
- **Chạy 1 thế hệ**: dùng khi tạm dừng.
- **Tiếp tục**: trở lại chế độ tự chạy từng thế hệ.
- **Dừng**: ngừng quá trình; không mặc định xem đó là kết quả hoàn tất.

Các chỉ số runtime trong log lấy từ Python; chạy thử nghiệm hàng loạt vẫn chạy ở tốc độ tối đa, không có khoảng nghỉ trình bày.

## Bản cập nhật dữ liệu đa dạng
- Tạo dữ liệu: đổi số lớp, phòng hoặc seed (35 ca/tuần cố định trên web) để sinh bài toán khác; thêm **Trọng số ưu tiên giờ** từ 0 đến 20 để điều chỉnh chi phí khung giờ riêng mỗi lớp. Nhớ bấm **Tạo bộ dữ liệu mới** sau khi chỉnh.
- Trọng số 0 quay về bài toán xếp phòng gần như chỉ dựa vào chỗ ngồi dư và phạt ca cuối nên hai thuật toán có thể trùng nghiệm. Tăng trọng số khiến sự phân bổ thứ tự lớp có tác động rõ hơn.
- GA không được bảo đảm điểm số thay đổi ở mỗi thế hệ hoặc luôn tốt hơn Greedy; chỉ báo số thực.
- Sau khi đổi objective, kết quả báo cáo chương 4–5 trước đây phải chạy lại.

## Theo dõi Greedy trong thực nghiệm

Mỗi lượt thực nghiệm được trình bày hai giai đoạn: Greedy gán lớp theo thứ tự rồi GA tìm kiếm qua các thế hệ. Bảng Greedy hiển thị mã lớp, phòng, ca, chi phí tăng thêm, objective tích lũy và runtime thuần; biểu đồ tích lũy **tăng** là bình thường vì mỗi lớp làm phát sinh chi phí. Khoảng nghỉ trình diễn không được tính vào Greedy ms hoặc GA ms. Dữ liệu và bảng lấy trực tiếp từ Python, không nội suy giá trị. Chế độ Nhanh có thể không kịp hiển thị tất cả bước trong lúc chạy nhưng nhật ký của lượt hiện tại vẫn có đủ các bước.


## Quan sát quá trình (bản cập nhật)
- Nút **Chạy thực nghiệm** luôn chạy thực nghiệm ở Python, không tự mở bảng tiến trình.
- Nút **Quan sát quá trình** mở/đóng bảng chi tiết Greedy và GA trong lúc chương trình đang chạy; đóng không làm dừng Python.
- **Nhanh (không thêm thời gian chờ)** đặt `display_delay_ms=0`: không có sleep nhân tạo nhưng 120 lượt vẫn mất thời gian do phải tính Greedy và GA.
- Chế độ 100/200 ms thêm khoảng nghỉ để nhìn rõ từng bước và không cộng vào runtime thuật toán.


## Bố cục bản cập nhật
- Kết quả các lượt hoàn thành và bảng tổng hợp luôn nằm bên ngoài mục Quan sát quá trình.
- Thanh trạng thái chung ghi Đang thực nghiệm Greedy & GA; bên trong Quan sát mới ghi đang tính Greedy hay GA.
- Đóng Quan sát không ngừng thực nghiệm và không ẩn bảng kết quả.


## Ghi nhận cấu hình thực nghiệm
Khi chạy hàng loạt, giao diện hiển thị số lượt, seed thực nghiệm, quần thể, số thế hệ, xác suất đột biến 0.4 và trọng số ưu tiên giờ. `results/<đợt>/runs.csv` chứa cấu hình và seed GA của từng lượt. `cau_hinh_thuc_nghiem.csv` tóm tắt cấu hình chung. Nút xuất JSON của thời khóa biểu đã được gỡ; metadata.json nội bộ vẫn được lưu để truy vết kỹ thuật. Seed GA trong mục 2 dành cho chạy đơn lẻ; thực nghiệm hàng loạt dùng seed_thuc_nghiem + 100000 + (k-1).


## Cấu hình kịch bản A/B/C
Trong mục 3 có bảng cấu hình ba kịch bản, với mặc định A=12 lớp/8 phòng/20 ca, B=20/10/25, C=30/15/30. Người dùng có thể chỉnh từng trường hoặc khôi phục mặc định trước khi bấm Chạy thực nghiệm. Cấu hình được gửi tới Python và lưu trong runs.csv, cau_hinh_thuc_nghiem.csv và metadata.json. Nút xuất JSON trên giao diện đã được loại bỏ; file JSON nội bộ giữ để lưu dấu vết thí nghiệm.


### Tùy chỉnh xác suất đột biến
Mục 2 có thêm ô **Xác suất đột biến (0–1)**, mặc định 0.4. Quần thể, số thế hệ, xác suất đột biến dùng cho cả chạy đơn và chạy hàng loạt. Seed GA ở mục 2 chỉ dùng cho chạy đơn; lượt k trong hàng loạt dùng seed thực nghiệm + 100000 + k - 1. CSV ghi mutation_probability cho từng lượt và file cau_hinh_thuc_nghiem.csv ghi giá trị chung.
