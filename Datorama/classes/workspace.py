import requests,json,inspect,os
from time import sleep
from pathlib import Path
from random import random
from datetime import datetime as dt

from Datorama import Bad_HTTP_Response,MissingStreamName
from Datorama import Stream


class Workspace():
    ''' Workspace class to represent the Datorama workspace object. '''

    def __init__(self,datorama,attributes=None,workspace_id=None,queue_max=15,restore_streams=False,throttle_jobs=False):
        self.restore_path = Path(os.path.dirname(inspect.getsourcefile(Workspace) ) )/'restoration/streams'
        self.check_backup_folders()
        self.ws_state = 'idle';self.ws_state_ts = dt.now()
        self.pending,self.queue_max,self.throttle = 0,queue_max,throttle_jobs
        self.logs,self.jobs = datorama.logs,datorama.jobs
        self.log_error,self.log_update,self.log_job = datorama.log_error,datorama.log_update,datorama.log_job
        self.streams,self.connection = datorama.streams,datorama.connection
        if workspace_id:
            self.id = workspace_id
            self.get_meta_data()
        if attributes:
            self.__dict__.update(attributes)
        if restore_streams:
            self.restore_streams()


    def check_backup_folders(self):

        if not os.path.exists(self.restore_path):
            if not os.path.exists(os.path.dirname(self.restore_path)):
                os.mkdir(os.path.dirname(self.restore_path) )
            os.mkdir(self.restore_path)


    def restore_streams(self):

        with open(self.restore_path/f'{self.id}_streams.json','r') as f:
            content = json.load(f)
        for dstr in content:
            self.streams.update( {dstr.get('id'):Stream(self,attributes=dstr) } )


    def get_meta_data(self):
        '''Get the metadata for the workspace.'''

        try:
            if self.connection.verbose:
                print('getting workspace metadata')

            self.get_meta_data_response = self.connection.call(method='GET',endpoint=f'/v1/workspaces/{self.id}')
            self.__dict__.update(self.get_meta_data_response.json() )

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='get_meta_data',error_raised=str(X),detail={'workspace':self.id} )


    def queue_check(self):
        '''Checks the jobs that have been submitted to determine how many are still pending.'''

        if not self.throttle:
            return True

        check = lambda: self.pending < self.queue_max

        if (dt.now() - self.ws_state_ts).total_seconds() < (self.pending//10 * 10):
            return False

        print(f'- updating {self.id} job queue -')
        pending = self.pending_queue()
        streams = list(set([x.get('stream') for x in pending] ) )

        for stream in streams:
            self.streams.get(stream).get_stream_runs()

        for item in pending:
            stream,job = item.get('stream'),item.get('job')

            job_instance = self.jobs[stream].get(job)
            queue = self.logs['job_log'].get(self.id)

            queue[stream][job].update( {'status':job_instance.status.lower() } )
            if job_instance.status.lower() in ['success']:
                try:
                    completed = dt.strptime(job_instance.processLog.split('[')[-1].split(']')[0][:-1],r'%Y-%m-%d %H:%M:%S')
                except:
                    completed = dt.now()
                queue[stream][job].update( {'exec_end':str(completed)} )

        self.queue_eval()
        return check()


    def queue_eval(self):
        '''Evaluate the number of pending jobs.'''

        try:
            self.ws_state_ts = dt.now()
            self.pending = len(self.pending_queue() )
            if self.pending and self.pending > 0:
                print(f'pending jobs for {self.id}: {self.pending}')
                self.ws_state = 'active'
            else:
                self.ws_state = 'ready'

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='queue_eval',error_raised=str(X),detail={'workspace':self.id} )
            raise RuntimeError()


    def pending_queue(self):
        '''Update the pending jobs based on the job log.'''

        try:
            queue = self.logs['job_log'].get(self.id)
            if not queue:
                return []
            return [ {'stream':job.get('stream'),'job':job.get('job')} for stream in queue.values() for job in stream.values() if job.get('status') not in ['success','failure','error'] ]

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='pending_queue',error_raised=str(X),detail={'workspace':self.id} )
            raise RuntimeError()


    def get_dimensions(self):
        '''Get the list of dimensions used in the workspace.'''

        try:
            if self.connection.verbose:
                print(f'- getting dimensions for workspace {self.id} -')

            self.get_dimensions_response = self.connection.call(method='GET',endpoint=f'/v1/workspaces/{self.id}/dimensions')
            self.dimensions = self.get_dimensions_response.json()

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='get_dimensions',error_raised=str(X),detail={'workspace':self.id} )


    def get_harmonized_dimensions(self):
        '''Get the list of harmonized dimensions used in the workspace.'''

        try:
            if self.connection.verbose:
                print(f'- getting harmonized dimensions for workspace {self.id} -')

            self.get_harmonized_dimensions_response = self.connection.call(method='GET',endpoint=f'/v1/workspaces/{self.id}/harmonized-dimensions')
            self.harmonized_dimensions = self.get_harmonized_dimensions_response.json()

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='get_dimensions',error_raised=str(X),detail={'workspace':self.id} )


    def get_patterns(self):
        '''Get the list of patterns used in the workspace.'''

        try:
            if self.connection.verbose:
                print(f'- getting patterns for workspace {self.id} -')

            self.get_patterns_response = self.connection.call(method='GET',endpoint=f'/v1/workspaces/{self.id}/patterns')
            self.patterns = self.get_patterns_response.json()

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='get_patterns',error_raised=str(X),detail={'workspace':self.id} )


    def create_pattern(self,params):
        '''Creates a pattern based on the input parameters.'''

        try:
            if self.connection.verbose:
                print(f'- getting patterns for workspace {self.id} -')

            self.create_pattern_response = self.connection.call(method='POST',endpoint=f'/v1/harmonization/patterns',body=params)

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='create_pattern',error_raised=str(X),detail={'workspace':self.id} )


    def get_streams(self):
        '''
        Get request to pull the list of workstreams by workspace id.
        Initializes the 'streams' attribute and populates the list from the api json response.
        '''

        try:
            if self.connection.verbose:
                print(f'- getting data streams for {self.id} -')


            self.get_streams_response = self.connection.call(method='GET',endpoint=f'/v1/workspaces/{self.id}/data-streams')
            streams_content = self.get_streams_response.json()
            self.store_streams(streams_content)

            for dstr in streams_content:
                self.streams.update( {dstr.get('id'):Stream(self,attributes=dstr) } )

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='get_streams',error_raised=str(X),detail={'workspace':self.id} )


    def store_streams(self,stream_content):
        ''

        retries = 0;saved = False
        while not saved and retries < 10:
            try:
                with open(self.restore_path/f'{self.id}_streams.json','w') as f:
                    json.dump(stream_content,f)
                saved = True
            except:
                retries += 1
                sleep(random() )
        if retries == 10:
            raise RuntimeError()


    def get_calculated_measurements(self):
        '''Gets the calculated measurements for the workspace.'''

        try:
            if self.connection.verbose:
                print(f'- getting calculated measures for {self.id} -')


            self.get_calc_measures_response = self.connection.call(method='GET',endpoint=f'/v1/workspaces/{self.id}/calculated-measurements')
            self.calculated_measures = self.get_calc_measures_response.json()

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='get_calculated_measurements',error_raised=str(X),detail={'workspace':self.id} )


    def create_calculated_measurement(self,params):
        '''Create calculated measurement in the active workspace.'''

        try:
            if self.connection.verbose:
                print(f'- getting calculated measures for {self.id} -')

            self.create_calc_measures_response = self.connection.call(method='POST',endpoint=f'/v1/workspaces/{self.id}/calculated-measurements',body=params.update( {'workspaceId':self.id} ) )

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='create_calculated_measurement',error_raised=str(X),detail={'workspace':self.id} )


    def create_stream(self,params):
        '''Create a data stream in the active workspace based on the input parameters.'''

        try:
            if not params.get('name'):
                if self.connection.verbose:
                    print('Input parameters missing stream name.')
                raise MissingStreamName()

            if self.connection.verbose:
                print(f'- creating data stream {params.get("name")} -')

            self.create_response = self.connection.call(method='POST',endpoint='/v1/data-streams',body=params)

            stream_content = self.create_response.json()
            self.streams.update( {stream_content.get('id'):stream_content} )

        except Exception as X:
            self.log_error(source_module='workspace',function_triggered='create_stream',error_raised=str(X),detail={'workspace':self.id} )