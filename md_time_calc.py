#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GROMACS MD runtime estimator (calibrated reference baseline)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

# Reference baseline from a calibrated ~25k-atom protein-ligand GPU run.
# Replace P0/N0/OMP0 after your own short benchmark if needed.
P0 = 263.685
N0 = 24598.0
OMP0 = 8.0

GPU_TABLE = [
    ("RTX 4050 Laptop", 0.70),
    ("RTX 4060 Laptop（参考基准）", 1.00),
    ("RTX 4060 台式", 1.20),
    ("RTX 3060", 0.95),
    ("RTX 3070 / 3070 Ti", 1.55),
    ("RTX 3080", 2.00),
    ("RTX 4070", 1.80),
    ("RTX 4080", 2.50),
    ("RTX 4090", 3.50),
    ("自定义 G…", None),
]


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def estimate(n_atoms, sim_ns, g, ntomp, safety, alpha):
    if min(n_atoms, sim_ns, g, ntomp, safety) <= 0:
        raise ValueError("所有数值输入必须大于 0")
    if alpha is None:
        alpha = 0.7 if n_atoms <= 50_000 else 1.0
    size_factor = (N0 / n_atoms) ** alpha
    c = clamp((ntomp / OMP0) ** 0.25, 0.85, 1.15)
    p = P0 * size_factor * g * c * safety
    hours = sim_ns / p * 24.0
    return {
        "alpha": alpha,
        "C": c,
        "P": p,
        "hours": hours,
        "minutes": hours * 60.0,
        "hour_per_ns": 24.0 / p,
    }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GROMACS MD 运行时间估算")
        self.geometry("600x680")
        self.minsize(560, 640)

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frm,
            text=(
                "参考基准：约 2.5 万原子 · RTX 4060 Laptop 档 · 8 线程 · ~264 ns/day\n"
                "公式：P = 264 × (24600/N)^α × G × C × S ； t小时 = 模拟ns / P × 24"
            ),
            wraplength=560,
            justify=tk.LEFT,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        box = ttk.LabelFrame(frm, text="体系大小", padding=10)
        box.grid(row=1, column=0, columnspan=3, sticky="ew", pady=4)
        box.columnconfigure(1, weight=1)

        self.n_res = self._entry(box, 0, "氨基酸残基数 N_res", "100")
        self.n_lig = self._entry(box, 1, "配体原子数 N_lig", "80")
        self.n_water = self._entry(box, 2, "水分子数（可空）", "")
        self.atoms_per_res = self._entry(box, 3, "无水数时每残基当量", "240")
        self.n_atoms_override = self._entry(box, 4, "直接指定总原子数（优先）", "")
        ttk.Label(
            box,
            text="总原子 ≈ 16×残基 + 配体原子 + 3×水分子；水未知则用「当量×残基」",
            foreground="#555",
            wraplength=540,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        hw = ttk.LabelFrame(frm, text="模拟长度与硬件", padding=10)
        hw.grid(row=2, column=0, columnspan=3, sticky="ew", pady=4)
        hw.columnconfigure(1, weight=1)

        self.sim_ns = self._entry(hw, 0, "模拟长度 (ns)", "10")
        self.ntomp = self._entry(hw, 1, "OpenMP 线程 -ntomp", "8")
        self.safety = self._entry(hw, 2, "安全系数 S（立项建议 0.7）", "0.7")

        ttk.Label(hw, text="GPU").grid(row=3, column=0, sticky="w", pady=3)
        self.gpu = ttk.Combobox(
            hw, values=[n for n, _ in GPU_TABLE], state="readonly", width=40
        )
        self.gpu.current(1)
        self.gpu.grid(row=3, column=1, sticky="ew", pady=3)
        self.gpu.bind("<<ComboboxSelected>>", self._on_gpu)

        self.g_custom = self._entry(hw, 4, "GPU 相对性能 G", "1.0")

        ttk.Label(hw, text="尺寸指数 α").grid(row=5, column=0, sticky="w", pady=3)
        self.alpha_mode = ttk.Combobox(
            hw,
            values=[
                "自动（N≤5万用 0.7，否则 1.0）",
                "0.7（小体系）",
                "1.0（中大体系）",
            ],
            state="readonly",
            width=40,
        )
        self.alpha_mode.current(0)
        self.alpha_mode.grid(row=5, column=1, sticky="ew", pady=3)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)
        ttk.Button(btns, text="估算", command=self.calc).pack(side=tk.LEFT)
        ttk.Button(btns, text="恢复默认示例", command=self.fill_defaults).pack(
            side=tk.LEFT, padx=8
        )

        out = ttk.LabelFrame(frm, text="结果", padding=10)
        out.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=4)
        frm.rowconfigure(4, weight=1)
        out.columnconfigure(0, weight=1)
        out.rowconfigure(0, weight=1)

        self.result = tk.Text(out, height=14, wrap=tk.WORD, font=("Microsoft YaHei UI", 10))
        self.result.grid(row=0, column=0, sticky="nsew")
        self.result.configure(state=tk.DISABLED)

        self._on_gpu()
        self.calc()

    def _entry(self, parent, row, label, default):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        e = ttk.Entry(parent)
        e.insert(0, default)
        e.grid(row=row, column=1, sticky="ew", pady=3, padx=(8, 0))
        return e

    def _on_gpu(self, _event=None):
        name = self.gpu.get()
        g = dict(GPU_TABLE).get(name)
        self.g_custom.configure(state="normal")
        if g is not None:
            self.g_custom.delete(0, tk.END)
            self.g_custom.insert(0, f"{g:.2f}")
            self.g_custom.configure(state="disabled")

    def fill_defaults(self):
        for w, v in [
            (self.n_res, "100"),
            (self.n_lig, "80"),
            (self.n_water, ""),
            (self.atoms_per_res, "240"),
            (self.n_atoms_override, ""),
            (self.sim_ns, "10"),
            (self.ntomp, "8"),
            (self.safety, "0.7"),
        ]:
            w.delete(0, tk.END)
            w.insert(0, v)
        self.gpu.current(1)
        self.alpha_mode.current(0)
        self._on_gpu()
        self.calc()

    def _f(self, entry, name, allow_empty=False):
        s = entry.get().strip()
        if not s:
            if allow_empty:
                return None
            raise ValueError(name + " 不能为空")
        try:
            return float(s)
        except ValueError as e:
            raise ValueError(name + " 不是有效数字: " + s) from e

    def _atoms(self):
        override = self._f(self.n_atoms_override, "总原子数", allow_empty=True)
        if override is not None:
            return override, "直接指定"
        n_res = self._f(self.n_res, "残基数")
        n_lig = self._f(self.n_lig, "配体原子数")
        n_water = self._f(self.n_water, "水分子数", allow_empty=True)
        apr = self._f(self.atoms_per_res, "每残基当量")
        if n_water is not None:
            n = 16.0 * n_res + n_lig + 3.0 * n_water
            note = "16x%g + %g + 3x%g = %.0f" % (n_res, n_lig, n_water, n)
        else:
            n = apr * n_res
            note = "%gx%g = %.0f (含水经验当量)" % (apr, n_res, n)
        return n, note

    def _alpha(self):
        mode = self.alpha_mode.current()
        if mode == 0:
            return None
        if mode == 1:
            return 0.7
        return 1.0

    def calc(self):
        try:
            n_atoms, atom_note = self._atoms()
            sim_ns = self._f(self.sim_ns, "模拟长度")
            ntomp = self._f(self.ntomp, "线程数")
            safety = self._f(self.safety, "安全系数")
            state = str(self.g_custom.cget("state"))
            self.g_custom.configure(state="normal")
            g = self._f(self.g_custom, "G")
            if state == "disabled":
                self.g_custom.configure(state="disabled")
            r = estimate(n_atoms, sim_ns, g, ntomp, safety, self._alpha())
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
            return

        total_min = r["minutes"]
        h = int(total_min // 60)
        m = total_min - h * 60
        lines = [
            "总原子数 N     = %.0f   (%s)" % (n_atoms, atom_note),
            "尺寸指数 a     = %.2f" % r["alpha"],
            "GPU 相对 G     = %.2f   ·  线程修正 C = %.3f" % (g, r["C"]),
            "安全系数 S     = %g" % safety,
            "",
            "预计速度       = %.1f ns/day" % r["P"],
            "每 ns 墙钟     = %.3f hour/ns" % r["hour_per_ns"],
            "",
            "模拟 %g ns 预计墙钟：" % sim_ns,
            "  -> %.2f 小时   (约 %.0f 分钟)" % (r["hours"], total_min),
            "  -> %d 小时 %.0f 分钟" % (h, m),
            "",
            "说明：S=1 对齐参考基准短跑；立项计划建议 S=0.7。",
            "校准：短跑 mdrun -nsteps 20000，用 log 的 ns/day 更新脚本内 P0/N0。",
        ]
        self.result.configure(state=tk.NORMAL)
        self.result.delete("1.0", tk.END)
        self.result.insert(tk.END, "\n".join(lines))
        self.result.configure(state=tk.DISABLED)


if __name__ == "__main__":
    App().mainloop()
