from .app import main
import argparse
parser=argparse.ArgumentParser(description='UE PartyUp PC private preview')
parser.add_argument('--smoke',action='store_true',help='Construct and close UI without Bluetooth operations')
main(smoke=parser.parse_args().smoke)
