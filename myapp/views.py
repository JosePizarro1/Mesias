from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import *
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
import json
from django.views.decorators.http import require_POST
import re
from django.db.models import Avg
from django.utils import timezone    # ← Aquí
from django.conf import settings
import openai
from openai import OpenAI
import os
from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta
# Inicializa el cliente de OpenAI con tu API Key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY))

@login_required
@require_POST
def analizar_view(request, eval_id):
    ev = get_object_or_404(Evaluacion, pk=eval_id, usuario=request.user)

    # Solo procesar si estamos en Fase 2
    if ev.fase != 'FASE2':
        return JsonResponse({'message': 'Evaluación no en estado correcto.'}, status=400)

    # 1) Recopilar promedios no cero
    SECCIONES = [
        ('Agencia humana y supervisión', ev.promedio_agencia),
        ('Bienestar Social y Ambiental', ev.promedio_bienestar),
        ('Diversidad, no discriminación y equidad', ev.promedio_diversidad),
        ('Responsabilidad', ev.promedio_responsabilidad),
        ('Robustez técnica y seguridad', ev.promedio_robustez),
        ('Transparencia', ev.promedio_transparencia),
    ]
    prompt = "Estos son los promedios por sección (solo >0):\n"
    for nombre, val in SECCIONES:
        if val and val > 0:
            prompt += f"- {nombre}: {val:.2f}\n"

    # 2) Añadir preguntas y respuestas
    prompt += "\nDetalles de respuestas por sección:\n"
    for nombre, _ in SECCIONES:
        respuestas = Respuesta.objects.filter(
            evaluacion=ev,
            pregunta__seccion=nombre
        ).select_related('pregunta').order_by('pregunta__subseccion')
        if respuestas.exists():
            prompt += f"\n[{nombre}]\n"
            for r in respuestas:
                prompt += f"* {r.pregunta.texto} → {r.valor}\n"

    # 3) Instrucciones D-E-S-C
    prompt += """
Por favor genera una retroalimentación de máximo 150 palabras siguiendo esta estructura:
1. D – Describir: identifica y resume los hallazgos clave.
2. E – Expresar: explica el impacto o implicancia.
3. S – Sugerir: sugiere una acción o mejora.
4. C – Consecuencia: advierte sobre los riesgos de no actuar.
"""

    # 4) Llamada a OpenAI usando la nueva interfaz
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente que da retroalimentación ética concisa."},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        feedback = response.choices[0].message.content.strip()
    except Exception as e:
        return JsonResponse({'message': f'Error al consultar OpenAI: {e}'}, status=500)

    # 5) Guardar resultado y avanzar a Fase 3
    ev.informe_gpt = feedback
    ev.fase        = 'FASE3'
    ev.fecha_fin   = timezone.now()
    ev.save()

    return JsonResponse({'message': 'Análisis completado. ¡Ve tus resultados!'})



@login_required
def evaluaciones_view(request):
    evs = Evaluacion.objects.filter(
        usuario=request.user
    ).exclude(fase='FASE1').order_by('-fecha_inicio')
    return render(request, 'evaluaciones.html', {
        'evaluaciones': evs
    })

@login_required
@require_POST
def responder_ajax(request, eval_id, seccion):
    ev = get_object_or_404(Evaluacion, pk=eval_id, usuario=request.user)

    # 1) Guardar cada respuesta
    for key, val in request.POST.items():
        if not key.startswith('valor_'):
            continue
        pid   = int(key.split('_',1)[1])
        valor = int(val)
        pregunta = get_object_or_404(Pregunta, pk=pid)
        Respuesta.objects.update_or_create(
            evaluacion=ev,
            pregunta=pregunta,
            defaults={'valor': valor}
        )

    # 2) Nombres exactos de tus secciones
    SECCIONES = {
        'Agencia humana y supervisión': 'promedio_agencia',
        'Bienestar Social y Ambiental': 'promedio_bienestar',
        'Diversidad, no discriminación y equidad': 'promedio_diversidad',
        'Responsabilidad': 'promedio_responsabilidad',
        'Robustez técnica y seguridad': 'promedio_robustez',
        'Transparencia': 'promedio_transparencia',
    }

    # 3) Calcular y asignar promedios
    for nombre_sec, campo_modelo in SECCIONES.items():
        media = (
            Respuesta.objects
                     .filter(evaluacion=ev, pregunta__seccion=nombre_sec)
                     .aggregate(avg_val=Avg('valor'))['avg_val']
        )
        setattr(ev, campo_modelo, float(media) if media is not None else None)


    ev.fase = 'FASE2'
    ev.fecha_fin = timezone.now()
    ev.save()

    # Mensaje de éxito
    messages.success(request, "¡Respuestas guardadas! Has avanzado a Fase 2.")

    # Redirige a la vista de evaluaciones
    return redirect('evaluaciones')

