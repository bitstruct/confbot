from django.db import models

class Need(models.Model):
    nick = models.CharField(max_length=30)
    need = models.TextField()

class Provider(models.Model):
    nick = models.CharField(max_length=30)
    provides = models.TextField()
