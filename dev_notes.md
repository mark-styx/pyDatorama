**General cleanup**
- Relocate the stream/job functions to take place at the workspace level
  - This to ensure that the workspace is aware of the pending items in the queue
  - workspace to control the flow of requests
- Update the workspace attribute to be a dictionary.
- Clean up logging functionality
- Push requests to the connection object


- could also save the workspaces/streams to save on calls and start times


Rerun Batch:

- added logic to keep track of pending jobs in each workspace
  - move on to next if queue full
  - if all queues full, pause for 30 seconds
- Datorama connection to be rate aware
  - pause for ten seconds if limit is reached



Connection State
Each instance should open the file so that it cannot be saved, then force the competing instance to reload the file before trying to save again. Also log a timestamp to ensure the file hasn't changed prior to saving.
Get rid of the file queue thing; keep the integrity aspect from it.

Catch the rate limit error and wait to retry the connection instead of just logging the error.



Job Execution Control Flow:

Job List
- check workspace bandwidth
  - pending vs max
  - last updated
  - state
- trigger job
  - add to queue