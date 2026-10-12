# Nhóm K4 Track 3A Day 24

- Tên nhóm: **NguyenMinhLuong** (làm cá nhân).
- Repo chung và nơi nộp: https://github.com/mluong2809-cpu/K4-Track-3A-Day24-Eval-Guard
- Trưởng nhóm, người tích hợp, chạy batch và nộp link: **Nguyễn Minh Lương — 2A202602618**.
- Commit dùng để chấm: HEAD của `origin/main` tại thời điểm nộp; SHA được gửi cùng link repo. Không tự ghi SHA của chính commit vào file vì nội dung đó sẽ đổi SHA.
- Deadline áp dụng: 23:59 ngày làm lab, Asia/Ho_Chi_Minh, trừ khi coach thông báo khác.

## Thành viên và phân công

| Thành viên | MSSV | Công việc thực tế | Bằng chứng |
|---|---|---|---|
| Nguyễn Minh Lương | 2A202602618 | Cá nhân thực hiện toàn bộ: tích hợp m1–m5, tạo 50 answers, Tasks 1–12, Task 13, chạy và kiểm tra A/B/C, báo cáo, Git | `src/`, `scripts/`, `artifacts/`, `doc/reports/`, lịch sử commit và checker |

Không có thành viên khác; số dòng trong mẫu không quy định số người.

## Môi trường, dữ liệu và nguồn model

- Windows, Python 3.11.9 trong `.venv`; Qdrant Docker `qdrant/qdrant:v1.9.7` đang chạy. Batch chuẩn bị đã index 102 points vào collection `lab24_production`. Hai PDF không có text layer nên loader bỏ qua; corpus Markdown vẫn được nạp.
- M1–m5 lấy từ pipeline bài trước và điều chỉnh adapter Qdrant/RAGAS. Weights `sentence-transformers/all-MiniLM-L6-v2` được cache local; BGE-M3/reranker chỉ có metadata, nên generation batch dùng MiniLM và lexical rerank fallback.
- `artifacts/answers_50q.json`: đủ 50 IDs với 20 factual, 20 multi_hop, 10 adversarial; ba contexts mỗi câu. Toàn bộ là `generation_mode=extractive_fallback`, `generation_model=null`; không trình bày đây là answer do LLM tạo. Answers không sao chép nguyên ground truth. API key ở `.env` bị Git ignore.
- NeMo Guardrails 0.10.0 hoạt động với `src/nemo_exact_index.py` (MiniLM + exact cosine) cho flow search vì Annoy 1.17.3 thiếu MSVC Build Tools trên máy. Đây là khác biệt backend so với starter, chỉ thay flow search, vẫn gọi NeMo self-check LLM thật. Presidio dùng regex recognizers cho CCCD/CMND, số điện thoại VN và email với NoOp NLP; chưa có spaCy `en_core_web_lg`, nên không nhận diện tên/ngữ cảnh tổng quát. `pip check` còn báo Annoy thiếu do gói NeMo khai dependency này.
- Phase A dùng `gemini-3.5-flash-lite` qua Gemini API và MiniLM local cho RAGAS; sau 500 request/ngày của model này, Phase B chuyển sang `gemini-3.1-flash-lite`. Artifact ghi model ID theo đúng vai trò. Việc provider alias đổi snapshot nội bộ không xác minh được từ metadata.

## Kết quả kiểm chứng

- Phase A: `artifacts/ragas_50q.json` có 50 per-question, bốn metric hữu hạn và evaluator metadata. Mean `avg_score`: factual 0.803, multi_hop 0.596, adversarial 0.793; multi_hop yếu nhất. Xem `doc/reports/failure_clusters.md` cho bottom 10 và phân tích từng câu.
- Phase B: `artifacts/judge_results.json` có 5 cặp × 2 lượt, 10 binary judgments trên supplied `model_answer`; κ=1.0, swap disagreement 0/5, longer-winner 2/3 decisive. Xem `doc/reports/bias_report.md` để đối chiếu lý do và giới hạn mẫu nhỏ.
- Phase C: batch thật đang thực hiện; kết quả, attack/clean/output và input-layer P95 sẽ được cập nhật sau khi artifact được lưu. Không suy số từ mock tests.
- Tests offline: `.venv\Scripts\python.exe -m pytest tests/ -q` đạt **91 passed, 3 deselected**. Checker đã đạt source, answers, Phase A/B; còn thiếu artifact C ở thời điểm cập nhật này.

## INDIVIDUAL — NguyenMinhLuong-2A202602618

- **Phần đã làm:** tích hợp pipeline cũ; sửa adapter m4 giữ `metadata.evaluator_models`; implement group/evaluation/bottom/matrix, pairwise/swap/kappa/bias, Presidio/NeMo input/output/latency; viết test cho exact MiniLM index; chạy A/B thật; chuẩn bị C và báo cáo.
- **Cách xác minh:** source và fixtures đối chiếu được bằng `scripts/check_lab.py`; 91 test offline đạt; artifact A/B lưu raw per-question/pairwise/binary; báo cáo liên kết ID với nguồn. Cần chạy lại checker sau C.
- **Điều học được:** faithfulness cao của answer trích nguyên văn không bảo đảm đủ ý; phải chọn nhóm yếu bằng mean; calibration phải chấm đúng answer có nhãn người; clean controls phát hiện guard chặn quá tay; latency hai tầng input không phải full-request latency.
- **Giới hạn và cách xử lý:** thiếu Annoy/MSVC nên dùng exact MiniLM index; thiếu spaCy model nên Presidio chỉ dùng recognizers xác định. Gemini 3.5 hết quota ngày sau A, dùng 3.1 cho B/C; một lỗi 503 tạm thời ở C được xử lý bằng retry có giới hạn. Không ghi kết quả C hoặc model generation chưa thực hiện như đã đo.
- **Nguồn hỗ trợ:** Codex hỗ trợ code, tích hợp, kiểm tra và diễn giải; dữ liệu nguồn, phản hồi API và artifact được giữ để thành viên đối chiếu, không điền số giả.

## Cập nhật sau khi nộp

Chưa nộp; ghi thay đổi sau thời điểm nộp thành commit riêng nếu phát sinh.
