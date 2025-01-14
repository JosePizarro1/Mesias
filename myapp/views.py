from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import *
from django.contrib.auth.models import User

def lineamiento_detalle(request, id):
    lineamiento = get_object_or_404(Lineamiento, pk=id)
    
    # Obtener el siguiente y el anterior lineamiento
    try:
        siguiente_lineamiento = Lineamiento.objects.filter(id__gt=lineamiento.id).order_by('id').first()
    except Lineamiento.DoesNotExist:
        siguiente_lineamiento = None
    
    try:
        anterior_lineamiento = Lineamiento.objects.filter(id__lt=lineamiento.id).order_by('-id').first()
    except Lineamiento.DoesNotExist:
        anterior_lineamiento = None
    
    context = {
        'lineamiento': lineamiento,
        'siguiente_lineamiento': siguiente_lineamiento,
        'anterior_lineamiento': anterior_lineamiento
    }
    return render(request, 'lineamientos_detalle.html', context)

def ver_lineamientos(request):
    query = request.GET.get('q', '')
    lineamientos = Lineamiento.objects.all()

    if query:
        lineamientos = lineamientos.filter(titulo_principal__icontains=query)  # Filtra por título principal

    return render(request, 'ver_lineamientos.html', {'lineamientos': lineamientos, 'query': query})

def LineamientoDetalleView(request, id):
    lineamiento = get_object_or_404(Lineamiento, id=id)
    
    # Obtener el siguiente y el anterior lineamiento
    siguiente_lineamiento = Lineamiento.objects.filter(id__gt=lineamiento.id).order_by('id').first()
    anterior_lineamiento = Lineamiento.objects.filter(id__lt=lineamiento.id).order_by('-id').first()

    context = {
        'lineamiento': lineamiento,
        'siguiente_lineamiento': siguiente_lineamiento,
        'anterior_lineamiento': anterior_lineamiento
    }

    return render(request, 'lineamiento_detalle.html', context)
    
def ingreso(request):
    lineamientos = Lineamiento.objects.all()
    return render(request, 'ingreso.html')

def home(request):
    lineamientos = Lineamiento.objects.all()
    recomendaciones = Recomendacion.objects.all().order_by('-fecha')[:10]  # Últimas 10 recomendaciones

    return render(request, 'home.html', {'lineamientos': lineamientos,
                                         'recomendaciones': recomendaciones
                                         })
def recomendacion(request):
    # Verifica si el usuario ya tiene una recomendación
    if Recomendacion.objects.filter(usuario=request.user).exists():
        return redirect('ingreso')  # Redirige si ya tiene una recomendación

    if request.method == 'POST':
        estrellas = request.POST.get('estrellas')
        comentario = request.POST.get('comentario')
        Recomendacion.objects.create(usuario=request.user, estrellas=estrellas, comentario=comentario)
        return redirect('ingreso')  # Redirige después de guardar la recomendación

    return render(request, 'recomendacion.html')
from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('home')  # Redirige después de cerrar sesión

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('ingreso')  # Cambia 'ingreso' al nombre de la URL de la página a la que deseas redirigir
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Validaciones básicas
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            messages.success(request, '¡Registro exitoso! Ahora puedes iniciar sesión.')
            login(request, user)  # Iniciar sesión automáticamente al registrarse
            return redirect('login')  # Redirigir a la página de inicio de sesión

    return render(request, 'register.html')