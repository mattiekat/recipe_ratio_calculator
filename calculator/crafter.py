class Crafter:
    def __init__(self, name: str, efficiency: float):
        self.name = name
        self.efficiency = efficiency

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.name
