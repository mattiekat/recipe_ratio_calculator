import sys
from recipe import Recipe, RecipeBook
import re
from typing import Dict, Optional, Set, Tuple
from itertools import chain
from tabulate import tabulate

request_pattern = re.compile('\s*(\d+(?:\.\d+)?)\s*([a-zA-Z_]\w*)')
Counts = Dict[str, Tuple[float, float]]


def propagate(book: RecipeBook, recipe_batches: Counts, resource_counts: Counts) -> bool:
    """
    Construct and propagate the implications of what recipe requirements we know to determine the total requirements of
    production by updating the batches and the resulting quantities of produced resources. This needs to be called
    multiple times for some problems to find an optimal solution.

    :param book: Book of all available recipes.
    :param recipe_batches: Counts for each of the recipe nodes.
    :param resource_counts: Counts for each of the resource nodes.
    :return: Whether any changes were made to the graph.
    """

    pending_changes: Set[str] = set(recipe_batches.keys())
    changes_made = False
    while pending_changes:
        # 1) choose a recipe node which needs to be updated
        recipe = book[pending_changes.pop()]

        # 2) find the total number of batches needed to produce the demanded output (for which it is the recipe of)
        base_batches = recipe_batches.get(recipe.name) or (0.0, 0.0)
        # If not reducing: the user may request a minimum number of batches (will be >= 0)
        # If reducing: max number of batches we can remove (will be <= 0) while preserving the user requested min
        batches = max(0.0, base_batches[0] - base_batches[1])

        for resource in recipe.outputs():
            demand, supply = resource_counts.get(resource) or (0.0, 0.0)

            if batches < 0.0:
                # Cannot reduce the number of batches below the demanded amount even if this is not designated recipe
                pass
            elif demand <= supply or book.get_recipe_for(resource) != recipe:
                # if it is already supplied, don't bother
                # if this is not the primary recipe for the resource, do not modify the number of batches based on it
                continue

            # If not reducing: use the difference; other things may add to the resource so we cannot start from scratch
            # If reducing: number we can remove is the minimum magnitude that can be removed from all resources
            #   (which becomes the maximum since the values are negative)
            batches = max(batches, recipe.batches_required(resource, demand - supply))

        # the new number of batches must satisfy the minimum specified by the user
        assert base_batches[1] + batches >= base_batches[0]
        if batches == 0:
            # nothing changes
            continue
        changes_made = True

        # update the current number of batches to the new number we have deemed appropriate
        recipe_batches[recipe.name] = (base_batches[0], base_batches[1] + batches)

        # 3) update the input resources to reflect the new demand
        for resource in recipe.inputs():
            counts = resource_counts.get(resource) or (0.0, 0.0)
            counts = (counts[0] + recipe.consumed(resource, batches), counts[1])  # increase/decrease demand

            # mark it's producing recipe as needing to be updated (if not raw)
            r2 = book.get_recipe_for(resource)
            if r2 is None:
                # it's a raw resource, so supply = demand
                counts = (counts[0], counts[0])
            else:
                pending_changes.add(r2.name)
            resource_counts[resource] = counts

        # 4) update the output resources to reflect the new supply
        for resource in recipe.outputs():
            counts = resource_counts.get(resource) or (0.0, 0.0)
            counts = (counts[0], counts[1] + recipe.produced(resource, batches))  # increase/decrease supply
            resource_counts[resource] = counts

    return changes_made


def calculate(book: RecipeBook, targets: Dict[str, float]) -> Tuple[Counts, Counts]:
    """
    Calculate the number of resources and batches of each recipe are needed to meet all the user, production targets.

    Note: Production targets for resources define how many of the resource must be "left over" (i.e. not consumed by
    other recipes) while production targets for recipes define the minimum number of batches which must be run.

    :param book: Book of all available recipes.
    :param targets: Production targets specified by the user.
    :return: The total recipe batches and resource counts.
    """

    # the total quantity of an ingredient/resource
    #       first part is the "demand", i.e. how much is required
    #       second part is the "supply", i.e. how much will be produced (may be greater than demand if it's a byproduct)
    resource_counts = {}

    # how many batches are we producing of each recipe
    recipe_batches = {}

    # set the demand for each target as the required quantities
    for target, required in targets.items():
        if book.is_recipe(target):
            recipe_batches[target] = (required, 0.0)
        elif book.is_resource(target):
            # find it's recipe and add that
            recipe = book.get_recipe_for(target)
            if recipe is None:
                # raw resource, not sure why it was requested, but give them what they want
                resource_counts[target] = (required, required)
            else:
                resource_counts[target] = (required, 0.0)
                recipe_batches[recipe.name] = (0.0, 0.0)
        else:
            raise RuntimeError("Unrecognized identifier: " + target)

    while propagate(book, recipe_batches, resource_counts):
        # multiple iterations are required when recipes produces useful byproducts
        pass

    return recipe_batches, resource_counts


def tabulate_recipe_batches(batches: Dict[str, Tuple[float, float]]) -> str:
    rows = sorted(map(lambda kv: [kv[0], kv[1][1], kv[1][0]], batches.items()))
    return tabulate(rows, headers=['Recipe', 'Required', 'Requested'])


def tabulate_resource_requirements(requirements: Dict[str, Tuple[float, float]], targets: Dict[str, float]) -> str:
    rows = sorted(map(lambda kv: [kv[0], kv[1][1], kv[1][0], targets.get(kv[0]) or 0.0], requirements.items()))
    return tabulate(rows, headers=['Resource', 'Produced', 'Required', 'Requested'])


def main():
    book = RecipeBook()
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as filestream:
            book.add_recipes_from_stream(filestream)
            print("Found recipes: {}".format(sorted(book.recipes())))
            print("Found resources: {}".format(sorted(book.resources())))
    else:
        print("Enter the list of required recipes.")
        book.add_recipes_from_stream(sys.stdin)

    print("Specify a quantity of a resource or recipe you would like produced and type END when done. You may also "
          "list multiple separated by comas instead and all will be considered.")
    while True:
        l = input('=> ')
        if l[0:3] == 'END':
            break

        targets = _read_request(l)
        if targets is None:
            continue
        for t in targets:
            if not (book.is_recipe(t) or book.is_resource(t)):
                print("Could not find target: " + t)
                continue

        batches, quantities = calculate(book, targets)
        print(tabulate_recipe_batches(batches), end='\n\n')
        print(tabulate_resource_requirements(quantities, targets), end='\n\n')


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
