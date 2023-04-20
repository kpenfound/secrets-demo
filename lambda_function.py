from datetime import datetime

def lambda_handler(event, context):
    now = datetime.now().strftime('Hi Demo people! %Y/%m/%d %H:%M:%S')
    return {
        'time': now
    }