import operator
import streamlit as st
import pandas as pd

import pandas as pd

class PlayerBattingStatistics:
    def __init__(self, name, ab=0, runs=0, singles=0, doubles=0, triples=0, hr=0, rbi=0, bb=0, so=0, sf=0, ab_risp=0, h_risp=0):
        self.name = name
        self.ab = ab
        self.runs = runs
        self.singles = singles
        self.doubles = doubles
        self.triples = triples
        self.hr = hr
        self.rbi = rbi
        self.bb = bb
        self.so = so
        self.sf = sf
        self.ab_risp = ab_risp
        self.h_risp = h_risp

    # --- Derived Counts ---
    @property
    def hits(self):
        return self.singles + self.doubles + self.triples + self.hr

    @property
    def total_bases(self):
        return (self.singles
                + 2 * self.doubles
                + 3 * self.triples
                + 4 * self.hr)

    # --- Basic Stats ---
    @property
    def avg(self):
        return round(self.hits / self.ab, 3) if self.ab > 0 else 0.0

    # --- Advanced Stats ---
    @property
    def pa(self):
        return self.ab + self.bb + self.sf

    @property
    def obp(self):
        return round((self.hits + self.bb) / self.pa, 3) if self.pa > 0 else 0.0

    @property
    def ba_risp(self):
        if self.h_risp > self.hits:
            print(f"{self.name} has {self.h_risp} RISP hits but only {self.hits} hits")
        return round(self.h_risp / self.ab_risp, 3) if self.ab_risp > 0 else 0.0

    @property
    def slg(self):
        return round(self.total_bases / self.ab, 3) if self.ab > 0 else 0.0

    @property
    def ops(self):
        return round(self.obp + self.slg, 3)

    @property
    def iso(self):
        """Isolated Power = SLG - AVG"""
        return round(self.slg - self.avg, 3)

    def to_dict(self):
        return {
            "Player": self.name,
            "AB": self.ab,
            "H": self.hits,
            "1B": self.singles,
            "2B": self.doubles,
            "3B": self.triples,
            "HR": self.hr,
            "R": self.runs,
            "RBI": self.rbi,
            "BB": self.bb,
            "AVG": self.avg,
            "OBP": self.obp,
            "SLG": self.slg,
            "OPS": self.ops,
            "ISO": self.iso,
            "SO": self.so,
            "SF": self.sf,
            "BA_RISP": self.ba_risp,
            "AB_RISP": self.ab_risp,
            "H_RISP": self.h_risp
        }


class TeamBattingStatistics:
    def __init__(self, team_name):
        self.team_name = team_name
        self.players = {}

    def add_player(self, player: PlayerBattingStatistics):
        self.players[player.name] = player

    def to_dataframe(self, include_totals=False):
        df_wo_totals = pd.DataFrame([p.to_dict() for p in self.players.values()])
        

        if include_totals and not df_wo_totals.empty:
            totals = df_wo_totals[["AB","H","1B","2B","3B","HR","R","RBI","BB","SO","SF","AB_RISP","H_RISP"]].sum()
            team_player = PlayerBattingStatistics(
                "TOTAL",
                ab=int(totals["AB"]),
                singles=int(totals["1B"]),
                doubles=int(totals["2B"]),
                triples=int(totals["3B"]),
                hr=int(totals["HR"]),
                rbi=int(totals["RBI"]),
                runs=int(totals["R"]),
                bb=int(totals["BB"]),
                so=int(totals["SO"]),
                sf=int(totals["SF"]),
                ab_risp=int(totals["AB_RISP"]),
                h_risp=int(totals["H_RISP"])
            )
            totals_row = team_player.to_dict()
            df_totals = pd.DataFrame([totals_row])
            
        df_wo_totals = df_wo_totals[["Player","AB","H","HR","R","RBI","BB","SO","SF","AVG","OBP", "SLG", "OPS", "BA_RISP", "ISO"]]
        df_totals = df_totals[["Player","AB","H","HR","R","RBI","BB","SO","SF","AVG", "OBP", "SLG", "OPS", "BA_RISP", "ISO"]]
        return df_wo_totals, df_totals




