# *Datorama*

## *Overview*

The purpose of this library is to provide simple wrapper to interface with the Datorama api. An API token provided by Datorama is required to access the API. This library is currently limited to the 'platform' requests. These functions generally are used for streamlining or automating administrative and bulk management tasks for Datorama. The available functionality includes:

- Bulk stream processing
- Bulk stream renaming
- Bulk job rerunning
- Single job rerun
- Single stream reprocess
- Rerun all jobs for a stream
- Collect metadata for all workspaces
- Collect metadata for all streams
- Collect metadata for all jobs
- Update the metadata for a stream

Future developments should include:

- Reporting api functions
- Shuffling tokens as rate limits are reached
- User/Workspace management functions


Not all functionality is present in this document. Functions and attributes can be accessed through each objects ''dir'' method. Additionally the pydocs will also be provided, and docstrings are provided for most things. Additionally, I do not consider this library to be anywhere close to complete. I wrote this to simplify my tasks and made many many changes on the fly as new functionality became needed. There are substantial areas that need to be cleaned up, however it is functional for what I needed it to do. I encourage everyone to provide feedback, additions, and edits where necessary. Hopefully this work is useful for others as it has been for me so far.

<br>

### *Getting Started*

#### *Installation*

Pip install wheel file.

#### *Using the library*

To begin using the library, import the 'datorama' class from Datorama.

```
from Datorama import datorama
```

Next, instantiate the datorama class and pass your api token.

```
dr = datorama(
    api_token,
    verbose=False,
    pause=.1,
    restore_spaces=False,
    restore_streams=False,
    restore_jobs=False
)
```

You should now be ready to get started.

### General Class Structure

**datorama** <br>
|_  **Workspace** <br>
&emsp;| - *functions (get_streams,etc)* <br>
&emsp;| - *attrs (id, create date, etc)* <br>
&emsp;|_  **Datastream** <br>
&emsp;&emsp;| - *functions (get_jobs, process, rerun_all, etc.)* <br>
&emsp;&emsp;| - *attrs (id, lastRowsProcessed, etc.)* <br>
&emsp;&emsp;|_  **Job** <br>
&emsp;&emsp;&emsp;| *- functions (rerun)* <br>
&emsp;&emsp;&emsp;| *- attrs (id, startDate, etc)* <br>
|_ **errors** (Should be phased out eventually as it has become unecessary)<br>
&emsp;| - *custom exceptions* <br>
|_ **Timer** <br>
&emsp;| - *execution timer and estimator* <br>
|_ **Connection** <br>
&emsp;| - *Initiates all api requests* <br>
&emsp;| - *Handles rate limits* <br>

<br>

#### **Workspaces**

