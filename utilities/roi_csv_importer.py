import csv

recipe = """\
{}:
  inputs: {}
  outputs: {}
  duration: {}
  crafters: {}
"""
# row indexes
location = {
    "farm": {
        "output": 0,
        "quantity": 9,
        "crafter": 1,
        "duration": 2,
        "inputs_start": 3,
        "inputs_stop": 8
    },
    "factory": {
        "output": 0,
        "quantity": 10,
        "crafter": 1,
        "duration": 3,
        "inputs_start": 4,
        "inputs_stop": 9
    }
}['factory']

def idf(s: str) -> str:
    return s.lower().replace(' ', '_').replace('_&_', '_and_')


file = open('roi.csv')
crafters = set()
for row in csv.reader(file):
    output = idf(row[location['output']])
    quantity = int(row[location['quantity']])
    crafter = idf(row[location['crafter']])
    crafters.add(crafter)
    duration = int(row[location['duration']])
    inputs = {}
    for i in range(location['inputs_start'], location['inputs_stop'], 2):
        name = idf(row[i])
        count = int('0' + row[i+1])
        if count > 0:
            inputs[name] = count
    print(recipe.format(output, str(inputs).replace('\'', ''), '{{{}: {}}}'.format(output, quantity), duration, crafter), end='')

print()
for crafter in crafters:
    print('{}: 1'.format(crafter))