def player_can_play_pos(player, pos):
    p = all_players_info[player]
    prefs = p.get("prefs", [])
    no_positions = p.get("no", [])
    
    # If position is in their "no" list, they can't play it
    if pos in no_positions:
        return False
    
    # If they have specific preferences, check if position is in their prefs
    if prefs:
        if pos in prefs:
            return True
        if "IF" in prefs and pos in infield_positions:
            return True
        if "OF" in prefs and pos in outfield_positions:
            return True
        return False
    
    # If they have no preferences (empty list), they can play any position except those in "no"
    return True

def get_position_importance(pos):
    """Get the importance score for a position (higher = more important)"""
    if pos in outfield_importance:
        return outfield_importance[pos]
    elif pos in infield_importance:
        return infield_importance[pos]
    return 1  # Default importance

def candidate_score(player, position):
    """
    Score a candidate for a position based on the priority order:
    1. Player's preferred position (highest priority)
    2. Athleticism × Position importance (second priority)
    """
    prefs = all_players_info[player].get("prefs", [])
    ath_score = athleticism_rank.get(player, 0)
    pos_importance = get_position_importance(position)
    
    # Priority 1: Player's preferred position (highest weight)
    preference_bonus = 1000 if position in prefs else 0
    
    # Priority 2: Athleticism × Position importance (medium weight)
    # This ensures more athletic players get more important positions
    athleticism_importance_score = ath_score * pos_importance * 50
    
    return preference_bonus + athleticism_importance_score

def prioritized_candidates(candidates, position=None):
    if not candidates:
        return []
    
    # Sort by the new scoring system
    return sorted(candidates, key=lambda p: candidate_score(p, position), reverse=True)

def optimize_lineup():
    """
    Optimize the lineup using a global optimization approach:
    1. Find all valid assignments for each position
    2. Calculate the total score for each possible lineup
    3. Return the lineup with the highest total score
    
    This ensures we get the globally optimal assignment rather than greedy local decisions.
    """
    def calculate_lineup_score(assignment):
        """Calculate the total score for a lineup assignment"""
        total_score = 0
        for pos, player in assignment.items():
            total_score += candidate_score(player, pos)
        return total_score
    
    def find_best_lineup():
        """Find the best lineup using a greedy approach with backtracking"""
        best_score = -1
        best_assignment = None
        
        def backtrack_optimize(available_players, current_assignment, pos_index):
            nonlocal best_score, best_assignment
            
            if pos_index == len(positions):
                # Complete assignment found
                score = calculate_lineup_score(current_assignment)
                if score > best_score:
                    best_score = score
                    best_assignment = current_assignment.copy()
                return
            
            pos = positions[pos_index]
            candidates = [p for p in available_players if player_can_play_pos(p, pos)]
            
            # Sort candidates by their score for this position
            sorted_candidates = prioritized_candidates(candidates, pos)
            
            for candidate in sorted_candidates:
                new_available = available_players - {candidate}
                current_assignment[pos] = candidate
                backtrack_optimize(new_available, current_assignment, pos_index + 1)
                del current_assignment[pos]
        
        backtrack_optimize(set(available_players), {}, 0)
        return best_assignment
    
    return find_best_lineup()

