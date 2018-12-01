import sys
from calculator.book import RecipeBook
import re
from typing import Dict, Tuple
from tabulate import tabulate
import yaml

request_pattern = re.compile('\s*(\d+(?:\.\d+)?)\s*([a-zA-Z_]\w*)\s*$')


def main():
    book = None
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as filestream:
            book = RecipeBook.from_obj(yaml.load(filestream))
            print("Found recipes: {}".format(sorted(book.recipes())))
            print("Found resources: {}".format(sorted(book.resources())))
    else:
        print("Must specify a recipe book!", file=sys.stderr)
        exit(1)

    if len(sys.argv) > 2:
        with open(sys.argv[2]) as filestream:
            book.set_defaults_from_obj(yaml.load(filestream))

    print("Specify a quantity of a resource you would like produced and type END when done.")
    while True:
        l = input('=> ')
        if l[0:3] == 'END':
            break

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

        batches, quantities = book.calculate(targets)
        print(tabulate_recipe_batches(book, batches), end='\n\n')
        print(tabulate_resource_requirements(quantities, targets), end='\n\n')


def tabulate_recipe_batches(book: RecipeBook, batches: Dict[str, Tuple[float, float]]) -> str:
    if book.crafters_defined():
        rows = sorted(map(lambda kv: [
            book.get_crafter_for(kv[0]) or 'Default',
            kv[0], kv[1][1], kv[1][0]
        ], batches.items()))
        return tabulate(rows, headers=['Crafter', 'Recipe', 'Required', 'Requested'])
    else:
        rows = sorted(map(lambda kv: [
            kv[0], kv[1][1], kv[1][0]
        ], batches.items()))
        return tabulate(rows, headers=['Recipe', 'Required', 'Requested'])


def tabulate_resource_requirements(requirements: Dict[str, Tuple[float, float]], targets: Dict[str, float]) -> str:
    rows = sorted(map(lambda kv: [
        kv[0],
        kv[1][0] - (targets.get(kv[0]) or 0.0),
        targets.get(kv[0]) or 0.0,
        kv[1][1] - kv[1][0]
    ], requirements.items()))
    return tabulate(rows, headers=['Resource', 'UsednProd', 'Requested', 'Excess'])


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
    main()
