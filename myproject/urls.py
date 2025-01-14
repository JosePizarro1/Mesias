
from django.contrib import admin
from django.urls import path
from myapp.views import *
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register, name='register'), 
    path('ingreso/', ingreso, name='ingreso'),  # Define la ruta para ingreso
    path('lineamiento/<int:id>/', LineamientoDetalleView, name='lineamiento_detalle'),
    path('recomendacion/', recomendacion, name='recomendacion'),
    path('logout/', logout_view, name='logout'),
    path('lineamiento/siguiente/<int:id>/', lineamiento_detalle, name='siguiente_lineamiento'),
    path('lineamiento/anterior/<int:id>/', lineamiento_detalle, name='lineamiento_anterior'),
    path('lineamientos/', ver_lineamientos, name='ver_lineamientos'),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)