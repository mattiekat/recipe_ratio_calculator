# Recipe Ratio Calculator
This is a utility designed to help with the computation of common recipe-related queries. Examples including finding
- The raw-ingredient cost of producing craftable items (Minecraft, Eve)
- How many batches of each sub-recipe is needed to (eventually) get the final product (Minecraft)
- The number of factories which are required at each stage to produce a fixed number of items per second (Factorio)
- What ratio of production facilities is needed to have no wasted products (Rise of Industry)


Admittedly, many of the above challenges already have domain-specific solutions, so why bother?
 
1) There are new games being released regularly and having a core framework for the algorithm will prevent the problem from needing to be re-solved over and over.

2) Even those games for which there is a solver already available, it often does not support the incredibly convoluted
tiers of recipes added by mods. *Yes, I am looking at you Greg and Bob.* 

These reasons all (eventually) lead me to create this generic solver for the recipe-ratio class of problems.

## Demo Session
```
$ python main.py examples/recipes/minecraft.yaml examples/defaults/minecraft.yaml
Specify a quantity of a resource or recipe you would like produced and type END when done.
=> 12 planks
Recipe      Required    Requested
--------  ----------  -----------
r_planks           3            0

Resource      UsednProd    Requested    Excess
----------  -----------  -----------  --------
planks                0           12         0
wood                  3            0         0

=> 64 piston
Recipe      Required    Requested
--------  ----------  -----------
r_iron_w     21.3333            0
r_piston     64                 0
r_planks     58.6667            0

Resource       UsednProd    Requested    Excess
-----------  -----------  -----------  --------
cobblestone     256                 0         0
iron             64                 0         0
iron_ore         64                 0         0
piston            0                64         0
planks          234.667             0         0
redstone         64                 0         0
wood             58.6667            0         0

=> 64 piston, 32 plank, 4 iron
Could not find target: plank
=> 64 piston, 32 planks, 4 iron
Recipe      Required    Requested
--------  ----------  -----------
r_iron_w     22.6667            0
r_piston     64                 0
r_planks     67.3333            0

Resource       UsednProd    Requested    Excess
-----------  -----------  -----------  --------
cobblestone     256                 0         0
iron             64                 4         0
iron_ore         68                 0         0
piston            0                64         0
planks          237.333            32         0
redstone         64                 0         0
wood             67.3333            0         0

=> END
```

## Installation
To run this script, you will need [Python v3.6](https://www.python.org/downloads/) or later, along with
[tabulate](https://pypi.org/project/tabulate/) package and [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation).

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

## Schema
There are two types of files, the first is a recipe book containing all the recipes needed to make calculations, and the
second is a list of (overriding) defaults which can (and probably should for some games) be modified as needed. **The
recipe book should remain the same across all uses.**

### Defaults
There are two defaults that can be specified. The first, is for each resource, you can define the default recipe to
craft it. The second, is for each recipe, you can define the default crafter/machine to craft it. In some games only
the default recipes section will make sense, so the `recipes` master object can be left out as long as there is not a
`crafters` tag.

**Full schema:**
```yaml
crafters:
  recipe_name: default_crafter_name
  # ...
recipes:
  resource_name: default_recipe_name
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

Finally, the `defaults` section simply specifies what recipe should be used to produce a given resource.

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
- allow rounding up of batches and/or product demands to integer values
- allow calculations with rational numbers instead of only real values
- allow auto-upscaling of a recipe get perfect ratios
- create graph output of the final recipe
