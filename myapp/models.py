from django.db import models
from django.contrib.auth.models import User

class Lineamiento(models.Model):
    imagen = models.ImageField(upload_to='lineamientos/', blank=True, null=True)
    titulo_secundario = models.CharField(max_length=100, blank=True, null=True)
    titulo_principal = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)
    objetivo = models.TextField(blank=True, null=True)
    puntos_clave = models.CharField(max_length=500, blank=True, null=True)  # Cambiado a CharField
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