def optimize_team_athleticism(assignments):
    """
    Post-optimization: Try to improve team athleticism by swapping players
    while respecting preferences and maintaining valid assignments
    """
    improved = True
    while improved:
        improved = False
        
        for pos1 in positions:
            for pos2 in positions:
                if pos1 >= pos2:
                    continue
                    
                player1 = assignments[pos1]
                player2 = assignments[pos2]
                
                # Check if both players can play each other's positions
                if not (player_can_play_pos(player1, pos2) and player_can_play_pos(player2, pos1)):
                    continue
                
                # Calculate current and potential scores
                current_score = (athleticism_rank.get(player1, 0) * get_position_importance(pos1) + 
                               athleticism_rank.get(player2, 0) * get_position_importance(pos2))
                
                potential_score = (athleticism_rank.get(player1, 0) * get_position_importance(pos2) + 
                                 athleticism_rank.get(player2, 0) * get_position_importance(pos1))
                
                # Only swap if it improves athleticism × importance AND doesn't violate strong preferences
                if potential_score > current_score:
                    # Check if either player strongly prefers their current position
                    prefs1 = all_players_info[player1].get("prefs", [])
                    prefs2 = all_players_info[player2].get("prefs", [])
                    
                    # Don't swap if it would move a player away from their preferred position
                    if (pos1 in prefs1 and pos2 not in prefs1) or (pos2 in prefs2 and pos1 not in prefs2):
                        continue
                    
                    # Perform the swap
                    assignments[pos1] = player2
                    assignments[pos2] = player1
                    improved = True
                    break
            if improved:
                break
    
    return assignments

def backtrack(assignments, used, pos_idx=0):
    """Fallback backtracking algorithm if the main optimization fails"""
    if pos_idx == len(positions):
        return assignments

    pos = positions[pos_idx]
    candidates = [p for p in available_players if p not in used and player_can_play_pos(p, pos)]

    for player in prioritized_candidates(candidates, pos):
        assignments[pos] = player
        used.add(player)
        result = backtrack(assignments, used, pos_idx + 1)
        if result is not None:
            return result
        used.remove(player)
        del assignments[pos]

    return None

def optimize_outfield(assignments):
    '''Given the current assignments, optimize the outfield position based on outfield importance and athleticism'''
    #get all outfielders
    outfielders = [v for k, v in assignments.items() if k in outfield_positions]
    
    #sort outfielders by athleticism
    outfielders.sort(key=lambda x: athleticism_rank.get(x, 0), reverse=True)

    # reassign outfielders to the positions in order of athleticism and importance (outfield_importance)
    for pos in outfield_importance:
        player = outfielders.pop(0)
        assignments[pos] = player
    return assignments

def calculate_optimal_batting_order(stats: TeamBattingStatistics, omit: list[str] = [""]):
    '''Given the current hitting stats, return the optimal batting lineup
    Philosophy:
    Top of the order (1–3): Need high OBP and speed/athleticism — guys who get on base to set the table.
    Middle (3–5): Best power hitters/sluggers — drive runs in.
    Lower/middle (6–8): Consistent contact hitters — keep rallies alive.
    Bottom (9–10): Weaker hitters, but ideally people who can still get on base and "turn the lineup over" back to the top.
    '''
    players = list(stats.players.values())
    for player in players:
        if player.name.strip() in omit:
            players.remove(player)
    lineup = []
    
    # 1. Leadoff hitter: Top 3 OBP players, then lowest SLG among them
    top_obp_players = sorted(players, key=operator.attrgetter('obp'), reverse=True)[:3]
    leadoff_candidates = sorted(top_obp_players, key=operator.attrgetter('slg'))
    lineup.append(leadoff_candidates[0])  # Lowest SLG among top 3 OBP
    
    # 2. Second hitter: Top 3 AVG players (excluding leadoff), then lowest SLG among them
    remaining_players = [p for p in players if p not in lineup]
    top_avg_players = sorted(remaining_players, key=operator.attrgetter('avg'), reverse=True)[:3]
    second_candidates = sorted(top_avg_players, key=operator.attrgetter('slg'))
    lineup.append(second_candidates[0])  # Lowest SLG among top 3 AVG
    
    # 3-4. Third and cleanup hitters: Top 2 SLG players among remaining
    remaining_players = [p for p in players if p not in lineup]
    top_slg_players = sorted(remaining_players, key=operator.attrgetter('slg'), reverse=True)
    lineup.extend([top_slg_players[1], top_slg_players[0]])  # 2nd and 1st SLG
    
    # 5-8. Middle order: Remaining players by SLG (excluding last batter)
    remaining_players = [p for p in players if p not in lineup]
    last_batter = max(remaining_players, key=operator.attrgetter('obp'))  # Highest OBP for "turnover"
    middle_order = [p for p in sorted(remaining_players, key=operator.attrgetter('slg'), reverse=True) if p != last_batter]
    lineup.extend(middle_order)
    
    # 9. Last batter: Highest OBP to "turn the lineup over"
    lineup.append(last_batter)
    
    # Create DataFrame with proper indexing
    return pd.DataFrame(lineup, index=range(1, len(lineup) + 1), columns=["Player"]).rename_axis("Batting Position")

