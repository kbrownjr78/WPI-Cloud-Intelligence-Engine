"""
WPI Quantitative Sports Engine (v20.0 - High-Speed Plain Text Ingestion Circuit)
File Name: automated_pipeline.py
Chunk 1 of 4: System Dependencies, Initialization Layer, and Core Mechanics
"""

import os
import csv
import math
import time
from datetime import datetime
import numpy as np
import pandas as pd
import requests

class WPIRawEngine:
    def __init__(self):
        print("⚡ WPI Autonomous Engine Active. Calibrating cross-sport parameter arrays...")

    def sigmoid(self, x):
        """Standard logistic sigmoid function compressing interaction tokens between 0 and 1."""
        try:
            return 1 / (1 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    def convert_odds_to_implied_prob(self, odds):
        """Converts American moneyline formats to clean Implied Market Probability (P_Market)."""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

    def evaluate_hard_market_filters(self, market_odds, sport, line_value=None, market_type=None):
        """Enforces Section 3 Hard Market Filters & Post-Audit Safety Constraints."""
        if market_odds < -175:
            return False, f"PRUNED: Premium requires break-even index worse than -175 ({market_odds})"
            
        return True, "PASSED"
    def run_simulation(self, sport, home_team, away_team, target_selection, home_metrics, away_metrics, env_metrics, market_odds, line_value=None, market_type='moneyline'):
        """Executes 100,000-loop Monte Carlo distribution structures across multi-sport and targets."""
        passed, msg = self.evaluate_hard_market_filters(market_odds, sport, line_value, market_type)
        if not passed:
            return None, None, None, f"FILTERED: {msg}"

        # 🔬 1. MICRO INDIVIDUAL PLAYER PROP ROUTING MATRIX
        if market_type.lower() in ['player_prop', 'prop']:
            iterations = 100000
            if sport.lower() == 'soccer':
                if 'goal' in target_selection.lower():
                    expected_player_goals = home_metrics.get('prop_baseline', 0.28) * env_metrics.get('matchup_scalar', 1.0)
                    sim_prop = np.random.poisson(expected_player_goals, iterations)
                    p_wpi = np.sum(sim_prop >= 1) / iterations
                else:
                    expected_stat = home_metrics.get('prop_baseline', 1.5) * env_metrics.get('matchup_scalar', 1.0)
                    sim_prop = np.random.normal(expected_stat, home_metrics.get('prop_variance', 0.45), iterations)
                    p_wpi = np.sum(sim_prop > line_value) / iterations if 'under' not in target_selection.lower() else np.sum(sim_prop < line_value) / iterations
            elif sport.lower() in ['mlb', 'baseball']:
                if 'strikeouts' in target_selection.lower() or 'k' in target_selection.lower():
                    expected_k = home_metrics.get('prop_baseline', 5.5) * env_metrics.get('matchup_scalar', 1.0)
                    sim_prop = np.random.normal(expected_k, home_metrics.get('prop_variance', 1.2), iterations)
                else:
                    expected_tb = home_metrics.get('prop_baseline', 1.5) * env_metrics.get('matchup_scalar', 1.0)
                    sim_prop = np.random.poisson(expected_tb, iterations)
                p_wpi = np.sum(sim_prop > line_value) / iterations if 'under' not in target_selection.lower() else np.sum(sim_prop < line_value) / iterations
            elif sport.lower() in ['basketball', 'wnba']:
                expected_pra = home_metrics.get('prop_baseline', 22.5) * env_metrics.get('pace_scalar', 1.0)
                sim_prop = np.random.normal(expected_pra, home_metrics.get('prop_variance', 3.5), iterations)
                p_wpi = np.sum(sim_prop > line_value) / iterations if 'under' not in target_selection.lower() else np.sum(sim_prop < line_value) / iterations
            else:
                p_wpi = 0.0

            p_market = self.convert_odds_to_implied_prob(market_odds)
            alpha_edge = p_wpi - p_market
            return p_wpi, p_market, alpha_edge, "SUCCESS"

        # 🏟️ 2. BASEBALL INNING-SEGMENT POISSON Core (F3, F5, F7, FULL GAME)
        if sport.lower() in ['mlb', 'baseball']:
            if market_type.lower() == 'f3':
                inning_scale, pen_weight_home, pen_weight_away = 3.0, 0.0, 0.0
            elif market_type.lower() == 'f5':
                inning_scale, pen_weight_home, pen_weight_away = 5.0, 0.0, 0.0
            elif market_type.lower() == 'f7':
                inning_scale, pen_weight_home, pen_weight_away = 7.0, 0.28, 0.28
            else:
                inning_scale, pen_weight_home, pen_weight_away = 9.0, 0.44, 0.44

            base_home_rate = (home_metrics['woba_vs_hand'] * (1 / max(away_metrics['starter_fip'], 0.5))) * home_metrics['runs_per_inning']
            base_away_rate = (away_metrics['woba_vs_hand'] * (1 / max(home_metrics['starter_fip'], 0.5))) * away_metrics['runs_per_inning']
            expected_home = ((base_home_rate * (1.0 - pen_weight_away)) + (away_metrics['bullpen_xfip'] * 0.15 * pen_weight_away)) * inning_scale
            expected_away = ((base_away_rate * (1.0 - pen_weight_home)) + (home_metrics['bullpen_xfip'] * 0.15 * pen_weight_home)) * inning_scale
            
            park_multiplier = env_metrics.get('park_factor', 1.00)
            weather_delta = 1.05 if env_metrics.get('temp', 72) > 82 else 0.96
            expected_home_runs = expected_home * park_multiplier * weather_delta
            expected_away_runs = expected_away * park_multiplier * weather_delta
            
            iterations = 100000
            sim_home = np.random.poisson(expected_home_runs, iterations)
            sim_away = np.random.poisson(expected_away_runs, iterations)
            
            if market_type in ['over', 'under', 'total']:
                p_wpi = np.sum((sim_home + sim_away) > line_value) / iterations
            else:
                p_wpi = np.sum(sim_home > sim_away) / iterations
            
            p_market = self.convert_odds_to_implied_prob(market_odds)
            alpha_edge = p_wpi - p_market
            return p_wpi, p_market, alpha_edge, "SUCCESS"

        # 🎾 3. TENNIS MODE INTERACTION LAYERS
        if sport.lower() == 'tennis':
            elo_a = home_metrics['elo_surface']['clay']
            elo_b = away_metrics['elo_surface']['clay']
            serve_eff_a = home_metrics['first_serve_pct'] * home_metrics['first_serve_pts_won']
            serve_eff_b = away_metrics['first_serve_pct'] * away_metrics['first_serve_pts_won']
            
            base_a = (elo_a / 1500.0) * home_metrics['dominance_ratio'] * ((0.6 * home_metrics['hold_pct']) + (0.4 * home_metrics['break_pct'])) * (1 + serve_eff_a)
            base_b = (elo_b / 1500.0) * away_metrics['dominance_ratio'] * ((0.6 * away_metrics['hold_pct']) + (0.4 * away_metrics['break_pct'])) * (1 + serve_eff_b)
            fatigue_a = home_metrics['games_played_72h'] / max(home_metrics['rest_hours'], 1)
            fatigue_b = away_metrics['games_played_72h'] / max(away_metrics['rest_hours'], 1)
            
            expected_home = base_a * (1.0 - (0.05 * fatigue_a))
            expected_away = base_b * (1.0 - (0.05 * fatigue_b))
            
            iterations = 100000
            sim_a = np.random.normal(expected_home, 0.15, iterations)
            sim_b = np.random.normal(expected_away, 0.15, iterations)
            p_wpi = np.sum(sim_a > sim_b) / iterations
            p_market = self.convert_odds_to_implied_prob(market_odds)
            alpha_edge = p_wpi - p_market
            return p_wpi, p_market, alpha_edge, "SUCCESS"

        # ⚽🏀 4. TEAM BASKETBALL & SOCCER INTERACTION LAYERS
        home_oi = home_metrics['xg_adjusted'] * (1 + home_metrics['sot_surge']) * home_metrics['league_scalar'] * 0.65
        away_oi = away_metrics['xg_adjusted'] * (1 + away_metrics['sot_surge']) * away_metrics['league_scalar'] * 0.65
        home_di = home_metrics['xga_adjusted'] * (home_metrics['ppda'] * home_metrics['clearance_factor']) * 1.14 * home_metrics['league_scalar']
        away_di = away_metrics['xga_adjusted'] * (away_metrics['ppda'] * away_metrics['clearance_factor']) * 1.14 * away_metrics['league_scalar']

        home_sf = (home_metrics['form_xg_delta'] - home_metrics['form_def_delta']) + math.log(max(home_metrics['rest_hours'], 1)) - home_metrics['travel_friction']
        away_sf = (away_metrics['form_xg_delta'] - away_metrics['form_def_delta']) + math.log(max(away_metrics['rest_hours'], 1)) - away_metrics['travel_friction']
        sf_live_delta = home_sf - away_sf

        weather_lambda = 1.025 if env_metrics['temp'] > 80 and env_metrics['humidity'] > 55 else (0.945 if env_metrics['temp'] < 52 and env_metrics['humidity'] > 70 else 1.000)
        base_interaction = (0.4 * (home_oi * away_di)) - (0.4 * (home_di * away_oi)) + (0.1 * math.pow(env_metrics['venue_index'], weather_lambda)) + (0.1 * sf_live_delta)
        p_base_home = self.sigmoid(base_interaction)
        
        if sport.lower() == 'soccer' and market_type.lower() == '1h':
            expected_home = p_base_home * 1.6 * 0.45
            expected_away = (1 - p_base_home) * 1.3 * 0.45
        elif sport.lower() == 'basketball' and market_type.lower() == '1h':
            expected_home = p_base_home * 98.5 * 0.50
            expected_away = (1 - p_base_home) * 94.2 * 0.50
        else:
            expected_home = p_base_home * 1.6 if sport.lower() == 'soccer' else p_base_home * 98.5
            expected_away = (1 - p_base_home) * 1.3 if sport.lower() == 'soccer' else (1 - p_base_home) * 94.2

        iterations = 100000
        sim_home = np.random.poisson(expected_home, iterations)
        sim_away = np.random.poisson(expected_away, iterations)
        
        if market_type == 'to_qualify':
            p_wpi = (np.sum(sim_home > sim_away) + (np.sum(sim_home == sim_away) * 0.53)) / iterations
        elif market_type in ['over_goals', 'total', '1h_total']:
            p_wpi = np.sum((sim_home + sim_away) > line_value) / iterations
        elif market_type in ['spread', '1h_spread']:
            p_wpi = np.sum((sim_home + line_value) > sim_away) / iterations
        else:
            p_wpi = np.sum(sim_home > sim_away) / iterations

        p_market = self.convert_odds_to_implied_prob(market_odds)
        alpha_edge = p_wpi - p_market
        return p_wpi, p_market, alpha_edge, "SUCCESS"
def run_cloud_pipeline():
    print("🛰️ Connecting to Plain Text Sports Ingestion Hub...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    portfolio = []
    
    try:
        url = "https://plaintextsports.com"
        response = requests.get(url, headers={"User-Agent": "WPI Quant Engine v20.0"}, timeout=10)
        
        if response.status_code == 200:
            lines = response.text.split('\n')
            print(f"📊 Document verified. Parsing {len(lines)} plain text database records.")
            
            current_league = "Global Circuit"
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Dynamic Context Isolation Tracker parses current league category lines
                if "World Cup" in line or "FIFA" in line:
                    current_league = "FIFA World Cup"
                elif "Major League Baseball" in line or "MLB" in line:
                    current_league = "MLB"
                elif "National Women's Soccer" in line or "NWSL" in line:
                    current_league = "NWSL"
                elif "Major League Soccer" in line or "MLS" in line:
                    current_league = "MLS"
                
                # Dynamic ASCII boundary pattern match blocker: "+-----------------+"
                if "+-------" in line or "+---" in line:
                    try:
                        # Extract the inner contender string layouts
                        team_1 = lines[i+2].replace('|', '').strip()
                        team_2 = lines[i+3].replace('|', '').strip()
                        
                        if team_1 and team_2 and not team_1.startswith('+') and not team_2.startswith('+'):
                            if current_league == "MLB":
                                sport, m_type, odds, val = "mlb", "f5", -110, None
                                home_m = {'starter_fip': 3.42, 'bullpen_xfip': 3.85, 'woba_vs_hand': 0.334, 'runs_per_inning': 0.52}
                                away_m = {'starter_fip': 4.12, 'bullpen_xfip': 4.22, 'woba_vs_hand': 0.312, 'runs_per_inning': 0.48}
                            elif current_league in ["FIFA World Cup", "NWSL", "MLS"]:
                                sport, m_type, odds, val = "soccer", "moneyline", -110, None
                                home_m = {'xg_adjusted': 1.85, 'sot_surge': 0.14, 'league_scalar': 1.0, 'xga_adjusted': 0.78, 'ppda': 8.2, 'clearance_factor': 1.15, 'form_xg_delta': 0.22, 'form_def_delta': -0.11, 'rest_hours': 96, 'travel_friction': 0.1}
                                away_m = {'xg_adjusted': 1.62, 'sot_surge': 0.08, 'league_scalar': 1.0, 'xga_adjusted': 1.12, 'ppda': 10.5, 'clearance_factor': 0.95, 'form_xg_delta': -0.05, 'form_def_delta': 0.18, 'rest_hours': 72, 'travel_friction': 0.3}
                            else:
                                sport, m_type, odds, val = "basketball", "moneyline", -160, None
                                home_m = {'xg_adjusted': 1.12, 'sot_surge': 0.05, 'league_scalar': 1.08, 'xga_adjusted': 0.96, 'ppda': 1.0, 'clearance_factor': 1.0, 'form_xg_delta': 0.06, 'form_def_delta': -0.02, 'rest_hours': 72, 'travel_friction': 0.0}
                                away_m = {'xg_adjusted': 0.98, 'sot_surge': 0.02, 'league_scalar': 1.08, 'xga_adjusted': 1.10, 'ppda': 1.0, 'clearance_factor': 1.0, 'form_xg_delta': -0.02, 'form_def_delta': 0.04, 'rest_hours': 48, 'travel_friction': 0.4}

                            portfolio.append({
                                "Sport": sport, "League": current_league, "Home": team_2, "Away": team_1,
                                "Target": f"{team_2} Moneyline", "Odds": odds, "Type": m_type, "Value": val,
                                "Home_M": home_m, "Away_M": away_m, "Env": {'temp': 74, 'humidity': 55, 'venue_index': 1.02, 'surface': 'clay', 'park_factor': 1.00}
                            })
                            i += 4
                    except Exception:
                        pass
                i += 1
    except Exception as e:
        print(f"❌ Ingestion Interruption: {str(e)}")

    # Forward the newly loaded data portfolio over to the closed processing block
    execute_matrix_processing(portfolio, today_str)
def execute_matrix_processing(portfolio, today_str):
    """Processes simulations independently outside the network request block to preserve layout indenting."""
    if len(portfolio) == 0:
        print("❌ CRITICAL ERROR: Plain Text Sports crawler returned 0 scheduled games.")
        print("🛑 Disengaging pipeline to prevent empty branch commits.")
        raise ValueError("DataIngestionError: Active portfolio tracking array tracks null.")

    engine = WPIRawEngine()
    raw_results = []
    
    print(f"🚀 Running 100,000-loop multi-sport randomizations across all {len(portfolio)} active items...")
    for match in portfolio:
        p_wpi, p_market, alpha, status = engine.run_simulation(
            match["Sport"], match["Home"], match["Away"], match["Target"],
            match["Home_M"], match["Away_M"], match["Env"], 
            match["Odds"], match["Value"], match["Type"]
        )
        
        if status == "SUCCESS":
            raw_results.append({
                "Date": today_str, "League": match["League"], "Matchup": f"{match['Home']} vs {match['Away']}",
                "Target_Selection": match["Target"], "Market_Odds": match["Odds"], "Market_Type": match["Type"].upper(),
                "P_WPI": p_wpi, "P_Market": p_market, "Alpha_Edge": alpha
            })
        else:
            raw_results.append({
                "Date": today_str, "League": match["League"], "Matchup": f"{match['Home']} vs {match['Away']}",
                "Target_Selection": match["Target"], "Market_Odds": match["Odds"], "Market_Type": match["Type"].upper(),
                "P_WPI": 0.0, "P_Market": 0.0, "Alpha_Edge": -99.0, "Notes": status
            })

    # 🗂️ STREAMLINED PROBABILITY MATRICES SORTING
    df_active = pd.DataFrame([r for r in raw_results if r.get("Alpha_Edge", -99.0) != -99.0])
    df_filtered = pd.DataFrame([r for r in raw_results if r.get("Alpha_Edge", -99.0) == -99.0])
    
    # Portfolio Group: Extract exactly the Top 10 rows by Simulated True Probability
    rank_prob = df_active.sort_values(by="P_WPI", ascending=False).head(10).copy()
    rank_prob["Optimization_Category"] = "TOP_10_PROBABILITY"

    # Concatenate streamlined arrays together
    final_df = pd.concat([rank_prob, df_filtered], ignore_index=True)
    
    if not final_df.empty:
        final_df["P_WPI"] = final_df.apply(lambda r: f"{r['P_WPI']*100:.1f}%" if r["Alpha_Edge"] != -99.0 else "FILTERED", axis=1)
        final_df["P_Market"] = final_df.apply(lambda r: f"{r['P_Market']*100:.1f}%" if r["Alpha_Edge"] != -99.0 else "FILTERED", axis=1)
        final_df["Alpha_Edge"] = final_df.apply(lambda r: f"{r['Alpha_Edge']*100:+.1f}%" if r["Alpha_Edge"] != -99.0 else "BLOCKED", axis=1)

        # 💾 PERSISTENT APPEND EXPORT MODULE (mode='a')
        output_file = "alpha_market_matrix.csv"
        file_exists = os.path.isfile(output_file)
        
        final_df.to_csv(output_file, mode='a', index=False, header=not file_exists)
        print(f"📊 SUCCESS! Appended {len(final_df)} plain text data rows cleanly to '{output_file}'.")
    else:
        print("⚠️ Pipeline alert: Calculated matrix returned empty. Data append skipped.")

if __name__ == "__main__":
    run_cloud_pipeline()
