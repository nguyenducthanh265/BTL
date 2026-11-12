# Audit engine và thuật toán tìm kiếm

Ngày kiểm tra: 2026-11-06. Phạm vi: toàn bộ `gameai/games`,
`gameai/search`, `gameai/agents.py`, `gameai/match.py` và bốn bộ test engine.
Vai trò áp dụng: `hackathon-kit/.codex/agents/ml_engineer.toml`.

## Lỗi đã sửa

1. `search()` không kiểm tra trạng thái kết thúc tại root: trả `+/-inf` và danh
   sách rỗng thay vì giá trị thắng/thua/hòa hữu hạn. Root terminal hiện trả điểm
   chính xác, không có nước đi và `nodes=1`.
2. `depth=0` bị giảm thành `-1`, làm mất điều kiện dừng độ sâu. Hiện đánh giá
   trực tiếp root; độ sâu âm hoặc không nguyên bị từ chối.
3. `TicTacToe.key()` thiếu cấu hình `size/k`. Dùng chung memo giữa các luật
   khác nhau có thể trả sai game value. Key hiện chứa geometry; regression
   dùng chung memo cho 3x3/k=3 (hòa) và 3x3/k=1 (X thắng).
4. `Xiangqi.key()` chỉ chứa board/to-play, dù luật hòa phụ thuộc số ply,
   số nước không bắt quân, giới hạn và lịch sử lặp. Key hiện chứa đủ context
   trên để không trộn memo giữa một board đang chơi và cùng board đã hòa.
5. Bộ đếm match dùng object agent làm key. Dùng cùng một instance ở hai ghế
   khiến thống kê của cả hai ghế bị cộng chung. Hiện thống kê theo bên chơi;
   regression kiểm game 7 ply có `first_nodes=4`, `second_nodes=3`.
6. Geometry không hợp lệ không bị chặn; heuristic chỉ hỗ trợ k=3/k=5 dù class
   mô tả generalized game; prior bàn 1x1 chia cho zero. Đã kiểm geometry,
   thêm trọng số heuristic cho các k khác và prior hữu hạn trên bàn 1x1.
7. Review sau audit phát hiện thang heuristic generalized k có thể vượt terminal:
   trên 9x9/k=9 sau `[0,9,1,11,2,13,3,15,4,17,5,19,6,21,7,23]`, cả Minimax và
   AB depth=1 chọn 16 (heuristic 2.097.097) thay vì 8 thắng ngay (999.999).
   Regression được chạy RED trước sửa: **2 failed** với `[16] != [8]`.
   Hiện điểm nonterminal được chặn trong
   `[-(WIN_SCORE-size²-1), +(WIN_SCORE-size²-1)]`: nhỏ nghiêm ngặt hơn trị tuyệt
   đối của terminal muộn nhất có thể trong size² ply. Geometry có diện tích
   từ `WIN_SCORE` trở lên bị từ chối trước cấp phát, để miền terminal thắng
   luôn dương. Thang k=3/k=5 thông thường giữ nguyên (test giá trị 4 và 20
   cho một quân giữa bàn 3x3 và 9x9). Có regression cả hai dấu heuristic.

## Bằng chứng 3x3 không thua

Test `test_every_3x3_search_choice_preserves_the_exact_value` xây tablebase
độc lập bằng tuple và tám đường thắng, không gọi `winner()` của engine để
tính giá trị tham chiếu. Test duyệt đúng **5.478 trạng thái hợp lệ** tính từ
bàn trống và dừng mở rộng khi game kết thúc. Tại mọi trạng thái chưa kết thúc:

- Minimax full-depth và Alpha-Beta full-depth phải cùng dấu với giá trị exact.
- Mọi nước được trả về trong `best_moves`, kể cả khi có nhiều lựa chọn bằng
  điểm, đều phải giữ nguyên giá trị exact sau khi chơi.
- `solve()` cũng được đối chiếu với tablebase.

Bàn trống có giá trị 0. Bởi các nước của chính sách giữ nguyên giá trị và mọi
nước hợp lệ của đối thủ đã được xét, Minimax/AB full-depth dùng **toàn bộ legal
moves** không thể thua từ bàn trống ở cả hai màu. Đây không phải tuyên bố không
thua từ các trạng thái đã có forced loss. `PerfectAgent` chọn ngẫu nhiên từ
`optimal_moves`, sử dụng cùng exact solver; tie breaking không đổi game value.

