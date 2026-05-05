from django.db import models
import uuid

from user.models import CustomUser



class Event(models.Model):
    class StatusChoice(models.TextChoices):
        FIRST = "Fi", "First"
        NEXT = "Ne", "Next"
        LIGHT = "Li", "Light"
        MEDIUM = "Me", "Medium"
        ADVANCED = "Ad", "Advanced"
        HARD = "Ha", "Hard"
        MASTER = "Ma", "Master"


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    measure = models.CharField(default="TRAINING")
    date=models.DateTimeField()
    level = models.CharField(max_length=2, choices=StatusChoice.choices, db_index=True,)
    place=models.CharField()
    trainer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="events",
    )
    members= models.ManyToManyField(CustomUser,blank=True,related_name="events_members")
    reserve = models.ManyToManyField(CustomUser,blank=True,related_name="events_reserve")
    max_member= models.IntegerField(blank=True,null=True)
    message_id= models.IntegerField(blank=True,null=True)
    link = models.URLField(blank=True,null=True)
    photo = models.ImageField(blank=True,null=True)

class Member(models.Model):
    member = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="members",
    )
    pos=models.IntegerField()
    event=models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="member_events",
    )
    def __str__(self) -> str:
        return f"{self.member.first_name} {self.pos}"

class Reserve(models.Model):
    reserve = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reserves",
    )
    pos=models.IntegerField()
    event=models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="reserve_events",
    )
    def __str__(self) -> str:
        return f"{self.reserve.first_name} {self.pos}"