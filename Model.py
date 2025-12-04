import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression # New import
from sklearn.ensemble import RandomForestClassifier # We'll bring this back for comparison
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier # New import
from sklearn.metrics import accuracy_score, classification_report
from collections import defaultdict, deque

# (All helper and feature engineering functions remain the same as the previous script)
def balance_data(df):
    print("Balancing the dataset...")
    f1_cols = [col for col in df.columns if col.startswith('f1') or col.startswith('fighter_1')]
    f2_cols = [col for col in df.columns if col.startswith('f2') or col.startswith('fighter_2')]
    rows_to_swap = np.random.rand(len(df)) > 0.5
    f1_data_to_swap = df.loc[rows_to_swap, f1_cols].copy(); f2_data_to_swap = df.loc[rows_to_swap, f2_cols].copy()
    df.loc[rows_to_swap, f1_cols] = f2_data_to_swap.values; df.loc[rows_to_swap, f2_cols] = f1_data_to_swap.values
    df.loc[rows_to_swap, 'result'] = df.loc[rows_to_swap, 'result'].apply(lambda x: 'loss' if x == 'win' else 'win')
    return df

def get_total_seconds(row):
    try:
        time_parts = str(row['time']).split(':'); minutes, seconds = int(time_parts[0]), int(time_parts[1])
        return ((row['round'] - 1) * 300) + (minutes * 60 + seconds)
    except: return 0

