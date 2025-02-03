from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Party(models.Model):
    party_code = models.CharField(max_length=6, unique=True)
    host = models.ForeignKey(User, related_name='hosted_parties', on_delete=models.CASCADE)
    participants = models.ManyToManyField(User, related_name='joined_parties')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Party {self.party_code}"
