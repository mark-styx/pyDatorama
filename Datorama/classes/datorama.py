import requests,time,os,pickle,inspect,json
import numpy as np
import pandas as pd
from math import ceil
from time import sleep
from pathlib import Path
from random import random
from datetime import datetime as dt

from Datorama import Connect,Workspace,Bad_HTTP_Response,Unequal_Input_Error,Timer

class datorama():
    '''
    Main class representing the parent Datorama object.
        Inputs:
            api_token (str)
                The api token provided by Datorama.
            verbose (boolean)
                Determines the amount of feedback to be returned to the user. Useful for debugging.
            pause (int,float)
                The length of time to sleep between standard iterated requests.
    '''


    def __init__(self,api_token,verbose=False,pause=.5,platform_rate_pause=30,restore_spaces=True,restore_streams=True,restore_jobs=False):
        self.instanceId = int(dt.now().timestamp()*1000)
        self.restore_path = Path(os.path.dirname(inspect.getsourcefile(datorama) ) )/'restoration/workspaces'
        self.log_path = Path(os.path.dirname(inspect.getsourcefile(datorama) ) )/'restoration/logs'
        self.check_backup_folders()
        self.logs = {'job_log':{},'update_log':[],'error_log':{},'maintenance':{} }
        self.connection = Connect(
            datorama=self,api_token=api_token,verbose=verbose,pause=pause,platform_rate_pause=platform_rate_pause
        )
        self.workspaces,self.streams,self.jobs = {},{},{}
        if restore_spaces:
            self.restore_spaces(restore_streams=restore_streams,restore_jobs=restore_jobs)
        else:
            self.get_workspaces()


    def check_backup_folders(self):

        if not os.path.exists(self.restore_path):
            if not os.path.exists(os.path.dirname(self.restore_path)):
                os.mkdir(os.path.dirname(self.restore_path) )
            os.mkdir(self.restore_path)

        if not os.path.exists(self.log_path):
            os.mkdir(self.log_path)


    def restore_spaces(self,restore_streams,restore_jobs):

        with open(self.restore_path/'spaces.json','r') as f:
            content = json.load(f)

        self.workspaces = {ws.get('id'):Workspace(self,attributes=ws) for ws in content}

        if restore_streams:
            for space in self.workspaces.values(): space.restore_streams()

        if restore_jobs:
            for stream in self.streams.values(): stream.restore_jobs()


    def log_error(self,source_module,function_triggered,error_raised,detail):
        '''Adds record to the error log.'''

        self.logs['error_log'].update(
                { (len(self.logs['error_log'])+1):{'module':source_module,'function':function_triggered,'timestamp':str(dt.now() ),'error_raised':error_raised,'detail':str(detail) } }
            )
        with open(self.log_path/f'{self.instanceId}_error_log.json','w') as f:
            json.dump(self.logs['error_log'],f)


    def log_update(self,action,obj,detail=None):
        '''Adds record to the error log.'''

        self.logs['maintenance'].update(
                { (len(self.logs['maintenance'])+1):{'action':action,'object':obj,'detail':detail,'timestamp':str(dt.now() )} }
            )


    def log_job(self,workspace,stream,job,job_type,start,end,isError=False):
        '''Add a record to the job log.'''

        status = 'queued'
        if isError:
            status = 'error'

        if workspace not in self.logs['job_log']: self.logs['job_log'][workspace] = {}
        if stream not in self.logs['job_log'][workspace]: self.logs['job_log'][workspace][stream] = {}

        self.logs['job_log'][workspace][stream].update(
            {job:{
                'workspace':workspace,'stream':stream,'job':job,
                'job_type':job_type,'start':start,'end':end,'status':status,
                'exec_start':str( dt.now() ),'exec_end':'nat'
                }
            }
        )

        with open(self.log_path/f'{self.instanceId}_job_log.json','w') as f:
            json.dump(self.logs['job_log'],f)


    def get_workspaces(self):
        '''Get request to pull the metadata for all workspaces from the api.'''

        try:
            if self.connection.verbose:
                print('getting workspaces')

            self.get_workspaces_response = self.connection.call(method='GET',endpoint='/v1/workspaces')
            self.ws_content = self.get_workspaces_response.json()
            self.workspaces = {ws.get('id'):Workspace(self,attributes=ws) for ws in self.ws_content}
            self.store_spaces()

        except Exception as X:
            self.log_error(source_module='datorama',function_triggered='get_workspace',error_raised=str(X),detail='No valid response')


    def store_spaces(self):
        ''

        retries = 0;saved = False
        while not saved and retries < 10:
            try:
                with open(self.restore_path/'spaces.json','w') as f:
                    json.dump(self.ws_content,f)
                saved = True
            except:
                retries += 1
                sleep(random() )
        if retries == 10:
            raise RuntimeError()


    def get_all_dimensions(self):
        '''Loop through all workspaces and retrieve the dimensions.'''

        print('- getting dimensions for all workspaces -')

        print('\tmaking calls to api')
        self.dimensions = {}
        cnt = len(self.workspaces)
        rtimer = Timer(cnt)
        for idx,space in enumerate(self.workspaces):
            self.workspaces.get(space).get_dimensions()
            self.dimensions.update( {space:self.workspaces.get(space).dimensions} )
            rtimer.update(idx)
        print('\tdone')


    def create_stream_df(self,export=False,export_name='Datorama Stream Meta Data.csv',fields=None):
        '''
        Creates a pandas data frame from the stream data.
            Inputs:
                export (boolean)
                    Whether to export the resulting data frame to a csv file.
                export_name (str)
                    The output filename with extension. Must be a csv file.
        '''

        if not self.streams:
            self.get_all_streams()

        if not fields:
            fields = [
                    'id','name','dataSourceId','sourceDisplayName','workspaceId',
                    'enabled','hasData','dataSourceAuthenticationId','createTime',
                    'lastUpdate','lastRunStatus','lastRowsRetrieved','processedRows',
                    'lastDataDate'
                ]

        print('- creating stream data frame -')
        self.stream_meta = []
        for stream in self.streams.values():
            self.stream_meta.append( {x:stream.__dict__.get(x) for x in stream.__dict__ if x in fields} )

        self.stream_df = pd.DataFrame(self.stream_meta).reset_index()
        self.stream_df['createTime'] = pd.to_datetime(self.stream_df['createTime'],unit='ms')
        self.stream_df['lastUpdate'] = pd.to_datetime(self.stream_df['lastUpdate'],unit='ms')

        if export:
            self.stream_df.to_csv(export_name,index=False)
        print('- done -')


    def get_all_streams(self,workspaces=None):
        '''Loops through all workspace objects and triggers each ones 'get_streams' function.'''

        print('- getting metadata for all streams -')
        if not workspaces:
            workspaces = self.workspaces
        else:
            workspaces = {k:v for k,v in self.workspaces.items() if v.id in workspaces}

        print('\tmaking calls to api')
        cnt = len(workspaces)
        rtimer = Timer(cnt)
        for idx,space in enumerate(workspaces):
            self.workspaces.get(space).get_streams()
            rtimer.update(idx)
        print('- done -')


    def create_jobs_df(self,export=False,export_name='Datorama Job Run Data.csv'):
        '''
        Creates a pandas data frame from the jobs data.
            Inputs:
                export (boolean)
                    Whether to export the resulting data frame to a csv file.
                export_name (str)
                    The output filename with extension. Must be a csv file.
        '''

        if not self.jobs:
            self.get_all_jobs()

        print('- creating job data frame -')

        exclusions = ['connection','logs','log_error','log_job']

        job_meta = []
        for stream in self.jobs.values():
            for job in stream.values():
                job_meta.append( {x:job.__dict__.get(x) for x in job.__dict__ if x not in exclusions} )

        self.jobs_df = pd.DataFrame(job_meta).reset_index()
        self.jobs_df['startExecutionTime'] = pd.to_datetime(self.jobs_df['startExecutionTime'],unit='ms')
        self.jobs_df['endExecutionTime'] = pd.to_datetime(self.jobs_df['endExecutionTime'],unit='ms')

        if export:
            self.jobs_df.drop(columns='processLog').to_csv(export_name,index=False)
        print('- done -')


    def get_all_jobs(self,pgSize=100,pgNum=1):
        '''Loops through all data stream objects and triggers each ones 'get_stream_runs' function.'''

        print('- getting metadata for all stream runs -')
        if not self.streams:
            self.get_all_streams()

        print('\tmaking calls to api')
        cnt = len(self.streams)
        rtimer = Timer(cnt)
        for idx,stream in enumerate(self.streams):
            self.streams.get(stream).get_stream_runs(pgSize=pgSize,pgNum=pgNum)
            rtimer.update(idx)
        print('- done -')


    def create_job_log_df(self,log_file='job_log.csv',export=False):
        '''
                log_file (str)
                    The output filename with extension for the process log. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
                error_file (str)
                    The output filename with extension for the error log. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
                export (boolean)
                    Whether to export the resulting data frame to a csv file.
        '''

        jobs = self.logs['job_log']
        job_log = pd.DataFrame( [job for space in jobs.values() for stream in space.values() for job in stream.values()] )
        if export:
            if log_file and os.path.exists(log_file):
                old_log = pd.read_csv(log_file)
                job_log = job_log.append(old_log)
            job_log = job_log.drop_duplicates()
            job_log.to_csv(log_file,index=False)
        self.jldf = job_log


    def bulk_rename_streams(self,streams,names,export=True,update_file='update_log.csv'):
        '''
        Packages the name into a dictionary and passes it to the streams' 'update_stream' function.
            Inputs:
                streams (integer, string, or list)
                names (string or list)
                update_file (str)
                    The output filename with extension for the update log. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
                export (boolean)
                    Whether to export the resulting data frame to a csv file.
        '''

        if not self.streams:
            self.get_all_streams()

        if type(streams) not in (str,int) and type(names) not in (str,int):    
            if not (len(streams) == len(names) ):
                raise Unequal_Input_Error()
        else:
            streams,names = [streams],[names]

        cnt = len(streams)
        rtimer = Timer(cnt)
        print(f'- updating {cnt} streams -')
        for idx,(stream,name) in enumerate( zip(streams,names) ):
            self.streams.get(stream).update_stream( {'name':name} )
            rtimer.update(idx)

        if export:
            update_log = pd.DataFrame(self.logs['update_log'])
            if update_file and os.path.exists(update_file):
                old_update_log = pd.read_csv(update_file)
                update_log = update_log.append(old_update_log)
            update_log.to_csv(update_file,index=False)
        print('- done -')


    def execute_job(self,job_dict,job_type,create_df=True,export=False,file_name='job_log',sleep_cadence=60):
        '''
        The main execution flow for completing jobs in datorama. Workspaces are aware of the number of pending jobs that are allocated,
        the event loop will skip jobs if the workspace is too busy and will wait to recheck the space until it has had 
        adequate time to complete the task.
            Inputs
                job_dict (dictionary)
                    Dictionary of jobs to run in the format: {'stream':12345,'status':'na','params':{} }
                job_type (str)
                    String representation of job type. One of rerun_batch, rerun_all, or process. Hashes a dictionary to output the proper stream function.
                create_df (boolean)
                    Whether to create a dataframe from the resulting jobs.
                export (boolean)
                    Whether to export the resulting dataframe to a csv file.
                file_name (str)
                    The output filename with extension. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
                sleep_cadence (int)
                    The number of seconds to pause in the event that all workspaces are busy.
        '''

        job_funct = lambda x: {'rerun_batch':x.rerun_job_batch,'rerun_all':x.rerun_all_jobs,'process':x.process}[job_type]
        all_jobs_submitted = lambda: all( [x.get('status') in ['submitted','failure'] for x in job_dict] )
        submitted_count = lambda: len( [1 for x in job_dict if x.get('status') in ['submitted','failure'] ] )
        spaces_with_jobs_left = lambda: set([x.get('workspace') for x in job_dict if x.get('status') not in ['submitted','failure'] ])
        bandwidth = lambda: any( [space.pending < space.queue_max for space in self.workspaces.values() if space.id in spaces_with_jobs_left() ] )

        if not self.streams:
            self.get_all_streams()

        all_jobs_complete = False
        print(f'- executing {len(job_dict)} jobs -')
        rtimer = Timer(len(job_dict) )
        while not all_jobs_complete:
            for job in job_dict:
                if job.get('status') in ['submitted','failure']:
                    continue
                else:
                    job_stream = self.streams.get(job.get('stream') )
                    if not job_stream:
                        self.log_error(
                            source_module='datorama',function_triggered='bulk_rerun_all',
                            error_raised='Suppressed',detail=f'stream {job.get("stream")} not found'
                        )
                        continue
                    exec_stat = job_funct(job_stream)(**job.get('params') )
                    if not exec_stat:
                        continue
                    if exec_stat == 'failed':
                        job.update( {'status':'failure'} )
                        continue
                    job.update( {'status':'submitted'} )

            total = sum( [space.pending for space in self.workspaces.values() ] )
            print(f'total pending: {total}')

            if all_jobs_submitted():
                if all( [space.ws_state != 'active' for space in self.workspaces.values()] ):
                    print('all spaces finished')
                    all_jobs_complete = True
                if total == 0:
                    print('all jobs finished')
                    all_jobs_complete = True

            for space in self.workspaces.values():
                if space.ws_state == 'active':
                    space.queue_check()
            rtimer.update(submitted_count() )
            if all_jobs_submitted() or not bandwidth():
                print(f'no bandwidth for additional jobs, pausing for {sleep_cadence} seconds')
                sleep(sleep_cadence)

        if create_df:
            self.create_job_log_df(
                log_file=f"{file_name} {job_type} {dt.now().strftime('%Y-%m-%d %H_%M_%S')}.csv",
                export=export
            )
        print('- done -')


    def rerun_all(self,streams,create_df=True,export=False,file_name='job_log'):
        '''
        Iterates a list of datastreams and executes each's 'rerun_all' function.
            Inputs:
                streams (list)
                    List representing the stream that each job belongs to.
                jobs (list)
                    List representing the job ids to rerun.
                create_df (boolean)
                    Whether to create a dataframe from the resulting jobs.
                export (boolean)
                    Whether to export the resulting dataframe to a csv file.
                file_name (str)
                    The output filename with extension. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
        '''

        jobs = [ {'stream':stream,'status':'na'} for stream in streams]
        self.execute_job(
            job_dict=jobs,job_type='rerun_all',
            create_df=create_df,export=export,file_name=file_name
        )
        print('- finished -')


    def rerun_batch(self,streams,jobs,create_df=True,export=False,file_name='job_log'):
        '''
        Groups the jobs by their stream and passes the list of jobs to the streams' 'rerun_job_batch' function.
            Inputs:
                streams (list)
                    List representing the stream that each job belongs to.
                jobs (list)
                    List representing the job ids to rerun.
                create_df (boolean)
                    Whether to create a dataframe from the resulting jobs.
                export (boolean)
                    Whether to export the resulting dataframe to a csv file.
                file_name (str)
                    The output filename with extension. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
        '''

        rerun_df = pd.DataFrame( {'stream':streams,'job':jobs} )
        jobs = [ {'stream':stream,'status':'na'} for stream in rerun_df.stream.unique() ]
        for x in jobs:
            batch = rerun_df[rerun_df['stream'] == x.get('stream')]['job'].to_list()
            x.update( {'params':{'job_ids':batch}} )

        self.execute_job(
            job_dict=jobs,job_type='rerun_batch',
            create_df=create_df,export=export,file_name=file_name
        )
        print('- finished -')


    def process_streams(self,streams,starts,ends,d_range=10,create_df=True,export=False,file_name='job_log'):
        '''
        Process an iterable of stream ids using the process_stream() function. Streams, starts, and ends must be the same length.
            Inputs:
                streams (iterable)
                    The list, array, or series representing the list of stream ids to process.
                starts (iterable)
                    The list, array, or series representing the list of start dates to process.
                ends (iterable)
                    The list, array, or series representing the list of end dates to process.
                d_range (integer)
                    Days to partition the day range by.
                create_df (boolean)
                    Whether to create a dataframe from the resulting jobs.
                export (boolean)
                    Whether to export the resulting dataframe to a csv file.
                file_name (str)
                    The output filename with extension. Must be a csv file.
                    For the previous log to be appended, the filename must be the same.
        '''

        if not ( len(streams) == len(starts) == len(ends) ):
            raise Unequal_Input_Error()

        jobs = []
        for (s,st,en) in zip(streams,starts,ends):
            for stream,start,end in self.date_partition_check(s,st,en,d_range):
                jobs.append( {'stream':stream,'params':{'start':start,'end':end},'status':'na'} )

        self.execute_job(
            job_dict=jobs,job_type='process',
            create_df=create_df,export=export,file_name=file_name
        )
        print('- finished -')


    def process_stream_batch(self,streams,start_date,end_date):
        '''Process a list of streams that share the same process date range.'''

        try:
            payload = {
                'dataStreamIds':streams,
                'startDate':start_date,'endDate':end_date,'create':False
            }
            self.connection.call(method='post',endpoint='/v1/data-streams/process',body=payload)
            for stream in streams:
                self.log_job(
                    workspace=self.streams[stream].workspaceId,stream=stream,job='generic',
                    job_type='batch_processing',start=start_date,end=end_date
                    )

        except Exception as X:
            self.log_error(
                source_module='datorama',function_triggered='process_stream_batch',error_raised=str(X),detail=payload
                )
            for stream in streams:
                self.log_job(
                    workspace=self.streams[stream].workspaceId,stream=stream,job='generic',
                    job_type='batch_processing',start=start_date,end=end_date,isError=True
                    )


    def date_partition_check(self,stream,start,end,d_range):
        '''Partitions a date range into chunks based on the d_range.'''

        days = pd.DatetimeIndex(start=start, end=end, freq='D').tolist()
        if len(days) > d_range:
            days = np.array_split(days,ceil(len(days)/d_range) )
            st_part = [str(d[0].date() ) for d in days]
            en_part = [str(d[-1].date() ) for d in days]
            return [(stream,st_pt,en_pt) for st_pt,en_pt in zip(st_part,en_part)]
        else:
            return [(stream,start,end)]


    def download_stats(self,folder_path):
        '''
        Loop through the jobs dictionary and collect the statistic files.
        '''

        try:
            for stream in self.jobs.values():
                for job in stream.values():
                    try: job.download(folder_path=folder_path)
                    except Exception as X:
                        self.log_error(
                            source_module='datorama',function_triggered='download_stats',error_raised=str(x),detail={'stream':stream.id,'job':job.id}
                            )

        except Exception as X:
            self.log_error(
                source_module='datorama',function_triggered='download_stats',error_raised=str(x),detail='general'
                )