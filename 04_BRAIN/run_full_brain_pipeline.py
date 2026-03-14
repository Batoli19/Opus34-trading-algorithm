"""
Master Script: Full Brain Pipeline Orchestrator.
Runs all 5 steps in sequence to upgrade the bot.
"""
import subprocess
import sys
from pathlib import Path

def run_step(script_name):
    print(f"\n>>> STARTING: {script_name}...")
    try:
        # Use sys.executable to ensure we use the same python environment
        result = subprocess.run([sys.executable, script_name], check=True, capture_output=False)
        print(f">>> SUCCESS: {script_name} finished.")
        return True
    except subprocess.CalledProcessError as e:
        print(f">>> ERROR: {script_name} failed with exit code {e.returncode}.")
        return False

def main():
    BRAIN_DIR = Path("04_BRAIN")
    steps = [
        "step1_extract_features.py",
        "step2_train_entry_model.py",
        "step3_train_exit_agent.py",
        "step4_evolve_parameters.py",
        "step5_validate_brain.py"
    ]
    
    print("====================================================")
    print("   ICT TRADING BOT - FULL BRAIN UPGRADE PIPELINE   ")
    print("====================================================\n")
    
    for step in steps:
        script_path = BRAIN_DIR / step
        if not run_step(str(script_path)):
            print("\n!!! PIPELINE HALTED DUE TO ERROR !!!")
            sys.exit(1)
            
    print("\n====================================================")
    print("   UPGRADE COMPLETE: BRAIN IS NOW READY FOR USE    ")
    print("====================================================")

if __name__ == "__main__":
    main()
