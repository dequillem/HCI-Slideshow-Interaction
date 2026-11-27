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

## Tiến độ (cập nhật 2026-11-25)

Đã có:
- Demo end-to-end chạy được (webcam -> MediaPipe -> GRU + luật -> gate -> pynput -> PowerPoint), UI TẬP/GỬI THẬT, log `sessions/*.jsonl`, replay.
- GRU v1 (HCI-project): Jester theo frame, accuracy 92.2%, F1 next/previous 0.88.
- 4 cấu hình C1–C4 trong app; C2 dùng **đúng công thức** của `HCI-project/src/policies.py` (đã đối chiếu số: lệch 0 trên 96 trường hợp).
- C3/C4 abstention **có tác dụng thật** (bản cũ ở cả hai repo chỉ đổi tên reject: margin ≥ 0.6 khi top-1 ≥ 0.8 nên ngưỡng margin không bao giờ chặn;
  `HCI-project/reports/frames/evaluation/policy_summary.csv` có fixed == fixed_abstention ở mọi chỉ số trừ abstention_rate).
- Replay session 23:23 (người dùng chỉ vuốt next ~10 lần): fixed 5 next + 3 previous sai; abstain/combined 7 next + 1 previous sai.
  Chưa phải kết quả chính thức vì session chưa có nhãn ý định.
- (2026-11-21) Thực nghiệm offline trong HCI-project (`src/09_compare_models.py`, `10_tune_policies.py`, `11_summarize_experiments.py`;
  phân tích `reports/EXPERIMENTS_NOTES.md`, số liệu `reports/EXPERIMENTS_RESULTS.md`). Abstention mới đã port sang `HCI-project/src/policies.py`
  (C1/C2 giữ nguyên kết quả cũ). Kết quả trên Jester test, chỉ next/previous là lệnh, kích hoạt nhầm ≤ 2%:
  - Cấu hình demo `swipe` (giữ 0 ms) với GRU: 59% đúng lệnh sạch, **30% kèm lệnh sai chiều**; C1 chỉnh (ngưỡng 0.8, giữ 500 ms, cooldown ~0.8 s):
    75.3% / 7.5% sai chiều / 1.6% nhầm. Mọi model đều chọn ngưỡng ~0.8 + giữ 500 ms.
  - Model: BiGRU 78.5% (C2), LSTM 77.7% (C4), GRU 75.3%, MLP 66%; cửa sổ 10–12 bước không giảm độ trễ. Một seed/model.
  - RQ1: C2 ≈ C1 ở 7/9 model, hơn ở BiGRU/TCN. RQ2: abstention không nhất quán trên Jester giả lập (hơn ở TCN/LSTM, kém ở GRU/attention),
    cần dữ liệu thật có nhịp lấy đà/đưa tay về để kết luận.
- (2026-11-22) Nhóm đã thu **dữ liệu thật có nhãn ý định** (67 video, 2 người: 6 video thuyết trình dài + 61 clip near-miss) ở
  `HCI-project/data/real_*.csv`. Đánh giá (`HCI-project/src/12_eval_real.py`, `reports/REAL_DATA_EVAL.md`): mọi model Jester chỉ nhận 5–11/29 lệnh;
  BiGRU (app) 7/29. Nguyên nhân chính: người đứng xa camera -> tay nhỏ ~4 lần Jester, model dùng tọa độ thô nên không thấy cú vuốt.
  C1–C4 không khác nhau đo được. Near-miss cự ly gần bị bắn 69%. Khi demo: đứng gần camera.
  Đã thử train lại với tăng cường "đứng xa" (co tọa độ tay 1–5 lần, `*_far.keras`): trúng 11–16/29 nhưng nhầm 87–133 lần/17 phút;
  ở cùng mức nhầm không hơn model cũ -> **không đổi model app**.
- (2026-11-25) **Môi trường GPU + thí nghiệm tham số C2/C3 (xong)** ở HCI-project; `config.yaml` chưa đổi, gate có thêm tùy chọn mặc định tắt. Cửa sổ ổn định và dải ngưỡng
  của C2 hiện tại gần như **không có tác dụng**, C2 ≈ C1 ngưỡng 0.78; C3 có lợi trên Jester, chưa xác nhận trên dữ liệu thật; trên dữ liệu thật mọi policy dừng ở 7/29 lệnh.
  Chi tiết: mục "Thí nghiệm tham số C2/C3 (2026-11-25)" cuối file.

