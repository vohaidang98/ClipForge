# ClipForge Studio 1.1

Mở ClipForge.exe trên Windows 64-bit. Giữ thư mục bin bên cạnh EXE. Không cần cài Python. Bản mã nguồn clipforge.py cũng được cung cấp để chỉnh sửa.

## Sử dụng

1. Chọn tab Cắt video hoặc Chuyển đổi, bấm Thêm video (có thể chọn nhiều file).
2. Chọn thư mục lưu. Để trống sẽ tạo ClipForge_Output cạnh từng video gốc.
3. Cắt: chọn bỏ đầu/đuôi hoặc lấy đoạn theo thời lượng. Khi lấy từ cuối, offset là khoảng bỏ qua từ cuối video, rồi lấy đoạn có thời lượng đã nhập.
4. Chuyển đổi: chọn codec, kích thước, FPS, bitrate và âm thanh. Default kéo ảnh vừa kích thước; Letterbox giữ tỷ lệ và thêm viền; Crop giữ tỷ lệ và cắt phần thừa.
5. Bấm Bắt đầu xử lý. Nút Dừng kết thúc tiến trình hiện tại, xóa kết quả chưa hoàn thành. Chi tiết lỗi xuất hiện ở khung nhật ký.

Không sửa video gốc. Kết quả trùng tên được thêm số thứ tự. Cắt dùng stream copy nên điểm cắt có thể lệch theo keyframe. Nếu container gốc không hỗ trợ các luồng nguồn, thao tác cắt có thể báo lỗi.

NVENC yêu cầu GPU NVIDIA và driver hỗ trợ. Nếu báo lỗi, bỏ chọn GPU để chạy CPU. Chưa kiểm thử NVENC trên phần cứng thực tế. Preset JSON lưu/nạp các trường tương ứng của MConvert; chưa bảo đảm mọi biến thể preset gốc.

## Phân tích MCutExtend_v1.0.6

File RAR chứa MCutEx.exe (~26,5 MB), Python 3.10, Tcl/Tk, thư viện tkinterdnd2, Crypto và các DLL. Dấu hiệu trong binary xác định ứng dụng được biên dịch bằng Nuitka, có ttkbootstrap, theme mặc định cyborg và cửa sổ ban đầu 600×660.

Các chức năng được xác định qua chuỗi và tên hàm trong binary:

- MCut: danh sách video, kéo thả, xóa mục, chọn thư mục; cắt đầu/đuôi; offset và thời lượng từ đầu/cuối; dừng xử lý. Dùng FFprobe đọc thời lượng và FFmpeg với codec copy.
- MConvert: H.264/H.265/MPEG-4; kích thước; Default/Letterbox/Crop; bitrate; FPS; AAC/AC3/MP3; sample rate; số kênh; NVENC; preset JSON; dừng chuyển đổi.
- Menu đổi theme; cơ chế kiểm tra license, lưu license và kiểm tra định kỳ qua mạng.
- Không thấy ffmpeg.exe hoặc ffprobe.exe trong archive được cung cấp. Chỉ riêng archive chưa cho biết môi trường chạy gốc cung cấp hai công cụ này như thế nào.

Đây là phân tích tĩnh, không chạy EXE gốc và không xác thực máy chủ license. Binary biên dịch không cung cấp mã nguồn Python ban đầu; không thể khẳng định khôi phục chính xác mọi hành vi chỉ từ các chuỗi quan sát được. Không đánh giá mức độ an toàn toàn bộ EXE bằng phương pháp này.

## Bản mới và giới hạn tương đương

ClipForge được viết độc lập, không chỉnh sửa binary gốc, không dùng lại tài nguyên thương hiệu hoặc cơ chế license gốc. Giao diện studio tiếng Việt 1120×900, hai tab, sáng/tối, nút thêm file rõ ràng, nhật ký, tiến độ theo số file, bảo vệ file gốc và tránh ghi đè.

Chức năng xử lý chính đã tái tạo theo các dấu hiệu quan sát được. Khác biệt: chọn file bằng hộp thoại thay kéo thả; hai chế độ sáng/tối thay bộ theme ttkbootstrap; preset lưu/nạp qua hộp thoại thay danh sách preset nội bộ; chưa có preview video. Không tuyên bố bản sao giống hệt 100%.

## Kiểm tra đã thực hiện

- Khởi tạo giao diện, chuyển tab và đổi sáng/tối.
- Kiểm tra tính khoảng cắt và từ chối khoảng không hợp lệ.
- Tạo video thử có âm thanh và thực hiện cắt thực tế.
- Chuyển đổi thực tế cả Default, Letterbox, Crop; dùng FFprobe xác nhận kích thước đầu ra.
- Chạy lặp và xác nhận tạo tên mới khi kết quả đã tồn tại.

Chưa kiểm thử mọi codec, mọi container, video lớn, GPU và mọi cấu hình Windows. Bộ kiểm tra sử dụng video tổng hợp, không có video dự án của người dùng.

## Biên dịch lại

Python 3.12 có Tkinter; cài PyInstaller rồi chạy:

    python -m PyInstaller --onefile --windowed --name ClipForge clipforge.py

Đặt bin cạnh EXE kết quả. Mã nguồn không cần thư viện Python bên ngoài khi chạy trực tiếp.

FFmpeg/FFprobe và DLL trong bin là bộ GPL shared có sẵn trên máy xây dựng. Giữ thông báo bản quyền/giấy phép đi kèm khi phân phối. Chạy bin/ffmpeg.exe -L để xem giấy phép, -version để xem phiên bản/cấu hình. Thông tin và mã nguồn FFmpeg: https://ffmpeg.org/ và https://github.com/BtbN/FFmpeg-Builds .

## Bộ cài 1.1

Chạy ClipForge-Setup-1.1.exe, chọn thư mục và làm theo hướng dẫn. Bộ cài có giao diện tiếng Anh; ứng dụng có giao diện tiếng Việt. Mặc định cài cho tài khoản hiện tại, không cần quyền quản trị. Có shortcut Desktop, Start Menu và mục gỡ trong Settings > Apps. Có thể đổi sang thư mục D:\Code nếu muốn. Bộ cài chưa ký số.

Bản 1.1 bổ sung giao diện tối xanh ngọc, chế độ sáng, bộ đếm file, hướng dẫn khi danh sách trống và icon Play riêng. Icon được nhúng vào EXE và thanh tiêu đề. Mã installer.iss dùng Inno Setup, tài liệu: https://jrsoftware.org/isinfo.php .


## Cập nhật 1.2

Hai tab đều có nút Thêm file video (chọn một hoặc nhiều file) và Thêm từ thư mục (lấy video trực tiếp trong thư mục đã chọn). Có thể thêm nhiều lần; giữ các video đã chọn trước đó và tự bỏ qua file trùng. Thư mục lưu là tùy chọn riêng cho kết quả đầu ra.