Datorama divides each account into a set of workspaces, which represents an individual work environment. The workspace api enables the management and setup of the workspaces (https://developers.datorama.com/docs/manage/workspaces/). The pyDatorama library represents this object as a class with the attributes and functions that are associated to each workspace. Each account has a list of workspaces, and since most platform operations are performed at the datastream level the workspaces are retreived by default at instantiation.

```
dr = datorama(
    api_token,
    verbose=False,
    pause=.1,
    restore_spaces=False,
    restore_streams=False,
    restore_jobs=False
)
```

If the *'restore_spaces'* parameter is set, pyDatorama will create the workspace objects based on the last workspace request retreived from the api. Otherwise, pyDatorama will call the *'List all permitted workspaces'* endpoint from the API and these objects will be created from this output.

The workspace objects act as a manager of the datastreams that belong to them. In rerun or process jobs, each datastream has the ability to check with the workspace to ensure that there is enough capacity to take on an additional job. This is set at the workspace level (the *workspace.throttle* attribute) and is not the default behavior as for most cases it is unnecessary. To complete this process, the workspace will go through each active stream and request an update on the jobs that belong to it. To limit the calls to the api, the workspace will first evaluate that a minimally sufficient time has passed based on the number of active jobs before calling the API to check the status. Again, this behavior is typically not required and is only needed in specific circumstances.

<br>

#### **Datastream**

A data stream in Datorama is a connection to a data source. The data stream API allows setup and management of API data streams (https://developers.datorama.com/docs/manage/data-streams/). The Stream object in pyDatorama represents this object as a class with the attributes and functions that are associated to each stream. Each workspace has a list of data streams, and these can be populated through calling the workspace function or by restoring the last streams that were retrieved for the active workspace if the *restore_streams* parameter is set on instantiation.

<br>

#### **Job**

A job (or stat) in Datorama is a specific instance of a data stream execution.
The data stream stats API allows you to view these statistics in order to understand the status of the process and can indicate whether it's succeeded or failed (https://developers.datorama.com/docs/manage/data-stream-stats/). The Job object in pyDatorama represents this object as a class with the attributes and functions that are associated to each job/stat. Each data stream has a list of jobs, and these can be populated through calling the stream function or by restoring the last jobs that were retrieved for the active stream if the *restore_jobs* parameter is set on instantiation.

<br>

#### **Timer**

The Timer object exists only to provide timing feedback to the user.

<br>

#### **Errors**

The errors module is a collection of custom exception classes to provide more specific feedback to the user. These exception classes should eventually be phased out as they are unnecessary.

<br>

#### **Connection**

The Connection class handles all connections to the Datorama api; This is to ensure that all requests pass through a common object, which allows improved call management. The connection creates a connection profile object that can be accessed by multiple instances of pyDatorama to ensure that requests do not surpass rate limits. Every response from the API contains updated rate counts and reset times that are passed to the shared profile. Each instance of the connection will store a history of the endpoints that were called for additional debugging.

<br>

## *Platform API*

<br>

### *Gathering Data*

#### *Workspaces*

When you instantiate the 'datorama' object it retrieves all of the workspace data by default. These spaces are accessble through the *datarama.workspaces* attribute. Currently, this attribute is a dictionary in the format {id:*workspace*}. Each workspace object contains all the metadata for the space as well as workspace specific functions such as the ability to retrieve all the data streams that belong to it.

#### *Datastream*

The main way to retrieve the datastreams is to call the 'get_all_streams' function from the 'datorama' class.

##### *datorama.get_all_streams()*

This function loops through each workspace and calls its 'get_streams' function. The 'get_streams' function collects all of the metadata for the streams belonging to the workspace and creates 'Stream' objects to be added to the datorama.streams attribute in the format {id:stream}. The stream object contains all of the metadata for each stream and functions to collect job information, rerun jobs, update stream data, and process jobs.

- create_df <br>
  Whether to create a data frame of the stream data.
- workspaces <br>
  List of the workspace ids to collect streams from, collects all by default.

#### *Jobs*

To retrieve the job data for all streams, you should call the 'get_all_jobs_meta' function of the datorama class. Please note that this process can consume a considerable amount of time and API calls. A token is limited to 60 platform calls/minute and 20k/day. If you have 5k streams, this process will take at least ~83 minutes to complete. In many cases it is probably better to identify the specific streams you require job data from and iterate through these streams and calling the *Stream.get_stream_runs* function. Getting stream jobs by either method will create and store job objects within the *datorama.jobs* attribute for convenience. There is also a function available that converts these objects' attributes into a Pandas dataframe. Additionally, each job object has a function available that downloads the actual raw data from that job.

##### *datorama.get_all_jobs()*

This function loops through all data streams and uses the 'get_stream_runs' function of the 'Streams' class to collect the run data for the stream. *Note: This will make at least one call to the API per stream in the datorama.streams dictionary depending on the number of jobs in the stream.*

##### *Stream.get_stream_runs(**pgSize=100,pgNum=1**)*

There may be cases where you do not want to return all jobs for all streams as this can be a lot of data; In addition, there may be thousands of streams and at most 60 call per minute may be made and could take some time to finish. In this case it may be more fitting to access the streams that you want run data for directly through this function. Also, it would probably be wise to specify a large page size to avoid multiple calls being made to collect the job data.

#### *Mapping*

##### *Stream.get_mapping()*

This function can be accessed from the Stream object and will populate it's mapping attribute. The data contained in the mapping attribute will also be found in the config attribute.

#### *Dimensions*

##### *workspace.get_dimensions()*

This function can be accessed from the workspace object and will populate it's dimensions attribute.

#### *Patterns*

##### *workspace.get_patterns()*

This function can be accessed from the workspace object and will populate it's patterns attribute.

#### *Harmonized Dimensions*

##### *workspace.get_harmonized_dimensions()*

This function can be accessed from the workspace object and will populate it's harmonized_dimensions attribute.

<br>

### *Processing*

Currently there are three ways to process a stream: The first and most common method is through the 'datorama' class 'bulk_process_streams' function. The second is through the 'Stream' class 'process' function. The third method is through the ''process_stream_batch' function.

#### *datorama.bulk_process_streams(**streams,starts,ends,d_range=10,create_df=True,export=False,file_name='job_log'**)*

To process a stream the api requires a stream id, start date, and end date. These are represented by the 'streams', 'starts', and 'ends' parameters here.

- streams <br>
  List containing the stream ids to be processed. The individual stream ids should be formatted as integers.
- starts <br>
  List containing the start dates for each stream.
- ends <br>
  List containing the end dates for each stream.
- create_df
  Whether to create a data frame of the job log.
- export <br>
  Whether to create a csv export of the job log; create_df must be set to True as well.
- log_file <br>
  The output filename of the process log file. If there is an existing log, enter the log path and the new records will be appended.

The final parameter is the number of days to include in a process day range. Datorama automatically splits the number of days in a range into chunks of ten days. For example, if you submit a full month to process, Datorama will split this into three jobs of ten days. This ensures that the job ranges submitted are predictable and replicable if there is an error midway through a run.

- d_range <br>
  Integer of the number of days to include in a single job. Large process requests will be split to conform to this requirement.

#### *Stream.process(**start,end**)*

The bulk_process_streams function packages bulk requests to be submitted to this function from the 'datastream' class. Most requests will be submitted through the bulk function. Notably, this function does not split requests into chunks based on date ranges.
-start <br>
The start day of the process range, formatted as yyyy-mm-dd.
-end <br>
The end day of the process range, formatted as yyyy-mm-dd.

#### *datorama.bulk_process_streams(**streams,start,end**)**

This method is particularly useful when you have many streams to process with the same start and end dates. It makes a single call to process each of the listed streams. Typically, I will group a list of streams by start and end dates and then pass each group to this function to conserve api calls.

<br>

### *Rerunning*

There are four methods available to rerun jobs of a datastream: Through the 'datorama' class 'bulk_rerun_jobs' function, the 'Stream' class 'rerun_all_jobs' and 'rerun_job_batch' functions, and the 'Job' class 'rerun' function. Similar to the processing functions, most users should leverage the bulk rerun function over the others.

#### *datorama.rerun_batch(**streams,jobs,create_df=True,export=False,file_name='job_log'**)*

To rerun a job, the api requires the stream id the job belongs to as well as the job ids to be rerun. This function accepts a list of each and groups the jobs by their stream id to limit the number of calls to the api.

- streams <br>
  List containing the stream ids to be processed. The individual stream ids should be formatted as integers.
- jobs <br>
  List containing the job ids to be processed. The individual job ids should be formatted as integers.
- export <br>
  Whether to create a csv export of the related logs.
- file_name <br>
  The output filename of the rerun log file.

#### *datorama.rerun_all(streams,create_df=True,export=False,file_name='job_log')*

This function accepts a list of streams and executes each stream's rerun_all_jobs() function.

- streams <br>
  List containing the stream ids to be processed. The individual stream ids should be formatted as integers.
- export <br>
  Whether to create a csv export of the related logs.
- file_name <br>
  The output filename of the rerun log file.

#### *Stream.rerun_all_jobs()*

This function takes no arguments. It belongs to the 'Stream' class and infers the id required for the api from its attributes. Reruns all jobs for the active stream object.

#### *Stream.rerun_job_batch(**job_ids**)*

This function powers the bulk rerun function. It accepts a list of job ids and uses the stream id attribute of the active stream to generate the payload.

- job_ids <br>
  List containing the job ids (formatted as integers)

#### *Job.rerun(**None**)*

This function also takes no arguments. It belongs to the 'Job' class and infers the required attributes from there. This function makes the same call to the api as the 'rerun_job_batch' function, but simply passes the active job id to the api.

<br>

### *Updates*

There are three functions available to update the metadata for the datastreams. One is a generic 'update_stream' function belonging to the 'Stream' class, and the other is the 'bulk_rename_streams' function of the 'datorama' class. The bulk rename function leverages the update function of each stream. The final and most useful is the *stream.patch* function. This function allows you to update a single or multiple parameters of the stream configuration by passing a dictionary.

#### *datorama.bulk_rename_streams(**streams,names,export=True,update_file='update_log.csv'**)*

- streams <br>
  List containing the stream ids to be processed. The individual stream ids should be formatted as integers.
- names <br>
  List containing the names to be used to update each stream.
- export <br>
  Whether to create a csv export of the related logs.
- update_file <br>
  The output filename of the update log file. If there is an existing log, enter the log path and the new records will be appended.

#### *Stream.update_stream(**params**)*

This function accepts a dictionary of parameters to update the metadata of the stream to.

- params
  Dictionary of new values.

#### *Stream.patch(**params**)*


This function accepts a dictionary of parameters to update the metadata of the stream to.

- params
  Dictionary of new values.

The main difference between this function and the update_stream function is that the update_stream function uses an endpoint that requires the entire configuration of the stream to be specified. To make this easier to use, this function updates the current configuration of the stream (in the *stream.config* attribute) based on the update params. Conversely, the patch function's endpoint just requires the values that are being changed to be specified. Ultimately this is a far safer and simpler practice and therefore should be the preferred usage.