Chưa có / việc tiếp theo (theo thứ tự ưu tiên):
1. **Dữ liệu thật có nhãn ý định** — đã có bản đầu ở HCI-project (29 lệnh, 2 người); cần thêm người, trích ~17 phút video "harmonic oscillation"
   đã gán nhãn, và train lại với tăng cường tỉ lệ / fine-tune trên dữ liệu thật. Session của app vẫn có `truth = null`. Ý tưởng: chế độ thu theo kịch bản trong UI
   (nhắc "vuốt NEXT" / "nói tự nhiên 30 s" / "chỉ vào màn hình" theo lịch, tự ghi `truth = cmd:next` / `bg:...`), rồi `src/evaluation/metrics.py` tính được ngay.
2. Hiệu chỉnh tham số abstention (`abstain_wait_ms`, `clear_conf`, `conflict_floor`) trên dữ liệu có nhãn; hiện là giá trị chọn tay.
3. ~~Port abstention sang HCI-project~~ (xong 2026-11-21). Còn: train thêm 2–3 seed cho GRU/BiGRU/LSTM trước khi đổi model của app;
   cân nhắc đổi cấu hình demo sang ngưỡng 0.8 + giữ 500 ms (giữ 0 ms gây sai chiều rất nhiều trong thực nghiệm).
4. Chốt bộ cử chỉ: thumb up/down giờ là LỆNH (start/exit) nhưng HCI-project coi Thumb Up/Down là near-miss -> `near_miss_trigger_rate` cho chúng mất nghĩa.
5. Tách cấu hình demo (`swipe`, gate lỏng) khỏi cấu hình thực nghiệm (C1–C4 chung hold/cooldown/reverse_block) khi chạy so sánh.
6. Latency: mô phỏng ~1.5 s từ lúc bắt đầu cử chỉ (cửa sổ GRU 2.7 s). Mục tiêu <100 ms trong báo cáo chỉ là phần mềm sau quyết định — ghi rõ khi báo cáo.
7. Quyết định có dùng `config_experiment.yaml` cho thực nghiệm người dùng không; giảm nhầm thumb up/down (mục "Thí nghiệm tham số C2/C3").

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
- **Mặc định `policy: swipe`** (demo, đổi 2026-11-21 theo yêu cầu): `gru_override` 0.8 (= ngưỡng cho vuốt), `swipe_hold_ms` 0 trong `config.yaml` hiện tại (từng là 500, 100), `conf` 0.7
  (để thumb up/down vẫn qua — luật chỉ đạt ~0.86). Replay session thật cho thấy giữ 500 ms làm sót nhiều cú vuốt (đỉnh GRU thật chỉ ~300 ms;
  phiên 23:23: 10 -> 4 lần next); 167 ms giữ được 8–9/10. `cooldown_ms` 800, `reverse_block_ms` 2500 (nhịp đưa tay về bị GRU đọc thành lệnh ngược). Nhảy slide bừa -> tăng `conf`/`gru_override`.
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

- Bộ test: 71 test, đều pass (17 test fail cũ đã được sửa).
- Model hiện tại trong `models/gru/` (vẫn tên `gru.keras`) là **BiGRU** (`HCI-project/models/zoo/bigru_L16.keras`, đổi 2026-11-21): Jester theo frame,
  accuracy 92.2%, F1 next 0.87 / previous 0.87 / none 0.95, ~6 ms/lần suy luận. GRU v1 cũ (92.2%) còn ở `HCI-project/models/gru.keras` và trong git.
  Trên session thật BiGRU không hơn GRU rõ rệt. Bản cũ v0 (1 dòng/video, 81%) đã xóa khỏi repo này; còn backup ở `HCI-project/models/v0_video_level/`.
- Mô phỏng offline (HCI-project, conf 0.8): `wrong_command_rate` 34%, median latency 1.5 s. Với cấu hình chỉ next/previous, giữ 200 ms,
  cooldown 2 s: vuốt đúng 82.5% nhưng 16.6% cú vuốt có thêm lệnh NGƯỢC CHIỀU, phần lớn bắn TRƯỚC lệnh đúng (đoạn lấy đà).
  Tăng giữ lên 350–500 ms và/hoặc `conf` 0.9 giảm còn 4–12% (bảng trong `HCI-project/reports/frames/`). Abstention C3 nhắm đúng lỗi này.
- TensorFlow chỉ được import khi `recognizer` là `gru`/`hybrid`.

## Thí nghiệm tham số C2/C3 (2026-11-25)

Mục đích: thử C2 với cửa sổ lịch sử 1/2/5 s thay vì 800 ms và dải ngưỡng rộng/hẹp hơn; thử C3 với thời gian giữ/chờ khác.
Làm ở HCI-project (file mới, **chưa commit**):

