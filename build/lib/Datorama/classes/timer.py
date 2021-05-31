import pandas as pd
from datetime import datetime as dt
from datetime import timedelta as td

class Timer():
    
    def __init__(self,length):
        ''
        self.start = dt.now()
        self.length = length

    def update(self,index):
        ''
        if index:
            self.elapsed = (dt.now() - self.start).total_seconds()
            self.completion_pct = round( (index/self.length)*100 )
            self.est_completion = dt.now() + td(seconds=(self.elapsed*self.length)/index)
            self.feedback()

    def feedback(self):
        ''
        print(f'current time: {dt.now()}')
        print(f'total elapsed time: {self.elapsed}')
        print(f'{self.completion_pct}% completed')
        print(f'estimated completion time: {self.est_completion}')