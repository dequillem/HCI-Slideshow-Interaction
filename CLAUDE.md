# HCI-Slideshow-Interaction

Hệ thống điều khiển slide bằng cử chỉ tay, có cơ chế chống Midas touch (kích hoạt nhầm). Nhóm 12, chủ đề B2.
Model GRU được **train ở repo nghiên cứu riêng** `HCI-project` (máy nhóm: `C:\Users\admin\OneDrive\Máy tính\Pacman\HCI-project`). Repo này chỉ **dùng** model, không train.

## Mục tiêu đề tài (theo "Báo cáo tiến độ 1 nhóm 12 chủ đề B2")

- **Bài toán:** người thuyết trình vung tay, chỉ biểu đồ khi nói -> hệ thống nhận cử chỉ nhưng không biết người dùng có *định* ra lệnh không (Midas Touch).
  Câu hỏi trọng tâm không phải "đây là cử chỉ gì" mà là "có nên thực thi không".
- **RQ1 — ngưỡng thích ứng theo độ mơ hồ:** cử chỉ rõ thì nhận nhanh, mơ hồ thì cần thêm bằng chứng. Có giảm false trigger mà không tăng
  đáng kể command miss và latency so với ngưỡng cố định không? Tín hiệu: độ tin cậy, margin top-1/top-2, độ ổn định qua khung, vận tốc/quỹ đạo.
- **RQ2 — abstention:** thêm trạng thái "chưa chắc chắn": quan sát thêm một cửa sổ ngắn (hoặc xin xác nhận có giới hạn), vẫn không rõ thì từ chối.
  Có giảm kích hoạt nhầm với mức tăng chấp nhận được về miss, tỉ lệ từ chối và latency không?
- **Thực nghiệm:** cùng một bộ nhận diện, chạy 4 cấu hình trên cùng dữ liệu: C1 ngưỡng cố định, C2 thích ứng, C3 cố định + abstention,
  C4 kết hợp (không mặc định là tốt nhất). Tình huống: lệnh có chủ ý, hoạt động nền (chỉ tay, vung tay, minh họa, chỉnh áo, cầm bút), near-miss.
- **Chỉ số:** false triggers/giờ (trọng tâm), command recall, precision, latency (từ lúc bắt đầu cử chỉ), task completion time, usability.
  Luôn báo cáo cả false trigger lẫn recall; tách train/test theo người/phiên.
- **Dữ liệu:** dữ liệu công khai (Jester, IPN Hand, HaGRID) cho nhận diện; **dữ liệu tự thu có nhãn Ý ĐỊNH** (bắt đầu/kết thúc, có ý định ra lệnh
  không, lệnh dự định) để đánh giá Midas Touch.
- **Sản phẩm cần đạt:** demo end-to-end tiến/lùi slide; UI trạng thái (chờ / nhận lệnh / chưa chắc / từ chối / thực thi); pipeline đổi cấu hình
  không phải viết lại; bộ dữ liệu nhỏ có nhãn ý định; báo cáo có số liệu trả lời **ít nhất một RQ**.

## Tiến độ (cập nhật 2026-11-16)

Đã có:
- Demo end-to-end chạy được (webcam -> MediaPipe -> GRU + luật -> gate -> pynput -> PowerPoint), UI TẬP/GỬI THẬT, log `sessions/*.jsonl`, replay.
- GRU v1 (HCI-project): Jester theo frame, accuracy 92.2%, F1 next/previous 0.88.
- 4 cấu hình C1–C4 trong app; C2 dùng **đúng công thức** của `HCI-project/src/policies.py` (đã đối chiếu số: lệch 0 trên 96 trường hợp).
- C3/C4 abstention **có tác dụng thật** (bản cũ ở cả hai repo chỉ đổi tên reject: margin ≥ 0.6 khi top-1 ≥ 0.8 nên ngưỡng margin không bao giờ chặn;
  `HCI-project/reports/frames/evaluation/policy_summary.csv` có fixed == fixed_abstention ở mọi chỉ số trừ abstention_rate).
- Replay session 23:23 (người dùng chỉ vuốt next ~10 lần): fixed 5 next + 3 previous sai; abstain/combined 7 next + 1 previous sai.
  Chưa phải kết quả chính thức vì session chưa có nhãn ý định.

Chưa có / việc tiếp theo (theo thứ tự ưu tiên):
1. **Dữ liệu thật có nhãn ý định** — lỗ hổng lớn nhất. Mọi session hiện có `truth = null`. Ý tưởng: chế độ thu theo kịch bản trong UI
   (nhắc "vuốt NEXT" / "nói tự nhiên 30 s" / "chỉ vào màn hình" theo lịch, tự ghi `truth = cmd:next` / `bg:...`), rồi `src/evaluation/metrics.py` tính được ngay.
