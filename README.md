# Recipe Ratio Calculator
This is a utility designed to help with the computation of common recipe-related queries. Examples including finding
- The raw-ingredient cost of producing craftable items (Minecraft, Eve)
- How many batches of each sub-recipe is needed to (eventually) get the final product (Minecraft)
- The number of factories which are required at each stage to produce a fixed number of items per second (Factorio)
- What ratio of production facilities is needed to have no wasted products (Rise of Industry)


Admittedly, many of the above challenges already have domain-specific solutions, so why bother?
 
1) There are new games being released regularly and having a core framework for the algorithm will prevent the problem
from needing to be re-solved over and over.

2) Even those games for which there is a solver already available, it often does not support the incredibly convoluted
tiers of recipes added by mods. *Yes, I am looking at you Greg and Bob.* 

These reasons all (eventually) lead me to create this generic solver for the recipe-ratio class of problems.

## Demo Session
```
$ python main.py examples/recipes/minecraft.yaml examples/defaults/minecraft.yaml
Found recipes: ['piston', 'planks', 'smelt_iron_with_coal', 'smelt_iron_with_planks']
Found resources: ['coal', 'cobblestone', 'iron_ingot', 'iron_ore', 'log', 'piston', 'planks', 'redstone']
Specify a quantity of a resource you would like produced and type END when done.
=> 12 planks
Recipe      Required
--------  ----------
planks             3

Resource      Requested    UsdnPrd    Supplied    Leftover    Produced    Excess
----------  -----------  ---------  ----------  ----------  ----------  --------
log                   0          3           0           0           3         0
planks               12          0           0           0          12         0

=> 64 piston
Recipe                    Required
----------------------  ----------
piston                     64
planks                     58.6667
smelt_iron_with_planks     21.3333

Resource       Requested    UsdnPrd    Supplied    Leftover    Produced    Excess
-----------  -----------  ---------  ----------  ----------  ----------  --------
cobblestone            0   256                0           0    256              0
iron_ingot             0    64                0           0     64              0
iron_ore               0    64                0           0     64              0
log                    0    58.6667           0           0     58.6667         0
piston                64     0                0           0     64              0
planks                 0   234.667            0           0    234.667          0
redstone               0    64                0           0     64              0

=> 64 piston, 32 planks, 4 iron_ingot
Recipe                    Required
----------------------  ----------
piston                     64
planks                     67.3333
smelt_iron_with_planks     22.6667

Resource       Requested    UsdnPrd    Supplied    Leftover    Produced    Excess
-----------  -----------  ---------  ----------  ----------  ----------  --------
cobblestone            0   256                0           0    256              0
iron_ingot             4    64                0           0     68              0
iron_ore               0    68                0           0     68              0
log                    0    67.3333           0           0     67.3333         0
piston                64     0                0           0     64              0
planks                32   237.333            0           0    269.333          0
redstone               0    64                0           0     64              0

=> END
```

