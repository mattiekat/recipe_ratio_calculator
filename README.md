# Recipe Ratio Calculator
This is a utility designed to help with the computation of common recipe-related queries. Examples including finding
- The raw-ingredient cost of producing craftable items (Minecraft, Eve)
- How many batches of each sub-recipe is needed to (eventually) get the final product (Minecraft)
- The number of factories which are required at each stage to produce a fixed number of items per second (Factorio)
- What ratio of production facilities is needed to have no wasted products (Rise of Industry)


Admittedly, many of the above challenges already have domain-specific solutions, so why bother?
 
1) There are new games being released regularly and having an core framework for the algorithms and description of the
algorithm will prevent the problem from needing to be re-solved over and over.

2) Even those games for which there is a solver already available, it often does not support the incredibly convoluted
tiers of recipes added by mods. *Yes, I am looking at you Greg and Bob.* 

These reasons all (eventually) lead me to create this generic solver for the recipe-ratio class of problems.

## Installation
To run this script, you will need [Python v3.6](https://www.python.org/downloads/) or later, along with the
[tabulate](https://pypi.org/project/tabulate/) package.

## Usage
You have two primary options right now for execution, the first is to define a recipe book in a plain-text document, and
the second is to input it into standard input (aka lots-o-typing).

If you use a file to specify the recipes, simply start the application by running `python main.py path/to/file.txt` in
the terminal if you are on a cool operating system and the command prompt if you are not. If you do not use a file, then
simply run `python main.py` and you will first be asked to enter in at minimum the relevant recipes to whatever
questions you will ask. In either case, read the recipe definition spec for more information.

After the recipes have been defined, enter queries in the form `count identifier[, count identifier[..]]`. Say I want
to create 10 piston units and 64 wood planks, then I would enter `16 piston, 64 planks`.

### Understanding User Targets
Note that `count` changes meaning depending on whether the `identifier` specifies a recipe or a resource.
- **If `count` specifies a resource/ingredient, then it defines the amount of that resource which should be left-over**
after all things have been considered. In the above example, I want to have 16 pistons result from all the crafting
along with 64 planks. If some planks are needed by another recipe (like the piston recipe...) we will **not** use those
for the pistons and instead produce the number we want left over plus any others which are required by other recipes.

- **If `count` specifies a recipe, then it defines the minimum number of batches that will be calculated.** For example,
if you chose to use the recipe for `planks` instead (`16 r_planks`), you would find you need to make only 64
(16 batches) instead of 112 (28 batches). This difference is because 48 planks are required by the piston recipe, so
some of those planks won't be left-over at the end.

### Understanding Resources
To effectively use this application, it is important to understand that **recipe inputs and outputs can be
thought of as both fixed quantities and production rates over time**. In Minecraft it is convenient to think of it in
the first sense because all recipes are one-time ordeals which you don't have as part of a production chain (usually)
whereas in games like Factorio the latter interpretation is more appropriate because factories are producing "flows" of
resources and you usually care about how many electronic circuits you produce per tick, for example, not how many
resources it would take to make 200 of them&mdash;besides, Factorio sort-of does that calculation for you. 

## Defining Recipes
A recipe has the following components:
1) Name - What we will refer to our recipe as
2) Inputs - What resources are consumed by the recipe
3) Outputs - What resources are produced by the recipe
4) Efficiency - How fast the machine which makes it operates
5) Duration - How long it takes to produce the recipe

Depending on which view of resources you take, efficiency and duration may or may not hold meaning. If they are both 1.0
(or left out as they default to 1.0), then it will be equivalent to single batch calculations, and if they are not, it
will be computing the items per unit time required to satisfy the flows.

A recipe book of very different types of recipes:
```
stealfurnace_ironplate {1 ironore} -> {1 ironplate} * 2 / 3.5
r_piston {3 planks, 4 cobblestone, 1 redstone, 1 iron} -> {1 piston}
factory_textile_heavy_fabric {1 fiber, 1 dye, 1 leather} -> {1 heavy_fabric} / 40
collector_water {} -> {1 water} / 10
burner_generator {1 coal} -> {}
END
```

What makes sense to represent as a recipe is very dependent on the situation. Also, the above examples were very rigid
in their format, but spaces may (technically) be omitted and tab characters are acceptable.

After all recipes have been specified, add an `END` statement is required to terminate the list.

## Defining Defaults
It is a good idea to define default recipes for any resource which has more than one way of being produced. If a default
is not specified in advance, you will be prompted during runtime to make a choice between available recipes if the need
arises. By specifying defaults you can streamline your use of this utility.

Note that defaults are defined separately from recipes which makes it possible to change them as needed without
altering the master set of recipes.

Defaults are defined simply by writing a resource name followed by the recipe which should be used to produce it. This
has no effect if there is only one recipe which produces a resource. An error will be raised if the resource or recipe
does not exist or if the recipe does not output the specified resource.

Example:
```
water collector_water
piston r_piston
END
```

## Contributions
I would love to add recipe books for games to prevent everyone needing to create their own. Please make a pull request
with any additions or corrections and I would be very grateful.

## Future Work
- allow rounding up of batches and/or product demands to integer values
- allow calculations with rational numbers instead of only real values
- allow defining machines (for efficiency values) which have recipes they can produce
- allow calculations with fractions instead of real numbers
- allow auto-upscaling of a recipe get perfect ratios
- create graph output of the final recipe