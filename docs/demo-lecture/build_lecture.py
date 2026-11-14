"""Build the LectureLoop demo lecture: "Regression, risk & loss".

Written by the LectureLoop team. Every sentence, example, dataset, figure and question here is
our own; the topics follow a standard intro-ML sequence. Output: one PDF plus one 1200x800 JPG
per page (the frontend's mock-pages).

    python build_lecture.py out/            # all pages
    python build_lecture.py out/ 1 6 12     # only some pages (previews)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ---------- look ----------
NAVY = "#14213D"
TEAL = "#1F8A8A"
CORAL = "#E4572E"
SAND = "#F4F1EA"
GREY = "#6B7280"
LIGHT = "#E5E7EB"
W, H = 12, 8  # inches at 100 dpi -> 1200 x 800
TOTAL = 36
TITLE = "Regression, risk & loss"

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "mathtext.fontset": "dejavusans",
    "axes.edgecolor": GREY,
    "axes.labelcolor": NAVY,
    "xtick.color": GREY,
    "ytick.color": GREY,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ---------- the running example: harbour ferry crossings ----------
rng = np.random.default_rng(3151)
N = 40
wind = np.sort(rng.uniform(0, 35, N))                 # knots
minutes = 22 + 0.45 * wind + rng.normal(0, 2.5, N)    # crossing time
TRUE_W1, TRUE_W0 = 0.45, 22.0


def fit_line(x, t):
    X = np.c_[x, np.ones_like(x)]
    w1, w0 = np.linalg.lstsq(X, t, rcond=None)[0]
    return w1, w0


def cost(w1, w0, x=wind, t=minutes):
    return np.mean((w1 * x + w0 - t) ** 2) / 2


# ---------- slide frame ----------
def frame(n, title, kicker=None):
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor("white")
    fig.add_artist(plt.Rectangle((0, 0), 0.012, 1, transform=fig.transFigure, color=NAVY))
    if kicker:
        fig.text(0.05, 0.915, kicker.upper(), fontsize=11, color=TEAL, weight="bold")
    fig.text(0.05, 0.855, title, fontsize=30, color=NAVY, weight="bold", va="center")
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.085, 0.085], transform=fig.transFigure, color=LIGHT, lw=1))
    fig.text(0.05, 0.05, f"LectureLoop demo lecture  ·  {TITLE}", fontsize=10, color=GREY)
    fig.text(0.95, 0.05, f"{n} / {TOTAL}", fontsize=10, color=GREY, ha="right")
    return fig


def bullets(fig, items, x=0.07, y=0.72, size=19, gap=0.075, width=None):
    import textwrap
    for item in items:
        sub = item.startswith("  ")
        text = item.strip()
        lines = 1
        if width and "$" not in text:
            text = textwrap.fill(text, width)
            lines = text.count("\n") + 1
        fig.text(x + (0.03 if sub else 0), y, "–" if sub else "•", fontsize=size - (3 if sub else 0),
                 color=TEAL if not sub else GREY, va="top")
        fig.text(x + (0.055 if sub else 0.025), y, text, fontsize=size - (3 if sub else 0), color=NAVY, va="top",
                 linespacing=1.35)
        y -= gap * (0.85 if sub else 1) + (lines - 1) * size * 0.0024
    return y


def card(fig, x, y, w, h, color=SAND):
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.015",
                                  transform=fig.transFigure, facecolor=color, edgecolor="none"))


# ---------- pages ----------
def p1():
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor(NAVY)
    ax = fig.add_axes([0.52, 0.12, 0.42, 0.62])
    ax.set_facecolor(NAVY)
    w1, w0 = fit_line(wind, minutes)
    ax.scatter(wind, minutes, s=46, color="#9FD8D8", edgecolor="none", alpha=0.95)
    xs = np.linspace(0, 35, 2)
    ax.plot(xs, w1 * xs + w0, color=CORAL, lw=3)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    fig.text(0.07, 0.80, "LECTURELOOP DEMO LECTURE", fontsize=13, color="#9FD8D8", weight="bold")
    fig.text(0.07, 0.62, "Regression,\nrisk & loss", fontsize=54, color="white", weight="bold", va="center",
             linespacing=1.05)
    fig.text(0.07, 0.40, "How a model learns from data: losses, risk,\ngradient descent, and when "
             "a straight line\nis the wrong tool.", fontsize=17, color="#D1D5DB", va="top", linespacing=1.5)
    fig.text(0.07, 0.14, "Running example: how long will the harbour ferry take today?", fontsize=13,
             color="#9FD8D8")
    fig.text(0.07, 0.08, "Written by the LectureLoop team · CC BY 4.0", fontsize=11, color="#9CA3AF")
    return fig


def p6():
    fig = frame(6, "Empirical risk: the part we can compute", "Risk")
    card(fig, 0.06, 0.47, 0.41, 0.27)
    fig.text(0.08, 0.70, "What we want", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.08, 0.59, r"$R(f)=\mathbb{E}_{(x,t)\sim\mathcal{D}}\,[\,\ell(f(x),t)\,]$", fontsize=22,
             color=NAVY)
    fig.text(0.08, 0.51, "Average loss over every crossing that\ncould ever happen. D is unknown.",
             fontsize=13, color=GREY, va="center")
    card(fig, 0.53, 0.47, 0.41, 0.27)
    fig.text(0.55, 0.70, "What we can compute", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.55, 0.59, r"$\hat{R}_n(f)=\dfrac{1}{n}\sum_{i=1}^{n}\ell(f(x^{(i)}),t^{(i)})$", fontsize=22,
             color=NAVY)
    fig.text(0.55, 0.51, "Average loss over the n crossings we\nactually logged.", fontsize=13, color=GREY,
             va="center")
    fig.text(0.07, 0.37, "Empirical risk minimisation (ERM)", fontsize=17, color=TEAL, weight="bold")
    fig.text(0.07, 0.27, r"$\hat{f}=\arg\min_{f\in\mathcal{F}}\ \hat{R}_n(f)$", fontsize=24, color=NAVY, va="center")
    fig.text(0.33, 0.27, "Pick the model in our class that fits the logged\ncrossings best, and hope it holds up tomorrow.",
             fontsize=16, color=NAVY, va="center", linespacing=1.4)
    fig.text(0.07, 0.15, "Other names you will meet for the same quantity: training loss, cost function, "
             "objective.", fontsize=14, color=GREY)
    return fig


def p12():
    fig = frame(12, r"The cost surface over $(w_1, w_0)$", "Weight space")
    w1s = np.linspace(-0.2, 1.1, 220)
    w0s = np.linspace(8, 36, 220)
    A, B = np.meshgrid(w1s, w0s)
    J = np.mean((A[..., None] * wind + B[..., None] - minutes) ** 2, axis=-1) / 2
    ax = fig.add_axes([0.08, 0.17, 0.5, 0.6])
    cs = ax.contourf(A, B, J, levels=np.geomspace(J.min(), J.max(), 18), cmap="GnBu_r")
    ax.contour(A, B, J, levels=np.geomspace(J.min(), J.max(), 18), colors="white", linewidths=0.4)
    w1, w0 = fit_line(wind, minutes)
    ax.plot(w1, w0, marker="*", ms=18, color=CORAL, mec="white")
    ax.annotate(f"minimum: $w_1$ ≈ {w1:.2f}, $w_0$ ≈ {w0:.1f}", (w1, w0), xytext=(w1 + 0.08, w0 + 7), fontsize=12,
                color=NAVY, arrowprops=dict(arrowstyle="-", color="white"),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"))
    ax.set_xlabel(r"$w_1$  (extra minutes per knot of wind)", fontsize=12)
    ax.set_ylabel(r"$w_0$  (minutes in calm water)", fontsize=12)
    fig.text(0.63, 0.72, "Each point is one possible line.", fontsize=17, color=NAVY, weight="bold")
    bullets(fig, [
        "Colour shows the cost J of that line",
        "Contours are ellipses around a single lowest point",
        "Training means finding the star",
        "The long diagonal valley: a steeper line with a lower start fits almost as well",
    ], x=0.63, y=0.64, size=15, gap=0.075, width=34)
    return fig


def p17():
    fig = frame(17, "Gradient descent, drawn", "Optimisation")
    w1s = np.linspace(-0.2, 1.1, 220)
    w0s = np.linspace(8, 36, 220)
    A, B = np.meshgrid(w1s, w0s)
    J = np.mean((A[..., None] * wind + B[..., None] - minutes) ** 2, axis=-1) / 2
    # plain gradient descent on the raw input: the narrow valley makes it zigzag
    a, b, lr, path = 1.0, 30.0, 0.0016, []
    for _ in range(6000):
        path.append((a, b))
        err = a * wind + b - minutes
        a, b = a - lr * np.mean(err * wind), b - lr * np.mean(err)
    path = np.array(path)
    keep = np.unique(np.r_[np.arange(12), np.geomspace(12, len(path) - 1, 40).astype(int)])
    path = path[keep]
    ax = fig.add_axes([0.08, 0.17, 0.5, 0.6])
    ax.contour(A, B, J, levels=np.geomspace(J.min(), J.max(), 18), cmap="GnBu_r", linewidths=1.2)
    ax.plot(path[:, 0], path[:, 1], "-o", color=CORAL, ms=4, lw=1.6)
    ax.plot(*path[0], "o", ms=10, color=NAVY)
    ax.annotate("start: a poor guess", path[0], xytext=(path[0][0] - 0.02, path[0][1] + 1.2), ha="right", fontsize=12,
                color=NAVY)
    ax.plot(*fit_line(wind, minutes), marker="*", ms=18, color=CORAL, mec="white")
    ax.set_xlim(w1s[0], w1s[-1]); ax.set_ylim(w0s[0], w0s[-1])
    ax.set_xlabel(r"$w_1$", fontsize=13); ax.set_ylabel(r"$w_0$", fontsize=13)
    fig.text(0.63, 0.72, "Walk downhill, one step at a time.", fontsize=17, color=NAVY, weight="bold")
    bullets(fig, [
        r"Each step moves against $\nabla J$",
        "First steps drop fast down the steep walls",
        "Then the path creeps along the narrow valley: rescaling the input would help",
        "The bowl is convex, so every downhill walk ends at the same minimum",
    ], x=0.63, y=0.64, size=15, gap=0.075, width=34)
    return fig


# ---------- more helpers ----------
import textwrap

MONO = "DejaVu Sans Mono"


def wrap(s, n):
    return "\n".join(textwrap.fill(par, n) for par in s.split("\n"))


def code(fig, src, x, y, w, h, size=12.5, label="Python"):
    card(fig, x, y, w, h, color="#EEF2F6")
    fig.text(x + 0.015, y + h - 0.035, label.upper(), fontsize=9, color=TEAL, weight="bold")
    fig.text(x + 0.015, y + h - 0.065, src, fontsize=size, family=MONO, color=NAVY, va="top", linespacing=1.45)


def output(fig, txt, x, y, w, h, size=12):
    code(fig, txt, x, y, w, h, size=size, label="Output")


def axes(fig, rect):
    ax = fig.add_axes(rect)
    ax.tick_params(labelsize=10)
    return ax


def boxes(fig, items, cols, x0=0.06, y0=0.73, w=0.205, h=0.25, gx=0.022, gy=0.04, size=13, width=26,
          numbered=False):
    for i, (head, body) in enumerate(items):
        r, c = divmod(i, cols)
        x, y = x0 + c * (w + gx), y0 - r * (h + gy) - h
        card(fig, x, y, w, h)
        label = f"{i + 1}  {head}" if numbered else head
        fig.text(x + 0.015, y + h - 0.045, label, fontsize=size + 2, color=TEAL, weight="bold")
        fig.text(x + 0.015, y + h - 0.095, wrap(body, width), fontsize=size, color=NAVY, va="top",
                 linespacing=1.4)


def lead(fig, text, y=0.75, size=18, width=95):
    fig.text(0.07, y, wrap(text, width), fontsize=size, color=NAVY, va="top", linespacing=1.45)


def note(fig, text, y=0.14, width=120):
    fig.text(0.07, y, wrap(text, width), fontsize=13, color=GREY, va="top", linespacing=1.4)


W1, W0 = fit_line(wind, minutes)

# a second, richer ferry log for the multivariate pages
rng2 = np.random.default_rng(42)
M = 200
wind_m = rng2.uniform(0, 35, M)
waves = np.clip(0.06 * wind_m + rng2.normal(0, 0.4, M), 0, None)
passengers = rng2.integers(20, 400, M)
X3 = np.c_[wind_m, waves, passengers]
TRUE_W3, TRUE_B3 = np.array([0.4, 3.0, 0.02]), 20.0
t3 = X3 @ TRUE_W3 + TRUE_B3 + rng2.normal(0, 1.5, M)
Xb = np.c_[X3, np.ones(M)]
W3 = np.linalg.solve(Xb.T @ Xb, Xb.T @ t3)

# tide height over one tidal cycle, for polynomial features
rng3 = np.random.default_rng(7)
PERIOD = 12.4


def tide(h):
    return 1.6 * np.cos(2 * np.pi * h / PERIOD)


h_tr = np.sort(rng3.uniform(0, PERIOD, 11))
y_tr = tide(h_tr) + rng3.normal(0, 0.45, 11)
h_va = np.sort(rng3.uniform(0, PERIOD, 40))
y_va = tide(h_va) + rng3.normal(0, 0.45, 40)


def poly_fit(deg):
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.pipeline import make_pipeline
    m = make_pipeline(PolynomialFeatures(deg, include_bias=False), LinearRegression())
    m.fit(h_tr[:, None] / PERIOD, y_tr)
    return m


def mse(m, h, y):
    return float(np.mean((m.predict(h[:, None] / PERIOD) - y) ** 2))


DEGS = list(range(0, 10))
POLY = {d: poly_fit(d) if d > 0 else None for d in DEGS}


def predict_deg(d, h):
    return np.full_like(h, y_tr.mean()) if d == 0 else POLY[d].predict(h[:, None] / PERIOD)


TRAIN_MSE = {d: float(np.mean((predict_deg(d, h_tr) - y_tr) ** 2)) for d in DEGS}
VAL_MSE = {d: float(np.mean((predict_deg(d, h_va) - y_va) ** 2)) for d in DEGS}

# late crossings (1 = more than 10 minutes late)
rng4 = np.random.default_rng(11)
K = 160
wind_c = rng4.uniform(0, 40, K)
waves_c = np.clip(0.06 * wind_c + rng4.normal(0, 0.4, K), 0, None)
p_late = 1 / (1 + np.exp(-(-7 + 0.22 * wind_c + 1.0 * waves_c)))
late = (rng4.uniform(size=K) < p_late).astype(int)
Xc = np.c_[wind_c, waves_c, np.ones(K)]
Wc = np.linalg.lstsq(Xc, late, rcond=None)[0]
pred_c = Xc @ Wc
ACC_C = float(np.mean((pred_c >= 0.5) == late))


# ---------- pages 2-36 ----------
def p2():
    fig = frame(2, "What you will be able to do", "Goals")
    bullets(fig, [
        "Describe the steps that take a question to a trained, tested model",
        "Write empirical risk for squared loss and explain why we minimise it",
        "Fit linear and polynomial regression with NumPy and scikit-learn",
        "Read a cost surface and follow a gradient descent path across it",
        "Solve multivariate regression in closed form with the normal equation",
        "Explain why fitting a line to 0/1 labels makes a poor classifier",
        "Spot under- and overfitting by comparing training and validation error",
    ], y=0.72, size=18, gap=0.08, width=80)
    return fig


def p3():
    fig = frame(3, "From a question to a model in service", "The supervised pipeline")
    boxes(fig, [
        ("Frame", "Which decision will the model support, and what does a wrong answer cost?"),
        ("Collect", "Gather inputs and labels. How were they measured, and by whom?"),
        ("Split", "Set aside validation and test data before looking closely."),
        ("Pick a family", "Line, tree, network? Trade capacity against clarity."),
        ("Loss & metric", "A loss to train with, a metric that reflects the decision."),
        ("Train", "Minimise the average loss on the training split."),
        ("Evaluate", "Score on held-out data; hunt for leakage and shift."),
        ("Ship & watch", "Set thresholds, add guardrails, monitor drift."),
    ], cols=4, y0=0.75, h=0.27, gy=0.045, size=12.5, width=24, numbered=True)
    return fig


def p4():
    fig = frame(4, "Four ingredients: data, model, loss, metric", "Vocabulary")
    boxes(fig, [
        ("Data", "Pairs (x, t): a crossing's conditions x and its measured duration t. "
                 "Stack inputs in X, targets in t."),
        ("Model", "A function f(x; w) with adjustable weights w. For a line: $f(x)=w_1x+w_0$."),
        ("Loss", "ℓ(y, t): the penalty for predicting y when the truth is t. Training minimises it."),
        ("Metric", "A summary for people deciding if the model is good enough: MAE in minutes, "
                   "share of crossings within 5 min."),
    ], cols=4, y0=0.73, h=0.38, size=14.5, width=21)
    lead(fig, "Loss and metric can differ. A metric only needs to be meaningful; a loss also needs to be "
              "easy to optimise.", y=0.25, size=16)
    return fig


def p5():
    fig = frame(5, "Expected risk: what we really care about", "Risk")
    lead(fig, "Picture the harbour as a machine that keeps producing crossings (x, t) from some fixed but "
              "unknown distribution D.", y=0.74)
    bullets(fig, [
        "We commit to a model f before the next crossing happens",
        "Each time it is wrong we pay a loss ℓ(f(x), t)",
        "What matters is the long-run average on crossings we have not seen yet:",
    ], y=0.6, size=17, gap=0.07, width=80)
    fig.text(0.12, 0.31, r"$R(f)=\mathbb{E}_{(x,t)\sim\mathcal{D}}\,[\,\ell(f(x),t)\,]$", fontsize=28, color=NAVY)
    note(fig, "The catch: D is never observed directly. All we have is a finite log of past crossings, so "
              "R(f) has to be estimated. That estimate is the next slide.", y=0.2)
    return fig


def p7():
    fig = frame(7, "Risk in numbers: four logged crossings", "Worked example")
    t = [27, 31, 35, 29]
    y = 30
    rows = [("Crossing", "True t (min)", "Prediction", "Squared loss")]
    for i, ti in enumerate(t, 1):
        rows.append((str(i), str(ti), str(y), str((y - ti) ** 2)))
    xs = [0.08, 0.22, 0.38, 0.53]
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            fig.text(xs[c], 0.70 - r * 0.07, cell, fontsize=16, color=TEAL if r == 0 else NAVY,
                     weight="bold" if r == 0 else "normal")
    fig.add_artist(plt.Line2D([0.08, 0.66], [0.675, 0.675], transform=fig.transFigure, color=LIGHT))
    mse_v = np.mean([(y - ti) ** 2 for ti in t])
    fig.text(0.08, 0.29, rf"Empirical risk = $(9+1+25+1)\,/\,4$ = {mse_v:g} min²", fontsize=18, color=NAVY)
    card(fig, 0.70, 0.22, 0.25, 0.52)
    fig.text(0.715, 0.69, "Read it as", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.715, 0.64, wrap("A model that always says 30 minutes is off by about 3 minutes on a typical "
                                "logged crossing (√9).\n\nIf tomorrow's crossings look like these, its "
                                "expected risk should be close to 9 as well. It is still only an estimate.",
                                28), fontsize=13, color=NAVY, va="top", linespacing=1.4)
    return fig


def p8():
    fig = frame(8, "Two losses for regression: L2 and L1", "Loss functions")
    ax = axes(fig, [0.08, 0.2, 0.36, 0.48])
    r = np.linspace(-6, 6, 200)
    ax.plot(r, r ** 2, color=CORAL, lw=2.5, label="squared r²")
    ax.plot(r, np.abs(r), color=TEAL, lw=2.5, label="absolute |r|")
    ax.set_xlabel("residual r = y − t (minutes)", fontsize=11)
    ax.legend(frameon=False, fontsize=11)
    card(fig, 0.5, 0.2, 0.45, 0.48)
    fig.text(0.52, 0.64, "Two forecasts for a 30-minute crossing", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.52, 0.58, "A says 32 min (off by 2)    B says 38 min (off by 8)", fontsize=14, color=NAVY)
    fig.text(0.52, 0.50, "Squared:  A pays 4,  B pays 64   → B is 16× worse", fontsize=14, color=NAVY)
    fig.text(0.52, 0.44, "Absolute: A pays 2,  B pays 8     → B is 4× worse", fontsize=14, color=NAVY)
    fig.text(0.52, 0.36, wrap("Squared loss (its average is MSE) punishes big misses much harder, so a few "
                               "storm-day outliers can drag the fit. Absolute loss (MAE) is more forgiving.",
                               52), fontsize=13, color=GREY, va="top", linespacing=1.4)
    return fig


def p9():
    fig = frame(9, "One input, one line", "1D linear regression")
    ax = axes(fig, [0.08, 0.17, 0.46, 0.58])
    ax.scatter(wind, minutes, s=28, color=TEAL)
    xs = np.linspace(0, 35, 2)
    ax.plot(xs, W1 * xs + W0, color=CORAL, lw=2.5)
    for i in [5, 18, 33]:
        ax.plot([wind[i]] * 2, [minutes[i], W1 * wind[i] + W0], color=NAVY, lw=1.5)
    ax.set_xlabel("wind speed x (knots)", fontsize=11)
    ax.set_ylabel("crossing time t (min)", fontsize=11)
    fig.text(0.6, 0.72, "Model", fontsize=16, color=TEAL, weight="bold")
    fig.text(0.6, 0.65, r"$y = w_1 x + w_0$", fontsize=22, color=NAVY)
    fig.text(0.6, 0.58, wrap("$w_1$: slope, minutes added per knot\n$w_0$: intercept, time in calm water", 40),
             fontsize=13, color=GREY, va="top", linespacing=1.4)
    fig.text(0.6, 0.44, "Residual of example i", fontsize=16, color=TEAL, weight="bold")
    fig.text(0.6, 0.37, r"$r^{(i)} = y^{(i)} - t^{(i)}$", fontsize=22, color=NAVY)
    fig.text(0.6, 0.30, wrap("The dark vertical segments. A good line keeps them short overall.", 40),
             fontsize=13, color=GREY, va="top", linespacing=1.4)
    return fig


def p10():
    fig = frame(10, r"From squared loss to the cost $J(w_1, w_0)$", "1D linear regression")
    fig.text(0.07, 0.70, "One crossing:", fontsize=17, color=TEAL, weight="bold")
    fig.text(0.30, 0.70, r"$\ell(y,t)=\frac{1}{2}(y-t)^2$", fontsize=24, color=NAVY, va="center")
    fig.text(0.07, 0.53, "The whole log:", fontsize=17, color=TEAL, weight="bold")
    fig.text(0.30, 0.53, r"$J(w_1,w_0)=\dfrac{1}{2n}\sum_{i=1}^{n}\left(w_1x^{(i)}+w_0-t^{(i)}\right)^2$",
             fontsize=24, color=NAVY, va="center")
    lead(fig, "J is just the empirical risk of the line, written as a function of its two weights. "
              "Training means finding the pair ($w_1$, $w_0$) that makes J smallest.", y=0.38, size=17)
    note(fig, "The ½ is a convenience: it cancels the 2 that appears when we differentiate.", y=0.2)
    return fig


def p11():
    fig = frame(11, "Two pictures of the same problem", "Data space vs weight space")
    cands = [(0.15, 30, "#9CA3AF"), (0.8, 14, "#F2A541"), (W1, W0, CORAL)]
    ax = axes(fig, [0.07, 0.2, 0.4, 0.5])
    ax.scatter(wind, minutes, s=18, color=TEAL)
    xs = np.linspace(0, 35, 2)
    for a, b, c in cands:
        ax.plot(xs, a * xs + b, color=c, lw=2.2)
    ax.set_title("Data space: lines through points", fontsize=12, color=NAVY)
    ax.set_xlabel("wind (knots)", fontsize=10); ax.set_ylabel("minutes", fontsize=10)
    w1s = np.linspace(-0.2, 1.1, 160); w0s = np.linspace(8, 36, 160)
    A, B = np.meshgrid(w1s, w0s)
    J = np.mean((A[..., None] * wind + B[..., None] - minutes) ** 2, axis=-1) / 2
    ax2 = axes(fig, [0.56, 0.2, 0.38, 0.5])
    ax2.contour(A, B, J, levels=np.geomspace(J.min(), J.max(), 14), cmap="GnBu_r", linewidths=1)
    for a, b, c in cands:
        ax2.plot(a, b, "o", ms=11, color=c, mec="white")
    ax2.set_title("Weight space: each line is one point", fontsize=12, color=NAVY)
    ax2.set_xlabel(r"$w_1$", fontsize=11); ax2.set_ylabel(r"$w_0$", fontsize=11)
    note(fig, "Same colour, same line. The best line on the left sits at the bottom of the bowl on the right.",
         y=0.13)
    return fig


def p13():
    fig = frame(13, "The ferry log in Python", "Example")
    src = ("import numpy as np\nimport pandas as pd\n\nrng = np.random.default_rng(3151)\n"
           "wind = rng.uniform(0, 35, 40)          # knots\n"
           "minutes = 22 + 0.45 * wind + rng.normal(0, 2.5, 40)\n\n"
           "log = pd.DataFrame({'wind_kn': wind,\n                    'minutes': minutes})\n"
           "log.head()")
    code(fig, src, 0.06, 0.2, 0.52, 0.55)
    rows = "     wind_kn   minutes\n" + "\n".join(
        f"{i}  {wind[j]:8.2f}  {minutes[j]:8.2f}" for i, j in enumerate([3, 17, 9, 30, 24]))
    output(fig, rows, 0.61, 0.43, 0.33, 0.32, size=13)
    fig.text(0.61, 0.36, wrap("Synthetic data with a known answer: about 22 minutes in calm water plus "
                               "0.45 minutes per knot, plus noise.", 34), fontsize=13, color=GREY, va="top",
             linespacing=1.4)
    return fig


def p14():
    fig = frame(14, "Fitting the line in Python", "Example")
    src = ("from sklearn.linear_model import LinearRegression\n\n"
           "model = LinearRegression()\n"
           "model.fit(log[['wind_kn']], log['minutes'])\n\n"
           "model.coef_[0], model.intercept_")
    code(fig, src, 0.06, 0.45, 0.46, 0.3, size=12)
    output(fig, f"({W1:.3f}, {W0:.2f})", 0.06, 0.27, 0.46, 0.13, size=13)
    fig.text(0.06, 0.2, wrap(f"About {W0:.1f} min in calm water and {W1 * 60:.0f} extra seconds per knot: "
                              "close to the values used to make the data.", 60), fontsize=13, color=GREY,
             va="top", linespacing=1.4)
    ax = axes(fig, [0.58, 0.2, 0.37, 0.55])
    ax.scatter(wind, minutes, s=22, color=TEAL)
    xs = np.linspace(0, 35, 2)
    ax.plot(xs, W1 * xs + W0, color=CORAL, lw=2.5, label="fitted line")
    ax.legend(frameon=False, fontsize=10)
    ax.set_xlabel("wind (knots)", fontsize=10); ax.set_ylabel("minutes", fontsize=10)
    return fig


def p15():
    fig = frame(15, "Slicing the bowl", "Weight space")
    ax = axes(fig, [0.08, 0.2, 0.42, 0.52])
    w1s = np.linspace(-0.3, 1.25, 200)
    ax.plot(w1s, [cost(a, W0) for a in w1s], color=CORAL, lw=2.5)
    ax.axvline(W1, color=GREY, ls=":", lw=1)
    ax.set_xlabel(rf"$w_1$  (with $w_0$ fixed at {W0:.1f})", fontsize=11)
    ax.set_ylabel(r"$J$", fontsize=12)
    src = ("w1_grid = np.linspace(-0.3, 1.25, 200)\n"
           "J = [np.mean((a*wind + w0 - minutes)**2) / 2\n     for a in w1_grid]")
    code(fig, src, 0.55, 0.52, 0.4, 0.2, size=11.5)
    fig.text(0.55, 0.44, wrap("Fix one weight and vary the other: every slice through J is a parabola "
                               "with a single lowest point.", 40), fontsize=15, color=NAVY, va="top",
             linespacing=1.4)
    fig.text(0.55, 0.28, wrap("Stack all the slices together and you get the bowl from slide 12.", 44),
             fontsize=13, color=GREY, va="top", linespacing=1.4)
    return fig


def p16():
    fig = frame(16, "Why one bowl? Quadratic and convex", "Weight space")
    boxes(fig, [
        ("Quadratic", "Each residual $w_1x^{(i)}+w_0-t^{(i)}$ is linear in the weights. Squaring it gives terms "
                      "no higher than $w_1^2$, $w_1w_0$, $w_0^2$. Averaging keeps the degree at 2."),
        ("Convex", "z ↦ z² is convex. Plugging in a linear function of the weights keeps it convex, and an "
                   "average of convex functions is convex too."),
    ], cols=2, y0=0.74, w=0.43, h=0.34, gx=0.03, size=15, width=46)
    lead(fig, "Consequence: there is no false bottom. Any point where the slope is zero is the global "
              "minimum, which is why gradient descent is dependable here.", y=0.3, size=17)
    return fig


def p18():
    fig = frame(18, "Step size matters", "Optimisation")
    cfg = [(0.0004, "too small: barely moves"), (0.0016, "about right"), (0.00305, "too large: zigzags")]
    for k, (lr, lab) in enumerate(cfg):
        ax = axes(fig, [0.07 + k * 0.31, 0.24, 0.26, 0.42])
        w1s = np.linspace(-0.3, 1.25, 200)
        ax.plot(w1s, [cost(a, W0) for a in w1s], color=LIGHT, lw=2.5)
        a, pts = 1.2, []
        for _ in range(8):
            pts.append(a)
            g = np.mean((a * wind + W0 - minutes) * wind)
            a -= lr * g
        ax.plot(pts, [cost(p, W0) for p in pts], "-o", color=CORAL, ms=5, lw=1.4)
        ax.set_title(f"α = {lr}: {lab}", fontsize=11, color=NAVY)
        ax.set_xlabel(r"$w_1$", fontsize=10)
        ax.set_yticks([])
    note(fig, "Eight steps each, same start, same slice of J as slide 15. The learning rate α is the "
              "only difference.", y=0.15)
    return fig


def p19():
    fig = frame(19, "The update rule", "Optimisation")
    fig.text(0.07, 0.71, "Gradients", fontsize=16, color=TEAL, weight="bold")
    fig.text(0.07, 0.62, r"$\dfrac{\partial J}{\partial w_1}=\dfrac{1}{n}\sum_i r^{(i)}x^{(i)}$"
                         r"$\qquad\dfrac{\partial J}{\partial w_0}=\dfrac{1}{n}\sum_i r^{(i)}$",
             fontsize=20, color=NAVY, va="center")
    fig.text(0.07, 0.49, "Update, repeated", fontsize=16, color=TEAL, weight="bold")
    fig.text(0.07, 0.42, r"$w_1 \leftarrow w_1-\alpha\,\partial J/\partial w_1"
                         r"\qquad w_0 \leftarrow w_0-\alpha\,\partial J/\partial w_0$",
             fontsize=20, color=NAVY, va="center")
    a, b, lr, rows = 1.0, 30.0, 0.0016, []
    for k in range(5):
        rows.append(f"{k}   {a:6.3f}  {b:6.2f}  {cost(a, b):8.2f}")
        err = a * wind + b - minutes
        a, b = a - lr * np.mean(err * wind), b - lr * np.mean(err)
    output(fig, "step   w1      w0        J\n" + "\n".join(rows), 0.6, 0.3, 0.34, 0.4, size=13)
    note(fig, "Starting from the poor guess on slide 17 ($w_1$ = 1, $w_0$ = 30) with α = 0.0016.", y=0.22)
    return fig


def p20():
    fig = frame(20, "Many inputs: matrix form and the bias trick", "Multivariate regression")
    lead(fig, "Now each crossing has d inputs: wind (kn), wave height (m), passengers on board.", y=0.75,
         size=17)
    bullets(fig, [
        "Stack the n crossings as rows of X (n × d), targets in t",
        "Weights w (d numbers) plus a bias b",
        "Bias trick: add a column of ones to X and fold b into w",
    ], y=0.64, size=16, gap=0.07, width=48)
    fig.text(0.6, 0.62, r"$\mathbf{y} = X\mathbf{w}$", fontsize=26, color=NAVY)
    fig.text(0.6, 0.48, r"$J(\mathbf{w})=\dfrac{1}{2n}\,\|X\mathbf{w}-\mathbf{t}\|^2$", fontsize=24,
             color=NAVY)
    note(fig, "Still a convex quadratic in w, just in d + 1 dimensions instead of 2. Everything from the "
              "1D case carries over.", y=0.28)
    return fig


def p21():
    fig = frame(21, "The normal equation", "Closed form")
    fig.text(0.07, 0.71, "Set the gradient to zero", fontsize=16, color=TEAL, weight="bold")
    fig.text(0.07, 0.62, r"$\nabla J=\dfrac{1}{n}X^\top(X\mathbf{w}-\mathbf{t})=\mathbf{0}$", fontsize=22,
             color=NAVY, va="center")
    fig.text(0.07, 0.49, r"$\Rightarrow\quad X^\top X\,\mathbf{w}=X^\top\mathbf{t}$", fontsize=22,
             color=NAVY, va="center")
    fig.text(0.07, 0.36, r"$\Rightarrow\quad \mathbf{w}^*=(X^\top X)^{-1}X^\top\mathbf{t}$", fontsize=24,
             color=CORAL, va="center")
    card(fig, 0.58, 0.26, 0.37, 0.48)
    fig.text(0.6, 0.69, "When to use it", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.6, 0.64, wrap("Needs XᵀX to be invertible (no perfectly redundant columns).\n\nOne solve, "
                              "no learning rate, no iterations: great for a few hundred features.\n\n"
                              "With very many features the solve gets expensive; gradient methods scale "
                              "better.", 36), fontsize=13, color=NAVY, va="top", linespacing=1.4)
    return fig


def p22():
    fig = frame(22, "Closed form vs scikit-learn", "Example")
    src = ("Xb = np.c_[X, np.ones(len(X))]        # bias trick\n"
           "w = np.linalg.solve(Xb.T @ Xb, Xb.T @ t)\n\n"
           "sk = LinearRegression().fit(X, t)\n"
           "print(w)\nprint(sk.coef_, sk.intercept_)")
    code(fig, src, 0.06, 0.45, 0.55, 0.3, size=12)
    from sklearn.linear_model import LinearRegression
    sk = LinearRegression().fit(X3, t3)
    out = (f"true:        [0.4   3.0   0.02 ]  20.0\n"
           f"closed form: [{W3[0]:.3f} {W3[1]:.3f} {W3[2]:.4f}] {W3[3]:.2f}\n"
           f"sklearn:     [{sk.coef_[0]:.3f} {sk.coef_[1]:.3f} {sk.coef_[2]:.4f}] {sk.intercept_:.2f}")
    output(fig, out, 0.06, 0.2, 0.55, 0.2, size=12)
    fig.text(0.65, 0.7, "200 crossings, three inputs", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.65, 0.64, wrap("Both routes land on the same weights, and both sit close to the values "
                               "used to generate the data.\n\nWaves add about 3 minutes per metre; each "
                               "passenger adds about a second (boarding time).", 30),
             fontsize=13, color=NAVY, va="top", linespacing=1.4)
    return fig


def p23():
    fig = frame(23, "Curves from a linear model: feature maps", "Nonlinear regression")
    lead(fig, "Tide height rises and falls over the day, so a straight line in time cannot follow it. "
              "Keep the model linear in the weights, but feed it new features:", y=0.75, size=17)
    fig.text(0.1, 0.52, r"$\phi(h)=[\,h,\ h^2,\ h^3\,]\qquad y=\mathbf{w}^\top\phi(h)+b$", fontsize=24,
             color=NAVY)
    bullets(fig, [
        "Any fixed map φ works: powers, sines, bins, products of inputs",
        "The cost is still a convex quadratic in w, so all earlier tools still apply",
        "The curve in h can bend, even though the fit is linear regression",
    ], y=0.4, size=16, gap=0.07, width=80)
    return fig


def tide_panel(ax, d, show_val=False):
    hh = np.linspace(0, PERIOD, 300)
    ax.plot(hh, tide(hh), "--", color=GREY, lw=1.2)
    ax.scatter(h_tr, y_tr, s=26, color=NAVY, zorder=3)
    if show_val:
        ax.scatter(h_va, y_va, s=14, color=TEAL, alpha=0.6, zorder=2)
    ax.plot(hh, predict_deg(d, hh), color=CORAL, lw=2.2)
    ax.set_ylim(-3, 3)
    ax.set_title(f"degree {d}", fontsize=11, color=NAVY)
    ax.set_xticks([0, 3, 6, 9, 12]); ax.tick_params(labelsize=9)


def p24():
    fig = frame(24, "Too simple, about right, too wiggly", "Under- and overfitting")
    for k, d in enumerate([0, 1, 3, 9]):
        ax = axes(fig, [0.07 + k * 0.225, 0.3, 0.19, 0.36])
        tide_panel(ax, d)
        ax.set_xlabel("hour", fontsize=9)
    note(fig, "Dark dots: 11 noisy tide readings. Dashed: the true tide curve. Red: polynomial fit of the "
              "given degree. Degree 9 threads through the noise instead of the tide.", y=0.2)
    return fig


def p25():
    fig = frame(25, "Polynomial fits in scikit-learn", "Example")
    src = ("from sklearn.preprocessing import PolynomialFeatures\n"
           "from sklearn.pipeline import make_pipeline\n\n"
           "for deg in [1, 3, 9]:\n"
           "    m = make_pipeline(PolynomialFeatures(deg),\n"
           "                      LinearRegression())\n"
           "    m.fit(h_train, y_train)\n"
           "    print(deg, mse(m, train), mse(m, val))")
    code(fig, src, 0.06, 0.25, 0.52, 0.5, size=12)
    out = "deg   train MSE   val MSE\n" + "\n".join(
        f"{d:>3}   {TRAIN_MSE[d]:9.3f}   {VAL_MSE[d]:7.3f}" for d in [1, 3, 9])
    output(fig, out, 0.62, 0.48, 0.32, 0.27, size=13)
    fig.text(0.62, 0.4, wrap("Training error only goes down as the degree grows. Validation error is "
                              "what tells the fits apart.", 32), fontsize=13, color=NAVY, va="top",
             linespacing=1.4)
    return fig


def p26():
    fig = frame(26, "Seeing it against fresh data", "Under- and overfitting")
    for k, d in enumerate([1, 3, 9]):
        ax = axes(fig, [0.07 + k * 0.305, 0.3, 0.26, 0.38])
        tide_panel(ax, d, show_val=True)
        ax.set_xlabel("hour", fontsize=9)
    note(fig, "Teal dots are 40 validation readings the fits never saw. Degree 1 misses the shape, degree 3 "
              "follows it, degree 9 swings away between the training points.", y=0.2)
    return fig


def p27():
    fig = frame(27, "Training vs validation error as the degree grows", "Model complexity")
    ax = axes(fig, [0.08, 0.2, 0.5, 0.52])
    ds = DEGS[1:]
    ax.plot(ds, [TRAIN_MSE[d] for d in ds], "-o", color=NAVY, label="training MSE")
    ax.plot(ds, [VAL_MSE[d] for d in ds], "-o", color=CORAL, label="validation MSE")
    ax.set_yscale("log")
    ax.set_xlabel("polynomial degree", fontsize=11); ax.set_ylabel("MSE (log scale)", fontsize=11)
    ax.legend(frameon=False, fontsize=11)
    bullets(fig, [
        "Training error keeps falling: more capacity always fits the log better",
        "Validation error falls, bottoms out, then climbs",
        "Pick the complexity at the bottom of the validation curve; the test set stays untouched",
    ], x=0.62, y=0.68, size=14, gap=0.07, width=32)
    return fig


def p28():
    fig = frame(28, "Losses for yes/no outcomes", "Classification")
    lead(fig, "New target: t ∈ {0, 1} (1 = crossing more than 10 minutes late). The model outputs "
              "p = its probability of a 1.", y=0.75, size=16)
    fig.text(0.07, 0.60, "0–1 loss", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.07, 0.555, wrap("1 if the rounded prediction is wrong, else 0. Easy to read, but flat almost "
                               "everywhere, so gradients give no direction.", 62), fontsize=13, color=NAVY,
             va="top", linespacing=1.4)
    fig.text(0.07, 0.4, "Log loss (cross-entropy)", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.07, 0.33, r"$\ell(p,t)=-\,[\,t\log p+(1-t)\log(1-p)\,]$", fontsize=20, color=NAVY,
             va="center")
    fig.text(0.07, 0.25, wrap("Smooth, so gradient methods work. Confident mistakes cost a lot: "
                               f"p = 0.9 on an on-time crossing costs {-np.log(0.1):.2f}, "
                               f"p = 0.6 costs {-np.log(0.4):.2f}.", 60), fontsize=13, color=NAVY,
             va="top", linespacing=1.4)
    ax = axes(fig, [0.62, 0.22, 0.32, 0.42])
    p = np.linspace(0.01, 0.99, 200)
    ax.plot(p, -np.log(p), color=CORAL, lw=2.4, label="log loss, t = 1")
    ax.plot(p, (p < 0.5).astype(float), color=TEAL, lw=2.4, label="0–1 loss, t = 1")
    ax.set_xlabel("predicted p", fontsize=10)
    ax.legend(frameon=False, fontsize=10)
    return fig


def p29():
    fig = frame(29, "Predicting a late crossing with a regression line?", "A tempting shortcut")
    lead(fig, "Inputs: wind (kn) and wave height (m). Label: late = 1 if the crossing ran more than 10 "
              "minutes over schedule.", y=0.75, size=16)
    boxes(fig, [
        ("The shortcut", "Treat the 0/1 label as a number, fit ordinary least squares, call it late when "
                         "the prediction is ≥ 0.5."),
        ("Why it is shaky", "Outputs are not confined to [0, 1], so they are not probabilities. Squared loss "
                            "ignores that each outcome is a coin flip with some chance p."),
    ], cols=2, y0=0.6, w=0.43, h=0.3, gx=0.03, size=14, width=46)
    note(fig, "It produces a classifier of sorts. The next slides show where it bends out of shape.", y=0.2)
    return fig


def p30():
    fig = frame(30, "Trying the shortcut in Python", "Example")
    src = ("X = np.c_[wind, waves]                 # 160 crossings\n"
           "reg = LinearRegression().fit(X, late)\n"
           "pred = reg.predict(X)\n\n"
           "print(pred.min(), pred.max())\n"
           "print(((pred >= 0.5) == late).mean())")
    code(fig, src, 0.06, 0.42, 0.55, 0.33, size=12)
    output(fig, f"{pred_c.min():.2f} {pred_c.max():.2f}\n{ACC_C:.3f}", 0.06, 0.24, 0.55, 0.14, size=13)
    n_out = int(np.sum((pred_c < 0) | (pred_c > 1)))
    fig.text(0.65, 0.7, "What came back", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.65, 0.64, wrap(f"{ACC_C:.0%} of crossings are labelled correctly, which sounds fine.\n\n"
                               f"But {n_out} of the 160 'probabilities' fall below 0 or above 1.", 30),
             fontsize=14, color=NAVY, va="top", linespacing=1.4)
    return fig


def p31():
    fig = frame(31, "Where the shortcut breaks", "A tempting shortcut")
    ax = axes(fig, [0.08, 0.22, 0.42, 0.48])
    ax.hist(pred_c, bins=24, color=TEAL)
    ax.axvspan(pred_c.min() - 0.1, 0, color=CORAL, alpha=0.15)
    ax.axvspan(1, pred_c.max() + 0.1, color=CORAL, alpha=0.15)
    ax.axvline(0.5, color=NAVY, ls=":", lw=1.2)
    ax.set_xlabel("regression output", fontsize=11); ax.set_ylabel("crossings", fontsize=11)
    bullets(fig, [
        "Shaded areas: outputs that cannot be probabilities",
        "The 0.5 cut-off is arbitrary; nothing in the fit gives it meaning",
        "Very windy days push the line up for everyone and can move the cut-off for ordinary days",
    ], x=0.56, y=0.68, size=14, gap=0.07, width=34)
    return fig


def p32():
    fig = frame(32, "A line versus an S-curve", "Towards logistic regression")
    ax = axes(fig, [0.08, 0.27, 0.5, 0.47])
    jitter = rng4.uniform(-0.04, 0.04, K)
    ax.scatter(wind_c, late + jitter, s=16, color=NAVY, alpha=0.6, label="observed late (1) / on time (0)")
    a, b = np.linalg.lstsq(np.c_[wind_c, np.ones(K)], late, rcond=None)[0]
    xs = np.linspace(0, 40, 200)
    ax.plot(xs, a * xs + b, color=CORAL, lw=2.4, label="straight-line fit")
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression().fit(wind_c[:, None], late)
    ax.plot(xs, lr.predict_proba(xs[:, None])[:, 1], color=TEAL, lw=2.4, label="logistic fit")
    ax.axhspan(-0.3, 0, color=LIGHT); ax.axhspan(1, 1.3, color=LIGHT)
    ax.set_ylim(-0.3, 1.3)
    ax.set_xlabel("wind (knots)", fontsize=11); ax.set_ylabel("late?", fontsize=11)
    ax.legend(frameon=False, fontsize=10, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    bullets(fig, [
        "The line runs past 0 and 1",
        "The S-curve stays inside [0, 1] and reads as a probability",
        "Fitting the S-curve with log loss is logistic regression: next module",
    ], x=0.62, y=0.68, size=14, gap=0.07, width=32)
    return fig


def p33():
    fig = frame(33, "The same recipe at scale", "Big picture")
    boxes(fig, [
        ("Language models", "Trained to predict the next token by minimising cross-entropy over a huge "
                            "vocabulary."),
        ("Image classifiers", "Cross-entropy again, now over thousands of classes."),
        ("Deep networks", "Stacks of linear maps and nonlinearities, tuned by gradient steps on an "
                          "average loss."),
    ], cols=3, y0=0.74, w=0.28, h=0.27, gx=0.03, size=13, width=30)
    lead(fig, "Data → model → loss → empirical risk → gradient steps. Once that chain makes sense for a "
              "ferry and a line, it makes sense for much larger systems.", y=0.33, size=17)
    return fig


def p34():
    fig = frame(34, "Check yourself", "Quick questions")
    qs = [
        ("1. A forecast misses by 3 minutes. How many times more does (y − t)² charge than |y − t|?",
         "A. 3×    B. the same    C. 1.5×    D. 9×"),
        ("2. On the tide data, raising the polynomial degree from 3 to 9 most likely…",
         "A. lowers both errors    B. lowers training error, raises validation error\n"
         "C. raises both errors    D. changes nothing"),
        ("3. Why is the normal equation less attractive with a million features?",
         "A. J stops being convex    B. it needs a learning rate\n"
         "C. solving with XᵀX becomes very expensive    D. it can only fit one input"),
    ]
    y = 0.73
    for q, a in qs:
        fig.text(0.07, y, wrap(q, 100), fontsize=15, color=NAVY, weight="bold", va="top")
        fig.text(0.09, y - 0.055, a, fontsize=14, color=NAVY, va="top", linespacing=1.4)
        y -= 0.2
    note(fig, "Answers: 1 — A (9 vs 3), 2 — B, 3 — C", y=0.13)
    return fig


def p35():
    fig = frame(35, "Where this goes next", "Looking ahead")
    boxes(fig, [
        ("Probability view", "Squared loss and log loss come out of maximum likelihood once noise is "
                             "modelled explicitly."),
        ("Logistic regression", "The S-curve from slide 32, trained with log loss and gradient descent."),
        ("Evaluation", "Validation curves, cross-validation, and what the bias–variance trade-off says "
                       "about slide 27."),
        ("Regularisation", "Penalties that tame high-degree fits, and optimisers that cope with big data."),
    ], cols=2, y0=0.74, w=0.43, h=0.24, gx=0.03, gy=0.04, size=14, width=46)
    return fig


def p36():
    fig = frame(36, "Further reading and credits", "References")
    bullets(fig, [
        "Bishop, C. M. (2006). Pattern Recognition and Machine Learning. Springer. Ch. 1 and 3",
        "Hastie, Tibshirani & Friedman (2009). The Elements of Statistical Learning, 2nd ed. Ch. 3",
        "scikit-learn user guide: Linear models; Polynomial features",
    ], y=0.72, size=16, gap=0.08, width=90)
    card(fig, 0.06, 0.18, 0.88, 0.26)
    fig.text(0.08, 0.39, "About this lecture", fontsize=15, color=TEAL, weight="bold")
    fig.text(0.08, 0.34, wrap("Written by the LectureLoop team as the demo lecture for our app. All text, "
                               "examples, figures and data are our own; the ferry, tide and lateness data "
                               "are synthetic and generated by build_lecture.py. Released under CC BY 4.0.",
                               110), fontsize=13, color=NAVY, va="top", linespacing=1.45)
    return fig


PAGES = {i: globals()[f"p{i}"] for i in range(1, 37)}


def main(out, only=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    nums = sorted(only or PAGES)
    with PdfPages(out / "lectureloop_demo_regression.pdf") as pdf:
        for n in nums:
            fig = PAGES[n]()
            pdf.savefig(fig)
            fig.savefig(out / f"{n}.jpg", dpi=100, pil_kwargs={"quality": 90})
            plt.close(fig)
    print("wrote", len(nums), "pages to", out)


if __name__ == "__main__":
    main(sys.argv[1], [int(a) for a in sys.argv[2:]] or None)
