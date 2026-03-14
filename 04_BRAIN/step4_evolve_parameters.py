"""
Step 4: Parameter Evolver (Genetic Algorithm).
Optimizes strategy settings like risk, TP, and SL using historical performance.
"""
import pandas as pd
import numpy as np
import json
import random
from pathlib import Path

def evolve_parameters():
    TRAIN_DIR = Path("04_BRAIN") / "training_data"
    MODELS_DIR = Path("04_BRAIN") / "models"
    REPORTS_DIR = Path("04_BRAIN") / "reports"
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        df = pd.read_csv(TRAIN_DIR / "features.csv")
    except FileNotFoundError:
        print("Features not found. Run Step 1 first.")
        return

    # Define Parameter Space
    # We are optimizing: TP_R_Multiple, SL_Pips, Trail_Trigger_R, Risk_Percent
    param_ranges = {
        'tp_r_multiple': (1.0, 5.0),
        'sl_pips': (10, 50),
        'trail_trigger_r': (0.3, 1.5),
        'risk_percent': (0.5, 3.0)
    }

    def generate_individual():
        return {k: random.uniform(v[0], v[1]) if isinstance(v[0], float) else random.randint(v[0], v[1]) 
                for k, v in param_ranges.items()}

    def fitness(individual):
        # Simplified Fitness: Calculate expected PnL based on the TP/SL ratios
        # If actual pnl_pips >= (SL * TP_R), it's a win of (Risk * TP_R)
        # Else it's a loss of Risk.
        
        sl = individual['sl_pips']
        tp_r = individual['tp_r_multiple']
        risk = individual['risk_percent']
        
        target_pips = sl * tp_r
        
        # We look at historical trades and see if they would have hit our new targets
        # This is a proxy since we don't have the full tick data here, but it's the 
        # "learning from backtest history" approach requested.
        wins = df['outcome_pips'] >= target_pips
        losses = df['outcome_pips'] < 0 # Simplified: if it was a loss, it stays a loss
        
        total_return = (wins.sum() * risk * tp_r) - (losses.sum() * risk)
        return total_return

    # GA Settings
    pop_size = 50
    generations = 20
    mutation_rate = 0.1
    
    population = [generate_individual() for _ in range(pop_size)]
    
    print(f"Starting Genetic Evolution for {generations} generations...")
    
    for gen in range(generations):
        # Evaluate
        scored_pop = [(fitness(ind), ind) for ind in population]
        scored_pop.sort(key=lambda x: x[0], reverse=True)
        
        best_fitness, best_ind = scored_pop[0]
        
        if gen % 5 == 0:
            print(f"Gen {gen}: Best Fitness = {best_fitness:.2f}")
            
        # Selection (Top 20%)
        parents = [ind for score, ind in scored_pop[:10]]
        
        # Crossover & Mutation
        new_population = parents.copy()
        while len(new_population) < pop_size:
            p1, p2 = random.sample(parents, 2)
            # Crossover
            child = {k: random.choice([p1[k], p2[k]]) for k in param_ranges}
            # Mutation
            if random.random() < mutation_rate:
                k = random.choice(list(param_ranges.keys()))
                v = param_ranges[k]
                child[k] = random.uniform(v[0], v[1]) if isinstance(v[0], float) else random.randint(v[0], v[1])
            new_population.append(child)
        
        population = new_population

    best_score, best_params = sorted([(fitness(ind), ind) for ind in population], key=lambda x: x[0], reverse=True)[0]
    
    print(f"\nEvolution Complete. Best Score: {best_score:.2f}")
    print(f"Best Parameters: {best_params}")
    
    # Save results
    with open(MODELS_DIR / "best_parameters.json", 'w') as f:
        json.dump(best_params, f, indent=4)
        
    report = (
        f"PARAMETER EVOLUTION REPORT\n"
        f"==========================\n"
        f"Algorithm: Genetic Algorithm (Evolutionary Strategy)\n"
        f"Generations: {generations}\n"
        f"Population Size: {pop_size}\n\n"
        f"BEST PARAMETERS FOUND:\n"
        f"{json.dumps(best_params, indent=4)}\n\n"
        f"Estimated Performance Score: {best_score:.2f}\n"
    )
    
    (REPORTS_DIR / "evolution_report.txt").write_text(report)
    print("Evolution results saved.")

if __name__ == "__main__":
    evolve_parameters()
