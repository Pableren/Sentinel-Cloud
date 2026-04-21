import pandas as pd
import numpy as np
import sklearn

def main():
    print("--------------------------------------------------")
    print("       Python Lab Environment Initialized         ")
    print("--------------------------------------------------")
    print(f"NumPy version      : {np.__version__}")
    print(f"Pandas version     : {pd.__version__}")
    print(f"Scikit-learn version: {sklearn.__version__}")
    print("--------------------------------------------------")
    print("Ready for experiments!")

if __name__ == "__main__":
    main()
