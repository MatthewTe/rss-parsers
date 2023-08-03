import logging
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from collections import OrderedDict

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
       
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        if log_record.get('message'):
            log_record['message'] = log_record['message']
        else:
            log_record['message'] = record.message

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record and serializes to json"""
        message_dict: Dict[str, Any] = {}
        # FIXME: logging.LogRecord.msg and logging.LogRecord.message in typeshed
        #        are always type of str. We shouldn't need to override that.
        if isinstance(record.msg, dict):
            message_dict = record.msg
            record.message = ""
        else:
            record.message = record.getMessage()
        # only format time if needed
        if "asctime" in self._required_fields:
            record.asctime = self.formatTime(record, self.datefmt)

        # Manually overwriting the exec info decleration logic as the exception has already been generated
        # on the log emittion side so we should be okay to just recieve the log and save the traceback to the
        # json dict: 
        if record.exc_info and not message_dict.get('exc_info'):
            message_dict['exc_info'] = record.exc_info
        
        if not message_dict.get('exc_info') and record.exc_text:
            message_dict['exc_info'] = record.exc_text
        # Display formatted record of stack frames
        # default format is a string returned from :func:`traceback.print_stack`
        if record.stack_info and not message_dict.get('stack_info'):
            message_dict['stack_info'] = self.formatStack(record.stack_info)

        log_record: Dict[str, Any] = OrderedDict()
        self.add_fields(log_record, record, message_dict)
        log_record = self.process_log_record(log_record)

        return self.serialize_log_record(log_record)
