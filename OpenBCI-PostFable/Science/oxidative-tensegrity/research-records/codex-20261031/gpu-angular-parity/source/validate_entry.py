import sys,pathlib,runpy
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
runpy.run_module('validate',run_name="__main__")
