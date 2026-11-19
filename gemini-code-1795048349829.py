import json, math, uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import numpy as np, pandas as pd, plotly.express as px, streamlit as st
from scipy import stats

st.set_page_config(page_title="Tuckies Studio | NUR-4 (AP Stats)", page_icon="🩺", layout="wide")

def dec(v): return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def usd(v): d = dec(v); return f"-${abs(d):,.2f}" if d < 0 else f"${d:,.2f}"

def get_exp_df(seed=2027):
    rng = np.random.default_rng(seed)
    s = np.r_[rng.permutation([1]*12 + [0]*28), rng.permutation([1]*20 + [0]*20)]
    df = pd.DataFrame({"prospect_id": [f"P{i:03}" for i in range(1, 81)], "message": ["A"]*40 + ["B"]*40, "converted": s})
    return df.iloc[rng.permutation(80)].reset_index(drop=True)

def calc_month(req, price, staff_h, h_per_u, seats, no_show, var_u, fix_tot, ad, cash, cap_ov=None):
    cap = int(cap_ov) if cap_ov is not None else min(math.floor(staff_h / h_per_u), int(seats))
    booked = min(int(req), cap)
    attended = math.floor(booked * (1.0 - no_show))
    rev = dec(price * Decimal(attended))
    var = dec(var_u * Decimal(attended))
    tot_exp = dec(var + fix_tot + ad)
    prof = dec(rev - tot_exp)
    end_cash = dec(cash + prof)
    return {"requested": int(req), "capacity": cap, "booked": booked, "unserved": max(0, int(req) - booked),
            "attended": attended, "sold": attended, "net_revenue": float(rev), "variable_expense": float(var),
            "fixed_expense": float(fix_tot), "marketing_expense": float(ad), "total_expense": float(tot_exp),
            "operating_profit": float(prof), "ending_cash": float(end_cash)}

def calc_stats(df):
    a, b = df[df["message"] == "A"]["converted"], df[df["message"] == "B"]["converted"]
    na, nb, xa, xb = len(a), len(b), int(a.sum()), int(b.sum())
    pa, pb, diff = xa / na, xb / nb, (xb / nb) - (xa / na)
    se_u = math.sqrt(pb*(1-pb)/nb + pa*(1-pa)/na)
    ci = (diff - 1.96 * se_u, diff + 1.96 * se_u)
    pp = (xa + xb) / (na + nb)
    se_p = math.sqrt(pp * (1 - pp) * (1/na + 1/nb))
    z = diff / se_p
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"pa": pa, "pb": pb, "diff": diff, "se_u": se_u, "ci": ci, "se_p": se_p, "z": z, "pval": pval}

def init_state():
    return {
        "team_id": "tuckies", "studio": "Tuckies Community Health Education Studio", "course": "AP Statistics",
        "pathway_id": "NUR-4", "level": "Advanced", "quarter": "Quarter 2", "v": 1, "snap": "SNAP-TUCKIES-V1",
        "cash": 4000.0, "equip": 1500.0, "equity": 6000.0, "re": -500.0, "run_ids": [], "ledger": [], "decisions": [],
        "p": {"price": 25.0, "D0": 80, "staff_h": 30.0, "h_per_u": 0.5, "seats": 60, "no_show": 0.0,
              "var_u": 5.0, "fix_m": 700.0, "access": 200.0},
        "offerings": [
            {"ID": "OFF-01", "Workshop (Fictional Nonclinical)": "General Wellness & Preventive Literacy", "Price": "$25", "D0": 80},
            {"ID": "OFF-02", "Workshop (Fictional Nonclinical)": "Family Caregiver Navigation Seminar", "Price": "$25", "D0": 0},
            {"ID": "OFF-03", "Workshop (Fictional Nonclinical)": "Everyday First-Aid & Home Safety Demo", "Price": "$25", "D0": 0},
        ],
        "camp": {"id": "CMP-001", "title": "Bilingual Community Flyers", "cash_cost": 100.0, "in_kind_labor": 30.0, "charged": False},
        "cross": [
            {"Subject": "English / Comm", "Application": "Plain-language CDC Clear Communication flyer review (Variant A vs B)"},
            {"Subject": "CTE Health Sci", "Application": "Strict nonclinical scope of practice & $1/seat sanitation consumables"},
        ],
    }