## Installation
To run this script, you will need:
- [Python v3.6](https://www.python.org/downloads/) (or later)
- [tabulate](https://pypi.org/project/tabulate/)
- [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [pydot](https://pypi.org/project/pydot/)
- [graphiz](https://graphviz.org/download/)

## Usage
You will need a recipe book defined for your domain, see the below schema section for more information on how to do
this, pass the path to this as the first parameter to the script.

Optionally, you can override defaults by adding the path to this as the second parameter to the script. While the
defaults within the recipe book should be sufficient to get started, overriding these allows you to choose different
recipes to produce resources or different machines to craft recipes, which as your game progresses, may make sense.    

After initializing everything, enter queries in the form `count identifier[, count identifier[..]]`. Say I want
to create 10 piston units and 64 wood planks, then I would enter `16 piston, 64 planks`. There is a more complete
example below.

### Understanding Resources
To effectively use this application, it is important to understand that **recipe inputs and outputs can be
thought of as both fixed quantities and production rates over time**. In Minecraft it is convenient to think of it in
the first sense because all recipes are one-time ordeals which you don't have as part of a production chain (usually)
whereas in games like Factorio the latter interpretation is more appropriate because factories are producing "flows" of
resources and you usually care about how many electronic circuits you produce per tick, for example, not how many
resources it would take to make 200 of them&mdash;besides, Factorio sort-of does that calculation for you.

### Available Resources
Let's say you are playing a game of minecraft and want to craft 10 pistons, but you already have 90 planks on hand and
8 iron ingots; so how much of the raw resources do you need now? Well...
```text
Recipe                    Required
----------------------  ----------
piston                          10
smelt_iron_with_planks           1

Resource       Requested    UsdnPrd    Supplied    Leftover    Produced    Excess
-----------  -----------  ---------  ----------  ----------  ----------  --------
cobblestone            0         40           0           0          40         0
iron_ingot             0         10           8           0           3         1
iron_ore               0          3           0           0           3         0
piston                10          0           0           0          10         0
planks                 0         32          90          58           0         0
redstone               0         10           0           0          10         0
``` 

As you can see, this recognizes you have enough planks, so it does not bother telling you to craft planks, and it also
notices that you do not have enough iron ingots, so you will have to make up the difference. This example used both
rounding of batches and resources, which is why all values are round, and also why there is an excess iron ingot
produced (since we don't allow fractional batches).

### Reading the Tables
There are two tables, the first lists the recipes used to craft resources and the number of batches required of that
recipe. If you are thinking of the resources as flows, then it will be the number of batches per time unit.

The second table has a lot of parts, so let me go through each of them:
- **Requested**: The amount of the resource you asked for explicitly.
- **UsdnProd**: Short for used in production, this is literally the total amount used in crafting everything.
- **Supplied**: The amount you said you had on hand at the beginning, i.e. the initially available amount.
- **Leftover**: Amount of what was supplied which was not used in production.
- **Produced**: Total amount of the resource which must/will be produced.
- **Excess**: Quantity of produced resources which go unused. Separate from the amount leftover.  

## Schema
There are two types of files, the first is a recipe book containing all the recipes needed to make calculations, and the
second is a list of (overriding) defaults which can (and probably should for some games) be modified as needed. **The
recipe book should remain the same across all uses.**

### Defaults
There are two defaults that can be specified. The first, is for each resource, you can define the default recipe to
craft it. The second, is for each recipe, you can define the default crafter/machine to craft it. In some games only
the default recipes section will make sense, so the `recipes` master object can be left out as long as there is not a
`crafters` tag.

If you leave a default recipe blank, as shown below for `raw_resource`, it will designate it as a raw resource, which
means that in calculations, it will only calculate how much of the resource is needed, and not how much you have to
produce. Depending on the resource, this could be a useful simplification; in factorio for instance, we often consider
the production of iron plates independently of each production chain that demands them. 

**Full schema:**
```yaml
crafters:
  recipe_name: default_crafter_name
  # ...
recipes:
  resource_name: default_recipe_name
  raw_resource: # leaving this blank designates it as a raw resource
  # ...
```

See also the example defaults.

### Recipe Book
A full recipe book has three sections (if `recipes` is not present, then it assumes the whole thing is the `recipes`
section). Both `crafters` and `defaults` may be omitted, and both can be overridden by the Defaults config listed above.

Each recipe consists of
- `inputs`: What it consumes and the amount consumed; may be omitted
- `outputs`: What it produces and the amount produced; may be omitted
- `duration`: How long the recipe takes to craft; may be omitted
- `crafters`: Which crafters are able to manufacture this recipe; may be omitted

*Note that inputs and outputs cannot both be omitted for the same recipe.*

The `crafters` section simply lists which crafters are available and how fast (efficiency or speed) of their operation.

Finally, the `defaults` section simply specifies what recipe should be used to produce a given resource. As in the
defaults file, leaving the recipe blank will designate it as a raw resource.

**Full schema:**
```yaml
recipes:
  recipe_name:
    inputs:
      input_name: quantity
      # ...
    outputs:
      output_name: quantity
      # ...
    duration: time_required
    crafters:
      - crafter_name
      # ...
  # ...
crafters:
  crafter_name: crafter_efficency # or speed
  # ...
defaults:
  resource_name: default_recipe_name
  # ...
```

## Contributions
I would love to add recipe books for games to prevent everyone needing to create their own. Please make a pull request
with any additions or corrections and I would be very grateful.

## Future Work
- better CLI