2. Hiệu chỉnh tham số abstention (`abstain_wait_ms`, `clear_conf`, `conflict_floor`) trên dữ liệu có nhãn; hiện là giá trị chọn tay.
3. HCI-project vẫn dùng abstention cũ (vô tác dụng) -> port abstention mới sang `HCI-project/src/policies.py` nếu muốn đánh giá offline trên Jester.
4. Chốt bộ cử chỉ: thumb up/down giờ là LỆNH (start/exit) nhưng HCI-project coi Thumb Up/Down là near-miss -> `near_miss_trigger_rate` cho chúng mất nghĩa.
5. Tách cấu hình demo (`swipe`, gate lỏng) khỏi cấu hình thực nghiệm (C1–C4 chung hold/cooldown/reverse_block) khi chạy so sánh.
6. Latency: mô phỏng ~1.5 s từ lúc bắt đầu cử chỉ (cửa sổ GRU 2.7 s). Mục tiêu <100 ms trong báo cáo chỉ là phần mềm sau quyết định — ghi rõ khi báo cáo.

Lệch so với thiết kế trong báo cáo (cần ghi nhận khi viết báo cáo): bỏ bước ARM (`require_arm: false`); thêm `reverse_block_ms` và cơ chế
"đổi cử chỉ rồi mới nhận lại" (heuristic kỹ thuật, áp dụng cho mọi cấu hình); thumb up/down = vào/thoát trình chiếu; bỏ 3 ngón và play_pause.

## Chạy

```powershell
python -m src ui                     # giao diện (mở ở chế độ TẬP, không gửi phím)
python -m src ui --policy abstain    # thử một cấu hình thực nghiệm
python -m src live --send-keys       # gửi phím thật vào PowerPoint
python -m src replay sessions/x.jsonl --policies fixed,adaptive,abstain,combined
python -m pytest -q --continue-on-collection-errors
```

Chọn bộ nhận diện trong `config.yaml`: `recognizer: hybrid | gru | rule` (`rule` chỉ có tư thế tĩnh, không chuyển slide được).
Random Forest + script thu/train cũ (`03_collect`, `04_train`, `06_hagrid`, `landmark_utils`) và cử chỉ 1–2 ngón đã bị xóa.

## Luồng xử lý (`src/pipeline.py`)

```
CameraSource (lật gương) -> HandTracker -> Observation -> FeatureExtractor -> FeatureWindow
  -> Recognizer -> Hypothesis -> IntentGate (policy) -> Decision -> ActionDispatcher -> phím
```

- `IntentGate` (`src/decision/gate.py`): IDLE -> (nắm tay giữ `arm_hold_ms`, chỉ khi `require_arm`) ARMED -> COMMAND (giữ `hold_ms`) -> EXECUTE -> COOLDOWN.
  Thumb up (`like`) = `start_show` (Shift+F5), thumb down (`dislike`) = `exit_show` (Esc), ánh xạ ở `datatypes.POSE_COMMANDS`; giữ `command_hold_ms` (600).
  Lệnh vừa thực hiện (tư thế tĩnh) hoặc vừa bị abstention từ chối phải đổi cử chỉ rồi mới nhận lại (`released`).
  CONFIRM còn trong code nhưng `confirm_commands: []`. Cử chỉ 3 ngón đã bỏ.
- Policy (`src/decision/policies.py`), hàm thuần `(cfg, Context) -> Gating`:
  - `fixed` C1 | `adaptive` C2 | `abstain` C3 | `combined` C4 — dùng chung `hold_ms`, `cooldown_ms`, `reverse_block_ms`, `require_arm`.
  - `naive`: không gate (mốc). `adaptive_speed`: adaptive cũ theo tốc độ tay. `swipe`: cấu hình DEMO, không dùng để so sánh.
- **C2 adaptive**: ngưỡng = `conf + margin_weight*(1-margin) + stability_weight*(1-ổn định)`, kẹp `[adapt_min_conf, adapt_max_conf]`.
  Ổn định = tỉ lệ khung cùng nhãn trong chuỗi khung hợp lệ liên tiếp (`stability_window_ms`), khung không hợp lệ xóa chuỗi, khung đầu không bị phạt —
  giống `history` của HCI-project. Đổi công thức ở một repo thì phải đổi cả repo kia.
- **C3 abstention**: khi đã giữ đủ lâu mà còn nghi ngờ (`low_conf` trên `uncertain_floor` | `unclear` < `clear_conf` | `low_margin` |
  `conflict` = chiều vuốt ngược ≥ `conflict_floor` trong `conflict_window_ms`) -> Decision UNCERTAIN, quan sát thêm tối đa `abstain_wait_ms`.
  Hết nghi ngờ -> thực thi; hết hạn: đủ ngưỡng và chiều ngược đã hết -> thực thi, ngược lại REJECT `abstain_timeout`.
  Nhắm vào lỗi lớn nhất: đoạn lấy đà bị đọc thành chiều ngược. Cử chỉ rõ (≥ `clear_conf`, không mâu thuẫn) không bị chậm thêm.
  `Hypothesis.swipe_probs` (Hybrid luôn gắn xác suất GRU next/previous, kể cả khi luật thắng) là nguồn để dò mâu thuẫn.
