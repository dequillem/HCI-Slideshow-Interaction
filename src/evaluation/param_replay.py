"""Thử tham số C1-C4 trên ĐÚNG pipeline của app (hybrid + gru_override + IntentGate), không cần webcam.

Dữ liệu:
  long   6 video thuyết trình tự thu có nhãn ý định (HCI-project/data/real_long_landmarks.csv, 7.5 fps)
  short  clip near-miss ngắn (bỏ nhóm "thu tay về" vì chứa lệnh thật)
  s2323  session webcam 2026-11-14 23:23, nhãn yếu: người dùng chỉ vuốt next ~10 lần -> previous là sai
  web    các session webcam hybrid còn lại, KHÔNG có nhãn: chỉ đếm số lệnh để xem mức thay đổi

    python -X utf8 -m src.evaluation.param_replay --out param_replay.csv
GRU được nhớ đệm theo cửa sổ đầu vào nên chạy nhiều cấu hình nhanh; bộ nhớ GRU vẫn được reset sau mỗi lệnh như app.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from dataclasses import fields, replace
from pathlib import Path

import numpy as np

from ..config import Config, load_config
from ..datatypes import ACCEPT, COOLDOWN, UNCERTAIN, Observation
from ..decision.gate import IntentGate
from ..perception.features import FeatureExtractor
from ..perception.gru_recognizer import GRURecognizer, HybridRecognizer
from ..perception.recognizer import RuleRecognizer
from .replay import load_log

RESEARCH = Path(__file__).resolve().parents[4] / "Pacman" / "HCI-project"
WEAK = "20261114-232311"
ALL4 = ("fixed", "adaptive", "abstain", "combined")


class _CachedRule:
    def __init__(self, table):
        self.table = table

    def __call__(self, fw):
        return self.table[id(fw)]


class Runner:
    def __init__(self, cfg: Config):
        raw, memo = GRURecognizer(cfg.gru_model_dir, flip_x=cfg.gru_flip_x, step_ms=cfg.gru_step_ms).model, {}

        def model(x):
            k = x.tobytes()
            if k not in memo:
                memo[k] = np.asarray(raw(x))
            return memo[k]
        self.gru_model = model
        self.streams = {}

    def add(self, name, observations, cfg, segs=None):
        fx, rule = FeatureExtractor(cfg), RuleRecognizer(exclude=("next", "previous"))
        fws = [fx(o) for o in observations]
        self.streams[name] = (fws, {id(f): rule(f) for f in fws}, segs)

    def run(self, name, cfg: Config):
        """-> ([(chỉ số khung, t_ms, lệnh)], số lượt vào trạng thái chưa chắc, số lần abstain_timeout)."""
        fws, table, _ = self.streams[name]
        gru = GRURecognizer(cfg.gru_model_dir, flip_x=cfg.gru_flip_x, step_ms=cfg.gru_step_ms, model=self.gru_model)
        rec, gate = HybridRecognizer(cfg, rule=_CachedRule(table), gru=gru), IntentGate(cfg)
        acc, unc, rej, was = [], 0, 0, False
        for i, fw in enumerate(fws):
            d = gate(fw, rec(fw))
            if d.verdict == ACCEPT:
                acc.append((i, fw.t_ms, d.command))
            if d.verdict == ACCEPT or d.state == COOLDOWN:
                rec.reset()
            now = d.verdict == UNCERTAIN
            unc += now and not was
            rej += d.reason == "abstain_timeout"
            was = now
        return acc, unc, rej


def _obs(sec, lm63):
    """Landmark của HCI-project (đã bỏ lật gương) -> Observation như camera app (lật gương)."""
    out = []
    for t, row in zip(sec, lm63):
        t_ms = int(round(t * 1000))
        if not np.any(row):
            out.append(Observation(t_ms))
            continue
        p = row.reshape(21, 3).copy()
        p[:, 0] = 1.0 - p[:, 0]
        out.append(Observation(t_ms, p.tolist()))
    return out


def load_all(runner, cfg, research: Path):
    import pandas as pd
    cols = [f"{a}{i}" for i in range(21) for a in "xyz"]
    df = pd.read_csv(research / "data" / "real_long_landmarks.csv", keep_default_na=False)
    for vid, v in df.groupby("video_id", sort=False):
        tid, scen, lab, segs, s0 = v["trial_id"].to_numpy(), v["scenario"].to_numpy(), v["label"].to_numpy(), [], 0
        for i in range(1, len(v) + 1):
            if i == len(v) or tid[i] != tid[s0]:
                segs.append((s0, i, scen[s0], lab[s0]))
                s0 = i
        runner.add(f"long:{vid}", _obs(v["sec"].astype(float).to_numpy(), v[cols].to_numpy(float)), cfg, segs)
    df = pd.read_csv(research / "data" / "real_short_landmarks.csv", keep_default_na=False)
    for vid, v in df.groupby("video_id", sort=False):
        if "thu tay" in str(v["sub_category"].iloc[0]).lower() or "command_then_return" in str(v["near_group"].iloc[0]):
            continue
        lm = v[cols].to_numpy(float)
        lm = np.concatenate([np.zeros((8, 63)), lm, np.repeat(lm[-1:], 8, axis=0)])
        runner.add(f"short:{vid}", _obs(np.arange(len(lm)) / 7.5, lm), cfg)
    for f in sorted(glob.glob("sessions/*.jsonl")):
        head, obs = load_log(f)
        stem = Path(f).stem
        if head.recognizer == "hybrid" and len(obs) >= 600:
            runner.add(("s2323:" if stem == WEAK else "web:") + stem, obs, cfg)


def evaluate(runner, cfg):
    m = dict(hits=0, p1=0, p2=0, commands=0, wrong=0, false_swipe=0, false_pose=0, near_long=0, short=0, s2323_next=0,
             s2323_previous=0, web_next=0, web_previous=0, web_pose=0, unc=0, rej=0)
    hit_ids, lat = [], []
    for name, (fws, _, segs) in runner.streams.items():
        acc, unc, rej = runner.run(name, cfg)
        kind, rest = name.split(":", 1)
        swipes = [a for a in acc if a[2] in ("next", "previous")]
        m["unc"] += unc
        m["rej"] += rej
        if kind == "long":
            m["false_pose"] += len(acc) - len(swipes)
            for s, e, scen, lab in segs:
                mine = [a for a in swipes if s <= a[0] < e]
                if scen != "intentional":
                    m["false_swipe"] += len(mine)
                    m["near_long"] += scen == "near_miss" and bool(mine)
                    continue
                m["commands"] += 1
                good = [a for a in mine if a[2] == lab]
                if good:
                    m["hits"] += 1
                    m["p1" if "nguoi_1" in rest else "p2"] += 1
                    hit_ids.append(f"{rest}@{s}")
                    lat.append(good[0][1] - fws[s].t_ms)
                m["wrong"] += any(a[2] != lab for a in mine)
        elif kind == "short":
            m["short"] += bool(swipes)
        else:
            for a in swipes:
                m[f"{kind}_{a[2]}"] += 1
            if kind == "web":
                m["web_pose"] += len(acc) - len(swipes)
    m["lat_ms"] = float(np.median(lat)) if lat else float("nan")
    m["hit_ids"] = " ".join(hit_ids)
    return m


def grid(base: Config):
    known = {f.name for f in fields(Config)}
    rows = []

    def add(group, value, policies, **kw):
        assert not set(kw) - known, kw
        for p in policies:
            rows.append((group, str(value), replace(base, policy=p, **kw)))
    for hold in (400, 100):
        h, b = f"giữ {hold} | ", dict(hold_ms=hold)
        add(h + "0 gốc", "config", ALL4, **b)
        for w in (800, 1000, 2000, 5000, 10000):
            add(h + "C2 cửa sổ ổn định (xóa lịch sử)", w, ("adaptive",), **b, stability_window_ms=w)
            add(h + "C2 cửa sổ ổn định (không xóa)", w, ("adaptive", "combined"), **b, stability_window_ms=w, stability_reset=False)
            add(h + "C2 không xóa, trọng số 0.4", w, ("adaptive",), **b, stability_window_ms=w, stability_reset=False,
                stability_weight=0.4, adapt_max_conf=0.99)
        for lo, hi in ((0.75, 0.85), (0.7, 0.8), (0.7, 0.95), (0.6, 0.99), (0.5, 0.999)):
            add(h + "C2 dải ngưỡng", f"{lo}-{hi}", ("adaptive",), **b, adapt_min_conf=lo, adapt_max_conf=hi)
        for ov in (0.5, 0.6, 0.7):
            for sc in (0.6, 0.7, 0.8, 0.9):
                add(h + f"gru_override {ov}, ngưỡng vuốt", sc, ALL4, **b, gru_override=ov, swipe_conf=sc,
                    adapt_min_conf=0.5, adapt_max_conf=0.99)
        for sc in (0.85, 0.9, 0.95, 0.98):
            add(h + "ngưỡng vuốt (override 0.8)", sc, ALL4, **b, swipe_conf=sc, adapt_max_conf=0.99)
        for w in (0, 167, 333, 600, 800, 1000, 1500, 2000):
            add(h + "C3 abstain_wait_ms", w, ("abstain",), **b, abstain_wait_ms=w)
        for c in (0.8, 0.85, 0.9, 0.95, 0.98, 0.99):
            add(h + "C3 clear_conf", c, ("abstain",), **b, clear_conf=c)
        for c in (0, 333, 700, 1000, 2000, 3000, 5000):
            add(h + "C3 conflict_window_ms", c, ("abstain",), **b, conflict_window_ms=c)
        for g in (0, 70, 100, 170, 250, 350):
            add(h + "dung sai grace_ms", g, ("fixed", "abstain"), **b, grace_ms=g)
        for c in (0.95, 0.98):
            for w in (600, 1000):
                for cw in (700, 2000):
                    for g in (0, 170):
                        add(h + "C3/C4 tổ hợp", f"clear {c} chờ {w} xung đột {cw} dung sai {g}", ("abstain", "combined"), **b,
                            clear_conf=c, abstain_wait_ms=w, conflict_window_ms=cw, grace_ms=g)
    for hold in (0, 100, 170, 250, 330, 400, 500, 600):
        add("thời gian giữ", hold, ALL4, hold_ms=hold)
        add("demo swipe_hold_ms", hold, ("swipe",), swipe_hold_ms=hold)
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--research", default=str(RESEARCH))
    ap.add_argument("--out", default="param_replay.csv")
    ap.add_argument("--base-only", action="store_true", help="Chỉ chạy các policy với config hiện tại")
    args = ap.parse_args()
    import pandas as pd
    cfg = load_config(args.config)
    runner = Runner(cfg)
    load_all(runner, cfg, Path(args.research))
    print("số luồng:", {k: sum(s.startswith(k) for s in runner.streams) for k in ("long", "short", "s2323", "web")}, flush=True)
    todo = ([("gốc", "config", replace(cfg, policy=p)) for p in (*ALL4, "swipe", "naive")] if args.base_only else grid(cfg))
    rows, seen = [], {}
    for group, value, c in todo:
        key = json.dumps(c.to_dict(), sort_keys=True)
        if key not in seen:
            seen[key] = evaluate(runner, c)
        rows.append({"group": group, "value": value, "policy": c.policy, **seen[key]})
        if len(rows) % 25 == 0:
            print(f"{len(rows)}/{len(todo)}", flush=True)
            pd.DataFrame(rows).to_csv(args.out, index=False)
    d = pd.DataFrame(rows)
    d.to_csv(args.out, index=False)
    if args.base_only:
        print(d.drop(columns=["hit_ids"]).to_string(index=False))


if __name__ == "__main__":
    main()