def extract_name(x):
    return x.name
    
def display_lineup_rationale(lineup):
    st.subheader("Lineup Rationale")

    # --- 1. Leadoff Hitter ---
    player = lineup.iloc[0,0]
    with st.expander(f"1. {player.name} (Leadoff Hitter)"):
        st.write(f"""
        Chosen from the **top 3 players in OBP**, but with the *lowest slugging percentage (SLG)* 
        among that group. This ensures {player.name} is someone who gets on base often 
        to start rallies, while leaving the big power bats for later.
        
        **Stats:** AVG {player.avg}, OBP {player.obp}, SLG {player.slg}
        """)
    

    # --- 2. Second Hitter ---
    player = lineup.iloc[1,0]
    with st.expander(f"2. {player.name} (Second Hitter)"):
        st.write(f"""
        Selected from the **top 3 players in batting average (AVG)** (excluding the leadoff), 
        and then the one with the *lowest slugging percentage (SLG)* is placed second.  
        This makes {player.name} a reliable contact hitter who moves runners along, 
        but doesn’t take away power slots.
        
        **Stats:** AVG {player.avg}, OBP {player.obp}, SLG {player.slg}
        """)

    # --- 3. Third Hitter ---
    player = lineup.iloc[2,0]
    with st.expander(f"3. {player.name} (Third Hitter)"):
        st.write(f"""
        Among the remaining players, sorted by slugging percentage (SLG), 
        the **second-highest slugger** is chosen for the #3 spot.  
        {player.name} provides both power and consistency, often batting in the 
        first inning with runners already on base.
        
        **Stats:** AVG {player.avg}, OBP {player.obp}, SLG {player.slg}
        """)

    # --- 4. Cleanup Hitter ---
    player = lineup.iloc[3,0]
    with st.expander(f"4. {player.name} (Cleanup Hitter)"):
        st.write(f"""
        The **highest slugging percentage (SLG)** among the remaining players 
        is placed here. {player.name} is the biggest power threat in the lineup, 
        tasked with driving in the top-of-the-order hitters.
        
        **Stats:** AVG {player.avg}, OBP {player.obp}, SLG {player.slg}
        """)

    # --- 5–8. Middle / Lower Order ---
    with st.expander(f"5–{len(lineup)-1}. Middle / Lower Order"):
        st.write("""
        After the first four spots are filled, the rest of the players are ordered 
        by slugging percentage (SLG). These are consistent contact hitters who can 
        keep innings alive, drive in runs, and set up chances for more runs.
        """)
        for i in range(4, len(lineup)-1):
            player = lineup.iloc[i,0]
            st.write(f"- **{i+1}. {player.name}** — AVG {player.avg}, OBP {player.obp}, SLG {player.slg}")

    # --- 9. Bottom of the Order ---
    player = lineup.iloc[-1,0]
    with st.expander(f"9. {player.name} (Bottom of the Order)"):
        st.write(f"""
        The last hitter is intentionally chosen — not the weakest bat.  
        From the remaining pool, the player with the **highest OBP** is placed last.  
        This ensures {player.name} can “turn the lineup over” by getting on base, 
        giving the top hitters more RBI opportunities.
        
        **Stats:** AVG {player.avg}, OBP {player.obp}, SLG {player.slg}
        """)




