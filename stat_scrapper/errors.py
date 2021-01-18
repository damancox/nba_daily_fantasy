class TeamAbbrevError(Exception):
    
    def __init__(self, abbrev):
        self.abbrev = abbrev
        super().__init__(self.abbrev)
        
    def __str__(self):
        return f'{self.abbrev} -> Does not exist or not of length 3 characters'
    
    