if "st" not in st.session_state: st.session_state.st = init_state()
S = st.session_state.st
def bump(): S["v"] += 1; S["snap"] = f"SNAP-TUCKIES-V{S['v']}"

# Sidebar: JSON Save/Load
with st.sidebar:
    st.subheader(f"🩺 {S['team_id']} | {S['pathway_id']} (v{S['v']})")
    st.download_button("⬇️ Save Snapshot (.json)", json.dumps(S, indent=2), f"tuckies_nur4_v{S['v']}.json", "application/json")
    up = st.file_uploader("⬆️ Load Snapshot (.json)", type=["json"])
    if up:
        d = json.loads(up.read().decode())
        if d.get("team_id") != "tuckies" or d.get("pathway_id") != "NUR-4": st.error("Rejected: wrong team/pathway ID.")
        elif st.button("Confirm Load"): st.session_state.st = d; st.rerun()
    if st.button("🔄 Reset Baseline"): st.session_state.st = init_state(); st.rerun()

st.title(f"🩺 {S['studio']}")
st.info("SIMULATION ONLY: Fictional nonclinical health education workshops. No diagnosis, clinical advice, or real patient data.")

p = S["p"]
prev = calc_month(p["D0"], dec(p["price"]), p["staff_h"], p["h_per_u"], p["seats"], p["no_show"], dec(p["var_u"]), dec(p["fix_m"]), dec(0), dec(S["cash"]))
tabs = st.tabs(["1. Overview", "2. Inputs & Ledger", "3. AP Stats", "4. Ops & Disruption", "5. Reports", "6. Marketing", "7. AI & Memos", "8. Cross-Course & Quiz"])

# 1. OVERVIEW
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", usd(S["cash"])); c2.metric("Capacity", f"{prev['capacity']} seats")
    c3.metric("Monthly Sales", f"{prev['sold']} seats", f"Unserved: {prev['unserved']}")
    c4.metric("Monthly Profit", usd(prev["operating_profit"]))
    st.write("**System Flow:** Student Inputs → `booked = min(req, floor(staff_h/h_per_u), seats)` → `attended = floor(booked*(1-no_show))` → Cash & Reports → AI Proposals (`pending`) → Student Approval.")
    st.dataframe(pd.DataFrame(S["offerings"]), use_container_width=True, hide_index=True)

