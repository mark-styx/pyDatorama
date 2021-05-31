import requests,json
from datetime import datetime as dt

from Datorama import Bad_HTTP_Response


class Job():
    def __init__(self,stream,attributes=None,job_id=None):
        self.connection = stream.connection
        self.workspaceId,self.streamId = stream.workspaceId,stream.id
        self.dataSourceName = stream.dataSourceName
        self.log_error,self.log_job = stream.log_error,stream.log_job
        self.logs = stream.logs
        if job_id:
            self.id = job_id
            self.get_meta_data()
        if attributes:
            self.__dict__.update(attributes)


    def get_meta_data(self):
        ''' Retreives the meta data for the job. '''

        try:
            if self.connection.verbose:
                print('- getting workspace metadata -')

            self.get_meta_data_response = self.connection.call(method='GET',endpoint=f'/v1/data-stream-stat/{self.id}')

            output = self.get_meta_data_response.json()
            self.__dict__.update(output)
            
        except Exception as X:
            self.log_error(source_module='run_stat',function_triggered='get_meta_data',error_raised=str(X),detail={'workspace':self.id,'api_response':str(self.get_meta_data_response.content) } )


    def rerun(self):
        ''' Rerun the job. '''

        try:
            if self.connection.verbose:
                print(f'- rerunning stream: {self.streamId} job_id: {self.id} -')
            
            self.rerun_response = self.connection.call(method='POST',endpoint=f'/v1/data-streams/api/{self.streamId}/rerun',body=[self.id])
            self.rerun_content = self.rerun_response.json()
            self.log_job(workspace=self.workspaceId,stream=self.streamId,job=self.id,job_type='rerun',start=self.rerun_content.get('dataStartDate'),end=self.rerun_content.get('dataEndDate') )

        except Exception as X:
            self.log_error(source_module='run_stat',function_triggered='rerun',error_raised=str(X),detail={'stream':self.streamId,'job_id':self.id,'api_response':str(self.rerun_response.content) } )
            self.log_job(workspace=self.workspaceId,stream=self.streamId,job=self.id,job_type='rerun',start=self.rerun_content.get('dataStartDate'),end=self.rerun_content.get('dataEndDate'),isError=True)


    def download(self,folder_path):
        '''
        Downloads the raw data files from the stat.
        '''

        try:
            if self.connection.verbose:
                print(f'- downloading statistic data for stream: {self.streamId}, stat: {self.id}-')

            if self.dataSourceName == 'TotalConnect':
                endpoint = f'/v1/data-stream-stats/dynamic/{self.id}/download'
                fname = f'{self.workspaceId}_{self.streamId}_{self.id}_data.csv'
            else:
                endpoint = f'/v1/data-stream-stats/api/{self.id}/download'
                fname = f'{self.workspaceId}_{self.streamId}_{self.id}_data.zip'
            
            self.download_response = self.connection.call(method='get',endpoint=endpoint)
            if self.download_response:
                with open(folder_path + f'/{fname}','wb') as f:
                    f.write(self.download_response.content)
                return fname
            else: return 'No_Data'

        
        except Exception as X:
            self.log_error(
                source_module='run_stat',
                function_triggered='download',
                error_raised=str(X),
                detail={'stream':self.streamId,'job_id':self.id,'api_response':str(self.download_response) }
            )