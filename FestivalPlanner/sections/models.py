from django.db import models

from festivals.models import Festival


class Section(models.Model):
    """
    Sections table.
    """

    # Define the fields.
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE)
    section_id = models.IntegerField()
    name = models.CharField(max_length=32)
    color = models.CharField(max_length=8)

    # Define a manager.
    sections = models.Manager()

    class Meta:
        db_table = 'section'
        unique_together = ('festival', 'section_id')

    def __str__(self):
        return f'{self.section_id} {self.name}'


class Subsection(models.Model):

    # Define the fields.
    subsection_id = models.IntegerField()
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=4048)
    url = models.URLField(null=True)

    # Define a manager.
    subsections = models.Manager()

    class Meta:
        db_table = 'subsection'
        constraints = [
            models.UniqueConstraint(fields=['subsection_id', 'section'],
                                    name='unique_subsection_id_section')
        ]

    def __str__(self):
        return f'{self.subsection_id} {self.name}, part of {self.section.name}'
