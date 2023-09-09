import pandas as pd
import numpy as np
import random
import math
import openpyxl

def clean_ads_data(data):
    ads = pd.read_excel(data, sheet_name='ads dimension (dim table)', header=1)
    mods = pd.read_excel(data, sheet_name='moderator dimension (dim table)', header=0)
    
    ads['punish_num'].fillna(0, inplace=True)
    
    def split_market(entry):
        if pd.notna(entry):
            if '/' in entry:
                return entry.split('/')
            elif '&' in entry:
                return entry.split('&')
            elif entry == 'USCA':
                return ['US', 'CA']
            elif entry == 'MENA':
                return ['ME', 'NA']
            else:
                return [entry]
        else:
            return [entry] 

    ads['queue_market_list'] = ads['queue_market'].apply(split_market)
    ads['queue_market_list'] = ads['queue_market_list'].apply(lambda x: ['Others'] if 'Other' in x else x)

    ads['ad_revenue'].fillna(0, inplace=True)

    mods = mods.dropna(subset=['Productivity', 'Utilisation %'])
    mods = mods[~mods[' accuracy '].apply(lambda x: '-' in str(x))]
    return ads, mods
    
def norm_ads(ads):
    latest_weight = 20
    start_weight = 20
    adrev_weight = 35
    st_weight = 25

    ads["adrev_diff"] = ads["ad_revenue"] - ads["avg_ad_revenue"]
    adrev_max = ads["adrev_diff"].max()
    adrev_min = ads["adrev_diff"].min()
    ads["adrev_score"] = (ads["adrev_diff"] - adrev_min) / (adrev_max - adrev_min) * adrev_weight

    st_max = ads["baseline_st"].max()
    st_min = ads["baseline_st"].min()
    ads["st_score"] = (st_max - ads["baseline_st"]) / (st_max - st_min) * st_weight

    ads['p_date_dateform'] = pd.to_datetime(ads['p_date'], format='%Y%m%d')
    ads['days_from_latest_to_p'] = (ads['p_date_dateform'] - ads['latest_punish_begin_date']).dt.days
    latest_max = ads["days_from_latest_to_p"].max()
    latest_min = ads["days_from_latest_to_p"].min()
    ads['latest_punish_score'] = ((ads["days_from_latest_to_p"] - latest_min) / (latest_max - latest_min) * latest_weight) / np.where(ads["punish_num"] > 0, ads["punish_num"], 1)

    ads['days_from_start_to_p'] = (ads['p_date_dateform'] - ads['start_time']).dt.days
    start_max = ads["days_from_start_to_p"].max()
    start_min = ads["days_from_start_to_p"].min()
    ads["start_score"] = (start_max - ads["days_from_start_to_p"]) / (start_max - start_min) * start_weight

    ads["total_score"] = ads["start_score"] + ads["latest_punish_score"] + ads["st_score"] + ads["adrev_score"]

    min_score = ads["total_score"].min()
    max_score = ads["total_score"].max()
    ads["normalized_score"] = (ads["total_score"] - min_score) / (max_score - min_score)

    return ads

def norm_mods(mods):
    mods["real_productivity"] = mods["Productivity"] - mods["Utilisation %"]
    mods.rename(columns={" accuracy ": "accuracy"}, inplace=True)
    mods = mods[mods["accuracy"] != "-"]
    mods.dropna(subset=["accuracy"], inplace=True)
    mods.reset_index(drop=True, inplace=True)

    Weight_Real_Productivity = 0.4
    Weight_Accuracy = 0.45
    Weight_Handling_Time = 0.15

    mods["score"] = (Weight_Real_Productivity * mods["real_productivity"] +
                     Weight_Accuracy * mods["accuracy"]) / (Weight_Handling_Time * mods["handling time"])

    min_score = mods["score"].min()
    max_score = mods["score"].max()

    mods["normalized_score"] = (mods["score"] - min_score) / (max_score - min_score)

    return mods

def optimise(ads_df, mods_df):

    # Check ad's market is in moderator's market
    def is_market_match(moderator_market, ad_country, ad_queue_market):
        return ad_country in moderator_market # or any(country in moderator_market for country in ad_queue_market)

    # Calculate the objective value (proximity) of a solution
    def calculate_proximity(solution, ads_df, mods_df):
        total_proximity = 0
        for moderator, allocated_ads in solution.items():
            moderator_score = mods_df.loc[mods_df['moderator'] == moderator, 'normalized_score'].values[0]
            ad_scores = [ads_df.loc[ads_df['ad_id'] == ad, 'normalized_score'].values[0] for ad in allocated_ads]
            ad_proximity = sum([abs(moderator_score - ad_score) for ad_score in ad_scores])
            total_proximity += ad_proximity
        return total_proximity
    
    # Simulated Annealing Parameters
    # If too large, compute time will be very long
    initial_temperature = 100
    final_temperature = 1
    cooling_rate = 0.1
    num_iterations = 1

    # Initialization
    current_solution = {moderator: [] for moderator in mods_df['moderator']}
    for ad_id in ads_df['ad_id']:
        moderator = random.choice(mods_df['moderator'].tolist())
        current_solution[moderator].append(ad_id)

    current_proximity = calculate_proximity(current_solution, ads_df, mods_df)
    best_solution = current_solution
    best_proximity = current_proximity

    current_temperature = initial_temperature

    # Simulated Annealing
    while current_temperature > final_temperature:
        for _ in range(num_iterations):
            
            # Generate a neighboring solution by moving one ad to another moderator
            neighbor_solution = current_solution.copy()
            ad_to_move = random.choice(list(ads_df['ad_id']))
            current_moderator = next((moderator for moderator, ads in current_solution.items() if ad_to_move in ads), None)
            available_moderators = [moderator for moderator in mods_df['moderator'] if
                                    ad_to_move in neighbor_solution[moderator]]
            new_moderator = random.choice(available_moderators)
            
            # Check if the ad's market matches the new moderator's market
            ad_country = ads_df.loc[ads_df['ad_id'] == ad_to_move, 'delivery_country'].values[0]
            moderator_market = mods_df.loc[mods_df['moderator'] == new_moderator, 'market'].values[0]
            ad_queue_market = ads_df.loc[ads_df['ad_id'] == ad_to_move, 'queue_market'].values[0]
            
            if is_market_match(moderator_market, ad_country, ad_queue_market):
                neighbor_solution[current_moderator].remove(ad_to_move)
                neighbor_solution[new_moderator].append(ad_to_move)
                
                # Calculate proximity of the neighboring solution
                neighbor_proximity = calculate_proximity(neighbor_solution, ads_df, mods_df)
                
                # Calculate change in proximity
                proximity_change = neighbor_proximity - current_proximity
                
                # Accept the neighboring solution with a probability
                if proximity_change < 0 or random.random() < math.exp(-proximity_change / current_temperature):
                    current_solution = neighbor_solution
                    current_proximity = neighbor_proximity
                    
                    # Update best solution
                    if current_proximity < best_proximity:
                        best_solution = current_solution
                        best_proximity = current_proximity
        
        # Reduce the temperature
        current_temperature *= cooling_rate

    # Save results
    output_file = "optimised_pairings.txt"

    content = "Best Solution:\n"
    for moderator, allocated_ads in best_solution.items():
        content += f"Moderator: {moderator}\n"
        for ad in allocated_ads:
            content += f"  Ad ID: {ad}\n"

    return dict(content=content, filename=output_file)