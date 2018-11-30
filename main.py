# TODO: make results more readable
# TODO: don't ask for recipes to produce waste byproducts
# TODO: allow specifying default recipes in advance (separate file?)
# TODO: implement rounding of batches and/or product demands
# TODO: allow defining machines (for efficiency values) which have recipes they can produce
# TODO: allow calculations with fractions instead of real numbers
# TODO: auto-upscale to have perfect ratios


import sys
from recipe import Recipe, read_recipe_book
import re
from typing import Dict, Optional, Set
from itertools import chain

request_pattern = re.compile('\s*(\d+(?:\.\d+)?)\s*([a-zA-Z_]\w*)')


def find_recipe(book: Dict[str, Recipe], resource: str) -> Optional[Recipe]:
    available = list(filter(None, map(
        lambda recipe: recipe if recipe.produces(resource) else None,
        book.values()
    )))

    if len(available) == 1:
        # there is exactly one recipe, so use it
        return available[0]
    if len(available) == 0:
        # there is no recipe, it is a raw resource
        return None

    # there is more than one recipe, so prompt the user
    print("Please select a recipe for '{}'".format(resource))
    for i, o in enumerate(available):
        print("{}: {}".format(i+1, repr(o)))
    choice = int(input('=> '))
    return available[choice-1]


def calculate(book: Dict[str, Recipe], targets: Dict[str, float]):
    # book is the list of recipes available for use
    # targets represent mandatory amounts

    # the total quantity of an ingredient/resource
    #       first part is the "demand", i.e. how much is required
    #       second part is the "supply", i.e. how much will be produced (may be greater than demand if it's a byproduct)
    resource_counts: Dict[str, (float, float)] = {}

    # how many batches are we producing of each recipe
    recipe_batches: Dict[str, (float, float)] = {}

    # dictionary of (resource, recipe to make it); a cache/index of recipes by resource (rbr) we want to create.
    # None if it is a raw resource
    rbr: Dict[str, Optional[Recipe]] = {}

    def get_recipe(resource: str) -> Optional[Recipe]:
        if resource in rbr:
            return rbr[resource]
        recipe = find_recipe(book, resource)
        rbr[resource] = recipe
        return recipe

    # recipes which need to be updated
    pending_changes: Set[str] = set()

    # set the demand for each target as the required quantities
    for target, required in targets.items():
        if target in book:
            # it's a recipe
            recipe_batches[target] = (required, 0.0)
            pending_changes.add(target)
        else:
            # it's a resource, find it's recipe and add that
            recipe = get_recipe(target)
            if recipe is None:
                # raw resource, not sure why it was requested, but give them what they want
                resource_counts[target] = (required, required)
            else:
                resource_counts[target] = (required, 0.0)
                recipe_batches[recipe.name] = (0.0, 0.0)
                pending_changes.add(recipe.name)

    while pending_changes:
        # 1) choose a recipe node which needs to be updated
        recipe = book[pending_changes.pop()]

        # 2) find the total number of batches needed to produce the demanded output (for which it is the recipe of)
        base_batches = recipe_batches.get(recipe.name) or (0.0, 0.0)
        # the user may request a minimum number of batches, so include them
        batches = max(0.0, base_batches[0] - base_batches[1])  # number of additional batches

        for resource in recipe.outputs():
            if get_recipe(resource) != recipe:
                # if this is not the primary recipe for the resource, do not modify the number of batches based on it
                continue

            demand, supply = resource_counts.get(resource) or (0.0, 0.0)
            if demand <= supply:
                continue

            # we use the difference, because other things may add to the resource so we cannot start from scratch
            batches = max(batches, recipe.batches_required(resource, demand - supply))

        recipe_batches[recipe.name] = (base_batches[0], base_batches[1] + batches)

        # 3) update the input resources to reflect the new demands
        for resource in recipe.inputs():
            counts = resource_counts.get(resource) or (0.0, 0.0)
            counts = (counts[0] + recipe.consumed(resource, batches), counts[1])  # increase demand

            # mark it's producing recipe as needing to be updated (if not raw)
            r2 = get_recipe(resource)
            if r2 is None:
                # it's a raw resource, so supply = demand
                counts = (counts[0], counts[0])
            else:
                pending_changes.add(r2.name)
            resource_counts[resource] = counts

        # 4) update the output resources to reflect the new supply
        for resource in recipe.outputs():
            counts = resource_counts.get(resource) or (0.0, 0.0)
            counts = (counts[0], counts[1] + recipe.produced(resource, batches))  # increase supply
            resource_counts[resource] = counts

    # Make a second pass to reduce batch sizes to their minimums. This is required if a recipe produces as a byproduct
    # the input for another which has a different preferred recipe and both are used.
    pending_changes = set(recipe_batches.keys())
    while pending_changes:
        recipe = book[pending_changes.pop()]
        base_batches = recipe_batches[recipe.name]
        batches = base_batches[1] - base_batches[0]  # max number of batches we can remove

        # number we can remove is the minimum amount that can be removed from all resources
        for resource in recipe.outputs():
            demand, supply = resource_counts[resource]
            batches = min(batches, recipe.batches_required(resource, supply - demand))

        assert batches >= 0.0
        assert base_batches[0] <= base_batches[1] - batches

        if batches <= 0.0:
            # can't remove anything
            continue

        recipe_batches[recipe.name] = (base_batches[0], base_batches[1] - batches)

        # update all inputs by reducing the demand
        for resource in recipe.inputs():
            counts = resource_counts[resource]
            counts = (counts[0] - recipe.consumed(resource, batches), counts[1])

            # mark it's producing recipe as needing to be updated (if not raw)
            r2 = get_recipe(resource)
            if r2 is None:
                # it's a raw resource, so supply = demand
                counts = (counts[0], counts[0])
            else:
                pending_changes.add(r2.name)
            resource_counts[resource] = counts

        # update all outputs by reducing the supply
        for resource in recipe.outputs():
            counts = resource_counts[resource]
            counts = (counts[0], counts[1] - recipe.produced(resource, batches))
            resource_counts[resource] = counts

    return recipe_batches, resource_counts


def read_request(str):
    request = {}
    for part in str.split(','):
        m = request_pattern.match(part)
        if m is None:
            print("Invalid request format")
            return None
        request[m[2]] = float(m[1])
    return request


def main():
    book = {}
    resources = set()
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as filestream:
            book, resources = read_recipe_book(filestream)
    else:
        print("Enter the list of required recipes.")
        book, resources = read_recipe_book(sys.stdin)

    print("Specify a quantity of a resource or recipe you would like produced and type END when done. You may also "
          "list multiple separated by comas instead and all will be considered.")
    while True:
        l = input('=> ')
        if l[0:3] == 'END':
            break

        targets = read_request(l)
        if targets is None:
            continue
        if any(map(lambda t: not (t in resources or t in book), chain(targets, book.keys()))):
            print("Could not find target")
            continue

        batches, quantities = calculate(book, targets)
        print(batches)
        print(quantities)
        print()


if __name__ == '__main__':
    main()