Test cây đầy đủ độc lập với policy xác nhận 549.946 nodes, 131.184 ván X thắng,
77.904 ván O thắng và 46.080 ván hòa.

## MCTS và giới hạn suy luận

UCT chuẩn dùng `W/N + c*sqrt(ln(N_parent)/N)`. Các test kiểm ví dụ số của đề,
visit accounting, reward theo người vừa đi, reproducibility, các biến thể và
ba rollout policies. Không thêm minimax oracle vào MCTS để tạo bảo đảm giả.

Regression `test_finite_mcts_budget_can_choose_a_forced_loss` là phản ví dụ
tái lập: vị trí sau `[1, 0, 6, 4]` còn hòa với nước 8, nhưng MCTS một iteration,
seed 1 chọn nước khác và exact solver xác nhận X bị forced loss. Kết quả tốt
với một budget/seed set chỉ là bằng chứng thực nghiệm; không suy ra bảo đảm
"MCTS hữu hạn không bao giờ thua". Cutoff và heuristic rollout là estimator
có bias; heuristic tic-tac-toe chỉ kiểm threat quanh hai quân gần nhất.

## Xiangqi và five-in-a-row

Legal tree Xiangqi kiểm an toàn tướng, cấm lộ mặt tướng, cản chân mã/mắt tượng,
pháo, cung, sông, chiếu, chiếu bí và bí nước (bí nước là thua). Perft khởi đầu
có các mốc 44, 1.920, 79.666 và 3.290.240 ở độ sâu 1–4. Các mốc này là regression
đã có sẵn trong repo; audit không xác minh nguồn xuất bản bên ngoài.

Luật giản lược phải công khai: lặp ba lần là hòa thường, không phân xử đầy đủ
chiếu đuổi/vây bắt lặp; mặc định 120 ply không bắt quân hoặc 200 tổng ply là hòa.
**Riêng simulation Xiangqi dùng pseudo-legal moves**, có thể để tướng bị bắt,
và không cập nhật các draw counters/repetition như legal tree; random/heuristic
rollout tối đa 200 bước trả hòa ở cutoff, rollout cutoff 16 bước trả heuristic
logistic. Giá trị MCTS vì thế là giá trị ước lượng của simulator xấp xỉ, không
phải rollout hoàn toàn theo luật legal-tree Xiangqi.

Five-in-a-row dùng luật freestyle (chuỗi dài hơn 5 cũng thắng). AB và Minimax
được đối chiếu trên cùng cây ứng viên/độ sâu; candidate radius bỏ bớt legal
moves nên không phải giải chính xác trò chơi đầy đủ. Depth-limited search
dựa vào heuristic cửa sổ, không có bảo đảm không thua trên bàn lớn. API hiện
dùng bàn vuông `size × size`, không có tham số hình chữ nhật m khác n.

## Lệnh và kết quả kiểm tra

- `python -m pytest tests/test_tictactoe.py tests/test_minimax.py tests/test_mcts.py tests/test_xiangqi.py -m 'not slow' -q`: 112 passed, 1 deselected, 96,26 giây tại lần chạy đầu; có warning quyền ghi pytest cache.
- Regression bổ sung sau lần đầu: 10 passed, 50 deselected, 12,02 giây (gồm vét cạn, root/depth, shared memo và phản ví dụ MCTS).
- `python -m pytest tests/test_tictactoe.py tests/test_minimax.py tests/test_mcts.py tests/test_xiangqi.py -p no:cacheprovider -q`: **115 passed, 133,81 giây**; gồm perft4 và toàn bộ regression mới, không warning.
- Sau sửa bound generalized heuristic: `python -m pytest tests/test_tictactoe.py tests/test_minimax.py -k 'generalized or evaluation_scale or invalid_geometry' -p no:cacheprovider -q`: **11 passed, 39 deselected, 0,14 giây**. Mốc 115 tests ở trên là trước sửa bổ sung này; integrated suite do root chạy lại.

Không dùng kết quả engine tests để suy ra sức mạnh thi đấu Xiangqi hay five-in-a-row,
không suy ra tính tối ưu của rollout/UCT variants và không coi fixed-seed tactical
tests là đánh giá thống kê tổng quát.
