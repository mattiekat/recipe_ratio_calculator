import csv

recipe = """\
{}:
  inputs: {}
  outputs: {}
  duration: {}
  crafters: {}
"""

def idf(s: str) -> str:
    return s.lower().replace(' ', '_').replace('_&_', '_and_')


file = open('farms.csv')
crafters = set()
for row in csv.reader(file):
    output = idf(row[0])
    quantity = int(row[9])
    crafter = idf(row[1])
    crafters.add(crafter)
    duration = int(row[2])
    inputs = {}
    for i in range(3, 8, 2):
        name = idf(row[i])
        count = int('0' + row[i+1])
        if count > 0:
            inputs[name] = count
    print(recipe.format(output, str(inputs).replace('\'', ''), '{{{}: {}}}'.format(output, quantity), duration, crafter), end='')

print()
for crafter in crafters:
    print('{}: 1'.format(crafter))
