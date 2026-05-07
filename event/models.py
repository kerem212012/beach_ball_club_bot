from django.db import models
import uuid

from user.models import CustomUser



class Event(models.Model):
    class StatusChoice(models.TextChoices):
        FIRST = "Fi", "First"
        FIRST_AND_NEXT = "FN", "First-Next"
        NEXT = "Ne", "Next"
        NEXT_AND_LIGHT = "NL", "Next-Light"
        LIGHT = "Li", "Light"
        LIGHT_AND_MEDIUM = "LM", "Light-Medium"
        MEDIUM = "Me", "Medium"
        MEDIUM_AND_ADVANCED = "MA", "Medium-Advanced"
        ADVANCED = "Ad", "Advanced"
        ADVANCED_AND_HARD = "AH", "Advanced-Hard"
        HARD = "Ha", "Hard"
        HARD_AND_MASTER = "HM", "Hard-Master"
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
    photo = models.ImageField(blank=True,null=True,upload_to="events",default="events/default.png")

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