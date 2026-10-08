"""Run the accompanying project financial pipeline from an installed skill."""
import sys
import json
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
CONFIG=SKILL/'project.json'
PROJECT=Path(json.loads(CONFIG.read_text(encoding='utf-8'))['project']) if CONFIG.exists() else Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT))
from quarterly_earnings import main

if __name__=='__main__':main()
