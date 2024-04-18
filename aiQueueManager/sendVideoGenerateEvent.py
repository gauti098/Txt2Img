from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from aiQueueManager.serializers import GenerateFinalVideoSerializer



def sendVideoEvent(videoGenQuery):

    allMainVideo = videoGenQuery.filter(isDefault=1)
    allUser = videoGenQuery.order_by().values_list('multipleScene__user__id').distinct()
    for userId in allUser:
        userId = userId[0]
        curntUserV = allMainVideo.filter(multipleScene__user__id=userId)
        jsonData = GenerateFinalVideoSerializer(curntUserV,many=True).data

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            str(userId),
            {
                "type": "sendSignals",
                "text": {"type": "mainVideo","data": jsonData},
            },
        )

    ## main Video Details
    allMainVideo = videoGenQuery.filter(isDefault=2)
    allUser = allMainVideo.order_by().values_list('multipleScene__user__id').distinct()
    for userId in allUser:
        userId = userId[0]
        curntUserV = allMainVideo.filter(multipleScene__user__id=userId)
        jsonData = GenerateFinalVideoSerializer(curntUserV,many=True).data

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            str(userId),
            {
                "type": "sendSignals",
                "text": {"type": "mainVideoDetails","data": jsonData},
            },
        )

    ## campaign Solo
    allMainVideo = videoGenQuery.filter(isDefault=0)
    allUser = allMainVideo.order_by().values_list('multipleScene__user__id').distinct()
    for userId in allUser:
        userId = userId[0]
        curntUserV = allMainVideo.filter(multipleScene__user__id=userId)
        jsonData = GenerateFinalVideoSerializer(curntUserV,many=True).data

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            str(userId),
            {
                "type": "sendSignals",
                "text": {"type": "mainVideoDetails","data": jsonData},
            },
        )

