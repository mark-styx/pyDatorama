class Bad_HTTP_Response(Exception):
    '''Exception to notify user of unexpected HTTP response.'''

    def __init__(self,status):
        self.message = f'Website responded with a {status} code.'
        super().__init__(self.message)


class Unequal_Input_Error(Exception):
    '''Exception to enforce inputs of equal length.'''

    def __init__(self):
        self.message = 'expected inputs of equal length'
        super().__init__(self.message)


class DateInputError(Exception):
    '''Exception to enforce date input formatting.'''

    def __init__(self,value):
        self.message = f'Input date "{value}" is not properly formatted'
        super().__init__(self.message)


class MissingStreamName(Exception):
    '''Exception to enforce stream name input.'''

    def __init__(self):
        self.message = 'No name provided for stream creation.'
        super().__init__(self.message)