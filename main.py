from apis.courses import Api
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--openapi', action='store_true')
    args = parser.parse_args()
    if args.openapi:
        Api().get_openapi()
