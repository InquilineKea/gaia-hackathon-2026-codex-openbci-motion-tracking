import sys,pathlib,runpy
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
runpy.run_module('benchmark',run_name="__main__")
