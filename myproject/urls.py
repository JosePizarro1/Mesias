
from django.contrib import admin
from django.urls import path
from myapp.views import *
from django.conf import settings
from django.contrib.auth import views as auth_views
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
    path('chat/', chat_view, name='chat'),
    path('api/get_response', get_response, name='get_response'),
    path('faq/', preguntas_frecuentes, name='preguntas_frecuentes'),
    path('perfil/', perfil, name='perfil'),
    path('recomendaciones/', recomendaciones, name='recomendaciones'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('api/get_response/', get_response, name='get_response'),
    path('evaluaciones/', evaluaciones_view, name='evaluaciones'),
    path('evaluaciones/responder/<int:eval_id>/<str:seccion>/',responder_ajax,name='responder_ajax'),
    path('evaluaciones/analizar/<int:eval_id>/',analizar_view,name='analizar'),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)