def create_combined_features(fight_file='ufc_fights_detailed_with_elo.csv', fighter_details_file='ufc_fighter_details.csv', form_window=3):
    print("Loading data and starting combined feature engineering...")
    df_fights = pd.read_csv(fight_file); df_fighter_details = pd.read_csv(fighter_details_file)
    df_fights = pd.merge(df_fights, df_fighter_details, left_on='fighter_1', right_on='full_name', how='left')
    df_fights.rename(columns={'height_inches': 'f1_height', 'reach_inches': 'f1_reach', 'stance': 'f1_stance'}, inplace=True)
    df_fights.drop('full_name', axis=1, inplace=True)
    df_fights = pd.merge(df_fights, df_fighter_details, left_on='fighter_2', right_on='full_name', how='left')
    df_fights.rename(columns={'height_inches': 'f2_height', 'reach_inches': 'f2_reach', 'stance': 'f2_stance'}, inplace=True)
    df_fights.drop('full_name', axis=1, inplace=True)
    df_fights = balance_data(df_fights)
    df_fights['event_date'] = pd.to_datetime(df_fights['event_date'])
    df_fights = df_fights.sort_values(by='event_date').reset_index(drop=True)
    df_fights['total_fight_seconds'] = df_fights.apply(get_total_seconds, axis=1)
    fighter_stats = defaultdict(lambda: {'fight_count': 0, 'wins': 0, 'ko_wins': 0, 'sub_wins': 0, 'total_fight_seconds': 0,
                                         'sig_str_landed': 0, 'sig_str_attempted': 0, 'td_landed': 0, 'td_attempted': 0, 'kd': 0,
                                         'recent_fights': deque(maxlen=form_window)})
    processed_fights = []
    for index, row in df_fights.iterrows():
        f1_name, f2_name = row['fighter_1'], row['fighter_2']; f1_hist, f2_hist = fighter_stats[f1_name], fighter_stats[f2_name]
        fight_features = {}; epsilon = 1e-6
        for prefix, hist in [('f1', f1_hist), ('f2', f2_hist)]:
            fight_features[f'{prefix}_win_pct'] = hist['wins'] / (hist['fight_count'] + epsilon)
            fight_features[f'{prefix}_ko_rate'] = hist['ko_wins'] / (hist['wins'] + epsilon)
            fight_features[f'{prefix}_sub_rate'] = hist['sub_wins'] / (hist['wins'] + epsilon)
            fight_features[f'{prefix}_avg_duration'] = hist['total_fight_seconds'] / (hist['fight_count'] + epsilon)
            fight_features[f'{prefix}_sig_str_landed_pm'] = (hist['sig_str_landed'] * 60) / (hist['total_fight_seconds'] + epsilon)
            fight_features[f'{prefix}_sig_str_accuracy'] = hist['sig_str_landed'] / (hist['sig_str_attempted'] + epsilon)
            fight_features[f'{prefix}_td_landed_pm'] = (hist['td_landed'] * 60) / (hist['total_fight_seconds'] + epsilon)
            fight_features[f'{prefix}_td_accuracy'] = hist['td_landed'] / (hist['td_attempted'] + epsilon)
            recent_fights = list(hist['recent_fights'])
            fight_features[f'{prefix}_form_win_pct'] = np.mean([f['win'] for f in recent_fights]) if recent_fights else 0.0
            fight_features[f'{prefix}_form_kd'] = np.mean([f['kd'] for f in recent_fights]) if recent_fights else 0.0
        fight_features.update({k: row[k] for k in ['f1_height', 'f1_reach', 'f1_stance', 'f2_height', 'f2_reach', 'f2_stance',
                                                    'fighter_1_elo_start', 'fighter_2_elo_start']})
        fight_features['fighter_1_wins'] = 1 if row['result'] == 'win' else 0
        processed_fights.append(fight_features)
        for prefix, hist in [('f1', f1_hist), ('f2', f2_hist)]:
            is_f1 = (prefix == 'f1')
            win = 1 if (is_f1 and row['result'] == 'win') or (not is_f1 and row['result'] == 'loss') else 0
            kd, sig_str_landed, sig_str_attempted, td_landed, td_attempted = (row[f'{prefix}_kd'], row[f'{prefix}_sig_str_landed'],
                                                                             row[f'{prefix}_sig_str_attempted'], row[f'{prefix}_td_landed'], row[f'{prefix}_td_attempted'])
            hist['fight_count'] += 1; hist['total_fight_seconds'] += row['total_fight_seconds']
            if win: hist['wins'] += 1; hist['ko_wins'] += 1 if 'KO' in row['method'] else 0; hist['sub_wins'] += 1 if 'SUB' in row['method'] else 0
            hist.update({'kd': hist['kd'] + kd, 'sig_str_landed': hist['sig_str_landed'] + sig_str_landed, 'sig_str_attempted': hist['sig_str_attempted'] + sig_str_attempted,
                         'td_landed': hist['td_landed'] + td_landed, 'td_attempted': hist['td_attempted'] + td_attempted})
            hist['recent_fights'].append({'win': win, 'kd': kd})
    feature_df = pd.DataFrame(processed_fights)
    print("Calculating final differential features...")
    for col in ['win_pct', 'ko_rate', 'sub_rate', 'avg_duration', 'sig_str_landed_pm', 'sig_str_accuracy', 'td_landed_pm', 'td_accuracy', 'form_win_pct', 'form_kd', 'height', 'reach']:
        feature_df[f'{col}_diff'] = feature_df[f'f1_{col}'] - feature_df[f'f2_{col}']
    feature_df['elo_diff'] = feature_df['fighter_1_elo_start'] - feature_df['fighter_2_elo_start']
    feature_df['stance_clash'] = (feature_df['f1_stance'] != feature_df['f2_stance']).astype(int)
    cols_to_drop = [col for col in feature_df.columns if col.startswith(('f1_', 'f2_'))]
    feature_df.drop(columns=cols_to_drop, inplace=True)
    print("Feature engineering complete.")
    return feature_df.fillna(0)


def train_and_evaluate_models(feature_df):
    """
    Trains and evaluates a suite of different models.
    """
    target = 'fighter_1_wins'; features = [col for col in feature_df.columns if col != target]
    X = feature_df[features]; y = feature_df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    print(f"\nTraining with {len(features)} features.")

    # Define all models to be tested
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=150, random_state=42),
        "LightGBM": LGBMClassifier(random_state=42),
        "XGBoost": XGBClassifier(n_estimators=150, random_state=42, use_label_encoder=False, eval_metric='logloss')
    }

    # Loop through each model, train it, and print its evaluation
    for name, model in models.items():
        print(f"\n--- Training {name} ---")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        print(classification_report(y_test, y_pred))

if __name__ == '__main__':
    final_featured_data = create_combined_features()
    train_and_evaluate_models(final_featured_data)