# 2. INPUTS, FUNDING & LEDGER
with tabs[1]:
    l, r = st.columns(2)
    with l:
        st.write("**Startup Capital:** $6,000 Equity = $1,500 Equipment Asset + $500 Pre-Opening Expense + **$4,000 Opening Cash**.")
        with st.form("p_form"):
            p["price"] = st.number_input("Price ($)", 1.0, value=float(p["price"]))
            p["D0"] = st.number_input("Baseline Demand (D0)", 0, value=int(p["D0"]))
            p["staff_h"] = st.number_input("Educator Hours/Mo", 0.0, value=float(p["staff_h"]))
            p["seats"] = st.number_input("Venue Seats/Mo", 0, value=int(p["seats"]))
            p["no_show"] = st.slider("No-Show Rate", 0.0, 0.8, float(p["no_show"]), 0.05)
            p["var_u"] = st.number_input("Variable Cost/Attended Seat ($)", 0.0, value=float(p["var_u"]))
            p["fix_m"] = st.number_input("Fixed Cost/Mo ($ incl. $200 accessibility)", 0.0, value=float(p["fix_m"]))
            if st.form_submit_button("Save Parameters"): bump(); st.success("Saved!"); st.rerun()
    with r:
        with st.form("m_form"):
            m_lbl = st.text_input("Month", f"2027-{len(S['ledger'])+1:02d}")
            m_req = st.number_input("Requested Seats", 0, value=int(p["D0"]))
            m_ad = st.number_input("Ad Cost ($)", 0.0, value=0.0)
            rid = st.text_input("Run ID", f"RUN-{m_lbl}")
            if st.form_submit_button("✅ Commit Month to Ledger"):
                if rid in S["run_ids"]: st.error("Duplicate Run ID blocked!")
                else:
                    row = calc_month(m_req, dec(p["price"]), p["staff_h"], p["h_per_u"], p["seats"], p["no_show"], dec(p["var_u"]), dec(p["fix_m"]), dec(m_ad), dec(S["cash"]))
                    row["month"], row["run_id"] = m_lbl, rid
                    S["ledger"].append(row); S["run_ids"].append(rid); S["cash"] = row["ending_cash"]; S["re"] = round(S["re"] + row["operating_profit"], 2); bump(); st.rerun()
        if st.button("🧪 Run Official 3-Month NUR Fixture Verification"):
            fix_in = [("2027-01", 80, 60, 0), ("2027-02", 88, 60, 100), ("2027-03", 72, 45, 0)]
            exp = [(60, 1500.0, 1000.0, 500.0, 4500.0), (60, 1500.0, 1100.0, 400.0, 4900.0), (45, 1125.0, 925.0, 200.0, 5100.0)]
            c, rows = dec(4000), []
            for (mo, rq, ov, ad), e in zip(fix_in, exp):
                o = calc_month(rq, dec(25), 30, 0.5, 60, 0.0, dec(5), dec(700), dec(ad), c, ov); c = dec(o["ending_cash"])
                ok = (o["sold"], o["net_revenue"], o["total_expense"], o["operating_profit"], o["ending_cash"]) == e
                rows.append({"Month": mo, "Sold": o["sold"], "Rev": usd(o["net_revenue"]), "Exp": usd(o["total_expense"]), "Profit": usd(o["operating_profit"]), "Cash": usd(o["ending_cash"]), "Status": "PASS" if ok else "FAIL"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if S["ledger"]: st.dataframe(pd.DataFrame(S["ledger"]), use_container_width=True, hide_index=True)

# 3. AP STATISTICS (FOUNDATION / APPLIED / ADVANCED)
with tabs[2]:
    lvl = st.radio("Level:", ["Foundation", "Applied", "Advanced"], index=["Foundation", "Applied", "Advanced"].index(S["level"]), horizontal=True)
    S["level"] = lvl
    df_exp = get_exp_df(2027); st_res = calc_stats(df_exp)
    st.write(f"**Synthetic Randomized Experiment (seed=2027, N=80):** Message A = **30.0%** (12/40) vs Message B = **50.0%** (20/40) | Diff = **+20.0%**.")
    st.plotly_chart(px.bar(x=["Message A (Standard)", "Message B (Action)"], y=[0.30, 0.50], labels={"x": "Variant", "y": "Conversion"}, title="Conversion Rate by Message (n=40 each)"), use_container_width=True)
    if lvl in ["Applied", "Advanced"]:
        st.write(f"**95% Unpooled CI:** `[{st_res['ci'][0]:.4f}, {st_res['ci'][1]:.4f}]` (SE={st_res['se_u']:.5f}) | **Pooled Two-Sided z-Test:** `z = {st_res['z']:.5f}`, `p = {st_res['pval']:.5f}` (SE_pool={st_res['se_p']:.5f}) → Fail to reject $H_0$ at $\\alpha=0.05$.")
    if lvl == "Advanced":
        n_sim = st.slider("Simulated Sample Size per Group (n)", 40, 250, 100, 10)
        rng = np.random.default_rng(2027)
        sa, sb = rng.binomial(n_sim, 0.30, 2000) / n_sim, rng.binomial(n_sim, 0.50, 2000) / n_sim
        pp = (sa + sb) / 2
        pwr = float(np.mean(np.abs((sb - sa) / np.sqrt(np.maximum(1e-9, pp*(1-pp)*(2/n_sim)))) > 1.96))
        st.metric(f"Simulation Power at n={n_sim}/group (true lift +20%, α=0.05)", f"{pwr:.1%}")
        st.caption("Note: 95% CI estimates true conversion lift, not individual monthly seat sales (which are capped at 60 venue seats).")

# 4. OPERATIONS & REQUIRED DISRUPTION
with tabs[3]:
    ns = calc_month(80, dec(25), 30, 0.5, 60, 0.20, dec(5), dec(700), dec(0), dec(4000))
    st.write(f"**NUR No-Show Test (`no_show=0.20`):** booked={ns['booked']}, attended={ns['attended']}, rev={usd(ns['net_revenue'])}, var={usd(ns['variable_expense'])}, profit={usd(ns['operating_profit'])} → **{'PASS' if ns['operating_profit']==260 else 'FAIL'}**")
    acc_add = st.slider("Required Disruption: Venue drops 20% (60 → 48 seats). Added Accessibility Budget ($/mo):", 0, 300, 150, 25)
    dis = calc_month(p["D0"], dec(p["price"]), p["staff_h"], p["h_per_u"], math.floor(p["seats"]*0.8), p["no_show"], dec(p["var_u"]), dec(p["fix_m"]+acc_add), dec(0), dec(S["cash"]))
    st.write(f"**Disruption Result:** Capacity = {dis['capacity']} seats | Attended = {dis['attended']} | Unserved = {dis['unserved']} | Operating Profit = **{usd(dis['operating_profit'])}**")

# 5. REPORT CENTER
with tabs[4]:
    scens = [calc_month(math.floor(p["D0"]*m), dec(p["price"]), p["staff_h"], p["h_per_u"], p["seats"], p["no_show"], dec(p["var_u"]), dec(p["fix_m"]), dec(0), dec(S["cash"])) | {"Scenario": lbl}
             for lbl, m in [("Downside (0.90x)", 0.9), ("Baseline (1.00x)", 1.0), ("Upside (1.10x)", 1.1)]]
    st.dataframe(pd.DataFrame(scens)[["Scenario", "requested", "capacity", "sold", "net_revenue", "total_expense", "operating_profit"]], use_container_width=True, hide_index=True)
    st.write(f"**Balance Sheet Check:** Assets ({usd(S['cash']+S['equip'])}) = Liabilities ($0) + Equity ({usd(S['equity']+S['re'])})")

# 6. COSTED MARKETING STUDIO
with tabs[5]:
    c = S["camp"]
    st.write(f"**{c['id']} ({c['title']}):** Cash Cost = **$100.00** ($20 graphics + $30 print + $50 placement) | In-Kind Student Labor = **$30.00** (2h @ $15/hr, non-cash).")
    if c["charged"]: st.success("Campaign already charged once (duplicate blocked).")
    elif st.button("✅ Approve & Charge $100 Campaign Once"):
        c["charged"] = True; S["cash"] -= 100.0; S["re"] -= 100.0; bump(); st.rerun()

# 7. AI ROLES & DECISION MEMOS
with tabs[6]:
    role = st.selectbox("Copy Role Prompt:", ["Finance", "Operations", "Market & Marketing", "Independent Reviewer"])
    st.code(f"Career Venture Lab | team_id=tuckies | pathway=NUR-4 | course=AP Statistics | level={S['level']} | snap={S['snap']} (v{S['v']}). Role: {role}. Use only v{S['v']}. Never commit changes or give clinical advice. Return structured analysis with approval_status=pending.")
    with st.form("dm"):
        q = st.text_input("Decision Question", "Adopt Message B & add $150 accessibility buffer?")
        rep = st.text_input("Two Cited Reports", "Report Center Scenarios + AP Stats Experiment (seed=2027)")
        pred = st.text_input("Prediction & Owner", "Profit >= $110/mo under 48-seat disruption; Owner: Tuckies Lead")
        if st.form_submit_button("Save Decision Memo"):
            S["decisions"].append({"Snap": S["snap"], "Question": q, "Reports": rep, "Prediction": pred}); bump(); st.rerun()
    if S["decisions"]: st.dataframe(pd.DataFrame(S["decisions"]), use_container_width=True, hide_index=True)

# 8. CROSS-COURSE & FROZEN ASSESSMENT
with tabs[7]:
    st.dataframe(pd.DataFrame(S["cross"]), use_container_width=True, hide_index=True)
    st.write("**Practice Question (Frozen Snapshot):** With 90 requested seats, 30 staff hrs (0.5h/seat), 60 venue seats, and 10% no-show rate at $25/seat ($5/seat var, $700 fixed), what is Operating Profit?")
    ans = st.number_input("Your Answer ($):", 0.0)
    if st.button("Check Answer"):
        st.success("Correct! booked=60, attended=54, rev=$1,350, var=$270, profit=$380.") if abs(ans - 380) < 0.01 else st.warning("Expected $380.00 (54 attended × $20 margin − $700 fixed).")