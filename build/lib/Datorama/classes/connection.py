import requests,json,pickle,os,inspect
from time import sleep
from pathlib import Path
from random import random
from datetime import datetime as dt

from Datorama import Bad_HTTP_Response

class Connect():
    ''' Connection class that retains the connection parameters. '''

    def __init__(self,datorama,api_token,verbose,pause,platform_rate_pause=10,query_rate_pause=1):
        self.conn_path = Path(os.path.dirname(inspect.getsourcefile(Connect) ) )
        self.log_path,self.instanceId = datorama.log_path,datorama.instanceId
        self.verbose,self.pause = verbose,pause
        self.api_url = 'https://api-us2.datorama.com'
        self.standard_header = {'Authorization':api_token,'Accept':'application/json','Content-Type':'application/json'}
        self.total_calls = 0
        self.platform_rate_pause,self.query_rate_pause = platform_rate_pause,query_rate_pause
        self.platform_rem,self.query_rem,self.daily_rem = 60,200,20000
        self.platform_reset,self.query_reset,self.daily_reset = None,None,None
        self.logs,self.log_error = datorama.logs,datorama.log_error
        self.call_history = {}


    def check_file_integrity(self):
        '''Checks the timestamp of the queue file to ensure that the file is current.'''

        try:
            with open(self.conn_path/'connection.temp','rb') as f:
                return pickle.load(f).get('timestamp') == self.last_update
        except: return False

        
    def load_connection(self):
        '''Loads the connection state file that contains the daily and active platform calls.'''

        main,temp = self.conn_path/'connection.main',self.conn_path/'connection.temp'

        retries = 0
        loaded,bkup = False,True
        while not loaded:
            if retries >= 50:
                if not bkup:
                    print('Backup failed and retries exceeded limit; Overwriting connection state.')
                    loaded = True

                print('Failed to load connection main and retries exceeded limit, fetching backup.')
                main = self.conn_path/'connection.bkup'
                bkup = False

            try:
                if not (os.path.exists(main) or os.path.exists(temp) ):
                    loaded = True
                if not os.path.exists(main):
                    raise FileNotFoundError()
                else:
                    os.rename(main,temp)
                    with open(temp,'rb') as f:
                        data = pickle.load(f)
                    self.platform_rem = data.get('platform_rem')
                    self.platform_reset = data.get('platform_reset')
                    self.query_rem = data.get('query_rem')
                    self.query_reset = data.get('query_reset')
                    self.daily_rem = data.get('daily_rem')
                    self.daily_reset = data.get('daily_reset')
                    self.last_update = data.get('timestamp')
                loaded = True

            except:
                sleep( random()/100 )
                retries += 1


    def save_connection(self):
        '''Updates the connection state file with the new daily and active platform calls.'''
        
        main,bkup,temp = self.conn_path/'connection.main',self.conn_path/'connection.bkup',self.conn_path/'connection.temp'

        retries = 0
        saved = False
        while not saved:
            if retries >= 100:
                print('Failed to save connection data and retries exceeded limit.')
                raise RuntimeError()
            try:
                if not self.check_file_integrity():
                    self.load_connection()
                data = {
                    'platform_rem':self.platform_rem,
                    'platform_reset':self.platform_reset,
                    'query_rem':self.query_rem,
                    'query_reset':self.query_reset,
                    'daily_rem':self.daily_rem,
                    'daily_reset':self.daily_reset,
                    'timestamp':dt.now().timestamp()
                }
                with open(self.conn_path/main,'wb') as f: pickle.dump(data,f)
                with open(self.conn_path/bkup,'wb') as f: pickle.dump(data,f)
                os.remove(temp)
                saved = True

            except:
                sleep( random()/100 )
                retries += 1


    def log_call(self,call_type,method,endpoint,status):

        self.call_history.update(
                {self.total_calls:{'call_type':call_type,'method':method,'endpoint':endpoint,'status':status}  }
            )
        with open(self.log_path/f'{self.instanceId}_call_log.json','w') as f:
            json.dump(self.call_history,f)
    

    def call(self,method,endpoint,body=None,call_type='platform'):
        '''Makes the api request; Raises error if response not 200 or 201.'''

        req = 'pre-submission'
        try:
            self.add_call(call_type)
            if body:
                body = json.dumps(body)
            req = requests.request(method=method,url=self.api_url + endpoint,headers=self.standard_header,data=body)
            self.log_call(call_type=call_type,method=method,endpoint=endpoint,status=req.status_code)

            self.update_rate_limits(req)
            if 'Too Many Requests' in str(req.content):
                sleep(10)
                self.call(method=method,endpoint=endpoint,body=body,call_type=call_type)
                
            if req.status_code not in [200,201]:
                if self.verbose:
                    print(f'\terror: {req.status_code}')
                raise Bad_HTTP_Response(req.status_code)

            if self.verbose:
                print( f'\tresponse: {req.status_code}' )
                print('- done -')
            
            sleep(self.pause)
            return req
        
        except Exception as X:
            try: req = req.content
            except: pass
            self.log_error(source_module='connection',function_triggered='call',error_raised=str(X),detail=req)


    def update_rate_limits(self,response):

        self.daily_reset = dt.fromtimestamp(int(response.headers.get('X-DailyQuota-Reset') )/1000)
        self.daily_rem = int(response.headers.get('X-DailyQuota-Remaining'))
        
        self.platform_reset = dt.fromtimestamp(int(response.headers.get('X-PlatformRateLimit-Reset') )/1000)
        self.platform_rem = int(response.headers.get('X-PlatformRateLimit-Remaining'))
        
        self.query_reset = dt.fromtimestamp(int(response.headers.get('X-QueryRateLimit-Reset') )/1000)
        self.query_rem = int(response.headers.get('X-QueryRateLimit-Remaining'))


    def add_call(self,call_type):
        '''Adds an interval to the api call count, warns every 5000th instance call, and triggers the active call updates.'''

        self.total_calls += 1
        self.load_connection()

        self.check_daily_calls()
        {'platform':self.check_platform_calls,'query':self.check_query_calls}[call_type]()

        if self.verbose:
            print(f'instance calls: {self.total_calls}')
        if self.total_calls%5000 == 0:
            print(f'warning: instance has made {self.total_calls} calls')

        self.save_connection()

    
    def check_daily_calls(self):
        '''Evaluate whether or not the daily call limit has been reached and waits for the reset if met.'''

        if self.daily_rem == 0:
            print(f'- daily rate limit reached, waiting for reset at {self.daily_reset} -')
            sleep( (self.daily_reset - dt.now() ).total_seconds() )


    def check_platform_calls(self):
        '''Checks the number of active calls and pauses for the set time if the limit is reached.'''

        if self.platform_rem == 0:
            print(f'- platform rate limit reached, reset occurs at {self.platform_reset} -')
            sleep(self.platform_rate_pause)

    
    def check_query_calls(self):
        '''Checks the number of active calls and pauses for the set time if the limit is reached.'''

        if self.query_rem == 0:
            print(f'- platform rate limit reached, reset occurs at {self.query_reset} -')
            sleep(self.query_rate_pause)