# st.set_page_config(layout="wide")
st.title("Freebasers Softball")
tab_choice = st.selectbox("Select Page", ["Hitting", "Fielding"])
# tab1, tab2 = st.tabs(["Fielding", "Hitting"])
# Original team data
players_info = {
    "Kevo": {"prefs": ["SS"]},
    "Werth": {"prefs": [], "no": ["P", "3B"]},
    "JD": {"prefs": ["3B", "SS"]},
    "Andrew": {"prefs": ["C", "RF"]},
    "Raymor": {"prefs": [], "no": ["3B", "P"]},  # versatile but no 3B or P
    "Balavich": {"prefs": ["OF"]},
    "Dave": {"prefs": []},
    "KBoe": {"prefs": [], "no": ["2B", "SS", "3B"]},
    "Stross": {"prefs": ["2B", "SS", "OF"], "no": ["P"]},
    "Damion": {"prefs": ["1B"], "no": ["P", "3B", "SS", "2B", "OF", "C"]},
    "Uncle Rich": {"prefs": ["P"]},
    "JG": {"prefs": ["P","OF"]},
}

infield_positions = ["P", "C", "1B", "2B", "SS", "3B"]
outfield_positions = ["LF", "LCF", "RCF", "RF"]

# Outfield position importance (higher = more action)
outfield_importance = {
    "LCF": 4,  # Most action
    "RCF": 2,  # Second most action
    "LF": 3,   # Third most action
    "RF": 1    # Least action
}

nine_players = False

# Infield position importance (higher = more action)
infield_importance = {
    "P": 2,
    "C": 1,
    "1B": 3,
    "2B": 4,
    "SS": 6,
    "3B": 5,
}

default_athleticism = {
    "Balavich": 10,
    "JD": 9,
    "KBoe": 6,
    "Raymor": 4,
    "Kevo": 6,
    "Stross": 7,
    "Damion": 6,
    "Uncle Rich": 3,
    "Dave": 4,
    "Werth": 8,
    "Andrew": 2,
    "JG": 1,
}

