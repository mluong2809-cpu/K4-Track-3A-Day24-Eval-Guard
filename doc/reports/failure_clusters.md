# Phase A — RAGAS trên 50 câu

Nhóm: NguyenMinhLuong (cá nhân), Nguyễn Minh Lương — 2A202602618. Nguồn: `artifacts/answers_50q.json` và `fixtures/test_set_50q.json`; kết quả đo: `artifacts/ragas_50q.json`. Cả 50 answers là `extractive_fallback` với ba contexts mỗi câu, nên faithfulness cao phản ánh việc trích nguyên văn, chưa chứng minh đã trả lời đúng và đủ. Evaluator ghi `gemini-3.5-flash-lite` và local `sentence-transformers/all-MiniLM-L6-v2`.

## So sánh distribution

| Nhóm | n | Faithfulness | Answer relevancy | Context precision | Context recall | Mean `avg_score` |
|---|---:|---:|---:|---:|---:|---:|
| factual | 20 | 0.986 | 0.774 | 0.767 | 0.683 | 0.803 |
| multi_hop | 20 | 0.978 | 0.677 | 0.250 | 0.479 | **0.596** |
| adversarial | 10 | 1.000 | 0.747 | 0.733 | 0.692 | 0.793 |

`multi_hop` yếu nhất theo **mean `avg_score`**, không theo tổng cột matrix. Mean adversarial (0.793) thấp hơn factual (0.803) rất ít; chênh lệch trên 10 câu chưa cho phép kết luận rộng.

Matrix đếm `worst_metric` của **mọi** câu, kể cả câu có điểm tốt:

| Worst metric | factual | multi_hop | adversarial | Tổng |
|---|---:|---:|---:|---:|
| faithfulness | 1 | 0 | 0 | 1 |
| answer_relevancy | 9 | 1 | 3 | 13 |
| context_precision | 5 | 15 | 4 | **24** |
| context_recall | 5 | 4 | 3 | 12 |

`context_precision` xuất hiện nhiều nhất (24/50), đặc biệt 15/20 multi_hop. Zero precision ở ID 2 và 5 vẫn cần đọc văn bản: contexts có tài liệu đúng chủ đề nhưng answer trích đoạn chưa đi đến con số/quy tắc được hỏi. Không quy mọi zero thành một lỗi search.

## Bottom 10 theo `avg_score` tăng dần

| Rank | ID | Nhóm | Avg | Worst | Evidence và hướng sửa |
|---:|---:|---|---:|---|---|
| 1 | 25 | multi_hop | 0.389 | context_precision | Hỏi lương Junior thử việc cao nhất; answer lấy đoạn **phân loại dữ liệu** dù contexts sau có quy tắc 85% từ `thu_viec.md`. Ưu tiên bảng lương Junior 20 triệu và tính 85% = **17 triệu**. |
| 2 | 5 | factual | 0.408 | context_precision | Context đầu là bảng thẩm quyền mua sắm nhưng answer bị cắt trước dòng trên 50 triệu. Chọn span đúng ngưỡng, trả CEO phê duyệt 55 triệu. |
| 3 | 30 | multi_hop | 0.414 | context_precision | Answer nêu thử việc và 85% lương; reference hỏi BHXH so với PVI. Tìm đủ `thu_viec.md` và `bao_hiem_suc_khoe.md`, diễn đạt hai trạng thái bảo hiểm. |
| 4 | 40 | multi_hop | 0.416 | context_precision | Answer chỉ nói thời gian thử việc Manager; contexts thiếu quy trình sự cố bảo mật. Bổ sung incident response để nêu **báo trong 1 giờ**, không tự xử lý/xóa dấu vết. |
| 5 | 27 | multi_hop | 0.422 | context_precision | Answer trích nghỉ ốm nhưng bỏ v2024 ngày phép và phép tính. Lấy chính sách phép 2024 và quy tắc trừ phép, tính 15+2−4=13 ngày. |
| 6 | 2 | factual | 0.422 | context_precision | Context có bảo hiểm PVI nhưng answer dừng ở phần mở đầu. Chọn span chứa hạn mức **200 triệu/năm** và các phạm vi nội/ngoại trú, nha khoa. |
| 7 | 7 | factual | 0.431 | context_precision | Answer chứa quy trình nghỉ không lương nhưng cắt trước ngưỡng 16–30 ngày. Trả CEO và điều kiện tự đóng bảo hiểm khi nghỉ trên 14 ngày. |
| 8 | 49 | adversarial | 0.442 | context_precision | Answer chỉ trích v2023 12 ngày dù context thứ hai có v2024. So sánh bản **đã hết hiệu lực** với bản hiện hành 15 ngày + 1 ngày/3 năm. |
| 9 | 33 | multi_hop | 0.467 | context_precision | Answer dùng phép v2023 và không tính phụ cấp; contexts có `phu_cap.md` nhưng thiếu phép v2024. Lọc hiệu lực và cộng 1,5 triệu phụ cấp, 19 ngày phép. |
| 10 | 35 | multi_hop | 0.480 | context_precision | Answer chỉ trích quy tắc 85%; contexts có bảng lương nhưng không tổng hợp. Tính 10,2 triệu lương thử việc + 1 triệu ăn trưa, không có điện thoại, tổng 11,2 triệu. |

Các hàng và thứ tự rank lấy trực tiếp từ JSON; `diagnosis`/`suggested_fix` trong artifact do Task 3 sinh, còn bảng này bổ sung đọc thủ công question, answer, contexts và reference.

## Ưu tiên sửa pipeline

1. **Ghép chứng cứ cho multi_hop.** Retrieval cần đủ văn bản cho phép tính/so sánh; enrichment giữ nguồn và thứ tự. ID 25, 27, 30, 33, 35, 40 cho thấy span được trích chỉ bao phủ một ý hoặc sai chủ đề.
2. **Trích đúng span và tổng hợp câu trả lời.** Với ID 2, 5, 7, context đầu có vẻ đúng tài liệu nhưng fallback cắt trước giá trị quyết định. Generation cần đọc span liên quan, thực hiện phép tính và trả thẳng con số.
3. **Chọn phiên bản hiệu lực.** ID 49/33 dùng v2023 dù câu hỏi cần 2024. Lưu metadata ngày hiệu lực; nếu hỏi cả cũ và mới, trình bày cả hai với trạng thái rõ ràng.

Hạn chế: 50 answers là fallback local, không phải output của LLM generation; RAGAS là phép đo tự động và có thể đánh giá khác việc đọc reference. Batch chỉ đại diện cho corpus, model và answers đã lưu.
