import re
import sys

import yaml

from calculator.book import RecipeBook

class ReloadBookRequest(StopIteration):
    pass

request_pattern = re.compile('\s*(\d+(?:\.\d+)?)\s*([a-zA-Z_]\w*)\s*$')


def main():
    book = None
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as filestream:
            book = RecipeBook.from_obj(yaml.full_load(filestream))
            print("Found recipes: {}".format(sorted(book.recipes())))
            print("Found resources: {}".format(sorted(book.resources())))
    else:
        print("Must specify a recipe book!", file=sys.stderr)
        exit(1)

    if len(sys.argv) > 2:
        with open(sys.argv[2]) as filestream:
            book.set_defaults_from_obj(yaml.full_load(filestream))

    print("Specify a quantity of a resource you would like produced and type END when done or RELOAD to refresh the book.")
    while True:
        l = input('=> ')
        if l[0:3] == 'END':
            break
        if l == 'RELOAD':
            raise ReloadBookRequest()

        targets = _read_request(l)
        if targets is None:
            continue

        invalid = False
        for t in targets:
            if not book.is_resource(t):
                print("Could not find target: " + t)
                invalid = True
        if invalid:
            continue

        results = book.calculate(targets)
        print(results.tabulate_recipes(), end='\n\n')
        print(results.tabulate_resources(), end='\n\n')
        results.write_graph()


def _read_request(str):
    request = {}
    for part in str.split(','):
        m = request_pattern.match(part)
        if m is None:
            print("Invalid request format")
            return None
        request[m[2]] = float(m[1])
    return request


if __name__ == '__main__':
    while True:
        try:
            main()
        except ReloadBookRequest:
            continue
        break