if tab_choice == "Hitting":
    st.header("Hitting Stats")
    season = st.selectbox("Select Season", ["Fall2025"])
    
    # Load per-game CSV
    df_games = pd.read_csv("game_stats.csv")
    df_games = df_games[df_games["Season"] == season]
    
    # Aggregate season totals per player
    df_totals = df_games.groupby("Player", as_index=False).sum()

    # Build team from totals
    team = TeamBattingStatistics("Freebasers")
    for _, row in df_totals.iterrows():
        player = PlayerBattingStatistics(
            row["Player"],
            ab=row["AB"],
            runs=row["R"],
            singles=row["1B"],
            doubles=row["2B"],
            triples=row["3B"],
            hr=row["HR"],
            rbi=row["RBI"],
            bb=row["BB"],
            so=row["SO"],
            sf=row["SF"],
            ab_risp=row["AB_RISP"],
            h_risp=row["H_RISP"]
        )
        team.add_player(player)

    # Convert to DataFrame (ready for Streamlit)
    df_season, df_season_totals = team.to_dataframe(include_totals=True)

    st.subheader("Season Totals")
    
    # Configure column widths for better display
    column_config = {
        "Player": st.column_config.TextColumn("Player", width="small"),
        "AB": st.column_config.NumberColumn("AB", width=50),
        "H": st.column_config.NumberColumn("H", width=50),
        "HR": st.column_config.NumberColumn("HR", width=50),
        "R": st.column_config.NumberColumn("R", width=50),
        "RBI": st.column_config.NumberColumn("RBI", width=50),
        "BB": st.column_config.NumberColumn("BB", width=50),
        "SO": st.column_config.NumberColumn("SO", width=50),
        "SF": st.column_config.NumberColumn("SF", width=50),
        "AVG": st.column_config.NumberColumn("AVG", format="%.3f", width="small"),
        "OBP": st.column_config.NumberColumn("OBP", format="%.3f", width="small"),
        "SLG": st.column_config.NumberColumn("SLG", format="%.3f", width="small"),
        "OPS": st.column_config.NumberColumn("OPS", format="%.3f", width="small"),
        "BA_RISP": st.column_config.NumberColumn("BA_RISP", format="%.3f", width="small"),
        "ISO": st.column_config.NumberColumn("ISO", format="%.3f", width="small"),
    }
    
    st.dataframe(
        df_season.sort_values(by="AVG", ascending=False), 
        column_config=column_config,
        use_container_width=True, 
        hide_index=True
    )
    st.dataframe(
        df_season_totals, 
        column_config=column_config,
        use_container_width=True, 
        hide_index=True
    )

    # Read the original game_stats.csv file for export
    with open("game_stats.csv", "r") as file:
        csv_data = file.read()
    
    st.download_button(
        label="📊 Download game_stats.csv",
        data=csv_data,
        file_name="game_stats.csv",
        mime="text/csv",
        help="Download the complete game statistics data as a CSV file"
    )
    
    # --- Per Game Totals Section ---
    st.subheader("Per Game Totals")
    
    # Aggregate team stats per game
    df_game_totals = df_games.groupby("Game", as_index=False).agg({
        "AB": "sum",
        "1B": "sum", 
        "2B": "sum",
        "3B": "sum",
        "HR": "sum",
        "R": "sum",
        "RBI": "sum",
        "BB": "sum",
        "SO": "sum",
        "SF": "sum",
        "AB_RISP": "sum",
        "H_RISP": "sum"
    }).copy()
    
    # Calculate derived stats for each game
    df_game_totals["H"] = df_game_totals["1B"] + df_game_totals["2B"] + df_game_totals["3B"] + df_game_totals["HR"]
    df_game_totals["AVG"] = df_game_totals.apply(
        lambda row: round(row["H"] / row["AB"], 3) if row["AB"] > 0 else 0.0, axis=1
    )
    df_game_totals["OBP"] = df_game_totals.apply(
        lambda row: round((row["H"] + row["BB"]) / (row["AB"] + row["BB"]), 3) if (row["AB"] + row["BB"]) > 0 else 0.0, axis=1
    )
    df_game_totals["SLG"] = df_game_totals.apply(
        lambda row: round((row["1B"] + 2*row["2B"] + 3*row["3B"] + 4*row["HR"]) / row["AB"], 3) if row["AB"] > 0 else 0.0, axis=1
    )
    df_game_totals["OPS"] = df_game_totals["OBP"] + df_game_totals["SLG"]
    df_game_totals["ISO"] = df_game_totals["SLG"] - df_game_totals["AVG"]
    df_game_totals["BA_RISP"] = df_game_totals.apply(
        lambda row: round(row["H_RISP"] / row["AB_RISP"], 3) if row["AB_RISP"] > 0 else 0.0, axis=1
    )
    
    # Reorder columns to match the Season Totals format
    df_game_totals = df_game_totals[["Game", "AB", "H", "HR", "R", "RBI", "BB", "SO", "SF", "AVG", "OBP", "SLG", "OPS", "BA_RISP", "ISO"]]
    
    # Configure column widths for per-game totals
    per_game_totals_column_config = {
        "Game": st.column_config.NumberColumn("Game #", width="small"),
        "AB": st.column_config.NumberColumn("AB", width=50),
        "H": st.column_config.NumberColumn("H", width=50),
        "HR": st.column_config.NumberColumn("HR", width=50),
        "R": st.column_config.NumberColumn("R", width=50),
        "RBI": st.column_config.NumberColumn("RBI", width=50),
        "BB": st.column_config.NumberColumn("BB", width=50),
        "SO": st.column_config.NumberColumn("SO", width=50),
        "SF": st.column_config.NumberColumn("SF", width=50),
        "AVG": st.column_config.NumberColumn("AVG", format="%.3f", width="small"),
        "OBP": st.column_config.NumberColumn("OBP", format="%.3f", width="small"),
        "SLG": st.column_config.NumberColumn("SLG", format="%.3f", width="small"),
        "OPS": st.column_config.NumberColumn("OPS", format="%.3f", width="small"),
        "BA_RISP": st.column_config.NumberColumn("BA_RISP", format="%.3f", width="small"),
        "ISO": st.column_config.NumberColumn("ISO", format="%.3f", width="small"),
    }
    
    st.dataframe(
        df_game_totals, 
        column_config=per_game_totals_column_config,
        use_container_width=True, 
        hide_index=True
    )
    
    st.subheader("Player Per Game Stats")

    # --- Player selection for per-game stats ---
    selected_player = st.selectbox(
        "Select a player to see per-game stats", df_totals["Player"]
    )

    if selected_player:
        df_player_games = df_games[df_games["Player"] == selected_player].copy()
        
        # Calculate per-game derived stats
        df_player_games["H"] = df_player_games["1B"] + df_player_games["2B"] + df_player_games["3B"] + df_player_games["HR"]
        df_player_games["AVG"] = df_player_games.apply(
            lambda row: round(row["H"] / row["AB"], 3) if row["AB"] > 0 else 0.0, axis=1
        )
        df_player_games["OBP"] = df_player_games.apply(
            lambda row: round((row["H"] + row["BB"]) / (row["AB"] + row["BB"]), 3) if (row["AB"] + row["BB"]) > 0 else 0.0, axis=1
        )
        df_player_games["SLG"] = df_player_games.apply(
            lambda row: round((row["1B"] + 2*row["2B"] + 3*row["3B"] + 4*row["HR"]) / row["AB"], 3) if row["AB"] > 0 else 0.0, axis=1
        )
        df_player_games["OPS"] = df_player_games["OBP"] + df_player_games["SLG"]
        df_player_games["ISO"] = df_player_games["SLG"] - df_player_games["AVG"]
        df_player_games = df_player_games.drop('Player', axis=1)

        
        
        # Configure column widths for per-game stats
        per_game_column_config = {
            "Game": st.column_config.NumberColumn("Game", width="small"),
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "AB": st.column_config.NumberColumn("AB", width=50),
            "H": st.column_config.NumberColumn("H", width=50),
            "1B": st.column_config.NumberColumn("1B", width=50),
            "2B": st.column_config.NumberColumn("2B", width=50),
            "3B": st.column_config.NumberColumn("3B", width=50),
            "HR": st.column_config.NumberColumn("HR", width=50),
            "R": st.column_config.NumberColumn("R", width=50),
            "RBI": st.column_config.NumberColumn("RBI", width=50),
            "BB": st.column_config.NumberColumn("BB", width=50),
            "SO": st.column_config.NumberColumn("SO", width=50),
            "AVG": st.column_config.NumberColumn("AVG", format="%.3f", width="small"),
            "OBP": st.column_config.NumberColumn("OBP", format="%.3f", width="small"),
            "SLG": st.column_config.NumberColumn("SLG", format="%.3f", width="small"),
            "OPS": st.column_config.NumberColumn("OPS", format="%.3f", width="small"),
            "BA_RISP": st.column_config.NumberColumn("BA_RISP", format="%.3f", width="small"),
            "ISO": st.column_config.NumberColumn("ISO", format="%.3f", width="small"),
        }
        
        st.dataframe(
            df_player_games, 
            column_config=per_game_column_config,
            use_container_width=True, 
            hide_index=True
        )
    
    st.write("\n\n\n\n\n\n\n")

    st.subheader("Optimal Batting Lineup -- Given Current Stats")
    df = calculate_optimal_batting_order(team)
    display_df = df
    display_df = display_df["Player"].apply(extract_name)
    st.dataframe(display_df)
    display_lineup_rationale(df)