- `src/policy_variants.py` (`VariantPolicy`): mặc định cho chuỗi lệnh giống hệt `policies.py` (`tests/test_policy_variants.py`; cả bộ 42 test pass).
  Thêm: cửa sổ ổn định có/không xóa lịch sử, ngưỡng kiểu dải `lo + (hi-lo)*rủi_ro`, cách quyết định khi hết hạn chờ, dung sai khung rớt.
- `src/14_policy_experiments.py predict|run`: ghép video Jester thành phiên dài liên tục (val 5.940 clip, test 5.825 clip, mỗi tập ~6.4 giờ, giữa hai
  clip có 0.5–2 s không tay), vì luồng cũ chỉ 6.7 s nên không thử được cửa sổ 2–5 s. Kèm 6 video thật + 40 clip near-miss thật.
- Kết quả ở `reports/policy_experiments/` (gitignore): `ofat.csv` = đổi từng tham số quanh cấu hình app, số **validation**; `search.csv` = 8.688 cấu hình/model;
  `selected.csv` = chọn trên validation, báo cáo **test** + CI 95% ghép cặp theo phiên so với C1.
- Offline dùng thẳng xác suất GRU, **không** qua `gru_override`; 1 bước = 167 ms.

Kết luận (BiGRU/GRU, trừ chỗ ghi khác; "sạch" = đúng lệnh, không kèm lệnh sai; "nhầm" = tỉ lệ clip không phải lệnh bị kích hoạt):

1. **Cửa sổ ổn định C2 từ 0.8 lên 10 s: 0 quyết định thay đổi** (cả LSTM, cả video thật), vì khung không hợp lệ xóa lịch sử. Nhận ngay (giữ 0 ms) thì
   `stability_weight` cũng vô tác dụng. Bỏ việc xóa lịch sử: chỉ bớt nhầm nhẹ khi cửa sổ ≥ 5 s (BiGRU giữ 500 ms: 1.7% -> 1.4%), sạch không tăng.
2. **Dải `adapt_min_conf`–`adapt_max_conf`**: đổi từ 0.7–0.8 tới 0.3–0.999 chỉ làm khác 0–6 lệnh (cả LSTM). Công thức chỉ CỘNG vào `conf` nên cận dưới ≤ `conf`
   không bao giờ chạm, cận trên hiếm khi chạm.
3. **C2 (app) ≈ C1 ngưỡng 0.77–0.78** ở cả 5 model (khác 15–40 lệnh trong ~630–1.190), vì margin gần như là hàm của độ tin cậy.
   Đọc code app (chưa chạy kiểm chứng): `gru_override` 0.80 loại vuốt < 0.80 trước gate còn ngưỡng C2 với `conf` 0.70 khi đó ≤ 0.78 (trừ lúc vừa đổi chiều)
   -> **với vuốt, C1 và C2 trong app gần như trùng nhau**; `low_conf`/`uncertain_floor` của C3/C4 cũng hầu như không hoạt động.
4. **Công thức dải mới** (nhiễu / mơ hồ / đổi nhãn trong 0.8–10 s; dải 0.75–0.85 tới 0.5–0.99): chưa hơn C1 nhất quán; sau chỉnh chỉ hơn rõ ở GRU
   ngân sách 1% (+4.8 điểm), còn lại ≤ 0.8 điểm.
5. **C3 thời gian chờ** (giữ 0 ms, `clear_conf` 0.90): 167 -> 667 ms: sạch BiGRU 60.4 -> 65.5%, GRU 64.7 -> 69.5%; 1 s tương đương và bớt nhầm chút;
   1.5–2 s bắt đầu mất lệnh. Hợp lý: ~700–1000 ms.
6. **C3 `clear_conf` là tham số có tác dụng nhất** (giữ 0 ms, BiGRU): 0.90 -> 0.98: sạch 65.5 -> 70.4%, nhầm 4.1 -> 2.4%, sai chiều 20.9 -> 13.3%,
   độ trễ trung vị vẫn 1.17 s. Gần bằng C1 giữ 500 ms (70.4 / 2.2 / 10.8%) mà nhanh hơn ~333 ms. GRU cùng chiều nhưng nhầm còn 4.9%.
   Khi đã giữ 500 ms thì gần như không đổi.
7. **C3 cửa sổ dò mâu thuẫn hướng** 0.7 -> 5 s (giữ 0 ms): nhầm BiGRU 4.1 -> 3.0%, GRU 6.6 -> 4.6%, sạch mất 0.1–0.9 điểm. Đây là nơi lịch sử dài có ích;
   ở giữ 500 ms tác dụng nhỏ. `conflict_floor`, `margin` ≤ 0.4, `uncertain_floor`: hầu như không đổi.
