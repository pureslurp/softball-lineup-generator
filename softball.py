import streamlit as st

# Original team data
players_info = {
    "Kevo": {"prefs": ["P", "SS"]},
    "Werth": {"prefs": [], "no": ["P", "3B"]},
    "JD": {"prefs": ["3B", "SS"]},
    "Andrew": {"prefs": []},
    "Raymor": {"prefs": [], "no": ["3B", "P"]},  # versatile but no 3B or P
    "Balavich": {"prefs": ["OF"]},
    "Dave": {"prefs": []},
    "KBoe": {"prefs": [], "no": ["2B", "SS", "3B"]},
    "Stross": {"prefs": ["2B", "SS", "OF"], "no": ["P"]},
    "Damion": {"prefs": ["1B"], "no": ["P", "3B", "SS", "2B", "OF", "C"]},
    "Mike Mac": {"prefs": ["RCF"]},
    "JG": {"prefs": ["P","OF"]},
}

positions = [
    "P", "C", "1B", "2B", "SS", "3B",
    "LF", "LCF", "RCF", "RF"
]

infield_positions = {"P", "C", "1B", "2B", "SS", "3B"}
outfield_positions = {"LF", "LCF", "RCF", "RF"}

# Outfield position importance (higher = more action)
outfield_importance = {
    "LCF": 4,  # Most action
    "RCF": 3,  # Second most action
    "LF": 2,   # Third most action
    "RF": 1    # Least action
}

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
    "Mike Mac": 3,
    "Dave": 4,
    "Werth": 8,
    "Andrew": 2,
    "JG": 1,
}

st.title("Softball Lineup Generator")

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

if len(available_players) < len(positions):
    st.error(f"Not enough players available! You have {len(available_players)} but need {len(positions)} starters.")
    st.stop()

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


    

st.header("Starting Lineup")
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
