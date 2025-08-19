import streamlit as st
import pandas as pd

import pandas as pd

class PlayerBattingStatistics:
    def __init__(self, name, ab=0, runs=0, singles=0, doubles=0, triples=0, hr=0, rbi=0, bb=0, so=0):
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
    def obp(self):
        pa = self.ab + self.bb
        return round((self.hits + self.bb) / pa, 3) if pa > 0 else 0.0

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
            "SO": self.so,
            "AVG": self.avg,
            "OBP": self.obp,
            "SLG": self.slg,
            "OPS": self.ops,
            "ISO": self.iso,
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
            totals = df_wo_totals[["AB","H","1B","2B","3B","HR","R","RBI","BB","SO"]].sum()
            team_player = PlayerBattingStatistics(
                "TEAM TOTAL",
                ab=int(totals["AB"]),
                singles=int(totals["1B"]),
                doubles=int(totals["2B"]),
                triples=int(totals["3B"]),
                hr=int(totals["HR"]),
                rbi=int(totals["RBI"]),
                runs=int(totals["R"]),
                bb=int(totals["BB"]),
                so=int(totals["SO"]),
            )
            totals_row = team_player.to_dict()
            df_totals = pd.DataFrame([totals_row])
            
        df_wo_totals = df_wo_totals[["Player","AB","H","HR","R","RBI","BB","SO","AVG", "OBP", "SLG", "OPS", "ISO"]]
        df_totals = df_totals[["Player","AB","H","HR","R","RBI","BB","SO","AVG", "OBP", "SLG", "OPS", "ISO"]]
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
st.set_page_config(layout="wide")
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
    
    # Load per-game CSV
    df_games = pd.read_csv("game_stats.csv")
    
    # Aggregate season totals per player
    df_totals = df_games.groupby("Player", as_index=False).sum()

    # Build team from totals
    team = TeamBattingStatistics("Sharks")
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
            so=row["SO"]
        )
        team.add_player(player)

    # Convert to DataFrame (ready for Streamlit)
    df_season, df_season_totals = team.to_dataframe(include_totals=True)

    st.subheader("Season Totals")
    st.dataframe(df_season, use_container_width=True, hide_index=True)
    st.dataframe(df_season_totals, use_container_width=True, hide_index=True)

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

        st.subheader(f"{selected_player} - Per Game Stats")
        st.dataframe(df_player_games, use_container_width=True, hide_index=True)


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