8. **C3 hết hạn chờ**: "còn nghi ngờ là từ chối" mất nhiều lệnh (BiGRU 65.5 -> 58.3% ở giữ 0 ms, 70.9 -> 58.7% ở giữ 500 ms). Giữ cách hiện tại.
9. **Dung sai 1–2 khung rớt khi giữ 500 ms**: C1 BiGRU 70.4 -> 72.6%, GRU 68.7 -> 70.5%, nhầm +0.2 điểm. Nhận ngay thì không có tác dụng.
10. **Sau khi chọn tham số (nhầm ≤ 2% trên validation), sạch trên test:**

    | | C1 | C1+dung sai | C2 gốc | C2 dải mới | C3 gốc | C3 mở rộng | C4 gốc | C4 mở rộng |
    |---|---|---|---|---|---|---|---|---|
    | BiGRU | 72.1 | 73.3 | 72.6 | 72.1 | 73.8 | 73.7* | 73.2 | 73.7 |
    | GRU | 63.3 | 66.7* | 63.3 | 63.8* | 66.3* | 69.0* | 66.2* | 68.8* |

    (* CI 95% của chênh lệch với C1 không chứa 0, chưa hiệu chỉnh so sánh nhiều lần; một seed/model.) C2 hơn C1 ≤ 0.5 điểm, C3/C4 hơn ~1–6 điểm.
    "Mở rộng" gồm cả dung sai khung rớt nên không phải toàn bộ lợi ích là của abstention.
11. **Dữ liệu thật:** trong 8.688 cấu hình/model, tốt nhất vẫn **7/29 lệnh** khi nhầm ≤ 4 (mọi họ C1–C4, cả hai model), dù chọn ngay trên dữ liệu đó
    -> nút thắt là model, không phải policy.

Làm tiếp (2026-11-25): đã chạy đủ 5 model và thử trên đúng pipeline app. Tổng hợp: `HCI-project/reports/POLICY_PARAM_EXPERIMENTS.md`.

- Công cụ: `python -X utf8 -m src.evaluation.param_replay --out x.csv` (video thật có nhãn + near-miss + session). Tùy chọn mới trong gate, **mặc định tắt**
  (đã đối chiếu: số lệnh không đổi): `swipe_conf`, `grace_ms`, `stability_reset`. Test: `tests/test_param_options.py`.
- Xác nhận mục 3 bằng replay: C1 và C2 gần như cùng số lệnh vuốt; cửa sổ 0.8–10 s (xóa lịch sử) và mọi dải ngưỡng không đổi gì.
- `hold_ms` >= 330 làm sót vuốt: session 23:23 (~10 next, nhãn yếu) 9 -> 4; 100–250 ms giữ được 8–9. Video có nhãn không phân biệt được (đều 7/29).
- Mục 6, 7 **không chuyển sang session thật**: `clear_conf` 0.95 hoặc cửa sổ mâu thuẫn >= 2 s (giữ 250) làm 23:23 còn 6–7 next. Mục 9 gần như không tác dụng.
- `config_experiment.yaml` (`gru_override` 0.6, `swipe_conf` 0.8, `hold_ms` 250, `adapt_max_conf` 0.99): C1–C4 khác nhau (C1 95-48, C2 89-36, C3 89-32,
  C4 87-28 lệnh next-previous trên 16 session không nhãn). Chưa biết phần giảm là lệnh sai hay lệnh thật -> cần dữ liệu có nhãn.
- **Nhầm chủ yếu là thumb up/down** (33 so với 2 lần vuốt trong 17 phút video, đo ở 7.5 fps): giữ 1500 ms còn 11, ngưỡng 0.84 còn 16.

## Train trên GPU (2026-11-25)

TensorFlow ≥ 2.11 không có GPU trên Windows -> dùng WSL2 Ubuntu, môi trường `/root/hci-gpu` (Python 3.12, TF 2.16.2, keras 3.15.1, RTX 3050 4 GB);
không phải sửa code train, lệnh chạy ở CLAUDE.md của HCI-project. Mỗi epoch so với CPU Windows (đo ngắn một lần, dữ liệu ngẫu nhiên): GRU/LSTM/BiGRU/MLP nhanh
~4–6 lần, TCN ~8 lần, attention ~32 lần. Model train trên GPU mở được trên Windows (bigru, lstm, attention: lệch xác suất ≤ 5e-5).
**Chưa train lại đủ 7 model.** Không trộn model CPU và GPU trong một bảng; `infer_ms` đo trong WSL là trên GPU, phải đo lại trên Windows.
