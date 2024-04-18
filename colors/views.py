from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response

from colors.models import Colors



class ColorsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        user = request.user
        _colorInst,created = Colors.objects.get_or_create(user=user)
        content = {'results': _colorInst.getColors()}
        return Response(content,status=status.HTTP_200_OK)

    def post(self, request, format=None):
        user = request.user
        _colorInst,created = Colors.objects.get_or_create(user=user)
        _colors = request.data.get("colors",None)
        if _colors:
            _nonVC = _colorInst.setColors(_colors.strip(','))
            if len(_nonVC)>0:
                content = {'colors': {'message': 'Some Data are not Valid.','data': _nonVC}}
                return Response(content,status=status.HTTP_200_OK)
            else:
                return Response(True,status=status.HTTP_200_OK)
        else:
            return Response({"colors": {'message': "This Field is Required."}},status=status.HTTP_400_BAD_REQUEST)
        

from colors.task import taskCheck

class HealthCheckView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        # _c = int(request.GET.get('c',10))
        # _t = int(request.GET.get('t',10))
        # _c = Colors.objects.all().count()
        # _task = taskCheck.delay({'c': _c})
        content = {'osinfo': {}}
        return Response(content,status=status.HTTP_200_OK)
