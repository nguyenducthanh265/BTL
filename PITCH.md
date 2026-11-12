# Kịch bản demo và vấn đáp

## Demo 3-5 phút

1. **30 giây:** bài toán là so sánh tìm kiếm chính xác và tìm kiếm mô phỏng khi ngân sách hữu hạn. Chỉ rõ bàn 3x3 kiểm chứng được toàn bộ; bàn 9x9/cờ tướng dùng đánh giá gần đúng.
2. **60 giây:** mở `python -m gameai.demo`; chọn 3x3 và Alpha-Beta depth 9. Người dùng đi trước, thử một đường chéo; chỉ số nodes cho thấy công việc tìm kiếm. Reset, đổi bên để minh họa AI đi trước.
3. **45 giây:** chọn MCTS, thay iteration nhỏ/lớn và quan sát bảng N, W, W/N. Nêu rõ UCT chọn nhánh để tìm kiếm, còn nước đánh cuối dùng nhánh nhiều lượt thăm nhất.
4. **45 giây:** chọn five-in-a-row 9x9, dùng ngân sách nhỏ để demo phản hồi. Đặt quân, hoàn tác, giải thích cắt ứng viên theo bán kính nếu bật.
5. **45 giây:** chọn cờ tướng, ưu tiên Alpha-Beta depth 1-2 hoặc MCTS 100 iteration cutoff. Chọn quân rồi ô đích được đánh dấu; giải thích cây legal và rollout pseudo-legal khác nhau.
6. **30 giây:** mở `results/SUMMARY.md` và PDF, chỉ đúng phần hoàn tất/partial. Không nói MCTS luôn không thua hay biến thể mới tốt hơn khi chưa đủ bằng chứng.

## Dự phòng offline

Demo và dữ liệu chạy cục bộ, không cần API. Nếu giao diện lỗi, dùng `python -m pytest tests/test_demo.py -p no:cacheprovider -q` để kiểm backend, sau đó trình bày PDF và bảng root-stat đã lưu. Chưa có backend fallback giả lập; không trình bày bảng lưu sẵn như ván AI vừa tính.

## 10 câu hỏi cần chuẩn bị

1. **Vì sao có căn và ln?** Sai số trung bình bị chặn có thang 1/sqrt(n); chọn tail theo thời gian cho ln(t). Trình bày phép biến đổi trong `docs/UCT_THEORY.md`, nói rõ điều kiện IID và giới hạn khi chuyển vào cây.
2. **c=sqrt(2) luôn tốt nhất?** Không. Đây là hệ số trong động cơ UCB1; thực nghiệm tìm kiếm đối kháng còn phụ thuộc reward, budget, rollout và đối thủ.
3. **W có phải số ván thắng?** Trong node là tổng reward, bao gồm 0.5 khi hòa; cột W của bảng W/D/L là số ván thắng. Đừng trộn hai nghĩa.
4. **Vì sao chọn N lớn nhất thay W/N?** Một nhánh ít mẫu có thể may mắn; N lớn thể hiện được phân bổ nhiều bằng chứng hơn. Cả hai vẫn cần thí nghiệm ở cùng budget.
5. **MCTS có không bao giờ thua 3x3?** Không có bảo đảm cho mọi budget/seed; có regression forced-loss và dữ liệu lỗi. Full-depth exact solver là baseline riêng.
6. **Alpha-Beta làm đổi kết quả?** Trên cùng cây/độ sâu thì không; ordering chỉ đổi số node. Candidate radius làm đổi cây nên phải ghi điều kiện so sánh.
7. **Kiểm chứng không bị hai thuật toán cùng sai?** Test tablebase độc lập dùng tuple và tám đường thắng; so toàn bộ 5.478 board hợp lệ và mọi best move.
8. **Heuristic rollout liên hệ value network?** Cả hai ước lượng lá; hiện dùng luật và hàm đánh giá viết tay, không huấn luyện mạng.
9. **Cờ tướng đúng luật giải đấu chưa?** Chưa đầy đủ luật xử lặp chiếu/đuổi; có giới hạn hòa giản lược. Rollout còn xấp xỉ pseudo-legal, dù nước chọn trong cây là legal.
10. **Còn thiếu gì trước nộp?** Thí nghiệm lớn theo PLAN, thông tin tác giả, kiểm format IEEE với công cụ nộp và GitHub do chủ dự án chọn. Bài toán thực tế thứ hai là bonus chưa triển khai.

Lấy mọi số liệu trình bày từ snapshot và audit hiện tại; không dùng số tiến trình đang chạy làm số cuối cùng.