- **Mặc định `policy: swipe`** (demo): không ARM, gate để lỏng theo yêu cầu: `conf` 0.7, `gru_override` 0.7, `swipe_hold_ms` 0 (đỉnh GRU chỉ dài ~300 ms),
  `cooldown_ms` 800, `reverse_block_ms` 2500 (nhịp đưa tay về bị GRU đọc thành lệnh ngược). Nhảy slide bừa -> tăng `conf`/`gru_override`.
  `disabled_commands: [play_pause]` vì mở bàn tay -> Space -> PowerPoint sang slide khi đang nói.
  `command_hold_ms` áp dụng cho mọi policy trừ `naive`.

## GRU / Hybrid (`src/perception/gru_recognizer.py`)

- **hybrid** (hướng nhóm chọn): GRU nhận **vuốt** phải = `next`, vuốt trái = `previous`; luật hình học (`RuleRecognizer`) nhận
  tư thế tĩnh `arm`, `play_pause`, `like`, `dislike`. Không còn mẫu next/previous tĩnh trong `RULE_TEMPLATES`.
  GRU thắng khi `p >= gru_override`; tay nhanh hơn `static_max_speed` thì không nhận tư thế lệnh tĩnh (tránh vuốt bàn tay mở bị đọc thành play_pause).
- Zoom (`zoom_in/zoom_out`) **tạm bỏ**: xác suất gộp vào `none`.
- Model nằm ở `models/gru/`: `gru.keras`, `gru.labels.json`, `gru.meta.json`. Cập nhật model = copy 3 file từ `HCI-project/models/`.
  `meta.json` quyết định `sequence_length` và `step_ms` — **không đặt cứng trong code**.

### Bất biến bắt buộc (sai là model chạy sai mà không báo lỗi)

1. Tiền xử lý giống hệt `HCI-project/src/sequence_utils.py`: 63 tọa độ ảnh **thô** (không chuẩn hóa, không làm mượt) + 7 motion so với bước trước;
   không thấy tay -> 0, motion = 0 khi bước này hoặc bước trước không có tay; cửa sổ đệm 0 bên trái.
   Vì vậy `FeatureWindow.landmarks` mang tọa độ thô; đừng đưa `FeatureWindow.vector` (đã chuẩn hóa + trung bình) vào GRU.
2. Lấy mẫu theo **thời gian** (`step_ms`), không theo số khung camera.
3. `gru_flip_x: true`: CameraSource lật gương còn ảnh Jester thì không (Jester "Swiping Left" có dx > 0). Tắt cờ này là next/previous bị đảo.
4. `tests/fixtures/gru_parity.json` sinh từ code + model của repo nghiên cứu. Đổi tiền xử lý hoặc model -> sinh lại fixture
   rồi chạy `tests/test_gru_recognizer.py`.
5. `Pipeline` gọi `recognizer.reset()` lúc ACCEPT và ở mọi khung COOLDOWN: cửa sổ GRU (~2.7 s) dài hơn cooldown, không xóa thì
   phần đuôi của chính cú vuốt vừa thực hiện bị nhận lại thành lệnh thứ hai.
6. Model chạy qua `tf.function` (graph, shape cố định): ~3 ms/lần. Gọi eager `keras_model(x)` mất ~180 ms/lần, làm khựng camera.

## Tình trạng đã biết

- Có sẵn 17 test fail (từ trước khi tích hợp GRU): `tests/helpers.make_hand` unpack sai `THUMBS` (4 điểm, code mong 2 giá trị),
  một số test mong nhãn `none` trong probs, và vài test vẫn dựng next/previous bằng tư thế 1–2 ngón (đã bỏ).
  `test_gru_recognizer.py`, `test_swipe_policy.py`, `test_ambiguity_policies.py` dùng helper riêng và đều pass.
- Model GRU hiện tại (v1, `models/gru/`): train trên CSV Jester theo frame (58k video, 6 fps, `step_ms` 166.7), accuracy 92.2% offline
  (F1 next 0.88, previous 0.88, none 0.94). Bản cũ v0 (1 dòng/video, 81%) đã xóa khỏi repo này; còn backup ở `HCI-project/models/v0_video_level/`.
- Mô phỏng offline (HCI-project, conf 0.8): `wrong_command_rate` 34%, median latency 1.5 s. Với cấu hình chỉ next/previous, giữ 200 ms,
  cooldown 2 s: vuốt đúng 82.5% nhưng 16.6% cú vuốt có thêm lệnh NGƯỢC CHIỀU, phần lớn bắn TRƯỚC lệnh đúng (đoạn lấy đà).
  Tăng giữ lên 350–500 ms và/hoặc `conf` 0.9 giảm còn 4–12% (bảng trong `HCI-project/reports/frames/`). Abstention C3 nhắm đúng lỗi này.
- TensorFlow chỉ được import khi `recognizer` là `gru`/`hybrid`.
