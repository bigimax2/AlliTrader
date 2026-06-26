from django.db import models

class EveAlliance(models.Model):
    alliance_id = models.PositiveIntegerField(primary_key=True, null=False, blank=False)
    creator_corporation_id = models.PositiveIntegerField(null=True, blank=True)
    creator_id = models.PositiveIntegerField(null=True, blank=True)
    date_founded = models.DateTimeField(null=True, blank=True)
    executor_corporation_id = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100, blank=False, null=False)
    ticker = models.CharField(max_length=100,null=True, blank=True)

    class Meta:
        verbose_name = "Альянс"
        verbose_name_plural = "Альянсы"

    def __str__(self):
        return self.name

class EveCorporation(models.Model):
    alliance = models.ForeignKey(EveAlliance, on_delete=models.DO_NOTHING, null=True, blank=True)
    ceo_id = models.PositiveIntegerField(null=True, blank=True)
    creator_id = models.PositiveIntegerField(null=True, blank=True)
    date_founded = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    home_station_id = models.PositiveIntegerField(null=True, blank=True)
    member_count = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100, blank=False, null=False)
    shares = models.PositiveIntegerField(null=True, blank=True)
    tax_rate = models.FloatField(null=True, blank=True)
    ticker = models.CharField(max_length=100,null=True, blank=True)
    url = models.CharField(max_length=100, null=True, blank=True)
    corporation_id = models.PositiveIntegerField(primary_key=True,null=False, blank=False)

    class Meta:
        verbose_name = "Корпорация"
        verbose_name_plural = "Корпорации"

    def __str__(self):
        return self.name


class EveCharacter(models.Model):
    birthday = models.DateTimeField(null=True, blank=True)
    corp = models.ForeignKey(EveCorporation, on_delete=models.CASCADE, null=True, blank=True)
    character_id = models.IntegerField(primary_key=True, blank=False, null=False)
    name = models.CharField(max_length=100, blank=False, null=False)
    security_status = models.FloatField(null=True, blank=True)
    alliance_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Персонаж"
        verbose_name_plural = "Персонажи"

    def __str__(self):
        return self.name

class RoleCharacters(models.Model):
    ceo = models.BooleanField(default=False)
    director = models.BooleanField(default=False)
    personage = models.OneToOneField(EveCharacter, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Корп-роль персонажа'
        verbose_name_plural = 'Корп-роли персонажей'

    def __str__(self):
        return f"CEO: {self.ceo}, Director: {self.director}, Character: {self.personage}"