@login_required
@require_GET
def get_response(request):
    msg = request.GET.get('message', '').strip()
    lower = msg.lower()
    session = request.session

    # ————————————————————————————————
    # Asegura que tengamos una Evaluación en sesión
    # ————————————————————————————————
    if 'eval_id' not in session:
        # Intentar recuperar una evaluación pendiente
        ev = (
            Evaluacion.objects
            .filter(usuario=request.user, nombre_proyecto__isnull=True)
            .order_by('-created_at')  # Solo si tienes este campo
            .first()
        )

        if not ev:
            ev = Evaluacion.objects.create(usuario=request.user)

        session['eval_id'] = ev.id
        session.modified = True
    else:
        ev = Evaluacion.objects.get(pk=session['eval_id'], usuario=request.user)


    # 0) Reinicio completo
    if 'reiniciar' in lower:
        session.clear()
        return JsonResponse({
            'response': (
                "👉 Flujo reiniciado.<br>"
                "Para empezar, por favor indícame el nombre de tu proyecto."
            )
        })

    # 1) Pedir nombre de proyecto
    if session.get('chat_stage') is None:
        session['chat_stage'] = 'AWAIT_PROJECT'
        session.modified = True
        return JsonResponse({
            'response': (
                "Empezemos cual es el <strong>nombre de tu proyecto?</strong>."
            )
        })

    # 2) Guardar nombre provisional y pedir confirmación
    if session['chat_stage'] == 'AWAIT_PROJECT':
        # Guardamos exactamente lo que envió
        session['pending_project'] = msg
        session['chat_stage']      = 'AWAIT_CONFIRM'
        session.modified = True

        return JsonResponse({
            'response': (
                f"✅ El nombre de proyecto será: <strong>\"{msg}\"</strong>.<br>"
                "¿Es correcto? Responde <strong>Sí</strong> o <strong>No</strong>."
            ),
            'project': msg,
            'confirm_required': True
        })

    # 3) Confirmación del nombre
    if session['chat_stage'] == 'AWAIT_CONFIRM':
        if lower in ('sí', 'si', 's', 'yes', 'y'):
            session['chat_stage'] = 'AWAIT_SCOPE'
            session.modified = True

            # Guardar aquí solo si lo confirmó
            ev = Evaluacion.objects.get(pk=session['eval_id'], usuario=request.user)
            ev.nombre_proyecto = session.get('pending_project')
            ev.save()

            return JsonResponse({
                'response': (
                    "¡Genial! 🎉<br>"
                    "Ahora, ¿deseas responder <strong>todas</strong> las preguntas o solo una <strong>sección específica</strong>?<br>"
                    "Escribe <em>todas</em> o el nombre de la sección."
                )
            })
        else:
            # Vuelve a pedir el nombre
            session['chat_stage'] = 'AWAIT_PROJECT'
            session.modified = True
            return JsonResponse({
                'response': (
                    "Entendido, escribamos de nuevo el nombre de tu proyecto."
                )
            })

    # 4) Procesar alcance (igual que antes)
    if session['chat_stage'] == 'AWAIT_SCOPE':
        secciones = list(
            Pregunta.objects
                    .values_list('seccion', flat=True)
                    .distinct()
                    .order_by('seccion')
        )

        if 'todas' in lower:
            qs = list(Pregunta.objects.all())
            session['chat_stage'] = 'RESPONDIENDO'
            session.modified = True

            preguntas_json = [
                {'id': p.id, 'texto': p.texto}
                for p in qs
            ]
            return JsonResponse({
                'type': 'questions',
                'section': 'todas',
                'count': len(preguntas_json),
                'questions': preguntas_json
            })

        seleccion = next((s for s in secciones if s.lower() in lower), None)
        if seleccion:
            qs = list(Pregunta.objects.filter(seccion=seleccion))
            session['chat_stage'] = 'RESPONDIENDO'
            session.modified = True

            preguntas_json = [
                {'id': p.id, 'texto': p.texto}
                for p in qs
            ]
            return JsonResponse({
                'type': 'questions',
                'section': seleccion,
                'count': len(preguntas_json),
                'questions': preguntas_json
            })

        # No reconoce sección
        return JsonResponse({
            'response': (
                "Estas son las disponibles:<br>"
                f"<ul class='list-disc ml-6'>"
                + "".join(f"<li>{s}</li>" for s in secciones)
                + "</ul><br>Escribe el nombre exacto o <em>todas</em>."
            )
        })

    # 5) Ya en RESPONDIENDO o DONE
    return JsonResponse({
        'response': (
            "👍 Ya recibiste las preguntas. Si quieres <strong>reiniciar</strong>, "
            "escribe 'reiniciar'."
        )
    })


