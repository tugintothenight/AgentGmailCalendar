# HydraDB: Cognitive Memory Core for AI Agents

*HydraDB bản demo, chưa có Knowledge Graph, hybrid search như bài báo về HydraDB.*

## Tính năng Cốt lõi
### 1. Kiến trúc Bộ nhớ 
Phân loại thành 3 vùng nhận thức:
- **Episodic:** Nhật ký những việc đã xảy ra
- **Semantic:** Sở thích, thói quen của người dùng
- **Procedural:** Các quy tắc hệ thống bất di bất dịch.

### 2. Semantic Search
Bỏ qua Keyword matching truyền thống. HydraDB sử dụng mô hình nhúng `all-MiniLM-L6-v2` để chuyển hóa văn bản thành Vector số thực và tìm kiếm bằng **Cosine Similarity**, giúp AI hiểu được ý nghĩa ẩn sau câu nói.

### 3. Thuật toán quên lãng
Mô phỏng đường cong lãng quên Ebbinghaus của não người. Ký ức càng cũ, trọng số ảnh hưởng càng thấp, nhưng khi được nhắc lại, ký ức sẽ được tăng cường mạnh hơn.
### 4. Memory Feedback Loop
Dùng prompt để hướng dẫn agent cập nhật bộ nhớ dựa trên hành động và phản hồi => Các ký ức quan trọng sẽ được củng cố, trong khi các ký ức ít sử dụng sẽ bị suy giảm theo thời gian.

## **file .bat**
do python có chế độ đệm theo khối, đợi đủ 1 khối dữ liệu nhất định sẽ nhả 1 lần dữ liệu, nhưng openfang lại đợi bộ đệm liên tục theo thời gian => lỗi => viết file `.bat` để ép python nhả bộ đệm liên tục (bật `PYTHONUNBUFFERED`)
