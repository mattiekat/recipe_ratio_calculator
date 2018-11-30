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

## Demo Session
```
$ python main.py
Enter recipes followed by 'END'.
r_piston {3 planks, 4 cobblestone, 1 redstone, 1 iron} -> {1 piston}
r_planks {1 wood} -> {4 planks}
r_iron_c {8 iron_ore, 1 coal} -> {8 iron}
r_iron_w {3 iron_ore, 2 planks} -> {3 iron}
END
Enter any defaults followed by 'END'.
iron r_iron_w
END
Enter any crafters followed by 'END'.
END
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
To run this script, you will need [Python v3.6](https://www.python.org/downloads/) or later, along with the
[tabulate](https://pypi.org/project/tabulate/) package.

## Usage
You have two primary options right now for execution, the first is to define the recipe book in a plain-text document
and also the defaults and crafters specifications. The second is to input them into standard input (aka lots-o-typing).
In either case, read on for more information about how to specify recipes, defaults, and crafters.

The parameter order is
1) recipes
2) default recipes
3) recipe crafters

If you wish to specify 1 and 2 in a file that works, but not 1 and 3 (for now). Any which are not specified will be
promoted for when you run the application, to which you may safely enter 'END' for more basic cases. 

After initializing everything, enter queries in the form `count identifier[, count identifier[..]]`. Say I want
to create 10 piston units and 64 wood planks, then I would enter `16 piston, 64 planks`. There is a more complete
example below.

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
4) Duration - How long it takes to produce the recipe

Depending on which view of resources you take, duration may or may not hold meaning. If it is 1.0
(or left out as it defaults to 1.0), then it will be equivalent to single batch calculations, and if it is not, the
system will be computing the items per unit time required to satisfy the flows.

A recipe book of very different types of recipes:
```
stealfurnace_ironplate {1 ironore} -> {1 ironplate} / 3.5
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

## Defining Crafters
In some games like Factorio, it makes sense to define not only recipes, but what crafts them as it alters the time
required to produce the resources.

To do this, include an additional file with each crafter defined as `crafter_name efficency recipe1, recipe2, ...` with
the end of file/input being denoted with `END`.

For example:
```
assembly_machine_1 0.5             r_copper_cable, r_iron_gear
assembly_machine_2 0.75            r_assembly_machine, r_gcirc
assembly_machine_3 1.25
stone_furnace 1.0
steel_furnace 2.0                  r_copperp, r_ironp
electric_furnace 3.0
END

```

In the above example, there are several crafters which have no recipes defined for them, this allows the recipes to be
easily moved around as the game progresses and the preferred crafters change. It also allows for having a blank/default
template for a game to prevent you from having to look up all the crafters and their speeds.   

## Contributions
I would love to add recipe books for games to prevent everyone needing to create their own. Please make a pull request
with any additions or corrections and I would be very grateful.

## Future Work
- allow rounding up of batches and/or product demands to integer values
- allow calculations with rational numbers instead of only real values
- allow auto-upscaling of a recipe get perfect ratios
- create graph output of the final recipe