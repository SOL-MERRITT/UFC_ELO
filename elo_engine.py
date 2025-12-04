import pandas as pd

class EloRatingSystem:
    def __init__(self, default_elo=1500, k_factor=40, finish_multiplier=1.25):
        self.default_elo = default_elo
        self.k_factor = k_factor
        self.finish_multiplier = finish_multiplier
        self.ratings = {}       # Current rating: {fighter_name: elo}
        self.peak_ratings = {}  # Peak rating: {fighter_name: max_elo}

    def _get_rating(self, fighter_name):
        return self.ratings.get(fighter_name, self.default_elo)

    def _update_peak(self, fighter_name, new_elo):
        current_peak = self.peak_ratings.get(fighter_name, self.default_elo)
        if new_elo > current_peak:
            self.peak_ratings[fighter_name] = new_elo
        # Ensure we track peak even if it's the first rating
        if fighter_name not in self.peak_ratings:
             self.peak_ratings[fighter_name] = max(new_elo, self.default_elo)

    def _expected_score(self, rating_a, rating_b):
        """
        Calculate the expected score for fighter A against fighter B.
        Formula: 1 / (1 + 10 ^ ((Rb - Ra) / 400))
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(self, winner, loser, method):
        """
        Update ratings for a win/loss result.
        """
        rating_w = self._get_rating(winner)
        rating_l = self._get_rating(loser)
        
        expected_w = self._expected_score(rating_w, rating_l)
        
        # Apply multiplier for finishes
        multiplier = 1.0
        # Normalize method string slightly to catch variations if needed, 
        # but caller should pass standard "KO/TKO", "SUB" etc.
        if method in ["KO/TKO", "SUB"]:
            multiplier = self.finish_multiplier
        
        # Calculate delta
        delta = self.k_factor * multiplier * (1 - expected_w)
        
        new_rating_w = round(rating_w + delta, 2)
        new_rating_l = round(rating_l - delta, 2)
        
        self.ratings[winner] = new_rating_w
        self.ratings[loser] = new_rating_l
        
        self._update_peak(winner, new_rating_w)
        self._update_peak(loser, new_rating_l)
        
        return new_rating_w, new_rating_l

    def handle_draw(self, fighter_a, fighter_b):
        """
        Update ratings for a draw.
        """
        rating_a = self._get_rating(fighter_a)
        rating_b = self._get_rating(fighter_b)
        
        expected_a = self._expected_score(rating_a, rating_b)
        
        # In a draw, actual score is 0.5
        # K-factor is typically halved or reduced for draws, but logic from previous script:
        # k = K_FACTOR * 0.5
        k = self.k_factor * 0.5
        
        delta_a = k * (0.5 - expected_a)
        # delta_b will be -delta_a symmetric
        
        new_rating_a = round(rating_a + delta_a, 2)
        new_rating_b = round(rating_b - delta_a, 2) # symmetric update
        
        self.ratings[fighter_a] = new_rating_a
        self.ratings[fighter_b] = new_rating_b
        
        self._update_peak(fighter_a, new_rating_a)
        self._update_peak(fighter_b, new_rating_b)

        return new_rating_a, new_rating_b

    def process_fights(self, fights_df: pd.DataFrame):
        """
        Iterate through the DataFrame chronologically and calculate ELOs.
        Returns the DataFrame with added ELO columns.
        """
        # Ensure date exists and sort
        if "event_date" in fights_df.columns:
            fights_df["event_date"] = pd.to_datetime(fights_df["event_date"], errors="coerce")
            fights_df = fights_df.sort_values(by=["event_date"], ascending=True)
        
        # Initialize columns
        fights_df["f1_elo_start"] = 0.0
        fights_df["f2_elo_start"] = 0.0
        fights_df["f1_elo_end"] = 0.0
        fights_df["f2_elo_end"] = 0.0

        # Iterate
        for index, row in fights_df.iterrows():
            f1 = row["fighter_1"]
            f2 = row["fighter_2"]
            result = str(row["result"]).lower().strip() if pd.notnull(row["result"]) else ""
            method = row.get("method", "")
            
            # Helper to normalize method if needed, based on old script
            # (The scraper produces consistent "KO/TKO", "SUB" usually, but let's be safe)
            
            # Get start ratings
            start_elo_f1 = self._get_rating(f1)
            start_elo_f2 = self._get_rating(f2)
            
            fights_df.at[index, "f1_elo_start"] = start_elo_f1
            fights_df.at[index, "f2_elo_start"] = start_elo_f2
            
            if result == "nc":
                # No Change
                fights_df.at[index, "f1_elo_end"] = start_elo_f1
                fights_df.at[index, "f2_elo_end"] = start_elo_f2
                continue
                
            if result == "draw":
                self.handle_draw(f1, f2)
            elif result == "win":
                # f1 won
                self.update_ratings(f1, f2, method)
            else:
                # Assume loss means f2 won (if result isn't win/draw/nc)
                # But wait, old script: winner = fighter_1 if result == "win" else fighter_2
                # If result is 'loss' for f1, then f2 is winner?
                # The scraper usually puts 'win' for the winner row? 
                # Wait, scraper output is per fight. 
                # Let's look at row structure: fighter_1, fighter_2, result. 
                # If result says 'win', it means fighter_1 won. 
                # If result says 'loss', it would be incorrect for this structure usually, 
                # typically we structure it so fighter_1 is the winner or we check who won.
                # In the old script: "winner = fighter_1 if result == 'win' else fighter_2"
                # This implies if result != 'win', fighter_2 won.
                winner = f1 if result == "win" else f2
                loser = f2 if result == "win" else f1
                self.update_ratings(winner, loser, method)
            
            # Record end ratings
            fights_df.at[index, "f1_elo_end"] = self.ratings[f1]
            fights_df.at[index, "f2_elo_end"] = self.ratings[f2]

        return fights_df

    def get_rankings(self):
        """
        Return a DataFrame of current rankings.
        """
        data = []
        for fighter, rating in self.ratings.items():
            data.append({
                "Fighter": fighter,
                "Final ELO": rating,
                "Peak ELO": self.peak_ratings.get(fighter, rating)
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values("Final ELO", ascending=False).reset_index(drop=True)
        return df

