from django.db import models

# Create your models here.
class Wish(models.Model):
    color = models.TextField(max_length='7', null="True")
    pub_date = models.DateTimeField("date wished")
    sound = models.FilePathField(path='media/')
