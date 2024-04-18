from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from threading import Thread
import time
def sendMessage(groupName,commandData,delay=1):
    time.sleep(delay)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        groupName,
        {
            "type": "sendCommand",
            "text": commandData,
        },
    )
    return True

def eventFire(user,command,data):
    '''
    Register Event
    ["videoEditor.thumbnailInst.update"]
    '''
    commandData = {"command": command,"data": data}
    _th = Thread(target=sendMessage,args=(user.getWebsocketGroupName(),commandData,))
    _th.start()
    return True