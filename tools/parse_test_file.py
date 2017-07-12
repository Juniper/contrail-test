import argparse
import os
import sys

def main():
    tests = []
    with open(sys.argv[1]) as f:
        content = f.readlines()
    with open(sys.argv[1],'w') as f:
        for line in content:
            test=line.split('[')[0]
            f.write(test+'\n') 

if __name__ == "__main__":
    main()
