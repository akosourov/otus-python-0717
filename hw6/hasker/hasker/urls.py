from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin

# from django.contrib.auth import get_user_model
# from rest_framework import serializers, viewsets, routers
#
# from api.views import QuestionViewSet
#
# User = get_user_model()
#
#
# class UserSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = User
#         fields = ('username', 'email')
#
#
# class UserViewSet(viewsets.ModelViewSet):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#
#
# router = routers.DefaultRouter()
# router.register(r'users', UserViewSet)
# router.register(r'questions', QuestionViewSet)


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('askme.urls')),
    url(r'^', include('hasker_user.urls')),
    # url(r'^api/v1/', include(router.urls)),
    url(r'^api/v1/', include('api.urls')),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
