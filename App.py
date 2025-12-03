import streamlit as st
import pandas as pd
import itertools

st.set_page_config(page_title="Générateur de Combinés 3 et 4", layout="wide")

st.title("🔢 Générateur de Combinés (3 & 4) — Probabilités optimisées")

# --- Fonctions de base ---
def odds_to_prob(odds):
    if odds <= 0:
        return 0
    return 1 / odds

def combine_probability(prob_list):
    p = 1
    for x in prob_list:
        p *= x
    return p

def combine_odds(odds_list):
    x = 1
    for o in odds_list:
        x *= o
    return x

def final_probability(odds, confidence, manual_prob):
    p_odd = odds_to_prob(odds)

    if manual_prob > 0:
        # mélange avec probabilité manuelle si fournie
        return confidence * manual_prob + (1 - confidence) * p_odd
    else:
        # petite modulation selon confiance
        modifier = 1 + (confidence - 0.5) * 0.2
        return max(0, min(1, p_odd * modifier))

# --- Sidebar ---
st.sidebar.header("Paramètres")
min_odds = st.sidebar.number_input("Odds min", 1.01, 100.0, 1.01)
max_odds = st.sidebar.number_input("Odds max", 1.01, 100.0, 10.0)
min_conf = st.sidebar.slider("Confiance min", 0.0, 1.0, 0.0, 0.05)

stake = st.sidebar.number_input("Mise (€)", 1.0, 1000.0, 5.0)

gen3 = st.sidebar.checkbox("Générer combinés de 3", True)
gen4 = st.sidebar.checkbox("Générer combinés de 4", True)

st.sidebar.write("---")

# --- Table de départ (éditable) ---
st.subheader("Liste des sélections (modifiable)")

df_default = [
    {"event": "Match 1", "market": "1X2 Maison", "odds": 1.55, "confidence": 0.6, "manual_prob": 0},
    {"event": "Match 2", "market": "1X2 Maison", "odds": 1.85, "confidence": 0.5, "manual_prob": 0},
    {"event": "Match 3", "market": "Under 2.5", "odds": 1.72, "confidence": 0.7, "manual_prob": 0},
    {"event": "Match 4", "market": "Over 2.5", "odds": 2.10, "confidence": 0.4, "manual_prob": 0},
    {"event": "Match 5", "market": "1X2 Maison", "odds": 1.95, "confidence": 0.5, "manual_prob": 0},
]

df = st.data_editor(pd.DataFrame(df_default), use_container_width=True)

# --- Filtrage ---
df_filtered = df[
    (df["odds"] >= min_odds) &
    (df["odds"] <= max_odds) &
    (df["confidence"] >= min_conf)
].reset_index(drop=True)

st.write(f"**Sélections gardées : {len(df_filtered)}**")

# --- Génération des combinés ---
def generate(df, k_values):
    combos = []
    idx_list = list(df.index)

    for k in k_values:
        if len(idx_list) < k:
            continue

        for comb in itertools.combinations(idx_list, k):
            sub = df.loc[list(comb)]

            odds = list(sub["odds"])
            confs = list(sub["confidence"])
            manuals = list(sub["manual_prob"])

            probs = [
                final_probability(o, c, m)
                for o, c, m in zip(odds, confs, manuals)
            ]

            p_comb = combine_probability(probs)
            o_comb = combine_odds(odds)
            payout = round(o_comb * stake, 2)

            combos.append({
                "legs": " | ".join(sub["event"] + " — " + sub["market"]),
                "n": k,
                "probabilité": round(p_comb * 100, 3),
                "cote combinée": round(o_comb, 3),
                "gain potentiel (€)": payout,
            })

    return pd.DataFrame(combos)

k_values = []
if gen3: k_values.append(3)
if gen4: k_values.append(4)

if len(k_values) == 0:
    st.warning("Sélectionne au moins 'combinés de 3' ou 'de 4' dans la sidebar.")
else:
    results = generate(df_filtered, k_values)

    if len(results) == 0:
        st.info("Aucun combiné possible avec les filtres actuels.")
    else:
        st.subheader("Top combinés (triés par probabilité)")
        results = results.sort_values("probabilité", ascending=False)

        top_n = st.number_input("Nombre de résultats", 1, 5000, 20)
        st.dataframe(results.head(int(top_n)), use_container_width=True)

        # Export
        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger CSV", csv, "combines.csv", "text/csv")
