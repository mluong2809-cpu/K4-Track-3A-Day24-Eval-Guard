# Phase B — độ tin cậy của LLM Judge

Nhóm: NguyenMinhLuong (cá nhân), Nguyễn Minh Lương — 2A202602618. Kết quả thật: `artifacts/judge_results.json`; judge model `gemini-3.1-flash-lite`. Mỗi pair lấy A từ `artifacts/answers_50q.json:answer`, B từ `fixtures/human_labels_10q.json:model_answer`; question/reference từ `fixtures/test_set_50q.json`. Pairwise và binary là hai phép chấm khác nhau; winner A/B không được dùng làm nhãn 0/1.

## Hai lượt pairwise và đổi thứ tự

Lượt 2 gửi B trước, A sau; các winner và scores dưới đây đã quy về danh tính A/B gốc. JSON giữ nguyên cả reasoning hai lượt và scores từng candidate.

| ID | A/B ký tự | Lượt 1 | Lượt 2 sau quy đổi | Final | Scores lượt 1 A/B | Scores lượt 2 A/B |
|---:|---:|---|---|---|---|---|
| 1 | 284/57 | A | A | A | 1.0/0.8 | 0.9/0.7 |
| 5 | 276/33 | tie | tie | tie | 0.1/0.1 | 0.1/0.1 |
| 12 | 280/50 | A | A | A | 0.9/0.4 | 0.8/0.6 |
| 21 | 288/82 | B | B | B | 0.5/1.0 | 0.4/1.0 |
| 41 | 286/37 | tie | tie | tie | 0.1/0.2 | 0.1/0.2 |

Không có case bất đồng sau swap: `position_bias_count=0/5`, `position_bias_rate=0`. Lượt 2 của ID 1 và 12 gọi winner “B” theo **vị trí** nhưng đó là A gốc; ánh xạ trong JSON và bảng đã xử lý đúng. Với ID 5, hai answers đều thiếu/sai người phê duyệt 55 triệu; ID 41, A chỉ nói quy trình còn B dùng 12 ngày của v2023. Judge chọn tie vì cả hai không đáp ứng reference, không vì độ dài. ID 21 B thắng dù ngắn hơn vì nêu cả số ngày phép lẫn khung lương; A bỏ khung lương.

Trong ba case decisive, A thắng và dài hơn ở ID 1 và 12 (`a_wins_a_longer=2`); B thắng và dài hơn ở 0 case (`b_wins_b_longer=0`), nên `verbosity_bias=2/3=0.667`. Nội dung reasoning nêu các điều kiện thiết yếu có trong A ở ID 1/12 và phần thông tin thiếu ở A của ID 21. Tập chỉ có năm cặp, nên tỷ lệ này **không** chứng minh judge thiên vị độ dài hay không có position bias trong tình huống khác.

## Binary calibration trên `model_answer` gốc

Mười lượt binary dùng chính `question`, `model_answer` trong fixture và `ground_truth` cùng ID; `human_label`/`human_note` không vào prompt. Nhãn judge/human theo thứ tự ID:

| ID | 1 | 5 | 12 | 21 | 23 | 29 | 33 | 41 | 46 | 50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Judge | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| Human | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |

Quan sát `p_o=10/10=1`. Mỗi phía có 6 nhãn 1 và 4 nhãn 0, nên `p_e=0.6²+0.4²=0.52`, `κ=(1−0.52)/(1−0.52)=1.0`. Không có case bất đồng ở bộ 10 câu này. Các nhãn 0 có lý do cụ thể: ID 5 sai thẩm quyền; ID 29 thiếu Kế toán trưởng/điều kiện phí; ID 41 dùng policy cũ; ID 50 cho phép VPN cá nhân trái reference.

κ=1.0 đạt ngưỡng bonus trên đúng nguồn được cấp, nhưng chỉ đo đồng thuận ở **10 model_answers cố định**. Nó không xác nhận chất lượng 50 answers của pipeline, không chứng minh judge luôn đúng, và không thay thế việc kiểm tra trên nhiều câu/phiên bản/độ dài hơn. `model_answer` không được thay bằng answer mới khi tính κ.
