# Audit demo local — 2026-11-06

## Phạm vi và cách chạy

Đã đọc `PLAN.md`, role `fullstack_dev` của hackathon-kit, toàn bộ mã nguồn
`gameai/demo/` và `tests/test_demo.py`. Không có `ARCHITECTURE.md` tại thời điểm audit.
Phạm vi thay đổi: frontend demo và kiểm thử HTTP; không sửa engine/search/experiments.
Demo phục vụ vấn đáp trực tiếp trên máy local, không yêu cầu public deploy.

Từ thư mục `btl-ai-mcts`:

```powershell
python -m gameai.demo --port 8765
python -m pytest tests/test_demo.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```

Mở `http://127.0.0.1:8765/`. Server chỉ bind loopback; nếu cổng bận, CLI in cổng
trống được chọn thay thế. Frontend HTML/CSS/JS nằm trong một file, không tải CDN.
Các request `POST /api/play` gửi lại lịch sử nước đi; server replay trên bàn mới,
kiểm tính hợp lệ và có thể thêm một nước AI. Reset gửi lịch sử rỗng; undo gửi lại
tiền tố lịch sử. Không có session bàn cờ lưu trên server.

## Lỗi đã tái hiện và sửa

1. Bàn 3×3 tràn ngang khi cửa sổ hẹp. Trước sửa: browser báo viewport 500px,
   bàn rộng 523.5px, mép trái -19.25px. Nguyên nhân kích thước ô chỉ giới hạn theo
   chiều cao màn hình. Đã giới hạn thêm theo chiều rộng thực của `#board` bằng
   CSS container units. Sau sửa: bàn rộng 460.97px trong khung 461px, không tràn.
2. Reset trong lúc chờ phản hồi vẫn hiển thị bàn cũ và “Lượt của bạn”. Đã tái hiện
   sau ván có lịch sử `[4, 0]` bằng cách trì hoãn việc nhận phản hồi HTTP thật 300ms.
   Đã xóa vị trí cũ khi bắt đầu ván mới và thêm trạng thái loading cho request
   cập nhật bàn. Sau sửa, trong lúc reset: `pos=null`, bảng hiện “Đang tải bàn cờ…”,
   status hiện “Đang cập nhật bàn cờ…”, rồi trở về bàn trống.

## Kiểm thử thực đã chạy

- Baseline: **145 tests PASS**, 6.91s. Có cảnh báo quyền ghi `.pytest_cache`.
  Các lần sau dùng `-p no:cacheprovider`, không còn cảnh báo này.
- Sau thay đổi và thêm 4 E2E HTTP tests: **149 tests PASS**, 6.46s.
  Fixture mở `ThreadingHTTPServer` trên cổng loopback thực và dùng `http.client`,
  không mock HTTP hoặc thuật toán AI.
- Full suite tại thời điểm hoàn tất audit: **297 tests PASS**, 161.74s
  (`python -m pytest -q -p no:cacheprovider`, exit 0). Root sẽ chạy lại integrated
  suite sau khi các phần việc khác kết thúc.
- Bổ sung kiểm tra: toàn bộ ván 3×3 giữa hai Alpha-Beta tối ưu kết thúc hòa;
  9×9 thắng đủ 5 quân, không thêm AI sau terminal, undo rồi reset;
  Xiangqi bắt quân, undo phục hồi quân bị bắt rồi reset; request sai không làm
  nhiễm trạng thái lần replay sau hoặc trò chơi khác.
- Bộ HTTP hiện có kiểm tra cả 4 bàn (3×3, 9×9, 15×15, Xiangqi), hai thuật toán,
  mọi formula và rollout, clamp tham số, illegal moves, JSON hỏng/quá lớn,
  terminal, chiếu tướng và GET phản hồi trong lúc AI đang tìm kiếm.

Đã mở Chrome qua browser tools và kiểm tra UI thật tại server cổng 8765:

| Luồng | Kết quả quan sát |
| --- | --- |
| 3×3: người đi, AI trả lời, Hoàn tác | PASS, 2 nửa nước rồi về bàn rỗng |
| Người chọn đi sau | PASS, AI tự mở ván; undo không xóa nước mở ván duy nhất |
| Sáu công thức MCTS | PASS, UI chọn và API analysis trả đúng công thức |
| Ba rollout | PASS, UI chọn và API analysis trả đúng rollout |
| 9×9 | PASS, người đi giữa bàn, AI trả lời, undo về bàn rỗng |
| Xiangqi | PASS, chọn pháo đỏ ô 70, đi ô 67, AI trả lời, undo phục hồi |
| AI request bị từ chối HTTP 400 | PASS, hiện “Công thức không hợp lệ”; giữ nước người vừa đi; undo phục hồi |
| Loading AI | PASS, hiện spinner/thời gian và bật Hoàn tác khi có nước để lùi |
| Undo/reset khi AI đang nghĩ | PASS, phản hồi cũ không ghi đè bàn mới |
| Bố cục desktop 1280×800 | PASS, cả 4 bàn nằm trong chiều rộng vùng chơi |
| Bố cục cửa sổ hẹp, viewport thực 500px | PASS, cả 4 bàn nằm trong vùng chơi |

Các ca race trì hoãn việc nhận phản hồi AI HTTP thật 500ms trong browser, rồi
undo/reset trước khi nhận; không thay thuật toán hoặc giả response. Kiểm tra lỗi
400 dùng giá trị formula ngoài whitelist để server thật từ chối. Console chỉ có
resource error 400 chủ động tạo ở ca này, không thấy exception JavaScript khác.

## Giới hạn

- Đây là kiểm chứng demo local và HTTP; không có bằng chứng public deployment.
- Browser desktop giới hạn chiều rộng tối thiểu thực tế 500px dù yêu cầu resize
  390px. Không tuyên bố đã kiểm chứng thiết bị mobile 390px hay thao tác cảm ứng.
- Kiểm browser được thực hiện trong phiên audit, chưa có runner browser tự động
  trong dependency của dự án. HTTP E2E được lưu trong `tests/test_demo.py`.
- Reset/undo bỏ qua kết quả request cũ bằng token, không dừng phép tìm kiếm Python
  đã chạy. Alpha-Beta độ sâu 4–5 trên bàn lớn có thể chậm; UI đã có cảnh báo.
- Không kiểm exhaustive toàn bộ ván Xiangqi qua UI. Chiếu tướng và capture/undo
  được kiểm HTTP; tính đúng luật engine và chất lượng AI thuộc audit riêng.
- Bàn Xiangqi dùng click/pointer trên SVG; chưa kiểm đầy đủ accessibility bàn
  bằng bàn phím hoặc screen reader.
- CSS container units yêu cầu browser hiện đại; đã kiểm Chrome của phiên audit.

Server cổng 8765 và tab demo được giữ mở để xem trực tiếp.
