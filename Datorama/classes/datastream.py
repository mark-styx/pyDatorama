import requests,json,os,inspect
from time import sleep
from pathlib import Path
from random import random
from datetime import datetime as dt

from Datorama import Bad_HTTP_Response,DateInputError
from Datorama import Job

class Stream():

    def __init__(self,workspace,attributes=None,stream_id=None,restore_jobs=False):
        self.restore_path = Path(os.path.dirname(inspect.getsourcefile(Stream) ) )/'restoration/jobs'
        self.check_backup_folders()
        self.connection = workspace.connection
        self.queue_check,self.queue_eval = workspace.queue_check,workspace.queue_eval
        self.jobs,self.logs = workspace.jobs,workspace.logs
        self.log_error,self.log_update,self.log_job = workspace.log_error,workspace.log_update,workspace.log_job
        if stream_id:
            self.id = stream_id
            self.get_meta_data()
        if attributes:
            self.__dict__.update(attributes)
        if restore_jobs:
            self.restore_jobs()


    def check_backup_folders(self):

        if not os.path.exists(self.restore_path):
            if not os.path.exists(os.path.dirname(self.restore_path)):
                os.mkdir(os.path.dirname(self.restore_path) )
            os.mkdir(self.restore_path)


    def restore_jobs(self):
        try:
            with open(self.restore_path/f'{self.id}_jobs.json','r') as f:
                content = json.load(f)
            if self.id not in self.jobs: self.jobs[self.id] = {}
            for stat in content:
                self.jobs[self.id].update( {stat.get('id'):Job(self,attributes=stat) } )

        except FileNotFoundError:
            print(f'No restoration file for {self.id}')


    def get_meta_data(self,ret=False):
        ''' Gathers the meta data for the stream. If ret=True, the response is returned. '''

        try:
            if self.connection.verbose:
                print('- getting workspace metadata -')

            self.get_meta_data_response = self.connection.call(method='GET',endpoint=f'/v1/data-streams/{self.id}')
            output = self.get_meta_data_response.json()

            if ret:
                return output

            self.__dict__.update(output)

        except Exception as X:
            self.log_error(
                source_module='datastream',function_triggered='get_meta_data',error_raised=str(X),detail={'stream':self.id}
                )


    def delete(self):
        '''Deletes the stream.'''

        try:
            self.connection.call(method='delete',endpoint=f'/v1/data-streams/{self.id}')
            self.log_update(action='delete',obj=self.id)

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='delete',error_raised=str(X),detail={'stream':self.id} )


    def enable(self):
        '''Enables the stream.'''

        try:
            self.connection.call(method='patch',endpoint=f'/v1/data-streams/{self.id}',body={'enabled':True})
            self.log_update(action='enable',obj=self.id)

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='enable',error_raised=str(X),detail={'stream':self.id} )


    def disable(self):
        '''Disables the stream.'''

        try:
            self.connection.call(method='patch',endpoint=f'/v1/data-streams/{self.id}',body={'enabled':False})
            self.log_update(action='disable',obj=self.id)

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='disable',error_raised=str(X),detail={'stream':self.id} )


    def process(self,start,end,**kwargs):
        '''
        Process the input stream between the start and end date.
            Inputs:
                start (string)
                    formatted yyyy-mm-dd
                end (string)
                    formatted yyyy-mm-dd
        '''

        try:
            if not self.queue_check():
                return False

            if self.connection.verbose:
                print(f'- processing {self.id} from {start} through {end} -')

            if type(start) is str and ':' in start: raise DateInputError(start)
            if type(end) is str and ':' in end: raise DateInputError(end)

            payload = {'startDate':start,'endDate':end}
            self.process_response = self.connection.call(method='POST',endpoint=f'/v1/data-streams/{self.id}/process',body=payload)
            self.process_content = self.process_response.json()

            for job in self.process_content:
                self.log_job(workspace=self.__dict__.get('workspaceId'),stream=self.id,job=job.get('id'),job_type='process',start=job.get('dataStartDate'),end=job.get('dataEndDate') )

            self.queue_eval()
            return True

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='process',error_raised=str(X),detail={'stream':self.id} )
            self.log_job(workspace=self.__dict__.get('workspaceId'),stream=self.id,job='na',job_type='process',start=start,end=end,isError=True)
            return 'failed'


    def get_mapping(self):
        '''Gets the current mapping of the datastream.'''

        try:
            if self.connection.verbose:
                print(f'- getting stream mapping for {self.id} -')

            self.get_mapping_response = self.connection.call(method='GET',endpoint=f'data-streams/api/{self.id}/mapping')
            self.mapping = self.get_mapping_response.json()

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='get_mapping',error_raised=str(X),detail={'stream':self.id} )


    def update_mapping(self,params):
        '''
        Update the mapping configuration for a data stream.
            Inputs:
                params (dictionary)
        '''

        try:
            if self.connection.verbose:
                print(f'- updating stream mapping for {self.id} -')

            self.get_mapping()
            old_params = self.mapping

            self.mapping.update(params)
            self.update_mapping_response = self.connection.call(method='PUT',endpoint=f'data-streams/api/{self.id}/mapping',body=self.mapping)

            self.logs['update_log'].append(
                {'stream':self.id,'new_params':params,'old_params':old_params,'status':'success','timestamp':dt.now() }
            )

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='update_mapping',error_raised=str(X),detail={'stream':self.id} )
            self.logs['update_log'].append( {'stream':self.id,'params':str(params),'status':'failed','timestamp':dt.now() } )


    def update_stream(self,params):
        '''
        Updates a data stream based on the passsed parameters.
            Inputs:
                stream (integer or string)
                params (dictionary)
        '''

        try:
            if self.connection.verbose:
                print(f'- updating stream: {self.id} -')

            stream_meta = self.get_meta_data(True)
            stream_meta.update(params)
            self.update_response = self.connection.call(method='PUT',endpoint=f'/v1/data-streams/{self.id}',body=stream_meta)

            old_params = {attr:self.__dict__.get(attr) for attr in self.__dict__ if attr in params}

            self.logs['update_log'].append(
                {'stream':self.id,'new_params':params,'old_params':old_params,'status':'success','timestamp':dt.now() }
            )

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='update_stream',error_raised=str(X),detail={'stream':self.id} )
            self.logs['update_log'].append( {'stream':self.id,'params':str(params),'status':'failed','timestamp':dt.now() } )


    def patch(self,params):
        '''
        Patches the data stream based on the input parameters.
            Inputs:
                params (dictionary)
                    ex. {'name':'new stream name'}
        '''

        try:
            if self.connection.verbose:
                print(f'- patching stream: {self.id} -')

            self.patch_response = self.connection.call(method='patch',endpoint=f'/v1/data-streams/{self.id}',body=params)
            self.log_update(action='patch',obj=self.id,detail=params)

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='patch',error_raised=str(X),detail={'stream':self.id} )


    def rerun_all_jobs(self,*args):
        ''' Rerun all jobs for the data stream. '''

        try:
            if not self.queue_check():
                return False

            if self.connection.verbose:
                print(f'- rerunning stream: {self.id} -')

            self.rerun_all_response = self.connection.call(method='POST',endpoint=f'/v1/data-streams/api/{self.id}/rerun-all')
            self.rerun_all_content = self.rerun_all_response.json()

            for job in self.rerun_all_content:
                self.log_job(workspace=self.__dict__.get('workspaceId'),stream=self.id,job=job.get('id'),job_type='rerun',start=job.get('dataStartDate'),end=job.get('dataEndDate') )

            self.queue_eval()
            return True

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='rerun_all_jobs',error_raised=str(X),detail={'stream':self.id} )
            return 'failed'


    def get_stream_runs(self,pgSize=100,pgNum=1):
        '''
        Post request to return the list of stream stats by workstream id. Set to page size of 150.
            Inputs:
                pgSize (integer)
                    Not really relevant now as the page numbers should loop until there are no more rows.
                pgNum (integer)
                    Not really relevant now as the page numbers should loop until there are no more rows.
        '''

        try:
            if self.connection.verbose:
                print( f'- getting stream runs for: {self.id} -' )

            endOfList = False;all_content = []
            while not endOfList:

                try:
                    payload = {'pageSize':pgSize,'pageNumber':pgNum}
                    self.runs_response = self.connection.call(method='POST',endpoint=f'/v1/data-streams/api/{self.id}/stats',body=payload)
                    self.runs_content = self.runs_response.json()

                    if len(self.runs_content) < pgSize:
                        endOfList = True

                    if self.id not in self.jobs: self.jobs[self.id] = {}
                    all_content.extend(self.runs_content)
                    for stat in self.runs_content:
                        self.jobs[self.id].update( {stat.get('id'):Job(self,attributes=stat) } )

                    pgNum += 1 # Next page

                except:
                    endOfList = True

            self.store_jobs(all_content)

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='get_stream_runs',error_raised=str(X),detail={'stream':self.id} )


    def store_jobs(self,job_content):
        ''

        retries = 0;saved = False
        while not saved and retries < 10:
            try:
                with open(self.restore_path/f'{self.id}_jobs.json','w') as f:
                    json.dump(job_content,f)
                saved = True
            except:
                retries += 1
                sleep(random() )
        if retries == 10:
            raise RuntimeError()


    def rerun_job_batch(self,job_ids,**kwargs):
        '''
        Rerun a list of job ids for a single datastream id.
            Inputs:
                job_ids (list, integer, or string)
        '''

        try:
            if not self.queue_check():
                return False

            if self.connection.verbose:
                print(f'- rerunning stream: {self.id} job_ids: {job_ids} -')

            if type(job_ids) is not list: job_ids = [job_ids]

            self.rerun_response = self.connection.call(method='POST',endpoint=f'/v1/data-streams/api/{self.id}/rerun',body=job_ids)
            self.rerun_content = self.rerun_response.json()

            for job in self.rerun_content:
                self.log_job(workspace=self.__dict__.get('workspaceId'),stream=self.id,job=job.get('id'),job_type='rerun',start=job.get('dataStartDate'),end=job.get('dataEndDate') )

            self.queue_eval()
            return True

        except Exception as X:
            self.log_error(source_module='datastream',function_triggered='rerun_job_batch',error_raised=str(X),detail={'stream':self.id} )
            for job in job_ids:
                self.log_job(workspace=self.__dict__.get('workspaceId'),stream=self.id,job=job,job_type='rerun',start='na',end='na',isError=True)
            return 'failed'