@login_required
def chat_view(request):
    # Limpiamos cualquier estado de chat previo
    request.session.pop('chat_stage', None)

    # 1) Buscamos una evaluación en Fase 1 aún abierta (sin fecha_fin)
    ev = (
        Evaluacion.objects
                  .filter(usuario=request.user, fase='FASE1', fecha_fin__isnull=True)
                  .order_by('-fecha_inicio')
                  .first()
    )

    # 2) Si no hay ninguna, creamos una nueva
    if not ev:
        ev = Evaluacion.objects.create(usuario=request.user, fase='FASE1')

    # 3) Guardamos su ID en sesión (para get_response)
    request.session['eval_id'] = ev.id
    request.session.modified = True

    # 4) Renderizamos pasando el ID
    return render(request, 'asistente.html', {
        'evaluacion_id': ev.id
    })

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
@login_required
def ingreso(request):
    usuario = request.user
    qs      = Evaluacion.objects.filter(usuario=usuario)

    # Métricas rápidas
    total_evals       = qs.count()
    total_projects    = qs.values('nombre_proyecto') \
                          .distinct() \
                          .exclude(nombre_proyecto='') \
                          .count()
    fase2_pendientes  = qs.filter(fase='FASE2').count()
    fase3_completadas = qs.filter(fase='FASE3').count()

    # Evolución últimos 6 meses (igual que antes)
    meses_labels = []
    meses_data   = []
    comienzo = now().replace(day=1)
    for i in range(5, -1, -1):
        mes = comienzo - timedelta(days=30*i)
        meses_labels.append(mes.strftime('%b %Y'))
        meses_data.append(
            qs.filter(
                fecha_inicio__year=mes.year,
                fecha_inicio__month=mes.month
            ).count()
        )

    # 1) Por sección de proyecto
    secciones = list(
        Pregunta.objects.values_list('seccion', flat=True)
                 .distinct()
                 .order_by('seccion')
    )
    sec_counts = []
    for sec in secciones:
        # contamos evaluaciones que tienen al menos una respuesta en esta sección
        cnt = qs.filter(
            respuestas__pregunta__seccion=sec
        ).distinct().count()
        sec_counts.append(cnt)

    # 2) Por fase
    # Iniciamos en cero y luego rellenamos
    fase_map = {'FASE1': 0, 'FASE2': 0, 'FASE3': 0}
    for entry in qs.values('fase').annotate(total=Count('pk')):
        fase_map[entry['fase']] = entry['total']
    fase_labels = ['Fase 1', 'Fase 2', 'Fase 3']
    fase_data   = [fase_map['FASE1'], fase_map['FASE2'], fase_map['FASE3']]

    return render(request, 'ingreso.html', {
        'total_projects':    total_projects,
        'total_evals':       total_evals,
        'fase2_pendientes':  fase2_pendientes,
        'fase3_completadas': fase3_completadas,
        'meses_labels':      meses_labels,
        'meses_data':        meses_data,
        'sec_labels':        secciones,
        'sec_data':          sec_counts,
        'fase_labels':       fase_labels,
        'fase_data':         fase_data,
    })


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
@login_required
def perfil(request):
    """
    Muestra y permite editar el perfil del usuario.
    """
    if request.method == 'POST':
        user = request.user

        # Cambiar nombre de usuario
        if 'username' in request.POST:
            new_username = request.POST.get('username')
            if new_username and new_username != user.username:
                if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                    messages.error(request, "El nombre de usuario ya está en uso.")
                else:
                    user.username = new_username
                    user.save()
                    messages.success(request, "Nombre de usuario actualizado correctamente.")

        # Cambiar email
        elif 'email' in request.POST:
            new_email = request.POST.get('email')
            if new_email and new_email != user.email:
                if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                    messages.error(request, "El correo electrónico ya está en uso.")
                else:
                    user.email = new_email
                    user.save()
                    messages.success(request, "Correo electrónico actualizado correctamente.")

        # Cambiar contraseña
        elif 'password1' in request.POST and 'password2' in request.POST:
            pw1 = request.POST.get('password1')
            pw2 = request.POST.get('password2')
            if pw1 and pw2:
                if pw1 != pw2:
                    messages.error(request, "Las contraseñas no coinciden.")
                else:
                    user.set_password(pw1)
                    user.save()
                    messages.success(request, "Contraseña actualizada correctamente. Por favor, vuelve a iniciar sesión.")

                    # Redirigir para evitar que pierda el login tras cambiar contraseña
                    return redirect('login')

    return render(request, 'perfil.html')

def recomendaciones(request):
    if request.method == 'POST':
        comentario = request.POST.get('comentario')
        estrellas = request.POST.get('estrellas')

        # Verifica si ya hizo una recomendación
        if Recomendacion.objects.filter(usuario=request.user).exists():
            messages.error(request, "Ya has enviado una recomendación.")
        else:
            Recomendacion.objects.create(
                usuario=request.user,
                comentario=comentario,
                estrellas=estrellas
            )
            messages.success(request, "¡Gracias por tu recomendación!")

        return redirect('recomendaciones')

    return render(request, 'recomendaciones.html')


def preguntas_frecuentes(request):
    """
    Muestra la página de Preguntas Frecuentes.
    """
    return render(request, 'preguntas_frecuentes.html')
