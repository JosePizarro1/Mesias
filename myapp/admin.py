from django.contrib import admin
from .models import Lineamiento, Recomendacion, Documento

# Personalización del admin para el modelo Lineamiento
class LineamientoAdmin(admin.ModelAdmin):
    list_display = ('titulo_principal', 'titulo_secundario', 'categoria', 'fecha', 'descripcion')  # Muestra más campos relevantes
    search_fields = ('titulo_principal', 'titulo_secundario', 'descripcion')  # Permite buscar en más campos
    list_filter = ('categoria', 'fecha')  # Filtros útiles por categoría y fecha
    list_per_page = 10  # Controla cuántos elementos se muestran por página
    ordering = ('-fecha',)  # Ordena los resultados por fecha descendente
    filter_horizontal = ('documentos',)  # Mejora la relación ManyToMany para seleccionar documentos

admin.site.register(Lineamiento, LineamientoAdmin)


# Personalización del admin para el modelo Recomendacion
@admin.register(Recomendacion)
class RecomendacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'comentario', 'estrellas', 'fecha')  # Muestra los campos más relevantes
    search_fields = ('usuario__username', 'comentario')  # Permite buscar por el nombre de usuario y comentario
    list_filter = ('estrellas', 'fecha')  # Filtros útiles por estrellas y fecha
    list_per_page = 15  # Controla cuántos elementos se muestran por página
    ordering = ('-fecha',)  # Ordena las recomendaciones por fecha descendente

# Personalización del admin para el modelo Documento (para facilitar la gestión de documentos)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'url')  # Muestra el nombre y la URL
    search_fields = ('nombre',)  # Permite buscar por el nombre del documento
    list_filter = ('nombre',)  # Filtro por nombre del documento
    list_per_page = 20  # Controla cuántos documentos se muestran por página

admin.site.register(Documento, DocumentoAdmin)