if tab_choice == "Fielding":
    st.header("Lineup Generator")
    # --- Player Availability first ---
    st.sidebar.header("Player Availability")
    availability = {}

    for player in players_info:
        availability[player] = st.sidebar.checkbox(player, value=True)

    # --- Guest entry AFTER availability ---
    st.sidebar.header("Add Guest Players")

    guest_names = []
    guest_prefs = {}
    guest_athleticism = {}

    # Up to 5 guests
    for i in range(1, 6):
        name = st.sidebar.text_input(f"Guest #{i} Name", key=f"guest_name_{i}").strip()
        if name:
            prefs_raw = st.sidebar.text_input(
                f"Guest #{i} Preferred Positions (comma-separated, e.g. 1B,OF)", key=f"guest_prefs_{i}"
            ).upper().replace(" ", "")
            prefs_list = [p for p in prefs_raw.split(",") if p]
            ath = st.sidebar.slider(f"Guest #{i} Athleticism", 1, 10, 5, key=f"guest_ath_{i}")
            guest_names.append(name)
            guest_prefs[name] = prefs_list
            guest_athleticism[name] = ath

    # Combine regular players and guests into one dict
    all_players_info = players_info.copy()
    for guest in guest_names:
        all_players_info[guest] = {"prefs": guest_prefs.get(guest, [])}

    # Combine athleticism info
    athleticism_rank = default_athleticism.copy()
    athleticism_rank.update(guest_athleticism)

    # Guests default to available, add them to availability dict (if not already present)
    for guest in guest_names:
        if guest not in availability:
            availability[guest] = True

    # Filter available players after guests added
    available_players = [p for p, avail in availability.items() if avail]

    if len(available_players) < 10:
        outfield_positions = ["LF", "LCF", "RF"]
        if len(available_players) < 9:
            st.error(f"Not enough players available! You have {len(available_players)} but need 9 starters.")
            st.stop()
    positions = infield_positions + outfield_positions
    

    # Try the new optimization first, fall back to backtracking if needed
    assignments = optimize_lineup()
    if assignments is None:
        # Fall back to the original backtracking approach
        assignments = backtrack({}, set())
        if assignments:
            assignments = optimize_outfield(assignments)

    # Apply team athleticism optimization
    if assignments:
        assignments = optimize_team_athleticism(assignments)

    if assignments is None:
        st.error("No valid lineup found, which should not happen with enough players.")
        st.stop()


        

    st.subheader("Starting Lineup")
    st.table([{ "Position": pos, "Player": player } for pos, player in sorted(assignments.items(), key=lambda x: positions.index(x[0]))])

    # Debug: Show lineup with athleticism and preferences
    if st.checkbox("Show Lineup Details"):
        st.write("Lineup with Athleticism and Preferences:")
        for pos in sorted(assignments.keys(), key=lambda x: positions.index(x)):
            player = assignments[pos]
            ath = athleticism_rank.get(player, 0)
            prefs = all_players_info[player].get("prefs", [])
            st.write(f"{pos}: {player} (Ath: {ath}, Prefs: {prefs})")

    # Debug: Show candidate scores for each position
    if st.checkbox("Show Candidate Scores"):
        st.write("Candidate Scores for Each Position:")
        for pos in positions:
            candidates = [p for p in available_players if player_can_play_pos(p, pos)]
            if candidates:
                st.write(f"\n{pos} candidates:")
                for candidate in candidates:
                    score = candidate_score(candidate, pos)
                    ath = athleticism_rank.get(candidate, 0)
                    prefs = all_players_info[candidate].get("prefs", [])
                    pref_bonus = 1000 if pos in prefs else 0
                    ath_imp_score = ath * get_position_importance(pos) * 50
                    st.write(f"  {candidate}: Score={score} (Pref={pref_bonus}, Ath×Imp={ath_imp_score})")

    subs = [p for p in available_players if p not in assignments.values()]
    st.header("Substitutes / Bench")
    if subs:
        st.write(", ".join(subs))
    else:
        st.write("No subs available.")