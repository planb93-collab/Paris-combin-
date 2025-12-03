import streamlit as st
import pandas as pd
import itertools
import requests

# ----------------------------
# CONFIGURATION
# ----------------------------
API_KEY = "TA_CLE_API_ICI"  # ← remplace par ta clé API
SPORT = "soccer_epl"        # Sport par défaut, tu peux changer
REGION = "uk"               
MARKET = "h2h"              
STAKE = 5                   

st.set_page_config(page_title="Générateur de Combinés Réels", layout="wide")
st.title("⚽ Générateur de Combinés avec matchs réels")

# ----------------------------
# FONCTIONS UTILES
# ----------------------------
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
        return confidence * manual_prob + (1 - confidence) * p_odd
    else:
        modifier = 1 + (confidence - 0.5) * 0.2
        return max(0, min(1, p_odd * modifier))

# ----------------------------
# PARAMÈTRES UTILISATEUR
# ----------------------------
st.sidebar.header("Paramètres API / filtre")
sport_input = st.sidebar.text_input("Sport (ex: soccer_epl)", SPORT)
region_input = st.sidebar.text_input("Region (uk, eu, us)", REGION)
market_input = st.sidebar.text_input("Market (h2h, spreads, totals)", MARKET)

min_conf = st.sidebar.slider("Confiance min", 0.0, 1.0, 0.0, 0.05)
gen3 = st.sidebar.checkbox("Générer combinés de 3", True)
gen4 = st.sidebar.checkbox("Générer combinés de 4", True)

# ----------------------------
# RÉCUPÉRER LES MATCHS VIA L’API
# ----------------------------
def get_matches():
    url = f"https://api.the-odds-api.com/v4/sports/{sport_input}/odds/?apiKey={API_KEY}&regions={region_input}&markets={market_input}&oddsFormat=decimal"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        st.error("Erreur lors de la récupération des matchs : " + str(e))
        return []

    matches = []
    for match in data:
        home = match.get('home_team')
        away = match.get('away_team')
        for bookmaker in match.get('bookmakers', []):
            for mkt in bookmaker.get('markets', []):
                if mkt['key'] == market_input:
                    for outcome in mkt.get('outcomes', []):
                        matches.append({
                            "event": f"{home} vs {away}",
                            "market": outcome['name'],
                            "odds": outcome['price'],
                            "confidence": 0.5,       # par défaut, tu peux modifier
                            "manual_prob": 0
                        })
    return pd.DataFrame(matches)

# ----------------------------
# AFFICHAGE DES MATCHS
# ----------------------------
st.subheader("Matchs récupérés via API")
df = get_matches()

if df.empty:
    st.warning("Aucun match récupéré. Vérifie ta clé API et les paramètres.")
else:
    st.data_editor(df, use_container_width=True)

# ----------------------------
# GÉNÉRATION DES COMBINÉS
# ----------------------------
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
            probs = [final_probability(o, c, m) for o, c, m in zip(odds, confs, manuals)]
            p_comb = combine_probability(probs)
            o_comb = combine_odds(odds)
            payout = round(o_comb * STAKE, 2)

            combos.append({
                "legs": " | ".join(sub["event"] + " — " + sub["market"]),
                "n": k,
                "probabilité": round(p_comb * 100, 3),
                "cote combinée": round(o_comb, 3),
                "gain potentiel (€)": payout
            })
    return pd.DataFrame(combos)

k_values = []
if gen3: k_values.append(3)
if gen4: k_values.append(4)

if not k_values:
    st.warning("Sélectionne au moins combinés de 3 ou 4 dans la sidebar.")
elif not df.empty:
    results = generate(df, k_values)
    results = results.sort_values("probabilité", ascending=False)
    top_n = st.number_input("Nombre de résultats", 1, 5000, 20)
    st.dataframe(results.head(int(top_n)), use_container_width=True)
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Télécharger CSV", csv, "combines.csv", "text/csv")
