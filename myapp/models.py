from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Lineamiento(models.Model):
    imagen = models.ImageField(upload_to='lineamientos/', blank=True, null=True)
    titulo_secundario = models.CharField(max_length=100, blank=True, null=True)
    titulo_principal = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)
    objetivo = models.TextField(blank=True, null=True)
    puntos_clave = models.TextField(max_length=500, blank=True, null=True)  # Cambiado a CharField
    documentos = models.ManyToManyField('Documento', blank=True)  # Relación con otro modelo para documentos

    def __str__(self):
        return self.titulo_principal

class Documento(models.Model):
    nombre = models.CharField(max_length=100)
    url = models.URLField()

    def __str__(self):
        return self.nombre
class Recomendacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    comentario = models.TextField(max_length=500)
    estrellas = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])  # Rating entre 1 y 5 estrellas
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.estrellas} estrellas"

class Pregunta(models.Model):
    seccion    = models.CharField(max_length=100)
    subseccion = models.CharField(max_length=100)
    texto      = models.TextField()

    class Meta:
        ordering = ['seccion', 'subseccion']

    def __str__(self):
        # Muestra las primeras 50 letras de la pregunta
        return self.texto[:50] + ('…' if len(self.texto) > 50 else '')


class Evaluacion(models.Model):
    FASE_CHOICES = [
        ('FASE1', 'Fase 1'),
        ('FASE2', 'Fase 2'),
        ('FASE3', 'Fase 3'),
    ]

    usuario      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre_proyecto = models.CharField(max_length=200, blank=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin    = models.DateTimeField(null=True, blank=True)
    fase         = models.CharField(max_length=10, choices=FASE_CHOICES, default='FASE1')
    # Promedios por sección
    promedio_agencia          = models.FloatField(null=True, blank=True)  # Agencia humana y supervisión
    promedio_bienestar        = models.FloatField(null=True, blank=True)  # Bienestar Social y Ambiental
    promedio_diversidad       = models.FloatField(null=True, blank=True)  # Diversidad, no discriminación y equidad
    promedio_responsabilidad  = models.FloatField(null=True, blank=True)  # Responsabilidad
    promedio_robustez         = models.FloatField(null=True, blank=True)  # Robustez técnica y seguridad
    promedio_transparencia    = models.FloatField(null=True, blank=True)  # Transparencia
    informe_gpt               = models.TextField(blank=True, help_text="Aquí se almacena el informe generado por GPT")

    def __str__(self):
        return f"{self.usuario.username} — {self.get_fase_display()} @ {self.fecha_inicio:%Y-%m-%d}"


class Respuesta(models.Model):
    VALOR_CHOICES = [(i, str(i)) for i in range(1, 6)]
    evaluacion   = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name='respuestas')
    pregunta     = models.ForeignKey(Pregunta,   on_delete=models.CASCADE)
    valor        = models.IntegerField(choices=VALOR_CHOICES)
    comentario   = models.TextField(blank=True)
    fecha        = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('evaluacion', 'pregunta')

    def __str__(self):
        # Usa el texto de la pregunta para identificarse
        return f"{self.pregunta} → {self.valor}"
