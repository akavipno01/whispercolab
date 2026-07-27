# Whisper Colab GPU Backend

Đây là một API Server được thiết kế để chạy trên **Google Colab (GPU)**, sử dụng mô hình **Whisper** của OpenAI để chuyển đổi âm thanh (`.mp3`, `.wav`) thành phụ đề dạng `.srt` hoặc `.vtt`. 
Dự án được tạo ra nhằm cung cấp giải pháp xử lý giọng nói thành văn bản hoàn toàn miễn phí nhờ sức mạnh của Colab GPU, kết hợp với Cloudflare Tunnel để mở API ra ngoài Internet.

## Tính năng
- **Chạy trên Colab GPU**: Tận dụng tối đa hiệu năng của Google Colab (T4 GPU).
- **FastAPI Backend**: Cung cấp API chuẩn RESTful, dễ dàng tích hợp.
- **Cloudflare Tunnel**: Tự động cấp phát HTTPS URL tạm thời không cần NAT Port.
- **Dễ triển khai**: Chỉ cần 1 click để chạy toàn bộ hệ thống qua file Notebook.

## Hướng dẫn sử dụng trên Google Colab
1. Mở file `Whisper_Colab.ipynb` trong repo này bằng Google Colab.
2. Trên Menu Colab: Chọn **Runtime** -> **Change runtime type** -> Hardware accelerator chọn **GPU (T4)**.
3. Chạy từng ô (Cell) hoặc ấn **Run all** để khởi chạy môi trường.
4. Đợi vài phút để hệ thống cài đặt `ffmpeg`, `cloudflared` và tải model Whisper.
5. Sau khi hoàn tất, ở Cell cuối cùng sẽ in ra một liên kết (URL) của Cloudflare (VD: `https://xyz.trycloudflare.com`).
6. Dùng URL đó làm Base URL cho API của bạn.

## API Endpoints

### `POST /transcribe`
Chuyển đổi file âm thanh thành phụ đề.

- **Request Body (Multipart/form-data):**
  - `file`: File âm thanh (.mp3, .wav...)

- **Response:**
  Trạng thái HTTP 200 kèm nội dung file `.srt`.

## Chạy thử cục bộ (Local)
Nếu bạn có sẵn GPU và muốn chạy ở máy cá nhân:
```bash
git clone https://github.com/akavipno01/whispercolab.git
cd whispercolab
pip install -r backend/requirements.txt
cd backend
python run.py
```
API sẽ chạy tại `http://localhost:8000`.

## Giấy phép
MIT License
