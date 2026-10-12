# Nhóm thực hiện K4 Track 3A

Tên nhóm: NguyenMinhLuong (làm cá nhân)

Repo chung: https://github.com/mluong2809-cpu/K4-Track-3A-Day24-Eval-Guard

Trưởng nhóm/người nộp: Nguyễn Minh Lương — 2A202602618

Ngày lab/deadline áp dụng: Chưa có thông báo riêng của coach; áp dụng quy định trong `doc/SUBMISSION.md` (23:59 ngày lab, Asia/Ho_Chi_Minh).

Commit dùng để chấm: Chưa chốt; sẽ ghi SHA sau khi hoàn thành và push.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Nguyễn Minh Lương | 2A202602618 | Phụ trách toàn bộ CP0–CP4; hiện đã tích hợp pipeline và chạy batch CP0 | `src/m1_chunking.py`–`src/m5_enrichment.py`, `scripts/setup_answers.py`, `artifacts/answers_50q.json`; các phase sau và commit sẽ cập nhật theo kết quả thực tế |

Người tích hợp/chạy batch/nộp link: Nguyễn Minh Lương. Đã chạy batch CP0; các phase sau chưa chạy.

## Môi trường và chuẩn bị trước lớp

- OS: Windows. Đã tạo `.venv` bằng Python 3.11.9; Python hệ thống là 3.13.3.
- Dependencies: Python 3.11.9 `.venv` đã cài các requirements phục vụ CP0; `pip check` sạch, 61/61 tests support/report contracts pass. Đã import được Torch 2.9.1+cpu, SentenceTransformers 5.7.0 và RAGAS 0.1.22. Chưa cài Annoy và NeMo: full install bị chặn ở `annoy==1.17.3` do thiếu MSVC 14.0+. `pyarrow` đã pin 17.0.0 để tương thích NumPy 1.26.4.
- Models: cache local có weights `all-MiniLM-L6-v2` (174 MB); snapshot `BAAI/bge-m3` và `BAAI/bge-reranker-v2-m3` chỉ có metadata, chưa có weights. Batch dùng MiniLM 384 chiều và lexical rerank fallback. spaCy `en_core_web_lg` chưa cài; đã thử tải wheel 400.7 MB nhưng dừng ở khoảng 172 MB do tốc độ tải quá thấp.
- Qdrant: Docker Compose đã chạy container `qdrant/qdrant:v1.9.7`; HTTP `localhost:6333/` trả version `1.9.7`. Batch Python 3.11 đã index 102 points vào collection `lab24_production` trên container thật; endpoint collection trả trạng thái `green`.
- API: Gemini key được giữ trong `.env` local bị Git ignore. Lượt gọi Gemini từ máy này bị auto-review từ chối vì có thể gửi câu hỏi/context corpus ra ngoài. Lần setup đầu thử gọi API nhưng 50 lượt đều báo `Connection error`; artifact cuối đã được tạo lại bằng `--offline`, chặn API trong code và dùng extractive fallback local.
- Corpus: m1 báo hai PDF `BCTC.pdf` và `Nghi_dinh_so_13-2023_ve_bao_ve_du_lieu_ca_nhan_508ee.pdf` không có text layer, nên bị bỏ qua; các file markdown vẫn được nạp.
- 50 answers: `.venv\Scripts\python.exe scripts/setup_answers.py --live --offline` tạo 50 rows trên Docker Qdrant với Python 3.11.9 và client Qdrant 1.9.2; factual/multi_hop/adversarial = 20/20/10, tất cả có contexts, 50/50 `generation_mode=extractive_fallback`, `generation_model=null`. `validate_answers` pass; 0 answer trùng nguyên văn ground_truth.
- Tests: `.venv\Scripts\python.exe -m pytest tests/test_report_contracts.py tests/test_support.py -q` đạt 61/61; đây là kiểm tra offline, không chứng minh full NeMo đã cài.

## INDIVIDUAL

### NguyenMinhLuong-2A202602618

- Phần được giao và phần thực tế đã làm: Làm cá nhân toàn bộ lab. Đã đưa m1–m5 từ repo Day 18 vào `src/`, sửa adapter Qdrant 1.9/newer và cấu hình generation để hỗ trợ key Gemini trong `.env` local.
- Bằng chứng: source trong `src/`, thay đổi `config.py`, `scripts/setup_answers.py`, `.env.example`, `artifacts/answers_50q.json`.
- Cách kiểm tra: `.venv\Scripts\python.exe scripts/setup_answers.py --live --offline` trên Python 3.11.9; `validate_answers` pass; 61/61 tests support/report contracts pass; Qdrant collection có 102 points và trạng thái `green`. Chưa có kiểm chứng Phase A/B/C.
- Điều đã học: metadata model generation/evaluator phải phản ánh model thực dùng; fallback local phải ghi `generation_mode` và không được coi là LLM generation.
- Giới hạn/cách xử lý: Docker đã chạy sau khi mở Desktop. Auto-review chặn gửi context sang Gemini; dùng extractive fallback và không gọi API trong lượt `--offline`. Annoy/NeMo cần C++ Build Tools (installer silent trả 1602); Torch Python 3.11 đã sửa lỗi DLL bằng pin 2.9.1.
- Nguồn/AI hỗ trợ: Codex hỗ trợ kiểm tra môi trường và tích hợp; đối chiếu bằng source, lệnh chạy và artifact, không dùng kết quả tự dựng.

## Cập nhật sau khi nộp

Chưa nộp; sẽ ghi commit, thời điểm và mọi thay đổi sau nộp khi có.

## Current integration update (2026-10-12)

- Tasks 1-12 were implemented in `src/phase_a_ragas.py`, `src/phase_b_judge.py`, and `src/phase_c_guard.py`. `src/m4_eval.py` was adapted to the installed RAGAS 0.1.22 signature and Windows Torch import order. Gemini-compatible judge and guard configuration is prepared in memory; keys remain in local `.env`.
- Offline verification: 87 passed, 3 integration tests deselected. The 50 saved answers are all extractive fallback with three contexts each; no live A/B/C artifact exists yet.
- A live RAGAS attempt initialized the local embedding model, then hit a network connection failure. A retry under elevated network access was rejected by automatic approval review because it would send 50 questions, answers, contexts, and references to Gemini without a separate explicit approval for that payload and destination. No score was recorded.
- NeMo 0.10.0 and its other Python dependencies installed, but Annoy 1.17.3 could not build without Microsoft C++ Build Tools. `setup_nemo_rails()` now uses a local exact-cosine MiniLM index when Annoy is absent; NeMo 0.10.0 initializes with this backend. This replaces only NeMo flow search, not the LLM rails. Phase C still has no live measurements because API-data approval is pending. `pip check` reports missing Annoy although the alternate backend works.
- The three Markdown reports record preliminary observations and proposed gates, with all unavailable measurements marked as not measured. The offline checker passes source and answers but fails the three absent A/B/C JSON artifacts. This is not yet a complete submission.
- Contribution: Nguyen Minh Luong is the sole member and integration/submission owner. Source edits, local tests and the existing answers are the work evidence; no fabricated experiment numbers were added.

- 2026-10-12 follow-up: user confirmed no Annoy environment. Added `src/nemo_exact_index.py` as an explicit NeMo embedding search provider using cached MiniLM weights and exact cosine ranking. NeMo initialization and a local semantic search smoke check succeeded. This backend difference must be disclosed with any later Phase C artifact.
