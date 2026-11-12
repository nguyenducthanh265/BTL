# Final local demo QA — 2026-11-06

Demo local đã được kiểm tra ở viewport CSS thực **390×844**, **360×800** và desktop
1280×800 bằng Chrome. Hai viewport hẹp dùng mobile/touch emulation, không phải
thiết bị cảm ứng thật. Bằng chứng có thể chạy lại nằm trong
[mobile-qa/README.md](mobile-qa/README.md),
[check.js](mobile-qa/check.js),
[390×844 JSON](mobile-qa/390x844.json) và [360×800 JSON](mobile-qa/360x800.json).

## Thay đổi

Chỉ sửa `gameai/demo/index.html`; không sửa engine hay API. Khi con trỏ coarse,
select/input và nút điều khiển cao tối thiểu 44px, chữ trong trường nhập là 16px.
Ô bàn vuông có cạnh tối thiểu 44px; vùng chọn trên bàn cờ tướng khoảng 44,09px.
Bàn lớn cuộn ngang trong vùng bàn và có hướng dẫn vuốt ngang khi cần. Hình quân,
tọa độ, bảng phân tích và bố cục desktop được giữ lại.

Trước sửa, input/select cao khoảng 31px, nút điều khiển khoảng 38px; ô 15×15 chỉ
rộng 23,19px ở 390px và 21,19px ở 360px. Sau sửa không còn thu nhỏ các vùng chọn
này để vừa chiều rộng điện thoại.

## Kết quả

| Ca kiểm tra | 390×844 | 360×800 |
| --- | --- | --- |
| Cả bốn bàn: nước người, AI thật trả lời, undo và reset | PASS | PASS |
| Chiều rộng document bằng viewport; analysis không tràn ngang | PASS | PASS |
| Mọi control đang hiện cao ≥44px | PASS | PASS |
| 3×3: cạnh ô | 116px | 106px |
| 9×9 và 15×15: cạnh ô | 44px | 44px |
| Xiangqi: đường kính vùng chọn theo bounding box | 44,09px | 44,09px |
| Mép phải từng bàn có thể đưa vào vùng nhìn bằng `scrollLeft` | PASS | PASS |
| 6 công thức, 3 rollout, c=1,8, Alpha-Beta sâu 9, người đi sau | PASS | PASS |
| Undo/reset khi chờ AI; bỏ qua phản hồi cũ trễ 600ms | PASS | PASS |
| HTTP 400 thực: hiện lỗi công thức; undo phục hồi bàn trống | PASS | PASS |

Khoảng cuộn ngang của 9×9 / 15×15 / Xiangqi là 48 / 312 / 81px tại 390px và
78 / 342 / 111px tại 360px. Bàn 3×3 không cần cuộn ngang. Trên desktop 1280×800,
cả bốn bàn vẫn nằm trong chiều rộng vùng chơi, không hiện hướng dẫn cuộn.

Script dùng DOM click events để kiểm tra handler và gọi HTTP/AI thật; dùng
`scrollLeft` để kiểm tra hình học và khả năng đưa ô mép vào vùng nhìn. Đây không
phải bằng chứng thao tác swipe hay trusted touch. Riêng tại 390×844, công cụ
browser-click native đã bấm ô giữa 3×3, nhận AI trả lời rồi bấm Hoàn tác thành công.
Ảnh toàn trang đã mở kiểm tra trực quan:
[cờ tướng 390px](mobile-qa/390-xiangqi.png) và
[15×15 360px](mobile-qa/360-five15.png).

Kiểm thử HTTP hiện có chạy lại thành công:

```powershell
python -m pytest tests/test_demo.py -q -p no:cacheprovider
# 149 passed in 4.52s; exit 0
```

Không thêm test HTTP vì hợp đồng server không đổi. `check.js` cung cấp kiểm tra
browser cho thay đổi kích thước/vùng cuộn; không thêm phụ thuộc browser vào dự án.
Không chạy lại full suite trong phần việc này; coordinator kiểm tra tích hợp riêng.

## Giới hạn

Chưa kiểm chứng thiết bị vật lý, độ chính xác ngón tay, swipe thực, Safari hay
screen reader. Bàn 9×9, 15×15 và cờ tướng cần cuộn ngang trên viewport hẹp để giữ
vùng chọn đủ lớn; ảnh không trình bày toàn bộ chiều ngang bàn cùng lúc. Các ca
browser không duyệt toàn bộ cây ván cờ tướng. Reset/undo bỏ qua kết quả AI cũ,
không ngắt phép tìm kiếm Python đang chạy. Không có bằng chứng public deployment.

Đã đọc role `fullstack_dev`, `PLAN.md`, `ARCHITECTURE.md`, `docs/audit_demo.md`,
toàn bộ `gameai/demo/` và `tests/test_demo.py`. Server local cổng 8765 và tab Chrome
được giữ mở để coordinator kiểm tra tiếp.

## Follow-up HTTP body-close regression

The final integrated run recorded one Win10053 while reading JSON404 for POST/nope; the original failing log is preserved in mobile-qa/integrated-failure-before-body-fix.log. Exact reproduction of that Windows error was not achieved. A separate deterministic socket experiment confirmed the original handler responded and closed before consuming a normal two-byte fragmented body (zero of two bytes consumed).

The handler now discards only declared bodies from zero through64KiB before rejecting an unknown POST path. It uses read1 chunks up to8192bytes and a one-second absolute monotonic deadline, restores the original socket timeout, does not parse unknown bodies, and skips invalid/oversized lengths. Existing /api/play handling is unchanged. This fixes the demonstrated unread-body condition; it does not prove the exact historical Windows error cause.

Six new HTTP regression cases cover fragmented uploads, maximum body size, invalid/oversized/negative lengths and a client that never finishes its upload. The implementer ran155 demo tests successfully. The coordinator independently reran the instrumented socket diagnostic: no early response and two of two bytes consumed before JSON404. See mobile-qa/unknown-path-before.json, mobile-qa/unknown-path-after.json and mobile-qa/diagnose_unknown_path.py. The final integrated result is recorded separately in verification-technical.log.
