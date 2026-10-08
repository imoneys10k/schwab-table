"""Run the accompanying project financial pipeline from an installed skill."""
import sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT))
from quarterly_earnings import main

if __name__=='__main__':main()
